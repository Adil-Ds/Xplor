import { useState, useMemo, useRef, useCallback } from 'react'
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, LabelList,
} from 'recharts'
import {
  Plus, Trash2, Settings, BarChart3, BarChart2, TrendingUp,
  PieChart as PieIcon, Activity, Table, Type, Hash,
  Download, Filter, X, Sparkles, Loader2, Copy, Palette, RefreshCw,
} from 'lucide-react'
import { useDashboardStore } from '../store/dashboardStore'
import { useDatasetStore } from '../store/datasetStore'
import { uuid, chartColor, formatNumber } from '../utils/helpers'
import { dashboardAPI } from '../api/endpoints'
import toast from 'react-hot-toast'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import { ResponsiveGridLayout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

/* ─── Widget catalogue ─── */
const WIDGET_TYPES = [
  { id: 'bar',     label: 'Bar Chart',   icon: BarChart3,  needsX: true,  needsY: true,  defW: 4, defH: 3 },
  { id: 'hbar',    label: 'Horiz. Bar',  icon: BarChart2,  needsX: true,  needsY: true,  defW: 4, defH: 3 },
  { id: 'line',    label: 'Line Chart',  icon: TrendingUp, needsX: true,  needsY: true,  defW: 4, defH: 3 },
  { id: 'area',    label: 'Area Chart',  icon: TrendingUp, needsX: true,  needsY: true,  defW: 4, defH: 3 },
  { id: 'pie',     label: 'Donut',       icon: PieIcon,    needsX: true,  needsY: true,  defW: 3, defH: 3 },
  { id: 'scatter', label: 'Scatter',     icon: Activity,   needsX: true,  needsY: true,  defW: 4, defH: 3 },
  { id: 'kpi',     label: 'KPI Card',    icon: Hash,       needsX: false, needsY: true,  defW: 2, defH: 2 },
  { id: 'table',   label: 'Data Table',  icon: Table,      needsX: false, needsY: false, defW: 6, defH: 4 },
  { id: 'text',    label: 'Text Block',  icon: Type,       needsX: false, needsY: false, defW: 3, defH: 2 },
]

const AGGREGATIONS = ['sum', 'mean', 'count', 'min', 'max']

/**
 * Build an explicit grid layout for a batch of AI-generated widgets.
 * Avoids y:Infinity stacking for multiple widgets added at once.
 *
 *  Row 1 — KPI cards:  w = 12 / count (up to 4), h = 2
 *  Rows 2+ — Charts:   w = 6 each (2 per row), h = 3
 *  Tables/text:        w = 12, h = 4
 */
function buildAILayout(widgets, startY = 0) {
  const kpis   = widgets.filter(w => w.type === 'kpi')
  const charts = widgets.filter(w => !['kpi', 'table', 'text'].includes(w.type))
  const others = widgets.filter(w => ['table', 'text'].includes(w.type))
  const layouts = []
  let y = startY

  // KPI row
  if (kpis.length) {
    const kpiW = Math.floor(12 / Math.min(kpis.length, 4))
    kpis.forEach((w, i) => {
      layouts.push({ i: w.id, x: (i % 4) * kpiW, y: y + Math.floor(i / 4) * 2, w: kpiW, h: 2, minW: 2, minH: 2 })
    })
    y += Math.ceil(kpis.length / 4) * 2
  }

  // Chart rows — 2 per row, 6 wide each
  charts.forEach((w, i) => {
    layouts.push({ i: w.id, x: (i % 2) * 6, y: y + Math.floor(i / 2) * 3, w: 6, h: 3, minW: 2, minH: 2 })
  })
  if (charts.length) y += Math.ceil(charts.length / 2) * 3

  // Tables / text — full width
  others.forEach((w, i) => {
    layouts.push({ i: w.id, x: 0, y: y + i * 4, w: 12, h: 4, minW: 2, minH: 2 })
  })

  return layouts
}

const COLOR_THEMES = [
  { name: 'Vivid',  start: 0 },
  { name: 'Ocean',  start: 1 },
  { name: 'Forest', start: 2 },
  { name: 'Sunset', start: 4 },
  { name: 'Neon',   start: 7 },
]

/* ─── Data helpers ─── */
function applySlicers(data, slicers) {
  if (!data || !slicers) return data || []
  return data.filter(row => {
    for (const [col, selected] of Object.entries(slicers)) {
      if (selected?.length > 0 && !selected.includes(String(row[col] ?? ''))) return false
    }
    return true
  })
}

function buildWidgetData(widget, data) {
  if (!data?.length || !widget.yCol) return []
  const { xCol, yCol, aggregate } = widget

  if (!xCol) {
    const vals = data.map(r => Number(r[yCol])).filter(v => !isNaN(v))
    if (!vals.length) return [{ value: 0 }]
    const sorted = [...vals].sort((a, b) => a - b)
    const agg = aggregate || 'sum'
    const value = {
      sum:   vals.reduce((s, v) => s + v, 0),
      mean:  vals.reduce((s, v) => s + v, 0) / vals.length,
      count: vals.length,
      min:   sorted[0],
      max:   sorted[sorted.length - 1],
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

  return Object.entries(groups).slice(0, 50).map(([key, vals]) => {
    const sorted = [...vals].sort((a, b) => a - b)
    const agg = aggregate || 'sum'
    const value = {
      sum:   vals.reduce((s, v) => s + v, 0),
      mean:  vals.reduce((s, v) => s + v, 0) / Math.max(vals.length, 1),
      count: vals.length,
      min:   sorted[0] ?? 0,
      max:   sorted[sorted.length - 1] ?? 0,
    }[agg] ?? 0
    return { name: key, value: +value.toFixed(2) }
  }).sort((a, b) => b.value - a.value)
}

/* ─── Tooltip ─── */
const CUSTOM_TOOLTIP = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-container-high border border-outline-variant/20 rounded-xl p-3 text-xs shadow-xl z-[999]">
      {label && <p className="text-on-surface-variant font-medium mb-1.5">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} className="font-semibold flex items-center gap-2" style={{ color: p.color || '#e4e4e7' }}>
          <span className="w-2 h-2 rounded-full inline-block" style={{ background: p.color || '#e4e4e7' }} />
          {p.name || p.dataKey}: {formatNumber(p.value)}
        </p>
      ))}
    </div>
  )
}

/* ─── Widget renderer ─── */
function WidgetContent({ widget, data, onCrossFilter, crossFilter }) {
  const chartData = useMemo(() => buildWidgetData(widget, data), [widget, data])
  const cs = widget.colorStart ?? 0
  const color0 = chartColor(cs)

  const isCrossActive = crossFilter && crossFilter.col === widget.xCol
  const cellOpacity = (name) => isCrossActive && crossFilter.value !== String(name) ? 0.2 : 1

  const handleBarClick = useCallback((entry) => {
    if (!widget.xCol || !onCrossFilter || !entry?.name) return
    onCrossFilter(widget.xCol, entry.name)
  }, [widget.xCol, onCrossFilter])

  const labelStyle = { fontSize: 10, fill: '#a1a1aa' }
  const labelFmt   = v => formatNumber(v)
  const gridStroke = 'rgba(255,255,255,0.04)'
  const tickStyle  = { fontSize: 10, fill: '#71717a' }
  const margin     = { top: 12, right: 12, left: -20, bottom: 0 }

  if (widget.type === 'text') {
    return (
      <div className="h-full p-4 overflow-y-auto custom-scrollbar">
        <p className="text-on-surface whitespace-pre-wrap leading-relaxed text-sm">
          {widget.textContent || 'Click ⚙ to edit text'}
        </p>
      </div>
    )
  }

  if (widget.type === 'kpi') {
    const val = chartData[0]?.value ?? 0
    return (
      <div className="flex flex-col h-full items-center justify-center p-4 gap-2">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: `${color0}20`, border: `1px solid ${color0}40` }}>
          <Hash size={20} style={{ color: color0 }} />
        </div>
        <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider text-center px-2">
          {widget.title || widget.yCol || 'KPI'}
        </p>
        <p className="text-3xl font-black tracking-tight" style={{ color: color0 }}>
          {formatNumber(val)}
        </p>
        <p className="text-[10px] font-bold text-on-surface-variant/60 uppercase tracking-widest bg-surface-container-highest px-2.5 py-1 rounded-full">
          {widget.aggregate || 'sum'}
        </p>
      </div>
    )
  }

  if (widget.type === 'table') {
    const cols = Object.keys(data[0] ?? {}).slice(0, 8)
    return (
      <div className="h-full overflow-auto custom-scrollbar">
        <table className="w-full text-left border-collapse text-[11px]">
          <thead className="sticky top-0 bg-surface-container-high z-10">
            <tr>
              {cols.map(c => (
                <th key={c} className="p-2 font-bold text-on-surface-variant uppercase tracking-wider text-[10px] border-b border-outline-variant/10 whitespace-nowrap">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/5">
            {data.slice(0, 50).map((row, i) => (
              <tr key={i} className="hover:bg-surface-container-highest/50 transition-colors">
                {cols.map(c => (
                  <td key={c} className="p-2 text-on-surface whitespace-nowrap truncate max-w-[150px]">
                    {String(row[c] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  if (!chartData.length) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-on-surface-variant/40 font-medium">
        Configure columns →
      </div>
    )
  }

  switch (widget.type) {
    case 'bar':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={margin}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
            <XAxis dataKey="name" tick={tickStyle} />
            <YAxis tick={tickStyle} />
            <Tooltip content={<CUSTOM_TOOLTIP />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} onClick={handleBarClick} cursor="pointer">
              {chartData.map((d, i) => (
                <Cell key={i} fill={chartColor(cs + i)} opacity={cellOpacity(d.name)} />
              ))}
              {widget.showLabels && (
                <LabelList dataKey="value" position="top" style={labelStyle} formatter={labelFmt} />
              )}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )

    case 'hbar':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} horizontal={false} />
            <XAxis type="number" tick={tickStyle} />
            <YAxis type="category" dataKey="name" tick={tickStyle} width={90} />
            <Tooltip content={<CUSTOM_TOOLTIP />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} onClick={handleBarClick} cursor="pointer">
              {chartData.map((d, i) => (
                <Cell key={i} fill={chartColor(cs + i)} opacity={cellOpacity(d.name)} />
              ))}
              {widget.showLabels && (
                <LabelList dataKey="value" position="right" style={labelStyle} formatter={labelFmt} />
              )}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )

    case 'line':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={margin}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
            <XAxis dataKey="name" tick={tickStyle} />
            <YAxis tick={tickStyle} />
            <Tooltip content={<CUSTOM_TOOLTIP />} />
            <Line
              type="monotone" dataKey="value" stroke={color0} strokeWidth={2.5}
              dot={{ r: 3, fill: color0, strokeWidth: 0 }}
              activeDot={{ r: 5, strokeWidth: 0 }}
            >
              {widget.showLabels && (
                <LabelList dataKey="value" position="top" style={labelStyle} formatter={labelFmt} />
              )}
            </Line>
          </LineChart>
        </ResponsiveContainer>
      )

    case 'area':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={margin}>
            <defs>
              <linearGradient id={`ag-${widget.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={color0} stopOpacity={0.35} />
                <stop offset="95%" stopColor={color0} stopOpacity={0}    />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
            <XAxis dataKey="name" tick={tickStyle} />
            <YAxis tick={tickStyle} />
            <Tooltip content={<CUSTOM_TOOLTIP />} />
            <Area
              type="monotone" dataKey="value" stroke={color0}
              fill={`url(#ag-${widget.id})`} strokeWidth={2.5}
            >
              {widget.showLabels && (
                <LabelList dataKey="value" position="top" style={labelStyle} formatter={labelFmt} />
              )}
            </Area>
          </AreaChart>
        </ResponsiveContainer>
      )

    case 'pie': {
      const total = chartData.reduce((s, d) => s + (d.value || 0), 0)
      return (
        <div className="relative h-full w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData} dataKey="value" nameKey="name"
                cx="50%" cy="50%" innerRadius="42%" outerRadius="70%"
                paddingAngle={2} stroke="none" cursor="pointer"
                onClick={(d) => { if (widget.xCol && onCrossFilter) onCrossFilter(widget.xCol, d.name) }}
                label={widget.showLabels
                  ? ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
                      if (percent < 0.04) return null
                      const R = Math.PI / 180
                      const r = innerRadius + (outerRadius - innerRadius) * 1.35
                      return (
                        <text
                          x={cx + r * Math.cos(-midAngle * R)}
                          y={cy + r * Math.sin(-midAngle * R)}
                          fill="#a1a1aa" textAnchor="middle"
                          dominantBaseline="central" fontSize={10}
                        >
                          {`${(percent * 100).toFixed(0)}%`}
                        </text>
                      )
                    }
                  : false}
              >
                {chartData.map((d, i) => (
                  <Cell key={i} fill={chartColor(cs + i)} opacity={cellOpacity(d.name)} />
                ))}
              </Pie>
              <Tooltip content={<CUSTOM_TOOLTIP />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#71717a' }} />
            </PieChart>
          </ResponsiveContainer>
          {/* Center total overlay */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none" style={{ paddingBottom: '15%' }}>
            <p className="text-base font-black text-on-surface leading-none">{formatNumber(total)}</p>
            <p className="text-[10px] font-medium text-on-surface-variant/50 uppercase tracking-wider mt-0.5">total</p>
          </div>
        </div>
      )
    }

    case 'scatter':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={margin}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
            <XAxis dataKey="name" type="category" tick={tickStyle} />
            <YAxis dataKey="value" tick={tickStyle} />
            <Tooltip content={<CUSTOM_TOOLTIP />} cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.08)' }} />
            <Scatter data={chartData} fill={color0} />
          </ScatterChart>
        </ResponsiveContainer>
      )

    default:
      return null
  }
}

/* ─── Docked right config panel ─── */
function WidgetConfigPanel({ widget, columns, onUpdate }) {
  const def = WIDGET_TYPES.find(t => t.id === widget.type)
  const isChart = !['text', 'table'].includes(widget.type)

  return (
    <div className="flex flex-col gap-4 p-5 overflow-y-auto custom-scrollbar h-full">

      {/* Title */}
      <div>
        <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-1.5">Title</p>
        <input
          className="w-full h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
          value={widget.title || ''}
          onChange={e => onUpdate({ title: e.target.value })}
          placeholder="Widget title"
        />
      </div>

      {/* X / Y columns */}
      {def?.needsX && widget.type !== 'kpi' && (
        <div>
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-1.5">X-Axis (Category)</p>
          <select
            className="w-full h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary outline-none appearance-none cursor-pointer"
            value={widget.xCol || ''}
            onChange={e => onUpdate({ xCol: e.target.value || null })}
          >
            <option value="">None</option>
            {columns.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      )}

      {(def?.needsY || widget.type === 'kpi') && (
        <div>
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-1.5">
            {widget.type === 'kpi' ? 'Value Column' : 'Y-Axis (Value)'}
          </p>
          <select
            className="w-full h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary outline-none appearance-none cursor-pointer"
            value={widget.yCol || ''}
            onChange={e => onUpdate({ yCol: e.target.value || null })}
          >
            <option value="">None</option>
            {columns.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      )}

      {/* Aggregation */}
      {isChart && (
        <div>
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-2">Aggregation</p>
          <div className="flex gap-1.5 flex-wrap">
            {AGGREGATIONS.map(a => (
              <button
                key={a}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase transition-all border ${
                  (widget.aggregate || 'sum') === a
                    ? 'bg-primary/15 text-primary border-primary/30'
                    : 'bg-surface-container text-on-surface-variant border-outline-variant/15 hover:border-outline-variant/40'
                }`}
                onClick={() => onUpdate({ aggregate: a })}
              >
                {a}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Text content */}
      {widget.type === 'text' && (
        <div>
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-1.5">Content</p>
          <textarea
            className="w-full p-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary outline-none resize-y"
            rows={5}
            value={widget.textContent || ''}
            onChange={e => onUpdate({ textContent: e.target.value })}
            placeholder="Enter text…"
          />
        </div>
      )}

      {/* Data labels toggle */}
      {isChart && (
        <div className="flex items-center justify-between pt-3 border-t border-outline-variant/10">
          <div>
            <p className="text-sm font-semibold text-on-surface">Data Labels</p>
            <p className="text-xs text-on-surface-variant/70">Show values on chart</p>
          </div>
          <button
            role="switch"
            aria-checked={!!widget.showLabels}
            className={`relative w-10 h-6 rounded-full transition-colors duration-200 ${widget.showLabels ? 'bg-primary' : 'bg-surface-container-highest border border-outline-variant/20'}`}
            onClick={() => onUpdate({ showLabels: !widget.showLabels })}
          >
            <span
              className="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200"
              style={{ transform: widget.showLabels ? 'translateX(16px)' : 'translateX(0)' }}
            />
          </button>
        </div>
      )}

      {/* Colour theme */}
      {isChart && (
        <div className="pt-3 border-t border-outline-variant/10">
          <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Palette size={12} /> Colour Theme
          </p>
          <div className="flex gap-2">
            {COLOR_THEMES.map(theme => (
              <button
                key={theme.name}
                title={theme.name}
                className={`w-8 h-8 rounded-lg border-2 transition-all ${
                  (widget.colorStart ?? 0) === theme.start
                    ? 'border-white/60 scale-110 shadow-md'
                    : 'border-transparent hover:border-white/20'
                }`}
                style={{ background: `linear-gradient(135deg, ${chartColor(theme.start)}, ${chartColor(theme.start + 1)})` }}
                onClick={() => onUpdate({ colorStart: theme.start })}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── Slicer config panel ─── */
function SlicerConfigPanel({ dash, ds, onUpdate, onClose }) {
  const columns = ds?.columnNames ?? []
  const [newCol, setNewCol] = useState('')

  const add = () => {
    if (!newCol) return
    onUpdate({ slicers: { ...(dash.slicers || {}), [newCol]: [] } })
    setNewCol('')
  }

  const remove = col => {
    const s = { ...(dash.slicers || {}) }
    delete s[col]
    onUpdate({ slicers: s })
  }

  return (
    <div className="absolute left-6 top-14 w-72 bg-surface-container-high/90 backdrop-blur-xl border border-outline-variant/20 rounded-2xl shadow-2xl z-50 p-5 flex flex-col gap-4 animate-in slide-in-from-left-8 duration-300">
      <div className="flex items-center justify-between pb-3 border-b border-outline-variant/10">
        <p className="font-bold text-on-surface flex items-center gap-2 text-sm">
          <Filter size={15} className="text-cyan-400" /> Dashboard Slicers
        </p>
        <button className="w-7 h-7 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-highest transition-colors" onClick={onClose}>
          <X size={14} />
        </button>
      </div>
      <div className="flex gap-2">
        <select
          className="flex-1 h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary outline-none appearance-none cursor-pointer"
          value={newCol} onChange={e => setNewCol(e.target.value)}
        >
          <option value="">Select column…</option>
          {columns.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <button className="h-9 px-3 rounded-lg bg-primary/15 text-primary hover:bg-primary/25 font-bold text-sm border border-primary/20 transition-colors" onClick={add}>
          Add
        </button>
      </div>
      <div className="flex flex-col gap-2">
        {Object.keys(dash.slicers || {}).map(col => (
          <div key={col} className="flex items-center justify-between p-3 rounded-xl bg-surface-container border border-outline-variant/10">
            <span className="font-semibold text-sm text-on-surface">{col}</span>
            <button className="text-rose-400 hover:text-rose-300 transition-colors" onClick={() => remove(col)}>
              <Trash2 size={14} />
            </button>
          </div>
        ))}
        {!Object.keys(dash.slicers || {}).length && (
          <p className="text-xs text-on-surface-variant/50 italic text-center py-2">No slicers added.</p>
        )}
      </div>
    </div>
  )
}

/* ─── Active slicer bar ─── */
function SlicerBar({ dash, ds, onUpdate }) {
  const slicers = dash.slicers || {}
  if (!Object.keys(slicers).length) return null

  const getUnique = col =>
    Array.from(new Set((ds?.preview || []).map(r => String(r[col] ?? '')))).filter(Boolean).slice(0, 12)

  const toggle = (col, val) => {
    const cur = slicers[col] || []
    onUpdate({ slicers: { ...slicers, [col]: cur.includes(val) ? cur.filter(v => v !== val) : [...cur, val] } })
  }

  return (
    <div className="px-6 py-2 bg-surface-container-lowest border-b border-outline-variant/10 flex items-center gap-4 overflow-x-auto shrink-0 custom-scrollbar z-10 shadow-sm">
      <div className="flex items-center gap-1.5 text-on-surface-variant shrink-0">
        <Filter size={13} />
        <span className="text-[10px] font-bold uppercase tracking-wider">Filters:</span>
      </div>
      {Object.keys(slicers).map(col => (
        <div key={col} className="flex items-center gap-1.5 bg-surface-container-high px-3 py-1.5 rounded-xl border border-outline-variant/10 shrink-0">
          <span className="text-xs font-semibold text-on-surface">{col}:</span>
          {getUnique(col).map(opt => (
            <button
              key={opt}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors border ${
                (slicers[col] || []).includes(opt)
                  ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
                  : 'bg-surface-container border-transparent hover:border-outline-variant/30 text-on-surface-variant'
              }`}
              onClick={() => toggle(col, opt)}
            >
              {opt}
            </button>
          ))}
        </div>
      ))}
    </div>
  )
}

/* ─── Main page ─── */
export default function DashboardPage() {
  const {
    dashboards, activeDashboard, createDashboard, setActive, deleteDashboard,
    addWidget, updateWidget, removeWidget, updateDashboard,
  } = useDashboardStore()
  const { datasets } = useDatasetStore()
  const canvasRef = useRef(null)

  const [newDashName, setNewDashName]       = useState('')
  const [addingDsId, setAddingDsId]         = useState('')
  const [showNewDash, setShowNewDash]       = useState(false)
  const [showAddPanel, setShowAddPanel]     = useState(false)
  const [showSlicerPanel, setShowSlicerPanel] = useState(false)
  const [addingType, setAddingType]         = useState(null)
  const [selectedWidget, setSelectedWidget] = useState(null)
  const [crossFilter, setCrossFilter]       = useState(null) // { col, value }
  const [aiGenerating, setAiGenerating]     = useState(false)
  const [widgetInsights, setWidgetInsights] = useState({})
  // { [widgetId]: { loading: bool, visible: bool, text: string|null, error: string|null } }

  const dash              = activeDashboard
  const activeDsForWidget = datasets.find(d => d.id === dash?.datasetId)
  const dsColumns         = activeDsForWidget?.columnNames ?? []
  const editingWidget     = dash?.widgets?.find(w => w.id === selectedWidget)

  /* ─── Handlers ─── */
  const handleCreateDashboard = () => {
    if (!newDashName.trim()) { toast.error('Enter a name'); return }
    const id = uuid()
    createDashboard({
      id, name: newDashName.trim(),
      datasetId: addingDsId || datasets[0]?.id || null,
      widgets: [], layout: [], slicers: {},
      createdAt: new Date().toISOString(),
    })
    setActive(id)
    setNewDashName('')
    setShowNewDash(false)
    toast.success('Dashboard created')
  }

  const handleAddWidget = () => {
    if (!dash || !addingType) return
    const wId = uuid()
    addWidget(dash.id, {
      id: wId, type: addingType.id, title: addingType.label,
      xCol: null, yCol: null, aggregate: 'sum',
      textContent: '', showLabels: false, colorStart: 0,
    })
    updateDashboard(dash.id, {
      layout: [...(dash.layout || []), {
        i: wId, x: (dash.widgets.length * addingType.defW) % 12, y: Infinity,
        w: addingType.defW, h: addingType.defH, minW: 2, minH: 2,
      }],
    })
    setSelectedWidget(wId)
    setShowAddPanel(false)
    setAddingType(null)
    toast.success(`${addingType.label} added`)
  }

  const handleRemoveWidget = useCallback((wId) => {
    if (!dash) return
    removeWidget(dash.id, wId)
    updateDashboard(dash.id, { layout: (dash.layout || []).filter(l => l.i !== wId) })
    if (selectedWidget === wId) setSelectedWidget(null)
  }, [dash, removeWidget, updateDashboard, selectedWidget])

  const handleCloneWidget = useCallback((widget) => {
    if (!dash) return
    const newId = uuid()
    const def = WIDGET_TYPES.find(t => t.id === widget.type) || { defW: 4, defH: 3 }
    addWidget(dash.id, { ...widget, id: newId, title: `${widget.title} (copy)` })
    updateDashboard(dash.id, {
      layout: [...(dash.layout || []), { i: newId, x: 0, y: Infinity, w: def.defW, h: def.defH, minW: 2, minH: 2 }],
    })
    toast.success('Widget cloned')
  }, [dash, addWidget, updateDashboard])

  const handleLayoutChange = useCallback((currentLayout, allLayouts) => {
    if (dash) updateDashboard(dash.id, { layout: allLayouts?.lg ?? currentLayout })
  }, [dash, updateDashboard])

  const handleCrossFilter = useCallback((col, value) => {
    setCrossFilter(prev =>
      prev?.col === col && prev?.value === String(value) ? null : { col, value: String(value) }
    )
  }, [])

  /* ─── Widget AI Insight ─── */
  const handleGetInsight = async (widget, chartData, force = false) => {
    const wId = widget.id
    const cur = widgetInsights[wId] || {}

    if (!force) {
      if (cur.visible && !cur.loading) {
        setWidgetInsights(p => ({ ...p, [wId]: { ...cur, visible: false } }))
        return
      }
      if (!cur.visible && cur.text) {
        setWidgetInsights(p => ({ ...p, [wId]: { ...cur, visible: true } }))
        return
      }
    }

    setWidgetInsights(p => ({ ...p, [wId]: { loading: true, visible: true, text: null, error: null } }))
    try {
      const res = await dashboardAPI.widgetInsight({
        title:     widget.title,
        type:      widget.type,
        xCol:      widget.xCol,
        yCol:      widget.yCol,
        aggregate: widget.aggregate || 'sum',
        chartData: chartData.slice(0, 15),
        rowCount:  activeDsForWidget?.rows || filteredData.length,
      })
      setWidgetInsights(p => ({ ...p, [wId]: { loading: false, visible: true, text: res.data.insight, error: null } }))
    } catch (err) {
      const msg = err.response?.data?.detail || 'AI insight failed'
      const isOllama = msg.toLowerCase().includes('not running') || err.response?.status === 503
      toast.error(isOllama ? 'Ollama is not running — start with: ollama serve' : `Insight: ${msg}`)
      setWidgetInsights(p => ({ ...p, [wId]: { loading: false, visible: false, text: null, error: msg } }))
    }
  }

  /* ─── AI Generate ─── */
  const handleAIGenerate = async () => {
    if (!dash) return
    if (!activeDsForWidget) {
      toast.error('Link a dataset to this dashboard first')
      return
    }

    setAiGenerating(true)

    try {
      const preview  = activeDsForWidget.preview || []
      const colNames = activeDsForWidget.columnNames || Object.keys(preview[0] ?? {})

      // Build rich schema: dtype, unique count, and real sample values
      const columns = colNames.map(name => {
        const allVals = preview.map(r => r[name]).filter(v => v !== null && v !== undefined && v !== '')
        const nums    = allVals.map(Number).filter(v => !isNaN(v))
        const isNum   = allVals.length > 0 && nums.length / allVals.length > 0.7
        const unique  = new Set(allVals.map(String)).size
        // Pick up to 6 representative samples (spread across the data)
        const step    = Math.max(1, Math.floor(allVals.length / 6))
        const samples = Array.from({ length: Math.min(6, allVals.length) }, (_, i) => allVals[i * step])
        return { name, dtype: isNum ? 'float64' : 'object', unique, samples }
      })

      const res = await dashboardAPI.suggestSchema({
        columns,
        row_count: activeDsForWidget.rows || preview.length || 100,
      })

      const suggestions = res.data.widgets || []
      if (!suggestions.length) {
        toast.error('AI returned no suggestions — make sure Ollama is running and try again.')
        setAiGenerating(false)
        return
      }

      let colorIdx = 0
      const newWidgets = suggestions.map(s => {
        const w = {
          id: uuid(),
          type:        s.type      || 'bar',
          title:       s.title     || 'AI Chart',
          xCol:        s.xCol      || null,
          yCol:        s.yCol      || null,
          aggregate:   s.aggregate || 'sum',
          textContent: '',
          showLabels:  false,
          colorStart:  colorIdx,
        }
        colorIdx = (colorIdx + 2) % 10
        return w
      })

      // ── Smart layout: no y:Infinity for batch adds — calculate explicit positions ──
      const existingBottom = (dash.layout || []).reduce(
        (max, l) => Math.max(max, (isFinite(l.y) ? l.y : 0) + (l.h || 0)), 0
      )
      const newLayouts = buildAILayout(newWidgets, existingBottom)

      newWidgets.forEach(w => addWidget(dash.id, w))
      updateDashboard(dash.id, { layout: [...(dash.layout || []), ...newLayouts] })
      setCrossFilter(null)
      toast.success(`✨ AI generated ${newWidgets.length} visualizations`)

    } catch (err) {
      const status = err.response?.status
      const detail = err.response?.data?.detail || ''
      const isTimeout = err.code === 'ECONNABORTED' || err.message?.toLowerCase().includes('timeout')

      if (isTimeout || status === 504) {
        toast.error('AI is taking too long — Ollama may still be loading the model. Try again in a moment.')
      } else if (status === 503) {
        toast.error('Ollama is not running. Start it with: ollama serve')
      } else if (status === 503 || detail.toLowerCase().includes('not running')) {
        toast.error('Ollama is not running. Start it with: ollama serve')
      } else {
        toast.error(`AI Visualize failed: ${detail || 'Check that Ollama is running with: ollama serve'}`)
      }
    }

    setAiGenerating(false)
  }

  /* ─── PDF export ─── */
  const handleExportPDF = async () => {
    if (!canvasRef.current) return
    toast.loading('Generating PDF…', { id: 'pdf' })
    try {
      const canvas = await html2canvas(canvasRef.current, { backgroundColor: '#0f1016', scale: 1.5 })
      const img = canvas.toDataURL('image/png')
      const pdf = new jsPDF({ orientation: 'landscape', unit: 'px', format: [canvas.width / 1.5, canvas.height / 1.5] })
      pdf.addImage(img, 'PNG', 0, 0, canvas.width / 1.5, canvas.height / 1.5)
      pdf.save(`${dash?.name ?? 'dashboard'}.pdf`)
      toast.success('PDF downloaded', { id: 'pdf' })
    } catch {
      toast.error('Export failed', { id: 'pdf' })
    }
  }

  /* ─── Filtered data (slicers + cross-filter) ─── */
  const filteredData = useMemo(() => {
    let d = applySlicers(activeDsForWidget?.preview || [], dash?.slicers)
    if (crossFilter) {
      d = d.filter(row => String(row[crossFilter.col] ?? '') === crossFilter.value)
    }
    return d
  }, [activeDsForWidget, dash?.slicers, crossFilter])

  /* ─── Render ─── */
  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-surface-container-low animate-in fade-in duration-500">

      {/* ── Toolbar ── */}
      <div className="flex items-center justify-between px-6 py-2.5 bg-surface-container border-b border-outline-variant/10 z-20 shadow-sm shrink-0">
        <div className="flex items-center gap-2">
          <select
            className="h-9 pl-3 pr-8 rounded-lg bg-surface-container-high border border-outline-variant/20 text-sm font-semibold text-on-surface focus:border-primary outline-none appearance-none cursor-pointer w-52 shadow-inner"
            value={dash?.id ?? ''}
            onChange={e => { setActive(e.target.value); setSelectedWidget(null); setCrossFilter(null) }}
          >
            <option value="">Select dashboard…</option>
            {dashboards.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>

          <button
            className="h-9 px-3 rounded-lg border border-outline-variant/30 text-on-surface font-semibold text-sm hover:bg-surface-container-highest transition-all flex items-center gap-1.5"
            onClick={() => setShowNewDash(v => !v)}
          >
            <Plus size={14} /> New
          </button>

          {dash && (
            <button
              className="h-9 w-9 rounded-lg text-rose-400/80 hover:bg-rose-500/10 hover:text-rose-400 transition-all flex items-center justify-center"
              onClick={() => { if (window.confirm(`Delete "${dash.name}"?`)) { deleteDashboard(dash.id); setSelectedWidget(null) } }}
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {crossFilter && (
            <button
              className="h-9 px-3 rounded-lg bg-amber-500/15 border border-amber-500/30 text-amber-400 text-xs font-bold flex items-center gap-2 hover:bg-amber-500/25 transition-colors"
              onClick={() => setCrossFilter(null)}
            >
              <Filter size={13} />
              {crossFilter.col}: {crossFilter.value}
              <X size={12} />
            </button>
          )}

          {dash && (
            <>
              <button
                className="h-9 px-4 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-500 text-white font-bold text-sm hover:from-violet-500 hover:to-indigo-400 transition-all flex items-center gap-2 shadow-md shadow-violet-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={handleAIGenerate}
                disabled={aiGenerating || !dash.datasetId}
                title={!dash.datasetId ? 'Link a dataset first' : 'AI auto-generates charts from dataset schema'}
              >
                {aiGenerating ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                {aiGenerating ? 'Generating…' : 'AI Visualize'}
              </button>

              <div className="w-px h-5 bg-outline-variant/20" />

              <button
                className={`h-9 px-3 rounded-lg border text-sm font-medium transition-all flex items-center gap-1.5 ${showSlicerPanel ? 'bg-cyan-500/15 border-cyan-500/30 text-cyan-400' : 'border-outline-variant/30 text-on-surface hover:bg-surface-container-highest'}`}
                onClick={() => setShowSlicerPanel(v => !v)}
              >
                <Filter size={14} /> Slicers
              </button>

              <button
                className="h-9 px-4 rounded-lg bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-colors flex items-center gap-1.5 shadow-md shadow-primary/20"
                onClick={() => setShowAddPanel(v => !v)}
              >
                <Plus size={14} /> Widget
              </button>

              <button
                className="h-9 px-3 rounded-lg border border-outline-variant/30 text-on-surface text-sm hover:bg-surface-container-highest transition-all flex items-center gap-1.5"
                onClick={handleExportPDF}
              >
                <Download size={14} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Active slicer bar ── */}
      {dash && <SlicerBar dash={dash} ds={activeDsForWidget} onUpdate={patch => updateDashboard(dash.id, patch)} />}

      {/* ── New dashboard popover ── */}
      {showNewDash && (
        <div className="absolute top-14 left-6 z-50 bg-surface-container-high/90 backdrop-blur-xl border border-outline-variant/20 rounded-xl shadow-2xl p-4 flex gap-2 animate-in slide-in-from-top-4 duration-300">
          <input
            className="h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary outline-none w-44"
            value={newDashName} onChange={e => setNewDashName(e.target.value)}
            placeholder="Dashboard name…"
            onKeyDown={e => e.key === 'Enter' && handleCreateDashboard()}
            autoFocus
          />
          <select
            className="h-9 px-3 rounded-lg bg-surface-container border border-outline-variant/20 text-sm text-on-surface outline-none appearance-none w-36"
            value={addingDsId} onChange={e => setAddingDsId(e.target.value)}
          >
            <option value="">No dataset</option>
            {datasets.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          <button className="h-9 px-4 rounded-lg bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-colors" onClick={handleCreateDashboard}>Create</button>
          <button className="h-9 px-3 rounded-lg text-on-surface-variant hover:bg-surface-container-highest transition-colors text-sm" onClick={() => setShowNewDash(false)}>✕</button>
        </div>
      )}

      {/* ── Add widget panel ── */}
      {showAddPanel && (
        <div className="absolute top-14 right-6 z-50 bg-surface-container-high/90 backdrop-blur-xl border border-outline-variant/20 rounded-2xl shadow-2xl p-5 flex flex-col gap-4 animate-in slide-in-from-top-4 duration-300 w-80">
          <div className="flex items-center justify-between">
            <p className="font-bold text-on-surface">Add Widget</p>
            <button className="text-on-surface-variant hover:text-on-surface" onClick={() => setShowAddPanel(false)}><X size={18} /></button>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {WIDGET_TYPES.map(t => (
              <button
                key={t.id}
                className={`flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl border transition-all ${
                  addingType?.id === t.id
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-outline-variant/15 bg-surface-container hover:bg-surface-container-highest text-on-surface-variant hover:text-on-surface'
                }`}
                onClick={() => setAddingType(t)}
              >
                <t.icon size={20} strokeWidth={addingType?.id === t.id ? 2 : 1.5} />
                <span className="text-[10px] font-semibold text-center leading-tight">{t.label}</span>
              </button>
            ))}
          </div>
          <button
            className="h-10 rounded-xl bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-colors disabled:opacity-40"
            onClick={handleAddWidget}
            disabled={!addingType}
          >
            Add to Dashboard
          </button>
        </div>
      )}

      {/* ── Slicers config panel ── */}
      {showSlicerPanel && dash && (
        <SlicerConfigPanel
          dash={dash}
          ds={activeDsForWidget}
          onUpdate={patch => updateDashboard(dash.id, patch)}
          onClose={() => setShowSlicerPanel(false)}
        />
      )}

      {/* ── Main body: canvas + docked properties panel ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Canvas */}
        <div className="flex-1 overflow-auto bg-surface-container-low/50 relative" ref={canvasRef}>
          {!dash ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-20 h-20 rounded-full bg-surface-container flex items-center justify-center text-on-surface-variant/30 mb-5 border border-outline-variant/10">
                <BarChart3 size={40} strokeWidth={1} />
              </div>
              <p className="font-bold text-xl text-on-surface mb-2">No dashboard selected</p>
              <p className="text-on-surface-variant mb-7 max-w-xs leading-relaxed text-sm">Create a new dashboard and link a dataset to start building.</p>
              <button
                className="h-11 px-6 rounded-xl bg-primary text-on-primary font-bold hover:bg-primary-fixed transition-colors flex items-center gap-2 shadow-lg shadow-primary/20"
                onClick={() => setShowNewDash(true)}
              >
                <Plus size={18} /> Create Dashboard
              </button>
            </div>
          ) : !dash.widgets?.length ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <BarChart3 size={48} className="text-on-surface-variant/20" strokeWidth={1} />
              <div className="text-center">
                <p className="text-on-surface font-semibold text-base mb-1">Canvas is empty</p>
                <p className="text-on-surface-variant/60 text-sm">Add widgets manually or let AI build your dashboard.</p>
              </div>
              <div className="flex gap-3 mt-2">
                <button
                  className="h-10 px-5 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-500 text-white font-bold text-sm hover:from-violet-500 hover:to-indigo-400 transition-all flex items-center gap-2 shadow-md shadow-violet-500/20 disabled:opacity-40"
                  onClick={handleAIGenerate}
                  disabled={aiGenerating || !dash.datasetId}
                >
                  {aiGenerating ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  {aiGenerating ? 'Generating…' : 'AI Generate'}
                </button>
                <button
                  className="h-10 px-5 rounded-xl bg-surface-container-highest border border-outline-variant/20 text-on-surface font-bold text-sm hover:bg-surface-container transition-colors flex items-center gap-2"
                  onClick={() => setShowAddPanel(true)}
                >
                  <Plus size={14} /> Add Widget
                </button>
              </div>
              {!dash.datasetId && (
                <p className="text-xs text-amber-400/80 mt-1">⚠ No dataset linked — AI Visualize requires a dataset.</p>
              )}
            </div>
          ) : (
            <div className="p-5 min-h-full">
              <ResponsiveGridLayout
                key={dash.id}
                className="layout"
                layouts={{ lg: dash.layout || [], md: [], sm: [], xs: [], xxs: [] }}
                breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
                cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
                rowHeight={100}
                onLayoutChange={handleLayoutChange}
                draggableHandle=".drag-handle"
                isResizable isDraggable
                compactType="vertical"
                preventCollision={false}
                margin={[20, 20]}
              >
                {dash.widgets.map(widget => {
                  const chartData = buildWidgetData(widget, filteredData)
                  const wInsight  = widgetInsights[widget.id] || {}
                  const canInsight = !['text', 'table'].includes(widget.type) && !!widget.yCol

                  return (
                  <div
                    key={widget.id}
                    className={`glass-card rounded-2xl border flex flex-col overflow-hidden transition-all duration-150 ${
                      selectedWidget === widget.id
                        ? 'border-primary/60 shadow-[0_0_0_1px_rgba(99,102,241,0.3),0_8px_30px_rgba(99,102,241,0.12)]'
                        : 'border-white/5 hover:border-white/10'
                    }`}
                  >
                    {/* Widget header */}
                    <div className="drag-handle flex items-center justify-between px-3 py-2 border-b border-outline-variant/10 bg-surface-container-low/80 cursor-move group shrink-0">
                      <p className="font-semibold text-xs text-on-surface truncate flex-1 pr-2">{widget.title}</p>
                      <div className="flex items-center gap-0.5">
                        {/* AI Insight button — always visible for chart widgets */}
                        {canInsight && (
                          <button
                            title="AI Insight"
                            className={`w-6 h-6 rounded flex items-center justify-center transition-colors ${
                              wInsight.visible
                                ? 'text-violet-400 bg-violet-500/15'
                                : 'text-on-surface-variant/40 hover:bg-surface-container-highest hover:text-violet-400'
                            }`}
                            onMouseDown={e => e.stopPropagation()}
                            onClick={e => { e.stopPropagation(); handleGetInsight(widget, chartData) }}
                          >
                            {wInsight.loading
                              ? <Loader2 size={11} className="animate-spin" />
                              : <Sparkles size={11} />}
                          </button>
                        )}
                        {/* Settings / clone / delete — hover-reveal */}
                        <div className={`flex items-center gap-0.5 transition-opacity ${selectedWidget === widget.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                          <button
                            className="w-6 h-6 rounded flex items-center justify-center text-on-surface-variant hover:bg-surface-container-highest hover:text-primary transition-colors"
                            onMouseDown={e => e.stopPropagation()}
                            onClick={e => { e.stopPropagation(); setSelectedWidget(selectedWidget === widget.id ? null : widget.id) }}
                          >
                            <Settings size={12} />
                          </button>
                          <button
                            className="w-6 h-6 rounded flex items-center justify-center text-on-surface-variant hover:bg-surface-container-highest hover:text-cyan-400 transition-colors"
                            onMouseDown={e => e.stopPropagation()}
                            onClick={e => { e.stopPropagation(); handleCloneWidget(widget) }}
                          >
                            <Copy size={12} />
                          </button>
                          <button
                            className="w-6 h-6 rounded flex items-center justify-center text-rose-400/70 hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
                            onMouseDown={e => e.stopPropagation()}
                            onClick={e => { e.stopPropagation(); handleRemoveWidget(widget.id) }}
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* AI Insight panel */}
                    {canInsight && wInsight.visible && (
                      <div className="border-b border-violet-500/10 bg-gradient-to-r from-violet-500/5 to-indigo-500/5 shrink-0 animate-in slide-in-from-top-2 duration-200">
                        {/* Panel header */}
                        <div className="flex items-center justify-between px-3 pt-2 pb-1">
                          <div className="flex items-center gap-1.5">
                            <Sparkles size={10} className="text-violet-400" />
                            <span className="text-[10px] font-bold text-violet-400 uppercase tracking-wider">AI Insight</span>
                          </div>
                          <div className="flex items-center gap-0.5">
                            {!wInsight.loading && wInsight.text && (
                              <button
                                title="Regenerate"
                                className="w-5 h-5 rounded flex items-center justify-center text-on-surface-variant/40 hover:text-violet-400 hover:bg-violet-500/10 transition-colors"
                                onMouseDown={e => e.stopPropagation()}
                                onClick={e => { e.stopPropagation(); handleGetInsight(widget, chartData, true) }}
                              >
                                <RefreshCw size={9} />
                              </button>
                            )}
                            <button
                              title="Close"
                              className="w-5 h-5 rounded flex items-center justify-center text-on-surface-variant/40 hover:text-on-surface hover:bg-surface-container-highest transition-colors"
                              onMouseDown={e => e.stopPropagation()}
                              onClick={e => { e.stopPropagation(); setWidgetInsights(p => ({ ...p, [widget.id]: { ...wInsight, visible: false } })) }}
                            >
                              <X size={9} />
                            </button>
                          </div>
                        </div>
                        {/* Content */}
                        <div className="px-3 pb-2.5">
                          {wInsight.loading ? (
                            <div className="flex items-center gap-2 py-1">
                              <Loader2 size={10} className="animate-spin text-violet-400 shrink-0" />
                              <span className="text-[11px] text-on-surface-variant/60 italic">Analyzing chart data…</span>
                            </div>
                          ) : wInsight.text ? (
                            <div className="space-y-1">
                              {wInsight.text.split('\n').filter(Boolean).map((line, i) => (
                                <p key={i} className="text-[11px] text-on-surface-variant leading-relaxed flex items-start gap-1.5">
                                  <span className="text-violet-400 mt-px shrink-0">•</span>
                                  <span>{line.replace(/^[•\-\*]\s*/, '')}</span>
                                </p>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    )}

                    {/* Widget body */}
                    <div className="flex-1 overflow-hidden" onMouseDown={e => e.stopPropagation()}>
                      <WidgetContent
                        widget={widget}
                        data={filteredData}
                        onCrossFilter={handleCrossFilter}
                        crossFilter={crossFilter}
                      />
                    </div>
                  </div>
                  )
                })}
              </ResponsiveGridLayout>
            </div>
          )}
        </div>

        {/* ── Docked right properties panel ── */}
        <div
          className="transition-all duration-300 overflow-hidden border-l border-outline-variant/10 bg-surface-container shrink-0"
          style={{ width: editingWidget ? 272 : 0 }}
        >
          {editingWidget && (
            <div className="w-[272px] h-full flex flex-col">
              <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant/10 shrink-0">
                <div>
                  <p className="font-bold text-sm text-on-surface">Properties</p>
                  <p className="text-[10px] text-on-surface-variant/70 capitalize">{editingWidget.type} widget</p>
                </div>
                <button
                  className="w-7 h-7 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-highest transition-colors"
                  onClick={() => setSelectedWidget(null)}
                >
                  <X size={14} />
                </button>
              </div>
              <WidgetConfigPanel
                widget={editingWidget}
                columns={dsColumns}
                onUpdate={patch => updateWidget(dash.id, editingWidget.id, patch)}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
