import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const EVENT_ICONS = {
  session_start: '🚀',
  agent_transfer: '🔀',
  tool_call: '🔧',
  tool_result: '✅',
  approval_required: '⚠️',
  approval_decision: '👤',
  reflexion_check: '🔍',
  mcp_query: '📖',
  mcp_write_blocked: '🚫',
  memory_recall: '🧠',
  memory_save: '💾',
  final_response: '💬',
  session_end: '🏁',
  error: '❌',
};

const EVENT_COLORS = {
  session_start: '#6366f1',
  agent_transfer: '#8b5cf6',
  tool_call: '#3b82f6',
  tool_result: '#10b981',
  approval_required: '#f59e0b',
  approval_decision: '#06b6d4',
  reflexion_check: '#ec4899',
  mcp_query: '#64748b',
  mcp_write_blocked: '#ef4444',
  memory_recall: '#7c3aed',
  memory_save: '#7c3aed',
  final_response: '#059669',
  session_end: '#374151',
  error: '#dc2626',
};

function TraceEvent({ event, index }) {
  const [expanded, setExpanded] = useState(false);
  const icon = EVENT_ICONS[event.event_type] || '•';
  const color = EVENT_COLORS[event.event_type] || '#6b7280';
  const time = event.ts ? new Date(event.ts).toLocaleTimeString() : '';

  return (
    <div style={{ display: 'flex', gap: '12px', marginBottom: '8px' }}>
      {/* Timeline spine */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: '24px' }}>
        <div style={{
          width: '24px', height: '24px', borderRadius: '50%',
          backgroundColor: color, display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontSize: '11px', flexShrink: 0
        }}>
          {icon}
        </div>
        <div style={{ width: '2px', flex: 1, backgroundColor: '#e5e7eb', marginTop: '4px' }} />
      </div>

      {/* Event content */}
      <div style={{
        flex: 1, paddingBottom: '12px', cursor: 'pointer'
      }} onClick={() => setExpanded(!expanded)}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{
              fontWeight: '600', fontSize: '13px', color: color
            }}>
              {event.event_type.replace(/_/g, ' ')}
            </span>
            <span style={{ fontSize: '12px', color: '#9ca3af', marginLeft: '8px' }}>
              {event.agent}
            </span>
          </div>
          <span style={{ fontSize: '11px', color: '#9ca3af' }}>{time}</span>
        </div>

        {/* Inline preview */}
        <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>
          {event.data?.summary || event.data?.tool || event.data?.message_preview || event.data?.response_preview || ''}
        </div>

        {/* Expanded detail */}
        {expanded && (
          <pre style={{
            backgroundColor: '#f9fafb',
            borderRadius: '4px',
            padding: '8px',
            fontSize: '11px',
            color: '#374151',
            marginTop: '6px',
            overflowX: 'auto',
            whiteSpace: 'pre-wrap'
          }}>
            {JSON.stringify(event.data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

export default function TraceTimeline({ sessionId, autoRefresh = false }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [source, setSource] = useState('memory');

  const fetchTrace = useCallback(async () => {
    if (!sessionId) return;
    try {
      setLoading(true);
      const res = await axios.get(`${API_BASE}/traces/${sessionId}?source=${source}`);
      setEvents(res.data.events || []);
      setError(null);
    } catch (err) {
      setError('Could not load trace.');
    } finally {
      setLoading(false);
    }
  }, [sessionId, source]);

  useEffect(() => {
    fetchTrace();
  }, [fetchTrace]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchTrace, 2000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchTrace]);

  if (!sessionId) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#9ca3af' }}>
        Start a conversation to see the agent trace timeline.
      </div>
    );
  }

  return (
    <div style={{
      backgroundColor: '#fff',
      borderRadius: '8px',
      boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
      padding: '20px',
      fontFamily: 'Inter, sans-serif',
      maxHeight: '600px',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: '700', color: '#111827' }}>
            🧵 Agent Trace Timeline
          </h3>
          <p style={{ margin: '2px 0 0 0', fontSize: '11px', color: '#9ca3af' }}>
            session: {sessionId}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <select
            value={source}
            onChange={e => setSource(e.target.value)}
            style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '4px', border: '1px solid #e5e7eb' }}
          >
            <option value="memory">Live (memory)</option>
            <option value="db">Persistent (DB)</option>
          </select>
          <button
            onClick={fetchTrace}
            disabled={loading}
            style={{
              padding: '4px 10px', fontSize: '12px', borderRadius: '4px',
              border: '1px solid #e5e7eb', cursor: 'pointer', backgroundColor: '#fff'
            }}
          >
            {loading ? '…' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div style={{
        display: 'flex', gap: '16px', marginBottom: '16px',
        padding: '10px 12px', backgroundColor: '#f9fafb', borderRadius: '6px'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '18px', fontWeight: '700', color: '#6366f1' }}>{events.length}</div>
          <div style={{ fontSize: '10px', color: '#6b7280' }}>Events</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '18px', fontWeight: '700', color: '#3b82f6' }}>
            {events.filter(e => e.event_type === 'tool_call').length}
          </div>
          <div style={{ fontSize: '10px', color: '#6b7280' }}>Tool Calls</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '18px', fontWeight: '700', color: '#8b5cf6' }}>
            {new Set(events.filter(e => e.event_type === 'agent_transfer').map(e => e.data?.to_agent)).size}
          </div>
          <div style={{ fontSize: '10px', color: '#6b7280' }}>Agents Used</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '18px', fontWeight: '700', color: '#f59e0b' }}>
            {events.filter(e => e.event_type === 'approval_required').length}
          </div>
          <div style={{ fontSize: '10px', color: '#6b7280' }}>Approvals</div>
        </div>
      </div>

      {error && (
        <div style={{ color: '#ef4444', fontSize: '13px', marginBottom: '12px' }}>{error}</div>
      )}

      {/* Event timeline */}
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {events.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#9ca3af', padding: '20px' }}>
            No events yet.
          </div>
        ) : (
          events.map((event, i) => (
            <TraceEvent key={i} event={event} index={i} />
          ))
        )}
      </div>
    </div>
  );
}
