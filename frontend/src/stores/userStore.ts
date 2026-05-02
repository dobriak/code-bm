import { create } from "zustand";
import { generateName } from "../lib/names";

const STORAGE_KEY = "raidio.user_label";

function getStoredLabel(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeLabel(label: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, label);
  } catch {
    // ignore
  }
}

interface UserState {
  userLabel: string;
  regenerate: () => void;
}

export const useUserStore = create<UserState>((set) => ({
  userLabel: getStoredLabel() ?? generateName(),
  regenerate: () => {
    const newLabel = generateName();
    storeLabel(newLabel);
    set({ userLabel: newLabel });
  },
}));

if (!getStoredLabel()) {
  storeLabel(useUserStore.getState().userLabel);
}