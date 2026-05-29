import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, ArrowRight, Lock, User } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const [mode, setMode]         = useState('login')  // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading]   = useState(false)
  const { login } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!username.trim() || !password.trim()) {
      toast.error('Please fill in all fields')
      return
    }
    setLoading(true)
    // Simulate auth
    await new Promise((r) => setTimeout(r, 800))
    const fakeUser  = { id: '1', username: username.trim(), role: 'Analyst' }
    const fakeToken = 'mock-jwt-token-' + Date.now()
    login(fakeUser, fakeToken)
    toast.success(`Welcome back, ${username}!`)
    navigate('/home')
    setLoading(false)
  }

  return (
    <div className="min-h-screen w-full bg-background flex items-center justify-center relative overflow-hidden font-body">
      
      {/* Animated background orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary/20 rounded-full blur-[120px] mix-blend-screen opacity-50 animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-tertiary/10 rounded-full blur-[150px] mix-blend-screen opacity-40" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)]" />
      </div>

      <div className="relative z-10 w-full max-w-md px-6 animate-scale-in">
        {/* Brand */}
        <div className="flex flex-col items-center justify-center mb-10">
          <img src="/logo.png" alt="Xplor Logo" className="h-24 object-contain mb-4 filter drop-shadow-[0_0_15px_rgba(207,188,255,0.3)]" />
          <p className="text-on-surface-variant font-label-caps tracking-[0.2em] text-xs uppercase opacity-80">
            Data Intelligence Platform
          </p>
        </div>

        {/* Card */}
        <div className="glass-card rounded-2xl overflow-hidden shadow-2xl border border-white/5 bg-surface-container/40 backdrop-blur-xl">
          {/* Tabs */}
          <div className="flex w-full p-2 gap-2 bg-surface-container-low/50">
            <button
              className={`flex-1 py-3 text-sm font-semibold rounded-xl transition-all duration-300 ${mode === 'login' ? 'bg-surface-container-highest text-on-surface shadow-lg' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50'}`}
              onClick={() => setMode('login')}
            >
              Sign In
            </button>
            <button
              className={`flex-1 py-3 text-sm font-semibold rounded-xl transition-all duration-300 ${mode === 'register' ? 'bg-surface-container-highest text-on-surface shadow-lg' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50'}`}
              onClick={() => setMode('register')}
            >
              Create Account
            </button>
          </div>

          <form className="p-8 flex flex-col gap-5" onSubmit={handleSubmit}>
            {/* Username */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-on-surface-variant tracking-wide">Username</label>
              <div className="relative flex items-center group">
                <User size={16} className="absolute left-3 text-on-surface-variant group-focus-within:text-primary transition-colors" />
                <input
                  className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl py-3 pl-10 pr-4 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all"
                  type="text"
                  placeholder="Enter your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  autoFocus
                />
              </div>
            </div>

            {/* Password */}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold text-on-surface-variant tracking-wide">Password</label>
              <div className="relative flex items-center group">
                <Lock size={16} className="absolute left-3 text-on-surface-variant group-focus-within:text-primary transition-colors" />
                <input
                  className="w-full bg-surface-container-low border border-outline-variant/30 rounded-xl py-3 pl-10 pr-10 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all tracking-widest"
                  type={showPass ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                />
                <button
                  type="button"
                  className="absolute right-3 text-on-surface-variant hover:text-primary transition-colors focus:outline-none"
                  onClick={() => setShowPass((v) => !v)}
                  tabIndex={-1}
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              className="mt-4 w-full flex items-center justify-center gap-2 py-3.5 rounded-xl ai-magic-gradient text-on-primary font-bold shadow-lg shadow-primary/20 hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-70 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-on-primary/30 border-t-on-primary rounded-full animate-spin" />
              ) : (
                <>
                  {mode === 'login' ? 'Sign In' : 'Create Account'}
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          {mode === 'login' && (
            <div className="p-4 border-t border-white/5 bg-surface-container-lowest/30 text-center">
              <p className="text-xs text-on-surface-variant/70">
                Use any username & password to demo the platform.
              </p>
            </div>
          )}
        </div>

        {/* Feature pills */}
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          {['Data Cleaning', 'Visual Analytics', 'Dashboard Builder', 'PDF Reports'].map((f) => (
            <span key={f} className="px-3 py-1.5 rounded-full border border-white/10 bg-surface-container/50 text-[11px] font-semibold text-on-surface-variant backdrop-blur-sm">
              {f}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
