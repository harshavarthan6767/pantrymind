import React, { useState, useEffect } from 'react';
import { Search, Plus, Pencil, Trash2, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { getInventory, addInventoryItem, updateInventoryItem, deleteInventoryItem } from '../services/api';
import TopBar from '../components/TopBar';
import ItemModal from '../components/ItemModal';
import ConfirmDialog from '../components/ConfirmDialog';
import './Inventory.css';

const categories = ['All Categories', 'Produce', 'Dairy', 'Grains', 'Spices', 'Meat', 'Beverages', 'Cooking'];
const sortOptions = ['Name', 'Expiry Date', 'Quantity', 'Category'];
const PAGE_SIZE = 8;

function getCategoryChipClass(cat) {
  return { Grains: 'chip-grains', Dairy: 'chip-dairy', Produce: 'chip-produce', Cooking: 'chip-cooking', Spices: 'chip-spices', Meat: 'chip-meat', Beverages: 'chip-beverages' }[cat] || '';
}

function getStatusLabel(s) {
  return { fresh: 'Fresh', expiring: 'Expiring', expired: 'Expired' }[s] || s;
}

function formatDate(iso) {
  if (!iso) return '--';
  return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function Inventory() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState('All Categories');
  const [sortBy, setSortBy] = useState('Name');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [editItem, setEditItem] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const loadItems = async () => {
    setLoading(true);
    try {
      const cat = selectedCategory === 'All Categories' ? null : selectedCategory;
      const data = await getInventory(cat);
      setItems(data.items || []);
    } catch { setItems([]); }
    setLoading(false);
  };

  useEffect(() => { loadItems(); }, [selectedCategory]);

  // -- Add Item --
  const handleAdd = async (formData) => {
    await addInventoryItem(formData);
    setShowAddModal(false);
    await loadItems();
  };

  // -- Edit Item --
  const handleEdit = async (formData) => {
    await updateInventoryItem(editItem._id, formData);
    setEditItem(null);
    await loadItems();
  };

  // -- Delete Item --
  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteInventoryItem(deleteTarget._id);
      setDeleteTarget(null);
      await loadItems();
    } finally { setDeleting(false); }
  };

  // Filter + sort
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
    <div className="inventory-page">
      <TopBar title="Inventory" subtitle={`${items.length} items in your pantry`} />

      <div className="filter-bar">
        <select value={selectedCategory} onChange={(e) => { setSelectedCategory(e.target.value); setCurrentPage(1); }}>
          {categories.map((c) => <option key={c}>{c}</option>)}
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          {sortOptions.map((o) => <option key={o}>{o}</option>)}
        </select>
        <div className="search-wrapper">
          <Search className="search-icon" />
          <input type="text" placeholder="Search items..." value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1); }} />
        </div>
        <button className="btn-add-item" type="button" onClick={() => setShowAddModal(true)}>
          <Plus /> Add Item
        </button>
      </div>

      <div className="inventory-table-card">
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60, gap: 12, color: 'var(--text-muted)' }}>
            <Loader2 size={20} className="spin" /> Loading from MongoDB...
          </div>
        ) : (
          <div className="inventory-table-wrapper">
            <table className="inventory-table">
              <thead>
                <tr>
                  <th>Item Name</th><th>Category</th><th>Quantity</th><th>Unit</th>
                  <th>Purchase Date</th><th>Expiry Date</th><th>Status</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {paged.map((item) => (
                  <tr key={item._id}>
                    <td style={{ fontWeight: 500 }}>{item.name}</td>
                    <td><span className={`chip ${getCategoryChipClass(item.category)}`}>{item.category}</span></td>
                    <td className="quantity-cell">{item.quantity}</td>
                    <td><span className="unit-label">{item.unit}</span></td>
                    <td>{formatDate(item.purchase_date)}</td>
                    <td>{formatDate(item.expiry_date)}</td>
                    <td>
                      <span className={`status-chip status-${item.status}`}>
                        <span className="status-dot" />{getStatusLabel(item.status)}
                      </span>
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button className="btn-action" type="button" onClick={() => setEditItem(item)} aria-label="Edit">
                          <Pencil />
                        </button>
                        <button className="btn-action btn-delete" type="button" onClick={() => setDeleteTarget(item)} aria-label="Delete">
                          <Trash2 />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {paged.length === 0 && (
                  <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No items found</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {!loading && totalPages > 1 && (
        <div className="pagination">
          <button className="page-nav" type="button" disabled={currentPage === 1} onClick={() => setCurrentPage((p) => p - 1)}>
            <ChevronLeft /> Previous
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((pg) => (
            <button key={pg} type="button" className={currentPage === pg ? 'active' : ''} onClick={() => setCurrentPage(pg)}>{pg}</button>
          ))}
          <button className="page-nav" type="button" disabled={currentPage === totalPages} onClick={() => setCurrentPage((p) => p + 1)}>
            Next <ChevronRight />
          </button>
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <ItemModal item={null} onClose={() => setShowAddModal(false)} onSave={handleAdd} />
      )}

      {/* Edit Modal */}
      {editItem && (
        <ItemModal item={editItem} onClose={() => setEditItem(null)} onSave={handleEdit} />
      )}

      {/* Delete Confirm */}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete Item"
          message={`Are you sure you want to delete "${deleteTarget.name}"? This cannot be undone.`}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}
    </div>
  );
}
