import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Package,
  ScanLine,
  ChefHat,
  BarChart2,
  Receipt,
  ShieldCheck,
  Settings,
  ChevronLeft,
  ChevronRight,
  HeartPulse
} from 'lucide-react';
import './Sidebar.css';

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/inventory', icon: Package, label: 'Inventory' },
  { to: '/kitchen', icon: ChefHat, label: 'Kitchen Chef' },
  { to: '/health', icon: HeartPulse, label: 'Health Profile' },
  { to: '/insights', icon: BarChart2, label: 'Insights' },
];

export default function Sidebar({ collapsed, onCollapse }) {
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <button 
        className="collapse-toggle" 
        onClick={() => onCollapse(!collapsed)}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      <div className="sidebar-top">
        <div className="user-avatar">H</div>
        {!collapsed && (
          <div className="user-context">
            <span className="user-name">Harsh</span>
            <span className="user-stats">Pantry — 47 items</span>
          </div>
        )}
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ to, icon: Icon, label, badge }) => (
          <div key={to} className="nav-item-container">
            <NavLink
              to={to}
              end={to === '/'}
              className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              title={collapsed ? label : undefined}
            >
              <Icon size={20} strokeWidth={1.8} className="nav-icon" />
              <span className="nav-label">{label}</span>
              {badge && <span className="nav-badge">{badge}</span>}
              <div className="active-dot" />
            </NavLink>
          </div>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <NavLink 
          to="/settings" 
          className={({ isActive }) => `sidebar-link settings-btn ${isActive ? 'active' : ''}`} 
          title={collapsed ? 'Settings' : undefined}
        >
          <Settings size={20} strokeWidth={1.8} className="nav-icon" />
          <span className="nav-label">Settings</span>
        </NavLink>
        {!collapsed && <span className="version-label">v1.0.0</span>}
      </div>
    </aside>
  );
}
