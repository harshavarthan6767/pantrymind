import React from 'react';
import { AlertTriangle, ShoppingCart, Check } from 'lucide-react';
import './ShoppingCompareCard.css'; // Reusing some base card styles if helpful

export default function InsufficientMacrosCard({ data, onAction }) {
  const missing = data.missing || {};

  return (
    <div className="shopping-compare-card">
      <div className="scc-header" style={{ background: 'rgba(255, 170, 0, 0.1)' }}>
        <div className="scc-header-left">
          <AlertTriangle size={20} color="#ffaa00" />
          <h3 style={{ color: '#ffaa00' }}>Ambitious Macros!</h3>
        </div>
      </div>
      <div className="scc-body">
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          It looks like your pantry doesn't have enough ingredients to meet these exact macronutrient goals.
        </p>
        <div style={{ background: 'var(--bg-surface-2)', padding: '12px', borderRadius: 'var(--radius-md)', marginBottom: '16px' }}>
          <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-tertiary)', marginBottom: '8px' }}>Missing Macros</h4>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {Object.entries(missing).map(([macro, val]) => (
              <li key={macro} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px' }}>
                <span style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>{macro}</span>
                <span style={{ color: 'var(--text-secondary)' }}>{val}</span>
              </li>
            ))}
          </ul>
        </div>
        
        <div style={{ display: 'flex', gap: '12px' }}>
          <button 
            className="order-skip-btn" 
            onClick={() => onAction('proceed')}
          >
            <Check size={16} /> Proceed Anyway
          </button>
          <button 
            className="order-confirm-btn" 
            onClick={() => onAction('find')}
          >
            <ShoppingCart size={16} /> Find Missing
          </button>
        </div>
      </div>
    </div>
  );
}
