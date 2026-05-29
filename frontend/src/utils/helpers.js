/**
 * Format a number for display (K, M, B)
 */
export function formatNumber(n, decimals = 1) {
  if (n === null || n === undefined || isNaN(n)) return '—'
  const abs = Math.abs(n)
  if (abs >= 1e9) return (n / 1e9).toFixed(decimals) + 'B'
  if (abs >= 1e6) return (n / 1e6).toFixed(decimals) + 'M'
  if (abs >= 1e3) return (n / 1e3).toFixed(decimals) + 'K'
  if (Number.isInteger(n)) return n.toLocaleString()
  return Number(n).toFixed(decimals)
}

/**
 * Format bytes to human-readable
 */
export function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

/**
 * Generate a UUID v4
 */
export function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

/**
 * Clamp a number between min and max
 */
export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

/**
 * Debounce a function
 */
export function debounce(fn, delay) {
  let timer
  return (...args) => {
    clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }
}

/**
 * Format a date string
 */
export function formatDate(dateStr, opts = {}) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d)) return dateStr
  return d.toLocaleDateString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric', ...opts
  })
}

/**
 * Format a relative time (e.g., "3 hours ago")
 */
export function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const min  = Math.floor(diff / 60000)
  const hr   = Math.floor(diff / 3600000)
  const day  = Math.floor(diff / 86400000)
  if (min < 1)  return 'just now'
  if (min < 60) return `${min}m ago`
  if (hr  < 24) return `${hr}h ago`
  if (day < 7)  return `${day}d ago`
  return formatDate(dateStr)
}

/**
 * Get dtype color badge class
 */
export function dtypeColor(dtype) {
  if (!dtype) return 'badge-muted'
  const t = dtype.toLowerCase()
  if (t.includes('int') || t.includes('float') || t === 'number') return 'badge-cyan'
  if (t.includes('date') || t.includes('time')) return 'badge-brand'
  if (t === 'bool' || t === 'boolean') return 'badge-warning'
  return 'badge-muted'
}

/**
 * Detect dtype display label
 */
export function dtypeLabel(dtype) {
  if (!dtype) return 'unknown'
  const t = dtype.toLowerCase()
  if (t.includes('int64') || t.includes('int32')) return 'integer'
  if (t.includes('float')) return 'float'
  if (t.includes('object') || t.includes('string')) return 'text'
  if (t.includes('bool')) return 'boolean'
  if (t.includes('date')) return 'datetime'
  return dtype
}

/**
 * Generate chart colours for N series
 */
const CHART_COLORS = [
  '#6366f1','#06b6d4','#10b981','#f59e0b','#f43f5e',
  '#8b5cf6','#ec4899','#14b8a6','#f97316','#a855f7'
]
export function chartColor(i) {
  return CHART_COLORS[i % CHART_COLORS.length]
}

/**
 * Truncate long strings
 */
export function truncate(str, max = 30) {
  if (!str) return ''
  return str.length > max ? str.slice(0, max) + '…' : str
}

/**
 * CSV row parser (single line)
 */
export function csvRow(values, sep = ',') {
  return values.map((v) => {
    const s = String(v ?? '')
    return s.includes(sep) || s.includes('"') || s.includes('\n')
      ? `"${s.replace(/"/g, '""')}"`
      : s
  }).join(sep)
}

/**
 * Download a Blob as a file
 */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a   = document.createElement('a')
  a.href     = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
