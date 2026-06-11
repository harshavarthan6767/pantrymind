import React from 'react';
import { Sun, Moon, User, Mail, Shield, Smartphone, HardDrive } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import TopBar from '../components/TopBar';
import './Settings.css';

export default function Settings() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="page-container animate-fade-rise">
      <TopBar title="Settings" subtitle="Manage your preferences and account" />
      
      <div className="settings-content">
        
        {/* Appearance */}
        <section className="settings-section card">
          <h2 className="settings-section-title">Appearance</h2>
          <div className="settings-row">
            <div className="settings-row-text">
              <span className="settings-label">Dark Mode</span>
              <span className="settings-subtext">Toggle between light and dark themes</span>
            </div>
            <button 
              className={`theme-toggle ${theme === 'dark' ? 'active' : ''}`}
              onClick={toggleTheme}
            >
              <div className="theme-toggle-knob">
                {theme === 'dark' ? <Moon size={14} color="var(--bg-surface)" /> : <Sun size={14} color="var(--terra-500)" />}
              </div>
            </button>
          </div>
        </section>

        {/* Profile */}
        <section className="settings-section card">
          <h2 className="settings-section-title">Profile</h2>
          <div className="settings-row">
            <div className="settings-icon-wrapper">
              <User size={20} />
            </div>
            <div className="settings-row-text">
              <span className="settings-label">Name</span>
              <span className="settings-subtext">Harsh</span>
            </div>
            <button className="btn-outline">Edit</button>
          </div>
          <div className="settings-divider"></div>
          <div className="settings-row">
            <div className="settings-icon-wrapper">
              <Mail size={20} />
            </div>
            <div className="settings-row-text">
              <span className="settings-label">Email</span>
              <span className="settings-subtext">harsh@example.com</span>
            </div>
            <button className="btn-outline">Edit</button>
          </div>
        </section>

        {/* System & Storage */}
        <section className="settings-section card">
          <h2 className="settings-section-title">System & Storage</h2>
          <div className="settings-row">
            <div className="settings-icon-wrapper">
              <HardDrive size={20} />
            </div>
            <div className="settings-row-text">
              <span className="settings-label">Local Data</span>
              <span className="settings-subtext">14.2 MB used</span>
            </div>
            <button className="btn-outline" style={{ color: 'var(--status-expired)', borderColor: 'var(--status-expired)' }}>
              Clear Data
            </button>
          </div>
          <div className="settings-divider"></div>
          <div className="settings-row">
            <div className="settings-icon-wrapper">
              <Shield size={20} />
            </div>
            <div className="settings-row-text">
              <span className="settings-label">Privacy Mode</span>
              <span className="settings-subtext">Disable cloud sync for receipts</span>
            </div>
            <div className="toggle-placeholder">Enabled</div>
          </div>
        </section>

        {/* About */}
        <section className="settings-section card">
          <h2 className="settings-section-title">About</h2>
          <div className="settings-row">
            <div className="settings-icon-wrapper">
              <Smartphone size={20} />
            </div>
            <div className="settings-row-text">
              <span className="settings-label">PantryMind Desktop</span>
              <span className="settings-subtext">Version 1.0.0</span>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
