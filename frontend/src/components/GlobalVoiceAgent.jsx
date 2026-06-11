import React, { useState } from 'react';
import { AlertTriangle, Bot, CheckCircle, Clock, Mic, ShoppingCart, Square, X, Package } from 'lucide-react';
import { useVoice } from '../contexts/VoiceContext';
import RecipeCard from './RecipeCard';
import './GlobalVoiceAgent.css';

function parseJsonBlock(text, blockName) {
  const regex = new RegExp(`:::${blockName}\\s*([\\s\\S]*?)\\s*:::`);
  const match = String(text || '').match(regex);
  if (!match) return { data: null, text };
  try {
    return {
      data: JSON.parse(match[1]),
      text: text.replace(match[0], '').trim(),
    };
  } catch {
    return { data: null, text };
  }
}

function parseListItems(sectionText) {
  return String(sectionText || '')
    .split('\n')
    .map(line => line.trim())
    .filter(line => /^[-*]\s+/.test(line))
    .map(line => line.replace(/^[-*]\s+/, '').trim())
    .filter(Boolean);
}

function parseSteps(sectionText) {
  const numbered = String(sectionText || '')
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => {
      const match = line.match(/^\d+[\).]\s*(.+)$/);
      return match ? match[1].trim() : null;
    })
    .filter(Boolean);

  return numbered.length ? numbered : parseListItems(sectionText);
}

function getSection(text, names) {
  const wanted = names.map(name => name.toLowerCase());
  const lines = String(text || '').split('\n');
  let capture = false;
  const collected = [];

  for (const line of lines) {
    const heading = line.match(/^#{2,4}\s+(.+?)\s*$/);
    if (heading) {
      const normalized = heading[1].toLowerCase();
      capture = wanted.some(name => normalized.includes(name));
      continue;
    }
    if (capture) collected.push(line);
  }

  return collected.join('\n').trim();
}

function parseMissingItem(line) {
  const parts = String(line || '').split(/\s+[—-]\s+/).map(part => part.trim()).filter(Boolean);
  const name = parts[0] || line;
  const quantity = parts[1] || '1';
  const reason = parts.slice(2).join(' - ');
  return { name, quantity, reason };
}

function parseVoiceWorkspace(text) {
  let cleaned = text || '';
  const recipeBlock = parseJsonBlock(cleaned, 'recipe');
  cleaned = recipeBlock.text;
  const orderBlock = parseJsonBlock(cleaned, 'order_confirm');
  cleaned = orderBlock.text;
  const shoppingBlock = parseJsonBlock(cleaned, 'shopping');
  cleaned = shoppingBlock.text;

  // Extract RecipeCard-compatible structure from :::recipe::: block
  let recipeCard = null;
  if (recipeBlock.data) {
    const rd = recipeBlock.data;
    recipeCard = {
      meal_name: rd.meal_name || rd.name || rd.title || 'Your Recipe',
      meal_type: rd.meal_type || rd.type || '',
      ingredients: (rd.ingredients || []).map(ing => {
        if (typeof ing === 'string') return { amount: '', name: ing, note: '' };
        return {
          amount: ing.amount || ing.quantity || '',
          name: ing.name || ing.ingredient || '',
          note: ing.note || ing.notes || '',
        };
      }),
      steps: rd.steps || rd.instructions || [],
      nutrition: rd.nutrition || {},
      tip: rd.tip || rd.tips || '',
    };
  }

  const title = cleaned.match(/^##\s+(.+)$/m)?.[1]?.trim()
    || recipeBlock.data?.meal_name
    || recipeBlock.data?.name
    || recipeBlock.data?.title
    || 'Meal Plan';
  const metaLine = cleaned.match(/\*\*Prep:\*\*\s*([^|]+)\|\s*\*\*Cook:\*\*\s*([^|]+)\|\s*\*\*Calories:\*\*\s*([^\n]+)/i);
  const ingredients = recipeBlock.data?.ingredients
    || parseListItems(getSection(cleaned, ['ingredients from your pantry', 'ingredients']));
  const steps = recipeBlock.data?.steps
    || recipeBlock.data?.instructions
    || parseSteps(getSection(cleaned, ['instructions', 'steps', 'method']));
  const missingFromBlock = orderBlock.data?.missing_items || orderBlock.data?.items || [];
  const missingFromText = parseListItems(getSection(cleaned, ['missing ingredients', 'out of inventory']))
    .map(parseMissingItem);
  const shoppingItems = Array.isArray(shoppingBlock.data) ? shoppingBlock.data : [];
  const missingItems = missingFromBlock.length ? missingFromBlock : (missingFromText.length ? missingFromText : shoppingItems);
  const nutrition = getSection(cleaned, ['nutrition']);
  const looksLikeMeal = recipeCard || steps.length > 0 || ingredients.length > 0 || missingItems.length > 0 || /meal|recipe|prep|cook|ingredient/i.test(cleaned);

  return {
    isMeal: looksLikeMeal,
    recipeCard,
    title,
    prep: metaLine?.[1]?.trim(),
    cook: metaLine?.[2]?.trim(),
    calories: metaLine?.[3]?.replace(/^~/, '').trim(),
    ingredients,
    steps,
    missingItems: missingItems.map(item => typeof item === 'string' ? parseMissingItem(item) : item),
    nutrition,
    text: cleaned,
  };
}

function VoiceMealWorkspace({ message, orderState, onBuyMissing }) {
  const parsed = parseVoiceWorkspace(message.text);
  const order = orderState || {};
  const [recipeFinished, setRecipeFinished] = useState(false);

  // Order result message — simple confirmation card
  if (message.isOrderResult) {
    const data = message.orderData || {};
    return (
      <div className="voice-meal-card">
        <div className={`voice-order-result-card ${data.success ? 'success' : 'error'}`}>
          <div className="voice-order-result-icon">
            {data.success ? <CheckCircle size={28} /> : <AlertTriangle size={28} />}
          </div>
          <p>{message.text}</p>
          {data.success && data.items_added?.length > 0 && (
            <div className="voice-chip-list" style={{ marginTop: '8px' }}>
              {data.items_added.map((name, i) => (
                <span key={i} className="voice-ingredient-chip">{name}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (!parsed.isMeal) {
    return <p>{message.text}</p>;
  }

  // If we have a properly structured RecipeCard, render it
  if (parsed.recipeCard) {
    return (
      <div className="voice-meal-card">
        {/* Summary text before the recipe card */}
        {parsed.text && parsed.text.trim() && (
          <p className="voice-meal-summary">{parsed.text}</p>
        )}

        {/* Reuse Kitchen Chef's RecipeCard */}
        <RecipeCard
          recipe={parsed.recipeCard}
          isFinished={recipeFinished}
          onFinish={() => setRecipeFinished(true)}
        />

        {/* Missing ingredients section */}
        {parsed.missingItems.length > 0 && (
          <section className="voice-missing-card">
            <div className="voice-missing-title">
              <AlertTriangle size={16} />
              <h5>Out Of Inventory</h5>
            </div>
            <p>Some ingredients are missing. Do you want me to buy these and add the spend to Finance Insights?</p>
            <div className="voice-missing-items">
              {parsed.missingItems.map((item, index) => (
                <div key={`${item.name || item.item}-${index}`} className="voice-missing-item">
                  <span>{item.name || item.item}</span>
                  <small>{item.quantity || item.suggested_qty || '1'} {item.unit || ''}</small>
                  {item.reason && <em>{item.reason}</em>}
                </div>
              ))}
            </div>
            <button
              className="voice-buy-btn"
              disabled={order.loading || order.done}
              onClick={() => onBuyMissing(parsed.missingItems)}
            >
              {order.done ? <CheckCircle size={16} /> : <ShoppingCart size={16} />}
              {order.loading ? 'Ordering...' : order.done ? `Ordered ₹${Number(order.amount || 0).toLocaleString('en-IN')}` : 'Buy Missing Ingredients'}
            </button>
            {order.error && <div className="voice-order-error">{order.error}</div>}
            {order.done && <div className="voice-order-success">Added to pantry and Finance Insights.</div>}
          </section>
        )}
      </div>
    );
  }

  // Fallback: text-based rendering (same as before)
  return (
    <div className="voice-meal-card">
      <div className="voice-meal-hero">
        <span className="voice-meal-kicker">Chef workspace</span>
        <h4>{parsed.title}</h4>
        <div className="voice-meal-meta">
          {parsed.prep && <span><Clock size={13} /> Prep {parsed.prep}</span>}
          {parsed.cook && <span><Clock size={13} /> Cook {parsed.cook}</span>}
          {parsed.calories && <span>{parsed.calories}</span>}
        </div>
      </div>

      {parsed.ingredients.length > 0 && (
        <section className="voice-meal-section">
          <h5>From Your Pantry</h5>
          <div className="voice-chip-list">
            {parsed.ingredients.map((item, index) => (
              <span key={`${item}-${index}`} className="voice-ingredient-chip">{typeof item === 'string' ? item : `${item.name} ${item.quantity || ''}`}</span>
            ))}
          </div>
        </section>
      )}

      {parsed.steps.length > 0 && (
        <section className="voice-meal-section">
          <h5>Steps To Prepare</h5>
          <ol className="voice-step-list">
            {parsed.steps.map((step, index) => (
              <li key={`${step}-${index}`}>
                <span>{index + 1}</span>
                <p>{step}</p>
              </li>
            ))}
          </ol>
        </section>
      )}

      {parsed.missingItems.length > 0 && (
        <section className="voice-missing-card">
          <div className="voice-missing-title">
            <AlertTriangle size={16} />
            <h5>Out Of Inventory</h5>
          </div>
          <p>Some ingredients are missing. Do you want me to buy these and add the spend to Finance Insights?</p>
          <div className="voice-missing-items">
            {parsed.missingItems.map((item, index) => (
              <div key={`${item.name || item.item}-${index}`} className="voice-missing-item">
                <span>{item.name || item.item}</span>
                <small>{item.quantity || item.suggested_qty || '1'} {item.unit || ''}</small>
                {item.reason && <em>{item.reason}</em>}
              </div>
            ))}
          </div>
          <button
            className="voice-buy-btn"
            disabled={order.loading || order.done}
            onClick={() => onBuyMissing(parsed.missingItems)}
          >
            {order.done ? <CheckCircle size={16} /> : <ShoppingCart size={16} />}
            {order.loading ? 'Ordering...' : order.done ? `Ordered ₹${Number(order.amount || 0).toLocaleString('en-IN')}` : 'Buy Missing Ingredients'}
          </button>
          {order.error && <div className="voice-order-error">{order.error}</div>}
          {order.done && <div className="voice-order-success">Added to pantry and Finance Insights.</div>}
        </section>
      )}

      {parsed.nutrition && (
        <section className="voice-meal-section compact">
          <h5>Nutrition</h5>
          <pre>{parsed.nutrition}</pre>
        </section>
      )}
    </div>
  );
}

export default function GlobalVoiceAgent({ isOpen, onClose }) {
  const [orderStates, setOrderStates] = useState({});
  const {
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
  } = useVoice();

  if (!isOpen) return null;

  const handleClose = () => {
    if (isActive) stopSession();
    onClose();
  };

  const handleBuyMissing = async (messageIndex, items) => {
    setOrderStates(prev => ({ ...prev, [messageIndex]: { loading: true } }));
    try {
      const normalizedItems = items.map(item => ({
        name: item.name || item.item,
        quantity: item.quantity || item.suggested_qty || 1,
        unit: item.unit || undefined,
        category: item.category || 'PANTRY_DRY',
        reason: item.reason || 'Needed for meal plan',
        estimated_cost: item.estimated_cost,
        estimated_price: item.estimated_price,
      })).filter(item => item.name);

      // Send order via WebSocket for real-time handling
      sendOrder(normalizedItems);
      setOrderStates(prev => ({
        ...prev,
        [messageIndex]: {
          loading: false,
          done: true,
          amount: 0,  // Will be updated by the order_result message
        }
      }));
    } catch (error) {
      setOrderStates(prev => ({
        ...prev,
        [messageIndex]: {
          loading: false,
          error: error.message || 'Could not place order.',
        }
      }));
    }
  };

  return (
    <div className="global-voice-overlay" onClick={handleClose}>
      <div className="global-voice-container" onClick={event => event.stopPropagation()}>
        <section className="voice-console">
          <button className="voice-close-btn" onClick={handleClose}><X size={22} /></button>
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
              {isActive ? <Square size={26} /> : <Mic size={26} />}
            </button>
          </div>

          <div className="voice-activity-box" aria-live="polite">
            <div className="voice-activity-header">
              <span>Activity</span>
              <span>{isActive ? "Live" : "Idle"}</span>
            </div>
            <div className="voice-activity-list">
              {activityLog?.length ? activityLog.map(item => (
                <div key={item.id} className={`voice-activity-row ${item.tone || 'info'}`}>
                  <span className="voice-activity-dot" aria-hidden="true"></span>
                  <p>{item.text}</p>
                  <time>{item.time}</time>
                </div>
              )) : (
                <div className="voice-activity-row muted">
                  <span className="voice-activity-dot" aria-hidden="true"></span>
                  <p>Waiting for your voice session...</p>
                </div>
              )}
            </div>
          </div>

          {userTranscript && (
            <div className="transcript-box">
              <p className="transcript-label">You</p>
              <p className="transcript-text">{userTranscript}</p>
            </div>
          )}

          {assistantTranscript && (
            <div className="transcript-box assistant-box">
              <p className="transcript-label">Assistant</p>
              <p className="transcript-text">{assistantTranscript}</p>
            </div>
          )}

          <p className="voice-hint">Ask about inventory, finances, meals, expiry, or analytics.</p>
        </section>

        <aside className="voice-results-panel">
          <div className="voice-results-header">
            <div>
              <span className="voice-results-eyebrow">Live agent workspace</span>
              <h3>Details</h3>
            </div>
            <Bot size={22} />
          </div>

          <div className="voice-results-body">
            {conversation.filter(m => m.role === "assistant").length === 0 ? (
              <div className="voice-results-empty">
                <Bot size={28} />
                <p>Meal plans, cooking steps, inventory lists, and detailed finance answers will appear here while the assistant summarizes them aloud.</p>
              </div>
            ) : conversation.map((message, index) => {
              if (message.role === "user") return null;
              return (
                <div key={`assistant-${index}`} className="voice-message assistant">
                  <span>PantryMind</span>
                  <VoiceMealWorkspace
                    message={message}
                    orderState={orderStates[index]}
                    onBuyMissing={(items) => handleBuyMissing(index, items)}
                  />
                </div>
              );
            })}
          </div>

          {activeAgent && (
            <div className="voice-agent-status">Working with {activeAgent.replaceAll("_", " ")}</div>
          )}
        </aside>
      </div>
    </div>
  );
}
