import React, { useState, useEffect } from 'react';
import { TrendingDown, IndianRupee, Loader2 } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { getFinanceTransactions, setSalary as saveSalary } from '../services/api';
import TopBar from '../components/TopBar';
import './Finance.css';

/* ── Spending by Category Data ── */
const spendingData = [
  { name: 'Groceries', amount: 6200 },
  { name: 'Dairy', amount: 2800 },
  { name: 'Meat & Fish', amount: 1900 },
  { name: 'Fruits', amount: 1050 },
  { name: 'Beverages', amount: 500 },
];

const barColors = ['#4ade80', '#22c55e', '#16a34a', '#15803d', '#166534'];

function formatINR(num) {
  return num.toLocaleString('en-IN');
}

function formatDate(iso) {
  if (!iso) return '--';
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function getTxChipClass(category) {
  const map = {
    Groceries: 'tx-chip-groceries',
    Produce: 'tx-chip-produce',
    Dairy: 'tx-chip-dairy',
    Mixed: 'tx-chip-mixed',
  };
  return map[category] || 'tx-chip-groceries';
}

/* ── Custom Recharts Tooltip ── */
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div
      style={{
        background: '#1a1a2e',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 8,
        padding: '10px 14px',
        fontSize: '0.825rem',
      }}
    >
      <div style={{ color: '#e5e2e1', fontWeight: 600, marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ color: '#4ade80' }}>
        Rs. {formatINR(payload[0].value)}
      </div>
    </div>
  );
}

export default function Finance() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [salaryInput, setSalaryInput] = useState(1800000);

  useEffect(() => {
    async function load() {
      try {
        const data = await getFinanceTransactions();
        setTransactions(data.transactions || []);
      } catch { setTransactions([]); }
      setLoading(false);
    }
    load();
  }, []);

  // Compute spending chart from real transactions
  const catSpend = {};
  transactions.forEach((tx) => {
    const cat = tx.category || 'Other';
    catSpend[cat] = (catSpend[cat] || 0) + (tx.amount || 0);
  });
  const spendingData = Object.entries(catSpend)
    .map(([name, amount]) => ({ name, amount }))
    .sort((a, b) => b.amount - a.amount);
  const totalSpent = transactions.reduce((s, t) => s + (t.amount || 0), 0);

  // Tax computation (New Regime FY 2026-27)
  const grossSalary = salaryInput;
  const standardDeduction = 75000;
  const taxableIncome = grossSalary - standardDeduction;
  const slabs = [
    { range: '0 - 4,00,000', rate: '0%', tax: Math.min(Math.max(taxableIncome, 0), 400000) * 0 },
    { range: '4,00,001 - 8,00,000', rate: '5%', tax: Math.min(Math.max(taxableIncome - 400000, 0), 400000) * 0.05 },
    { range: '8,00,001 - 12,00,000', rate: '10%', tax: Math.min(Math.max(taxableIncome - 800000, 0), 400000) * 0.10 },
    { range: '12,00,001 - 16,00,000', rate: '15%', tax: Math.min(Math.max(taxableIncome - 1200000, 0), 400000) * 0.15 },
    { range: '16,00,001+', rate: '20%', tax: Math.max(taxableIncome - 1600000, 0) * 0.20 },
  ];
  const taxBeforeCess = Math.round(slabs.reduce((s, sl) => s + sl.tax, 0));
  const healthCess = Math.round(taxBeforeCess * 0.04);
  const totalTax = taxBeforeCess + healthCess;
  const netAnnual = grossSalary - totalTax;
  const netMonthly = Math.round(netAnnual / 12);

  const handleSalaryBlur = () => {
    saveSalary(Math.round(salaryInput / 12), 'new').catch(() => {});
  };

  return (
    <div className="finance-page">
      <TopBar title="Finance" subtitle="Track spending and compute taxes" />

      {/* ── Top Stats Row ── */}
      <div className="finance-stats-row">
        {/* Monthly Spending */}
        <div className="finance-stat-card">
          <span className="stat-label">Monthly Spending</span>
          <span className="stat-value">Rs. {formatINR(totalSpent)}</span>
          <span className="stat-change negative">
            <TrendingDown size={14} />
            {transactions.length} transactions
          </span>
        </div>

        {/* Salary / Annual Income */}
        <div className="finance-stat-card">
          <span className="stat-label">Annual Salary</span>
          <div className="salary-input-wrapper">
            <input
              type="number"
              className="salary-input"
              value={salaryInput}
              onChange={(e) => setSalaryInput(Number(e.target.value) || 0)}
              onBlur={handleSalaryBlur}
              min="0"
            />
          </div>
          <span className="salary-input-hint">Type to recalculate tax</span>
        </div>

        {/* Estimated Tax */}
        <div className="finance-stat-card">
          <span className="stat-label">Estimated Tax</span>
          <span className="stat-value">Rs. {formatINR(totalTax)}</span>
          <span className="stat-subtitle">
            Effective rate: {grossSalary > 0 ? ((totalTax / grossSalary) * 100).toFixed(1) : '0'}%
          </span>
        </div>
      </div>

      {/* -- Two Columns -- */}
      <div className="finance-columns">
        {/* Spending by Category */}
        <div className="glass-card spending-chart-card">
          <h3 className="glass-card-title">Spending by Category</h3>
          <div className="spending-chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={spendingData}
                layout="vertical"
                margin={{ top: 0, right: 20, bottom: 0, left: 10 }}
              >
                <XAxis
                  type="number"
                  tick={{ fill: '#9ca3af', fontSize: 12 }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
                  tickLine={false}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: '#e5e2e1', fontSize: 13 }}
                  axisLine={false}
                  tickLine={false}
                  width={90}
                />
                <Tooltip
                  content={<CustomTooltip />}
                  cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                />
                <Bar dataKey="amount" radius={[0, 6, 6, 0]} barSize={28}>
                  {spendingData.map((_, i) => (
                    <Cell key={i} fill={barColors[i]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Tax Breakdown */}
        <div className="glass-card tax-card">
          <h3 className="glass-card-title">Tax Breakdown</h3>
          <p className="glass-card-subtitle">New Regime FY 2026-27</p>
          <table className="tax-table">
            <tbody>
              <tr className="tax-row-highlight">
                <td>Gross Salary</td>
                <td>Rs. {formatINR(grossSalary)}</td>
              </tr>
              <tr className="tax-deduction">
                <td>Standard Deduction</td>
                <td>- Rs. {formatINR(standardDeduction)}</td>
              </tr>
              <tr className="tax-row-highlight">
                <td>Taxable Income</td>
                <td>Rs. {formatINR(taxableIncome)}</td>
              </tr>

              {/* Slab header */}
              <tr className="tax-row-header">
                <td>Income Slab</td>
                <td>Tax</td>
              </tr>

              {slabs.map((slab, i) => (
                <tr key={i} className={`tax-row-slab ${slab.tax === 0 ? 'tax-nil' : ''}`}>
                  <td>{slab.range} ({slab.rate})</td>
                  <td>{slab.tax === 0 ? 'Nil' : `Rs. ${formatINR(slab.tax)}`}</td>
                </tr>
              ))}

              <tr className="tax-row-highlight">
                <td>Tax before Cess</td>
                <td>Rs. {formatINR(taxBeforeCess)}</td>
              </tr>
              <tr className="tax-nil">
                <td>Rebate u/s 87A</td>
                <td>Not applicable</td>
              </tr>
              <tr className="tax-row-cess">
                <td>Health & Education Cess (4%)</td>
                <td>Rs. {formatINR(healthCess)}</td>
              </tr>
              <tr className="tax-row-total">
                <td>Total Tax Liability</td>
                <td>Rs. {formatINR(totalTax)}</td>
              </tr>
              <tr className="tax-row-net">
                <td>Net Monthly Take-Home</td>
                <td>Rs. {formatINR(netMonthly)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Recent Transactions ── */}
      <div className="glass-card transactions-card">
        <h3 className="glass-card-title">Recent Transactions</h3>
        <table className="transactions-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Merchant</th>
              <th>Amount</th>
              <th>Category</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx, i) => (
              <tr key={tx._id || i}>
                <td>{formatDate(tx.date)}</td>
                <td style={{ fontWeight: 500 }}>{tx.merchant}</td>
                <td className="transaction-amount">Rs. {formatINR(tx.amount)}</td>
                <td>
                  <span className={`tx-chip ${getTxChipClass(tx.category)}`}>
                    {tx.category}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
