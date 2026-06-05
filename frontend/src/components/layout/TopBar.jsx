import { useLocation } from 'react-router-dom'
import { useDatasetStore } from '../../store/datasetStore'
import { useAIStore } from '../../store/aiStore'
import {
  Home, Database, LayoutDashboard, FileText, Settings,
  Eye, Scissors, MessageSquare, Sparkles, Cpu, Cloud, Zap,
} from 'lucide-react'

const ROUTES = {
  '/home':      { label: 'Home',       sub: 'Welcome back',                       icon: Home           },
  '/datasets':  { label: 'Datasets',   sub: 'Upload and manage your data files',   icon: Database       },
  '/explore':   { label: 'Explore',    sub: 'Analyse distributions and correlations', icon: Eye         },
  '/clean':     { label: 'Clean',      sub: 'Transform and fix data quality issues', icon: Scissors     },
  '/chat':      { label: 'AI Chat',    sub: 'Ask natural language questions',       icon: MessageSquare  },
  '/dashboard': { label: 'Dashboards', sub: 'Build and share visual analytics',    icon: LayoutDashboard },
  '/reports':   { label: 'Reports',    sub: 'Scheduled and shared reports',        icon: FileText       },
  '/settings':  { label: 'Settings',   sub: 'Application preferences',             icon: Settings       },
}

const PROVIDERS = [
  { id: 'auto',   label: 'Auto',  icon: Zap,   title: 'Try local Ollama first, fall back to Groq cloud' },
  { id: 'ollama', label: 'Local', icon: Cpu,   title: 'Force local Ollama only' },
  { id: 'groq',   label: 'Cloud', icon: Cloud, title: 'Force Groq cloud API only' },
]

/* ─── AI provider 3-way toggle ─── */
function ProviderToggle() {
  const { provider, setProvider } = useAIStore()
  return (
    <div className="flex items-center gap-0.5 p-0.5 rounded-full bg-surface-container-high border border-outline-variant/15 shadow-inner">
      <Sparkles size={13} className="text-violet-400 ml-2 mr-1 shrink-0" />
      {PROVIDERS.map(p => {
        const Icon = p.icon
        const active = provider === p.id
        return (
          <button
            key={p.id}
            title={p.title}
            onClick={() => setProvider(p.id)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider transition-all ${
              active
                ? 'bg-violet-500/20 text-violet-300 shadow-sm'
                : 'text-on-surface-variant/60 hover:text-on-surface-variant'
            }`}
          >
            <Icon size={12} strokeWidth={active ? 2.4 : 1.8} />
            {p.label}
          </button>
        )
      })}
    </div>
  )
}

export default function TopBar() {
  const { pathname } = useLocation()
  const { datasets }  = useDatasetStore()

  const base  = '/' + (pathname.split('/')[1] || 'home')
  const route = ROUTES[base] || ROUTES['/home']
  const Icon  = route.icon

  const dsCount = datasets.length

  return (
    <header className="sticky top-0 z-50 flex items-center justify-between px-7 w-full h-16 bg-surface-container/80 backdrop-blur-xl border-b border-outline-variant/10 shrink-0">

      {/* ── Breadcrumb ── */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-surface-container-highest border border-outline-variant/10 flex items-center justify-center">
          <Icon size={16} className="text-on-surface-variant" strokeWidth={1.8} />
        </div>
        <div>
          <h1 className="text-sm font-bold text-on-surface leading-tight">{route.label}</h1>
          <p className="text-[11px] text-on-surface-variant/60 leading-none mt-0.5">{route.sub}</p>
        </div>
      </div>

      {/* ── Right status strip ── */}
      <div className="flex items-center gap-3">

        {/* Dataset count */}
        {dsCount > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container-high border border-outline-variant/15 shadow-inner">
            <Database size={13} className="text-indigo-400" />
            <span className="text-[11px] font-semibold text-on-surface-variant">
              {dsCount} dataset{dsCount !== 1 ? 's' : ''}
            </span>
          </div>
        )}

        {/* AI provider toggle */}
        <ProviderToggle />
      </div>
    </header>
  )
}
