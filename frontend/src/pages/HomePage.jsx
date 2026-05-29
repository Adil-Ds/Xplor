import { useNavigate } from 'react-router-dom'
import {
  Database, BarChart3, Wand2, TrendingUp, ArrowRight,
  Upload, Activity, Zap, Clock,
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { useDatasetStore } from '../store/datasetStore'
import { useDashboardStore } from '../store/dashboardStore'
import { formatBytes, timeAgo } from '../utils/helpers'

const QUICK_ACTIONS = [
  {
    id: 'action-upload',
    icon: Upload,
    label: 'Upload Dataset',
    desc: 'CSV, Excel, JSON, Parquet',
    color: 'text-indigo-400',
    bg: 'bg-indigo-500/10',
    to: '/datasets',
  },
  {
    id: 'action-dashboard',
    icon: BarChart3,
    label: 'New Dashboard',
    desc: 'Drag-and-drop builder',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
    to: '/dashboard',
  },
  {
    id: 'action-clean',
    icon: Wand2,
    label: 'Clean Data',
    desc: 'Visual no-code cleaner',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    to: '/datasets',
  },
  {
    id: 'action-reports',
    icon: TrendingUp,
    label: 'Export Report',
    desc: 'PDF & shareable links',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    to: '/reports',
  },
]

export default function HomePage() {
  const { user }       = useAuthStore()
  const { datasets }   = useDatasetStore()
  const { dashboards } = useDashboardStore()
  const navigate       = useNavigate()

  const totalRows   = datasets.reduce((s, d) => s + (d.rows ?? 0), 0)
  const totalSize   = datasets.reduce((s, d) => s + (d.size ?? 0), 0)

  const recentDatasets   = datasets.slice(0, 5)
  const recentDashboards = dashboards.slice(0, 3)

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="flex flex-col gap-8 p-8 max-w-[1400px] mx-auto w-full animate-in fade-in duration-500">
      
      {/* Hero greeting */}
      <div className="flex items-center justify-between bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] bg-surface-container-low rounded-3xl p-10 border border-outline-variant/10 shadow-2xl relative overflow-hidden">
        <div className="absolute top-[-50%] right-[-10%] w-[500px] h-[500px] bg-primary/20 rounded-full blur-[100px] pointer-events-none" />
        
        <div className="relative z-10 flex flex-col gap-2">
          <p className="text-primary font-label-caps tracking-widest text-sm font-bold uppercase">{greeting} 👋</p>
          <h2 className="text-5xl font-black text-on-surface tracking-tight">{user?.username ?? 'Analyst'}</h2>
          <p className="text-on-surface-variant text-lg mt-2 max-w-xl leading-relaxed">
            You have <strong className="text-on-surface">{datasets.length}</strong> dataset{datasets.length !== 1 ? 's' : ''} and{' '}
            <strong className="text-on-surface">{dashboards.length}</strong> dashboard{dashboards.length !== 1 ? 's' : ''} ready to explore.
          </p>
        </div>
        
        <div className="relative z-10 hidden lg:flex items-center justify-center w-32 h-32 rounded-full ai-magic-gradient shadow-[0_0_40px_rgba(207,188,255,0.4)]">
          <Zap size={48} className="text-on-primary drop-shadow-md" />
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={<Database size={24} />}
          iconColor="text-indigo-400"
          iconBg="bg-indigo-500/10 border-indigo-500/20"
          value={datasets.length}
          label="Total Datasets"
          change="+2 this week"
          positive
        />
        <StatCard
          icon={<Activity size={24} />}
          iconColor="text-cyan-400"
          iconBg="bg-cyan-500/10 border-cyan-500/20"
          value={totalRows.toLocaleString()}
          label="Total Rows"
          change="across all datasets"
        />
        <StatCard
          icon={<BarChart3 size={24} />}
          iconColor="text-emerald-400"
          iconBg="bg-emerald-500/10 border-emerald-500/20"
          value={dashboards.length}
          label="Dashboards"
          change="interactive reports"
        />
        <StatCard
          icon={<Zap size={24} />}
          iconColor="text-amber-400"
          iconBg="bg-amber-500/10 border-amber-500/20"
          value={formatBytes(totalSize)}
          label="Data Stored"
          change="total size"
        />
      </div>

      {/* Quick Actions */}
      <section className="flex flex-col gap-4">
        <h3 className="font-semibold text-lg text-on-surface flex items-center gap-2">
          <Zap size={18} className="text-primary" /> Quick Actions
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {QUICK_ACTIONS.map((a) => (
            <button
              key={a.id}
              id={a.id}
              onClick={() => navigate(a.to)}
              className="glass-card flex flex-col items-start p-6 rounded-2xl hover:bg-surface-container-highest transition-all group active:scale-[0.98] text-left border border-white/5 relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 p-4 opacity-0 -translate-x-4 group-hover:opacity-100 group-hover:translate-x-0 transition-all">
                <ArrowRight size={20} className="text-on-surface-variant" />
              </div>
              <div className={`p-3 rounded-xl border ${a.bg} ${a.color} mb-4 border-current border-opacity-20`}>
                <a.icon size={24} />
              </div>
              <p className="font-bold text-on-surface mb-1">{a.label}</p>
              <p className="text-xs text-on-surface-variant">{a.desc}</p>
            </button>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 pb-8">
        {/* Recent Datasets */}
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-lg text-on-surface flex items-center gap-2">
              <Database size={18} className="text-primary" /> Recent Datasets
            </h3>
            <button
              className="text-sm font-semibold text-primary hover:text-primary-fixed flex items-center gap-1 transition-colors"
              onClick={() => navigate('/datasets')}
            >
              View all <ArrowRight size={14} />
            </button>
          </div>

          <div className="glass-card rounded-2xl overflow-hidden border border-white/5">
            {recentDatasets.length === 0 ? (
              <EmptyState
                icon={<Database size={32} />}
                title="No datasets yet"
                desc="Upload your first file to get started"
                action={{ label: 'Upload', to: '/datasets' }}
              />
            ) : (
              <div className="flex flex-col divide-y divide-outline-variant/10">
                {recentDatasets.map((ds) => (
                  <div key={ds.id} className="flex items-center gap-4 p-4 hover:bg-surface-container-highest/50 transition-colors cursor-pointer group" onClick={() => navigate(`/explore/${ds.id}`)}>
                    <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center border border-outline-variant/10 text-primary group-hover:scale-110 transition-transform">
                      <Database size={18} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm text-on-surface truncate">{ds.name}</p>
                      <p className="text-xs text-on-surface-variant mt-0.5 truncate">
                        {ds.rows?.toLocaleString() ?? '—'} rows · {formatBytes(ds.size)}
                      </p>
                    </div>
                    <span className="text-xs text-on-surface-variant/70 flex items-center gap-1 whitespace-nowrap">
                      <Clock size={12} /> {timeAgo(ds.createdAt)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Recent Dashboards */}
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-lg text-on-surface flex items-center gap-2">
              <BarChart3 size={18} className="text-primary" /> Recent Dashboards
            </h3>
            <button
              className="text-sm font-semibold text-primary hover:text-primary-fixed flex items-center gap-1 transition-colors"
              onClick={() => navigate('/dashboard')}
            >
              View all <ArrowRight size={14} />
            </button>
          </div>

          <div className="glass-card rounded-2xl overflow-hidden border border-white/5">
            {recentDashboards.length === 0 ? (
              <EmptyState
                icon={<BarChart3 size={32} />}
                title="No dashboards yet"
                desc="Create your first dashboard"
                action={{ label: 'Create Dashboard', to: '/dashboard' }}
              />
            ) : (
              <div className="flex flex-col divide-y divide-outline-variant/10">
                {recentDashboards.map((db) => (
                  <div key={db.id} className="flex items-center gap-4 p-4 hover:bg-surface-container-highest/50 transition-colors cursor-pointer group" onClick={() => navigate('/dashboard')}>
                    <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center border border-cyan-500/20 text-cyan-400 group-hover:scale-110 transition-transform">
                      <BarChart3 size={18} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm text-on-surface truncate">{db.name}</p>
                      <p className="text-xs text-on-surface-variant mt-0.5 truncate">{db.widgets?.length ?? 0} widgets</p>
                    </div>
                    <span className="text-xs text-on-surface-variant/70 flex items-center gap-1 whitespace-nowrap">
                      <Clock size={12} /> {timeAgo(db.createdAt)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

function StatCard({ icon, iconBg, iconColor, value, label, change, positive }) {
  return (
    <div className="glass-card p-6 rounded-2xl border border-white/5 flex flex-col gap-4 hover:-translate-y-1 transition-transform duration-300">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center border ${iconBg} ${iconColor}`}>
        {icon}
      </div>
      <div>
        <div className="text-3xl font-black text-on-surface tracking-tight mb-1">{value}</div>
        <div className="text-sm font-semibold text-on-surface-variant">{label}</div>
        {change && (
          <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${positive ? 'text-emerald-400' : 'text-on-surface-variant/70'}`}>
            {positive && <TrendingUp size={12} />}
            {change}
          </div>
        )}
      </div>
    </div>
  )
}

function EmptyState({ icon, title, desc, action }) {
  const navigate = useNavigate()
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div className="w-16 h-16 rounded-full bg-surface-container flex items-center justify-center text-on-surface-variant mb-4 border border-outline-variant/10">
        {icon}
      </div>
      <p className="font-bold text-on-surface text-lg mb-2">{title}</p>
      <p className="text-sm text-on-surface-variant max-w-[250px] mb-6 leading-relaxed">{desc}</p>
      {action && (
        <button
          className="px-6 py-2.5 rounded-xl border border-outline-variant text-on-surface font-semibold text-sm hover:bg-surface-container-highest transition-all"
          onClick={() => navigate(action.to)}
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
