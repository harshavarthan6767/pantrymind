import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export default function ApprovalInbox() {
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchActions = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE}/approvals?status=pending`);
      setActions(response.data.actions || []);
      setError(null);
    } catch (err) {
      setError('Failed to load pending actions.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActions();
    // Poll every 10 seconds
    const interval = setInterval(fetchActions, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (actionId) => {
    try {
      await axios.post(`${API_BASE}/approvals/${actionId}/approve`);
      await axios.post(`${API_BASE}/approvals/${actionId}/execute`);
      fetchActions();
    } catch (err) {
      alert('Failed to approve action: ' + err.message);
    }
  };

  const handleReject = async (actionId) => {
    try {
      await axios.post(`${API_BASE}/approvals/${actionId}/reject`);
      fetchActions();
    } catch (err) {
      alert('Failed to reject action: ' + err.message);
    }
  };

  if (loading && actions.length === 0) {
    return null; // Don't show anything during initial load
  }

  if (error) {
    return null; // Fail silently — this is a background widget
  }

  if (actions.length === 0) {
    return null; // Don't show if empty
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      width: '350px',
      backgroundColor: '#fff',
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      borderRadius: '8px',
      overflow: 'hidden',
      zIndex: 1000,
      fontFamily: 'Inter, sans-serif'
    }}>
      <div style={{
        backgroundColor: '#f59e0b',
        color: '#fff',
        padding: '12px 16px',
        fontWeight: '600',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span>Pending Approvals ({actions.length})</span>
      </div>
      
      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
        {actions.map(action => (
          <div key={action._id} style={{
            padding: '16px',
            borderBottom: '1px solid #e5e7eb'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontWeight: '500', fontSize: '14px' }}>{action.agent_name}</span>
              <span style={{ 
                fontSize: '11px', 
                padding: '2px 6px', 
                borderRadius: '4px',
                backgroundColor: action.risk_level === 'high' ? '#fee2e2' : '#fef3c7',
                color: action.risk_level === 'high' ? '#991b1b' : '#92400e'
              }}>
                {action.risk_level.toUpperCase()} RISK
              </span>
            </div>
            
            <p style={{ fontSize: '13px', color: '#4b5563', margin: '0 0 12px 0' }}>
              {action.summary}
            </p>
            
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                onClick={() => handleApprove(action._id)}
                style={{
                  flex: 1,
                  padding: '6px 0',
                  backgroundColor: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: '500'
                }}>
                Approve
              </button>
              <button 
                onClick={() => handleReject(action._id)}
                style={{
                  flex: 1,
                  padding: '6px 0',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: '500'
                }}>
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
