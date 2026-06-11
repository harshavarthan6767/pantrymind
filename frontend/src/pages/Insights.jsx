import React, { useState, useEffect } from 'react';
import { TrendingDown, Zap, Tv, Laptop, Refrigerator, Smartphone } from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import {
  getCarbonFootprint, getBehaviorInsights, getFinanceTransactions, setSalary as saveSalary
} from '../services/api';
import TopBar from '../components/TopBar';
import FinanceChatAssistant from '../components/FinanceChatAssistant';
import { MessageSquareText } from 'lucide-react';
import './Insights.css';

const CHART_COLORS = ['#7CAE82', '#E8956D', '#E8D5A3', '#A8916A', '#C47979', '#7A9DC4', '#C4B59A', '#8A7FC8'];

function formatDate(iso) {
  if (!iso) return '--';
  try {
    return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
  } catch { return '--'; }
}

const CustomTooltip = ({ active, payload, label, prefix = '' }) => {
  if (active && payload && payload.length) {
    return (
      <div className="chart-tooltip">
        <div className="tt-label">{label}</div>
        <div className="tt-value">{prefix}₹{Number(payload[0].value).toLocaleString('en-IN')}</div>
      </div>
    );
  }
  return null;
};

export default function Insights() {
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [salaryInput, setSalaryInput] = useState(1800000);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [state, setState] = useState({
    totalSpent: 0, avgWeek: 0, biggestDay: 0,
    spendingTrend: [],
    categoryData: [],
    carbonData: [],
    transactions: [],
  });

  useEffect(() => {
    async function loadAll() {
      setLoading(true);
      try {
        const [behavior, carbon, trans] = await Promise.allSettled([
          getBehaviorInsights(),
          getCarbonFootprint(),
          getFinanceTransactions(),
        ]);

        const beh = behavior.status === 'fulfilled' ? behavior.value : {};
        const carb = carbon.status === 'fulfilled' ? carbon.value : {};
        const tx = trans.status === 'fulfilled' ? trans.value : {};

        const totalSpent = beh.total_spent || 0;
        const catBreakdown = beh.category_breakdown || {};
        
        const txList = tx.transactions || [];
        const spendingTrend = txList.slice(0, 14).reverse().map((t) => ({
          name: formatDate(t.date),
          amount: Math.abs(t.amount || 0)
        }));
        
        const categoryData = Object.entries(catBreakdown)
          .map(([name, value]) => ({ name, value }))
          .sort((a, b) => b.value - a.value)
          .slice(0, 7);

        const carbLog = carb.carbon_log || [];
        let carbonData = [];
        if (carbLog.length > 0 && carbLog[0].breakdown) {
          carbonData = Object.entries(carbLog[0].breakdown)
            .map(([name, value]) => ({ name, value }))
            .sort((a, b) => b.value - a.value)
            .slice(0, 6);
        }

        const avgWeek = totalSpent > 0 ? Math.round(totalSpent / 4) : 0;
        const biggestDay = spendingTrend.reduce((max, d) => Math.max(max, d.amount), 0);

        setState({
          totalSpent,
          avgWeek,
          biggestDay,
          spendingTrend,
          categoryData,
          carbonData,
          transactions: txList.slice(0, 12),
        });

      } catch (e) {
        console.error('Insights load error:', e);
      }
      setLoading(false);
    }
    loadAll();
  }, []);

  const handleSalaryBlur = () => {
    saveSalary(Math.round(salaryInput / 12), 'new').catch(() => {});
  };

  // Tax computation
  const grossSalary = salaryInput;
  const standardDeduction = 75000;
  const taxableIncome = grossSalary - standardDeduction;
  const slabs = [
    { range: '0 - 4L', rate: '0%', tax: 0 },
    { range: '4L - 8L', rate: '5%', tax: Math.min(Math.max(taxableIncome - 400000, 0), 400000) * 0.05 },
    { range: '8L - 12L', rate: '10%', tax: Math.min(Math.max(taxableIncome - 800000, 0), 400000) * 0.10 },
    { range: '12L - 16L', rate: '15%', tax: Math.min(Math.max(taxableIncome - 1200000, 0), 400000) * 0.15 },
    { range: '16L+', rate: '20%', tax: Math.max(taxableIncome - 1600000, 0) * 0.20 },
  ];
  const taxBeforeCess = Math.round(slabs.reduce((s, sl) => s + sl.tax, 0));
  const healthCess = Math.round(taxBeforeCess * 0.04);
  const totalTax = taxBeforeCess + healthCess;
  const netMonthly = Math.round((grossSalary - totalTax) / 12);

  return (
    <>
      <div className="page-container insights-page animate-fade-rise">
        <TopBar title="Insights" subtitle="Combined analytics, spending, and financial overview" />
      
      <div className="insights-tabs">
        <button className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>Overview</button>
        <button className={`tab-btn ${activeTab === 'tax' ? 'active' : ''}`} onClick={() => setActiveTab('tax')}>Tax & Income</button>
      </div>

      <div className="insights-content">
        {activeTab === 'overview' && (
          <>
            <div className="fin-strip card">
              <div className="fin-stats">
                <div className="fin-block">
                  <div className="fin-label">Total Spent</div>
                  <div className="fin-value">₹{state.totalSpent.toLocaleString('en-IN')}</div>
                </div>
                <div className="fin-divider" />
                <div className="fin-block">
                  <div className="fin-label">Avg / Week</div>
                  <div className="fin-value">₹{state.avgWeek.toLocaleString('en-IN')}</div>
                </div>
                <div className="fin-divider" />
                <div className="fin-block">
                  <div className="fin-label">Biggest Day</div>
                  <div className="fin-value">₹{state.biggestDay.toLocaleString('en-IN')}</div>
                </div>
              </div>
            </div>

            <div className="charts-grid">
              <div className="chart-card full card">
                <h3 className="chart-title">Spending Over Time</h3>
                {loading ? <div className="skeleton" style={{height: 240}} /> : (
                  <ResponsiveContainer width="100%" height={240}>
                    <AreaChart data={state.spendingTrend} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                      <defs>
                        <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="var(--sage-500)" stopOpacity={0.25} />
                          <stop offset="100%" stopColor="var(--sage-500)" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="name" tick={{ fill: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip content={<CustomTooltip />} />
                      <Area type="monotone" dataKey="amount" stroke="var(--sage-500)" strokeWidth={2} fill="url(#sg)" dot={false} activeDot={{ r: 4, fill: 'var(--sage-500)' }} />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </div>

              <div className="chart-card card">
                <h3 className="chart-title">By Category</h3>
                {loading ? <div className="skeleton" style={{height: 240}} /> : state.categoryData.length > 0 ? (
                  <div className="pie-layout">
                    <div className="pie-wrap">
                      <ResponsiveContainer width="100%" height={180}>
                        <PieChart>
                          <Pie data={state.categoryData} innerRadius={45} outerRadius={75} paddingAngle={3} dataKey="value" stroke="none">
                            {state.categoryData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                          </Pie>
                          <Tooltip formatter={(v) => [`₹${v.toLocaleString('en-IN')}`, 'Spent']} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                ) : (
                  <div className="empty-chart">No spending data yet</div>
                )}
              </div>


            </div>

            <section className="ledger-section card">
              <h2 className="section-heading">Recent Transactions</h2>
              {loading ? <div className="skeleton" style={{height: 100}} /> : (
                <div className="ledger-list">
                  {state.transactions.map((tx, i) => (
                    <div key={i} className="ledger-row">
                      <div className="ledger-date">{formatDate(tx.date)}</div>
                      <div className="ledger-info">
                        <div className="ledger-name">{tx.description || tx.category || 'Transaction'}</div>
                        <div className="ledger-type">{tx.type === 'expense' ? 'Expense' : 'Income'}</div>
                      </div>
                      <div className={`ledger-amount ${tx.type === 'expense' ? 'expense' : 'income'}`}>
                        {tx.type === 'expense' ? '-' : '+'}₹{Math.abs(tx.amount || 0).toLocaleString('en-IN')}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </>
        )}

        {activeTab === 'tax' && (
          <div className="tax-grid">
            <div className="card tax-input-card">
              <h3 className="chart-title">Annual Salary</h3>
              <input
                type="number"
                className="salary-input"
                value={salaryInput}
                onChange={(e) => setSalaryInput(Number(e.target.value) || 0)}
                onBlur={handleSalaryBlur}
              />
              <div className="tax-summary">
                <div className="tax-summary-item">
                  <span>Estimated Tax</span>
                  <strong>₹{totalTax.toLocaleString('en-IN')}</strong>
                </div>
                <div className="tax-summary-item">
                  <span>Net Monthly</span>
                  <strong style={{color: 'var(--status-fresh)'}}>₹{netMonthly.toLocaleString('en-IN')}</strong>
                </div>
              </div>
            </div>

            <div className="card tax-breakdown-card">
              <h3 className="chart-title">Tax Breakdown (New Regime)</h3>
              <table className="tax-table">
                <tbody>
                  <tr><td>Gross Salary</td><td>₹{grossSalary.toLocaleString('en-IN')}</td></tr>
                  <tr><td>Standard Deduction</td><td>-₹{standardDeduction.toLocaleString('en-IN')}</td></tr>
                  <tr className="highlight"><td>Taxable Income</td><td>₹{Math.max(taxableIncome, 0).toLocaleString('en-IN')}</td></tr>
                  <tr><td colSpan="2" className="table-divider"></td></tr>
                  {slabs.map((slab, i) => (
                    <tr key={i}>
                      <td>{slab.range} ({slab.rate})</td>
                      <td>{slab.tax === 0 ? 'Nil' : `₹${slab.tax.toLocaleString('en-IN')}`}</td>
                    </tr>
                  ))}
                  <tr><td colSpan="2" className="table-divider"></td></tr>
                  <tr><td>Tax before Cess</td><td>₹{taxBeforeCess.toLocaleString('en-IN')}</td></tr>
                  <tr><td>Health & Education Cess (4%)</td><td>₹{healthCess.toLocaleString('en-IN')}</td></tr>
                  <tr className="highlight total"><td>Total Tax Liability</td><td>₹{totalTax.toLocaleString('en-IN')}</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
      </div>

      <button className="fab-chat" onClick={() => setIsChatOpen(true)}>
        <MessageSquareText size={24} />
      </button>

      <FinanceChatAssistant isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </>
  );
}
