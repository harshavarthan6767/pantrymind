/**
 * PantryMind -- API Service Layer
 * Centralized HTTP client for all backend communication.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = { ...options };
  if (!(options.body instanceof FormData)) {
    config.headers = { 'Content-Type': 'application/json', ...options.headers };
  } else {
    config.headers = { ...options.headers };
  }

  try {
    const res = await fetch(url, config);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ message: res.statusText }));
      throw new Error(err.detail || err.message || `API Error ${res.status}`);
    }
    return res.json();
  } catch (error) {
    console.error(`[API] ${endpoint}:`, error);
    throw error;
  }
}

/* -- Health -------------------------------------------------- */
export const checkHealth = () => request('/health');

/* -- Dashboard ----------------------------------------------- */
export const getDashboardStats = () => request('/api/dashboard/stats');

/* -- Inventory ----------------------------------------------- */
export const getInventory = (category) => {
  const params = category ? `?category=${encodeURIComponent(category)}` : '';
  return request(`/api/inventory${params}`);
};

export const addInventoryItem = (item) =>
  request('/api/inventory', {
    method: 'POST',
    body: JSON.stringify(item),
  });

export const updateInventoryItem = (itemId, item) =>
  request(`/api/inventory/${itemId}`, {
    method: 'PUT',
    body: JSON.stringify(item),
  });

export const deleteInventoryItem = (itemId) =>
  request(`/api/inventory/${itemId}`, {
    method: 'DELETE',
  });

export const consumeItem = (itemName, quantity = 1) => {
  const form = new URLSearchParams({ item_name: itemName, quantity });
  return request('/api/inventory/consume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  });
};

/* -- Receipts ------------------------------------------------ */
export const getReceipts = () => request('/api/receipts');

export const uploadReceiptData = (receiptData) => {
  return request('/api/receipts/upload', {
    method: 'POST',
    body: JSON.stringify(receiptData),
  });
};

/* -- Chat (Agent) -------------------------------------------- */
export const sendChat = (message) =>
  request('/api/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });

/* -- User Profile -------------------------------------------- */
export const getUserProfile = () => request('/api/user/profile');

/* -- Finance ------------------------------------------------- */
export const setSalary = (monthlySalary, taxRegime = 'new') => {
  const form = new URLSearchParams({ monthly_salary: monthlySalary, tax_regime: taxRegime });
  return request('/api/finance/set-salary', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  });
};

export const getFinanceSummary = () => request('/api/finance/summary');
export const getFinanceTransactions = () => request('/api/finance/transactions');

/* -- Analytics ----------------------------------------------- */
export const getCarbonFootprint = () => request('/api/analytics/carbon');
export const getNutritionReport = () => request('/api/analytics/nutrition');
export const getRestockAlerts = () => request('/api/analytics/restock');
export const getBehaviorInsights = () => request('/api/analytics/behavior');
export const getWarranties = () => request('/api/analytics/warranties');
