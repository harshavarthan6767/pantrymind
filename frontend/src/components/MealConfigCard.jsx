import React, { useState, useRef } from 'react';
import { ChefHat, Flame, Minus, Plus, ChevronDown, ChevronUp, Globe } from 'lucide-react';
import './MealConfigCard.css';

export default function MealConfigCard({ config, onConfirm }) {
  const [calInputStr, setCalInputStr] = useState(String(config.calories?.value || 600));
  const [macros, setMacros] = useState({
    protein: config.macros?.protein?.value || 40,
    carbs: config.macros?.carbs?.value || 50,
    fat: config.macros?.fat?.value || 20,
    fiber: config.macros?.fiber?.value || 10,
    sugar: config.macros?.sugar?.value || 5,
    sodium: config.macros?.sodium?.value || 500,
  });
  const [showMacros, setShowMacros] = useState(false);
  const [spice, setSpice] = useState(config.spice_level?.value || 'Medium');
  const [method, setMethod] = useState(config.cooking_method?.value || 'Best for ingredients');
  const [cuisine, setCuisine] = useState(config.cuisine?.value || 'Indian');
  const [selectedIngredients, setSelectedIngredients] = useState([]);

  const ringRef = useRef(null);

  const calMin = 0;
  const calMax = 5000;
  
  // Parse safely, default to 0 if typing but 600 if invalid on blur
  let currentVal = parseInt(calInputStr, 10);
  if (isNaN(currentVal)) currentVal = 0;
  const calories = Math.min(calMax, Math.max(calMin, currentVal));
  const calPercent = calMax > 0 ? (calories / calMax) * 100 : 0;

  const handleRingInteraction = (e) => {
    if (!ringRef.current) return;
    const rect = ringRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    const clientX = e.clientX;
    const clientY = e.clientY;
    
    const dx = clientX - centerX;
    const dy = clientY - centerY;
    
    let angle = Math.atan2(dy, dx) + Math.PI / 2; 
    if (angle < 0) angle += 2 * Math.PI;
    
    let percent = angle / (2 * Math.PI);
    let newValue = Math.round(percent * calMax);
    newValue = Math.round(newValue / 50) * 50;
    
    setCalInputStr(String(newValue));
  };

  const handlePointerDown = (e) => {
    handleRingInteraction(e);
    const onMove = (eMove) => handleRingInteraction(eMove);
    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
  };

  const handleConfirm = () => {
    onConfirm({
      ...config,
      calories: { ...config.calories, value: calories || 600 },
      macros: {
        protein: { value: macros.protein, unit: 'g' },
        carbs: { value: macros.carbs, unit: 'g' },
        fat: { value: macros.fat, unit: 'g' },
        fiber: { value: macros.fiber, unit: 'g' },
        sugar: { value: macros.sugar, unit: 'g' },
        sodium: { value: macros.sodium, unit: 'mg' },
      },
      spice_level: { ...config.spice_level, value: spice },
      cooking_method: { ...config.cooking_method, value: method },
      cuisine: { ...(config.cuisine || {}), value: cuisine },
      suggested_ingredients: selectedIngredients,
    });
  };

  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDash = (calPercent / 100) * circumference;

  return (
    <div className="meal-config-card">
      <div className="mcc-header">
        <ChefHat size={20} />
        <h3>{config.meal_name || 'Your Meal'}</h3>
        <span className="mcc-type-badge">{config.meal_type}</span>
      </div>

      <div className="mcc-body">
        {/* Calorie Ring */}
        <div className="calorie-section">
          <div className="calorie-ring-container">
            <svg 
              className="calorie-ring" 
              viewBox="0 0 128 128"
              ref={ringRef}
              onPointerDown={handlePointerDown}
              style={{ cursor: 'pointer', touchAction: 'none' }}
            >
              <circle className="ring-bg" cx="64" cy="64" r={radius} />
              <circle
                className="ring-fill"
                cx="64" cy="64" r={radius}
                strokeDasharray={circumference}
                strokeDashoffset={circumference - strokeDash}
              />
            </svg>
            <div className="calorie-center">
              <input 
                type="number" 
                className="cal-input" 
                value={calInputStr} 
                onChange={(e) => setCalInputStr(e.target.value)}
                onBlur={() => {
                  let v = parseInt(calInputStr, 10);
                  if (isNaN(v)) v = 600;
                  setCalInputStr(String(Math.min(calMax, Math.max(calMin, v))));
                }}
              />
              <span className="cal-label">kcal</span>
            </div>
          </div>
          <div className="calorie-controls">
            <button className="cal-btn" onClick={() => setCalInputStr(String(Math.max(calMin, calories - 50)))}>
              <Minus size={16} />
            </button>
            <button className="cal-btn" onClick={() => setCalInputStr(String(Math.min(calMax, calories + 50)))}>
              <Plus size={16} />
            </button>
          </div>
        </div>

        {/* Macros Toggle */}
        <button className="macros-toggle" onClick={() => setShowMacros(!showMacros)}>
          <span>Macros</span>
          {showMacros ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
        {showMacros && (
          <div className="macros-panel">
            {[
              { key: 'protein', max: 100, unit: 'g' },
              { key: 'carbs', max: 200, unit: 'g' },
              { key: 'fat', max: 100, unit: 'g' },
              { key: 'fiber', max: 50, unit: 'g' },
              { key: 'sugar', max: 50, unit: 'g' },
              { key: 'sodium', max: 2000, unit: 'mg', step: 50 }
            ].map((m) => (
              <div key={m.key} className="macro-slider-row">
                <label className="macro-label">{m.key.charAt(0).toUpperCase() + m.key.slice(1)}</label>
                <input
                  type="range" min="0" max={m.max} step={m.step || 1}
                  value={macros[m.key]}
                  onChange={(e) => setMacros({ ...macros, [m.key]: parseInt(e.target.value) })}
                  className={`macro-range range-${m.key}`}
                />
                <span className="macro-val">{macros[m.key]}{m.unit}</span>
              </div>
            ))}
          </div>
        )}

        {/* Spice Level */}
        {config.spice_level?.options && (
          <div className="pill-section">
            <label className="pill-label"><Flame size={14} /> Spice Level</label>
            <div className="pill-group">
              {config.spice_level.options.map((opt) => (
                <button key={opt} className={`pill ${spice === opt ? 'active' : ''}`} onClick={() => setSpice(opt)}>
                  {opt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Cuisine */}
        {config.cuisine?.options && (
          <div className="pill-section">
            <label className="pill-label"><Globe size={14} /> Cuisine</label>
            <div className="pill-group">
              {config.cuisine.options.map((opt) => (
                <button key={opt} className={`pill ${cuisine === opt ? 'active' : ''}`} onClick={() => setCuisine(opt)}>
                  {opt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Cooking Method */}
        {config.cooking_method?.options && (
          <div className="pill-section">
            <label className="pill-label">Cooking Method</label>
            <div className="pill-group">
              {config.cooking_method.options.map((opt) => (
                <button key={opt} className={`pill ${method === opt ? 'active' : ''}`} onClick={() => setMethod(opt)}>
                  {opt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Excluded Ingredients */}
        {config.excluded_ingredients?.length > 0 && (
          <div className="ingredient-section">
            <label className="pill-label">Excluded</label>
            <div className="ingredient-badges">
              {config.excluded_ingredients.map((item, i) => (
                <span key={i} className="badge excluded">{item}</span>
              ))}
            </div>
          </div>
        )}

        {/* Suggested Ingredients */}
        {config.suggested_ingredients?.length > 0 && (
          <div className="ingredient-section">
            <label className="pill-label">Using</label>
            <div className="ingredient-badges">
              {config.suggested_ingredients.map((item, i) => {
                const isSelected = selectedIngredients.includes(item);
                return (
                  <span 
                    key={i} 
                    className={`badge suggested ${isSelected ? 'selected' : 'unselected'}`}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedIngredients(selectedIngredients.filter(ing => ing !== item));
                      } else {
                        setSelectedIngredients([...selectedIngredients, item]);
                      }
                    }}
                    style={{ cursor: 'pointer', opacity: isSelected ? 1 : 0.5 }}
                  >
                    {item}
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <button className="mcc-go-btn" onClick={handleConfirm}>
        <ChefHat size={18} /> Prepare This Meal
      </button>
    </div>
  );
}
