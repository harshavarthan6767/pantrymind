import { app, BrowserWindow, ipcMain } from 'electron';
import { spawn } from 'child_process';
import http from 'http';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow;
let pythonProcess = null;

const isDev = process.env.NODE_ENV === 'development';

/**
 * Wait for a TCP port to become available.
 * Polls every 500ms until the port responds or timeout is reached.
 */
function waitForPort(port, timeout = 45000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    const check = () => {
      const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
        if (res.statusCode < 500) {
          resolve();
        } else {
          retry();
        }
        res.resume();
      });
      req.on('error', retry);
      req.setTimeout(800, () => { req.destroy(); retry(); });
    };

    const retry = () => {
      if (Date.now() - start > timeout) {
        reject(new Error(`Backend did not start within ${timeout}ms`));
      } else {
        setTimeout(check, 500);
      }
    };

    check();
  });
}

function startPythonBackend() {
  const rootDir = path.join(__dirname, '..', '..');
  const pythonExecutable = path.join(rootDir, '.venv', 'Scripts', 'python.exe');

  console.log('[Electron] Starting Python backend at:', pythonExecutable);

  pythonProcess = spawn(
    pythonExecutable,
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'],
    {
      cwd: rootDir,
      env: { ...process.env, APP_ENV: isDev ? 'development' : 'production' },
    }
  );

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python Backend]: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    // Uvicorn writes startup logs to stderr â€” only log actual errors
    const msg = data.toString();
    if (msg.includes('ERROR') || msg.includes('Exception')) {
      console.error(`[Python Backend Error]: ${msg}`);
    } else {
      console.log(`[Python Backend]: ${msg}`);
    }
  });

  pythonProcess.on('close', (code) => {
    console.log(`[Python Backend] exited with code ${code}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: 'PantryMind',
    frame: false,
    titleBarStyle: 'hidden',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    autoHideMenuBar: true,
    backgroundColor: '#0c0c10',
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    // Only open DevTools if explicitly requested
    // mainWindow.webContents.openDevTools();
  } else {
    const indexPath = path.join(__dirname, '..', 'dist', 'index.html');
    mainWindow.loadFile(indexPath);
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  ipcMain.on('window-minimize', () => {
    if (mainWindow) mainWindow.minimize();
  });

  ipcMain.on('window-maximize', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
      } else {
        mainWindow.maximize();
      }
    }
  });

  ipcMain.on('window-close', () => {
    if (mainWindow) mainWindow.close();
  });
}

app.whenReady().then(async () => {
  startPythonBackend();

  // Show a loading splash while backend starts up
  const splash = new BrowserWindow({
    width: 360,
    height: 200,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    backgroundColor: '#00000000',
    webPreferences: { nodeIntegration: false },
  });

  splash.loadURL(`data:text/html,
    <html>
      <body style="margin:0;background:linear-gradient(135deg,#1a2a1e,#0c0c10);display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;font-family:system-ui;color:#e8e8f0;border-radius:16px;">
        <div style="font-size:40px;margin-bottom:16px;">ðŸŒ¿</div>
        <div style="font-size:20px;font-weight:500;letter-spacing:0.02em;">PantryMind</div>
        <div style="margin-top:16px;font-size:12px;color:#6b8f71;letter-spacing:0.05em;">Starting backend...</div>
        <div style="margin-top:20px;width:120px;height:2px;background:rgba(255,255,255,0.1);border-radius:1px;overflow:hidden;">
          <div style="width:40%;height:100%;background:#6b8f71;border-radius:1px;animation:slide 1.2s ease-in-out infinite alternate;" id="bar"></div>
        </div>
        <style>@keyframes slide{from{margin-left:0}to{margin-left:60%}}</style>
      </body>
    </html>
  `);

  try {
    console.log('[Electron] Waiting for Python backend on port 8000...');
    await waitForPort(8000, 45000);
    console.log('[Electron] Backend ready! Loading app...');
  } catch (err) {
    console.error('[Electron] Backend startup timeout:', err.message);
    // Open app anyway â€” api.js retry logic will handle it
  }

  // Close splash, open main window
  createWindow();
  splash.close();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  if (pythonProcess) {
    console.log('[Electron] Killing Python backend...');
    spawn('taskkill', ['/pid', pythonProcess.pid, '/f', '/t']);
  }
});
import React, { useState, useRef, useEffect } from 'react';
import { Mic, X, Square } from 'lucide-react';
import { LiveAudioStreamer } from '../utils/liveAudio';
import './GlobalVoiceAgent.css';

export default function GlobalVoiceAgent({ isOpen, onClose }) {
  const [isActive, setIsActive] = useState(false);
  const [status, setStatus] = useState("Ready");
  const [userTranscript, setUserTranscript] = useState("");
  const [assistantTranscript, setAssistantTranscript] = useState("");
  const liveAudioRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    if (!isOpen && isActive) {
      stopSession();
    }
  }, [isOpen]);

  const startSession = async () => {
    try {
      setUserTranscript("");
      
      // Start browser speech recognition for transcript display
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;
        
        recognitionRef.current.onresult = (event) => {
          let transcript = "";
          let isFinal = false;
          
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            transcript += event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              isFinal = true;
            }
          }
          setUserTranscript(transcript);
          
          if (isFinal && liveAudioRef.current?.ws?.readyState === WebSocket.OPEN) {
             liveAudioRef.current.ws.send(JSON.stringify({
               type: "user_speech_final",
               transcript
             }));
             setStatus("Thinking...");
          }
        };
        recognitionRef.current.start();
      }

      setStatus("Connecting...");
      liveAudioRef.current = new LiveAudioStreamer(
        '/api/voice/live',
        (msg) => {
          if (msg.type === "turn_complete") {
             setStatus("Listening...");
          } else if (msg.type === "status") {
             setStatus(msg.message);
          } else if (msg.type === "partial_text") {
             setAssistantTranscript(prev => prev + msg.text);
          }
        },
        () => {
          setStatus("Speaking...");
          setAssistantTranscript("");
        }
      );
      await liveAudioRef.current.start();
      setIsActive(true);
      setStatus("Listening...");
    } catch (err) {
      console.error("Global Voice error:", err);
      setStatus("Error: Check permissions or server");
    }
  };

  const stopSession = () => {
    if (liveAudioRef.current) {
      liveAudioRef.current.stop();
    }
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsActive(false);
    setStatus("Ready");
  };

  if (!isOpen) return null;

  return (
    <div className="global-voice-overlay">
      <div className="global-voice-container">
        <button className="close-btn" onClick={onClose}><X size={24} /></button>
        <div className="voice-visualizer">
          <div className={`orb ${isActive ? 'active' : ''} ${status === 'Speaking...' ? 'speaking' : ''}`}></div>
          <div className={`orb-ripple ${isActive ? 'active' : ''}`}></div>
        </div>
        
        <h3 className="voice-title">PantryMind Assistant</h3>
        <p className="voice-status">{status}</p>
        
        <div className="voice-controls">
          <button 
            className={`voice-action-btn ${isActive ? 'active' : ''}`}
            onClick={isActive ? stopSession : startSession}
          >
            {isActive ? <Square size={28} /> : <Mic size={28} />}
          </button>
        </div>
        
        {userTranscript && (
          <div className="transcript-box">
            <p className="transcript-label">YOU SAID:</p>
            <p className="transcript-text">{userTranscript}</p>
          </div>
        )}

        {assistantTranscript && (
          <div className="transcript-box assistant-box">
            <p className="transcript-label">ASSISTANT:</p>
            <p className="transcript-text">{assistantTranscript}</p>
          </div>
        )}
        
        <p className="voice-hint">Ask about your pantry, finances, or meal plans</p>
      </div>
    </div>
  );
}
export class LiveAudioStreamer {
  constructor(endpointPath, onMessage, onAudioStarted) {
    this.ws = null;
    this.audioContext = null;
    this.recordContext = null;
    this.micStream = null;
    this.workletNode = null;
    
    // Playback state
    this.playQueue = [];
    this.currentSources = [];
    this.isPlaying = false;
    this.nextPlayTime = 0;
    
    this.onMessage = onMessage; // callback for transcript/tool updates if we send them
    this.onAudioStarted = onAudioStarted; // callback when AI starts talking
    this.endpointPath = endpointPath || '/api/kitchen/live';
  }

  async start() {
    // 1. Connect WebSocket
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.hostname}:8000${this.endpointPath}`;
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onmessage = async (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "audio") {
        if (this.onAudioStarted) this.onAudioStarted();
        this.enqueueAudio(msg.data, msg.mime_type);
      } else if (msg.type === "turn_complete") {
        if (this.onMessage) this.onMessage({ type: "turn_complete" });
      } else if (msg.type === "text" || msg.type === "status" || msg.type === "partial_text") {
        if (this.onMessage) this.onMessage(msg);
      }
    };

    // Wait for WS to open
    await new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
    });

    // 2. Start Playback Context (Let browser decide sample rate)
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    await this.audioContext.resume();

    // 3. Start Recording Context (Fixed 16kHz for Gemini)
    this.recordContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    await this.recordContext.resume();

    this.micStream = await navigator.mediaDevices.getUserMedia({ audio: {
      channelCount: 1,
      sampleRate: 16000,
      echoCancellation: true,
      noiseSuppression: true
    }});

    const source = this.recordContext.createMediaStreamSource(this.micStream);
    
    // Load AudioWorklet
    await this.recordContext.audioWorklet.addModule("/audio/pcmProcessor.js");
    this.workletNode = new AudioWorkletNode(this.recordContext, "pcm-processor");
    
    this.workletNode.port.onmessage = (event) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
      
      const buffer = event.data;
      if (buffer instanceof ArrayBuffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        for (let i = 0; i < bytes.byteLength; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        const base64Str = btoa(binary);
        
        // Interrupt assistant if they are speaking and we send new audio
        if (this.isPlaying) {
          this.clearPlaybackQueue();
          this.ws.send(JSON.stringify({ type: "interrupt" }));
        }

        console.log("[VOICE] Sending mic audio", {
          wsState: this.ws?.readyState,
          bytes: bytes.byteLength
        });

        this.ws.send(JSON.stringify({
          type: "audio",
          data: base64Str,
          mime_type: "audio/pcm;rate=16000"
        }));
      }
    };

    source.connect(this.workletNode);
    // Worklets need to be connected to destination in some browsers to fire 'process'
    const silentGain = this.recordContext.createGain();
    silentGain.gain.value = 0;
    this.workletNode.connect(silentGain);
    silentGain.connect(this.recordContext.destination);
  }

  enqueueAudio(base64Data, mimeType) {
    const binary = atob(base64Data);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    const pcm16 = new Int16Array(bytes.buffer);
    
    // Convert Int16 to Float32
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) {
      float32[i] = pcm16[i] / 0x8000;
    }
    
    // Parse sample rate from mime type or default to 24000
    let sampleRate = 24000;
    const match = mimeType?.match(/rate=(\d+)/);
    if (match) {
      sampleRate = Number(match[1]);
    }
    
    const audioBuffer = this.audioContext.createBuffer(1, float32.length, sampleRate);
    audioBuffer.getChannelData(0).set(float32);
    
    this.playQueue.push(audioBuffer);
    this.schedulePlayback();
  }

  schedulePlayback() {
    if (this.isPlaying && this.audioContext.currentTime < this.nextPlayTime) {
      return; // Already scheduled
    }
    
    if (this.playQueue.length === 0) {
      this.isPlaying = false;
      return;
    }
    
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

  clearPlaybackQueue() {
    this.playQueue = [];
    this.nextPlayTime = this.audioContext ? this.audioContext.currentTime : 0;
    
    if (this.currentSources) {
      this.currentSources.forEach(source => {
        try {
          source.stop();
        } catch (e) {}
      });
    }
    this.currentSources = [];
    this.isPlaying = false;
  }

  stop() {
    this.clearPlaybackQueue();
    
    if (this.workletNode) {
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    if (this.micStream) {
      this.micStream.getTracks().forEach(t => t.stop());
      this.micStream = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    if (this.recordContext) {
      this.recordContext.close();
      this.recordContext = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.playQueue = [];
    this.isPlaying = false;
  }
}
import os
import json
import logging
import asyncio
import base64
import traceback
from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from google.genai import types as genai_types
from google import genai
from agents.root_agent import root_agent

logger = logging.getLogger("pantrymind.global_voice")

GLOBAL_VOICE_PROMPT = """\
You are PantryMind voice assistant.
For this test, do not call any tools.
When the user speaks, respond with: I heard you clearly.
"""

DELEGATE_TOOL = genai_types.FunctionDeclaration(
    name="delegate_to_pantrymind",
    description="Delegates a query to the PantryMind Root Agent which has access to Inventory, Finance, Dietary, and Analytics agents. Use this whenever you need to fetch user data or perform an action.",
    parameters=genai_types.Schema(
        type=genai_types.Type.OBJECT,
        properties={
            "query": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="The user's query or instruction to pass to the agent system.",
            )
        },
        required=["query"],
    ),
)


class GlobalVoiceService:
    def __init__(self, gemini_client=None):
        if gemini_client:
            self.gemini = gemini_client
        else:
            use_vertex = os.getenv("GEMINI_BACKEND", "").lower() == "vertex"
            if use_vertex:
                self.gemini = genai.Client(
                    vertexai=True,
                    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                    location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
                )
            else:
                self.gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    async def handle_live_session(
        self, websocket: WebSocket, session_id: str, user_id: str
    ):
        logger.info(f"Starting Global Live API session {session_id} for user {user_id}")

        config = genai_types.LiveConnectConfig(
            system_instruction=genai_types.Content(
                parts=[genai_types.Part.from_text(text=GLOBAL_VOICE_PROMPT)]
            ),
            tools=[{"function_declarations": [DELEGATE_TOOL]}],
            response_modalities=["AUDIO"],
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name="Puck"
                    )
                )
            )
        )

        GEMINI_BACKEND = os.getenv("GEMINI_BACKEND", "ai_studio").lower().strip()

        ai_studio_default = "gemini-2.5-flash-native-audio-preview-12-2025"
        model_name = "gemini-3.1-flash-live-preview"
        logger.info(f"Forcing model_name to: {model_name}")

        blocked_models = {
            "gemini-2.0-flash-exp",
            "models/gemini-2.0-flash-exp",
            "gemini-2.0-flash",
            "models/gemini-2.0-flash",
            "gemini-2.5-flash-live-preview",
            "gemini-2.0-flash-live-001",
            "models/gemini-2.0-flash-live-001"
        }

        if model_name in blocked_models:
            model_name = vertex_default if GEMINI_BACKEND == "vertex" else ai_studio_default

        # Honor VOICE_DISABLE_TOOLS flag
        tools_disabled = os.getenv("VOICE_DISABLE_TOOLS", "false").lower() == "true"
        if tools_disabled:
            config.tools = []

        logger.info(f"Using Gemini backend: {GEMINI_BACKEND}")
        logger.info(f"Using Gemini Live model: {model_name}")
        logger.info(f"Tools disabled: {tools_disabled}")

        try:
            async with self.gemini.aio.live.connect(
                model=model_name, config=config
            ) as session:
                print(">>> Connected to Gemini Global Live API")
                logger.info("Connected to Gemini Global Live API")

                async def receive_from_websocket():
                    try:
                        while True:
                            raw = await websocket.receive_text()
                            logger.info("Client WS message received: %s chars", len(raw))
                            try:
                                payload = json.loads(raw)
                            except json.JSONDecodeError:
                                payload = {
                                    "type": "audio",
                                    "data": raw,
                                    "mime_type": "audio/pcm;rate=16000"
                                }

                            if payload.get("type") == "audio":
                                pcm_data = base64.b64decode(payload["data"])
                                mime_type = payload.get("mime_type", "audio/pcm;rate=16000")
                                await session.send_realtime_input(
                                    media=genai_types.Blob(
                                        data=pcm_data, mime_type=mime_type
                                    )
                                )
                            elif payload.get("type") == "user_speech_final":
                                logger.info(f"USER SPEECH FINAL: {payload.get('transcript')}")
                                await websocket.send_json({
                                    "type": "status",
                                    "status": "thinking",
                                    "message": "Thinking..."
                                })
                            elif payload.get("type") == "interrupt":
                                logger.info("User interrupted assistant")
                            elif payload.get("type") == "init":
                                logger.info(f"Client init: {payload}")
                    except WebSocketDisconnect:
                        logger.info("Frontend disconnected")
                    except Exception as e:
                        logger.error(f"Receive loop error: {e}")

                async def receive_from_gemini():
                    try:
                        logger.info("Connected â€” waiting for setup_complete or messages...")
                        async for msg in session.receive():
                            logger.info("Gemini message received: %s", type(msg).__name__)

                            setup_complete = getattr(msg, "setup_complete", None)
                            if setup_complete:
                                logger.info("Gemini setup_complete received")
                                await websocket.send_json({
                                    "type": "status",
                                    "status": "listening",
                                    "message": "Listening..."
                                })
                                continue

                            tool_call = getattr(msg, "tool_call", None)
                            if tool_call:
                                logger.info("Gemini tool call received: %s", tool_call)
                                for function_call in tool_call.function_calls:
                                    logger.info(f"Global Live API Tool Call: {function_call.name}")
                                    try:
                                        result_str = "Error: Tool not found."
                                        if function_call.name == "delegate_to_pantrymind":
                                            query = getattr(function_call.args, "fields", {}).get("query", {}).get("string_value", "")
                                            # Also support regular dict unpacking depending on how args is structured
                                            if not query and hasattr(function_call.args, "get"):
                                                query = function_call.args.get("query", "")
                                                
                                            logger.info(f"Delegating query: {query}")
                                            
                                            await websocket.send_json({
                                                "type": "status",
                                                "status": "thinking",
                                                "message": "Checking PantryMind..."
                                            })

                                            try:
                                                response = await asyncio.wait_for(
                                                    asyncio.to_thread(root_agent.run, query),
                                                    timeout=20
                                                )
                                                result_str = getattr(response, "text", str(response))
                                                
                                                await websocket.send_json({
                                                    "type": "status",
                                                    "status": "speaking",
                                                    "message": "Preparing your answer..."
                                                })
                                            except asyncio.TimeoutError:
                                                result_str = "The PantryMind agents took too long to respond. Please try again with a smaller request."
                                                logger.warning("root_agent timeout")
                                            except Exception as ag_err:
                                                logger.error(f"Agent error: {ag_err}", exc_info=True)
                                                result_str = f"Agent encountered an error: {ag_err}"

                                        function_response = genai_types.LiveClientContent(
                                            tool_response=genai_types.LiveClientToolResponse(
                                                function_responses=[
                                                    genai_types.FunctionResponse(
                                                        id=function_call.id,
                                                        name=function_call.name,
                                                        response={"result": result_str},
                                                    )
                                                ]
                                            )
                                        )
                                        await session.send(input=function_response)
                                    except Exception as e:
                                        logger.error(f"Tool execution failed in Live API: {e}", exc_info=True)
                                        
                            server_content = getattr(msg, "server_content", None)
                            if not server_content:
                                logger.info("Gemini message without server_content: %s", msg)
                                continue

                            model_turn = getattr(server_content, "model_turn", None)
                            if model_turn and getattr(model_turn, "parts", None):
                                for part in model_turn.parts:
                                    inline_data = getattr(part, "inline_data", None)
                                    text = getattr(part, "text", None)

                                    if text:
                                        logger.info("Gemini text part: %s", text[:300])
                                        await websocket.send_json({
                                            "type": "partial_text",
                                            "text": text
                                        })

                                    if inline_data:
                                        logger.info(
                                            "Gemini audio chunk received: %s bytes %s",
                                            len(inline_data.data),
                                            getattr(inline_data, "mime_type", "audio/pcm;rate=24000")
                                        )
                                        b64_audio = base64.b64encode(inline_data.data).decode("utf-8")
                                        await websocket.send_json({
                                            "type": "audio",
                                            "data": b64_audio,
                                            "mime_type": getattr(inline_data, "mime_type", "audio/pcm;rate=24000")
                                        })

                            if getattr(server_content, "turn_complete", False):
                                logger.info("Gemini turn complete")
                                await websocket.send_json({"type": "turn_complete"})
                                await websocket.send_json({
                                    "type": "status", 
                                    "status": "listening", 
                                    "message": "Listening..."
                                })

                    except ConnectionClosedOK as e:
                        logger.warning("Gemini Live closed normally: code=%s reason=%s", e.code, e.reason)
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Gemini Live closed normally before response. code={e.code}, reason={e.reason}"
                        })
                    except ConnectionClosedError as e:
                        logger.error("Gemini Live closed with error: code=%s reason=%s", e.code, e.reason)
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Gemini Live connection closed. code={e.code}, reason={e.reason}"
                        })
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        if "1000 None" in str(e):
                            logger.warning("Gemini Live closed cleanly (APIError 1000).")
                        else:
                            logger.exception("Gemini receive loop error")
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Gemini receive loop error: {e}"
                            })

            gemini_task = asyncio.create_task(receive_from_gemini())
            ws_task = asyncio.create_task(receive_from_websocket())

            done, pending = await asyncio.wait(
                [gemini_task, ws_task], return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()
                
            await asyncio.gather(*pending, return_exceptions=True)
            logger.info("Global Voice Session cleaned up completely")
        except Exception as e:
            print(f">>> GLOBAL VOICE FATAL ERROR: {type(e).__name__} - {e}")
            logger.error(f"Global Voice connection failed: {e}")
            import traceback

            traceback.print_exc()
"""
PantryMind â€” Personal AI Life Management Agent
FastAPI application entry point.

Architecture:
  User â†’ FastAPI â†’ Root Orchestrator Agent (Google ADK)
    â†’ Ingestion Agent (Receipt OCR)
    â†’ Inventory Agent (MongoDB CRUD via MCP)
    â†’ Financial Agent (Tax + Budgeting)
    â†’ Dietary Agent (Chef Chatbot + PuLP)
    â†’ Expiry Agent (Food Spoilage Prediction)
    â†’ Analytics Agent (Warranty, Behavior, Carbon, Nutrition, Restock)
"""

import os
import io
import re
import json
import base64
import logging
import asyncio
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from services.llm_client import call_gemini_with_retry
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel
from bson import ObjectId
from google import genai
from google.genai import types as genai_types
from PIL import Image



load_dotenv(override=True)

from adk.runner import init_runner
from routers.agent import router as agent_router
from routers.proactive import router as proactive_router
from routers.approvals import router as approvals_router
from routers.traces import router as traces_router

from services.db_service import MongoDBService, get_db_service
from services.chat_service import ChatService
from services.kitchen_chat_service import KitchenChatService
from services.voice_service import GlobalVoiceService
from services.auth import get_current_user
from schemas.requests import ChatRequest, InventoryItemRequest
from middleware.error_handler import global_exception_handler, validation_exception_handler
from services.expiry_calculator import calculate_expiry_dates, get_item_status
from services.enrichment_service import enrich_packed_items_background
from services.smart_expiry_agent import estimate_expiry_with_ai
from services.image_service import get_product_image_url
from services.medical_agent import research_condition, check_inventory_safety, get_dietary_restrictions
from services.finance_chat_service import FinanceChatService

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("pantrymind")

# ---------------------------------------------------------------------------
# Global Services
# ---------------------------------------------------------------------------
_db_service = None
_gemini_client = None
chat_service = None
kitchen_chat_service = None
global_voice_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to MongoDB Atlas + pre-warm PaddleOCR. Shutdown: close connection."""
    global _db_service, chat_service, kitchen_chat_service, finance_chat_service, global_voice_service
    _db_service = get_db_service()
    await _db_service.connect()
    
    kitchen_model = os.getenv("GEMINI_MODEL_KITCHEN", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    kitchen_chat_service = KitchenChatService(_db_service, _gemini_client, model_name=kitchen_model)
    # Finance Agent â€” uses Flash Lite for cost savings on structured queries
    finance_model = "gemini-2.5-flash-lite"
    finance_chat_service = FinanceChatService(_db_service, _gemini_client, model_name=finance_model)
    chat_service = ChatService(_db_service, _gemini_client)
    global_voice_service = GlobalVoiceService(_gemini_client)
    
    logger.info("MongoDB Atlas connected.")
    
    # NEW: Initialize ADK runner
    await init_runner()
    
    daemon_task = asyncio.create_task(image_generation_daemon())
    
    yield
    daemon_task.cancel()
    await _db_service.close()
    logger.info("MongoDB Atlas disconnected.")


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PantryMind",
    description="Personal AI Life Management Agent â€” Receipt scanning, inventory, "
    "meal planning, financial tracking, and smart analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
_cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
_cors_regex = r"http://localhost(:\d+)?" if not _cors_origins else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# NEW: Unified ADK agent router
app.include_router(agent_router)

# NEW: Proactive scanners router
app.include_router(proactive_router)

# NEW: Approvals router for Governance layer
app.include_router(approvals_router)

# NEW: Traces router for evidence capture
app.include_router(traces_router)

# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check():
    """Health check â€” verifies MongoDB connectivity."""
    try:
        await _db_service.ping()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": str(e)},
        )


# ---------------------------------------------------------------------------
# Gemini VLM Receipt Extraction Engine
# ---------------------------------------------------------------------------

# Configure the Gemini client (new google-genai SDK with Vertex AI & Studio support)
_gemini_backend = os.getenv("GEMINI_BACKEND", "studio").lower()

if _gemini_backend == "vertex":
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    _gemini_client = genai.Client(
        vertexai=True,
        project=project_id,
        location=location
    )
    logger.info(f"Gemini Vertex AI client initialized (Project: {project_id}, Location: {location}).")
else:
    _gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if _gemini_api_key:
        _gemini_client = genai.Client(api_key=_gemini_api_key)
        logger.info("Gemini AI Studio client initialized.")
    else:
        _gemini_client = None
        logger.warning("Neither GEMINI_BACKEND=vertex nor GEMINI_API_KEY is configured.")

# Strict JSON schema for constrained decoding (OpenAPI-subset)
# (Schema dict removed during cleanup)
RECEIPT_EXTRACTION_PROMPT = """
You are an expert grocery receipt analyst and product categorizer.

Analyze this receipt image and extract every line item. For EACH item, classify it using the taxonomy below.

## CATEGORY TAXONOMY (use EXACTLY these values)

PRIMARY CATEGORIES:
- PRODUCE          â†’ Fresh fruits and vegetables
- MEAT_SEAFOOD     â†’ All raw/fresh meat, poultry, fish, shellfish  
- DAIRY_EGGS       â†’ Milk, cheese, yogurt, butter, cream, eggs
- FROZEN           â†’ Frozen meals, frozen meat, ice cream, frozen veg
- BAKERY           â†’ Bread, buns, cakes, pastries, cookies (fresh/unpackaged)
- BEVERAGES        â†’ Juice, soda, water, tea, coffee, alcohol, energy drinks
- PANTRY_DRY       â†’ Rice, pasta, flour, sugar, lentils, canned goods, oils, spices
- SNACKS           â†’ Chips, crackers, packaged cookies, candy, nuts (packaged)
- CONDIMENTS       â†’ Ketchup, sauces, dressings, pickles, spreads, jams
- HOUSEHOLD        â†’ Cleaning products, detergents, paper goods, trash bags
- PERSONAL_CARE    â†’ Soap, shampoo, toothpaste, cosmetics, hygiene products
- CLOTHING         â†’ Any apparel, footwear, accessories, fabric items
- ELECTRONICS      â†’ Gadgets, batteries, cables, light bulbs, small appliances
- MEDICATIONS      â†’ Medicines, vitamins, supplements, first aid
- BABY_PRODUCTS    â†’ Baby food, diapers, baby care items
- PET_SUPPLIES     â†’ Pet food, pet care products
- OTHER            â†’ Anything that does not fit above

SUB-CATEGORY EXAMPLES (infer the best sub-category):
- PRODUCE:        leafy_greens, root_vegetables, tomatoes_peppers, tropical_fruits, citrus_fruits, berries, mushrooms, herbs
- MEAT_SEAFOOD:   poultry, red_meat, pork, seafood_fish, seafood_shellfish, processed_deli, eggs_in_meat_section
- DAIRY_EGGS:     milk, hard_cheese, soft_cheese, yogurt, butter_cream, eggs
- FROZEN:         frozen_meat, frozen_meals, ice_cream, frozen_vegetables, frozen_seafood
- BEVERAGES:      juice_fresh, juice_packed, soda_carbonated, water, alcohol_beer, alcohol_spirits, hot_beverage

DIETARY FLAGS (assign the MOST specific that applies):
- VEG          â†’ Vegetarian, plant-based, no meat/seafood/eggs
- VEGAN        â†’ Fully plant-based, no animal products at all  
- NON_VEG      â†’ Contains meat (chicken, mutton, beef, pork, etc.)
- SEAFOOD      â†’ Fish or shellfish (some consider veg, so separate)
- DAIRY        â†’ Contains milk/cheese/yogurt (no meat)
- EGG          â†’ Contains eggs (no meat/dairy)
- MIXED        â†’ Contains multiple animal products
- NA           â†’ Non-food item (household, clothing, electronics)

## OUTPUT FORMAT

Return ONLY a valid JSON object. No markdown, no explanation, no extra text.

{
  "receipt_meta": {
    "store_name": "string or null",
    "receipt_date": "YYYY-MM-DD or null",
    "subtotal": 0.0,
    "taxes": 0.0,
    "grand_total": 0.0,
    "currency": "INR"
  },
  "items": [
    {
      "item_name": "exact name from receipt",
      "normalized_name": "clean generic name (e.g. 'chicken breast' not 'PREMIUM CHKN BRST 500G')",
      "brand": "brand name if visible, else null",
      "category": "PRIMARY_CATEGORY from taxonomy",
      "sub_category": "sub_category value",
      "dietary_flag": "dietary flag value",
      "is_perishable": true,
      "is_packed_product": true,
      "quantity": 1.0,
      "unit": "unit",
      "unit_price": 0.0,
      "total_price": 0.0,
      "gemini_confidence": 1.0
    }
  ]
}
"""


async def extract_receipt_with_gemini(raw_ocr_text: str) -> dict:
    """
    Client-Side OCR + Backend LLM pipeline:
      Stage 1 â€” Executed in browser natively via ONNX
      Stage 2 â€” Gemini text-only: Semantically structure the raw text into JSON.
    """
    if not _gemini_client:
        raise RuntimeError("Gemini client is not initialized. Set GEMINI_API_KEY.")

    if not raw_ocr_text.strip():
        raise ValueError("Provided OCR text is empty.")

    # ---------------------------------------------------------------------------
    # Stage 2: Gemini text-only â€” processes text tokens, not image tokens (~1-3s)
    # ---------------------------------------------------------------------------
    logger.info(f"Stage 2: Sending {len(raw_ocr_text)} chars of OCR text to Gemini...")
    model_name = os.getenv("GEMINI_MODEL_OCR", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

    # Embed raw OCR text directly into the prompt
    full_prompt = f"{RECEIPT_EXTRACTION_PROMPT}\n\nRAW OCR TEXT:\n{raw_ocr_text}"

    response = await call_gemini_with_retry(lambda: _gemini_client.aio.models.generate_content(
        model=model_name,
        contents=full_prompt,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        )
    ))
    return json.loads(response.text)



# ---------------------------------------------------------------------------
# Direct Image Upload Endpoint (Image â†’ Gemini Flash Vision â†’ MongoDB)
# ---------------------------------------------------------------------------
@app.post("/api/receipts/upload-image", tags=["Receipts"])
async def upload_receipt_image(
    file: UploadFile = File(...), 
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user_id: str = Depends(get_current_user)
):
    """
    Accept an image file, extract structured data via Gemini Vision,
    apply expiry rules locally, and persist to MongoDB concurrently.
    """
    if not _gemini_client:
        raise HTTPException(503, "Gemini API key is not configured on the server.")

    now = datetime.utcnow()
    image_bytes = await file.read()
    
    # validate_receipt_file Logic
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large. Maximum size is 10MB.")
    if file.content_type not in ["image/jpeg", "image/png", "image/webp", "application/pdf"]:
        raise HTTPException(415, "Unsupported media type. Only JPEG, PNG, WEBP, and PDF are allowed.")

    try:
        logger.info(f"Sending image ({len(image_bytes)} bytes) to Gemini Vision...")
        image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=file.content_type or "image/jpeg")
        model_name = os.getenv("GEMINI_MODEL_OCR", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
        
        response = await call_gemini_with_retry(lambda: _gemini_client.aio.models.generate_content(
            model=model_name,
            contents=[RECEIPT_EXTRACTION_PROMPT, image_part],
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            )
        ))
        extracted = json.loads(response.text)
        logger.info(f"Gemini extracted {len(extracted.get('items', []))} items from receipt image.")
    except Exception as e:
        logger.error(f"Gemini Vision extraction failed: {e}")
        raise HTTPException(500, f"AI extraction failed: {str(e)}")

    receipt_meta = extracted.get("receipt_meta", {})
    store_name  = receipt_meta.get("store_name", "Unknown Store")
    grand_total = float(receipt_meta.get("grand_total") or 0.0)
    subtotal    = float(receipt_meta.get("subtotal") or 0.0)
    # the new prompt puts taxes as a single float, but our DB expects dict. we'll just store the dict or adjust it
    taxes       = receipt_meta.get("taxes", 0.0)
    if isinstance(taxes, (int, float)):
        taxes = {"total_tax": taxes}
        
    items = extracted.get("items", [])

    db_tasks = []

    receipt_doc_id = str(ObjectId())
    db_tasks.append(_db_service.insert_one("receipts", {
        "_id": ObjectId(receipt_doc_id),
        "user_id": user_id,
        "store": store_name,
        "date": now.isoformat(),
        "total": grand_total,
        "subtotal": subtotal,
        "taxes": taxes,
        "item_count": len(items),
        "status": "processed",
        "engine": "gemini-vision-flash"
    }))

    if grand_total > 0:
        db_tasks.append(_db_service.insert_one("financial_ledger", {
            "user_id": user_id,
            "date": now.isoformat(),
            "amount": grand_total,
            "category": "Groceries",
            "description": f"Receipt from {store_name}",
            "type": "expense"
        }))

    inventory_items = []
    packed_item_ids = []
    packed_item_names = []
    
    for item in items:
        qty   = float(item.get("quantity") or 1)
        price = float(item.get("total_price") or 0.0)
        
        category = item.get("category", "OTHER")
        sub_category = item.get("sub_category", "default")
        is_packed_product = item.get("is_packed_product", False)
        
        expiry_data = calculate_expiry_dates(
            category=category,
            sub_category=sub_category,
            purchase_date=now,
            is_packed_product=is_packed_product
        )
        
        status = get_item_status(expiry_data["safe_expiry_date"])
        
        item_id = str(ObjectId())
        
        inventory_items.append({
            "_id": ObjectId(item_id),
            "user_id": user_id,
            "name": str(item.get("item_name", "Unknown"))[:60],
            "normalized_name": item.get("normalized_name"),
            "brand": item.get("brand"),
            "category": category,
            "sub_category": sub_category,
            "dietary_flag": item.get("dietary_flag", "NA"),
            "is_perishable": item.get("is_perishable", False),
            "is_packed_product": is_packed_product,
            "quantity": qty,
            "unit": str(item.get("unit", "unit")),
            "cost_per_unit": round(price / qty, 2) if qty > 0 else price,
            "store": store_name,
            "status": status,
            "purchase_date": now.isoformat(),
            "created_at": now.isoformat(),
            "shelf_life_days": expiry_data["shelf_life_days"],
            "safe_days": expiry_data["safe_days"],
            "safety_factor_applied": expiry_data.get("safety_factor_applied"),
            "expiry_date": expiry_data["expiry_date"].isoformat() if expiry_data["expiry_date"] else None,
            "safe_expiry_date": expiry_data["safe_expiry_date"].isoformat() if expiry_data["safe_expiry_date"] else None,
            "storage_note": expiry_data["storage_note"],
            "track_as_warranty": expiry_data["track_as_warranty"],
            "source": "receipt_scan",
            "consumed_quantity": 0,
            "is_consumed": False,
            "enrichment_status": "pending" if is_packed_product else "n/a"
        })
        
        if is_packed_product and item.get("normalized_name"):
            packed_item_ids.append(ObjectId(item_id))
            packed_item_names.append(item.get("normalized_name"))

    if inventory_items:
        db_tasks.append(_db_service.insert_many("inventory", inventory_items))

    await asyncio.gather(*db_tasks)
    
    # Launch AI tasks for each newly added inventory item
    for inv_item in inventory_items:
        _id_str = str(inv_item["_id"])
        name_str = inv_item["name"]
        cat_str = inv_item["category"]
        
        # 1. Image generation
        background_tasks.add_task(_generate_single_item_image, _id_str, name_str)
        
        # 2. Auto-categorize generic items
        generic_cats = ["Groceries", "OTHER", "Other", "Produce", "Dairy", "Grains", "Spices", "Meat", "Beverages", "Cooking"]
        if cat_str in generic_cats:
            background_tasks.add_task(_categorize_single_item, _id_str, name_str)
            
        # 3. Auto-estimate expiry if missing
        if not inv_item.get("expiry_date"):
            background_tasks.add_task(_estimate_single_item_expiry, _id_str, name_str, cat_str)
    
    if packed_item_ids:
        background_tasks.add_task(
            enrich_packed_items_background,
            _db_service.db, packed_item_ids, packed_item_names
        )

    return {
        "status": "success",
        "message": f"Gemini extracted {len(items)} items from receipt.",
        "extracted_items": [{**inv, "_id": str(inv["_id"])} for inv in inventory_items],
        "extracted_data": {
            "store": store_name,
            "subtotal": subtotal,
            "taxes": taxes,
            "grandTotal": grand_total,
            "items": len(items)
        }
    }

# Imported from schemas.requests


@app.post("/api/chat", tags=["Agent"])
async def chat(body: ChatRequest, user_id: str = Depends(get_current_user)):
    """
    Send a natural language message to the PantryMind AI.
    Gemini translates the query into MongoDB operations, executes them,
    and returns a human-readable answer.
    """
    if not _gemini_client:
        raise HTTPException(503, "Gemini API key is not configured.")

    session_id = body.session_id or f"sess_{uuid4().hex[:12]}"
    chat_model = os.getenv("GEMINI_MODEL_CHAT", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    chat_service = ChatService(_db_service, _gemini_client, model_name=chat_model, user_id=user_id)

    try:
        reply, metadata = await chat_service.process_message(
            session_id=session_id,
            user_message=body.message,
        )
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(500, f"Chat failed: {str(e)}")

    return {
        "status": "ok",
        "reply": reply,
        "session_id": session_id,
        "metadata": metadata,
    }


@app.get("/api/chat/history/{session_id}", tags=["Agent"])
async def get_chat_history(session_id: str, limit: int = 50, user_id: str = Depends(get_current_user)):
    """Retrieve conversation history for a session."""
    messages = await _db_service.find(
        "conversation_history",
        {"session_id": session_id, "user_id": user_id},
        limit=limit,
        sort=[("timestamp", 1)],
    )
    return {"session_id": session_id, "messages": messages}

# --- Kitchen Chat API ---
class KitchenChatRequest(BaseModel):
    message: str
    session_id: str
    

@app.post("/api/kitchen/chat")
async def handle_kitchen_chat(request: KitchenChatRequest, user_id: str = Depends(get_current_user)):
    if not kitchen_chat_service:
        raise HTTPException(status_code=500, detail="Kitchen Chat Service not initialized")
    try:
        reply, metadata = await kitchen_chat_service.process_message(
            session_id=request.session_id,
            user_id=user_id,
            user_message=request.message
        )
        return {"reply": reply, "metadata": metadata}
    except Exception as e:
        logger.error(f"Kitchen Chat API Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/kitchen/chat/history/{session_id}")
async def get_kitchen_chat_history(session_id: str):
    if not kitchen_chat_service:
        raise HTTPException(status_code=500, detail="Kitchen Chat Service not initialized")
    try:
        history = await kitchen_chat_service.load_history(session_id, limit=50)
        return {"history": history}
    except Exception as e:
        logger.error(f"Kitchen Chat History Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kitchen/voice")
async def handle_kitchen_voice(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    if not kitchen_chat_service:
        raise HTTPException(status_code=500, detail="Kitchen Chat Service not initialized")
    try:
        audio_bytes = await audio.read()
        mime_type = audio.content_type or "audio/webm"
        
        reply, metadata, audio_b64 = await kitchen_chat_service.process_voice_message(
            session_id=session_id,
            user_id=user_id,
            audio_bytes=audio_bytes,
            mime_type=mime_type
        )
        return {"reply": reply, "audio_base64": audio_b64, "metadata": metadata}
    except Exception as e:
        logger.error(f"Kitchen Voice API Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/api/kitchen/live")
async def kitchen_live_agent(websocket: WebSocket):
    await websocket.accept()
    if not kitchen_chat_service:
        await websocket.close(code=1011, reason="Kitchen Chat Service not initialized")
        return
    
    session_id = "default_session"
    user_id = "default_user"
    
    try:
        await kitchen_chat_service.handle_live_session(websocket, session_id, user_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"Live API WebSocket error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass

@app.websocket("/api/voice/live")
async def global_voice_live_agent(websocket: WebSocket):
    await websocket.accept()
    if not global_voice_service:
        await websocket.close(code=1011, reason="Global Voice Service not initialized")
        return
    
    session_id = "global_voice_" + str(uuid4())[:8]
    user_id = "default_user"
    
    try:
        await global_voice_service.handle_live_session(websocket, session_id, user_id)
    except WebSocketDisconnect:
        logger.info(f"Global Voice WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"Global Live API WebSocket error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass

# ---------------------------------------------------------------------------
# AI Background Helpers (Category Agent + Expiry Agent)
# ---------------------------------------------------------------------------
async def _categorize_single_item(item_id: str, item_name: str):
    """Background task: classify a single item via Gemini Flash."""
    if not _gemini_client:
        return
    try:
        prompt = f"""Classify this grocery item into one category.

Item: "{item_name}"

Categories: PRODUCE, MEAT_SEAFOOD, DAIRY_EGGS, FROZEN, BAKERY, BEVERAGES, PANTRY_DRY, SNACKS, CONDIMENTS, HOUSEHOLD, PERSONAL_CARE, OTHER

Return JSON: {{"category": "...", "sub_category": "...", "dietary_flag": "VEG|NON_VEG|SEAFOOD|DAIRY|NA", "is_perishable": true|false}}"""

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = await call_gemini_with_retry(lambda: _gemini_client.aio.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            )
        ))
        cls = json.loads(response.text)
        await _db_service.update_one(
            "inventory",
            {"_id": ObjectId(item_id)},
            {"$set": {
                "category": cls.get("category", "OTHER"),
                "sub_category": cls.get("sub_category", "default"),
                "dietary_flag": cls.get("dietary_flag", "NA"),
                "is_perishable": cls.get("is_perishable", False),
            }}
        )
        logger.info(f"Auto-categorized '{item_name}' â†’ {cls.get('category')}")
    except Exception as e:
        logger.warning(f"Auto-categorize failed for '{item_name}': {e}")


async def _estimate_single_item_expiry(item_id: str, item_name: str, category: str):
    """Background task: estimate expiry for a single item via Gemini."""
    if not _gemini_client:
        return
    try:
        is_packed = category in ["PANTRY_DRY", "SNACKS", "BEVERAGES", "CONDIMENTS", "FROZEN"]
        result = await estimate_expiry_with_ai(_gemini_client, item_name, category, is_packed)

        remaining = result.get("remaining_days")
        if remaining and remaining > 0:
            now = datetime.utcnow()
            expiry_date = now + timedelta(days=remaining)
            safe_factor = 0.75 if is_packed else 0.50
            safe_days = int(remaining * safe_factor)
            safe_expiry = now + timedelta(days=safe_days)

            status = get_item_status(safe_expiry)

            await _db_service.update_one(
                "inventory",
                {"_id": ObjectId(item_id)},
                {"$set": {
                    "expiry_date": expiry_date.isoformat(),
                    "safe_expiry_date": safe_expiry.isoformat(),
                    "shelf_life_days": result.get("total_shelf_life_days", remaining),
                    "safe_days": safe_days,
                    "status": status,
                    "storage_note": result.get("storage_tip", ""),
                    "expiry_source": "ai_estimated",
                    "expiry_confidence": result.get("confidence", 0),
                    "expiry_reasoning": result.get("reasoning", ""),
                }}
            )
            logger.info(f"AI estimated expiry for '{item_name}': {remaining} days (safe: {safe_days} days)")
    except Exception as e:
        logger.warning(f"Expiry estimation background task failed for '{item_name}': {e}")


async def _generate_single_item_image(item_id: str, item_name: str):
    """Background task: generate image for a single item via Gemini."""
    try:
        from services.image_service import assign_product_image
        await assign_product_image(_db_service, _gemini_client, item_id, item_name)
    except Exception as e:
        logger.warning(f"Image generation background task failed for '{item_name}': {e}")


image_agent_status = {
    "state": "monitoring",
    "item": None
}

async def image_generation_daemon():
    """Background loop to continuously monitor the pantry and generate images one by one."""
    logger.info("Image generation daemon started.")
    global image_agent_status
    while True:
        try:
            if not _gemini_client:
                await asyncio.sleep(15)
                continue
                
            # Find an item that lacks an image_url
            item = await _db_service.find_one(
                "inventory",
                {"$or": [{"image_url": None}, {"image_url": {"$exists": False}}]}
            )
            if item and item.get("name"):
                logger.info(f"Daemon picked up missing image for '{item['name']}'")
                image_agent_status["state"] = "generating"
                image_agent_status["item"] = item["name"]
                
                await _generate_single_item_image(str(item["_id"]), item["name"])
                
                # Wait 5 seconds between creations to avoid rate limits
                await asyncio.sleep(5)
            else:
                image_agent_status["state"] = "monitoring"
                image_agent_status["item"] = None
                # Sleep longer if nothing to do
                await asyncio.sleep(15)
        except asyncio.CancelledError:
            logger.info("Image generation daemon cancelled.")
            image_agent_status["state"] = "offline"
            image_agent_status["item"] = None
            break
        except Exception as e:
            logger.error(f"Image generation daemon error: {e}")
            image_agent_status["state"] = "error"
            image_agent_status["item"] = None
            await asyncio.sleep(15)

@app.get("/api/system/agent-status", tags=["System"])
async def get_agent_status():
    """Get the current live status of the background monitoring agent."""
    return image_agent_status



# ---------------------------------------------------------------------------
# Inventory Endpoints (REST fallback for frontend)
# ---------------------------------------------------------------------------
@app.get("/api/inventory", tags=["Inventory"])
async def get_inventory(category: str | None = None, user_id: str = Depends(get_current_user)):
    """Retrieve current inventory, optionally filtered by category."""
    query = {"quantity": {"$gt": 0}, "user_id": user_id}
    if category:
        query["category"] = category
    items = await _db_service.find("inventory", query)
    return {"items": items, "count": len(items)}


@app.post("/api/inventory", tags=["Inventory"])
async def add_inventory_item(
    item: InventoryItemRequest, 
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Add a new item to the inventory."""
    doc = item.model_dump()
    doc["created_at"] = datetime.utcnow().isoformat()
    inserted_id = await _db_service.insert_one("inventory", doc)
    doc["_id"] = inserted_id

    # Auto-categorize if generic category
    generic_cats = ["Groceries", "OTHER", "Other", "Produce", "Dairy", "Grains", "Spices", "Meat", "Beverages", "Cooking"]
    if item.category in generic_cats:
        background_tasks.add_task(_categorize_single_item, inserted_id, item.name)

    # Auto-estimate expiry if not provided
    if not item.expiry_date:
        background_tasks.add_task(_estimate_single_item_expiry, str(inserted_id), item.name, item.category)

    # Note: Image generation is now handled automatically by the background daemon

    return {"status": "created", "item": doc}


@app.put("/api/inventory/{item_id}", tags=["Inventory"])
async def update_inventory_item(
    item_id: str, 
    item: InventoryItemRequest,
    user_id: str = Depends(get_current_user)
):
    """Update an existing inventory item by its ObjectId."""
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(400, "Invalid item ID format.")

    modified = await _db_service.update_one(
        "inventory",
        {"_id": oid},
        {"$set": item.model_dump()},
    )
    if modified == 0:
        raise HTTPException(404, "Item not found.")
    return {"status": "updated", "item_id": item_id}


@app.delete("/api/inventory/{item_id}", tags=["Inventory"])
async def delete_inventory_item(item_id: str, user_id: str = Depends(get_current_user)):
    """Delete an inventory item by its ObjectId."""
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(400, "Invalid item ID format.")

    deleted = await _db_service.delete_one("inventory", {"_id": oid, "user_id": user_id})
    if deleted == 0:
        raise HTTPException(404, "Item not found.")
    return {"status": "deleted", "item_id": item_id}


class BulkDeleteRequest(BaseModel):
    item_ids: list[str]

class TransactionRequest(BaseModel):
    amount: float
    category: str
    description: str
    type: str = "expense" # income or expense


@app.post("/api/inventory/bulk-delete", tags=["Inventory"])
async def bulk_delete_inventory_items(req: BulkDeleteRequest, user_id: str = Depends(get_current_user)):
    """Delete multiple inventory items by their ObjectIds."""
    try:
        oids = [ObjectId(item_id) for item_id in req.item_ids]
    except Exception:
        raise HTTPException(400, "Invalid item ID format in list.")

    deleted = await _db_service.delete_many("inventory", {"_id": {"$in": oids}, "user_id": user_id})
    return {"status": "deleted", "deleted_count": deleted}


@app.post("/api/inventory/consume", tags=["Inventory"])
async def consume_item(
    user_id: str = Depends(get_current_user),
    item_name: str = Form(...),
    quantity: float = Form(1.0),
):
    """Mark an item as consumed â€” decrements inventory and logs to history."""
    import re
    escaped_words = [re.escape(w) for w in item_name.split()]
    regex_pattern = "".join([f"(?=.*{w})" for w in escaped_words])

    # Find the item using word-independent search
    items = await _db_service.find(
        "inventory",
        {"name": {"$regex": regex_pattern, "$options": "i"}, "user_id": user_id},
        limit=1,
    )
    if not items:
        raise HTTPException(404, f"Item '{item_name}' not found in inventory.")

    item = items[0]
    new_qty = max(0, float(item.get("quantity", 0)) - quantity)

    # Update quantity
    await _db_service.update_one(
        "inventory",
        {"_id": ObjectId(item["_id"]), "user_id": user_id},
        {"$set": {"quantity": new_qty}},
    )

    # Log to consumption history
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")
    await _db_service.insert_one("consumption_history", {
        "item_name": item.get("name", item_name),
        "user_id": user_id,
        "month_key": month_key,
        "consumed_qty": quantity,
        "date": now.isoformat(),
    })

    return {
        "status": "consumed",
        "item_name": item.get("name", item_name),
        "user_id": user_id,
        "quantity_consumed": quantity,
        "remaining": new_qty,
    }


# ---------------------------------------------------------------------------
# Dashboard Stats
# ---------------------------------------------------------------------------
@app.get("/api/dashboard/stats", tags=["Dashboard"])
async def get_dashboard_stats(user_id: str = Depends(get_current_user)):
    """Aggregate dashboard statistics from multiple collections in parallel."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {"date": {"$gte": month_start.isoformat()}, "user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]

    # Run queries concurrently
    total_items_task = _db_service.count_documents("inventory", {"user_id": user_id})
    expiring_items_task = _db_service.find("inventory", {"status": "expiring", "user_id": user_id})
    monthly_spending_task = _db_service.aggregate("financial_ledger", pipeline)
    recent_receipts_task = _db_service.find("receipts", {"user_id": user_id}, limit=3, sort=[("date", -1)])

    total_items, expiring_items, agg_result, recent_receipts = await asyncio.gather(
        total_items_task,
        expiring_items_task,
        monthly_spending_task,
        recent_receipts_task,
    )

    monthly_spending = agg_result[0]["total"] if agg_result else 0

    return {
        "total_items": total_items,
        "expiring_soon": len(expiring_items),
        "monthly_spending": monthly_spending,
        "recent_receipts": recent_receipts,
        "expiring_items": expiring_items,
    }


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------
@app.get("/api/receipts", tags=["Receipts"])
async def get_receipts(user_id: str = Depends(get_current_user)):
    """Return all receipts sorted by date descending."""
    receipts = await _db_service.find(
        "receipts", {"user_id": user_id}, sort=[("date", -1)]
    )
    return {"receipts": receipts, "count": len(receipts)}


# ---------------------------------------------------------------------------
# Finance â€” AI Chat Agent (Flash Lite)
# ---------------------------------------------------------------------------
@app.post("/api/finance/chat", tags=["Finance"])
async def finance_chat(body: ChatRequest, user_id: str = Depends(get_current_user)):
    """
    Send a natural language finance question to the PantryMind Finance Agent.
    Uses Gemini Flash Lite for cost-efficient structured financial queries.
    """
    if not finance_chat_service:
        raise HTTPException(503, "Finance chat service is not initialized.")

    session_id = body.session_id or f"fin_{uuid4().hex[:12]}"

    try:
        reply, metadata = await finance_chat_service.process_message(
            session_id=session_id,
            user_message=body.message,
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"Finance chat failed: {e}")
        raise HTTPException(500, f"Finance chat failed: {str(e)}")

    return {
        "status": "ok",
        "reply": reply,
        "session_id": session_id,
        "metadata": metadata,
    }

@app.get("/api/finance/chat/history/{session_id}", tags=["Finance"])
async def get_finance_chat_history(session_id: str, user_id: str = Depends(get_current_user)):
    """Retrieve finance chat history for a given session ID."""
    history = await _db_service.find(
        "finance_conversation_history",
        {"session_id": session_id},
        sort=[("timestamp", 1)]
    )
    return {"history": history}

# ---------------------------------------------------------------------------
# Finance â€” Transactions
# ---------------------------------------------------------------------------
@app.get("/api/finance/transactions", tags=["Finance"])
async def get_finance_transactions(user_id: str = Depends(get_current_user)):
    """Return all financial ledger entries sorted by date descending."""
    transactions = await _db_service.find(
        "financial_ledger", {"user_id": user_id}, sort=[("date", -1)]
    )
    return {"transactions": transactions, "count": len(transactions)}


# ---------------------------------------------------------------------------
# Financial Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/finance/set-salary", tags=["Finance"])
async def set_salary(
    monthly_salary: float = Form(..., description="Gross monthly salary in INR"),
    tax_regime: str = Form("new", description="'new' or 'old'"),
):
    """Set or update the user's salary and tax regime preference."""
    await _db_service.update_one(
        "user_profile",
        {},  # Single-user system
        {"$set": {
            "monthly_salary": monthly_salary,
            "tax_regime": tax_regime,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return {
        "status": "saved",
        "monthly_salary": monthly_salary,
        "tax_regime": tax_regime,
    }


@app.post("/api/finance/transaction", tags=["Finance"])
async def create_finance_transaction(req: TransactionRequest, user_id: str = Depends(get_current_user)):
    """Log a manual transaction to the financial ledger."""
    now = datetime.now(timezone.utc)
    transaction = {
        "date": now.isoformat(),
        "description": req.description,
        "amount": req.amount,
        "category": req.category,
        "type": req.type,
    }
    
    res = await _db_service.insert_one("financial_ledger", transaction)
    transaction["_id"] = res
    return transaction
@app.get("/api/finance/summary", tags=["Finance"])
async def get_financial_summary(user_id: str = Depends(get_current_user)):
    """Get financial summary: monthly spending, income, and category breakdown."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Spending by category this month
    pipeline = [
        {"$match": {"date": {"$gte": month_start.isoformat()}, "type": "expense"}},
        {"$group": {"_id": "$category", "total": {"$sum": "$amount"}}},
        {"$sort": {"total": -1}},
    ]
    by_category = await _db_service.aggregate("financial_ledger", pipeline)

    total_spending = sum(c.get("total", 0) for c in by_category)

    # User profile for salary
    profile = await _db_service.find_one("user_profile", {})
    salary = profile.get("monthly_salary", 0) if profile else 0

    return {
        "month": now.strftime("%B %Y"),
        "total_spending": total_spending,
        "monthly_salary": salary,
        "disposable_income": salary - total_spending,
        "category_breakdown": [
            {"category": c["_id"], "amount": c["total"]} for c in by_category
        ],
    }


# ---------------------------------------------------------------------------
# Analytics Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/analytics/carbon", tags=["Analytics"])
async def get_carbon_footprint(user_id: str = Depends(get_current_user)):
    """Get carbon footprint entries sorted by month."""
    entries = await _db_service.find(
        "carbon_log", {}, sort=[("month", -1)]
    )
    return {"carbon_log": entries, "count": len(entries)}


@app.get("/api/analytics/nutrition", tags=["Analytics"])
async def get_nutrition_report(user_id: str = Depends(get_current_user)):
    """Get nutrition log entries sorted by date."""
    entries = await _db_service.find(
        "nutrition_log", {}, sort=[("date", -1)], limit=30
    )
    return {"nutrition_log": entries, "count": len(entries)}


@app.get("/api/analytics/restock", tags=["Analytics"])
async def get_restock_alerts(user_id: str = Depends(get_current_user)):
    """Items likely to run out soon (low quantity or expiring)."""
    low_qty = await _db_service.find(
        "inventory",
        {
            "user_id": user_id, 
            "is_consumed": {"$ne": True},
            "quantity": {"$gt": 0}, 
            "$or": [{"status": "expiring"}, {"quantity": {"$lte": 1}}]
        },
    )
    return {"restock_items": low_qty, "count": len(low_qty)}


@app.get("/api/analytics/behavior", tags=["Analytics"])
async def get_behavior_insights(user_id: str = Depends(get_current_user)):
    """Spending patterns from financial ledger."""
    transactions = await _db_service.find(
        "financial_ledger", {"user_id": user_id}, sort=[("date", -1)], limit=50
    )
    # Category breakdown
    by_cat = {}
    for tx in transactions:
        cat = tx.get("category", "Other")
        by_cat[cat] = by_cat.get(cat, 0) + tx.get("amount", 0)
    return {
        "transactions": transactions,
        "category_breakdown": by_cat,
        "total_spent": sum(by_cat.values()),
    }


@app.get("/api/user/profile", tags=["User"])
async def get_user_profile():
    """Get the user profile."""
    profile = await _db_service.find_one("user_profile", {})
    return {"profile": profile}


@app.get("/api/analytics/warranties", tags=["Analytics"])
async def get_warranties():
    """Get all warranties from the warranties collection."""
    warranties = await _db_service.find("warranties", {})
    return {"warranties": warranties, "count": len(warranties)}


# ---------------------------------------------------------------------------
# AI Category Agent â€” Batch Re-categorization
# ---------------------------------------------------------------------------
@app.post("/api/inventory/categorize", tags=["Inventory"])
async def categorize_inventory():
    """Re-categorize inventory items that have generic categories."""
    if not _gemini_client:
        raise HTTPException(503, "Gemini client not available.")

    # Find items with generic categories
    generic_cats = ["Groceries", "OTHER", "Other", "Produce", "Dairy", "Grains", "Spices", "Meat", "Beverages", "Cooking"]
    all_items = await _db_service.find("inventory", {"category": {"$in": generic_cats}})

    if not all_items:
        return {"status": "ok", "message": "No items need categorization", "categorized": 0}

    # Build prompt with all item names
    item_names = [item.get("name", "Unknown") for item in all_items]

    prompt = f"""You are a grocery categorization expert. Classify each item below into exactly one category.

CATEGORIES (use EXACTLY these values):
PRODUCE, MEAT_SEAFOOD, DAIRY_EGGS, FROZEN, BAKERY, BEVERAGES, PANTRY_DRY, SNACKS, CONDIMENTS, HOUSEHOLD, PERSONAL_CARE, OTHER

SUB-CATEGORIES:
- PRODUCE: leafy_greens, root_vegetables, tomatoes_peppers, tropical_fruits, citrus_fruits, berries, mushrooms, herbs, onion_garlic, gourd_vegetables
- MEAT_SEAFOOD: poultry, red_meat, pork, seafood_fish, seafood_shellfish, processed_deli
- DAIRY_EGGS: milk, hard_cheese, soft_cheese, yogurt, butter_cream, eggs
- FROZEN: frozen_meat, frozen_meals, ice_cream, frozen_vegetables, frozen_seafood
- BEVERAGES: juice_fresh, juice_packed, soda_carbonated, water, alcohol_beer, hot_beverage
- PANTRY_DRY: rice_pasta, flour, legumes_pulses, canned_goods, spices_masala, oil, sugar_salt, instant_food
- SNACKS: chips_crisps, cookies_biscuits, namkeen, nuts_dried_fruits, chocolate_candy
- CONDIMENTS: ketchup_sauces, mayonnaise, spread_butter

DIETARY FLAGS: VEG, VEGAN, NON_VEG, SEAFOOD, DAIRY, EGG, MIXED, NA

IS_PERISHABLE: true if the item spoils (fruits, meat, dairy, bakery). false for dry goods, household, etc.

Items to classify:
{json.dumps(item_names)}

Return ONLY a JSON array:
[{{"name": "...", "category": "...", "sub_category": "...", "dietary_flag": "...", "is_perishable": true}}]"""

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    response = await call_gemini_with_retry(lambda: _gemini_client.aio.models.generate_content(
        model=model_name,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        )
    ))

    classifications = json.loads(response.text)

    # Build a lookup from name -> classification
    class_map = {c["name"].lower(): c for c in classifications}

    updated = 0
    for item in all_items:
        name_lower = item.get("name", "").lower()
        cls = class_map.get(name_lower)
        if not cls:
            # Try fuzzy: find the first classification whose name is contained in item name or vice versa
            for cn, cv in class_map.items():
                if cn in name_lower or name_lower in cn:
                    cls = cv
                    break

        if cls:
            update_data = {
                "category": cls.get("category", "OTHER"),
                "sub_category": cls.get("sub_category", "default"),
                "dietary_flag": cls.get("dietary_flag", "NA"),
                "is_perishable": cls.get("is_perishable", False),
            }
            await _db_service.update_one(
                "inventory",
                {"_id": ObjectId(item["_id"]), "user_id": user_id},
                {"$set": update_data}
            )
            updated += 1

    return {"status": "ok", "categorized": updated, "total_checked": len(all_items)}


# ---------------------------------------------------------------------------
# Smart Expiry Agent â€” Batch AI Expiry Estimation
# ---------------------------------------------------------------------------
@app.post("/api/inventory/estimate-expiry", tags=["Inventory"])
async def estimate_expiry_batch():
    """Estimate expiry dates for items missing them using Gemini AI."""
    if not _gemini_client:
        raise HTTPException(503, "Gemini client not available.")

    # Find items without expiry dates
    items = await _db_service.find(
        "inventory",
        {"$or": [
            {"expiry_date": None},
            {"expiry_date": {"$exists": False}},
            {"safe_expiry_date": None},
            {"safe_expiry_date": {"$exists": False}},
        ]},
        limit=50
    )

    if not items:
        return {"status": "ok", "message": "All items have expiry dates", "estimated": 0}

    estimated = 0
    for item in items:
        name = item.get("name", "Unknown")
        category = item.get("category", "OTHER")
        is_packed = category in ["PANTRY_DRY", "SNACKS", "BEVERAGES", "CONDIMENTS", "FROZEN"]

        result = await estimate_expiry_with_ai(_gemini_client, name, category, is_packed)
        remaining = result.get("remaining_days")

        if remaining and remaining > 0:
            now = datetime.utcnow()
            expiry_date = now + timedelta(days=remaining)
            safe_factor = 0.75 if is_packed else 0.50
            safe_days = int(remaining * safe_factor)
            safe_expiry = now + timedelta(days=safe_days)

            status = get_item_status(safe_expiry)

            await _db_service.update_one(
                "inventory",
                {"_id": ObjectId(item["_id"]), "user_id": user_id},
                {"$set": {
                    "expiry_date": expiry_date.isoformat(),
                    "safe_expiry_date": safe_expiry.isoformat(),
                    "shelf_life_days": result.get("total_shelf_life_days", remaining),
                    "safe_days": safe_days,
                    "status": status,
                    "storage_note": result.get("storage_tip", ""),
                    "expiry_source": "ai_estimated",
                    "expiry_confidence": result.get("confidence", 0),
                    "expiry_reasoning": result.get("reasoning", ""),
                }}
            )
            estimated += 1

    return {"status": "ok", "estimated": estimated, "total_checked": len(items)}


@app.get("/api/images/cloud/{slug}", tags=["Inventory", "Images"])
async def get_cloud_image(slug: str):
    """Serve a product image from the cloud database cache."""
    doc = await _db_service.find_one("cloud_images", {"slug": slug})
    if not doc or "image_base64" not in doc:
        raise HTTPException(status_code=404, detail="Image not found")
    
    from fastapi.responses import Response
    import base64
    image_bytes = base64.b64decode(doc["image_base64"])
    content_type = doc.get("content_type", "image/webp")
    return Response(content=image_bytes, media_type=content_type)



# ---------------------------------------------------------------------------
# Medical Conditions & Health Profile
# ---------------------------------------------------------------------------
class MedicalConditionRequest(BaseModel):
    condition_name: str
    user_id: str = "default_user"


@app.get("/api/medical/conditions", tags=["Medical"])
async def get_medical_conditions(user_id: str = "default_user"):
    """List all medical conditions for a user."""
    conditions = await _db_service.find("medical_conditions", {"user_id": user_id})
    return {"conditions": conditions, "count": len(conditions)}


@app.post("/api/medical/conditions", tags=["Medical"])
async def add_medical_condition(req: MedicalConditionRequest, background_tasks: BackgroundTasks):
    """Add a new medical condition and trigger AI research."""
    existing = await _db_service.find_one("medical_conditions", {
        "user_id": req.user_id,
        "condition_name": {"$regex": f"^{req.condition_name}$", "$options": "i"}
    })
    if existing:
        raise HTTPException(409, f"Condition '{req.condition_name}' already exists.")

    doc = {
        "user_id": req.user_id,
        "condition_name": req.condition_name,
        "researched": False,
        "foods_to_avoid": [],
        "foods_to_eat": [],
        "medicines": [],
        "treatments": [],
        "dietary_notes": "Researching...",
        "created_at": datetime.utcnow().isoformat(),
    }
    inserted_id = await _db_service.insert_one("medical_conditions", doc)
    doc["_id"] = inserted_id

    background_tasks.add_task(_research_condition_background, str(inserted_id), req.condition_name)

    return {"status": "created", "condition": doc, "message": "Gemini is researching this condition..."}


async def _research_condition_background(condition_id: str, condition_name: str):
    """Background task to research a medical condition via Gemini."""
    if not _gemini_client:
        logger.warning("Cannot research condition - no Gemini client")
        return
    try:
        result = await research_condition(_gemini_client, condition_name)
        await _db_service.update_one(
            "medical_conditions",
            {"_id": ObjectId(condition_id)},
            {"$set": result}
        )
        logger.info(f"Medical research complete for '{condition_name}'")
    except Exception as e:
        logger.error(f"Medical research background task failed: {e}")


@app.delete("/api/medical/conditions/{condition_id}", tags=["Medical"])
async def delete_medical_condition(condition_id: str):
    """Delete a medical condition."""
    try:
        oid = ObjectId(condition_id)
    except Exception:
        raise HTTPException(400, "Invalid condition ID format.")
    deleted = await _db_service.delete_one("medical_conditions", {"_id": oid})
    if deleted == 0:
        raise HTTPException(404, "Condition not found.")
    return {"status": "deleted", "condition_id": condition_id}


@app.get("/api/medical/inventory-check", tags=["Medical"])
async def run_inventory_safety_check(user_id: str = "default_user"):
    """Run 2nd-line-of-defence inventory safety scan against medical restrictions."""
    if not _gemini_client:
        raise HTTPException(503, "Gemini client not available.")
    return await check_inventory_safety(_gemini_client, _db_service, user_id)


@app.get("/api/medical/restrictions", tags=["Medical"])
async def get_restrictions(user_id: str = "default_user"):
    """Get aggregated dietary restrictions from all conditions."""
    return await get_dietary_restrictions(_db_service, user_id)


# ---------------------------------------------------------------------------
# Serve Frontend (production only â€” in dev, Vite handles this)
# ---------------------------------------------------------------------------
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", tags=["Frontend"])
    async def serve_spa(full_path: str):
        """SPA fallback â€” serve index.html for all unmatched routes."""
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("APP_PORT", 8000)),
        reload=os.getenv("APP_ENV") == "development",
    )
