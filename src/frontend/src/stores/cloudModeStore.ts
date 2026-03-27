import { create } from "zustand";

const STORAGE_KEY = "cloudOnly";

interface CloudModeStoreType {
  cloudOnly: boolean;
  setCloudOnly: (value: boolean) => void;
}

export const useCloudModeStore = create<CloudModeStoreType>((set) => ({
  cloudOnly: (() => {
    try {
      return window.localStorage.getItem(STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  })(),
  setCloudOnly: (value) => {
    set({ cloudOnly: value });
    try {
      window.localStorage.setItem(STORAGE_KEY, value.toString());
    } catch {
      // localStorage may be unavailable in private browsing or SSR
    }
  },
}));
