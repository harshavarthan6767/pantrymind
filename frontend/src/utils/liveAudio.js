export class LiveAudioStreamer {
  constructor(endpointPath, onMessage, onAudioStarted, onAudioEnded) {
    this.ws = null;
    this.audioContext = null;
    this.recordContext = null;
    this.micStream = null;
    this.workletNode = null;
    
    this.playQueue = [];
    this.currentSources = [];
    this.isPlaying = false;
    this.nextPlayTime = 0;
    this.assistantTurnOpen = false;
    this.receivedTurnComplete = false;
    this.drainTimer = null;
    this.drainGraceMs = 450;
    this.audioStallTimer = null;
    this.audioStallGraceMs = 3000;
    this.manualStop = false;
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;
    this.maxReconnectAttempts = 6;
    
    this.onMessage = onMessage; 
    this.onAudioStarted = onAudioStarted; 
    this.onAudioEnded = onAudioEnded;
    this.endpointPath = endpointPath || '/api/voice/live';
  }

  async start() {
    this.manualStop = false;
    await this.connectWebSocket();

    this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 24000
    });
    await this.audioContext.resume();

    this.recordContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    await this.recordContext.resume();

    this.micStream = await navigator.mediaDevices.getUserMedia({ 
        audio: { 
            channelCount: 1, 
            sampleRate: 16000, 
            echoCancellation: true, 
            noiseSuppression: true,
            autoGainControl: true
        }
    });

    const source = this.recordContext.createMediaStreamSource(this.micStream);
    await this.recordContext.audioWorklet.addModule("/audio/pcmProcessor.js");
    this.workletNode = new AudioWorkletNode(this.recordContext, "pcm-processor");
    
    // ==========================================
    // CRITICAL FIX: AUDIO BUFFERING
    // ==========================================
    let audioBuffer = [];

    this.workletNode.port.onmessage = (event) => {
      if (
        !this.ws ||
        this.ws.readyState !== WebSocket.OPEN ||
        this.assistantTurnOpen
      ) return;
      
      const buffer = event.data;
      if (buffer instanceof ArrayBuffer) {
        const bytes = new Uint8Array(buffer);
        
        // Push raw bytes into our temporary array
        for (let i = 0; i < bytes.length; i++) {
          audioBuffer.push(bytes[i]);
        }
        
        // Only trigger a network request when we have collected ~128ms of audio (2048 bytes)
        if (audioBuffer.length >= 2048) {
          let binary = '';
          for (let i = 0; i < audioBuffer.length; i++) {
            binary += String.fromCharCode(audioBuffer[i]);
          }
          
          this.ws.send(JSON.stringify({
            type: "audio",
            data: btoa(binary),
            mime_type: "audio/pcm;rate=16000"
          }));
          
          audioBuffer = []; // Reset the buffer for the next batch
        }
      }
    };

    source.connect(this.workletNode);
    const silentGain = this.recordContext.createGain();
    silentGain.gain.value = 0.001; 
    this.workletNode.connect(silentGain);
    silentGain.connect(this.recordContext.destination);
  }

  async connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.hostname}:8000${this.endpointPath}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onmessage = async (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "audio") {
        if (!this.assistantTurnOpen && this.onAudioStarted) {
          this.onAudioStarted();
        }
        this.assistantTurnOpen = true;
        this.receivedTurnComplete = false;
        this.clearDrainTimer();
        this.clearAudioStallTimer();
        this.enqueueAudio(msg.data, msg.mime_type);
      } else if (msg.type === "turn_complete") {
        this.receivedTurnComplete = true;
        this.clearAudioStallTimer();
        this.finishAssistantTurnIfDrained();
      } else if (msg.type === "interrupted") {
        this.receivedTurnComplete = true;
        this.assistantTurnOpen = false;
        this.clearDrainTimer();
        this.clearAudioStallTimer();
        if (this.onAudioEnded) this.onAudioEnded();
        if (this.onMessage) this.onMessage(msg);
      } else if (msg.type === "audio_stalled") {
        this.recoverFromAudioStall(msg);
      } else if (msg.type === "status" || msg.type === "partial_text" || msg.type === "user_transcript" || msg.type === "agent_activity" || msg.type === "agent_result") {
        if (this.onMessage) this.onMessage(msg);
      }
    };

    // NEW: Handle sudden server disconnections so the UI doesn't get stuck
    this.ws.onclose = () => {
      console.log("[VOICE] WebSocket closed by server.");
      this.ws = null;
      if (this.manualStop) {
        this.clearPlaybackQueue();
        this.isPlaying = false;
        return;
      }

      this.scheduleReconnect();
    };

    await new Promise((resolve, reject) => {
      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.ws.send(JSON.stringify({ type: "init", client: "electron_pantrymind" }));
        if (this.onMessage) this.onMessage({ type: "status", message: "Connected" });
        resolve();
      };
      this.ws.onerror = reject;
    });
  }

  scheduleReconnect() {
    if (this.reconnectTimer || this.manualStop) return;

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      if (this.onMessage) this.onMessage({ type: "status", message: "Disconnected" });
      this.clearPlaybackQueue();
      this.isPlaying = false;
      return;
    }

    this.reconnectAttempts += 1;
    const delay = Math.min(750 * this.reconnectAttempts, 4000);
    if (this.onMessage) {
      this.onMessage({
        type: "status",
        message: `Reconnecting voice channel (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
      });
    }

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;
      try {
        await this.connectWebSocket();
      } catch (error) {
        console.warn("[VOICE] Reconnect failed:", error);
        this.scheduleReconnect();
      }
    }, delay);
  }

  enqueueAudio(base64Data, mimeType) {
    const binary = atob(base64Data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    const pcm16 = new Int16Array(bytes.buffer);
    
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) {
      float32[i] = pcm16[i] / 0x8000;
    }
    
    let sampleRate = 24000;
    const match = mimeType?.match(/rate=(\d+)/);
    if (match) sampleRate = Number(match[1]);
    
    const audioBuffer = this.audioContext.createBuffer(1, float32.length, sampleRate);
    audioBuffer.getChannelData(0).set(float32);
    
    this.playQueue.push(audioBuffer);
    this.schedulePlayback();
  }

  schedulePlayback() {
    if (this.playQueue.length === 0) {
      if (this.currentSources.length > 0) return;
      this.isPlaying = false;
      this.scheduleAudioStallCheck();
      this.finishAssistantTurnIfDrained();
      return;
    }

    while (this.playQueue.length > 0) {
      this.isPlaying = true;
      const buffer = this.playQueue.shift();
      const source = this.audioContext.createBufferSource();
      source.buffer = buffer;
      source.connect(this.audioContext.destination);
      
      const startTime = Math.max(this.audioContext.currentTime, this.nextPlayTime);
      source.start(startTime);
      this.nextPlayTime = startTime + buffer.duration;
      
      source.onended = () => {
        this.currentSources = this.currentSources.filter(s => s !== source);
        this.schedulePlayback();
      };
      
      this.currentSources.push(source);
    }
  }

  clearPlaybackQueue() {
    this.clearDrainTimer();
    this.clearAudioStallTimer();
    this.playQueue = [];
    this.nextPlayTime = this.audioContext ? this.audioContext.currentTime : 0;
    if (this.currentSources) {
      this.currentSources.forEach(source => {
        try { source.stop(); } catch (e) {}
      });
    }
    this.currentSources = [];
    this.isPlaying = false;
  }

  clearDrainTimer() {
    if (this.drainTimer) {
      clearTimeout(this.drainTimer);
      this.drainTimer = null;
    }
  }

  clearAudioStallTimer() {
    if (this.audioStallTimer) {
      clearTimeout(this.audioStallTimer);
      this.audioStallTimer = null;
    }
  }

  clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  scheduleAudioStallCheck() {
    if (!this.assistantTurnOpen || this.receivedTurnComplete || this.audioStallTimer) {
      return;
    }

    this.audioStallTimer = setTimeout(() => {
      this.audioStallTimer = null;
      if (!this.assistantTurnOpen || this.receivedTurnComplete || this.isPlaying || this.playQueue.length > 0) {
        return;
      }

      this.recoverFromAudioStall({
        type: "audio_stalled",
        message: "Audio stopped unexpectedly; listening again."
      });
    }, this.audioStallGraceMs);
  }

  recoverFromAudioStall(msg) {
    this.clearAudioStallTimer();
    this.clearDrainTimer();
    this.assistantTurnOpen = false;
    this.receivedTurnComplete = false;
    this.nextPlayTime = this.audioContext?.currentTime || 0;
    this.playQueue = [];
    if (this.currentSources) {
      this.currentSources.forEach(source => {
        try { source.stop(); } catch (e) {}
      });
    }
    this.currentSources = [];
    this.isPlaying = false;
    if (this.onMessage) this.onMessage(msg);
    if (this.onAudioEnded) this.onAudioEnded();
  }

  finishAssistantTurnIfDrained() {
    if (!this.receivedTurnComplete || this.isPlaying || this.playQueue.length > 0) {
      return;
    }

    this.clearDrainTimer();
    this.drainTimer = setTimeout(() => {
      if (!this.receivedTurnComplete || this.isPlaying || this.playQueue.length > 0) {
        return;
      }

      this.assistantTurnOpen = false;
      this.receivedTurnComplete = false;
      this.nextPlayTime = this.audioContext?.currentTime || 0;
      this.clearAudioStallTimer();
      if (this.onMessage) this.onMessage({ type: "turn_complete" });
      if (this.onAudioEnded) this.onAudioEnded();
    }, this.drainGraceMs);
  }

  stop() {
    this.manualStop = true;
    this.clearReconnectTimer();
    this.clearPlaybackQueue();
    this.assistantTurnOpen = false;
    this.receivedTurnComplete = false;
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this.micStream) {
      this.micStream.getTracks().forEach(t => t.stop());
      this.micStream = null;
    }
    if (this.audioContext) this.audioContext.close();
    if (this.recordContext) this.recordContext.close();
    if (this.ws) {
        this.ws.close();
        this.ws = null;
    }
  }
}
