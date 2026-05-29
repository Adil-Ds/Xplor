import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

export default function Sidebar() {
  const { logout } = useAuthStore()

  return (
    <aside className="fixed left-0 top-0 h-screen flex flex-col p-4 gap-y-4 bg-surface-container-low border-r border-outline-variant/10 w-64 z-40">
      {/* Logo */}
      <div className="flex items-center gap-3 px-2 mb-6 mt-2">
        <div className="flex items-center justify-center">
          <img src="/logo.png" alt="Xplor Logo" className="h-10 object-contain drop-shadow-[0_0_8px_rgba(207,188,255,0.4)]" />
        </div>
        <div>
          <h1 className="font-headline-md text-headline-md font-bold text-on-surface">Xplor AI</h1>
          <p className="text-[10px] font-label-caps text-label-caps uppercase tracking-widest text-on-surface-variant/60">Local-first</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 flex-grow">
        <NavLink
          to="/home"
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 active:scale-[0.98] ` +
            (isActive ? 'bg-secondary-container text-on-secondary-container font-bold' : 'text-on-surface-variant hover:bg-surface-container-highest')
          }
        >
          <span className="material-symbols-outlined">home</span>
          <span className="font-body-base text-body-base">Home</span>
        </NavLink>
        <NavLink
          to="/datasets"
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 active:scale-[0.98] ` +
            (isActive ? 'bg-secondary-container text-on-secondary-container font-bold' : 'text-on-surface-variant hover:bg-surface-container-highest')
          }
        >
          <span className="material-symbols-outlined">database</span>
          <span className="font-body-base text-body-base">Datasets</span>
        </NavLink>
        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 active:scale-[0.98] ` +
            (isActive ? 'bg-secondary-container text-on-secondary-container font-bold' : 'text-on-surface-variant hover:bg-surface-container-highest')
          }
        >
          <span className="material-symbols-outlined">dashboard</span>
          <span className="font-body-base text-body-base">Dashboards</span>
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 active:scale-[0.98] ` +
            (isActive ? 'bg-secondary-container text-on-secondary-container font-bold' : 'text-on-surface-variant hover:bg-surface-container-highest')
          }
        >
          <span className="material-symbols-outlined">settings</span>
          <span className="font-body-base text-body-base">Settings</span>
        </NavLink>
      </nav>

      {/* Bottom Actions */}
      <div className="mt-auto pt-4 border-t border-outline-variant/10 flex flex-col gap-1">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-2 text-on-surface-variant hover:bg-surface-container-highest hover:text-error rounded-lg transition-all duration-200 w-full text-left"
        >
          <span className="material-symbols-outlined">logout</span>
          <span className="font-label-caps text-label-caps">Logout</span>
        </button>
      </div>
    </aside>
  )
}
