import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowUp,
  Mic,
  ChefHat,
  Minus,
  Plus,
  ChevronDown,
  ShoppingBag,
  Check,
  Flame,
  Beef,
  Wheat,
  Droplets,
} from 'lucide-react';
import TopBar from '../components/TopBar';
import { sendChat } from '../services/api';
import './Kitchen.css';

/* ── Circular Progress Ring ─────────────────────────── */
function CircularProgress({ value, max, color, label, display }) {
  const radius = 34;
  const stroke = 5;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(value / max, 1);
  const offset = circumference * (1 - pct);

  return (
    <div className="circular-progress-item">
      <svg className="circular-svg" viewBox="0 0 80 80">
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={stroke}
        />
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 40 40)"
          className="circular-bar"
        />
        <text
          x="40"
          y="38"
          textAnchor="middle"
          dominantBaseline="central"
          className="circular-pct"
          fill="#e5e2e1"
        >
          {Math.round(pct * 100)}%
        </text>
      </svg>
      <span className="circular-label">{label}</span>
      <span className="circular-value">{display}</span>
    </div>
  );
}

/* ── Shopping Item ──────────────────────────────────── */
function ShoppingItem({ name, qty, checked, onToggle }) {
  return (
    <label className="shopping-item">
      <span
        className={`shopping-checkbox ${checked ? 'shopping-checkbox--checked' : ''}`}
        onClick={onToggle}
        role="checkbox"
        aria-checked={checked}
        tabIndex={0}
      >
        {checked && <Check size={12} />}
      </span>
      <span className={`shopping-name ${checked ? 'shopping-name--done' : ''}`}>{name}</span>
      <span className="shopping-qty">{qty}</span>
    </label>
  );
}

/* ── Kitchen Page ───────────────────────────────────── */
export default function Kitchen() {
  const [calorieTarget, setCalorieTarget] = useState(1800);
  const [diet, setDiet] = useState('Vegetarian');
  const [strictInventory, setStrictInventory] = useState(true);
  const [checkedItems, setCheckedItems] = useState({});
  const [chatInput, setChatInput] = useState('');
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'user', text: 'Plan meals for the week with 1800 calories per day using my pantry items' },
    { role: 'ai', type: 'plan', data: {
      title: 'Day 1 Meal Plan (1,800 cal)',
      meals: [
        { label: 'Breakfast', desc: 'Oats with banana and honey', cal: 320 },
        { label: 'Lunch', desc: 'Dal rice with cucumber raita', cal: 580 },
        { label: 'Dinner', desc: 'Paneer bhurji with 2 chapati', cal: 620 },
        { label: 'Snack', desc: 'Mixed nuts and chai', cal: 280 },
      ],
      total: 1800,
    }},
    { role: 'ai', text: 'I used PuLP linear programming to optimize for your 1,800 cal target while staying within your inventory. All ingredients are available in your pantry.' },
    { role: 'ai', text: 'Want me to generate a shopping list or plan for the full week?' },
  ]);
  const chatEndRef = useRef(null);

  const toggleItem = (key) =>
    setCheckedItems((prev) => ({ ...prev, [key]: !prev[key] }));

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const text = chatInput.trim();
    if (!text || sending) return;
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setChatInput('');
    setSending(true);
    try {
      const data = await sendChat(text);
      setMessages((prev) => [...prev, { role: 'ai', text: data.reply }]);
    } catch {
      setMessages((prev) => [...prev, { role: 'ai', text: 'Sorry, something went wrong. Please try again.' }]);
    }
    setSending(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="kitchen-page">
      <TopBar title="Kitchen" subtitle="AI Chef and Meal Planner" />

      <div className="kitchen-layout">
        {/* ═══ LEFT: AI Chef ═══ */}
        <div className="kitchen-left">
          <div className="glass-card kitchen-chat-card">
            <div className="card-header">
              <ChefHat size={18} className="icon-green" />
              <h3>AI Chef</h3>
            </div>

            <div className="chat-area">
              {messages.map((msg, i) => {
                if (msg.role === 'user') {
                  return (
                    <div key={i} className="chat-row chat-row--user">
                      <div className="chat-bubble chat-bubble--user">{msg.text}</div>
                    </div>
                  );
                }
                if (msg.type === 'plan') {
                  return (
                    <div key={i} className="chat-row chat-row--ai">
                      <div className="chat-bubble chat-bubble--ai chat-bubble--plan">
                        <div className="meal-plan-header">{msg.data.title}</div>
                        <ul className="meal-plan-list">
                          {msg.data.meals.map((m, j) => (
                            <li key={j}>
                              <span className="meal-label">{m.label}</span>
                              <span className="meal-desc">{m.desc}</span>
                              <span className="meal-cal">{m.cal} cal</span>
                            </li>
                          ))}
                        </ul>
                        <div className="meal-plan-total">
                          <span>Total</span>
                          <span className="meal-plan-total-val">{msg.data.total.toLocaleString()} cal</span>
                        </div>
                      </div>
                    </div>
                  );
                }
                return (
                  <div key={i} className="chat-row chat-row--ai">
                    <div className="chat-bubble chat-bubble--ai">{msg.text}</div>
                  </div>
                );
              })}
              {sending && (
                <div className="chat-row chat-row--ai">
                  <div className="chat-bubble chat-bubble--ai" style={{ opacity: 0.6 }}>Thinking...</div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* ── Chat input ── */}
            <div className="chat-input-bar">
              <input
                type="text"
                className="chat-input"
                placeholder="Ask the AI Chef..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={sending}
              />
              <button className="chat-send-btn" aria-label="Send" onClick={handleSend} disabled={sending}>
                <ArrowUp size={18} />
              </button>
              <button className="chat-mic-btn" aria-label="Voice input">
                <Mic size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* ═══ RIGHT: Stacked cards ═══ */}
        <div className="kitchen-right">
          {/* ── Nutrition Today ── */}
          <div className="glass-card">
            <div className="card-header">
              <Flame size={18} className="icon-green" />
              <h3>Nutrition Today</h3>
            </div>
            <div className="nutrition-grid">
              <CircularProgress
                value={1450}
                max={1800}
                color="#4ade80"
                label="Calories"
                display="1450 / 1800"
              />
              <CircularProgress
                value={52}
                max={60}
                color="#818cf8"
                label="Protein"
                display="52g / 60g"
              />
              <CircularProgress
                value={180}
                max={225}
                color="#fbbf24"
                label="Carbs"
                display="180g / 225g"
              />
              <CircularProgress
                value={38}
                max={50}
                color="#f472b6"
                label="Fat"
                display="38g / 50g"
              />
            </div>
          </div>

          {/* ── Meal Settings ── */}
          <div className="glass-card">
            <div className="card-header">
              <Beef size={18} className="icon-green" />
              <h3>Meal Settings</h3>
            </div>

            <div className="settings-row">
              <span className="settings-label">Calorie Target</span>
              <div className="settings-stepper">
                <button
                  className="stepper-btn"
                  onClick={() => setCalorieTarget((v) => Math.max(1200, v - 100))}
                  aria-label="Decrease calories"
                >
                  <Minus size={14} />
                </button>
                <span className="stepper-value">
                  {calorieTarget.toLocaleString()} cal/day
                </span>
                <button
                  className="stepper-btn"
                  onClick={() => setCalorieTarget((v) => Math.min(4000, v + 100))}
                  aria-label="Increase calories"
                >
                  <Plus size={14} />
                </button>
              </div>
            </div>

            <div className="settings-row">
              <span className="settings-label">Diet</span>
              <div className="settings-select-wrapper">
                <select
                  className="settings-select"
                  value={diet}
                  onChange={(e) => setDiet(e.target.value)}
                >
                  <option>Vegetarian</option>
                  <option>Non-Vegetarian</option>
                  <option>Vegan</option>
                  <option>Keto</option>
                </select>
                <ChevronDown size={14} className="select-arrow" />
              </div>
            </div>

            <div className="settings-row">
              <span className="settings-label">Strict inventory only</span>
              <button
                className={`toggle-switch ${strictInventory ? 'toggle-switch--on' : ''}`}
                onClick={() => setStrictInventory((v) => !v)}
                role="switch"
                aria-checked={strictInventory}
              >
                <span className="toggle-knob" />
              </button>
            </div>
          </div>

          {/* ── Shopping List ── */}
          <div className="glass-card">
            <div className="card-header">
              <ShoppingBag size={18} className="icon-green" />
              <h3>Shopping List</h3>
            </div>

            <div className="shopping-list">
              <ShoppingItem
                name="Milk"
                qty="2L"
                checked={!!checkedItems.milk}
                onToggle={() => toggleItem('milk')}
              />
              <ShoppingItem
                name="Eggs"
                qty="12 pcs"
                checked={!!checkedItems.eggs}
                onToggle={() => toggleItem('eggs')}
              />
              <ShoppingItem
                name="Wheat Flour"
                qty="5 kg"
                checked={!!checkedItems.flour}
                onToggle={() => toggleItem('flour')}
              />
            </div>

            <button className="btn-primary shopping-add-btn">Add All to Cart</button>
          </div>
        </div>
      </div>
    </div>
  );
}
