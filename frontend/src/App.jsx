import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TitleBar from './components/TitleBar';
import Dashboard from './pages/Dashboard';
import Inventory from './pages/Inventory';
import Insights from './pages/Insights';
import Kitchen from './pages/Kitchen';
import Settings from './pages/Settings';
import HealthProfile from './pages/HealthProfile';
import ChatAssistant from './components/ChatAssistant';
import ScanReceiptModal from './components/ScanReceiptModal';
import ApprovalInbox from './components/ApprovalInbox';
import GlobalVoiceAgent from './components/GlobalVoiceAgent';
import { Mic } from 'lucide-react';
import './index.css';

function ScanPage() {
  return (
    <div className="page-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
      <ScanReceiptModal
        onClose={() => window.history.back()}
        onSuccess={() => { window.history.back(); }}
      />
    </div>
  );
}

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isVoiceOpen, setIsVoiceOpen] = useState(false);

  return (
    <div className="app-shell">
      <TitleBar />
      <Sidebar collapsed={sidebarCollapsed} onCollapse={setSidebarCollapsed} />
      <main className={`main-content ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/scan" element={<ScanPage />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/kitchen" element={<Kitchen />} />
          <Route path="/health" element={<HealthProfile />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/chat" element={<ChatAssistant />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <ApprovalInbox />

      {/* Global Voice FAB */}
      <button
        className="global-voice-fab"
        onClick={() => setIsVoiceOpen(true)}
        style={{
          position: 'fixed',
          bottom: '92px',
          right: '24px',
          width: '56px',
          height: '56px',
          borderRadius: '28px',
          backgroundColor: 'var(--sage-700)',
          color: 'white',
          border: 'none',
          boxShadow: '0 4px 12px rgba(107, 158, 112, 0.4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          zIndex: 900,
          transition: 'transform 0.2s'
        }}
        onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
        onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
      >
        <Mic size={24} />
      </button>

      <GlobalVoiceAgent isOpen={isVoiceOpen} onClose={() => setIsVoiceOpen(false)} />
    </div>
  );
}
