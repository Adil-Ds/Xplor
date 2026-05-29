import { useState, useMemo, useRef, useEffect } from 'react'
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import {
  Plus, Trash2, Settings, BarChart3, TrendingUp, PieChart as PieIcon,
  Circle, ScatterChart as ScatterIcon, Table, Type, Hash, Save,
  Download, RefreshCw, Copy, Maximize2, Filter, X
} from 'lucide-react'
import { useDashboardStore } from '../store/dashboardStore'
import { useDatasetStore } from '../store/datasetStore'
import { uuid, chartColor, formatNumber } from '../utils/helpers'
import toast from 'react-hot-toast'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

import { ResponsiveGridLayout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

/* ─── Widget type definitions ─── */
const WIDGET_TYPES = [
  { id: 'bar',     label: 'Bar Chart',    icon: BarChart3,     needsX: true,  needsY: true,  defW: 4, defH: 3 },
  { id: 'line',    label: 'Line Chart',   icon: TrendingUp,    needsX: true,  needsY: true,  defW: 4, defH: 3 },
  { id: 'area',    label: 'Area Chart',   icon: TrendingUp,    needsX: true,  needsY: true,  defW: 4, defH: 3 },
  { id: 'pie',     label: 'Pie / Donut',  icon: PieIcon,       needsX: true,  needsY: true,  defW: 3, defH: 3 },
  { id: 'scatter', label: 'Scatter Plot', icon: ScatterIcon,   needsX: true,  needsY: true,  defW: 4, defH: 3 },
  { id: 'kpi',     label: 'KPI Card',     icon: Hash,          needsX: false, needsY: true,  defW: 2, defH: 2 },
  { id: 'table',   label: 'Data Table',   icon: Table,         needsX: false, needsY: false, defW: 6, defH: 4 },
  { id: 'text',    label: 'Text Block',   icon: Type,          needsX: false, needsY: false, defW: 3, defH: 2 },
]

const AGGREGATIONS = ['sum', 'mean', 'count', 'min', 'max']

/* ─── Data prep & Slicers ─── */
function applySlicers(data, slicers) {
  if (!data || !slicers) return data || []
  return data.filter(row => {
    for (const [col, selectedValues] of Object.entries(slicers)) {
      if (selectedValues && selectedValues.length > 0) {
        if (!selectedValues.includes(String(row[col] ?? ''))) return false
      }
    }
    return true
  })
}

function buildWidgetData(widget, data) {
  if (!data?.length || !widget.yCol) return []
  const { xCol, yCol, aggregate } = widget

  if (!xCol) {
    const vals = data.map(r=>Number(r[yCol])).filter(v=>!isNaN(v))
    if (!vals.length) return [{ value: 0 }]
    const agg = aggregate || 'sum'
    const sorted = [...vals].sort((a,b)=>a-b)
    const value = {
      sum:   vals.reduce((s,v)=>s+v,0),
      mean:  vals.reduce((s,v)=>s+v,0)/vals.length,
      count: vals.length,
      min:   sorted[0],
      max:   sorted[sorted.length-1],
    }[agg]
    return [{ value }]
  }

  const groups = {}
  data.forEach(r => {
    const key = String(r[xCol] ?? 'null')
    if (!groups[key]) groups[key] = []
    const v = Number(r[yCol])
    if (!isNaN(v)) groups[key].push(v)
  })

  return Object.entries(groups).slice(0,50).map(([key, vals]) => {
    const sorted = [...vals].sort((a,b)=>a-b)
    const agg = aggregate || 'sum'
    const value = {
      sum:   vals.reduce((s,v)=>s+v,0),
      mean:  vals.reduce((s,v)=>s+v,0)/Math.max(vals.length,1),
      count: vals.length,
      min:   sorted[0] ?? 0,
      max:   sorted[sorted.length-1] ?? 0,
    }[agg] ?? 0
    return { name: key, value: +value.toFixed(2) }
  }).sort((a,b)=>b.value-a.value)
}

const CUSTOM_TOOLTIP = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-container-high border border-outline-variant/20 rounded-xl p-3 text-xs shadow-xl z-[999]">
      {label && <p className="text-on-surface-variant font-medium mb-2">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} className="font-semibold flex items-center gap-2" style={{ color: p.color || 'var(--text-primary)' }}>
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color || 'var(--text-primary)' }} />
          {p.name || p.dataKey}: <span>{formatNumber(p.value)}</span>
        </p>
      ))}
    </div>
  )
}

/* ─── Widget renderer ─── */
function WidgetContent({ widget, data }) {
  const chartData = useMemo(() => buildWidgetData(widget, data), [widget, data])
  const color0 = chartColor(0)

  if (widget.type === 'text') {
    return (
      <div className="flex flex-col h-full w-full p-4 overflow-y-auto custom-scrollbar">
        <p className="text-on-surface whitespace-pre-wrap">{widget.textContent || 'Double-click settings to edit text'}</p>
      </div>
    )
  }

  if (widget.type === 'kpi') {
    const val = chartData[0]?.value ?? 0
    return (
      <div className="flex flex-col h-full w-full items-center justify-center p-4">
        <p className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">{widget.title || widget.yCol || 'KPI'}</p>
        <p className="text-4xl font-black tracking-tight my-2 truncate max-w-full" style={{ color: color0 }}>{formatNumber(val)}</p>
        <p className="text-[10px] font-bold text-on-surface-variant/70 uppercase tracking-wider bg-surface-container-highest px-2 py-1 rounded-full">{widget.aggregate || 'sum'}</p>
      </div>
    )
  }

  if (widget.type === 'table') {
    const cols = Object.keys(data[0] ?? {}).slice(0, 8)
    return (
      <div className="h-full w-full overflow-auto custom-scrollbar">
        <table className="w-full text-left border-collapse text-[11px]">
          <thead className="sticky top-0 bg-surface-container-high z-10 shadow-sm">
            <tr>
              {cols.map(c=><th key={c} className="p-2 font-bold text-on-surface-variant uppercase tracking-wider border-b border-outline-variant/10 whitespace-nowrap">{c}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5">
            {data.slice(0,50).map((row,i)=>(
              <tr key={i} className="hover:bg-surface-container-highest/50 transition-colors">
                {cols.map(c=><td key={c} className="p-2 text-on-surface whitespace-nowrap truncate max-w-[150px]">{String(row[c]??'')}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  if (!chartData.length) {
    return <div className="flex h-full w-full items-center justify-center text-sm font-medium text-on-surface-variant opacity-60">Configure X/Y columns</div>
  }

  const commonProps = {
    data: chartData,
    margin: { top: 15, right: 15, left: -20, bottom: 5 },
  }

  switch (widget.type) {
    case 'bar':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#a1a1aa' }} />
            <YAxis tick={{ fontSize: 10, fill: '#a1a1aa' }} />
            <Tooltip content={<CUSTOM_TOOLTIP />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
            <Bar dataKey="value" radius={[4,4,0,0]}>
              {chartData.map((_,i)=><Cell key={i} fill={chartColor(i)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )
    case 'line':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#a1a1aa' }} />
            <YAxis tick={{ fontSize: 10, fill: '#a1a1aa' }} />
            <Tooltip content={<CUSTOM_TOOLTIP />} />
            <Line type="monotone" dataKey="value" stroke={color0} strokeWidth={2} dot={{ r:3, fill: color0, strokeWidth: 0 }} activeDot={{ r: 5, strokeWidth: 0 }} />
          </LineChart>
        </ResponsiveContainer>
      )
    case 'area':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart {...commonProps}>
            <defs>
              <linearGradient id={`areaGrad-${widget.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={color0} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color0} stopOpacity={0}   />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#a1a1aa' }} />
            <YAxis tick={{ fontSize: 10, fill: '#a1a1aa' }} />
            <Tooltip content={<CUSTOM_TOOLTIP />} />
            <Area type="monotone" dataKey="value" stroke={color0} fill={`url(#areaGrad-${widget.id})`} strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      )
    case 'pie':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%"
              innerRadius="50%" outerRadius="80%" paddingAngle={2} stroke="none">
              {chartData.map((_,i)=><Cell key={i} fill={chartColor(i)} />)}
            </Pie>
            <Tooltip content={<CUSTOM_TOOLTIP />} />
            <Legend wrapperStyle={{ fontSize: 11, color: '#a1a1aa' }} />
          </PieChart>
        </ResponsiveContainer>
      )
    case 'scatter':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="name" type="category" tick={{ fontSize: 10, fill: '#a1a1aa' }} />
            <YAxis dataKey="value" tick={{ fontSize: 10, fill: '#a1a1aa' }} />
            <Tooltip content={<CUSTOM_TOOLTIP />} cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.1)' }} />
            <Scatter data={chartData} fill={color0} />
          </ScatterChart>
        </ResponsiveContainer>
      )
    default:
      return null
  }
}

/* ─── Widget config panel ─── */
function WidgetConfigPanel({ widget, ds, onUpdate, onClose }) {
  const columns = ds?.columnNames ?? []
  const def = WIDGET_TYPES.find(t=>t.id===widget.type)
  return (
    <div className="absolute right-4 top-20 w-80 bg-surface-container-high/90 backdrop-blur-xl border border-outline-variant/20 rounded-2xl shadow-2xl z-50 p-5 flex flex-col gap-4 animate-in slide-in-from-right-8 duration-300">
      <div className="flex items-center justify-between pb-3 border-b border-outline-variant/10">
        <p className="font-bold text-on-surface">Configure Widget</p>
        <button className="w-8 h-8 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-highest hover:text-on-surface transition-colors" onClick={onClose}><X size={16}/></button>
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Title</label>
        <input className="w-full h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all" value={widget.title||''} onChange={e=>onUpdate({title:e.target.value})} placeholder="Widget title" />
      </div>

      {def?.needsX && (
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">X-axis Column (Category)</label>
          <select className="w-full h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all appearance-none cursor-pointer" value={widget.xCol||''} onChange={e=>onUpdate({xCol:e.target.value})}>
            <option value="">None</option>
            {columns.map(c=><option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      )}
      {def?.needsY && widget.type !== 'table' && widget.type !== 'text' && (
        <>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Y-axis Column (Value)</label>
            <select className="w-full h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all appearance-none cursor-pointer" value={widget.yCol||''} onChange={e=>onUpdate({yCol:e.target.value})}>
              <option value="">None</option>
              {columns.map(c=><option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Aggregation</label>
            <select className="w-full h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all appearance-none cursor-pointer" value={widget.aggregate||'sum'} onChange={e=>onUpdate({aggregate:e.target.value})}>
              {AGGREGATIONS.map(a=><option key={a} value={a}>{a}</option>)}
            </select>
          </div>
        </>
      )}
      {widget.type === 'text' && (
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Content</label>
          <textarea className="w-full p-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all resize-y" rows={3} value={widget.textContent||''} onChange={e=>onUpdate({textContent:e.target.value})} placeholder="Enter text here…" />
        </div>
      )}
    </div>
  )
}

/* ─── Slicers Config Panel ─── */
function SlicerConfigPanel({ dash, ds, onUpdate, onClose }) {
  const columns = ds?.columnNames ?? []
  const [newSlicerCol, setNewSlicerCol] = useState('')

  const handleAddSlicer = () => {
    if (!newSlicerCol) return
    const slicers = dash.slicers || {}
    if (slicers[newSlicerCol]) return
    onUpdate({ slicers: { ...slicers, [newSlicerCol]: [] } })
    setNewSlicerCol('')
  }

  const handleRemoveSlicer = (col) => {
    const slicers = { ...dash.slicers }
    delete slicers[col]
    onUpdate({ slicers })
  }

  return (
    <div className="absolute left-6 top-16 w-80 bg-surface-container-high/90 backdrop-blur-xl border border-outline-variant/20 rounded-2xl shadow-2xl z-50 p-5 flex flex-col gap-4 animate-in slide-in-from-left-8 duration-300">
      <div className="flex items-center justify-between pb-3 border-b border-outline-variant/10">
        <p className="font-bold text-on-surface flex items-center gap-2"><Filter size={16} className="text-cyan-400" /> Dashboard Slicers</p>
        <button className="w-8 h-8 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-highest hover:text-on-surface transition-colors" onClick={onClose}><X size={16}/></button>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <select 
            className="flex-1 h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all appearance-none cursor-pointer"
            value={newSlicerCol}
            onChange={e=>setNewSlicerCol(e.target.value)}
          >
            <option value="">Select column to filter...</option>
            {columns.map(c=><option key={c} value={c}>{c}</option>)}
          </select>
          <button className="h-9 px-3 rounded-lg bg-surface-container-highest text-primary hover:bg-primary/20 transition-colors font-bold text-sm" onClick={handleAddSlicer}>Add</button>
        </div>
      </div>

      <div className="flex flex-col gap-3 mt-2">
        {Object.keys(dash.slicers || {}).map(col => (
          <div key={col} className="p-3 rounded-xl border border-outline-variant/10 bg-surface-container flex items-center justify-between">
            <span className="font-semibold text-sm text-on-surface">{col}</span>
            <button className="text-rose-400 hover:text-rose-300 transition-colors" onClick={()=>handleRemoveSlicer(col)}>
              <Trash2 size={14} />
            </button>
          </div>
        ))}
        {Object.keys(dash.slicers || {}).length === 0 && (
          <p className="text-xs text-on-surface-variant italic text-center py-4">No slicers added yet. Slicers allow you to globally filter all charts on this dashboard.</p>
        )}
      </div>
    </div>
  )
}

/* ─── Slicer Bar (Active Filters) ─── */
function SlicerBar({ dash, ds, onUpdate }) {
  const slicers = dash.slicers || {}
  const slicerCols = Object.keys(slicers)
  if (slicerCols.length === 0) return null

  const getUniqueValues = (col) => {
    const data = ds?.preview || []
    return Array.from(new Set(data.map(r => String(r[col] ?? '')))).filter(Boolean)
  }

  const handleToggleValue = (col, val) => {
    const current = slicers[col] || []
    const updated = current.includes(val) ? current.filter(v => v !== val) : [...current, val]
    onUpdate({ slicers: { ...slicers, [col]: updated } })
  }

  return (
    <div className="px-6 py-3 bg-surface-container-lowest border-b border-outline-variant/10 flex items-center gap-4 overflow-x-auto shrink-0 custom-scrollbar z-10 relative shadow-sm">
      <div className="flex items-center gap-2 text-on-surface-variant shrink-0">
        <Filter size={16} />
        <span className="text-xs font-bold uppercase tracking-wider">Filters:</span>
      </div>
      
      {slicerCols.map(col => {
        const activeVals = slicers[col] || []
        const options = getUniqueValues(col).slice(0, 15) // Limit to top 15 distinct values for the UI
        return (
          <div key={col} className="flex items-center gap-2 bg-surface-container-high px-3 py-1.5 rounded-xl border border-outline-variant/10 shrink-0">
            <span className="text-xs font-semibold text-on-surface">{col}:</span>
            <div className="flex items-center gap-1">
              {options.map(opt => (
                <button
                  key={opt}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors border ${activeVals.includes(opt) ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' : 'bg-surface-container border-transparent hover:border-outline-variant/30 text-on-surface-variant hover:text-on-surface'}`}
                  onClick={() => handleToggleValue(col, opt)}
                >
                  {opt}
                </button>
              ))}
              {getUniqueValues(col).length > 15 && <span className="text-xs text-on-surface-variant">...</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ─── Main Dashboard page ─── */
export default function DashboardPage() {
  const { dashboards, activeDashboard, createDashboard, setActive, deleteDashboard,
          addWidget, updateWidget, removeWidget, updateDashboard } = useDashboardStore()
  const { datasets } = useDatasetStore()
  const canvasRef    = useRef(null)

  const [newDashName, setNewDashName]   = useState('')
  const [showNewDash, setShowNewDash]   = useState(false)
  const [selectedWidget, setSelectedWidget] = useState(null) // widget id being configured
  const [addingType, setAddingType]     = useState(null)      // widget type being added
  const [addingDsId, setAddingDsId]     = useState(datasets[0]?.id ?? '')
  const [showAddPanel, setShowAddPanel] = useState(false)
  const [showSlicerPanel, setShowSlicerPanel] = useState(false)

  const dash = activeDashboard
  const ds   = datasets.find(d => d.id === (dash?.datasetId ?? addingDsId))

  const handleCreateDashboard = () => {
    if (!newDashName.trim()) { toast.error('Enter a name'); return }
    const id = uuid()
    createDashboard({
      id, name: newDashName.trim(),
      datasetId: addingDsId || datasets[0]?.id || null,
      widgets: [], layout: [], slicers: {}, createdAt: new Date().toISOString(),
    })
    setActive(id)
    setNewDashName('')
    setShowNewDash(false)
    toast.success('Dashboard created')
  }

  const handleAddWidget = () => {
    if (!dash) return
    if (!addingType) { toast.error('Select widget type'); return }
    const wId = uuid()
    const widget = {
      id:    wId,
      type:  addingType.id,
      title: addingType.label,
      xCol: null, yCol: null, aggregate: 'sum', textContent: '',
    }
    
    // Add to grid layout
    const newLayoutItem = {
      i: wId,
      x: (dash.widgets.length * addingType.defW) % 12,
      y: Infinity, // puts it at the bottom
      w: addingType.defW,
      h: addingType.defH,
      minW: 2, minH: 2
    }
    
    addWidget(dash.id, widget)
    updateDashboard(dash.id, { layout: [...(dash.layout || []), newLayoutItem] })
    
    setSelectedWidget(wId)
    setShowAddPanel(false)
    setAddingType(null)
    toast.success(`${addingType.label} added`)
  }

  const handleRemoveWidget = (wId) => {
    removeWidget(dash.id, wId)
    if (dash.layout) {
      updateDashboard(dash.id, { layout: dash.layout.filter(l => l.i !== wId) })
    }
  }

  const handleLayoutChange = (layout) => {
    if (!dash) return
    updateDashboard(dash.id, { layout })
  }

  const handleExportPDF = async () => {
    if (!canvasRef.current) return
    toast.loading('Generating PDF…', { id: 'pdf' })
    try {
      const canvas = await html2canvas(canvasRef.current, { backgroundColor: '#0f1016', scale: 1.5 })
      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF({ orientation: 'landscape', unit: 'px', format: [canvas.width/1.5, canvas.height/1.5] })
      pdf.addImage(imgData, 'PNG', 0, 0, canvas.width/1.5, canvas.height/1.5)
      pdf.save(`${dash?.name ?? 'dashboard'}.pdf`)
      toast.success('PDF downloaded', { id: 'pdf' })
    } catch {
      toast.error('Export failed', { id: 'pdf' })
    }
  }

  const editingWidget = dash?.widgets?.find(w => w.id === selectedWidget)
  const activeDsForWidget = datasets.find(d => d.id === dash?.datasetId)
  
  // Apply slicers to data before passing to widgets
  const filteredData = useMemo(() => {
    return applySlicers(activeDsForWidget?.preview || [], dash?.slicers)
  }, [activeDsForWidget, dash?.slicers])

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-surface-container-low animate-in fade-in duration-500 relative">
      {/* Top toolbar */}
      <div className="flex items-center justify-between px-6 py-3 bg-surface-container border-b border-outline-variant/10 z-20 shadow-sm shrink-0">
        <div className="flex items-center gap-3">
          {/* Dashboard selector */}
          <div className="relative w-56">
            <BarChart3 size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-primary pointer-events-none" />
            <select
              className="w-full h-9 pl-9 pr-8 rounded-lg bg-surface-container-high border border-outline-variant/20 text-sm font-semibold text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all appearance-none cursor-pointer shadow-inner"
              value={dash?.id ?? ''}
              onChange={e => { setActive(e.target.value); setSelectedWidget(null) }}
            >
              <option value="">Select dashboard…</option>
              {dashboards.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>

          <button
            className="h-9 px-3 rounded-lg border border-outline-variant/30 text-on-surface font-semibold text-sm hover:bg-surface-container-highest hover:border-outline-variant/50 transition-all flex items-center gap-1.5"
            onClick={() => setShowNewDash(v => !v)}
          >
            <Plus size={14} /> New
          </button>

          {dash && (
            <button className="h-9 px-3 rounded-lg text-rose-400 hover:bg-rose-500/10 transition-all flex items-center gap-1.5 text-sm font-medium ml-2" onClick={() => { if(window.confirm(`Delete "${dash.name}"?`)) { deleteDashboard(dash.id); setSelectedWidget(null) } }}>
              <Trash2 size={14} /> Delete
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {dash && (
            <>
              <button
                className={`h-9 px-3 rounded-lg border transition-all flex items-center gap-1.5 text-sm font-medium ${showSlicerPanel ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-400' : 'border-outline-variant/30 text-on-surface hover:bg-surface-container-highest hover:border-outline-variant/50'}`}
                onClick={() => setShowSlicerPanel(v=>!v)}
              >
                <Filter size={14} /> Slicers
              </button>
              <div className="w-px h-6 bg-outline-variant/20 mx-2" />
              <button
                className="h-9 px-4 rounded-lg bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed hover:text-on-primary-fixed transition-colors flex items-center gap-1.5 shadow-md shadow-primary/20"
                onClick={() => setShowAddPanel(v=>!v)}
              >
                <Plus size={16} /> Add Widget
              </button>
              <button className="h-9 px-3 rounded-lg border border-outline-variant/30 text-on-surface font-semibold text-sm hover:bg-surface-container-highest transition-all flex items-center gap-1.5 ml-2" onClick={handleExportPDF}>
                <Download size={14} /> PDF
              </button>
            </>
          )}
        </div>
      </div>

      {/* Slicer active bar */}
      {dash && <SlicerBar dash={dash} ds={activeDsForWidget} onUpdate={(patch) => updateDashboard(dash.id, patch)} />}

      {/* New dashboard form */}
      {showNewDash && (
        <div className="absolute top-16 left-6 z-50 bg-surface-container-high/90 backdrop-blur-xl border border-outline-variant/20 rounded-xl shadow-2xl p-4 flex gap-2 animate-in slide-in-from-top-4 duration-300">
          <input
            className="h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all w-48"
            value={newDashName}
            onChange={e=>setNewDashName(e.target.value)}
            placeholder="Dashboard name…"
            onKeyDown={e=>e.key==='Enter'&&handleCreateDashboard()}
            autoFocus
          />
          <select
            className="h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary outline-none transition-all appearance-none w-40"
            value={addingDsId}
            onChange={e=>setAddingDsId(e.target.value)}
          >
            <option value="">No dataset</option>
            {datasets.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          <button className="h-9 px-4 rounded-lg bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-colors" onClick={handleCreateDashboard}>Create</button>
          <button className="h-9 px-3 rounded-lg text-on-surface-variant hover:bg-surface-container-highest hover:text-on-surface transition-colors text-sm font-medium" onClick={()=>setShowNewDash(false)}>Cancel</button>
        </div>
      )}

      {/* Add widget panel */}
      {showAddPanel && (
        <div className="absolute top-16 right-6 z-50 bg-surface-container-high/90 backdrop-blur-xl border border-outline-variant/20 rounded-2xl shadow-2xl p-6 flex flex-col gap-4 animate-in slide-in-from-top-4 duration-300 w-[360px]">
          <div className="flex items-center justify-between">
            <p className="font-bold text-on-surface text-lg">Choose Widget Type</p>
            <button className="text-on-surface-variant hover:text-on-surface" onClick={()=>setShowAddPanel(false)}><X size={18}/></button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {WIDGET_TYPES.map(t => (
              <button
                key={t.id}
                className={`flex flex-col items-center justify-center gap-2 p-4 rounded-xl border transition-all ${
                  addingType?.id === t.id ? 'border-primary bg-primary/10 text-primary' : 'border-outline-variant/20 bg-surface-container hover:bg-surface-container-highest text-on-surface-variant hover:text-on-surface'
                }`}
                onClick={() => setAddingType(t)}
              >
                <t.icon size={24} strokeWidth={addingType?.id === t.id ? 2 : 1.5} />
                <span className="text-xs font-semibold">{t.label}</span>
              </button>
            ))}
          </div>
          <div className="flex gap-2 mt-2">
            <button className="flex-1 h-10 rounded-xl bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-colors disabled:opacity-50 disabled:cursor-not-allowed" onClick={handleAddWidget} disabled={!addingType}>
              Add to Dashboard
            </button>
          </div>
        </div>
      )}

      {/* Slicers Config panel */}
      {showSlicerPanel && dash && (
        <SlicerConfigPanel
          dash={dash}
          ds={activeDsForWidget}
          onUpdate={(patch) => updateDashboard(dash.id, patch)}
          onClose={() => setShowSlicerPanel(false)}
        />
      )}

      <div className="flex-1 overflow-auto bg-surface-container-low/50" ref={canvasRef}>
        {!dash ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-24 h-24 rounded-full bg-surface-container flex items-center justify-center text-on-surface-variant/50 mb-6 border border-outline-variant/10 shadow-inner">
              <BarChart3 size={48} strokeWidth={1} />
            </div>
            <p className="font-bold text-on-surface text-2xl mb-2">No dashboard selected</p>
            <p className="text-on-surface-variant mb-8 max-w-[300px] leading-relaxed">Create a new dashboard or select an existing one to get started analyzing your data.</p>
            <button className="h-12 px-6 rounded-xl bg-primary text-on-primary font-bold text-base hover:bg-primary-fixed transition-colors flex items-center gap-2 shadow-lg shadow-primary/20" onClick={() => setShowNewDash(true)}>
              <Plus size={20} /> Create Dashboard
            </button>
          </div>
        ) : (
          <div className="w-full h-full min-h-[600px] p-6">
            {(!dash.widgets || dash.widgets.length === 0) ? (
              <div className="flex flex-col items-center justify-center h-full max-h-[600px] rounded-3xl border-2 border-dashed border-outline-variant/20 bg-surface-container-low/30">
                <BarChart3 size={48} className="text-on-surface-variant/30 mb-4" strokeWidth={1} />
                <p className="text-on-surface-variant font-medium text-lg mb-4">Your dashboard is empty</p>
                <button className="h-10 px-5 rounded-xl bg-surface-container-highest text-on-surface font-bold text-sm hover:bg-surface-container transition-colors flex items-center gap-2" onClick={() => setShowAddPanel(true)}>
                  <Plus size={16} /> Add your first widget
                </button>
              </div>
            ) : (
              <ResponsiveGridLayout
                className="layout"
                layouts={{ lg: dash.layout || [] }}
                breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
                rowHeight={100}
                onLayoutChange={handleLayoutChange}
                draggableHandle=".drag-handle"
                isResizable={true}
                isDraggable={true}
                margin={[24, 24]}
              >
                {dash.widgets.map(widget => (
                  <div key={widget.id} className={`glass-card rounded-2xl border flex flex-col overflow-hidden transition-all duration-200 ${selectedWidget === widget.id ? 'border-primary shadow-[0_0_20px_rgba(99,102,241,0.2)] ring-1 ring-primary' : 'border-white/5 hover:border-outline-variant/30 hover:shadow-lg'}`}>
                    <div className="drag-handle flex items-center justify-between px-4 py-2 border-b border-outline-variant/10 bg-surface-container-low/80 cursor-move group">
                      <p className="font-semibold text-sm text-on-surface truncate flex-1 pr-2">{widget.title}</p>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" style={{ opacity: selectedWidget === widget.id ? 1 : undefined }}>
                        <button className="w-7 h-7 rounded flex items-center justify-center text-on-surface-variant hover:bg-surface-container-highest hover:text-primary transition-colors" onClick={e=>{e.stopPropagation();setSelectedWidget(selectedWidget===widget.id?null:widget.id)}} onMouseDown={e=>e.stopPropagation()}>
                          <Settings size={14} />
                        </button>
                        <button className="w-7 h-7 rounded flex items-center justify-center text-rose-400 hover:bg-rose-500/10 transition-colors" onClick={e=>{e.stopPropagation();handleRemoveWidget(widget.id)}} onMouseDown={e=>e.stopPropagation()}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                    <div className="flex-1 w-full h-[calc(100%-41px)] relative bg-surface-container-low/20 overflow-hidden" onMouseDown={e=>e.stopPropagation()}>
                      <WidgetContent
                        widget={widget}
                        data={filteredData}
                      />
                    </div>
                  </div>
                ))}
              </ResponsiveGridLayout>
            )}
          </div>
        )}
      </div>

      {/* Config panel */}
      {editingWidget && (
        <WidgetConfigPanel
          widget={editingWidget}
          ds={activeDsForWidget}
          onUpdate={(patch) => updateWidget(dash.id, editingWidget.id, patch)}
          onClose={() => setSelectedWidget(null)}
        />
      )}
    </div>
  )
}
