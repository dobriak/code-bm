/**
 * User identity store — persists funny name to localStorage.
 * Uses Zustand with persist middleware.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { generateName } from "../lib/names";

interface UserState {
  label: string;
  reroll: () => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      label: generateName(),
      reroll: () => set({ label: generateName() }),
    }),
    {
      name: "raidio.user_label",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ label: state.label }),
    },
  ),
);
