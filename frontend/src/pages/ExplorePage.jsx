import { useState, useMemo, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import {
  ChevronLeft, BarChart3, TrendingUp, AlertTriangle,
  Lightbulb, Hash, Type, Database,
  CheckCircle, XCircle, Loader2, Zap,
  ShieldAlert, Wand2, Eye, Sparkles,
} from 'lucide-react'
import { useDatasetStore } from '../store/datasetStore'
import { useAuthStore } from '../store/authStore'
import { formatNumber, chartColor } from '../utils/helpers'
import api from '../api/client'
import toast from 'react-hot-toast'

/* ─── Stats engine (in-browser) ─── */
function computeStats(data, column) {
  const vals = data.map((r) => r[column]).filter((v) => v !== null && v !== undefined && v !== '')
  const nums  = vals.map(Number).filter((n) => !isNaN(n))
  const nulls = data.length - vals.length

  const isNumeric = nums.length / Math.max(vals.length, 1) > 0.7

  if (isNumeric) {
    const sorted = [...nums].sort((a, b) => a - b)
    const mean   = nums.reduce((s, v) => s + v, 0) / nums.length
    const variance = nums.reduce((s, v) => s + (v - mean) ** 2, 0) / nums.length
    const std    = Math.sqrt(variance)
    const q1     = sorted[Math.floor(sorted.length * 0.25)]
    const median = sorted[Math.floor(sorted.length * 0.5)]
    const q3     = sorted[Math.floor(sorted.length * 0.75)]
    const iqr    = q3 - q1
    const outliers = nums.filter((n) => n < q1 - 1.5 * iqr || n > q3 + 1.5 * iqr)

    return {
      type: 'numeric', count: vals.length, nulls, nullPct: (nulls / data.length * 100).toFixed(1),
      min: sorted[0], max: sorted[sorted.length - 1], mean, median, std, q1, q3, iqr,
      unique: new Set(nums).size, outliers: outliers.length,
      histogram: buildHistogram(nums, 10),
    }
  } else {
    const freqMap = {}
    vals.forEach((v) => { const k = String(v); freqMap[k] = (freqMap[k] || 0) + 1 })
    const sorted = Object.entries(freqMap).sort((a, b) => b[1] - a[1])
    return {
      type: 'categorical', count: vals.length, nulls, nullPct: (nulls / data.length * 100).toFixed(1),
      unique: sorted.length,
      topValues: sorted.slice(0, 15).map(([v, c]) => ({ value: v, count: c })),
    }
  }
}

function buildHistogram(nums, bins) {
  if (!nums.length) return []
  const min = Math.min(...nums), max = Math.max(...nums)
  if (min === max) return [{ bin: String(min), count: nums.length }]
  const binSize = (max - min) / bins
  const buckets = Array(bins).fill(0)
  nums.forEach((n) => {
    let i = Math.floor((n - min) / binSize)
    if (i >= bins) i = bins - 1
    buckets[i]++
  })
  return buckets.map((count, i) => ({
    bin: formatNumber(min + i * binSize, 1),
    count,
  }))
}

function computeSummary(data, columns) {
  const rows = data.length
  const colCount = columns.length
  const numCols = columns.filter((c) => {
    const vals = data.slice(0, 100).map((r) => r[c]).filter((v) => v !== null && v !== '')
    const nums = vals.map(Number).filter((n) => !isNaN(n))
    return nums.length / Math.max(vals.length, 1) > 0.7
  })
  const totalNulls = columns.reduce((s, c) => {
    return s + data.filter((r) => r[c] === null || r[c] === undefined || r[c] === '').length
  }, 0)

  // Handle divide by zero
  const pct = (rows * colCount) === 0 ? 0 : (totalNulls / (rows * colCount) * 100)
  return { rows, colCount, numericCols: numCols.length, totalNulls, nullPct: pct.toFixed(1) }
}

function generateSuggestions(data, columns) {
  const hints = []
  columns.forEach((col) => {
    const nulls = data.filter((r) => r[col] === null || r[col] === undefined || r[col] === '').length
    const pct = data.length === 0 ? 0 : (nulls / data.length * 100)
    if (pct > 40) hints.push({ type: 'warning', text: `"${col}" has ${pct.toFixed(0)}% missing values — consider dropping or imputing.` })
    else if (pct > 10) hints.push({ type: 'info', text: `"${col}" has ${pct.toFixed(0)}% nulls — consider filling with mean/median.` })
  })
  if (hints.length === 0) hints.push({ type: 'success', text: 'Dataset looks clean! No major quality issues detected.' })
  return hints
}

const CUSTOM_TOOLTIP = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-container-high border border-outline-variant/20 rounded-xl p-3 text-xs shadow-xl z-50">
      <p className="text-on-surface-variant font-medium mb-2">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="font-semibold flex items-center gap-2" style={{ color: p.color || 'var(--text-primary)' }}>
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color || 'var(--text-primary)' }} />
          {p.name}: {formatNumber(p.value)}
        </p>
      ))}
    </div>
  )
}

function StatMini({ label, value, color }) {
  return (
    <div className="glass-card p-4 rounded-xl flex flex-col gap-1 border border-white/5 relative overflow-hidden h-full">
      <div className="absolute top-0 left-0 w-1 h-full" style={{ background: color }} />
      <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">{label}</span>
      <span className="text-xl font-black text-on-surface tracking-tight truncate">{value}</span>
    </div>
  )
}

export default function ExplorePage() {
  const { id }   = useParams()
  const navigate = useNavigate()
  const { getById } = useDatasetStore()
  const ds       = getById(id)

  const [activeCol, setActiveCol] = useState(null)
  const [activeTab, setActiveTab] = useState('overview') // overview | distribution | correlation | data | suggestions | anomalies
  const [suggestionsData, setSuggestions] = useState(null)
  const [anomaliesData, setAnomalies]     = useState(null)
  const [suggestionsLoading, setSugLoading] = useState(false)
  const [anomaliesLoading, setAnoLoading]   = useState(false)
  const [rejectedIds, setRejectedIds]       = useState(new Set())
  const [acceptedIds, setAcceptedIds]       = useState(new Set())

  const data    = ds?.preview ?? []
  const columns = ds?.columnNames ?? Object.keys(data[0] ?? {})

  const summary     = useMemo(() => computeSummary(data, columns), [data, columns])
  const suggestions = useMemo(() => generateSuggestions(data, columns), [data, columns])
  const colStats    = useMemo(() => activeCol ? computeStats(data, activeCol) : null, [data, activeCol])

  // Fetch AI suggestions from backend
  const fetchSuggestions = useCallback(async () => {
    if (!id) return
    setSugLoading(true)
    try {
      const res  = await api.get(`/explore/${id}/suggestions`)
      setSuggestions(res.data)
    } catch { setSuggestions(null) }
    setSugLoading(false)
  }, [id])

  // Fetch anomalies from backend
  const fetchAnomalies = useCallback(async () => {
    if (!id) return
    setAnoLoading(true)
    try {
      const res  = await api.get(`/explore/${id}/anomalies`)
      setAnomalies(res.data)
    } catch { setAnomalies(null) }
    setAnoLoading(false)
  }, [id])

  // Auto-fetch when switching to AI tabs
  useEffect(() => {
    if (activeTab === 'suggestions' && !suggestionsData && !suggestionsLoading) fetchSuggestions()
    if (activeTab === 'anomalies'   && !anomaliesData   && !anomaliesLoading)   fetchAnomalies()
  }, [activeTab, suggestionsData, suggestionsLoading, anomaliesData, anomaliesLoading, fetchSuggestions, fetchAnomalies])

  // Correlation matrix (numeric columns, pearson approximation)
  const corrData = useMemo(() => {
    const numCols = columns.filter((c) => {
      const vals = data.slice(0,50).map(r=>r[c])
      return vals.filter(v=>!isNaN(Number(v)) && v!=='').length/Math.max(vals.length,1) > 0.7
    }).slice(0,8)
    if (numCols.length < 2) return { cols: [], matrix: [] }
    const vecs = numCols.map((c) => data.map(r=>Number(r[c])).filter(v=>!isNaN(v)))
    const pearson = (a,b) => {
      const n=Math.min(a.length,b.length)
      if (n === 0) return 0
      const ma=a.reduce((s,v)=>s+v,0)/n, mb=b.reduce((s,v)=>s+v,0)/n
      const num=a.slice(0,n).reduce((s,v,i)=>s+(v-ma)*(b[i]-mb),0)
      const da=Math.sqrt(a.slice(0,n).reduce((s,v)=>s+(v-ma)**2,0))
      const db=Math.sqrt(b.slice(0,n).reduce((s,v)=>s+(v-mb)**2,0))
      return da===0||db===0 ? 0 : num/(da*db)
    }
    const matrix = numCols.map((_,i)=>numCols.map((_,j)=>+pearson(vecs[i],vecs[j]).toFixed(3)))
    return { cols: numCols, matrix }
  }, [data, columns])

  if (!ds) return (
    <div className="flex flex-col items-center justify-center h-[calc(100vh-64px)] bg-surface-container-low animate-in fade-in">
      <p className="font-bold text-xl text-on-surface mb-4">Dataset not found.</p>
      <button className="h-10 px-4 rounded-xl border border-outline-variant text-on-surface font-semibold text-sm hover:bg-surface-container-highest transition-all flex items-center gap-2" onClick={() => navigate('/datasets')}><ChevronLeft size={16} /> Back</button>
    </div>
  )

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'distribution', label: 'Distribution' },
    { id: 'correlation', label: 'Correlation' },
    { id: 'data', label: 'Data' },
    { id: 'suggestions', label: '✨ AI Suggestions' },
    { id: 'anomalies', label: '🔍 Anomalies' },
  ]

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-surface-container-low animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between px-6 bg-surface-container-low/80 backdrop-blur-xl border-b border-outline-variant/10 shrink-0 h-16 z-20 relative shadow-sm">
        <div className="flex items-center gap-4">
          <button className="h-9 px-3 rounded-lg border border-outline-variant text-on-surface font-semibold text-sm hover:bg-surface-container-highest transition-all flex items-center gap-1.5" onClick={() => navigate('/datasets')}>
            <ChevronLeft size={16} /> Datasets
          </button>
          <div className="w-[1px] h-6 bg-outline-variant/20" />
          <Eye size={20} className="text-indigo-400" />
          <div className="flex flex-col">
            <p className="font-bold text-on-surface text-sm leading-tight">Explore Mode</p>
            <p className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">{ds.name} · {summary.rows.toLocaleString()} rows</p>
          </div>
        </div>
        <div className="flex items-center bg-surface-container-high rounded-xl p-1 border border-outline-variant/10 shadow-inner">
          {tabs.map(t => (
            <button 
              key={t.id} 
              className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all ${activeTab === t.id ? 'bg-surface-container-highest text-on-surface shadow-sm border border-outline-variant/20' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50'}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 md:p-8 relative z-10 custom-scrollbar">
        <div className="max-w-[1200px] mx-auto w-full h-full flex flex-col">
          {activeTab === 'overview' && (
            <OverviewTab summary={summary} suggestions={suggestions} columns={columns} data={data} onColumnClick={(c)=>{setActiveCol(c);setActiveTab('distribution')}} />
          )}
          {activeTab === 'distribution' && (
            <DistributionTab columns={columns} activeCol={activeCol} setActiveCol={setActiveCol} colStats={colStats} />
          )}
          {activeTab === 'correlation' && (
            <CorrelationTab corrData={corrData} />
          )}
          {activeTab === 'data' && (
            <DataTab data={data} columns={columns} />
          )}
          {activeTab === 'suggestions' && (
            <AITab
              data={suggestionsData}
              loading={suggestionsLoading}
              rejectedIds={rejectedIds}
              acceptedIds={acceptedIds}
              onAccept={(id) => setAcceptedIds(prev => new Set([...prev, id]))}
              onReject={(id) => setRejectedIds(prev => new Set([...prev, id]))}
              onRefresh={fetchSuggestions}
            />
          )}
          {activeTab === 'anomalies' && (
            <AnomaliesTab data={anomaliesData} loading={anomaliesLoading} onRefresh={fetchAnomalies} />
          )}
        </div>
      </div>
    </div>
  )
}

/* ─── Overview Tab ─── */
function OverviewTab({ summary, suggestions, columns, data, onColumnClick }) {
  return (
    <div className="flex flex-col gap-6 animate-in slide-in-from-bottom-4 duration-300">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatMini label="Rows"         value={summary.rows.toLocaleString()}    color="#60a5fa" />
        <StatMini label="Columns"      value={summary.colCount}                  color="#22d3ee" />
        <StatMini label="Numeric cols" value={summary.numericCols}               color="#34d399" />
        <StatMini label="Missing vals" value={`${summary.nullPct}%`}            color={Number(summary.nullPct)>10 ? '#f43f5e' : '#fbbf24'} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Column profiles */}
        <div className="md:col-span-2 glass-card p-6 rounded-2xl border border-white/5 shadow-sm">
          <p className="font-bold text-on-surface mb-4">Column Profiles</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {columns.map((col) => {
              const nulls  = data.filter(r=>r[col]===null||r[col]===undefined||r[col]==='').length
              const nullPct = data.length === 0 ? 0 : (nulls/data.length*100)
              const vals   = data.slice(0,50).map(r=>r[col]).filter(v=>v!==null&&v!=='')
              const isNum  = vals.length > 0 && vals.map(Number).filter(v=>!isNaN(v)).length/vals.length>0.7
              return (
                <div key={col} className="bg-surface-container-low border border-outline-variant/10 p-3 rounded-xl hover:border-indigo-500/50 cursor-pointer transition-colors" onClick={()=>onColumnClick(col)}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-sm text-on-surface truncate pr-2">{col}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${isNum ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' : 'bg-surface-container-highest text-on-surface-variant border-outline-variant/10'}`}>{isNum?'numeric':'text'}</span>
                  </div>
                  <div className="w-full h-1.5 bg-surface-container-highest rounded-full overflow-hidden mb-2">
                    <div className="h-full" style={{ width: `${100-nullPct}%`, background: isNum?'#22d3ee':'#818cf8' }} />
                  </div>
                  <div className="flex justify-between text-xs font-medium text-on-surface-variant">
                    <span>{data.length - nulls} values</span>
                    <span className={nullPct > 10 ? 'text-rose-400' : ''}>{nullPct.toFixed(0)}% null</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Basic Suggestions */}
        <div className="glass-card p-6 rounded-2xl border border-white/5 shadow-sm flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <Lightbulb size={18} className="text-amber-400" />
            <p className="font-bold text-on-surface">Quick Insights</p>
          </div>
          <div className="flex flex-col gap-3 flex-1 overflow-y-auto">
            {suggestions.map((s, i) => (
              <div key={i} className={`p-3 rounded-xl border flex gap-3 ${s.type === 'warning' ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' : s.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-amber-500/10 border-amber-500/20 text-amber-400'}`}>
                <div className="mt-0.5 shrink-0">
                  {s.type === 'warning' ? <AlertTriangle size={14} /> : s.type === 'success' ? <TrendingUp size={14} /> : <Lightbulb size={14} />}
                </div>
                <p className="text-xs font-medium leading-relaxed">{s.text}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ─── Distribution Tab ─── */
function DistributionTab({ columns, activeCol, setActiveCol, colStats }) {
  return (
    <div className="flex h-full gap-6 animate-in slide-in-from-bottom-4 duration-300">
      {/* Column list */}
      <div className="w-64 flex flex-col gap-2 overflow-y-auto pr-2 custom-scrollbar shrink-0">
        <p className="font-bold text-sm text-on-surface-variant uppercase tracking-wider mb-2 pl-2">Columns</p>
        {columns.map((c) => (
          <button 
            key={c} 
            className={`text-left px-4 py-3 rounded-xl text-sm font-semibold transition-all ${activeCol===c ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'bg-surface-container-low hover:bg-surface-container text-on-surface border border-transparent'}`} 
            onClick={()=>setActiveCol(c)}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Stats panel */}
      <div className="flex-1 glass-card border border-white/5 rounded-2xl p-6 overflow-y-auto custom-scrollbar">
        {!activeCol ? (
          <div className="h-full flex flex-col items-center justify-center text-on-surface-variant opacity-60">
            <BarChart3 size={48} className="mb-4 opacity-50" />
            <p className="font-semibold text-lg">Select a column on the left</p>
          </div>
        ) : !colStats ? null : colStats.type === 'numeric' ? (
          <NumericPanel colStats={colStats} activeCol={activeCol} />
        ) : (
          <CategoricalPanel colStats={colStats} activeCol={activeCol} />
        )}
      </div>
    </div>
  )
}

function NumericPanel({ colStats, activeCol }) {
  const stats = [
    ['Min',    formatNumber(colStats.min)],
    ['Max',    formatNumber(colStats.max)],
    ['Mean',   formatNumber(colStats.mean)],
    ['Median', formatNumber(colStats.median)],
    ['Std Dev',formatNumber(colStats.std)],
    ['Q1',     formatNumber(colStats.q1)],
    ['Q3',     formatNumber(colStats.q3)],
    ['Unique', colStats.unique],
    ['Nulls',  `${colStats.nulls} (${colStats.nullPct}%)`],
    ['Outliers',colStats.outliers],
  ]
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Hash size={24} className="text-cyan-400" />
        <h3 className="text-xl font-bold text-on-surface">{activeCol} <span className="text-sm font-medium text-on-surface-variant ml-2 tracking-normal">— Numeric</span></h3>
      </div>
      
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {stats.map(([l,v])=>(
          <div key={l} className="bg-surface-container-low p-3 rounded-xl border border-outline-variant/10 flex flex-col gap-1">
            <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">{l}</span>
            <span className="text-sm font-semibold text-on-surface truncate">{v}</span>
          </div>
        ))}
      </div>
      
      {/* Histogram */}
      <div className="bg-surface-container-low border border-outline-variant/10 rounded-2xl p-5">
        <p className="font-bold text-sm text-on-surface mb-4">Histogram Distribution</p>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={colStats.histogram} margin={{ top:10, right:10, left:-20, bottom:0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="bin" tick={{ fontSize:10, fill:'#a1a1aa' }} />
            <YAxis tick={{ fontSize:10, fill:'#a1a1aa' }} />
            <Tooltip content={<CUSTOM_TOOLTIP />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
            <Bar dataKey="count" radius={[4,4,0,0]} fill="#22d3ee" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function CategoricalPanel({ colStats, activeCol }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Type size={24} className="text-indigo-400" />
        <h3 className="text-xl font-bold text-on-surface">{activeCol} <span className="text-sm font-medium text-on-surface-variant ml-2 tracking-normal">— Categorical</span></h3>
      </div>
      
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-surface-container-low p-3 rounded-xl border border-outline-variant/10 flex flex-col gap-1"><span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Total values</span><span className="text-lg font-semibold text-on-surface truncate">{colStats.count}</span></div>
        <div className="bg-surface-container-low p-3 rounded-xl border border-outline-variant/10 flex flex-col gap-1"><span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Unique values</span><span className="text-lg font-semibold text-on-surface truncate">{colStats.unique}</span></div>
        <div className="bg-surface-container-low p-3 rounded-xl border border-outline-variant/10 flex flex-col gap-1"><span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">Nulls</span><span className="text-lg font-semibold text-on-surface truncate">{colStats.nulls} ({colStats.nullPct}%)</span></div>
      </div>

      <div className="bg-surface-container-low border border-outline-variant/10 rounded-2xl p-5">
        <p className="font-bold text-sm text-on-surface mb-4">Top Frequencies</p>
        <ResponsiveContainer width="100%" height={Math.max(colStats.topValues.length * 40, 200)}>
          <BarChart layout="vertical" data={colStats.topValues} margin={{ top:0, right:20, left:0, bottom:0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize:10, fill:'#a1a1aa' }} />
            <YAxis type="category" dataKey="value" tick={{ fontSize:11, fill:'#e4e4e7' }} width={120} />
            <Tooltip content={<CUSTOM_TOOLTIP />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
            <Bar dataKey="count" radius={[0,4,4,0]}>
              {colStats.topValues.map((_,i)=><Cell key={i} fill={chartColor(i)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/* ─── Correlation Tab ─── */
function CorrelationTab({ corrData }) {
  const { cols, matrix } = corrData
  if (cols.length < 2) return (
    <div className="h-full flex flex-col items-center justify-center text-on-surface-variant opacity-60 animate-in fade-in">
      <TrendingUp size={48} className="mb-4 opacity-50" />
      <p className="font-semibold text-lg">Need at least 2 numeric columns for correlation analysis.</p>
    </div>
  )
  const corrColor = (v) => {
    const abs = Math.abs(v)
    if (abs > 0.7) return v > 0 ? 'rgba(16,185,129,0.7)' : 'rgba(244,63,94,0.7)'
    if (abs > 0.3) return v > 0 ? 'rgba(6,182,212,0.4)'  : 'rgba(245,158,11,0.4)'
    return 'rgba(255,255,255,0.05)'
  }
  return (
    <div className="glass-card border border-white/5 rounded-2xl p-8 max-w-5xl mx-auto w-full animate-in slide-in-from-bottom-4 duration-300">
      <p className="font-bold text-lg text-on-surface mb-6">Correlation Matrix (Pearson)</p>
      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-2 border border-outline-variant/10 bg-surface-container min-w-[120px]" />
              {cols.map(c => <th key={c} className="p-2 border border-outline-variant/10 bg-surface-container text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={cols[i]}>
                <td className="p-2 border border-outline-variant/10 bg-surface-container text-[10px] font-bold text-on-surface-variant uppercase tracking-wider whitespace-nowrap">{cols[i]}</td>
                {row.map((val, j) => (
                  <td key={j} className="p-2 border border-outline-variant/10 text-center text-xs font-semibold font-mono transition-colors" style={{ background: corrColor(val), color: Math.abs(val) > 0.3 ? '#fff' : 'var(--text-muted)' }}>
                    {val.toFixed(2)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-6 mt-6 pt-4 border-t border-outline-variant/10 text-xs font-medium text-on-surface-variant">
        <span className="flex items-center gap-2"><div className="w-3 h-3 rounded bg-emerald-500/70" /> Strong positive</span>
        <span className="flex items-center gap-2"><div className="w-3 h-3 rounded bg-rose-500/70" /> Strong negative</span>
        <span className="flex items-center gap-2"><div className="w-3 h-3 rounded bg-surface-container-highest" /> Weak/No correlation</span>
      </div>
    </div>
  )
}

/* ─── Data Tab ─── */
function DataTab({ data, columns }) {
  const [page, setPage] = useState(0)
  const pageSize = 50
  const totalPages = Math.ceil(data.length / pageSize)
  const pageData = data.slice(page * pageSize, (page+1) * pageSize)
  return (
    <div className="h-full flex flex-col glass-card border border-white/5 rounded-2xl overflow-hidden animate-in slide-in-from-bottom-4 duration-300">
      <div className="flex items-center justify-between p-4 bg-surface-container-high/50 border-b border-outline-variant/10">
        <p className="text-sm font-bold text-on-surface">Raw Data Preview</p>
        <div className="flex items-center gap-3">
          <button className="h-8 px-3 rounded bg-surface-container-highest hover:bg-surface-container text-xs font-bold text-on-surface-variant transition-colors disabled:opacity-50" disabled={page===0} onClick={()=>setPage(p=>p-1)}>Prev</button>
          <span className="text-xs font-semibold text-on-surface-variant">Page {page+1} of {totalPages}</span>
          <button className="h-8 px-3 rounded bg-surface-container-highest hover:bg-surface-container text-xs font-bold text-on-surface-variant transition-colors disabled:opacity-50" disabled={page>=totalPages-1} onClick={()=>setPage(p=>p+1)}>Next</button>
        </div>
      </div>
      <div className="flex-1 overflow-auto custom-scrollbar bg-surface-container-low/50">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="sticky top-0 bg-surface-container-high z-10 shadow-sm">
            <tr>{columns.slice(0,15).map(c=><th key={c} className="p-3 font-bold text-on-surface-variant uppercase tracking-wider text-[10px] border-b border-outline-variant/10 whitespace-nowrap">{c}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5 font-mono text-[11px]">
            {pageData.map((row,i)=>(
              <tr key={i} className="hover:bg-surface-container-highest/30">
                {columns.slice(0,15).map(c=>(
                  <td key={c} className={`p-3 whitespace-nowrap truncate max-w-[200px] ${row[c]==null||row[c]===''?'text-on-surface-variant/30 italic':'text-on-surface'}`}>{String(row[c]??'null')}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ─── AI Suggestions Tab ─── */
function AITab({ data, loading, rejectedIds, acceptedIds, onAccept, onReject, onRefresh }) {
  const navigate = useNavigate()
  const { id } = useParams()

  if (loading || !data) return (
    <div className="h-full flex flex-col items-center justify-center text-on-surface-variant opacity-60 animate-in fade-in">
      <Loader2 size={48} className="animate-spin mb-4 text-primary" />
      <p className="font-semibold text-lg text-on-surface">Generating AI suggestions…</p>
      <p className="text-sm">Running distilBERT heuristics.</p>
    </div>
  )

  const pending = data.suggestions.filter(s => !rejectedIds.has(s.id) && !acceptedIds.has(s.id))
  const accepted = data.suggestions.filter(s => acceptedIds.has(s.id))

  const handleApplyAll = () => {
    navigate(`/clean/${id}`)
  }

  return (
    <div className="max-w-4xl mx-auto w-full flex flex-col gap-6 animate-in slide-in-from-bottom-4 duration-300">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 glass-card border border-white/5 rounded-2xl shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
            <Sparkles size={24} />
          </div>
          <div>
            <p className="font-bold text-lg text-on-surface">AI Data Quality Suggestions</p>
            <p className="text-sm font-medium text-on-surface-variant mt-1">Powered by distilBERT + IsolationForest</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button className="h-10 px-4 rounded-xl border border-outline-variant/20 hover:bg-surface-container-highest transition-colors font-bold text-sm text-on-surface flex items-center gap-2" onClick={onRefresh}>
            <Zap size={16} className="text-amber-400" /> Retry Scan
          </button>
          {accepted.length > 0 && (
            <button className="h-10 px-5 rounded-xl bg-primary hover:bg-primary-fixed transition-colors font-bold text-sm text-on-primary flex items-center gap-2 shadow-lg shadow-primary/20" onClick={handleApplyAll}>
              <Wand2 size={16} /> Apply {accepted.length} Fixes
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-4">
        {pending.length === 0 && accepted.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-on-surface-variant border-2 border-dashed border-outline-variant/20 rounded-2xl">
             <CheckCircle size={48} className="text-emerald-400 mb-4 opacity-50" />
             <p className="font-bold text-lg">No pending suggestions.</p>
          </div>
        )}
        {pending.map(s => (
          <div key={s.id} className="glass-card border border-white/5 rounded-2xl p-5 shadow-sm hover:border-outline-variant/30 transition-all flex flex-col sm:flex-row gap-5 items-start">
            <div className={`mt-1 p-2 rounded-lg ${s.type === 'warning' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' : s.type === 'info' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'}`}>
              {s.type === 'warning' ? <ShieldAlert size={20}/> : s.type === 'info' ? <Lightbulb size={20}/> : <CheckCircle size={20}/>}
            </div>
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="font-bold text-base text-on-surface">{s.column || 'Dataset'}</span>
                {s.label && <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-surface-container-highest text-on-surface-variant uppercase border border-outline-variant/10">{s.label}</span>}
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${s.impact === 'high' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : s.impact === 'medium' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-surface-container-highest text-on-surface-variant border-outline-variant/10'}`}>
                  Impact: {s.impact}
                </span>
              </div>
              <p className="text-sm font-medium text-on-surface-variant leading-relaxed">{s.text}</p>
            </div>
            {s.action && (
              <div className="flex flex-row sm:flex-col gap-2 shrink-0 w-full sm:w-auto mt-2 sm:mt-0 pt-3 sm:pt-0 border-t sm:border-t-0 border-outline-variant/10">
                <button className="flex-1 sm:flex-none h-9 px-4 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 font-bold text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2" onClick={() => onAccept(s.id)}>
                  <CheckCircle size={14}/> Accept
                </button>
                <button className="flex-1 sm:flex-none h-9 px-4 rounded-lg bg-surface-container-highest hover:bg-rose-500/10 hover:text-rose-400 text-on-surface-variant border border-transparent font-bold text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2" onClick={() => onReject(s.id)}>
                  <XCircle size={14}/> Reject
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

/* ─── Anomalies Tab ─── */
function AnomaliesTab({ data, loading, onRefresh }) {
  if (loading || !data) return (
    <div className="h-full flex flex-col items-center justify-center text-on-surface-variant opacity-60 animate-in fade-in">
      <Loader2 size={48} className="animate-spin mb-4 text-rose-400" />
      <p className="font-semibold text-lg text-on-surface">Running IsolationForest…</p>
      <p className="text-sm">Scanning for multi-dimensional anomalies.</p>
    </div>
  )

  const { anomaly_count, total_rows, columns_used, anomaly_rows } = data

  if (anomaly_count === 0) return (
    <div className="h-full flex flex-col items-center justify-center text-on-surface-variant border-2 border-dashed border-outline-variant/20 rounded-2xl animate-in zoom-in-95">
      <CheckCircle size={64} className="text-emerald-400 mb-4 opacity-50" />
      <p className="font-bold text-2xl text-on-surface mb-2">No anomalies detected</p>
      <p className="text-muted text-sm max-w-sm text-center">Checked {total_rows} rows across {columns_used?.length || 0} numeric columns using IsolationForest algorithm.</p>
    </div>
  )

  return (
    <div className="flex flex-col h-full gap-6 animate-in slide-in-from-bottom-4 duration-300">
      <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center gap-5 shadow-lg shadow-rose-500/5 shrink-0">
        <div className="w-14 h-14 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center border border-rose-500/30">
          <ShieldAlert size={28} />
        </div>
        <div>
          <p className="font-black text-2xl text-rose-400">{anomaly_count} Anomalies Detected</p>
          <p className="text-sm font-medium text-rose-400/80 mt-1">Found in {((anomaly_count / total_rows) * 100).toFixed(1)}% of rows using IsolationForest.</p>
        </div>
      </div>

      <div className="flex-1 flex flex-col glass-card border border-white/5 rounded-2xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-outline-variant/10 bg-surface-container-high/50">
          <p className="font-bold text-sm text-on-surface">Flagged Rows Sample</p>
        </div>
        <div className="flex-1 overflow-auto custom-scrollbar bg-surface-container-low/50">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="sticky top-0 bg-surface-container-high z-10 shadow-sm">
              <tr>{columns_used?.map(c => <th key={c} className="p-3 font-bold text-on-surface-variant uppercase tracking-wider text-[10px] border-b border-outline-variant/10 whitespace-nowrap">{c}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/5 font-mono text-[11px]">
              {anomaly_rows?.slice(0, 100).map((row, i) => (
                <tr key={i} className="bg-rose-500/5 hover:bg-rose-500/10 transition-colors">
                  {columns_used?.map(c => (
                    <td key={c} className="p-3 text-rose-200/90 whitespace-nowrap">{String(row[c] ?? 'null')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
