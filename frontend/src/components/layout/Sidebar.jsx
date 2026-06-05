import { Link, NavLink, useLocation } from 'react-router-dom'
import {
  Home, Database, LayoutDashboard, FileText, Settings,
  LogOut, Eye, Scissors, MessageSquare, Sparkles,
  ChevronRight, Layers, Shield, BarChart3, Eye as EyeIcon,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import { useDatasetStore } from '../../store/datasetStore'

const ROLE_META = {
  admin:   { label: 'Admin',   color: 'text-violet-400', bg: 'bg-violet-500/15 border-violet-500/25', icon: Shield },
  analyst: { label: 'Analyst', color: 'text-cyan-400',   bg: 'bg-cyan-500/15 border-cyan-500/25',     icon: BarChart3 },
  viewer:  { label: 'Viewer',  color: 'text-amber-400',  bg: 'bg-amber-500/15 border-amber-500/25',   icon: EyeIcon },
}

/* ─── Nav item ─── */
function NavItem({ to, icon: Icon, label, end = false }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `relative flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 group ${
          isActive
            ? 'bg-primary/10 text-primary font-semibold'
            : 'text-on-surface-variant hover:bg-surface-container-highest hover:text-on-surface'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-primary rounded-r-full" />
          )}
          <Icon size={17} strokeWidth={isActive ? 2.2 : 1.8} className="shrink-0" />
          <span className="truncate">{label}</span>
        </>
      )}
    </NavLink>
  )
}

/* ─── Dataset tool item (prefix-based active) ─── */
function ToolItem({ to, icon: Icon, label, active }) {
  return (
    <Link
      to={to}
      className={`relative flex items-center gap-3 pl-[38px] pr-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
        active
          ? 'bg-primary/10 text-primary font-semibold'
          : 'text-on-surface-variant hover:bg-surface-container-highest hover:text-on-surface'
      }`}
    >
      {active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-primary rounded-r-full" />
      )}
      <Icon size={16} strokeWidth={active ? 2.2 : 1.8} className="shrink-0" />
      <span className="truncate">{label}</span>
      {active && <ChevronRight size={13} className="ml-auto opacity-50" />}
    </Link>
  )
}

/* ─── Section label ─── */
function SectionLabel({ children }) {
  return (
    <p className="px-4 pt-5 pb-1 text-[10px] font-bold uppercase tracking-[0.12em] text-on-surface-variant/35 select-none">
      {children}
    </p>
  )
}

export default function Sidebar() {
  const { logout, user } = useAuthStore()
  const { datasets } = useDatasetStore()
  const { pathname } = useLocation()

  /* Resolve the dataset ID to use for tool links */
  const urlId      = pathname.split('/')[2] || null
  const fallbackId = datasets[0]?.id ?? null
  const activeId   = urlId || fallbackId

  const link = (base) => activeId ? `${base}/${activeId}` : '/datasets'

  const isExplore  = pathname.startsWith('/explore/')
  const isClean    = pathname.startsWith('/clean/')
  const isChat     = pathname.startsWith('/chat/')
  const isDatasets = pathname === '/datasets'
  const isOverview = isDatasets || pathname === '/home'

  /* Active dataset metadata */
  const currentDs = activeId ? datasets.find(d => d.id === activeId) : null

  /* User display + role */
  const displayName = user?.username || user?.email?.split('@')[0] || 'User'
  const initials    = displayName.slice(0, 2).toUpperCase()
  const role        = (user?.role || 'viewer').toLowerCase()
  const roleMeta    = ROLE_META[role] || ROLE_META.viewer
  const canEdit     = role === 'admin' || role === 'analyst'  // viewers are read-only

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 flex flex-col bg-surface-container-low border-r border-outline-variant/10 z-40 overflow-hidden">

      {/* ── Logo ── */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-outline-variant/10 shrink-0">
        <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shadow-lg shadow-primary/30">
          <Sparkles size={16} className="text-on-primary" />
        </div>
        <div>
          <p className="font-bold text-on-surface text-sm leading-tight tracking-tight">Xplor AI</p>
          <p className="text-[10px] font-semibold text-on-surface-variant/50 uppercase tracking-widest">Local-first</p>
        </div>
      </div>

      {/* ── Scrollable nav ── */}
      <div className="flex-1 overflow-y-auto py-3 custom-scrollbar">

        {/* Workspace nav */}
        <SectionLabel>Workspace</SectionLabel>
        <nav className="flex flex-col gap-0.5 px-3">
          <NavItem to="/home"      icon={Home}            label="Home"       end />
          <NavItem to="/datasets"  icon={Database}        label="Datasets"   end />
          <NavItem to="/dashboard" icon={LayoutDashboard} label="Dashboards" end />
          <NavItem to="/reports"   icon={FileText}        label="Reports"    end />
        </nav>

        {/* Dataset tools */}
        {datasets.length > 0 && (
          <>
            <SectionLabel>Data Tools</SectionLabel>

            {/* Active dataset chip */}
            <div className="mx-3 mb-2 px-3 py-2 rounded-xl bg-surface-container border border-outline-variant/10 flex items-center gap-2 min-w-0">
              <Database size={13} className="text-cyan-400 shrink-0" />
              <span className="text-xs font-semibold text-on-surface truncate flex-1">
                {currentDs?.name ?? 'Select a dataset'}
              </span>
            </div>

            <nav className="flex flex-col gap-0.5 px-3">
              <ToolItem to="/datasets"       icon={Layers}        label="Overview" active={isOverview} />
              <ToolItem to={link('/explore')} icon={Eye}          label="Explore"  active={isExplore} />
              {canEdit && (
                <ToolItem to={link('/clean')} icon={Scissors}     label="Clean"    active={isClean} />
              )}
              {canEdit && (
                <ToolItem to={link('/chat')}  icon={MessageSquare} label="AI Chat" active={isChat} />
              )}
            </nav>
          </>
        )}

        {/* Preferences */}
        <SectionLabel>Preferences</SectionLabel>
        <nav className="flex flex-col gap-0.5 px-3">
          <NavItem to="/settings" icon={Settings} label="Settings" end />
        </nav>
      </div>

      {/* ── User footer ── */}
      <div className="shrink-0 border-t border-outline-variant/10 px-3 py-3">
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-surface-container-highest transition-colors group">
          {/* Avatar */}
          <div className="w-8 h-8 rounded-lg bg-primary/15 border border-primary/20 flex items-center justify-center shrink-0">
            <span className="text-[11px] font-bold text-primary">{initials}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-on-surface truncate leading-tight">{displayName}</p>
            {/* Role badge */}
            <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold border mt-0.5 ${roleMeta.bg} ${roleMeta.color}`}>
              <roleMeta.icon size={9} strokeWidth={2.5} />
              {roleMeta.label}
            </span>
          </div>
          <button
            onClick={logout}
            title="Sign out"
            className="w-7 h-7 rounded-lg flex items-center justify-center text-on-surface-variant/50 hover:text-rose-400 hover:bg-rose-500/10 transition-colors opacity-0 group-hover:opacity-100"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  )
}
