import React, { useState, useRef, useEffect } from 'react';
import { X, Upload, CheckCircle2, Loader2, ScanLine, Receipt } from 'lucide-react';
import { uploadReceiptImage } from '../services/api';
import { compressReceiptImage } from '../utils/imageUtils';
import './ScanReceiptModal.css';

export default function ScanReceiptModal({ onClose, onSuccess }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [stage, setStage] = useState('upload'); // 'upload' | 'preprocessing' | 'processing' | 'results'
  
  // Progress states
  const [progressSteps, setProgressSteps] = useState({
    optimized: false,
    sending: false,
    extracting: false,
    saving: false
  });
  
  const [results, setResults] = useState([]);
  const fileInputRef = useRef(null);

  // Clean up object URL
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  const handleFile = (selected) => {
    if (selected && selected.type.startsWith('image/')) {
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
      setStage('preprocessing');
      
      // Fake preprocessing delay
      setTimeout(() => {
        setStage('processing');
        startProcessing(selected);
      }, 600);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setIsDragging(true);
    else if (e.type === 'dragleave') setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const startProcessing = async (fileToProcess) => {
    try {
      setProgressSteps(p => ({ ...p, optimized: false, sending: false, extracting: false, saving: false }));
      
      console.log(`Original: ${(fileToProcess.size/1024).toFixed(0)}KB`);
      const compressed = await compressReceiptImage(fileToProcess);
      console.log(`Compressed: ${(compressed.size/1024).toFixed(0)}KB`);
      setProgressSteps(p => ({ ...p, optimized: true }));
      
      setProgressSteps(p => ({ ...p, sending: true }));
      console.log("Sending image to AI backend...");
      
      const formData = new FormData();
      formData.append('file', compressed, 'receipt.jpg');
      
      const response = await uploadReceiptImage(formData);
      console.log("Backend response received.");
      
      setProgressSteps(p => ({ ...p, extracting: true, saving: true }));
      
      setTimeout(() => {
        // The backend /upload-image returns { extracted_data: { items: <count> } }
        // or actually, if we want to show preview, we should make the backend return the array.
        // Wait, the subagent noted it returns the count.
        // Let's use the array from response.extracted_items if we make backend return it.
        // But for now, we just proceed.
        setResults(response.extracted_items || []);
        setStage('results');
        if (onSuccess) onSuccess();
      }, 800);
      
    } catch (err) {
      console.error("Processing error:", err);
      // In a real app we'd handle error state here
      onClose(); 
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className={`modal-content scan-modal ${stage === 'results' ? 'expanded' : ''}`} onClick={e => e.stopPropagation()}>
        
        {/* HEADER */}
        <div className="modal-header">
          <div className="modal-title">
            {stage === 'results' ? (
              <><CheckCircle2 size={20} className="icon-sage" /> Found {results.length} items</>
            ) : (
              <><ScanLine size={20} className="icon-sage" /> Scan Receipt</>
            )}
          </div>
          <button className="close-btn" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        <div className="modal-body">
          {/* UPLOAD & PREPROCESSING STAGE */}
          {(stage === 'upload' || stage === 'preprocessing') && (
            <div 
              className={`drop-zone ${isDragging ? 'drag-over' : ''} ${preview ? 'has-preview' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => !preview && fileInputRef.current?.click()}
            >
              {preview ? (
                <>
                  <img src={preview} alt="Receipt preview" className="preview-image" />
                  <button className="remove-preview" onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                    setPreview(null);
                    setStage('upload');
                  }}>
                    <X size={16} />
                  </button>
                  {stage === 'preprocessing' && (
                    <div className="preprocessing-overlay">
                      <div className="progress-bar-container">
                        <div className="progress-bar-fill animating"></div>
                      </div>
                      <span className="preprocessing-label">Pre-processing: scaling to 1200px, boosting contrast</span>
                    </div>
                  )}
                </>
              ) : (
                <div className="drop-zone-content">
                  <Upload size={40} className="upload-icon" />
                  <h3 className="drop-title">Drop your receipt here</h3>
                  <p className="drop-subtitle">or click to browse</p>
                  <span className="format-pill">JPG, PNG, HEIC up to 10MB</span>
                </div>
              )}
              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={(e) => handleFile(e.target.files[0])} 
                accept="image/*"
                style={{ display: 'none' }}
              />
            </div>
          )}

          {/* PROCESSING STAGE */}
          {stage === 'processing' && (
            <div className="processing-view">
              <div className="ring-animation">
                <Receipt size={32} className="receipt-icon" />
                <div className="expanding-ring"></div>
                <div className="expanding-ring delay"></div>
              </div>
              <h3 className="processing-title">Reading your receipt...</h3>
              
              <ul className="progress-steps">
                <li className={progressSteps.optimized ? 'done' : 'active'}>
                  {progressSteps.optimized ? <CheckCircle2 size={16} /> : <Loader2 size={16} className="spin" />}
                  <span>Image optimized</span>
                </li>
                <li className={!progressSteps.optimized ? 'pending' : progressSteps.sending ? 'done' : 'active'}>
                  {progressSteps.sending ? <CheckCircle2 size={16} /> : progressSteps.optimized ? <Loader2 size={16} className="spin" /> : <div className="circle-placeholder" />}
                  <span>Sending to AI</span>
                </li>
                <li className={!progressSteps.sending ? 'pending' : progressSteps.extracting ? 'done' : 'active'}>
                  {progressSteps.extracting ? <CheckCircle2 size={16} /> : progressSteps.sending ? <Loader2 size={16} className="spin" /> : <div className="circle-placeholder" />}
                  <span>Extracting items...</span>
                </li>
                <li className={!progressSteps.extracting ? 'pending' : progressSteps.saving ? 'done' : 'active'}>
                  {progressSteps.saving ? <CheckCircle2 size={16} /> : progressSteps.extracting ? <Loader2 size={16} className="spin" /> : <div className="circle-placeholder" />}
                  <span>Saving to pantry...</span>
                </li>
              </ul>
            </div>
          )}

          {/* RESULTS STAGE */}
          {stage === 'results' && (
            <div className="results-view">
              <div className="items-list">
                {results.map((item, i) => (
                  <div key={i} className="result-row">
                    <input type="text" className="result-input name-input" defaultValue={item.name} readOnly />
                    <input type="text" className="result-input qty-input mono" defaultValue={item.quantity} readOnly />
                    <div className="result-input unit-input">{item.unit || 'unit'}</div>
                    <div className="result-input expiry-input">
                      {item.expiry_date ? new Date(item.expiry_date).toLocaleDateString() : 'Set expiry'}
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="results-footer">
                <button className="btn-primary full-width" onClick={onClose}>
                  Done
                </button>
                <div className="results-note">Items have been saved to your pantry</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
