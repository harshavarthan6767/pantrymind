import React, { useRef, useState } from 'react';
import { ChefHat, Download, Clock, Flame, Utensils, Check } from 'lucide-react';
import html2canvas from 'html2canvas';
import { request } from '../services/api';
import './RecipeCard.css';

export default function RecipeCard({ recipe, isFinished, onFinish }) {
  const cardRef = useRef(null);
  const [checkedSteps, setCheckedSteps] = useState(() => {
    const saved = localStorage.getItem(`recipe_steps_${recipe.meal_name}`);
    return saved ? new Set(JSON.parse(saved)) : new Set();
  });

  const toggleStep = (i) => {
    const newSet = new Set(checkedSteps);
    if (newSet.has(i)) newSet.delete(i);
    else newSet.add(i);
    setCheckedSteps(newSet);
    localStorage.setItem(`recipe_steps_${recipe.meal_name}`, JSON.stringify(Array.from(newSet)));
  };

  const handleSaveImage = async () => {
    if (!cardRef.current) return;
    try {
      const originalTheme = document.documentElement.getAttribute('data-theme');
      document.documentElement.setAttribute('data-theme', 'light');
      
      // Let React and CSS apply the light theme styles before capturing
      await new Promise(resolve => setTimeout(resolve, 100));

      const canvas = await html2canvas(cardRef.current, {
        backgroundColor: '#FDFAF6', // Light theme bg-surface
        scale: 2,
        useCORS: true,
      });

      if (originalTheme) {
        document.documentElement.setAttribute('data-theme', originalTheme);
      } else {
        document.documentElement.removeAttribute('data-theme');
      }

      const link = document.createElement('a');
      link.download = `${(recipe.meal_name || 'recipe').replace(/\s+/g, '_')}_card.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (e) {
      console.error('Save image failed:', e);
    }
  };

  const handleFinishedCooking = async () => {
    if (isFinished) return;
    if (onFinish) onFinish();

    try {
      // Consume ingredients
      if (recipe.ingredients && recipe.ingredients.length > 0) {
        for (const ing of recipe.ingredients) {
          if (!ing.name) continue;
          const formData = new FormData();
          formData.append('item_name', ing.name);
          formData.append('quantity', 1.0); // Simplified default, could parse amount
          await request('/api/inventory/consume', {
            method: 'POST',
            body: formData,
          });
        }
      }

      // Log transaction
      await request('/api/finance/transaction', {
        method: 'POST',
        body: JSON.stringify({
          amount: 0, // Sunk cost for pantry items, can be extended later
          category: 'Food',
          description: `Cooked ${recipe.meal_name || 'Meal'}`,
          type: 'expense'
        })
      });
      
    } catch (e) {
      console.error('Failed to log cooking completion:', e);
    }
  };

  const totalNutrition = recipe.nutrition || {};

  return (
    <div className="recipe-card-wrapper">
      <div className="recipe-card" ref={cardRef}>
        {/* Header */}
        <div className="rc-header">
          <div className="rc-header-left">
            <ChefHat size={22} className="rc-header-icon" />
            <div>
              <h3 className="rc-title">{recipe.meal_name || 'Your Recipe'}</h3>
              {recipe.meal_type && <span className="rc-type-badge">{recipe.meal_type}</span>}
            </div>
          </div>
        </div>

        {/* Ingredients Table */}
        {recipe.ingredients?.length > 0 && (
          <div className="rc-section">
            <h4 className="rc-section-title">
              <Utensils size={16} /> Ingredients
            </h4>
            <table className="rc-ingredients-table">
              <thead>
                <tr>
                  <th>Amount</th>
                  <th>Ingredient</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {recipe.ingredients.map((ing, i) => (
                  <tr key={i} className={i % 2 === 0 ? 'even' : 'odd'}>
                    <td className="rc-amount">{ing.amount}</td>
                    <td className="rc-ingredient-name">{ing.name}</td>
                    <td className="rc-note">{ing.note || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Capture Area for Image Save */}
        <div className="rc-prep-capture-area">
          {/* Steps */}
          {recipe.steps?.length > 0 && (
            <div className="rc-section">
              <h4 className="rc-section-title">
                <Clock size={16} /> Preparation
              </h4>
              <ol className="rc-steps">
                {recipe.steps.map((step, i) => (
                  <li 
                    key={i} 
                    className={`rc-step ${checkedSteps.has(i) ? 'completed' : ''}`}
                    onClick={() => toggleStep(i)}
                  >
                    <div className="rc-step-checkbox">
                      {checkedSteps.has(i) ? <Check size={14} /> : <span className="rc-step-num">{i + 1}</span>}
                    </div>
                    <span className="rc-step-text">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Nutrition Summary */}
          <div className="rc-section rc-nutrition-section">
            <h4 className="rc-section-title">
              <Flame size={16} /> Nutrition
            </h4>
            <div className="rc-nutrition-grid">
              <div className="rc-nutri-pill cal">
                <span className="rc-nutri-value">{totalNutrition.calories || '—'}</span>
                <span className="rc-nutri-label">kcal</span>
              </div>
              <div className="rc-nutri-pill protein">
                <span className="rc-nutri-value">{totalNutrition.protein || '—'}</span>
                <span className="rc-nutri-label">Protein</span>
              </div>
              <div className="rc-nutri-pill carbs">
                <span className="rc-nutri-value">{totalNutrition.carbs || '—'}</span>
                <span className="rc-nutri-label">Carbs</span>
              </div>
              <div className="rc-nutri-pill fat">
                <span className="rc-nutri-value">{totalNutrition.fat || '—'}</span>
                <span className="rc-nutri-label">Fat</span>
              </div>
            </div>
          </div>
        </div>

        {/* Tip */}
        {recipe.tip && (
          <div className="rc-tip">
            <span className="rc-tip-icon">💡</span>
            <span>{recipe.tip}</span>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
        <button 
          className="rc-save-btn" 
          onClick={handleFinishedCooking}
          style={{ flex: 1, background: isFinished ? 'var(--sage-700)' : 'var(--sage-500)', color: 'white', border: 'none' }}
          disabled={isFinished}
        >
          <Check size={16} /> {isFinished ? 'Finished & Logged!' : 'I Finished Cooking!'}
        </button>
        <button className="rc-save-btn" onClick={handleSaveImage} style={{ flex: 1, background: 'var(--bg-surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-subtle)' }}>
          <Download size={16} /> Save as Image
        </button>
      </div>
    </div>
  );
}
