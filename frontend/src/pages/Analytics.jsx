import React, { useState, useEffect } from 'react';
import {
  Leaf, TrendingDown, AlertTriangle, TrendingUp, Apple,
  RefreshCw, Shield, ArrowRightLeft, Loader2, Clock, Package,
} from 'lucide-react';
import {
  BarChart, Bar, AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts';
import {
  getCarbonFootprint, getBehaviorInsights, getNutritionReport,
  getRestockAlerts, getWarranties,
} from '../services/api';
import TopBar from '../components/TopBar';
import './Analytics.css';

const TABS = [
  { id: 'carbon', label: 'Carbon Footprint', icon: Leaf },
  { id: 'behavior', label: 'Behavior', icon: TrendingUp },
  { id: 'nutrition', label: 'Nutrition', icon: Apple },
  { id: 'restock', label: 'Restock', icon: RefreshCw },
  { id: 'warranties', label: 'Warranties', icon: Shield },
];

const SWAPS = [
  { from: 'Chicken', to: 'Tofu', save: 3.0 },
  { from: 'Butter', to: 'Olive Oil', save: 6.0 },
  { from: 'Cheese', to: 'Paneer', save: 13.0 },
  { from: 'Rice', to: 'Oats', save: 2.4 },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="chart-tooltip glass-static">
        <span className="tooltip-label">{label}</span>
        <span className="tooltip-value">{payload[0].value} kg CO2</span>
      </div>
    );
  }
  return null;
};

function formatDate(iso) {
  if (!iso) return '--';
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function daysUntil(iso) {
  if (!iso) return '--';
  const diff = (new Date(iso) - new Date()) / (1000 * 60 * 60 * 24);
  return Math.max(0, Math.ceil(diff));
}

/* =============== CARBON TAB =============== */
function CarbonTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCarbonFootprint()
      .then((d) => setData(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  const entries = data?.carbon_log || [];
  const monthlyTrend = entries.map((e) => ({
    month: e.month || e.date || '',
    co2: e.total_kg_co2 || e.co2 || 0,
  })).reverse();

  const latest = entries[0] || {};
  const prev = entries[1] || {};
  const currentCo2 = latest.total_kg_co2 || 0;
  const prevCo2 = prev.total_kg_co2 || 1;
  const pctChange = prevCo2 > 0 ? (((currentCo2 - prevCo2) / prevCo2) * 100).toFixed(0) : 0;

  const breakdown = latest.breakdown || {};
  const carbonByCategory = Object.entries(breakdown)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="analytics-content stagger-2">
      <div className="analytics-stats">
        <div className="glass a-stat-card">
          <div className="a-stat-icon" style={{ color: 'var(--primary)' }}><Leaf size={20} strokeWidth={1.8} /></div>
          <span className="label-sm">This Month</span>
          <span className="headline-md">{currentCo2.toFixed(1)} kg</span>
          <span className="label-sm text-green">CO2 emissions</span>
        </div>
        <div className="glass a-stat-card">
          <div className="a-stat-icon" style={{ color: 'var(--primary)' }}><TrendingDown size={20} strokeWidth={1.8} /></div>
          <span className="label-sm">vs Last Month</span>
          <span className={`headline-md ${Number(pctChange) <= 0 ? 'text-green' : 'text-amber'}`}>{pctChange}%</span>
          <span className="label-sm text-green">{Number(pctChange) <= 0 ? 'Improvement' : 'Increase'}</span>
        </div>
        <div className="glass a-stat-card">
          <div className="a-stat-icon" style={{ color: 'var(--tertiary)' }}><AlertTriangle size={20} strokeWidth={1.8} /></div>
          <span className="label-sm">Top Emitter</span>
          <span className="headline-sm">{carbonByCategory[0]?.name || 'N/A'}</span>
          <span className="label-sm text-amber">{carbonByCategory[0]?.value?.toFixed(1) || 0} kg CO2</span>
        </div>
      </div>

      <div className="analytics-two-col">
        <div className="glass card-section">
          <span className="headline-sm">Carbon by Category</span>
          <div style={{ width: '100%', height: 260 }}>
            {carbonByCategory.length > 0 ? (
              <ResponsiveContainer>
                <BarChart data={carbonByCategory} layout="vertical" barSize={18}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} unit=" kg" />
                  <YAxis type="category" dataKey="name" tick={{ fill: '#e5e2e1', fontSize: 13, fontWeight: 500 }} axisLine={false} tickLine={false} width={70} />
                  <Tooltip content={<CustomTooltip />} cursor={false} />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]} fill="#4ade80" />
                </BarChart>
              </ResponsiveContainer>
            ) : <EmptyState msg="No carbon data yet" />}
          </div>
        </div>

        <div className="glass card-section">
          <span className="headline-sm">Green Swap Suggestions</span>
          <div className="swap-list">
            {SWAPS.map((s, i) => (
              <div key={i} className="swap-row">
                <div className="swap-info">
                  <ArrowRightLeft size={16} style={{ color: 'var(--primary)', flexShrink: 0 }} />
                  <div>
                    <span className="swap-label">Swap <strong>{s.from}</strong> for <strong>{s.to}</strong></span>
                    <span className="label-sm text-green">Save {s.save} kg CO2/kg</span>
                  </div>
                </div>
                <button className="btn btn-secondary btn-sm">Apply</button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {monthlyTrend.length > 1 && (
        <div className="glass card-section">
          <span className="headline-sm">Monthly Carbon Trend</span>
          <div style={{ width: '100%', height: 240 }}>
            <ResponsiveContainer>
              <AreaChart data={monthlyTrend}>
                <defs>
                  <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4ade80" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#4ade80" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" tick={{ fill: '#9ca3af', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false} unit=" kg" />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="co2" stroke="#4ade80" strokeWidth={2} fill="url(#greenGrad)"
                  dot={{ r: 4, fill: '#4ade80', stroke: '#0a0a0a', strokeWidth: 2 }}
                  activeDot={{ r: 6, fill: '#4ade80' }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

/* =============== BEHAVIOR TAB =============== */
function BehaviorTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBehaviorInsights()
      .then((d) => setData(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  const breakdown = data?.category_breakdown || {};
  const totalSpent = data?.total_spent || 0;
  const chartData = Object.entries(breakdown)
    .map(([name, amount]) => ({ name, amount }))
    .sort((a, b) => b.amount - a.amount);

  return (
    <div className="analytics-content stagger-2">
      <div className="analytics-stats">
        <div className="glass a-stat-card">
          <div className="a-stat-icon" style={{ color: 'var(--secondary)' }}><TrendingUp size={20} strokeWidth={1.8} /></div>
          <span className="label-sm">Total Spent</span>
          <span className="headline-md">Rs. {totalSpent.toLocaleString('en-IN')}</span>
          <span className="label-sm text-secondary">All time</span>
        </div>
        <div className="glass a-stat-card">
          <div className="a-stat-icon" style={{ color: 'var(--primary)' }}><Package size={20} strokeWidth={1.8} /></div>
          <span className="label-sm">Categories</span>
          <span className="headline-md">{Object.keys(breakdown).length}</span>
          <span className="label-sm text-green">Tracked</span>
        </div>
      </div>

      <div className="glass card-section">
        <span className="headline-sm">Spending by Category</span>
        <div style={{ width: '100%', height: 280 }}>
          {chartData.length > 0 ? (
            <ResponsiveContainer>
              <BarChart data={chartData} layout="vertical" barSize={22}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 12 }} axisLine={false} tickLine={false}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <YAxis type="category" dataKey="name" tick={{ fill: '#e5e2e1', fontSize: 13 }} axisLine={false} tickLine={false} width={90} />
                <Tooltip cursor={false} content={({ active, payload, label }) =>
                  active && payload?.[0] ? (
                    <div className="chart-tooltip glass-static">
                      <span className="tooltip-label">{label}</span>
                      <span className="tooltip-value">Rs. {payload[0].value.toLocaleString('en-IN')}</span>
                    </div>
                  ) : null
                } />
                <Bar dataKey="amount" radius={[0, 6, 6, 0]} fill="#818cf8" />
              </BarChart>
            </ResponsiveContainer>
          ) : <EmptyState msg="No spending data yet" />}
        </div>
      </div>
    </div>
  );
}

/* =============== NUTRITION TAB =============== */
function NutritionTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getNutritionReport()
      .then((d) => setData(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  const logs = data?.nutrition_log || [];

  return (
    <div className="analytics-content stagger-2">
      <div className="glass card-section">
        <span className="headline-sm">Recent Nutrition Log</span>
        {logs.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th><th>Calories</th><th>Protein</th><th>Carbs</th><th>Fat</th><th>Fiber</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((row, i) => (
                <tr key={row._id || i}>
                  <td>{formatDate(row.date)}</td>
                  <td><strong>{row.calories || 0}</strong></td>
                  <td>{row.protein_g || 0}g</td>
                  <td>{row.carbs_g || 0}g</td>
                  <td>{row.fat_g || 0}g</td>
                  <td>{row.fiber_g || 0}g</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <EmptyState msg="No nutrition data yet" />}
      </div>
    </div>
  );
}

/* =============== RESTOCK TAB =============== */
function RestockTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRestockAlerts()
      .then((d) => setData(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  const items = data?.restock_items || [];

  return (
    <div className="analytics-content stagger-2">
      <div className="analytics-stats">
        <div className="glass a-stat-card">
          <div className="a-stat-icon" style={{ color: 'var(--tertiary)' }}><AlertTriangle size={20} strokeWidth={1.8} /></div>
          <span className="label-sm">Items to Restock</span>
          <span className="headline-md">{items.length}</span>
          <span className="label-sm text-amber">Need attention</span>
        </div>
      </div>

      <div className="glass card-section">
        <span className="headline-sm">Low Stock / Expiring Items</span>
        {items.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr><th>Item</th><th>Category</th><th>Quantity</th><th>Unit</th><th>Status</th><th>Expiry</th></tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={item._id || i}>
                  <td style={{ fontWeight: 500 }}>{item.name}</td>
                  <td>{item.category}</td>
                  <td>{item.quantity}</td>
                  <td>{item.unit}</td>
                  <td><span className={`status-chip status-${item.status}`}><span className="status-dot" />{item.status}</span></td>
                  <td>{formatDate(item.expiry_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <EmptyState msg="Everything is well-stocked" />}
      </div>
    </div>
  );
}

/* =============== WARRANTIES TAB =============== */
function WarrantiesTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getWarranties()
      .then((d) => setData(d))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;

  const warranties = data?.warranties || [];

  return (
    <div className="analytics-content stagger-2">
      <div className="analytics-stats">
        <div className="glass a-stat-card">
          <div className="a-stat-icon" style={{ color: 'var(--primary)' }}><Shield size={20} strokeWidth={1.8} /></div>
          <span className="label-sm">Active Warranties</span>
          <span className="headline-md">{warranties.length}</span>
          <span className="label-sm text-green">Tracked</span>
        </div>
      </div>

      <div className="glass card-section">
        <span className="headline-sm">Your Warranties</span>
        {warranties.length > 0 ? (
          <table className="data-table">
            <thead>
              <tr><th>Product</th><th>Brand</th><th>Purchase</th><th>Expires</th><th>Days Left</th><th>Status</th></tr>
            </thead>
            <tbody>
              {warranties.map((w, i) => {
                const days = daysUntil(w.warranty_end);
                const status = days === '--' ? 'unknown' : days < 30 ? 'expiring' : 'fresh';
                return (
                  <tr key={w._id || i}>
                    <td style={{ fontWeight: 500 }}>{w.product_name}</td>
                    <td>{w.brand}</td>
                    <td>{formatDate(w.purchase_date)}</td>
                    <td>{formatDate(w.warranty_end)}</td>
                    <td>{days}</td>
                    <td><span className={`status-chip status-${status}`}><span className="status-dot" />{status === 'expiring' ? 'Expiring Soon' : 'Active'}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : <EmptyState msg="No warranties tracked yet" />}
      </div>
    </div>
  );
}

/* =============== SHARED COMPONENTS =============== */
function LoadingState() {
  return (
    <div className="placeholder-tab glass stagger-2" style={{ display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'center' }}>
      <Loader2 size={20} className="spin" /> Loading data...
    </div>
  );
}

function EmptyState({ msg }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40, color: 'var(--text-muted)' }}>
      {msg}
    </div>
  );
}

/* =============== MAIN ANALYTICS PAGE =============== */
export default function Analytics() {
  const [activeTab, setActiveTab] = useState('carbon');

  return (
    <div className="analytics-page">
      <TopBar title="Analytics" subtitle="Insights across all your data" />

      <div className="tab-bar glass stagger-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`tab-item ${activeTab === id ? 'tab-item--active' : ''}`}
            onClick={() => setActiveTab(id)}
          >
            <Icon size={16} strokeWidth={1.8} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {activeTab === 'carbon' && <CarbonTab />}
      {activeTab === 'behavior' && <BehaviorTab />}
      {activeTab === 'nutrition' && <NutritionTab />}
      {activeTab === 'restock' && <RestockTab />}
      {activeTab === 'warranties' && <WarrantiesTab />}
    </div>
  );
}
