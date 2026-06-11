import React from 'react';
import './AITable.css';

export default function AITable({ tableLines }) {
  if (!tableLines || tableLines.length < 3) return null;

  const parseRow = (line) => {
    return line.split('|').map(s => s.trim()).filter((_, i, arr) => i !== 0 && i !== arr.length - 1);
  };

  const headers = parseRow(tableLines[0]);
  const rows = tableLines.slice(2).map(parseRow);

  return (
    <div className="ai-table-container">
      <div className="ai-table-header">
        {headers.map((h, i) => (
          <div key={i} className={`ai-table-col-${i}`}>{h.replace(/\*\*/g, '')}</div>
        ))}
      </div>
      
      <div className="ai-table-rows">
        {rows.map((row, i) => {
           if (!row[0]) return null;
           
           const itemText = row[0] || '';
           const isRed = itemText.includes('🔴');
           const isYellow = itemText.includes('🟡');
           
           let statusColor = '#10B981'; // Green (FRESH)
           if (isRed) statusColor = '#EF4444';
           else if (isYellow) statusColor = '#F59E0B';
           
           // Highlight strong tags from markdown
           const cleanItemHtml = itemText.replace(/🔴|🟡|🟢/g, '').trim().replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

           return (
             <div key={i} className="ai-table-row row-hover">
               <div className="ai-table-col-0">
                  <div className="ai-status-dot" style={{ backgroundColor: statusColor, boxShadow: `0 0 8px ${statusColor}` }}></div>
                  <div className="ai-item-name" dangerouslySetInnerHTML={{ __html: cleanItemHtml }} />
               </div>
               <div className="ai-table-col-1">{row[1]?.replace(/\*\*/g, '')}</div>
               <div className="ai-table-col-2">{row[2]?.replace(/\*\*/g, '')}</div>
               <div className="ai-table-col-3">
                  <span className="ai-expires-badge" style={{ backgroundColor: `${statusColor}1A`, color: statusColor }}>
                    {row[3]?.replace(/\*\*/g, '').toUpperCase()}
                  </span>
               </div>
             </div>
           );
        })}
      </div>
    </div>
  );
}
