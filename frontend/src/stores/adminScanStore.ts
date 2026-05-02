import { create } from "zustand";

export interface ScanProgress {
  phase: string;
  total: number;
  done: number;
  current_path: string;
  errors: string[];
}

interface AdminScanState {
  progress: ScanProgress | null;
  isConnected: boolean;
  setProgress: (progress: ScanProgress | null) => void;
  setConnected: (connected: boolean) => void;
}

export const useAdminScanStore = create<AdminScanState>((set) => ({
  progress: null,
  isConnected: false,
  setProgress: (progress) => set({ progress }),
  setConnected: (isConnected) => set({ isConnected }),
}));