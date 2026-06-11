import React, { useState, useEffect } from 'react';
import { HeartPulse, Plus, Trash2, ShieldAlert, Search, Loader, Check, AlertTriangle, Pill, Apple, Stethoscope, X } from 'lucide-react';
import { getMedicalConditions, addMedicalCondition, deleteMedicalCondition, runInventorySafetyCheck } from '../services/api';
import './HealthProfile.css';

export default function HealthProfile() {
  const [conditions, setConditions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newCondition, setNewCondition] = useState('');
  const [adding, setAdding] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [safetyReport, setSafetyReport] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const loadConditions = async () => {
    setLoading(true);
    try {
      const data = await getMedicalConditions();
      setConditions(data.conditions || []);
    } catch { setConditions([]); }
    setLoading(false);
  };

  useEffect(() => { loadConditions(); }, []);

  // Auto-refresh every 5s to catch research completions
  useEffect(() => {
    const pending = conditions.some(c => !c.researched);
    if (!pending) return;
    const interval = setInterval(loadConditions, 5000);
    return () => clearInterval(interval);
  }, [conditions]);

  const handleAdd = async () => {
    if (!newCondition.trim() || adding) return;
    setAdding(true);
    try {
      await addMedicalCondition(newCondition.trim());
      setNewCondition('');
      await loadConditions();
    } catch (e) {
      alert(e.message || 'Failed to add condition');
    }
    setAdding(false);
  };

  const handleDelete = async (id) => {
    try {
      await deleteMedicalCondition(id);
      setDeleteTarget(null);
      await loadConditions();
    } catch { /* ignore */ }
  };

  const handleSafetyCheck = async () => {
    setScanning(true);
    try {
      const result = await runInventorySafetyCheck();
      setSafetyReport(result);
    } catch { setSafetyReport({ status: 'error', flagged_items: [] }); }
    setScanning(false);
  };

  return (
    <div className="page-container animate-fade-rise">
      <header className="health-header">
        <div>
          <h1 className="health-title"><HeartPulse size={28} className="title-icon" /> Health Profile</h1>
          <p className="health-subtitle">Manage your medical conditions — AI will adapt your diet</p>
        </div>
        <button className="btn-outline scan-btn" onClick={handleSafetyCheck} disabled={scanning || conditions.length === 0}>
          <ShieldAlert size={16} />
          {scanning ? 'Scanning...' : 'Scan Pantry Safety'}
        </button>
      </header>

      {/* Add Condition Form */}
      <div className="add-condition-bar">
        <input
          className="condition-input"
          type="text"
          placeholder="Enter a medical condition (e.g., Type 2 Diabetes, Lactose Intolerance)"
          value={newCondition}
          onChange={(e) => setNewCondition(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          disabled={adding}
        />
        <button className="btn-primary add-condition-btn" onClick={handleAdd} disabled={!newCondition.trim() || adding}>
          {adding ? <Loader size={18} className="spin" /> : <Plus size={18} />}
          {adding ? 'Researching...' : 'Add Condition'}
        </button>
      </div>

      {/* Safety Report */}
      {safetyReport && (
        <div className="safety-report">
          <div className="safety-report-header">
            <ShieldAlert size={20} />
            <span>Pantry Safety Report — {safetyReport.flagged_items?.length || 0} items flagged</span>
            <button className="close-report" onClick={() => setSafetyReport(null)}><X size={16} /></button>
          </div>
          {safetyReport.flagged_items?.length > 0 ? (
            <div className="flagged-items-list">
              {safetyReport.flagged_items.map((item, i) => (
                <div key={i} className={`flagged-item severity-${item.severity}`}>
                  <AlertTriangle size={16} />
                  <div className="flagged-info">
                    <strong>{item.item_name}</strong>
                    <span>{item.reason}</span>
                    <small>Condition: {item.condition}</small>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="safety-ok"><Check size={16} /> Your pantry looks safe for your conditions!</p>
          )}
        </div>
      )}

      {/* Condition Cards */}
      {loading ? (
        <div className="loading-state"><Loader size={24} className="spin" /> Loading conditions...</div>
      ) : conditions.length === 0 ? (
        <div className="empty-state">
          <HeartPulse size={48} />
          <h3>No medical conditions added</h3>
          <p>Add your conditions above and our AI will research dietary guidelines for you.</p>
        </div>
      ) : (
        <div className="conditions-grid">
          {conditions.map((c) => (
            <div key={c._id} className={`condition-card ${expandedId === c._id ? 'expanded' : ''}`}>
              <div className="condition-card-header" onClick={() => setExpandedId(expandedId === c._id ? null : c._id)}>
                <div className="condition-name-row">
                  <Stethoscope size={20} className="condition-icon" />
                  <h3>{c.condition_name}</h3>
                  <span className={`research-badge ${c.researched ? 'done' : 'pending'}`}>
                    {c.researched ? <><Check size={12} /> Researched</> : <><Loader size={12} className="spin" /> Researching...</>}
                  </span>
                </div>
                <button className="delete-condition" onClick={(e) => { e.stopPropagation(); setDeleteTarget(c._id); }}>
                  <Trash2 size={16} />
                </button>
              </div>

              {c.researched && expandedId === c._id && (
                <div className="condition-details">
                  <p className="dietary-notes">{c.dietary_notes}</p>
                  
                  <div className="detail-section avoid">
                    <h4><AlertTriangle size={14} /> Foods to Avoid</h4>
                    <div className="tag-list">
                      {(c.foods_to_avoid || []).map((f, i) => <span key={i} className="tag avoid-tag">{f}</span>)}
                    </div>
                  </div>

                  <div className="detail-section eat">
                    <h4><Apple size={14} /> Recommended Foods</h4>
                    <div className="tag-list">
                      {(c.foods_to_eat || []).map((f, i) => <span key={i} className="tag eat-tag">{f}</span>)}
                    </div>
                  </div>

                  {c.medicines?.length > 0 && (
                    <div className="detail-section medicines">
                      <h4><Pill size={14} /> Medicines</h4>
                      <div className="medicine-list">
                        {c.medicines.map((m, i) => (
                          <div key={i} className="medicine-item">
                            <strong>{m.name}</strong>
                            <span>{m.purpose}</span>
                            {m.dosage && <small>Dosage: {m.dosage}</small>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {c.treatments?.length > 0 && (
                    <div className="detail-section treatments">
                      <h4>Treatments & Lifestyle</h4>
                      <ul>{c.treatments.map((t, i) => <li key={i}>{t}</li>)}</ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteTarget && (
        <div className="modal-overlay" onClick={() => setDeleteTarget(null)}>
          <div className="confirm-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Remove Condition?</h3>
            <p>This will delete the condition and all associated dietary research.</p>
            <div className="confirm-actions">
              <button className="btn-outline" onClick={() => setDeleteTarget(null)}>Cancel</button>
              <button className="btn-danger" onClick={() => handleDelete(deleteTarget)}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
