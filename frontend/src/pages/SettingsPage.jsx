import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { useDatasetStore } from '../store/datasetStore'
import { useDashboardStore } from '../store/dashboardStore'
import { User, Shield, Palette, Database, Trash2, Info, Bell, Settings, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'

const SECTIONS = ['Profile', 'Appearance', 'Data', 'About']

export default function SettingsPage() {
  const [active, setActive] = useState('Profile')
  const { user, updateUser }   = useAuthStore()
  const { datasets, removeDataset } = useDatasetStore()
  const { dashboards, deleteDashboard } = useDashboardStore()

  const [username, setUsername] = useState(user?.username ?? '')
  const [email, setEmail]       = useState(user?.email ?? '')

  const handleSaveProfile = () => {
    updateUser({ username, email })
    toast.success('Profile updated')
  }

  const handleClearDatasets = () => {
    if (!window.confirm('Delete ALL datasets? This cannot be undone.')) return
    datasets.forEach(d => removeDataset(d.id))
    toast.success('All datasets deleted')
  }

  const handleClearDashboards = () => {
    if (!window.confirm('Delete ALL dashboards? This cannot be undone.')) return
    dashboards.forEach(d => deleteDashboard(d.id))
    toast.success('All dashboards deleted')
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-surface-container-low animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="flex items-center px-8 bg-surface-container-low/80 backdrop-blur-xl border-b border-outline-variant/10 shrink-0 h-20 z-20 relative shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-surface-container border border-outline-variant/20 flex items-center justify-center shadow-sm">
            <Settings size={20} className="text-on-surface-variant" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-on-surface leading-none mb-1">Settings</h1>
            <p className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Manage your workspace preferences</p>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden max-w-7xl mx-auto w-full px-4 py-8 md:px-8">
        
        {/* Sidebar */}
        <div className="w-64 shrink-0 flex flex-col gap-1 pr-8">
          {SECTIONS.map(s => {
            const Icon = s === 'Profile' ? User : s === 'Appearance' ? Palette : s === 'Data' ? Database : Info
            return (
              <button
                key={s}
                className={`flex items-center gap-3 w-full text-left px-4 py-3 rounded-xl text-sm font-semibold transition-all ${active===s ? 'bg-primary text-on-primary shadow-md shadow-primary/20' : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'}`}
                onClick={() => setActive(s)}
              >
                <Icon size={16} />
                {s}
              </button>
            )
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto pb-12 animate-in slide-in-from-right-4 duration-300">
          
          {active === 'Profile' && (
            <div className="flex flex-col gap-8 max-w-2xl">
              <div>
                <h3 className="text-2xl font-black text-on-surface mb-2">Profile Information</h3>
                <p className="text-on-surface-variant">Update your account details and public profile.</p>
              </div>

              <div className="glass-card p-6 rounded-2xl border border-white/5 flex items-center gap-6 shadow-sm">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-on-primary text-3xl font-black shadow-lg">
                  {user?.username?.[0]?.toUpperCase()??'U'}
                </div>
                <div>
                  <p className="text-xl font-bold text-on-surface mb-1">{user?.username || 'User'}</p>
                  <p className="text-sm font-semibold text-primary uppercase tracking-wider px-2 py-0.5 rounded-md bg-primary/10 border border-primary/20 inline-block">{user?.role ?? 'Analyst'}</p>
                </div>
              </div>

              <div className="flex flex-col gap-5">
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider pl-1">Username</label>
                  <input 
                    className="h-12 px-4 rounded-xl bg-surface-container border border-outline-variant/20 text-on-surface focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all shadow-inner" 
                    value={username} 
                    onChange={e=>setUsername(e.target.value)} 
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider pl-1">Email (optional)</label>
                  <input 
                    className="h-12 px-4 rounded-xl bg-surface-container border border-outline-variant/20 text-on-surface focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all shadow-inner" 
                    type="email" 
                    value={email} 
                    onChange={e=>setEmail(e.target.value)} 
                    placeholder="you@example.com" 
                  />
                </div>
                <button 
                  className="h-12 px-6 rounded-xl bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-colors shadow-lg shadow-primary/20 mt-2 self-start flex items-center gap-2" 
                  onClick={handleSaveProfile}
                >
                  <CheckCircle size={16} /> Save Changes
                </button>
              </div>
            </div>
          )}

          {active === 'Appearance' && (
            <div className="flex flex-col gap-8 max-w-2xl">
              <div>
                <h3 className="text-2xl font-black text-on-surface mb-2">Appearance Settings</h3>
                <p className="text-on-surface-variant">Customize how Xplor looks on your device.</p>
              </div>

              <div className="flex flex-col gap-3">
                <div className="glass-card p-5 rounded-2xl border border-white/5 flex items-center justify-between hover:border-outline-variant/30 transition-colors">
                  <div>
                    <p className="font-bold text-on-surface mb-1">Color Theme</p>
                    <p className="text-sm text-on-surface-variant">Currently using dark mode (Xplor default)</p>
                  </div>
                  <span className="px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Dark Mode</span>
                </div>
                
                <div className="glass-card p-5 rounded-2xl border border-white/5 flex items-center justify-between hover:border-outline-variant/30 transition-colors">
                  <div>
                    <p className="font-bold text-on-surface mb-1">Accent Color</p>
                    <p className="text-sm text-on-surface-variant">Brand primary accent</p>
                  </div>
                  <div className="w-8 h-8 rounded-full bg-indigo-500 border-[3px] border-surface-container-high shadow-md" />
                </div>
                
                <div className="glass-card p-5 rounded-2xl border border-white/5 flex items-center justify-between hover:border-outline-variant/30 transition-colors">
                  <div>
                    <p className="font-bold text-on-surface mb-1">Chart Color Palette</p>
                    <p className="text-sm text-on-surface-variant">10-color Xplor spectrum</p>
                  </div>
                  <div className="flex items-center gap-1.5 p-1 bg-surface-container-high rounded-full border border-outline-variant/10">
                    {['#6366f1','#06b6d4','#10b981','#f59e0b','#f43f5e'].map(c=>(
                      <div key={c} className="w-5 h-5 rounded-full shadow-sm" style={{ background:c }} />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {active === 'Data' && (
            <div className="flex flex-col gap-8 max-w-2xl">
              <div>
                <h3 className="text-2xl font-black text-on-surface mb-2">Data Management</h3>
                <p className="text-on-surface-variant">Manage your locally stored datasets and dashboards.</p>
              </div>

              <div className="flex flex-col gap-4">
                <div className="glass-card p-6 rounded-2xl border border-white/5 flex items-center justify-between shadow-sm">
                  <div>
                    <p className="font-bold text-lg text-on-surface mb-1">Datasets</p>
                    <p className="text-sm text-on-surface-variant"><span className="font-semibold text-on-surface">{datasets.length}</span> dataset{datasets.length!==1?'s':''} stored locally</p>
                  </div>
                  <button
                    className="h-10 px-4 rounded-xl bg-rose-500/10 text-rose-400 font-bold text-sm hover:bg-rose-500/20 transition-colors flex items-center gap-2 border border-rose-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={handleClearDatasets}
                    disabled={datasets.length===0}
                  >
                    <Trash2 size={16} /> Clear All
                  </button>
                </div>
                
                <div className="glass-card p-6 rounded-2xl border border-white/5 flex items-center justify-between shadow-sm">
                  <div>
                    <p className="font-bold text-lg text-on-surface mb-1">Dashboards</p>
                    <p className="text-sm text-on-surface-variant"><span className="font-semibold text-on-surface">{dashboards.length}</span> dashboard{dashboards.length!==1?'s':''} saved</p>
                  </div>
                  <button
                    className="h-10 px-4 rounded-xl bg-rose-500/10 text-rose-400 font-bold text-sm hover:bg-rose-500/20 transition-colors flex items-center gap-2 border border-rose-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={handleClearDashboards}
                    disabled={dashboards.length===0}
                  >
                    <Trash2 size={16} /> Clear All
                  </button>
                </div>
                
                <div className="flex items-start gap-3 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl mt-4">
                  <Shield size={20} className="text-emerald-400 shrink-0 mt-0.5" />
                  <p className="text-sm font-medium text-emerald-200/90 leading-relaxed">
                    All data is stored securely in your browser's local storage. Nothing is sent to any external server. You own your data completely.
                  </p>
                </div>
              </div>
            </div>
          )}

          {active === 'About' && (
            <div className="flex flex-col gap-8 max-w-2xl">
              <div className="flex flex-col items-center text-center py-8 glass-card rounded-3xl border border-white/5 relative overflow-hidden">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-indigo-500/20 rounded-full blur-[80px] pointer-events-none" />
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-on-primary mb-6 shadow-lg shadow-indigo-500/20 relative z-10 border border-white/20">
                  <Sparkles size={36} />
                </div>
                <h2 className="text-4xl font-black text-on-surface tracking-tight mb-2 relative z-10">Xplor</h2>
                <p className="text-on-surface-variant font-medium relative z-10">Data Intelligence Platform · <span className="px-2 py-0.5 rounded bg-surface-container-high border border-outline-variant/10 text-xs text-on-surface-variant">v1.0.0</span></p>
              </div>

              <div>
                <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-4 px-2">Core Capabilities</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {[
                    ['📂', 'Data Ingest',    'CSV, Excel, JSON support'],
                    ['🧹', 'Data Cleaning',  'AI-powered recipe-based'],
                    ['📊', 'Exploration',    'Auto EDA & correlations'],
                    ['📈', 'Dashboards',     '8 chart types, drag & drop'],
                    ['📄', 'Reports',        'HTML/PDF export, share'],
                    ['🤖', 'AI Assistant',   'Qwen 2.5 local inference'],
                  ].map(([emoji, title, desc]) => (
                    <div key={title} className="p-4 rounded-2xl bg-surface-container border border-outline-variant/10 flex items-start gap-4">
                      <div className="w-10 h-10 rounded-xl bg-surface-container-high flex items-center justify-center text-xl shrink-0">{emoji}</div>
                      <div>
                        <p className="font-bold text-on-surface mb-1">{title}</p>
                        <p className="text-xs text-on-surface-variant">{desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-6 bg-surface-container rounded-2xl border border-outline-variant/10 text-center">
                <p className="text-sm font-medium text-on-surface-variant leading-relaxed">
                  Built with React, Tailwind CSS, Recharts, Zustand, PapaParse, and Transformers.js.<br />
                  <strong className="text-on-surface">100% Local-first architecture — maximum privacy.</strong>
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function CheckCircle({ size, className }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
      <polyline points="22 4 12 14.01 9 11.01"></polyline>
    </svg>
  )
}
