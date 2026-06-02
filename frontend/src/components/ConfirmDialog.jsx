import React, { useRef } from 'react';
import { AlertTriangle } from 'lucide-react';
import './ItemModal.css';

export default function ConfirmDialog({ title, message, onConfirm, onCancel, loading }) {
  const overlayRef = useRef(null);

  const handleOverlayClick = (e) => {
    if (e.target === overlayRef.current) onCancel();
  };

  return (
    <div className="modal-overlay" ref={overlayRef} onClick={handleOverlayClick}>
      <div className="confirm-card glass">
        <AlertTriangle size={36} color="#ef4444" />
        <h3 className="headline-sm" style={{ marginTop: 12 }}>{title}</h3>
        <p>{message}</p>
        <div className="modal-actions" style={{ justifyContent: 'center' }}>
          <button className="btn btn-secondary" onClick={onCancel} type="button">Cancel</button>
          <button className="btn btn-danger" onClick={onConfirm} disabled={loading} type="button">
            {loading ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
