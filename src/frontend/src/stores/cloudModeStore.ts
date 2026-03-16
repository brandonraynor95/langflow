import { create } from "zustand";

interface CloudModeStoreType {
  cloudOnly: boolean;
  setCloudOnly: (value: boolean) => void;
}

export const useCloudModeStore = create<CloudModeStoreType>((set) => ({
  cloudOnly: (() => {
    const stored = window.localStorage.getItem("cloudOnly");
    return stored === "true";
  })(),
  setCloudOnly: (value) => {
    set({ cloudOnly: value });
    window.localStorage.setItem("cloudOnly", value.toString());
  },
}));
