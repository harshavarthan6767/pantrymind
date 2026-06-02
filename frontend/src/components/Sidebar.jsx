import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Package,
  Wallet,
  ChefHat,
  BarChart3,
  Settings,
} from 'lucide-react';
import './Sidebar.css';

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/inventory', icon: Package, label: 'Inventory' },
  { to: '/finance', icon: Wallet, label: 'Finance' },
  { to: '/kitchen', icon: ChefHat, label: 'Kitchen' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar glass-static">
      {/* ---- Logo ---- */}
      <div className="sidebar-logo">
        <span className="logo-text">
          Pantry<span className="logo-accent">Mind</span>
        </span>
        <span className="logo-tag">AI Life Manager</span>
      </div>

      {/* ---- Navigation ---- */}
      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'sidebar-link--active' : ''}`
            }
          >
            <Icon size={20} strokeWidth={1.8} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* ---- Bottom ---- */}
      <div className="sidebar-bottom">
        <button className="sidebar-link" title="Settings">
          <Settings size={20} strokeWidth={1.8} />
          <span>Settings</span>
        </button>
        <div className="sidebar-user">
          <div className="avatar">H</div>
          <div className="user-info">
            <span className="user-name">Harsh</span>
            <span className="user-role">Personal</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
