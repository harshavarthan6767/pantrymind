import React, { useState, useEffect } from 'react';
import { Search, Plus, Pencil, Trash2, ChevronLeft, ChevronRight, LayoutGrid, List, Brain, Clock, Wand2, ChevronDown, Sparkles, Image as ImageIcon } from 'lucide-react';
import { getInventory, addInventoryItem, updateInventoryItem, deleteInventoryItem, deleteMultipleInventoryItems, categorizeInventory, estimateExpiry, getAgentStatus } from '../services/api';
import ItemModal from '../components/ItemModal';
import ConfirmDialog from '../components/ConfirmDialog';
import TransparentImage from '../components/TransparentImage';
import './Inventory.css';

const CATEGORY_OPTIONS = [
  { label: 'All', value: null },
  { label: 'Produce', value: 'PRODUCE' },
  { label: 'Dairy & Eggs', value: 'DAIRY_EGGS' },
  { label: 'Meat', value: 'MEAT_SEAFOOD' },
  { label: 'Pantry', value: 'PANTRY_DRY' },
  { label: 'Frozen', value: 'FROZEN' },
  { label: 'Beverages', value: 'BEVERAGES' },
  { label: 'Snacks', value: 'SNACKS' },
  { label: 'Bakery', value: 'BAKERY' },
  { label: 'Other', value: 'OTHER' },
];
const sortOptions = ['Name', 'Expiry Date', 'Quantity', 'Category'];
const PAGE_SIZE = 12;

const CATEGORY_COLORS = {
  PRODUCE: 'var(--status-fresh)',
  DAIRY_EGGS: 'var(--sage-300)',
  MEAT_SEAFOOD: 'var(--status-expired)',
  PANTRY_DRY: 'var(--terra-300)',
  FROZEN: '#818cf8',
  BEVERAGES: '#7A9DC4',
  SNACKS: 'var(--status-warning)',
  BAKERY: 'var(--terra-500)',
  OTHER: 'var(--sage-100)',
  Groceries: 'var(--sage-300)',
};

function getCategoryColor(cat) {
  return CATEGORY_COLORS[cat] || 'var(--sage-300)';
}


function formatDate(iso) {
  if (!iso) return '--';
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
}

function daysUntilExpiry(iso) {
  if (!iso) return 99;
  const diff = (new Date(iso) - new Date()) / (1000 * 60 * 60 * 24);
  return Math.ceil(diff);
}

export default function Inventory() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState(null); // null = 'All'
  const [sortBy, setSortBy] = useState('Name');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'table'

  // Modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false);
  const [aiWorking, setAiWorking] = useState(null); // 'categorize' | 'expiry' | 'images' | null
  const [aiMessage, setAiMessage] = useState('');
  const [showAiMenu, setShowAiMenu] = useState(false);
  const [agentStatus, setAgentStatus] = useState({ state: 'monitoring', item: null });

  const loadItems = async () => {
    setLoading(true);
    try {
      const data = await getInventory(selectedCategory);
      setItems(data.items || []);
    } catch { setItems([]); }
    setLoading(false);
  };

  useEffect(() => { loadItems(); }, [selectedCategory]);

  // Poll background agent status
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await getAgentStatus();
        setAgentStatus(res);
      } catch (err) {
        console.error("Failed to fetch agent status", err);
      }
    };
    fetchStatus();
    const intervalId = setInterval(fetchStatus, 3000);
    return () => clearInterval(intervalId);
  }, []);

  const handleAdd = async (formData) => {
    await addInventoryItem(formData);
    setShowAddModal(false);
    await loadItems();
  };

  const handleEdit = async (formData) => {
    await updateInventoryItem(editItem._id, formData);
    setEditItem(null);
    await loadItems();
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteInventoryItem(deleteTarget._id);
      setDeleteTarget(null);
      const newSelected = new Set(selectedIds);
      newSelected.delete(deleteTarget._id);
      setSelectedIds(newSelected);
      await loadItems();
    } finally { setDeleting(false); }
  };

  const handleBulkDelete = async () => {
    setDeleting(true);
    try {
      await deleteMultipleInventoryItems(Array.from(selectedIds));
      setSelectedIds(new Set());
      setShowBulkDeleteConfirm(false);
      await loadItems();
    } finally { setDeleting(false); }
  };

  let filtered = items.filter((item) =>
    item.name.toLowerCase().includes(searchQuery.toLowerCase())
  );
  if (sortBy === 'Name') filtered.sort((a, b) => a.name.localeCompare(b.name));
  else if (sortBy === 'Expiry Date') filtered.sort((a, b) => new Date(a.expiry_date) - new Date(b.expiry_date));
  else if (sortBy === 'Quantity') filtered.sort((a, b) => a.quantity - b.quantity);
  else if (sortBy === 'Category') filtered.sort((a, b) => a.category.localeCompare(b.category));

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  return (
    <div className="page-container animate-fade-rise">
      <header className="inv-header">
        <div>
          <h1 className="inv-title">Inventory</h1>
          <p className="inv-subtitle">{items.length} items in your pantry</p>
        </div>
        <div className="inv-header-actions">
          <div className="ai-dropdown-container">
            <button
              className="btn-outline ai-btn ai-assist-trigger"
              disabled={!!aiWorking}
              onClick={() => setShowAiMenu(!showAiMenu)}
            >
              <Sparkles size={16} className="text-accent" />
              <span>{aiWorking ? 'AI is Working...' : 'AI Assist'}</span>
              <ChevronDown size={16} />
            </button>
            
            {showAiMenu && (
              <div className="ai-dropdown-menu">
                <button
                  className="ai-dropdown-item"
                  onClick={async () => {
                    setShowAiMenu(false);
                    setAiWorking('categorize');
                    setAiMessage('');
                    try {
                      const res = await categorizeInventory();
                      setAiMessage(`✅ ${res.categorized} items re-categorized`);
                      await loadItems();
                    } catch { setAiMessage('❌ Categorization failed'); }
                    setAiWorking(null);
                    setTimeout(() => setAiMessage(''), 4000);
                  }}
                >
                  <Brain size={16} /> Auto-Categorize
                </button>
                <button
                  className="ai-dropdown-item"
                  onClick={async () => {
                    setShowAiMenu(false);
                    setAiWorking('expiry');
                    setAiMessage('');
                    try {
                      const res = await estimateExpiry();
                      setAiMessage(`✅ ${res.estimated} items updated with expiry`);
                      await loadItems();
                    } catch { setAiMessage('❌ Expiry estimation failed'); }
                    setAiWorking(null);
                    setTimeout(() => setAiMessage(''), 4000);
                  }}
                >
                  <Clock size={16} /> Estimate Expiry
                </button>

              </div>
            )}
          </div>
          <button className="btn-primary" onClick={() => setShowAddModal(true)}>
            <Plus size={18} /> Add Item
          </button>
        </div>
      </header>
      {aiMessage && <div className="ai-toast">{aiMessage}</div>}

      <div className="inv-filter-strip">
        <div className="category-scroll">
          {CATEGORY_OPTIONS.map((c) => (
            <button
              key={c.label}
              className={`cat-chip ${selectedCategory === c.value ? 'active' : ''}`}
              onClick={() => { setSelectedCategory(c.value); setCurrentPage(1); }}
            >
              {c.label}
            </button>
          ))}
        </div>
        
        <div className="inv-controls">
          <div className="search-box">
            <Search size={16} />
            <input 
              type="text" 
              placeholder="Search..." 
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }}
            />
          </div>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="sort-select">
            {sortOptions.map((o) => <option key={o}>{o}</option>)}
          </select>
          <div className="view-toggle">
            <button className={`view-btn ${viewMode === 'grid' ? 'active' : ''}`} onClick={() => setViewMode('grid')}><LayoutGrid size={16} /></button>
            <button className={`view-btn ${viewMode === 'table' ? 'active' : ''}`} onClick={() => setViewMode('table')}><List size={16} /></button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="skeleton" style={{ height: '400px', borderRadius: 'var(--radius-lg)' }} />
      ) : viewMode === 'grid' ? (
        <div className="inv-grid">
          {paged.map((item, i) => {
            const catColor = getCategoryColor(item.category);
            const days = daysUntilExpiry(item.expiry_date);
            const isExpired = days < 0;
            const isWarning = days >= 0 && days <= 3;
            
            return (
              <div key={item._id} className="inv-card" style={{ animationDelay: `${i * 30}ms` }}>
                <div className="card-top" style={{ backgroundColor: `${catColor}1A` }}>
                  {item.image_url ? (
                    <TransparentImage src={item.image_url} alt={item.name} className="inv-image" />
                  ) : (
                    <div className="ghost-letter" style={{ color: catColor }}>
                      {item.category.charAt(0)}
                    </div>
                  )}
                  <div className="card-status">
                    {isExpired ? <span className="pill expired">Expired</span> : 
                     isWarning ? <span className="pill warning">{days}d left</span> : 
                     <span className="pill fresh">Fresh</span>}
                  </div>
                </div>
                <div className="card-bottom">
                  <div className="item-name">{item.name}</div>
                  <div className="item-meta">
                    {item.quantity} {item.unit} &middot; Added {formatDate(item.purchase_date)}
                  </div>
                  <div className="card-actions-row">
                    <button className="icon-action-btn" title="Edit" onClick={() => setEditItem(item)}><Pencil size={14}/></button>
                    <button className="icon-action-btn trash" title="Delete" onClick={() => setDeleteTarget(item)}><Trash2 size={14}/></button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="inv-table-wrapper card">
          <table className="inv-table">
            <thead>
              <tr>
                <th>Name</th><th>Category</th><th>Quantity</th><th>Expiry</th><th>Status</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((item) => (
                <tr key={item._id}>
                  <td className="font-medium">{item.name}</td>
                  <td>
                    <span className="cat-pill" style={{ backgroundColor: `${getCategoryColor(item.category)}1A`, color: getCategoryColor(item.category) }}>
                      {item.category}
                    </span>
                  </td>
                  <td>{item.quantity} {item.unit}</td>
                  <td className="font-mono">{formatDate(item.expiry_date)}</td>
                  <td>
                    {daysUntilExpiry(item.expiry_date) < 0 ? (
                      <span className="text-expired">Expired</span>
                    ) : daysUntilExpiry(item.expiry_date) <= 3 ? (
                      <span className="text-warning">Expiring soon</span>
                    ) : (
                      <span className="text-fresh">Fresh</span>
                    )}
                  </td>
                  <td>
                    <div className="table-actions">
                      <button className="icon-action-btn" onClick={() => setEditItem(item)}><Pencil size={14}/></button>
                      <button className="icon-action-btn trash" onClick={() => setDeleteTarget(item)}><Trash2 size={14}/></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && totalPages > 1 && (
        <div className="pagination">
          <button className="page-btn" disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)}><ChevronLeft size={16} /></button>
          <span className="page-info">{currentPage} / {totalPages}</span>
          <button className="page-btn" disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => p + 1)}><ChevronRight size={16} /></button>
        </div>
      )}

      {showAddModal && <ItemModal item={null} onClose={() => setShowAddModal(false)} onSave={handleAdd} />}
      {editItem && <ItemModal item={editItem} onClose={() => setEditItem(null)} onSave={handleEdit} />}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete Item"
          message={`Are you sure you want to delete "${deleteTarget.name}"?`}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}

      {/* Live Agent Status Indicator */}
      <div className={`agent-status-bar ${agentStatus?.state}`}>
        {agentStatus?.state === 'generating' ? (
          <>
            <Sparkles size={16} className="spin-slow" />
            <span>Agent generating image for <strong>'{agentStatus.item}'</strong>...</span>
          </>
        ) : agentStatus?.state === 'monitoring' ? (
          <>
            <Brain size={16} className="pulse-slow" />
            <span>Agent monitoring pantry for missing images...</span>
          </>
        ) : null}
      </div>
    </div>
  );
}
