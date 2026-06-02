import React, { useState, useRef } from 'react';
import { X, Upload, FileText, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { uploadReceipt } from '../services/api';
import './ScanReceiptModal.css';

export default function ScanReceiptModal({ onClose, onSuccess }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setError(null);
    }
  };

  const handleScan = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      await uploadReceipt(file, 'receipt');
      setSuccess(true);
      setTimeout(() => {
        if (onSuccess) onSuccess();
        onClose();
      }, 2000);
    } catch (err) {
      setError(err.message || 'Failed to scan receipt');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content scan-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Scan Receipt</h2>
          <button className="btn-icon modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {success ? (
            <div className="scan-success">
              <CheckCircle2 size={48} className="success-icon" />
              <p>Receipt scanned and processed successfully!</p>
            </div>
          ) : (
            <div className="scan-area">
              <div 
                className={`upload-zone ${file ? 'has-file' : ''}`}
                onClick={() => fileInputRef.current?.click()}
              >
                {file ? (
                  <div className="file-info">
                    <FileText size={32} />
                    <p>{file.name}</p>
                    <span>{(file.size / 1024).toFixed(1)} KB</span>
                  </div>
                ) : (
                  <div className="upload-prompt">
                    <Upload size={32} />
                    <p>Click to upload receipt image</p>
                    <span>Supports JPG, PNG, PDF</span>
                  </div>
                )}
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  accept="image/*,application/pdf"
                  style={{ display: 'none' }}
                />
              </div>

              {error && (
                <div className="scan-error">
                  <AlertCircle size={16} />
                  <span>{error}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {!success && (
          <div className="modal-footer">
            <button className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleScan} disabled={!file || loading}>
              {loading ? (
                <><Loader2 size={16} className="spin" /> Processing...</>
              ) : (
                'Upload & Scan'
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
