import { create } from "zustand";

const STORAGE_KEY = "raidio.admin_jwt";

function getStoredToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeToken(token: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, token);
  } catch {
    // ignore
  }
}

function clearToken(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}

interface AdminAuthState {
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string) => void;
  logout: () => void;
}

export const useAdminAuthStore = create<AdminAuthState>((set) => ({
  token: getStoredToken(),
  isAuthenticated: !!getStoredToken(),
  login: (token: string) => {
    storeToken(token);
    set({ token, isAuthenticated: true });
  },
  logout: () => {
    clearToken();
    set({ token: null, isAuthenticated: false });
  },
}));
