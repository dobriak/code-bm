/**
 * Admin auth store — persists JWT to localStorage.
 * Uses Zustand with persist middleware.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface AdminAuthState {
  jwt: string | null;
  setJwt: (token: string) => void;
  clearJwt: () => void;
}

export const useAdminAuthStore = create<AdminAuthState>()(
  persist(
    (set) => ({
      jwt: null,
      setJwt: (token) => set({ jwt: token }),
      clearJwt: () => set({ jwt: null }),
    }),
    {
      name: "raidio.admin_jwt",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ jwt: state.jwt }),
    },
  ),
);
