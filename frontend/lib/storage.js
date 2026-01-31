export const STORAGE_KEYS = {
  AUTH: 'app_auth',
  SETTINGS: 'app_settings',
  AGENT_MESSAGES: 'app_agent_messages',
  ACTIVITY_LOG: 'app_activity_log',
  TOTAL_QUERIES: 'app_total_queries',
};

export function safeJsonParse(value, fallback) {
  try {
    if (!value) return fallback;
    return JSON.parse(value);
  } catch (e) {
    return fallback;
  }
}

export function loadFromStorage(key, fallback) {
  if (typeof window === 'undefined') return fallback;
  return safeJsonParse(window.localStorage.getItem(key), fallback);
}

export function saveToStorage(key, value) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(key, JSON.stringify(value));
}

export function removeFromStorage(key) {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(key);
}

export function loadFromSession(key, fallback) {
  if (typeof window === 'undefined') return fallback;
  return safeJsonParse(window.sessionStorage.getItem(key), fallback);
}

export function saveToSession(key, value) {
  if (typeof window === 'undefined') return;
  window.sessionStorage.setItem(key, JSON.stringify(value));
}

export function removeFromSession(key) {
  if (typeof window === 'undefined') return;
  window.sessionStorage.removeItem(key);
}
