import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, Box, AlertTriangle, Leaf, Trash2, ShoppingCart, Check, X, Plus } from 'lucide-react';
import { sendKitchenChat, getDashboardStats } from '../services/api';
import MealConfigCard from '../components/MealConfigCard';
import RecipeCard from '../components/RecipeCard';
import ShoppingCompareCard from '../components/ShoppingCompareCard';
import InsufficientMacrosCard from '../components/InsufficientMacrosCard';
import AITable from '../components/AITable';
import { extractBlocks, renderMarkdown } from '../utils/markdownUtils';
import './Kitchen.css';

function ChefIllustration() {
  return (
    <div className="chef-avatar">
      <svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="60" fill="var(--terra-100)" />
        <path d="M60 40C52 40 45 47 45 55V65C45 73 52 80 60 80C68 80 75 73 75 65V55C75 47 68 40 60 40Z" fill="var(--terra-300)" />
        <path d="M40 50C40 38.9543 48.9543 30 60 30C71.0457 30 80 38.9543 80 50H40Z" fill="var(--terra-500)" />
        <path d="M50 30V25C50 22.2386 52.2386 20 55 20H65C67.7614 20 70 22.2386 70 25V30" fill="var(--terra-500)" />
      </svg>
    </div>
  );
}

// Hidden template prompts — these are sent by button clicks and should not appear as user messages
const HIDDEN_PROMPTS = [
  'I understand the limits. Please proceed and make the best possible recipe using only my current inventory.',
  'Please generate a shopping list for the missing ingredients to meet my original macro goals.',
  "I'll skip ordering for now. Please proceed with the recipe using only available ingredients."
];

function isHiddenMessage(msg) {
  if (msg.role !== 'user') return false;
  if (msg.text.startsWith('[MEAL_CONFIG]')) return true;
  if (msg.text.startsWith('[ORDER_CONFIRMED]')) return true;
  return HIDDEN_PROMPTS.includes(msg.text);
}

function parseMessage(text) {
  let result = { text, config: null, recipe: null, shopping: null, order_confirm: null };
  
  // Parse options block
  const optionsRegex = /:::options\s*([\s\S]*?)\s*:::/;
  const optionsMatch = result.text.match(optionsRegex);
  if (optionsMatch) {
    try {
      result.config = JSON.parse(optionsMatch[1]);
      result.text = result.text.replace(optionsMatch[0], '').trim();
    } catch {}
  }

  // Parse recipe block
  const recipeRegex = /:::recipe\s*([\s\S]*?)\s*:::/;
  const recipeMatch = result.text.match(recipeRegex);
  if (recipeMatch) {
    try {
      result.recipe = JSON.parse(recipeMatch[1]);
      result.text = result.text.replace(recipeMatch[0], '').trim();
    } catch {}
  }

  // Parse shopping block
  const shoppingRegex = /:::shopping\s*([\s\S]*?)\s*:::/;
  const shoppingMatch = result.text.match(shoppingRegex);
  if (shoppingMatch) {
    try {
      result.shopping = JSON.parse(shoppingMatch[1]);
      result.text = result.text.replace(shoppingMatch[0], '').trim();
    } catch {}
  }

  // Parse order_confirm block (human-in-the-loop ordering)
  const orderConfirmRegex = /:::order_confirm\s*([\s\S]*?)\s*:::/;
  const orderConfirmMatch = result.text.match(orderConfirmRegex);
  if (orderConfirmMatch) {
    try {
      result.order_confirm = JSON.parse(orderConfirmMatch[1]);
      result.text = result.text.replace(orderConfirmMatch[0], '').trim();
    } catch {}
  }

  // Parse insufficient macros block
  const insufficientRegex = /:::insufficient_macros\s*([\s\S]*?)\s*:::/;
  const insufficientMatch = result.text.match(insufficientRegex);
  if (insufficientMatch) {
    try {
      result.insufficient_macros = JSON.parse(insufficientMatch[1]);
      result.text = result.text.replace(insufficientMatch[0], '').trim();
    } catch {}
  }

  return result;
}

// Inline OrderConfirmCard component
function OrderConfirmCard({ data, onConfirm, onSkip }) {
  const items = data.missing_items || [];
  const message = data.message || 'These items are not in your pantry. Add to shopping list?';
  
  return (
    <div className="order-confirm-card">
      <div className="order-confirm-header">
        <ShoppingCart size={18} />
        <h4>Missing Ingredients</h4>
      </div>
      <p className="order-confirm-message">{message}</p>
      <div className="order-confirm-items">
        {items.map((item, i) => (
          <div key={i} className="order-confirm-item">
            <span className="item-name">{item.name}</span>
            <span className="item-qty">{item.quantity}</span>
            {item.reason && <span className="item-reason">{item.reason}</span>}
          </div>
        ))}
      </div>
      <div className="order-confirm-actions">
        <button className="order-skip-btn" onClick={onSkip}>
          <X size={16} /> Skip
        </button>
        <button className="order-confirm-btn" onClick={() => onConfirm(items)}>
          <Check size={16} /> Add to Shopping List
        </button>
      </div>
    </div>
  );
}

export default function Kitchen() {
  const [chatInput, setChatInput] = useState('');
  const [sending, setSending] = useState(false);
  const [pantryStats, setPantryStats] = useState({ total_items: 0, expiring_soon: 0, expiring_items: [] });
  const [sessions, setSessions] = useState(() => {
    const saved = localStorage.getItem('kitchen_sessions');
    if (saved) {
      try { return JSON.parse(saved); } catch {}
    }
    return [];
  });
  const [sessionId, setSessionId] = useState(() => {
    let sid = localStorage.getItem('kitchen_chat_active_session');
    if (!sid) {
      sid = crypto.randomUUID();
      localStorage.setItem('kitchen_chat_active_session', sid);
    }
    return sid;
  });
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(`kitchen_messages_${sessionId}`);
    if (saved) {
      try { 
        const parsed = JSON.parse(saved);
        return parsed.filter(m => !(m.role === 'ai' && m.text.includes("Hello! I'm Chef Mira")));
      } catch {}
    }
    return [];
  });
  

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('kitchen_sessions', JSON.stringify(sessions));
  }, [sessions]);

  const switchSession = (id) => {
    setSessionId(id);
    localStorage.setItem('kitchen_chat_active_session', id);
    const saved = localStorage.getItem(`kitchen_messages_${id}`);
    if (saved) {
      try { 
        const parsed = JSON.parse(saved);
        setMessages(parsed.filter(m => !(m.role === 'ai' && m.text.includes("Hello! I'm Chef Mira")))); 
        return; 
      } catch {}
    }
    setMessages([]);
  };

  const createNewSession = () => {
    const newId = crypto.randomUUID();
    setSessionId(newId);
    localStorage.setItem('kitchen_chat_active_session', newId);
    setMessages([]);
  };

  const deleteSession = (e, id) => {
    e.stopPropagation();
    setSessions(prev => prev.filter(s => s.id !== id));
    localStorage.removeItem(`kitchen_messages_${id}`);
    if (sessionId === id) {
      createNewSession();
    }
  };

  useEffect(() => {
    getDashboardStats().then(s => setPantryStats(s)).catch(() => {});
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    localStorage.setItem(`kitchen_messages_${sessionId}`, JSON.stringify(messages));
  }, [messages, sessionId]);

  const markMessageFinished = (index) => {
    setMessages(prev => {
      const newArr = [...prev];
      newArr[index] = { ...newArr[index], isFinished: true };
      return newArr;
    });
  };

  const handleSend = async (textOverride) => {
    const text = textOverride || chatInput.trim();
    if (!text || sending) return;
    
    // Create new session entry if it's the first message
    if (!sessions.find(s => s.id === sessionId)) {
      let title = text;
      if (title.startsWith('[MEAL_CONFIG]')) title = 'Meal Configuration';
      setSessions(prev => [{ id: sessionId, title, timestamp: Date.now() }, ...prev]);
    }
    
    setMessages((prev) => [...prev, { role: 'user', text, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }]);
    
    if (!textOverride) {
      setChatInput('');
      if (inputRef.current) inputRef.current.textContent = '';
    }
    
    setSending(true);
    
    try {
      const data = await sendKitchenChat(text, sessionId);
      setMessages((prev) => [...prev, { role: 'ai', text: data.reply, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }]);
      } catch (err) {
        setMessages((prev) => [...prev, { role: 'ai', text: `Sorry, I'm having trouble connecting to the AI right now: ${err.message}`, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) }]);
      }
    setSending(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestions = [
    "What can I cook tonight?",
    "Use my expiring items",
    "Quick breakfast ideas",
    "Low calorie meals"
  ];



  return (
    <div className="kitchen-page animate-fade-rise">
      {/* LEFT PANEL - CHEF CONTEXT */}
      <div className="chef-context-panel">
        <div className="chef-profile">
          <ChefIllustration />
          <h2 className="chef-name">Chef Mira</h2>
          <p className="chef-subtitle">I know your pantry</p>
        </div>

        <div className="pantry-context-card">
          <div className="context-title">What I know</div>
          <div className="context-list">
            <div className="context-item">
              <Box size={16} className="context-icon sage" />
              <span>{pantryStats.total_items} items in stock</span>
            </div>
            <div className="context-item">
              <AlertTriangle size={16} className="context-icon warning" />
              <span>{pantryStats.expiring_soon} expiring soon</span>
            </div>
            {pantryStats.expiring_items?.length > 0 && (
              <div className="context-item">
                <Leaf size={16} className="context-icon fresh" />
                <span>Watch: {pantryStats.expiring_items.slice(0,3).map(i => i.name).join(', ')}</span>
              </div>
            )}
          </div>
        </div>

        <div className="suggested-topics" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div className="context-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Chat History</span>
            <button onClick={createNewSession} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--sage-700)' }} title="New Chat">
              <Plus size={18} />
            </button>
          </div>
          <div className="topic-chips" style={{ flexDirection: 'column', alignItems: 'stretch', flex: 1, overflowY: 'auto' }}>
            {sessions.length === 0 && (
              <span style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>No history yet</span>
            )}
            {sessions.map((s) => {
              let displayMsg = s.title;
              if (displayMsg.length > 28) displayMsg = displayMsg.substring(0, 25) + '...';
              return (
                <div
                  key={s.id} 
                  className="topic-chip" 
                  style={{ 
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    textAlign: 'left', 
                    opacity: s.id === sessionId ? 1 : 0.6,
                    background: s.id === sessionId ? 'rgba(107, 158, 112, 0.15)' : 'transparent',
                    border: s.id === sessionId ? '1px solid rgba(107, 158, 112, 0.3)' : '1px solid var(--border-subtle)'
                  }} 
                  onClick={() => switchSession(s.id)}
                >
                  <span>{displayMsg}</span>
                  <button 
                    onClick={(e) => deleteSession(e, s.id)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', opacity: 0.8 }}
                    title="Delete Chat"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* RIGHT PANEL - CHAT INTERFACE */}
      <div className="chef-chat-panel">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="kitchen-welcome">
              <ChefIllustration />
              <h2>Ready to cook?</h2>
              <p>Ask me to plan a meal, check your pantry, or use up ingredients.</p>
              <div className="welcome-chips">
                {suggestions.map(s => (
                  <button key={s} onClick={() => { setChatInput(s); if(inputRef.current) inputRef.current.textContent = s; }}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg, i) => {
            // Hide template prompts from button clicks
            if (isHiddenMessage(msg)) return null;

            let parsed = msg.role === 'ai' ? parseMessage(msg.text) : { text: msg.text, config: null, recipe: null, shopping: null, order_confirm: null };

            return (
              <div key={i} className={`chat-row ${msg.role === 'user' ? 'user' : 'ai'}`}>
                {parsed.text && (
                  <div className={`chat-bubble ${msg.role === 'user' ? 'user' : 'ai'}`}>
                    {msg.role === 'ai' ? (
                      extractBlocks(parsed.text).map((block, idx) => 
                        block.type === 'text' ? (
                          <div key={idx} dangerouslySetInnerHTML={{ __html: renderMarkdown(block.content) }} />
                        ) : (
                          <AITable key={idx} tableLines={block.lines} />
                        )
                      )
                    ) : (
                      parsed.text
                    )}
                  </div>
                )}
                {parsed.config && (
                  <MealConfigCard
                    config={parsed.config}
                    onConfirm={(finalConfig) => {
                      const configMsg = `[MEAL_CONFIG] ${JSON.stringify(finalConfig)}`;
                      handleSend(configMsg);
                    }}
                  />
                )}
                {parsed.recipe && (
                  <RecipeCard 
                    recipe={parsed.recipe} 
                    isFinished={msg.isFinished}
                    onFinish={() => markMessageFinished(i)}
                  />
                )}
                {parsed.shopping && (
                  <ShoppingCompareCard items={parsed.shopping} />
                )}
                {parsed.order_confirm && (
                  <OrderConfirmCard
                    data={parsed.order_confirm}
                    onConfirm={(items) => {
                      handleSend(`[ORDER_CONFIRMED] ${JSON.stringify({ items })}`);
                    }}
                    onSkip={() => {
                      handleSend("I'll skip ordering for now. Please proceed with the recipe using only available ingredients.");
                    }}
                  />
                )}
                {parsed.insufficient_macros && (
                  <InsufficientMacrosCard 
                    data={parsed.insufficient_macros}
                    onAction={(action) => {
                      if (action === 'proceed') {
                        handleSend("I understand the limits. Please proceed and make the best possible recipe using only my current inventory.");
                      } else if (action === 'find') {
                        handleSend("Please generate a shopping list for the missing ingredients to meet my original macro goals.");
                      }
                    }}
                  />
                )}
                {msg.time && <div className="chat-time">{msg.time}</div>}
              </div>
            );
          })}
          
          {sending && (
            <div className="chat-row ai">
              <div className="chat-bubble ai typing-bubble">
                <span className="typing-label">Chef Mira is thinking</span>
                <div className="typing-dots">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="chat-input-area">
          <div className="input-wrapper">
            <div 
              className="chat-input"
              ref={inputRef}
              contentEditable
              data-placeholder="Ask Chef Mira anything about your pantry..."
              onInput={(e) => setChatInput(e.currentTarget.textContent)}
              onKeyDown={handleKeyDown}
            />
            {!chatInput && <div className="input-placeholder" style={{ left: 16 }}>Ask Chef Mira anything about your pantry...</div>}
          </div>
          <button 
            className={`send-btn ${chatInput.trim() ? 'enabled' : ''}`} 
            disabled={!chatInput.trim() || sending}
            onClick={() => handleSend()}
          >
            <ArrowUp size={20} />
          </button>
        </div>
        <div className="session-status">
          <div className="status-dot-mini pulsing"></div>
          Session active &middot; Chef remembers this conversation
        </div>
      </div>
    </div>
  );
}
