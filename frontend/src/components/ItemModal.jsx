import React, { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import './ItemModal.css';

const CATEGORIES = ['Produce', 'Dairy', 'Grains', 'Spices', 'Meat', 'Beverages', 'Cooking'];
const UNITS = ['kg', 'g', 'L', 'ml', 'pcs'];
const STATUSES = ['fresh', 'expiring', 'expired'];

export default function ItemModal({ item, onClose, onSave }) {
  const isEdit = !!item;
  const [form, setForm] = useState({
    name: '',
    category: 'Produce',
    quantity: '',
    unit: 'kg',
    purchase_date: new Date().toISOString().split('T')[0],
    expiry_date: '',
    status: 'fresh',
    cost_per_unit: '',
    store: '',
  });
  const [saving, setSaving] = useState(false);
  const overlayRef = useRef(null);

  useEffect(() => {
    if (item) {
      setForm({
        name: item.name || '',
        category: item.category || 'Produce',
        quantity: item.quantity || '',
        unit: item.unit || 'kg',
        purchase_date: item.purchase_date ? item.purchase_date.split('T')[0] : '',
        expiry_date: item.expiry_date ? item.expiry_date.split('T')[0] : '',
        status: item.status || 'fresh',
        cost_per_unit: item.cost_per_unit || '',
        store: item.store || '',
      });
    }
  }, [item]);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.quantity) return;
    setSaving(true);
    try {
      await onSave({
        ...form,
        quantity: parseFloat(form.quantity),
        cost_per_unit: parseFloat(form.cost_per_unit) || 0,
        purchase_date: form.purchase_date ? new Date(form.purchase_date).toISOString() : null,
        expiry_date: form.expiry_date ? new Date(form.expiry_date).toISOString() : null,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target === overlayRef.current) onClose();
  };

  return (
    <div className="modal-overlay" ref={overlayRef} onClick={handleOverlayClick}>
      <div className="modal-card glass">
        <div className="modal-header">
          <h2 className="headline-sm">{isEdit ? 'Edit Item' : 'Add New Item'}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <form className="modal-form" onSubmit={handleSubmit}>
          {/* Row 1: Name + Category */}
          <div className="form-row">
            <label className="form-field">
              <span className="form-label">Item Name</span>
              <input
                type="text"
                value={form.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="e.g. Basmati Rice"
                required
                autoFocus
              />
            </label>
            <label className="form-field">
              <span className="form-label">Category</span>
              <select value={form.category} onChange={(e) => handleChange('category', e.target.value)}>
                {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
          </div>

          {/* Row 2: Quantity + Unit + Status */}
          <div className="form-row form-row-3">
            <label className="form-field">
              <span className="form-label">Quantity</span>
              <input
                type="number"
                value={form.quantity}
                onChange={(e) => handleChange('quantity', e.target.value)}
                placeholder="5"
                required
                min="0"
                step="any"
              />
            </label>
            <label className="form-field">
              <span className="form-label">Unit</span>
              <select value={form.unit} onChange={(e) => handleChange('unit', e.target.value)}>
                {UNITS.map((u) => <option key={u}>{u}</option>)}
              </select>
            </label>
            <label className="form-field">
              <span className="form-label">Status</span>
              <select value={form.status} onChange={(e) => handleChange('status', e.target.value)}>
                {STATUSES.map((s) => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
              </select>
            </label>
          </div>

          {/* Row 3: Dates */}
          <div className="form-row">
            <label className="form-field">
              <span className="form-label">Purchase Date</span>
              <input
                type="date"
                value={form.purchase_date}
                onChange={(e) => handleChange('purchase_date', e.target.value)}
              />
            </label>
            <label className="form-field">
              <span className="form-label">Expiry Date</span>
              <input
                type="date"
                value={form.expiry_date}
                onChange={(e) => handleChange('expiry_date', e.target.value)}
              />
            </label>
          </div>

          {/* Row 4: Cost + Store */}
          <div className="form-row">
            <label className="form-field">
              <span className="form-label">Cost per Unit (Rs.)</span>
              <input
                type="number"
                value={form.cost_per_unit}
                onChange={(e) => handleChange('cost_per_unit', e.target.value)}
                placeholder="85"
                min="0"
                step="any"
              />
            </label>
            <label className="form-field">
              <span className="form-label">Store</span>
              <input
                type="text"
                value={form.store}
                onChange={(e) => handleChange('store', e.target.value)}
                placeholder="e.g. BigBasket"
              />
            </label>
          </div>

          {/* Actions */}
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary-solid" disabled={saving}>
              {saving ? 'Saving...' : isEdit ? 'Update Item' : 'Add Item'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
