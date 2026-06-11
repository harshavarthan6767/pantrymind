import React, { useState } from 'react';
import './ChoiceCard.css';

export default function ChoiceCard({ choiceData, onProceed }) {
  const [selectedId, setSelectedId] = useState(null);

  if (!choiceData || !choiceData.options) return null;

  const handleProceed = () => {
    if (selectedId) {
      const selectedOption = choiceData.options.find((opt) => opt.id === selectedId);
      if (selectedOption && onProceed) {
        onProceed(selectedOption);
      }
    }
  };

  return (
    <div className="choice-card-container">
      <h3 className="choice-card-title">{choiceData.title || 'Action Required'}</h3>
      {choiceData.summary && (
        <p className="choice-card-summary">{choiceData.summary}</p>
      )}

      <div className="choice-options">
        {choiceData.options.map((opt) => (
          <div
            key={opt.id}
            className={`choice-option ${selectedId === opt.id ? 'selected' : ''}`}
            onClick={() => setSelectedId(opt.id)}
          >
            <div className="choice-option-radio"></div>
            <div className="choice-option-text">
              <span className="choice-option-label">{opt.label}</span>
              {opt.description && (
                <span className="choice-option-desc">{opt.description}</span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="choice-card-actions">
        <button
          className="choice-proceed-btn"
          disabled={!selectedId}
          onClick={handleProceed}
        >
          {choiceData.proceed_label || 'Proceed'}
        </button>
      </div>
    </div>
  );
}
