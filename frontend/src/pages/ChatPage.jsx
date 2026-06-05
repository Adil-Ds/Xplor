import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  MessageSquare, Send, ChevronLeft, Zap, Database,
  AlertCircle, CheckCircle, Code2, ChevronDown, ChevronUp,
  Bot, User, Loader2, Wifi, WifiOff, Sparkles,
} from 'lucide-react'
import { useDatasetStore } from '../store/datasetStore'
import { useAuthStore } from '../store/authStore'
import api from '../api/client'

/* ─── Utility: render result from backend ─── */
function ResultRenderer({ result }) {
  if (!result) return null

  if (result.type === 'table') {
    return (
      <div className="flex flex-col gap-2 mt-4 bg-surface-container-low rounded-xl border border-outline-variant/20 overflow-hidden">
        <div className="px-4 py-2 bg-surface-container border-b border-outline-variant/10 flex justify-between items-center">
          <p className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">
            {result.total_rows} row{result.total_rows !== 1 ? 's' : ''}
            {result.total_rows > result.rows?.length ? ` (showing ${result.rows?.length})` : ''}
          </p>
        </div>
        <div className="overflow-x-auto max-h-[300px]">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="sticky top-0 bg-surface-container z-10 shadow-sm">
              <tr>{result.columns?.map(c => <th key={c} className="p-2 font-semibold text-on-surface border-b border-outline-variant/10 whitespace-nowrap">{c}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/5">
              {result.rows?.map((row, i) => (
                <tr key={i} className="hover:bg-surface-container-highest/30 transition-colors">
                  {result.columns?.map(c => (
                    <td key={c} className={`p-2 whitespace-nowrap ${row[c] == null ? 'text-on-surface-variant/30 italic' : 'text-on-surface-variant'}`}>
                      {String(row[c] ?? 'null')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  if (result.type === 'scalar') {
    return (
      <div className="inline-flex items-center mt-3 px-4 py-2 bg-primary/10 border border-primary/20 rounded-xl">
        <span className="font-mono text-lg font-bold text-primary">{result.value}</span>
      </div>
    )
  }

  if (result.type === 'error') {
    return (
      <div className="flex items-center gap-2 mt-3 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm">
        <AlertCircle size={16} className="shrink-0" />
        <span className="font-medium">{result.value}</span>
      </div>
    )
  }

  return <p className="text-on-surface leading-relaxed mt-2">{result.value}</p>
}

/* ─── Code block (collapsible) ─── */
function CodeBlock({ code }) {
  const [open, setOpen] = useState(false)
  if (!code) return null
  return (
    <div className="mt-4 flex flex-col gap-2">
      <button 
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-highest border border-outline-variant/10 text-xs font-semibold text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors w-max"
        onClick={() => setOpen(v => !v)}
      >
        <Code2 size={14} />
        <span>Pandas code executed</span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {open && (
        <pre className="p-4 rounded-xl bg-[#0f1016] border border-white/5 text-xs font-mono text-cyan-200 overflow-x-auto shadow-inner">
          {code}
        </pre>
      )}
    </div>
  )
}

/* ─── Elapsed timer shown while AI is loading ─── */
function ElapsedTimer() {
  const [secs, setSecs] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setSecs(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [])
  return (
    <span className="text-[11px] font-mono text-cyan-400/60 ml-1">
      {secs}s
    </span>
  )
}

/* ─── Message bubble ─── */
function Message({ msg, modelName }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex w-full mb-6 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex gap-4 max-w-[85%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>

        {/* Avatar */}
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-lg ${isUser ? 'bg-primary text-on-primary' : 'bg-surface-container border border-outline-variant/20 text-cyan-400'}`}>
          {isUser ? <User size={20} /> : <Bot size={20} />}
        </div>

        {/* Content */}
        <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          {isUser ? (
            <div className="px-5 py-3.5 rounded-2xl bg-surface-container-high border border-outline-variant/10 text-on-surface rounded-tr-sm shadow-md">
              <p className="text-[15px]">{msg.content}</p>
            </div>
          ) : (
            <div className="px-5 py-4 rounded-2xl glass-card border border-white/5 text-on-surface rounded-tl-sm w-full shadow-lg">
              {msg.loading ? (
                <div className="flex items-center gap-3 text-cyan-400 font-medium">
                  <Loader2 size={18} className="animate-spin" />
                  <span>{modelName} is thinking…</span>
                  <ElapsedTimer />
                </div>
              ) : (
                <>
                  <ResultRenderer result={msg.result} />
                  <CodeBlock code={msg.result?.code} />
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ─── Ollama status badge ─── */
function OllamaStatus({ status }) {
  if (!status) return null
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border shadow-sm ${status.running ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-rose-500/10 border-rose-500/20 text-rose-400'}`}>
      {status.running
        ? <><Wifi size={14} /> <span className="text-[11px] font-bold uppercase tracking-wider">Ollama · {status.models?.[0] ?? 'Ready'}</span></>
        : <><WifiOff size={14} /> <span className="text-[11px] font-bold uppercase tracking-wider">Ollama Offline</span></>
      }
    </div>
  )
}

/* ─── Suggested questions ─── */
const STARTERS = [
  'How many rows are in this dataset?',
  'Show me the top 5 rows sorted by the first numeric column.',
  'What are the column names and their types?',
  'Show me a summary of missing values per column.',
  'What is the mean of each numeric column?',
]

export default function ChatPage() {
  const { id }     = useParams()
  const navigate   = useNavigate()
  const { getById } = useDatasetStore()
  const { token }  = useAuthStore()
  const ds         = getById(id)

  const [messages,  setMessages]  = useState([])
  const [input,     setInput]     = useState('')
  const [loading,   setLoading]   = useState(false)
  const [ollamaStatus, setOllama] = useState(null)
  const bottomRef  = useRef(null)

  // Check Ollama status on mount
  useEffect(() => {
    api.get('/chat/status')
      .then(res => setOllama(res.data))
      .catch(() => setOllama({ running: false }))
  }, [])

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (question) => {
    const q = (question || input).trim()
    if (!q || loading) return
    setInput('')
    setLoading(true)

    // Add user message + AI placeholder
    const userMsg  = { id: Date.now(), role: 'user', content: q }
    const aiMsg    = { id: Date.now() + 1, role: 'ai', loading: true }
    setMessages(prev => [...prev, userMsg, aiMsg])

    try {
      // Use a 200 s timeout — LLM inference can be slow on first load
      const res = await api.post(`/chat/${id}`, { question: q }, { timeout: 200_000 })
      setMessages(prev =>
        prev.map(m => m.id === aiMsg.id ? { ...m, loading: false, result: res.data } : m)
      )
    } catch (err) {
      const httpStatus = err.response?.status
      const detail     = err.response?.data?.detail || ''
      const isTimeout  = err.code === 'ECONNABORTED' || err.message?.toLowerCase().includes('timeout')

      const errorValue =
        isTimeout
          ? `Ollama took too long to respond. The model may still be loading — try again in a moment, or ask a simpler question.`
          : httpStatus === 504
          ? detail || 'Ollama timed out. Try a simpler question or check Ollama is running.'
          : httpStatus === 503
          ? detail || 'Ollama is not running. Start it with: ollama serve'
          : httpStatus === 404
          ? 'Dataset not found on the server. Re-upload your file from the Datasets page to enable AI Chat.'
          : httpStatus === 500
          ? `Server error: ${detail || 'Something went wrong on the backend.'}`
          : !err.response
          ? 'Cannot reach the backend. Run: cd backend && python -m uvicorn main:app --port 8000'
          : `Unexpected error (HTTP ${httpStatus}).`

      setMessages(prev =>
        prev.map(m => m.id === aiMsg.id ? {
          ...m, loading: false,
          result: { type: 'error', value: errorValue },
        } : m)
      )
    }
    setLoading(false)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const modelName = ollamaStatus?.models?.[0] ?? 'Qwen 2.5'

  if (!ds) return (
    <div className="flex flex-col items-center justify-center h-[calc(100vh-64px)] bg-surface-container-low gap-4">
      <MessageSquare size={48} className="text-on-surface-variant/30" strokeWidth={1} />
      <p className="text-on-surface font-bold text-lg">Dataset not found</p>
      <p className="text-on-surface-variant text-sm">This dataset was removed or hasn't been uploaded yet.</p>
      <button
        className="h-10 px-5 rounded-xl bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-colors mt-2"
        onClick={() => navigate('/datasets')}
      >
        Go to Datasets
      </button>
    </div>
  )

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] bg-surface-container-low relative animate-in fade-in duration-500">
      
      {/* Background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between px-6 bg-surface-container-low/80 backdrop-blur-xl border-b border-outline-variant/10 shrink-0 h-16 z-20 relative shadow-sm">
        <div className="flex items-center gap-4">
          <button className="h-9 px-3 rounded-lg border border-outline-variant text-on-surface font-semibold text-sm hover:bg-surface-container-highest transition-all flex items-center gap-1.5" onClick={() => navigate('/datasets')}>
            <ChevronLeft size={16} /> Datasets
          </button>
          <div className="w-[1px] h-6 bg-outline-variant/20" />
          <MessageSquare size={20} className="text-cyan-400" />
          <div className="flex flex-col">
            <p className="font-bold text-on-surface text-sm leading-tight">Chat with Data</p>
            <p className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">
              {ds?.name ?? 'Unknown'} · {ds?.rows?.toLocaleString() ?? '?'} rows
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <OllamaStatus status={ollamaStatus} />
          <button
            className="h-9 px-4 rounded-lg bg-surface-container border border-outline-variant/20 text-on-surface font-semibold text-sm hover:bg-surface-container-highest transition-all flex items-center gap-2"
            onClick={() => navigate(`/explore/${id}`)}
          >
            <Database size={14} className="text-indigo-400" /> Explore Mode
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-6 md:p-8 relative z-10">
        <div className="max-w-4xl mx-auto w-full">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 animate-in fade-in zoom-in-95 duration-500">
              <div className="w-20 h-20 rounded-2xl ai-magic-gradient shadow-[0_0_40px_rgba(6,182,212,0.3)] flex items-center justify-center text-on-primary mb-8 border border-white/20">
                <Sparkles size={36} />
              </div>
              <h2 className="text-4xl font-black text-on-surface tracking-tight mb-4">Ask anything about your data</h2>
              <p className="text-lg text-on-surface-variant max-w-xl text-center mb-10 leading-relaxed">
                Powered by <strong className="text-cyan-400">{ollamaStatus?.models?.[0] ?? 'Qwen 2.5'} via Ollama</strong> — answers are generated as Pandas code and executed securely on your local machine. No data leaves your device.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
                {STARTERS.map((s, i) => (
                  <button
                    key={i}
                    className="p-4 text-left rounded-xl glass-card border border-white/5 hover:border-cyan-500/30 hover:bg-surface-container-highest transition-all group shadow-sm hover:shadow-md"
                    onClick={() => sendMessage(s)}
                  >
                    <p className="text-sm font-medium text-on-surface group-hover:text-cyan-100 transition-colors">{s}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map(msg => <Message key={msg.id} msg={msg} modelName={modelName} />)}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input bar */}
      <div className="p-6 bg-gradient-to-t from-surface-container-low via-surface-container-low to-transparent shrink-0 relative z-20">
        <div className="max-w-4xl mx-auto flex flex-col gap-2">
          <div className="relative flex items-end glass-card p-2 rounded-2xl border border-white/10 shadow-2xl focus-within:border-cyan-500/50 focus-within:ring-1 focus-within:ring-cyan-500/50 transition-all bg-surface-container-high/80">
            <textarea
              className="w-full bg-transparent border-none text-on-surface focus:ring-0 resize-none py-3 pl-4 pr-16 max-h-32 placeholder:text-on-surface-variant/50 leading-relaxed"
              placeholder="Ask a question about your dataset… (Enter to send)"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              rows={1}
              disabled={loading}
              style={{ minHeight: '52px' }}
            />
            <button
              className={`absolute right-3 bottom-3 w-10 h-10 rounded-xl flex items-center justify-center transition-all ${!input.trim() || loading ? 'bg-surface-container text-on-surface-variant cursor-not-allowed' : 'bg-cyan-500 text-[#0f1016] shadow-lg shadow-cyan-500/20 hover:bg-cyan-400 active:scale-95'}`}
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} className="ml-0.5" />}
            </button>
          </div>
          <p className="text-center text-[11px] font-medium text-on-surface-variant/70 tracking-wide mt-2">
            Results are generated locally via Ollama. Always verify critical insights.
          </p>
        </div>
      </div>
    </div>
  )
}
