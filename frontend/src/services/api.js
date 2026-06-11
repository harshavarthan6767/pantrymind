/**
 * PantryMind -- API Service Layer
 * Centralized HTTP client for all backend communication.
 * Includes automatic retry with exponential backoff for startup 502s.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function request(endpoint, options = {}, retries = 4) {
  const url = `${API_BASE}${endpoint}`;
  const config = { ...options };
  const userId = localStorage.getItem('pantrymind_user_id') || 'demo_user_001';
  
  if (!(options.body instanceof FormData)) {
    config.headers = { 'Content-Type': 'application/json', 'X-User-Id': userId, ...options.headers };
  } else {
    config.headers = { 'X-User-Id': userId, ...options.headers };
  }

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, config);
      if (!res.ok) {
        // 502 = backend not ready yet — retry with backoff
        if (res.status === 502 && attempt < retries) {
          await sleep(1000 * Math.pow(1.5, attempt)); // 1s, 1.5s, 2.25s, 3.4s
          continue;
        }
        const err = await res.json().catch(() => ({ message: res.statusText }));
        throw new Error(err.detail || err.message || `API Error ${res.status}`);
      }
      return res.json();
    } catch (error) {
      if (attempt < retries && (error.message?.includes('502') || error.message?.includes('fetch'))) {
        await sleep(1000 * Math.pow(1.5, attempt));
        continue;
      }
      console.error(`[API] ${endpoint}:`, error);
      throw error;
    }
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

export const deleteMultipleInventoryItems = (itemIds) =>
  request('/api/inventory/bulk-delete', {
    method: 'POST',
    body: JSON.stringify({ item_ids: itemIds }),
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

/**
 * Send raw extracted OCR text to the backend.
 * Gemini 1.5 Flash handles structured JSON mapping server-side.
 */
export const uploadReceiptImage = (formData) => {
  return request('/api/receipts/upload-image', {
    method: 'POST',
    body: formData,
  });
};

/* -- Chat (Agent) -------------------------------------------- */
export async function streamAgentMessage({
  message,
  sessionId = "default_session",
  userId = "default_user",
  imageFile = null,
  onToken,
  onToolCall,
  onAgentSwitch,
  onDone,
  onError
}) {
  const formData = new FormData()
  formData.append("message", message)
  formData.append("session_id", sessionId)
  formData.append("user_id", userId)
  if (imageFile) {
    formData.append("image", imageFile)
  }

  const response = await fetch("/api/agent/chat", {
    method: "POST",
    body: formData
  })

  if (!response.ok) {
    onError?.(`HTTP ${response.status}`)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n")
    buffer = lines.pop()    // Keep incomplete line in buffer

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue
      try {
        const event = JSON.parse(line.slice(6))
        
        switch (event.type) {
          case "token":
            onToken?.(event.data)
            break
          case "tool_call":
            onToolCall?.(event.data, event.agent)
            break
          case "agent":
            onAgentSwitch?.(event.data)
            break
          case "done":
            onDone?.()
            break
          case "error":
            onError?.(event.data)
            break
        }
      } catch (e) {
        // Skip malformed events
      }
    }
  }
}

export const getChatHistory = (sessionId) =>
  request(`/api/agent/sessions/${sessionId}/history`);

// Legacy exports to prevent Vite crash
export const sendChat = (message, sessionId) => request('/api/chat', { method: 'POST', body: JSON.stringify({ message, session_id: sessionId }) });
export const sendKitchenChat = (message, sessionId) => request('/api/kitchen/chat', { method: 'POST', body: JSON.stringify({ message, session_id: sessionId }) });
export const getKitchenChatHistory = (sessionId) => request(`/api/kitchen/chat/history/${sessionId}`);
export const sendFinanceChat = (message, sessionId) => request('/api/finance/chat', { method: 'POST', body: JSON.stringify({ message, session_id: sessionId }) });
export const getFinanceChatHistory = (sessionId) => request(`/api/finance/chat/history/${sessionId}`);

export const sendKitchenVoice = (formData) => request('/api/kitchen/voice', { method: 'POST', body: formData });

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

/* -- Shopping / Ordering ------------------------------------ */
export const simulateShoppingOrder = (items, source = 'voice_workspace') =>
  request('/api/shopping/simulate-order', {
    method: 'POST',
    body: JSON.stringify({ items, source }),
  });

/* -- Analytics ----------------------------------------------- */
export const getCarbonFootprint = () => request('/api/analytics/carbon');
export const getNutritionReport = () => request('/api/analytics/nutrition');
export const getRestockAlerts = () => request('/api/analytics/restock');
export const getBehaviorInsights = () => request('/api/analytics/behavior');
export const getWarranties = () => request('/api/analytics/warranties');

/* -- AI Agents ----------------------------------------------- */
export const categorizeInventory = () =>
  request('/api/inventory/categorize', { method: 'POST' });

export const estimateExpiry = () =>
  request('/api/inventory/estimate-expiry', { method: 'POST' });

/* -- Medical / Health Profile -------------------------------- */
export const getMedicalConditions = (userId = 'default_user') =>
  request(`/api/medical/conditions?user_id=${userId}`);

export const addMedicalCondition = (conditionName, userId = 'default_user') =>
  request('/api/medical/conditions', {
    method: 'POST',
    body: JSON.stringify({ condition_name: conditionName, user_id: userId }),
  });

export const deleteMedicalCondition = (conditionId, userId = 'default_user') =>
  request(`/api/medical/conditions/${conditionId}?user_id=${userId}`, {
    method: 'DELETE',
  });

/* -- System -------------------------------------------------- */
export const getAgentStatus = () => request('/api/system/agent-status');


export const runInventorySafetyCheck = (userId = 'default_user') =>
  request(`/api/medical/inventory-check?user_id=${userId}`);
