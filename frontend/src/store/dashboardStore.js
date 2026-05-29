import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useDashboardStore = create(
  persist(
    (set, get) => ({
      dashboards: [],
      activeDashboard: null,

      createDashboard: (dash) => set((s) => ({ dashboards: [dash, ...s.dashboards] })),
      deleteDashboard: (id) => set((s) => ({
        dashboards: s.dashboards.filter((d) => d.id !== id),
        activeDashboard: s.activeDashboard?.id === id ? null : s.activeDashboard,
      })),
      updateDashboard: (id, patch) => set((s) => ({
        dashboards: s.dashboards.map((d) => d.id === id ? { ...d, ...patch } : d),
        activeDashboard: s.activeDashboard?.id === id ? { ...s.activeDashboard, ...patch } : s.activeDashboard,
      })),
      setActive: (id) => set((s) => ({
        activeDashboard: s.dashboards.find((d) => d.id === id) || null,
      })),

      addWidget: (dashId, widget) => {
        const dash = get().dashboards.find((d) => d.id === dashId)
        if (!dash) return
        const updated = { ...dash, widgets: [...(dash.widgets || []), widget] }
        set((s) => ({
          dashboards: s.dashboards.map((d) => d.id === dashId ? updated : d),
          activeDashboard: s.activeDashboard?.id === dashId ? updated : s.activeDashboard,
        }))
      },

      updateWidget: (dashId, widgetId, patch) => {
        const dash = get().dashboards.find((d) => d.id === dashId)
        if (!dash) return
        const updated = {
          ...dash,
          widgets: dash.widgets.map((w) => w.id === widgetId ? { ...w, ...patch } : w),
        }
        set((s) => ({
          dashboards: s.dashboards.map((d) => d.id === dashId ? updated : d),
          activeDashboard: s.activeDashboard?.id === dashId ? updated : s.activeDashboard,
        }))
      },

      removeWidget: (dashId, widgetId) => {
        const dash = get().dashboards.find((d) => d.id === dashId)
        if (!dash) return
        const updated = { ...dash, widgets: dash.widgets.filter((w) => w.id !== widgetId) }
        set((s) => ({
          dashboards: s.dashboards.map((d) => d.id === dashId ? updated : d),
          activeDashboard: s.activeDashboard?.id === dashId ? updated : s.activeDashboard,
        }))
      },
    }),
    { name: 'xplor-dashboards' }
  )
)
