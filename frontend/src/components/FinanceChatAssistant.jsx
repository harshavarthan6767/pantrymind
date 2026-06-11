import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Sparkles, Trash2, IndianRupee } from 'lucide-react';
import { sendFinanceChat, getFinanceChatHistory } from '../services/api';
import './FinanceChatAssistant.css';

const SESSION_KEY = 'pantrymind_finance_chat_session';

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

function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/₹([\d,.]+)/g, '<span class="currency">₹$1</span>')
    .replace(/\n/g, '<br/>');
  return html;
}

export default function FinanceChatAssistant({ isOpen, onClose, autoSendQuery }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const hasSentAutoQuery = useRef(false);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    if (!isOpen) {
      hasSentAutoQuery.current = false;
      return;
    }
    const sid = getSessionId();
    setSessionId(sid);
    loadHistory(sid);
    
    if (autoSendQuery && !hasSentAutoQuery.current) {
      hasSentAutoQuery.current = true;
      // Slight delay to allow overlay to animate
      setTimeout(() => {
        handleSendText(autoSendQuery, sid);
      }, 400);
    }
  }, [isOpen, autoSendQuery]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const loadHistory = async (sid) => {
    try {
      const res = await getFinanceChatHistory(sid);
      if (res && res.history) {
        setMessages(res.history);
      }
    } catch (e) {
      console.error("Failed to load finance chat history", e);
    }
  };

  const handleSendText = async (text, currentSid) => {
    if (!text.trim() || isLoading) return;
    const now = new Date().toISOString();
    setMessages(prev => [...prev, { role: 'user', content: text, timestamp: now }]);
    setIsLoading(true);
    try {
      const res = await sendFinanceChat(text, currentSid || sessionId);
      if (res.reply) {
        setMessages(prev => [...prev, { role: 'assistant', content: res.reply, timestamp: new Date().toISOString() }]);
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'system', content: 'Connection error. Please try again.', timestamp: new Date().toISOString() }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const userMsg = input.trim();
    setInput('');
    await handleSendText(userMsg, sessionId);
  };

  const clearHistory = () => {
    if (window.confirm("Delete finance chat history?")) {
      const newSid = crypto.randomUUID();
      localStorage.setItem(SESSION_KEY, newSid);
      setSessionId(newSid);
      setMessages([]);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="finance-chat-overlay" onClick={onClose}>
      <div className="finance-chat-drawer" onClick={e => e.stopPropagation()}>
        <div className="chat-header">
          <div className="chat-title">
            <IndianRupee className="chat-icon" size={20} />
            <h2>Finance Agent</h2>
            <span className="model-badge">Flash Lite</span>
          </div>
          <div className="chat-actions">
            <button className="icon-btn" onClick={clearHistory} title="Clear Chat">
              <Trash2 size={16} />
            </button>
            <button className="close-btn" onClick={onClose}>&times;</button>
          </div>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-empty">
              <Sparkles size={32} className="empty-icon" />
              <h3>Finance Assistant</h3>
              <p>Ask about your spending, budgets, or month-over-month trends.</p>
              <div className="chat-suggestions">
                <button onClick={() => setInput("What was my total spend last month?")}>"What was my total spend last month?"</button>
                <button onClick={() => setInput("How much did I spend on groceries this month?")}>"How much did I spend on groceries this month?"</button>
                <button onClick={() => setInput("What is my disposable income?")}>"What is my disposable income?"</button>
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`chat-bubble ${m.role}`}>
              <div 
                className="chat-content" 
                dangerouslySetInnerHTML={{ __html: renderMarkdown(m.content) }} 
              />
              <div className="chat-time">{formatTime(m.timestamp)}</div>
            </div>
          ))}

          {isLoading && (
            <div className="chat-bubble assistant loading">
              <div className="typing-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Ask about your finances..."
            disabled={isLoading}
          />
          <button className="send-btn" onClick={handleSend} disabled={!input.trim() || isLoading}>
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
