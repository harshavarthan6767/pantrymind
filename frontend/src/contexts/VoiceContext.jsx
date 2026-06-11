import React, { createContext, useContext, useRef, useState } from 'react';
import { LiveAudioStreamer } from '../utils/liveAudio';

const VoiceContext = createContext(null);

export const VoiceProvider = ({ children }) => {
  const [isActive, setIsActive] = useState(false);
  const [status, setStatus] = useState("Ready");
  const [userTranscript, setUserTranscript] = useState("");
  const [assistantTranscript, setAssistantTranscript] = useState("");
  const [conversation, setConversation] = useState([]);
  const [activeAgent, setActiveAgent] = useState("");
  const [activityLog, setActivityLog] = useState([]);
  
  const liveAudioRef = useRef(null);
  const recognitionRef = useRef(null);
  const speechTurnBufferRef = useRef("");
  const speechFinalTimerRef = useRef(null);
  const lastSentFinalSpeechRef = useRef({ text: "", at: 0 });
  const serverTranscriptRef = useRef("");
  const lastActivityRef = useRef({ text: "", at: 0 });

  const normalizeSpeech = (text) => String(text || "").replace(/\s+/g, " ").trim();

  const appendActivity = (text, tone = "info") => {
    if (!text) return;
    const now = Date.now();
    if (lastActivityRef.current.text === text && now - lastActivityRef.current.at < 1500) {
      return;
    }
    lastActivityRef.current = { text, at: now };
    setActivityLog(prev => [
      ...prev,
      {
        id: `${now}-${Math.random().toString(16).slice(2)}`,
        text,
        tone,
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      }
    ].slice(-10));
  };

  const resetActivity = (text) => {
    lastActivityRef.current = { text, at: Date.now() };
    setActivityLog([{
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      text,
      tone: "info",
      time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    }]);
  };

  const describeAgentActivity = (msg) => {
    const name = String(msg.tool || msg.agent || msg.data || "").replaceAll("_", " ");
    if (msg.message) return msg.message;
    if (msg.activity_type === "tool_call" && name) return `Calling ${name}`;
    if (msg.activity_type === "agent" && name) return `Routing to ${name}`;
    if (name) return `Working with ${name}`;
    return "Checking PantryMind";
  };

  const sendUserSpeechFinal = (transcript) => {
    const cleanTranscript = normalizeSpeech(transcript);
    if (!cleanTranscript || liveAudioRef.current?.ws?.readyState !== WebSocket.OPEN) {
      return;
    }

    const now = Date.now();
    const lastSent = lastSentFinalSpeechRef.current;
    if (lastSent.text === cleanTranscript && now - lastSent.at < 2500) {
      return;
    }

    lastSentFinalSpeechRef.current = { text: cleanTranscript, at: now };
    liveAudioRef.current.ws.send(JSON.stringify({
      type: "user_speech_final",
      transcript: cleanTranscript
    }));
    setStatus("Thinking...");
    appendActivity(`Heard: ${cleanTranscript}`, "user");
    appendActivity("Thinking through the request", "info");
  };

  const startSession = async () => {
    try {
      setUserTranscript("");
      setAssistantTranscript("");
      speechTurnBufferRef.current = "";
      serverTranscriptRef.current = "";
      lastSentFinalSpeechRef.current = { text: "", at: 0 };
      resetActivity("Opening live voice channel");

      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;
        
        recognitionRef.current.onresult = (event) => {
          let finalTranscript = "";
          let interimTranscript = "";
          
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
            } else {
              interimTranscript += event.results[i][0].transcript;
            }
          }

          const cleanFinal = normalizeSpeech(finalTranscript);
          if (cleanFinal) {
            speechTurnBufferRef.current = normalizeSpeech(`${speechTurnBufferRef.current} ${cleanFinal}`);
            setUserTranscript(speechTurnBufferRef.current);

            if (speechFinalTimerRef.current) {
              clearTimeout(speechFinalTimerRef.current);
            }
            speechFinalTimerRef.current = setTimeout(() => {
              const transcriptToSend = speechTurnBufferRef.current;
              speechTurnBufferRef.current = "";
              sendUserSpeechFinal(transcriptToSend);
            }, 450);
          } else {
            const cleanInterim = normalizeSpeech(interimTranscript);
            if (cleanInterim) {
              setUserTranscript(normalizeSpeech(`${speechTurnBufferRef.current} ${cleanInterim}`));
            }
          }
        };
        recognitionRef.current.start();
        appendActivity("Browser speech recognition is listening", "success");
      }

      setStatus("Connecting...");
      liveAudioRef.current = new LiveAudioStreamer(
        '/api/voice/live',
        (msg) => {
          if (msg.type === "turn_complete") {
             setStatus("Listening...");
             serverTranscriptRef.current = "";
             appendActivity("Ready for your follow-up", "success");
          } else if (msg.type === "status") {
            setStatus(msg.message);
            appendActivity(msg.message, msg.message === "Disconnected" ? "error" : "info");
            if (msg.message === "Disconnected") {
               setIsActive(false);
            }
          } else if (msg.type === "partial_text") {
             setAssistantTranscript(prev => prev + msg.text);
          } else if (msg.type === "user_transcript") {
            serverTranscriptRef.current = normalizeSpeech(`${serverTranscriptRef.current} ${msg.text}`);
            setUserTranscript(serverTranscriptRef.current);
          } else if (msg.type === "agent_activity") {
            setActiveAgent(msg.agent || msg.data || "");
            appendActivity(describeAgentActivity(msg), "agent");
          } else if (msg.type === "agent_result") {
            setConversation(prev => [
              ...prev,
              { role: "user", text: msg.query },
              { role: "assistant", text: msg.text }
            ]);
            appendActivity("Opened detailed answer in the side panel", "success");
          } else if (msg.type === "order_result") {
            const orderMsg = msg.success
              ? `✅ Order placed! ${msg.message || `${(msg.items_added || []).length} items ordered for ₹${msg.total || 0}`}. Added to pantry & Finance Insights.`
              : `❌ Order failed: ${msg.message || 'Unknown error'}`;
            setConversation(prev => [
              ...prev,
              { role: "assistant", text: orderMsg, isOrderResult: true, orderData: msg }
            ]);
            appendActivity(
              msg.success ? `Order placed — ₹${msg.total || 0}` : "Order failed",
              msg.success ? "success" : "error"
            );
          } else if (msg.type === "interrupted") {
            liveAudioRef.current?.clearPlaybackQueue();
            setStatus("Listening...");
            appendActivity("Interrupted response; listening again", "info");
          } else if (msg.type === "audio_stalled") {
            setStatus("Listening...");
            appendActivity(msg.message || "Audio stopped unexpectedly; listening again", "error");
          }
        },
        () => {
          setStatus("Speaking...");
          setAssistantTranscript("");
          speechTurnBufferRef.current = "";
          serverTranscriptRef.current = "";
          appendActivity("Speaking response", "agent");
        },
        () => {
          setStatus("Listening...");
          appendActivity("Finished speaking; keeping session live", "success");
        }
      );
      await liveAudioRef.current.start();
      setIsActive(true);
      setStatus("Listening...");
      appendActivity("Voice channel is live", "success");
    } catch (err) {
      console.error("Global Voice error:", err);
      setStatus("Error: Check permissions or server");
      appendActivity("Could not start voice session. Check microphone permission and backend server.", "error");
    }
  };

  const stopSession = () => {
    if (liveAudioRef.current) {
      liveAudioRef.current.stop();
    }
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    if (speechFinalTimerRef.current) {
      clearTimeout(speechFinalTimerRef.current);
      speechFinalTimerRef.current = null;
    }
    speechTurnBufferRef.current = "";
    serverTranscriptRef.current = "";
    setIsActive(false);
    setStatus("Ready");
    appendActivity("Voice session stopped", "info");
  };

  const sendOrder = (items) => {
    if (!liveAudioRef.current?.ws || liveAudioRef.current.ws.readyState !== WebSocket.OPEN) {
      appendActivity("Cannot order: voice session not connected", "error");
      return;
    }
    liveAudioRef.current.ws.send(JSON.stringify({
      type: "voice_order",
      items: items,
    }));
    appendActivity("Sending order to PantryMind...", "agent");
  };

  return (
    <VoiceContext.Provider value={{
      isActive,
      status,
      userTranscript,
      assistantTranscript,
      conversation,
      activeAgent,
      activityLog,
      startSession,
      stopSession,
      sendOrder
    }}>
      {children}
    </VoiceContext.Provider>
  );
};

export const useVoice = () => useContext(VoiceContext);
