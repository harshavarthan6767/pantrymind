import React, { useState, useEffect } from 'react';
import { MapPin, ShoppingCart, Star, ExternalLink } from 'lucide-react';
import './ShoppingCompareCard.css';

// Mock provider data — Phase 2 will replace with real MCP server calls
const MOCK_PROVIDERS = [
  { id: 'blinkit', name: 'Blinkit', color: '#F7C948', delivery: '10 min' },
  { id: 'zepto', name: 'Zepto', color: '#7B61FF', delivery: '8 min' },
  { id: 'freshmart', name: 'FreshMart', color: '#34C759', delivery: '15 min' },
];

function getMockPrice(itemName, providerIdx) {
  // Generate deterministic-ish mock prices based on item name
  const base = (itemName.length * 7 + providerIdx * 13) % 100 + 20;
  return `₹${base}`;
}

function getMockRating(itemName, providerIdx) {
  const r = ((itemName.length * 3 + providerIdx * 11) % 20 + 30) / 10;
  return r.toFixed(1);
}

export default function ShoppingCompareCard({ items }) {
  const [location, setLocation] = useState(null);

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          try {
            const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${pos.coords.latitude}&lon=${pos.coords.longitude}&format=json`);
            const data = await res.json();
            setLocation(data.address?.city || data.address?.town || data.address?.state || 'Your area');
          } catch {
            setLocation('Your area');
          }
        },
        () => setLocation('Location unavailable')
      );
    }
  }, []);

  if (!items || items.length === 0) return null;

  return (
    <div className="scc-wrapper">
      <div className="scc-header">
        <div className="scc-header-left">
          <ShoppingCart size={18} />
          <h4>Out of Inventory — Compare Prices</h4>
        </div>
        {location && (
          <div className="scc-location">
            <MapPin size={14} />
            <span>{location}</span>
          </div>
        )}
      </div>

      <div className="scc-table-wrapper">
        <table className="scc-table">
          <thead>
            <tr>
              <th className="scc-item-col">Item</th>
              {MOCK_PROVIDERS.map((p) => (
                <th key={p.id} className="scc-provider-col">
                  <div className="scc-provider-header">
                    <span className="scc-provider-dot" style={{ background: p.color }} />
                    <span>{p.name}</span>
                  </div>
                  <span className="scc-delivery">{p.delivery}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => {
              const prices = MOCK_PROVIDERS.map((_, pi) => {
                const priceStr = getMockPrice(item.name || item, pi);
                return { price: parseInt(priceStr.replace('₹', '')), display: priceStr, rating: getMockRating(item.name || item, pi) };
              });
              const minPrice = Math.min(...prices.map(p => p.price));

              return (
                <tr key={i}>
                  <td className="scc-item-name">
                    <span>{item.name || item}</span>
                    {item.quantity && <span className="scc-item-qty">{item.quantity}</span>}
                  </td>
                  {prices.map((p, pi) => (
                    <td key={pi} className={`scc-price-cell ${p.price === minPrice ? 'best' : ''}`}>
                      <span className="scc-price">{p.display}</span>
                      <div className="scc-rating">
                        <Star size={10} fill="currentColor" /> {p.rating}
                      </div>
                      {p.price === minPrice && <span className="scc-best-tag">Best</span>}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="scc-footer">
        <span className="scc-disclaimer">Prices are illustrative. Connect grocery APIs in Settings for live data.</span>
      </div>
    </div>
  );
}
