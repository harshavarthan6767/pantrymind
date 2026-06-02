import React, { useState, useEffect } from 'react';
import {
  Package, AlertTriangle, IndianRupee, Leaf,
  FileText, Clock, ShoppingCart, ArrowRight, Loader2,
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { getDashboardStats, getRestockAlerts, getNutritionReport } from '../services/api';
import TopBar from '../components/TopBar';
import ScanReceiptModal from '../components/ScanReceiptModal';
import './Dashboard.css';

function formatAmount(n) {
  if (!n) return '0';
  return n.toLocaleString('en-IN');
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
}

function daysUntilExpiry(iso) {
  if (!iso) return 99;
  const diff = (new Date(iso) - new Date()) / (1000 * 60 * 60 * 24);
  return Math.max(0, Math.ceil(diff));
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [restock, setRestock] = useState([]);
  const [nutrition, setNutrition] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [s, r, n] = await Promise.all([
          getDashboardStats(),
          getRestockAlerts(),
          getNutritionReport(),
        ]);
        setStats(s);
        setRestock(r.restock_items || []);
        setNutrition(n.nutrition_log?.[0] || null);
      } catch (err) {
        console.error('[Dashboard]', err);
      }
      setLoading(false);
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="dashboard">
        <TopBar title="Dashboard" subtitle="Overview of your household" />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 100, gap: 12, color: 'var(--text-muted)' }}>
          <Loader2 size={20} className="spin" /> Loading dashboard...
        </div>
      </div>
    );
  }

  const totalItems = stats?.total_items || 0;
  const expiringSoon = stats?.expiring_soon || 0;
  const monthlySpending = stats?.monthly_spending || 0;
  const recentReceipts = stats?.recent_receipts || [];
  const expiringItems = stats?.expiring_items || [];

  const STATS_DATA = [
    { icon: Package, label: 'Total Items', value: String(totalItems), sub: `${totalItems} tracked`, color: 'var(--primary)' },
    { icon: AlertTriangle, label: 'Expiring Soon', value: String(expiringSoon), sub: 'Next 3 days', color: 'var(--tertiary)' },
    { icon: IndianRupee, label: 'This Month', value: formatAmount(monthlySpending), sub: 'Grocery spend', color: 'var(--primary)' },
    { icon: Leaf, label: 'CO2 Saved', value: '2.3 kg', sub: 'This month', color: 'var(--primary)' },
  ];

  const cal = nutrition?.calories || 0;
  const target = nutrition?.target_calories || 1800;
  const donutData = [
    { name: 'Consumed', value: cal, fill: '#4ade80' },
    { name: 'Remaining', value: Math.max(0, target - cal), fill: 'rgba(255,255,255,0.05)' },
  ];

  const macros = [
    { name: 'Protein', value: nutrition?.protein_g || 0, max: 60, fill: '#4ade80' },
    { name: 'Carbs', value: nutrition?.carbs_g || 0, max: 225, fill: '#818cf8' },
    { name: 'Fat', value: nutrition?.fat_g || 0, max: 50, fill: '#fbbf24' },
  ];

  return (
    <div className="dashboard">
      <TopBar 
        title="Dashboard" 
        subtitle="Overview of your household"
        actions={
          <button className="btn btn-primary" onClick={() => setIsScanModalOpen(true)}>
            <Package size={18} />
            Scan Receipt
          </button>
        }
      />

      {isScanModalOpen && (
        <ScanReceiptModal 
          onClose={() => setIsScanModalOpen(false)} 
          onSuccess={() => window.location.reload()}
        />
      )}

      <section className="welcome glass stagger-1">
        <div className="welcome-bar" />
        <div>
          <h2 className="headline-lg">Good Evening, Harsh</h2>
          <p className="body-md text-secondary" style={{ marginTop: 6 }}>
            Your pantry has {totalItems} items. {expiringSoon > 0 ? `${expiringSoon} items expiring soon.` : 'All items fresh.'}
          </p>
        </div>
      </section>

      <section className="stats-row">
        {STATS_DATA.map((s, i) => (
          <div key={s.label} className={`stat-card glass stagger-${i + 2}`}>
            <div className="stat-icon" style={{ color: s.color }}><s.icon size={20} strokeWidth={1.8} /></div>
            <span className="label-sm">{s.label}</span>
            <span className="headline-md">{s.value}</span>
            <span className="label-sm" style={{ color: s.color }}>{s.sub}</span>
          </div>
        ))}
      </section>

      <section className="two-col stagger-6">
        {/* Recent Receipts */}
        <div className="glass card-section">
          <div className="card-header">
            <FileText size={18} strokeWidth={1.8} />
            <span className="headline-sm">Recent Receipts</span>
          </div>
          <div className="receipt-list">
            {recentReceipts.length > 0 ? recentReceipts.map((r, i) => (
              <div key={i} className="receipt-row">
                <div className="receipt-info">
                  <span className="receipt-store">{r.store}</span>
                  <span className="label-sm">{formatDate(r.date)} &middot; {r.items?.length || 0} items</span>
                </div>
                <span className="receipt-amount text-green">Rs. {formatAmount(r.total)}</span>
              </div>
            )) : (
              <p className="text-muted body-sm" style={{ padding: '20px 0' }}>No receipts yet</p>
            )}
          </div>
          <button className="view-all">View All <ArrowRight size={14} /></button>
        </div>

        {/* Expiring Soon */}
        <div className="glass card-section">
          <div className="card-header">
            <Clock size={18} strokeWidth={1.8} />
            <span className="headline-sm">Expiring Soon</span>
          </div>
          <div className="expiry-list">
            {expiringItems.length > 0 ? expiringItems.map((e, i) => {
              const days = daysUntilExpiry(e.expiry_date);
              const severity = days <= 1 ? 'expired' : 'expiring';
              const label = days <= 1 ? 'Expires Tomorrow' : `${days} days left`;
              return (
                <div key={i} className={`expiry-row expiry-${severity}`}>
                  <div className="expiry-info">
                    <span className="expiry-name">{e.name}</span>
                    <span className="label-sm">{days} day{days !== 1 ? 's' : ''} remaining</span>
                  </div>
                  <span className={`chip chip-${severity}`}>{label}</span>
                </div>
              );
            }) : (
              <p className="text-muted body-sm" style={{ padding: '20px 0' }}>No expiring items</p>
            )}
          </div>
        </div>
      </section>

      <section className="two-col stagger-6">
        {/* Nutrition Donut */}
        <div className="glass card-section">
          <div className="card-header">
            <span className="headline-sm">Daily Nutrition</span>
          </div>
          <div className="nutrition-wrap">
            <div className="donut-container">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie data={donutData} dataKey="value" cx="50%" cy="50%"
                    innerRadius={52} outerRadius={72} startAngle={90} endAngle={-270} strokeWidth={0}>
                    {donutData.map((entry, idx) => <Cell key={idx} fill={entry.fill} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="donut-center">
                <span className="donut-val">{formatAmount(cal)}</span>
                <span className="donut-label">/ {formatAmount(target)} cal</span>
              </div>
            </div>
            <div className="macro-list">
              {macros.map((n) => (
                <div key={n.name} className="macro-row">
                  <span className="macro-dot" style={{ background: n.fill }} />
                  <span className="macro-name">{n.name}</span>
                  <span className="macro-val" style={{ color: n.fill }}>{n.value}g</span>
                  <span className="text-muted label-sm">/ {n.max}g</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Restock Alerts */}
        <div className="glass card-section">
          <div className="card-header">
            <ShoppingCart size={18} strokeWidth={1.8} />
            <span className="headline-sm">Restock Alerts</span>
          </div>
          <div className="restock-list">
            {restock.length > 0 ? restock.slice(0, 5).map((r, i) => {
              const pct = r.quantity <= 1 ? 15 : 40;
              return (
                <div key={i} className="restock-row">
                  <div className="restock-info">
                    <span className="restock-name">{r.name}</span>
                    <span className="label-sm text-muted">{r.quantity} {r.unit} remaining</span>
                    <div className="restock-bar">
                      <div className="restock-fill" style={{
                        width: `${pct}%`,
                        background: pct < 20 ? 'var(--error)' : 'var(--tertiary)',
                      }} />
                    </div>
                  </div>
                  <button className="btn btn-secondary btn-sm">Add to List</button>
                </div>
              );
            }) : (
              <p className="text-muted body-sm" style={{ padding: '20px 0' }}>All stocked up</p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
