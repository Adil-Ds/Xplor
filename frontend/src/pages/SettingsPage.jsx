import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { useDatasetStore } from '../store/datasetStore'
import { useDashboardStore } from '../store/dashboardStore'
import { authAPI } from '../api/endpoints'
import {
  User, Shield, Palette, Database, Trash2, Info, Settings,
  Sparkles, CheckCircle, Users, BarChart3, Eye, Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'

const ROLE_COLORS = {
  admin:   'bg-violet-500/10 text-violet-400 border-violet-500/20',
  analyst: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  viewer:  'bg-amber-500/10 text-amber-400 border-amber-500/20',
}

const ROLE_ICONS = { admin: Shield, analyst: BarChart3, viewer: Eye }

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore()
  const { datasets, removeDataset } = useDatasetStore()
  const { dashboards, deleteDashboard } = useDashboardStore()

  const role    = (user?.role || 'viewer').toLowerCase()
  const isAdmin = role === 'admin'

  const sections = ['Profile', 'Appearance', 'Data', ...(isAdmin ? ['Users'] : []), 'About']
  const [active, setActive] = useState('Profile')

  const [username, setUsername] = useState(user?.username ?? '')
  const [email, setEmail]       = useState(user?.email ?? '')

  // Users tab state
  const [users, setUsers]         = useState([])
  const [usersLoading, setUL]     = useState(false)

  const fetchUsers = async () => {
    setUL(true)
    try {
      const res = await authAPI.users()
      setUsers(res.data)
    } catch {
      toast.error('Could not load users')
    }
    setUL(false)
  }

  useEffect(() => {
    if (active === 'Users' && isAdmin) fetchUsers()
  }, [active])

  const handleSaveProfile = () => {
    updateUser({ username, email })
    toast.success('Profile updated (local only — re-login to persist to backend)')
  }

  const handleClearDatasets = () => {
    if (!window.confirm('Delete ALL local datasets?')) return
    datasets.forEach(d => removeDataset(d.id))
    toast.success('All datasets deleted')
  }

  const handleClearDashboards = () => {
    if (!window.confirm('Delete ALL dashboards?')) return
    dashboards.forEach(d => deleteDashboard(d.id))
    toast.success('All dashboards deleted')
  }

  const handleRoleChange = async (userId, newRole) => {
    try {
      await authAPI.updateRole(userId, newRole)
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u))
      toast.success('Role updated')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update role')
    }
  }

  const handleDeleteUser = async (userId, username) => {
    if (!window.confirm(`Delete user "${username}"? This cannot be undone.`)) return
    try {
      await authAPI.deleteUser(userId)
      setUsers(prev => prev.filter(u => u.id !== userId))
      toast.success(`User "${username}" deleted`)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete user')
    }
  }

  const SECTION_ICONS = {
    Profile: User, Appearance: Palette, Data: Database,
    Users: Users, About: Info,
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-surface-container-low animate-in fade-in duration-500">

      {/* Header */}
      <div className="flex items-center px-8 bg-surface-container-low/80 backdrop-blur-xl border-b border-outline-variant/10 shrink-0 h-20 z-20 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-surface-container border border-outline-variant/20 flex items-center justify-center">
            <Settings size={20} className="text-on-surface-variant" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-on-surface leading-none mb-1">Settings</h1>
            <p className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Workspace preferences</p>
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden max-w-7xl mx-auto w-full px-4 py-8 md:px-8">

        {/* Sidebar nav */}
        <div className="w-56 shrink-0 flex flex-col gap-1 pr-8">
          {sections.map(s => {
            const Icon = SECTION_ICONS[s] || Info
            return (
              <button
                key={s}
                className={`flex items-center gap-3 w-full text-left px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                  active === s
                    ? 'bg-primary text-on-primary shadow-md shadow-primary/20'
                    : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                }`}
                onClick={() => setActive(s)}
              >
                <Icon size={15} />
                {s}
                {s === 'Users' && (
                  <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-400">Admin</span>
                )}
              </button>
            )
          })}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto pb-12 custom-scrollbar animate-in slide-in-from-right-4 duration-300">

          {/* ── Profile ── */}
          {active === 'Profile' && (
            <div className="flex flex-col gap-6 max-w-2xl">
              <div>
                <h3 className="text-2xl font-black text-on-surface mb-1">Profile</h3>
                <p className="text-on-surface-variant text-sm">Your account information.</p>
              </div>

              <div className="glass-card p-5 rounded-2xl border border-white/5 flex items-center gap-5">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-white text-2xl font-black shadow-lg">
                  {user?.username?.[0]?.toUpperCase() ?? 'U'}
                </div>
                <div>
                  <p className="text-lg font-bold text-on-surface">{user?.username || 'User'}</p>
                  {user?.email && <p className="text-sm text-on-surface-variant">{user.email}</p>}
                  <span className={`inline-flex items-center gap-1.5 mt-1 px-2.5 py-1 rounded-lg text-xs font-bold border ${ROLE_COLORS[role] || ROLE_COLORS.analyst}`}>
                    {(() => { const I = ROLE_ICONS[role] || BarChart3; return <I size={11} /> })()}
                    {(user?.role || 'Analyst')}
                  </span>
                </div>
              </div>

              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Username</label>
                  <input className="h-11 px-4 rounded-xl bg-surface-container border border-outline-variant/20 text-on-surface focus:border-primary/50 focus:ring-1 focus:ring-primary/40 outline-none transition-all" value={username} onChange={e => setUsername(e.target.value)} />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Email (optional)</label>
                  <input className="h-11 px-4 rounded-xl bg-surface-container border border-outline-variant/20 text-on-surface focus:border-primary/50 focus:ring-1 focus:ring-primary/40 outline-none transition-all" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" />
                </div>
                <button className="h-11 px-6 rounded-xl bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-colors self-start flex items-center gap-2 shadow-lg shadow-primary/20" onClick={handleSaveProfile}>
                  <CheckCircle size={15} /> Save Changes
                </button>
              </div>
            </div>
          )}

          {/* ── Appearance ── */}
          {active === 'Appearance' && (
            <div className="flex flex-col gap-6 max-w-2xl">
              <div>
                <h3 className="text-2xl font-black text-on-surface mb-1">Appearance</h3>
                <p className="text-on-surface-variant text-sm">Customize the look and feel.</p>
              </div>
              {[
                ['Color Theme', 'Currently using dark mode (Xplor default)', <span className="px-3 py-1 rounded-lg text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Dark Mode</span>],
                ['Chart Palette', '10-colour Xplor spectrum', <div className="flex gap-1.5">{['#6366f1','#06b6d4','#10b981','#f59e0b','#f43f5e'].map(c=><div key={c} className="w-5 h-5 rounded-full" style={{background:c}}/>)}</div>],
              ].map(([title, desc, widget]) => (
                <div key={title} className="glass-card p-5 rounded-2xl border border-white/5 flex items-center justify-between">
                  <div><p className="font-bold text-on-surface">{title}</p><p className="text-sm text-on-surface-variant">{desc}</p></div>
                  {widget}
                </div>
              ))}
            </div>
          )}

          {/* ── Data ── */}
          {active === 'Data' && (
            <div className="flex flex-col gap-6 max-w-2xl">
              <div>
                <h3 className="text-2xl font-black text-on-surface mb-1">Data Management</h3>
                <p className="text-on-surface-variant text-sm">Manage locally stored datasets and dashboards.</p>
              </div>
              <div className="glass-card p-5 rounded-2xl border border-white/5 flex items-center justify-between">
                <div><p className="font-bold text-on-surface">Datasets</p><p className="text-sm text-on-surface-variant">{datasets.length} stored locally</p></div>
                <button className="h-9 px-4 rounded-xl bg-rose-500/10 text-rose-400 font-bold text-sm hover:bg-rose-500/20 border border-rose-500/20 flex items-center gap-2 disabled:opacity-40" onClick={handleClearDatasets} disabled={!datasets.length}><Trash2 size={14}/> Clear All</button>
              </div>
              <div className="glass-card p-5 rounded-2xl border border-white/5 flex items-center justify-between">
                <div><p className="font-bold text-on-surface">Dashboards</p><p className="text-sm text-on-surface-variant">{dashboards.length} saved</p></div>
                <button className="h-9 px-4 rounded-xl bg-rose-500/10 text-rose-400 font-bold text-sm hover:bg-rose-500/20 border border-rose-500/20 flex items-center gap-2 disabled:opacity-40" onClick={handleClearDashboards} disabled={!dashboards.length}><Trash2 size={14}/> Clear All</button>
              </div>
            </div>
          )}

          {/* ── Users (Admin only) ── */}
          {active === 'Users' && isAdmin && (
            <div className="flex flex-col gap-6 max-w-3xl">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-black text-on-surface mb-1">User Management</h3>
                  <p className="text-on-surface-variant text-sm">Manage accounts and roles. Admin access only.</p>
                </div>
                <button className="h-9 px-4 rounded-xl border border-outline-variant/20 text-sm font-semibold text-on-surface hover:bg-surface-container-highest flex items-center gap-2 transition-colors" onClick={fetchUsers}>
                  {usersLoading ? <Loader2 size={14} className="animate-spin"/> : <Users size={14}/>} Refresh
                </button>
              </div>

              {usersLoading ? (
                <div className="flex items-center justify-center py-16 text-on-surface-variant">
                  <Loader2 size={32} className="animate-spin" />
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  {users.map(u => {
                    const isSelf = u.id === user?.id
                    const uRole  = (u.role || 'analyst').toLowerCase()
                    const RIcon  = ROLE_ICONS[uRole] || BarChart3
                    return (
                      <div key={u.id} className="glass-card p-4 rounded-2xl border border-white/5 flex items-center gap-4">
                        {/* Avatar */}
                        <div className="w-10 h-10 rounded-xl bg-primary/15 border border-primary/20 flex items-center justify-center shrink-0">
                          <span className="text-sm font-bold text-primary">{u.username.slice(0,2).toUpperCase()}</span>
                        </div>
                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="font-bold text-sm text-on-surface truncate">{u.username}</p>
                            {isSelf && <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-primary/15 text-primary border border-primary/20">You</span>}
                          </div>
                          <p className="text-xs text-on-surface-variant truncate">{u.email || 'No email'}</p>
                        </div>
                        {/* Role selector */}
                        <select
                          className={`h-8 px-3 rounded-lg text-xs font-bold border outline-none cursor-pointer ${ROLE_COLORS[uRole] || ROLE_COLORS.analyst}`}
                          value={uRole}
                          disabled={isSelf}
                          onChange={e => handleRoleChange(u.id, e.target.value)}
                        >
                          <option value="admin">Admin</option>
                          <option value="analyst">Analyst</option>
                          <option value="viewer">Viewer</option>
                        </select>
                        {/* Delete */}
                        {!isSelf && (
                          <button
                            className="w-8 h-8 rounded-lg flex items-center justify-center text-rose-400/70 hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
                            onClick={() => handleDeleteUser(u.id, u.username)}
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    )
                  })}
                  {!users.length && !usersLoading && (
                    <p className="text-center text-on-surface-variant py-8 text-sm">No users found.</p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── About ── */}
          {active === 'About' && (
            <div className="flex flex-col gap-6 max-w-2xl">
              <div className="flex flex-col items-center text-center py-8 glass-card rounded-3xl border border-white/5 relative overflow-hidden">
                <div className="absolute inset-0 bg-indigo-500/10 rounded-3xl blur-2xl pointer-events-none" />
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center text-white mb-4 shadow-lg relative z-10">
                  <Sparkles size={28} />
                </div>
                <h2 className="text-3xl font-black text-on-surface tracking-tight mb-1 relative z-10">Xplor AI</h2>
                <p className="text-on-surface-variant text-sm relative z-10">Data Intelligence Platform · v1.0.0</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  ['📂','Data Ingest','CSV, Excel, JSON'],
                  ['🧹','AI Cleaning','Recipe-based pipeline'],
                  ['📊','Exploration','EDA & correlation'],
                  ['📈','Dashboards','9 chart types'],
                  ['🤖','AI Chat','Ollama local LLM'],
                  ['👥','RBAC','Admin · Analyst · Viewer'],
                ].map(([e, t, d]) => (
                  <div key={t} className="p-4 rounded-2xl bg-surface-container border border-outline-variant/10 flex items-start gap-3">
                    <span className="text-xl">{e}</span>
                    <div><p className="font-bold text-sm text-on-surface">{t}</p><p className="text-xs text-on-surface-variant">{d}</p></div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
