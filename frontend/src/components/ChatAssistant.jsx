import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Sparkles } from 'lucide-react';
import { streamAgentMessage, getChatHistory } from '../services/api';
import ChoiceCard from './ChoiceCard';
import AITable from './AITable';
import './ChatAssistant.css';

/* ---- Helpers ---- */
const SESSION_KEY = 'pantrymind_chat_session';

function getSessionId() {
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

function formatTime(ts) {
  const d = ts ? new Date(ts) : new Date();
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Lightweight markdown → HTML for assistant messages.
 * Handles **bold**, *italic*, bullet lists, and preserves ₹ currency.
 */
function renderMarkdown(text) {
  if (!text) return '';

  let html = text
    // escape angle brackets (safety)
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // bold **text**
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // italic *text*
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
    // line breaks
    .replace(/\n/g, '<br/>');

  // Convert bullet lines (- item or • item) into <ul><li>
  const lines = html.split('<br/>');
  let inList = false;
  const processed = [];

  for (const line of lines) {
    const bulletMatch = line.match(/^\s*[-•]\s+(.+)/);
    if (bulletMatch) {
      if (!inList) { processed.push('<ul>'); inList = true; }
      processed.push(`<li>${bulletMatch[1]}</li>`);
    } else {
      if (inList) { processed.push('</ul>'); inList = false; }
      processed.push(line ? `<p>${line}</p>` : '');
    }
  }
  if (inList) processed.push('</ul>');

  return processed.join('');
}

/**
 * Extracts a complete <choice>...</choice> block from the text.
 * Returns the cleaned text, and the parsed choice data.
 * If the choice block is incomplete (streaming), it hides the partial block.
 */
function extractChoiceAndCleanText(text) {
  if (!text) return { cleanText: '', choiceData: null };
  
  const completeRegex = /<choice>([\s\S]*?)<\/choice>/i;
  const completeMatch = text.match(completeRegex);
  
  if (completeMatch) {
    try {
      const choiceData = JSON.parse(completeMatch[1].trim());
      const cleanText = text.replace(completeRegex, '').trim();
      return { cleanText, choiceData };
    } catch {
      // Invalid JSON, hide block
      return { cleanText: text.replace(completeRegex, '').trim(), choiceData: null };
    }
  }

  const partialIndex = text.indexOf('<choice>');
  if (partialIndex !== -1) {
    return { cleanText: text.slice(0, partialIndex).trim(), choiceData: null };
  }

  return { cleanText: text, choiceData: null };
}

/**
 * Extracts alternating text and table blocks from raw markdown text.
 */
function extractBlocks(text) {
  if (!text) return [];
  const parts = [];
  const lines = text.split('\n');
  let currentText = [];
  let currentTable = [];
  let inTable = false;

  for (let line of lines) {
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      if (!inTable) {
        if (currentText.length > 0) {
          parts.push({ type: 'text', content: currentText.join('\n') });
          currentText = [];
        }
        inTable = true;
      }
      currentTable.push(line);
    } else {
      if (inTable) {
        parts.push({ type: 'table', lines: currentTable });
        currentTable = [];
        inTable = false;
      }
      currentText.push(line);
    }
  }
  
  if (currentText.length > 0) parts.push({ type: 'text', content: currentText.join('\n') });
  if (currentTable.length > 0) parts.push({ type: 'table', lines: currentTable });
  
  return parts;
}

/* ---- Quick-prompt suggestions ---- */
const SUGGESTIONS = [
  "What's expiring soon?",
  'Show my monthly spending',
  'Suggest a recipe',
  'Nutrition summary',
];

/* ============================================================
   Component
   ============================================================ */
export default function ChatAssistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  
  // New Streaming State
  const [streamingText, setStreamingText] = useState("");
  const [activeTools, setActiveTools] = useState([]);
  const [activeAgent, setActiveAgent] = useState("pantrymind_orchestrator");

  const sessionId = useRef(getSessionId());
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  /* ---- Auto-scroll ---- */
  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, scrollToBottom]);

  /* ---- Load history on mount ---- */
  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      try {
        const data = await getChatHistory(sessionId.current);
        if (cancelled) return;

        // API may return { messages: [...] } or an array directly
        const history = Array.isArray(data) ? data : data?.messages ?? [];
        if (history.length) {
          setMessages(
            history.map((m) => ({
              role: m.role,
              content: m.content,
              timestamp: m.timestamp || new Date().toISOString(),
            }))
          );
        }
      } catch {
        // History endpoint may not exist yet — silently ignore
      } finally {
        if (!cancelled) setHistoryLoaded(true);
      }
    }

    loadHistory();
    return () => { cancelled = true; };
  }, []);

  /* ---- Focus input after history loads ---- */
  useEffect(() => {
    if (historyLoaded) inputRef.current?.focus();
  }, [historyLoaded]);

  /* ---- Send message ---- */
  const handleSend = useCallback(async (overrideText) => {
    const text = (overrideText ?? input).trim()
    if (!text || loading) return

    const userMsg = { role: "user", content: text, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    setInput("")
    setLoading(true)
    
    // Reset stream state
    setStreamingText("")
    setActiveTools([])
    setActiveAgent("pantrymind_orchestrator")

    try {
      await streamAgentMessage({
        message: text,
        sessionId: sessionId.current,
        onToken: (token) => {
          setStreamingText(prev => prev + token)
        },
        onToolCall: (toolName, agentName) => {
          setActiveTools(prev => [...prev, toolName])
          if (agentName) setActiveAgent(agentName)
        },
        onAgentSwitch: (agentName) => {
          setActiveAgent(agentName)
          setActiveTools([]) // Reset tools for new agent
        },
        onDone: () => {
          setMessages(prev => {
            // Need to read the LATEST streamingText state here
            // The cleanest way is to just let the next render push it to history,
            // but we can also use a ref for streamingText. 
            // For simplicity, we just trigger a save below by ending the stream.
            return prev
          })
        },
        onError: (err) => {
          console.error(err)
        }
      })
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
      // Push the final streamed text to the main message log
      setMessages(prev => {
        // We need a way to get the final streaming text. We'll do it by relying
        // on the fact that handleSend is bound to current state, but streamAgentMessage 
        // updates it via state setters. We can just use the final state hook if we had a ref.
        // Actually, let's fix it right here:
        return prev; // We'll handle pushing to history in a useEffect when loading flips to false
      })
      inputRef.current?.focus()
    }
  }, [input, loading]);

  // Push streaming text to history when done
  useEffect(() => {
    if (!loading && streamingText) {
      setMessages(prev => [
        ...prev, 
        { role: "assistant", content: streamingText, timestamp: new Date().toISOString() }
      ])
      setStreamingText("")
      setActiveTools([])
      setActiveAgent("pantrymind_orchestrator")
    }
  }, [loading, streamingText])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChoiceProceed = (selectedOption) => {
    if (!selectedOption) return;
    
    // Create the structured payload the agent will understand
    const payloadMsg = JSON.stringify({
      type: "choice_selection",
      selected_option_id: selectedOption.id,
      payload: selectedOption.payload
    });

    // Add a friendly message to the UI
    setMessages(prev => [
      ...prev,
      { role: "user", content: `Selected: ${selectedOption.label}`, timestamp: new Date().toISOString() }
    ]);

    // Send silently to agent
    setLoading(true);
    setStreamingText("");
    setActiveTools([]);
    setActiveAgent("pantrymind_orchestrator");

    streamAgentMessage({
      message: payloadMsg, // Raw JSON string acting as prompt
      sessionId: sessionId.current,
      onToken: (token) => setStreamingText(prev => prev + token),
      onToolCall: (toolName, agentName) => {
        setActiveTools(prev => [...prev, toolName]);
        if (agentName) setActiveAgent(agentName);
      },
      onAgentSwitch: (name) => {
        setActiveAgent(name);
        setActiveTools([]);
      },
      onDone: () => {},
      onError: (err) => console.error(err)
    }).finally(() => {
      setLoading(false);
      setMessages(prev => prev);
      inputRef.current?.focus();
    });
  };

  /* ---- Render ---- */
  const isEmpty = messages.length === 0 && !loading;

  return (
    <div className="chat-page">
      {/* Header */}
      <header className="chat-header">
        <div className="chat-header-avatar">
          <Sparkles size={22} color="#0a0a0a" />
        </div>
        <div className="chat-header-info">
          <span className="chat-header-title">PantryMind AI</span>
          <span className="chat-header-status">Online</span>
        </div>
      </header>

      {/* Messages */}
      <div className="chat-messages">
        {isEmpty && (
          <div className="chat-empty">
            <div className="chat-empty-icon">🧠</div>
            <h2 className="chat-empty-title">Hi! I'm PantryMind AI</h2>
            <p className="chat-empty-desc">
              Ask me anything about your pantry, spending, nutrition, or recipes.
              I can help you manage your kitchen smarter.
            </p>
            <div className="chat-empty-chips">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="chat-empty-chip"
                  onClick={() => handleSend(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          const { cleanText, choiceData } = msg.role === 'assistant' 
            ? extractChoiceAndCleanText(msg.content)
            : { cleanText: msg.content, choiceData: null };

          return (
            <div key={i} className={`chat-msg chat-msg--${msg.role}`}>
              <div className={`chat-bubble chat-bubble--${msg.role === 'system' ? 'error' : msg.role}`}>
                {msg.role === 'assistant' ? (
                  <>
                    {cleanText && extractBlocks(cleanText).map((block, idx) => 
                      block.type === 'text' ? (
                        <div key={idx} dangerouslySetInnerHTML={{ __html: renderMarkdown(block.content) }} />
                      ) : (
                        <AITable key={idx} tableLines={block.lines} />
                      )
                    )}
                    {choiceData && <ChoiceCard choiceData={choiceData} onProceed={handleChoiceProceed} />}
                  </>
                ) : (
                  cleanText
                )}
              </div>
              <span className="chat-timestamp">{formatTime(msg.timestamp)}</span>
            </div>
          );
        })}

        {loading && (
          <div className="chat-msg chat-msg--assistant chat-msg--streaming">
            <div className="chat-bubble chat-bubble--assistant">
              {/* Agent Status Header */}
              <div className="streaming-status-header">
                <span className="agent-badge">🤖 {activeAgent.replace('_agent', '').replace('_', ' ')}</span>
                {activeTools.length > 0 && (
                  <span className="tool-badge animate-pulse">
                    🛠️ Using: {activeTools[activeTools.length - 1]}
                  </span>
                )}
              </div>
              
              {/* Streaming Content */}
              {streamingText ? (
                (() => {
                  const { cleanText, choiceData } = extractChoiceAndCleanText(streamingText);
                  return (
                    <>
                      {cleanText && extractBlocks(cleanText).map((block, idx) => 
                        block.type === 'text' ? (
                          <div key={idx} dangerouslySetInnerHTML={{ __html: renderMarkdown(block.content) }} />
                        ) : (
                          <AITable key={idx} tableLines={block.lines} />
                        )
                      )}
                      {choiceData && <ChoiceCard choiceData={choiceData} onProceed={handleChoiceProceed} />}
                    </>
                  );
                })()
              ) : (
                <div className="chat-typing">
                  <span className="chat-typing-dot" />
                  <span className="chat-typing-dot" />
                  <span className="chat-typing-dot" />
                </div>
              )}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-bar">
        <div className="chat-input-wrapper">
          <input
            ref={inputRef}
            className="chat-input"
            type="text"
            placeholder="Ask PantryMind anything…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
        </div>
        <button
          className="chat-send-btn"
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          title="Send message"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  );
}
