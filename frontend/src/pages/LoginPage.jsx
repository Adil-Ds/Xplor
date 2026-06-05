import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, ArrowRight, Lock, User, Mail, Shield, BarChart3, Eye as EyeIcon } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { authAPI } from '../api/endpoints'
import toast from 'react-hot-toast'

const ROLES = [
  {
    id:    'analyst',
    label: 'Analyst',
    icon:  BarChart3,
    desc:  'Upload, clean, explore, chat with data & build dashboards',
  },
  {
    id:    'admin',
    label: 'Admin',
    icon:  Shield,
    desc:  'Full access + manage users and roles',
  },
  {
    id:    'viewer',
    label: 'Viewer',
    icon:  EyeIcon,
    desc:  'Read-only — explore and view dashboards',
  },
]

export default function LoginPage() {
  const [mode, setMode]           = useState('login')
  const [username, setUsername]   = useState('')
  const [email, setEmail]         = useState('')
  const [password, setPassword]   = useState('')
  const [showPass, setShowPass]   = useState(false)
  const [selectedRole, setRole]   = useState('analyst')
  const [loading, setLoading]     = useState(false)
  const { login } = useAuthStore()
  const navigate  = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) {
      toast.error('Username and password are required')
      return
    }
    if (mode === 'register' && password.length < 6) {
      toast.error('Password must be at least 6 characters')
      return
    }

    setLoading(true)
    try {
      const res = mode === 'login'
        ? await authAPI.login({ username: username.trim(), password })
        : await authAPI.register({
            username: username.trim(),
            password,
            email:    email.trim() || undefined,
            role:     selectedRole,
          })

      const { token, user } = res.data
      login(user, token)
      toast.success(
        mode === 'login'
          ? `Welcome back, ${user.username}!`
          : `Account created! Welcome, ${user.username} (${user.role})`,
      )
      navigate('/home')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Something went wrong. Is the backend running?'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  const switchMode = (next) => {
    setMode(next)
    setUsername('')
    setEmail('')
    setPassword('')
    setRole('analyst')
  }

  return (
    <div className="min-h-screen w-full bg-background flex items-center justify-center relative overflow-hidden">

      {/* Background glows */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary/20 rounded-full blur-[120px] opacity-50 animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-violet-500/10 rounded-full blur-[150px] opacity-40" />
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)]" />
      </div>

      <div className="relative z-10 w-full max-w-md px-6">

        {/* Brand */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-primary flex items-center justify-center shadow-xl shadow-primary/30 mb-4">
            <BarChart3 size={28} className="text-on-primary" strokeWidth={1.8} />
          </div>
          <h1 className="font-black text-2xl text-on-surface tracking-tight">Xplor AI</h1>
          <p className="text-on-surface-variant text-xs uppercase tracking-widest mt-1">Data Intelligence Platform</p>
        </div>

        {/* Card */}
        <div className="glass-card rounded-2xl overflow-hidden shadow-2xl border border-white/5 bg-surface-container/40 backdrop-blur-xl">

          {/* Mode tabs */}
          <div className="flex p-2 gap-2 bg-surface-container-low/50">
            {[['login', 'Sign In'], ['register', 'Create Account']].map(([m, label]) => (
              <button
                key={m}
                className={`flex-1 py-2.5 text-sm font-semibold rounded-xl transition-all duration-200 ${
                  mode === m
                    ? 'bg-surface-container-highest text-on-surface shadow-lg'
                    : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50'
                }`}
                onClick={() => switchMode(m)}
              >
                {label}
              </button>
            ))}
          </div>

          <form className="p-7 flex flex-col gap-4" onSubmit={handleSubmit}>

            {/* Username */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Username</label>
              <div className="relative flex items-center group">
                <User size={15} className="absolute left-3 text-on-surface-variant group-focus-within:text-primary transition-colors" />
                <input
                  className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl py-3 pl-9 pr-4 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/40 transition-all"
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  autoComplete="username"
                  autoFocus
                />
              </div>
            </div>

            {/* Email (register only) */}
            {mode === 'register' && (
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">
                  Email <span className="text-on-surface-variant/40 normal-case font-normal">(optional)</span>
                </label>
                <div className="relative flex items-center group">
                  <Mail size={15} className="absolute left-3 text-on-surface-variant group-focus-within:text-primary transition-colors" />
                  <input
                    className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl py-3 pl-9 pr-4 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/40 transition-all"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    autoComplete="email"
                  />
                </div>
              </div>
            )}

            {/* Password */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Password</label>
              <div className="relative flex items-center group">
                <Lock size={15} className="absolute left-3 text-on-surface-variant group-focus-within:text-primary transition-colors" />
                <input
                  className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl py-3 pl-9 pr-10 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-primary/60 focus:ring-1 focus:ring-primary/40 transition-all"
                  type={showPass ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                />
                <button
                  type="button"
                  className="absolute right-3 text-on-surface-variant hover:text-primary transition-colors"
                  onClick={() => setShowPass(v => !v)}
                  tabIndex={-1}
                >
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              {mode === 'register' && (
                <p className="text-[11px] text-on-surface-variant/50">Minimum 6 characters</p>
              )}
            </div>

            {/* Role selector (register only) */}
            {mode === 'register' && (
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Role</label>
                <div className="flex flex-col gap-2">
                  {ROLES.map(r => {
                    const Icon = r.icon
                    const active = selectedRole === r.id
                    return (
                      <button
                        key={r.id}
                        type="button"
                        onClick={() => setRole(r.id)}
                        className={`flex items-center gap-3 p-3 rounded-xl border text-left transition-all ${
                          active
                            ? 'border-primary/50 bg-primary/10 text-primary'
                            : 'border-outline-variant/20 bg-surface-container hover:border-outline-variant/40 text-on-surface-variant'
                        }`}
                      >
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${active ? 'bg-primary/20' : 'bg-surface-container-highest'}`}>
                          <Icon size={16} strokeWidth={active ? 2.2 : 1.8} />
                        </div>
                        <div className="min-w-0">
                          <p className={`text-sm font-bold leading-tight ${active ? 'text-primary' : 'text-on-surface'}`}>{r.label}</p>
                          <p className="text-[11px] text-on-surface-variant/70 leading-snug mt-0.5">{r.desc}</p>
                        </div>
                        {active && (
                          <div className="ml-auto w-4 h-4 rounded-full bg-primary flex items-center justify-center shrink-0">
                            <div className="w-2 h-2 rounded-full bg-on-primary" />
                          </div>
                        )}
                      </button>
                    )
                  })}
                </div>
                <p className="text-[11px] text-on-surface-variant/50">
                  Note: the very first account registered is automatically promoted to Admin.
                </p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              className="mt-2 w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-500 text-white font-bold shadow-lg hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-60 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  {mode === 'login' ? 'Sign In' : 'Create Account'}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </div>

        {/* Feature pills */}
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          {['AI Chat', 'Data Cleaning', 'Dashboards', 'Anomaly Detection', 'RBAC'].map(f => (
            <span key={f} className="px-3 py-1 rounded-full border border-white/10 bg-surface-container/50 text-[11px] font-semibold text-on-surface-variant backdrop-blur-sm">
              {f}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
