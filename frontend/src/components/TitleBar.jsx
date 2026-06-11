import React, { useState, useEffect } from 'react';
import './TitleBar.css';
import { checkHealth } from '../services/api';

export default function TitleBar() {
  const [isWindows, setIsWindows] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [statusText, setStatusText] = useState('connecting...');

  useEffect(() => {
    setIsWindows(navigator.userAgent.includes('Win'));

    let interval;

    const runHealthCheck = async () => {
      try {
        const health = await checkHealth();
        const ok = health?.status === 'healthy' || health?.status === 'ok';
        setIsConnected(ok);
        setStatusText(ok ? 'connected' : 'degraded');
        if (ok && interval) {
          // Once connected, slow down to a 30s keepalive
          clearInterval(interval);
          interval = setInterval(runHealthCheck, 30000);
        }
      } catch {
        setIsConnected(false);
        setStatusText('connecting...');
      }
    };

    // Poll every 3s on startup until backend is ready
    runHealthCheck();
    interval = setInterval(runHealthCheck, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleMinimize = () => {
    if (window.electronAPI) window.electronAPI.minimize();
  };

  const handleMaximize = () => {
    if (window.electronAPI) window.electronAPI.maximize();
  };

  const handleClose = () => {
    if (window.electronAPI) window.electronAPI.close();
  };

  return (
    <div className="titlebar">
      <div className="titlebar-left">
        {!isWindows ? (
          <div className="mac-controls">
            <div className="mac-btn close" onClick={handleClose}></div>
            <div className="mac-btn minimize" onClick={handleMinimize}></div>
            <div className="mac-btn maximize" onClick={handleMaximize}></div>
          </div>
        ) : (
          <div className="win-controls-placeholder"></div>
        )}
      </div>
      
      <div className="titlebar-center">
        <svg className="leaf-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 22C12 22 20 18 20 12C20 6 12 2 12 2C12 2 4 6 4 12C4 18 12 22 12 22Z" fill="var(--sage-500)"/>
          <path d="M12 22V12" stroke="var(--bg-surface-2)" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
        <span className="app-wordmark">PantryMind</span>
      </div>
      
      <div className="titlebar-right">
        <div className="status-container" title={`Backend: ${statusText}`}>
          <div className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
          {!isConnected && (
            <span style={{ fontSize: '10px', color: 'var(--text-tertiary)', marginLeft: '6px', fontFamily: 'var(--font-mono)' }}>
              {statusText}
            </span>
          )}
        </div>
        {isWindows && (
          <div className="win-controls">
            <div className="win-btn" onClick={handleMinimize}>
              <svg width="12" height="12" viewBox="0 0 12 12"><rect fill="currentColor" width="10" height="1" x="1" y="6"></rect></svg>
            </div>
            <div className="win-btn" onClick={handleMaximize}>
              <svg width="12" height="12" viewBox="0 0 12 12"><rect stroke="currentColor" fill="none" width="9" height="9" x="1.5" y="1.5"></rect></svg>
            </div>
            <div className="win-btn close-btn" onClick={handleClose}>
              <svg width="12" height="12" viewBox="0 0 12 12"><polygon fill="currentColor" points="11 1.576 6.583 6 11 10.424 10.424 11 6 6.583 1.576 11 1 10.424 5.417 6 1 1.576 1.576 1 6 5.417 10.424 1"></polygon></svg>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
