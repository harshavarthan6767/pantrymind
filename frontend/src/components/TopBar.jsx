import React from 'react';
import './TopBar.css';

export default function TopBar({ title, subtitle, actions }) {
  return (
    <div className="topbar">
      <div className="topbar-left">
        <h1 className="topbar-title">{title}</h1>
        {subtitle && <span className="topbar-subtitle">{subtitle}</span>}
      </div>
      {actions && <div className="topbar-actions">{actions}</div>}
    </div>
  );
}
