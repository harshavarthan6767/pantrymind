class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.silenceFrames = 0;
    this.SILENCE_THRESHOLD = 0.008;
    this.MAX_SILENCE_FRAMES = 1000; // Allow 1000 frames (~8 seconds at 16kHz) so Gemini VAD can detect end-of-speech
  }

  calculateRMS(channelData) {
    let sum = 0;
    for (let i = 0; i < channelData.length; i++) {
      sum += channelData[i] * channelData[i];
    }
    return Math.sqrt(sum / channelData.length);
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) {
      return true;
    }

    const channelData = input[0];
    const rms = this.calculateRMS(channelData);

    if (rms < this.SILENCE_THRESHOLD) {
      this.silenceFrames++;
      if (this.silenceFrames > this.MAX_SILENCE_FRAMES) {
        // Drop audio chunk, gate closed
        return true;
      }
    } else {
      this.silenceFrames = 0; // Reset tail on any loud frame
    }

    // Convert to PCM16
    const pcm16 = new Int16Array(channelData.length);
    for (let i = 0; i < channelData.length; i++) {
      const s = Math.max(-1, Math.min(1, channelData[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }

    this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    return true;
  }
}

registerProcessor("pcm-processor", PCMProcessor);
