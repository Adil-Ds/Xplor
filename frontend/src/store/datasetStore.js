import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useDatasetStore = create(
  persist(
    (set, get) => ({
      datasets: [],        // list of dataset metadata objects
      activeDataset: null, // currently selected dataset

      addDataset: (ds) => set((s) => ({ datasets: [ds, ...s.datasets] })),

      removeDataset: (id) => set((s) => ({
        datasets: s.datasets.filter((d) => d.id !== id),
        activeDataset: s.activeDataset?.id === id ? null : s.activeDataset,
      })),

      updateDataset: (id, patch) => set((s) => ({
        datasets: s.datasets.map((d) => d.id === id ? { ...d, ...patch } : d),
      })),

      setActive: (id) => set((s) => ({
        activeDataset: s.datasets.find((d) => d.id === id) || null,
      })),

      getById: (id) => get().datasets.find((d) => d.id === id),
    }),
    { name: 'xplor-datasets' }
  )
)
