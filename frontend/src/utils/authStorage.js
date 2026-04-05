const TOKEN_KEY = "access_token";
const ROLE_KEY = "user_role";

function getSessionStore() {
  if (typeof window === "undefined") return null;
  return window.sessionStorage;
}

function getLegacyStore() {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

function migrateKey(key) {
  const sessionStore = getSessionStore();
  const legacyStore = getLegacyStore();
  if (!sessionStore || !legacyStore) return "";

  const currentValue = sessionStore.getItem(key);
  if (currentValue) return currentValue;

  const legacyValue = legacyStore.getItem(key);
  if (!legacyValue) return "";

  sessionStore.setItem(key, legacyValue);
  legacyStore.removeItem(key);
  return legacyValue;
}

export function getAccessToken() {
  return migrateKey(TOKEN_KEY);
}

export function getUserRole() {
  return migrateKey(ROLE_KEY);
}

export function setAuthSession(token, role) {
  const sessionStore = getSessionStore();
  const legacyStore = getLegacyStore();
  if (!sessionStore) return;

  if (token) {
    sessionStore.setItem(TOKEN_KEY, token);
  } else {
    sessionStore.removeItem(TOKEN_KEY);
  }

  if (role) {
    sessionStore.setItem(ROLE_KEY, role);
  } else {
    sessionStore.removeItem(ROLE_KEY);
  }

  legacyStore?.removeItem(TOKEN_KEY);
  legacyStore?.removeItem(ROLE_KEY);
}

export function setStoredUserRole(role) {
  const sessionStore = getSessionStore();
  const legacyStore = getLegacyStore();
  if (!sessionStore) return;

  if (role) {
    sessionStore.setItem(ROLE_KEY, role);
  } else {
    sessionStore.removeItem(ROLE_KEY);
  }

  legacyStore?.removeItem(ROLE_KEY);
}

export function clearAuthSession() {
  const sessionStore = getSessionStore();
  const legacyStore = getLegacyStore();
  sessionStore?.removeItem(TOKEN_KEY);
  sessionStore?.removeItem(ROLE_KEY);
  legacyStore?.removeItem(TOKEN_KEY);
  legacyStore?.removeItem(ROLE_KEY);
}
