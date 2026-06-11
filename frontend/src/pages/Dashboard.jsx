import React, { useState, useEffect } from 'react';
import {
  Package, AlertTriangle, Clock, TrendingUp, ScanLine, ChefHat, Plus, Activity
} from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { getDashboardStats, getRestockAlerts } from '../services/api';
import ScanReceiptModal from '../components/ScanReceiptModal';
import FinanceChatAssistant from '../components/FinanceChatAssistant';
import './Dashboard.css';
import { useNavigate } from 'react-router-dom';

function formatAmount(n) {
  if (!n) return '0';
  return n.toLocaleString('en-IN');
}

function daysUntilExpiry(iso) {
  if (!iso) return 99;
  const diff = (new Date(iso) - new Date()) / (1000 * 60 * 60 * 24);
  return Math.ceil(diff);
}

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'morning';
  if (hour < 18) return 'afternoon';
  return 'evening';
}

function EmptyPlant() {
  return (
    <div className="empty-state">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--sage-300)" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22c0-8 6-12 6-12s-4 1-6 5c-2-4-6-5-6-5s6 4 6 12"/>
        <path d="M12 22V12"/>
      </svg>
      <div className="empty-title">All clear — your pantry is thriving</div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [restock, setRestock] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatQuery, setChatQuery] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    async function load() {
      try {
        const [s, r] = await Promise.all([
          getDashboardStats(),
          getRestockAlerts(),
        ]);
        setStats(s);
        setRestock(r.restock_items || []);
      } catch (err) {
        console.error('[Dashboard]', err);
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="page-container">
        <div className="skeleton" style={{ height: '200px', borderRadius: 'var(--radius-lg)' }} />
      </div>
    );
  }

  const totalItems = stats?.total_items || 0;
  const expiringSoon = stats?.expiring_soon || 0;
  const monthlySpending = stats?.monthly_spending || 0;
  
  // Create mock trend data for sparklines
  const generateTrend = (base, volatility) => Array.from({length: 10}, () => ({ value: base + (Math.random() - 0.5) * volatility }));

  const STATS_DATA = [
    { 
      label: 'TOTAL ITEMS', 
      icon: Package, 
      value: String(totalItems), 
      color: 'var(--sage-500)', 
      trend: generateTrend(totalItems, 5) 
    },
    { 
      label: 'EXPIRING SOON', 
      icon: Clock, 
      value: String(expiringSoon), 
      color: 'var(--status-warning)', 
      trend: generateTrend(expiringSoon, 2) 
    },
    { 
      label: 'EXPIRED', 
      icon: AlertTriangle, 
      value: '0', 
      color: 'var(--status-expired)', 
      trend: generateTrend(0, 1) 
    },
    { 
      label: 'MONTHLY SPEND', 
      icon: TrendingUp, 
      value: `₹${formatAmount(monthlySpending)}`, 
      color: 'var(--text-primary)', 
      trend: generateTrend(monthlySpending, 500) 
    },
  ];

  const greetingTime = getGreeting();
  const subMessage = expiringSoon > 0 
    ? `${expiringSoon} items need your attention soon.` 
    : 'Your pantry is in good shape today.';

  const attentionItems = restock.slice(0, 4);
  const recentEvents = [
    { text: 'Scanned Reliance receipt · 14 items added', time: '2 hours ago', type: 'scan' },
    { text: 'Consumed 2 Milk', time: '5 hours ago', type: 'consume' },
    { text: 'Bread expired', time: 'Yesterday', type: 'expire' },
  ];

  return (
    <div className="page-container animate-fade-rise">
      {isScanModalOpen && (
        <ScanReceiptModal 
          onClose={() => setIsScanModalOpen(false)} 
          onSuccess={() => window.location.reload()}
        />
      )}

      {/* Page Header */}
      <header className="dash-header">
        <h1 className="dash-title">
          Good <span className="dash-title-italic">{greetingTime}</span>, Harsh
        </h1>
        <p className="dash-subtitle">{subMessage}</p>
      </header>

      {/* Stat Row */}
      <section className="stat-grid">
        {STATS_DATA.map((s, idx) => (
          <div key={idx} className="stat-card" style={{ animationDelay: `${idx * 40}ms` }}>
            <div className="stat-top">
              <s.icon size={20} strokeWidth={1.5} color="var(--text-tertiary)" />
              <span className="stat-label">{s.label}</span>
            </div>
            <div className="stat-val" style={{ color: s.color }}>{s.value}</div>
            <div className="stat-sparkline">
              <ResponsiveContainer width="100%" height={40}>
                <LineChart data={s.trend}>
                  <Line type="monotone" dataKey="value" stroke={s.color} strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </section>

      {/* Middle Section */}
      <section className="dash-middle">
        {/* Needs Attention */}
        <div className="dash-col dash-col-left">
          <h2 className="section-title">Needs Attention</h2>
          {attentionItems.length > 0 ? (
            <div className="alert-list">
              {attentionItems.map((item, i) => {
                const days = daysUntilExpiry(item.expiry_date);
                const isExpired = days < 0;
                const statusColor = isExpired ? 'var(--status-expired)' : (days <= 3 ? 'var(--status-warning)' : 'var(--status-low)');
                const statusText = isExpired ? 'Expired' : (days <= 3 ? `Expires in ${days}d` : 'Low Stock');
                
                return (
                  <div key={i} className="alert-card" style={{ '--card-color': statusColor, animationDelay: `${i * 40}ms` }}>
                    <div className="alert-icon-wrap" style={{ backgroundColor: `${statusColor}1A` }}>
                      <Activity size={24} color={statusColor} />
                    </div>
                    <div className="alert-info">
                      <div className="alert-name">{item.name}</div>
                      <div className="alert-date" style={{ color: statusColor }}>{item.expiry_date || 'No date'}</div>
                    </div>
                    <div className="alert-badge" style={{ backgroundColor: statusColor }}>{statusText}</div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyPlant />
          )}
        </div>

        {/* Recent Activity */}
        <div className="dash-col dash-col-right">
          <h2 className="section-title">Recent</h2>
          <div className="timeline">
            {recentEvents.map((ev, i) => {
              const color = ev.type === 'scan' ? 'var(--sage-500)' : ev.type === 'consume' ? 'var(--terra-500)' : 'var(--status-warning)';
              return (
                <div key={i} className="timeline-item" style={{ animationDelay: `${i * 40}ms` }}>
                  <div className="timeline-dot" style={{ backgroundColor: color }} />
                  <div className="timeline-content">
                    <div className="timeline-text">{ev.text}</div>
                    <div className="timeline-time">{ev.time}</div>
                  </div>
                </div>
              );
            })}
            <button className="timeline-view-all" onClick={() => {
              setChatQuery("What were my recent activities?");
              setIsChatOpen(true);
            }}>View all</button>
          </div>
        </div>
      </section>

      {/* Quick Actions Strip */}
      <section className="quick-actions">
        <button className="action-btn action-primary" onClick={() => setIsScanModalOpen(true)}>
          <ScanLine size={16} /> <span>+ Scan Receipt</span>
        </button>
        <button className="action-btn action-outline" onClick={() => navigate('/kitchen')}>
          <ChefHat size={16} /> <span>Ask the Chef</span>
        </button>
      </section>

      <FinanceChatAssistant 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)} 
        autoSendQuery={chatQuery} 
      />
    </div>
  );
}
