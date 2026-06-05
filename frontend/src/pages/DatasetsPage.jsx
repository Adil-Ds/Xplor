import { useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { useNavigate } from 'react-router-dom'
import {
  Database, Upload, Trash2, Wand2, BarChart3,
  FileSpreadsheet, FileJson, File, Search, Filter,
  ChevronDown, MoreHorizontal, Eye, MessageSquare, Cpu, CheckCircle2, Loader2,
} from 'lucide-react'
import { useDatasetStore } from '../store/datasetStore'
import { useAuthStore } from '../store/authStore'
import { formatBytes, formatDate, timeAgo, uuid } from '../utils/helpers'
import toast from 'react-hot-toast'
import Papa from 'papaparse'
import * as XLSX from 'xlsx'
import api from '../api/client'

const API = 'http://localhost:8000'

/* ─── Analysis status badge ─── */
function AnalysisBadge({ status }) {
  if (!status || status === 'pending') return null
  if (status === 'running') return (
    <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-[10px] font-bold uppercase tracking-wider">
      <Loader2 size={10} className="animate-spin" />
      AI Analyzing…
    </span>
  )
  if (status === 'done') return (
    <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold uppercase tracking-wider">
      <CheckCircle2 size={10} />
      AI Ready
    </span>
  )
  return (
    <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px] font-bold uppercase tracking-wider">
      <Cpu size={10} />
      Analysis failed
    </span>
  )
}

const FILE_ICONS = {
  csv:     <FileSpreadsheet size={24} className="text-emerald-400" />,
  xlsx:    <FileSpreadsheet size={24} className="text-indigo-400" />,
  xls:     <FileSpreadsheet size={24} className="text-indigo-400" />,
  json:    <FileJson size={24} className="text-amber-400" />,
  parquet: <File size={24} className="text-cyan-400" />,
}
function fileIcon(name) {
  const ext = name?.split('.').pop()?.toLowerCase()
  return FILE_ICONS[ext] || <File size={24} className="text-on-surface-variant" />
}

export default function DatasetsPage() {
  const { datasets, addDataset, removeDataset } = useDatasetStore()
  const navigate   = useNavigate()
  const [search, setSearch]     = useState('')
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)

  // Parse uploaded file and extract metadata
  const parseFile = (file) => {
    return new Promise((resolve) => {
      const ext = file.name.split('.').pop().toLowerCase()

      if (ext === 'csv') {
        Papa.parse(file, {
          header: true,
          skipEmptyLines: true,
          complete: (result) => {
            resolve({
              id:        uuid(),
              name:      file.name.replace(/\.[^.]+$/, ''),
              filename:  file.name,
              type:      'csv',
              rows:      result.data.length,
              columns:   result.meta.fields?.length ?? 0,
              columnNames: result.meta.fields ?? [],
              size:      file.size,
              preview:   result.data.slice(0, 200),
              rawHeaders: result.meta.fields ?? [],
              createdAt: new Date().toISOString(),
            })
          },
          error: () => resolve(null),
        })
      } else if (['xlsx', 'xls'].includes(ext)) {
        const reader = new FileReader()
        reader.onload = (e) => {
          try {
            const wb    = XLSX.read(e.target.result, { type: 'binary' })
            const ws    = wb.Sheets[wb.SheetNames[0]]
            const data  = XLSX.utils.sheet_to_json(ws, { defval: '' })
            const headers = Object.keys(data[0] ?? {})
            resolve({
              id:        uuid(),
              name:      file.name.replace(/\.[^.]+$/, ''),
              filename:  file.name,
              type:      ext,
              rows:      data.length,
              columns:   headers.length,
              columnNames: headers,
              size:      file.size,
              preview:   data.slice(0, 200),
              rawHeaders: headers,
              createdAt: new Date().toISOString(),
            })
          } catch { resolve(null) }
        }
        reader.readAsBinaryString(file)
      } else if (ext === 'json') {
        const reader = new FileReader()
        reader.onload = (e) => {
          try {
            const data = JSON.parse(e.target.result)
            const arr  = Array.isArray(data) ? data : [data]
            const headers = Object.keys(arr[0] ?? {})
            resolve({
              id:        uuid(),
              name:      file.name.replace(/\.[^.]+$/, ''),
              filename:  file.name,
              type:      'json',
              rows:      arr.length,
              columns:   headers.length,
              columnNames: headers,
              size:      file.size,
              preview:   arr.slice(0, 200),
              rawHeaders: headers,
              createdAt: new Date().toISOString(),
            })
          } catch { resolve(null) }
        }
        reader.readAsText(file)
      } else {
        resolve({
          id:        uuid(),
          name:      file.name.replace(/\.[^.]+$/, ''),
          filename:  file.name,
          type:      ext,
          rows:      null,
          columns:   null,
          size:      file.size,
          preview:   [],
          createdAt: new Date().toISOString(),
        })
      }
    })
  }

  const onDrop = useCallback(async (acceptedFiles) => {
    if (!acceptedFiles.length) return
    setUploading(true)
    setProgress(0)

    for (let i = 0; i < acceptedFiles.length; i++) {
      const file = acceptedFiles[i]
      setProgress(Math.round((i / acceptedFiles.length) * 100))

      // 1. Parse locally for immediate preview + column metadata
      const localDs = await parseFile(file)
      if (!localDs) {
        toast.error(`Failed to parse "${file.name}"`)
        setProgress(Math.round(((i + 1) / acceptedFiles.length) * 100))
        continue
      }

      // 2. Upload raw file to backend so AI routes (chat, explore, clean) can load it
      let finalDs = localDs
      try {
        const formData = new FormData()
        formData.append('file', file)
        const res = await api.post('/datasets/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        // Use the backend-generated UUID — all backend AI endpoints key on this ID
        finalDs = { ...localDs, id: res.data.id, backendSynced: true }
      } catch (err) {
        if (err.response?.status !== 401) {
          // 401 is already handled by the interceptor (session expired → login)
          // Any other error means backend is down or unavailable — store locally only
          console.warn('Backend upload failed, falling back to local storage:', err)
          toast('Saved locally — start the backend server to enable AI features.', {
            icon: '⚠️',
            duration: 5000,
          })
        }
      }

      addDataset(finalDs)
      if (finalDs.backendSynced) {
        toast.success(`"${localDs.name}" ready — ${localDs.rows?.toLocaleString() ?? '?'} rows · AI enabled`)
      }
      setProgress(Math.round(((i + 1) / acceptedFiles.length) * 100))
    }

    setUploading(false)
  }, [addDataset])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv':                                          ['.csv'],
      'application/vnd.ms-excel':                         ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/json':                                 ['.json'],
    },
    multiple: true,
  })

  const handleDelete = (id, name) => {
    if (!window.confirm(`Delete "${name}"?`)) return
    removeDataset(id)
    toast.success('Dataset removed')
  }

  const filtered = datasets.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex flex-col gap-8 p-8 max-w-[1400px] mx-auto w-full animate-in fade-in duration-500">
      
      {/* Upload Zone */}
      <div
        {...getRootProps()}
        className={`flex flex-col items-center justify-center p-10 rounded-3xl border-2 border-dashed transition-all duration-300 cursor-pointer overflow-hidden relative ${
          isDragActive ? 'border-primary bg-primary/5 scale-[1.02]' : 
          uploading ? 'border-primary/50 bg-surface-container-high cursor-wait' : 
          'border-outline-variant hover:border-primary/50 hover:bg-surface-container-high/50'
        }`}
      >
        <input {...getInputProps()} />
        <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 transition-all duration-300 ${
          isDragActive ? 'bg-primary text-on-primary scale-110 shadow-lg shadow-primary/20' : 
          'bg-surface-container-highest text-primary border border-outline-variant/10'
        }`}>
          <Upload size={28} strokeWidth={isDragActive ? 2 : 1.5} />
        </div>
        
        {uploading ? (
          <div className="flex flex-col items-center gap-3 w-full max-w-md z-10">
            <p className="font-bold text-on-surface text-lg">Processing files…</p>
            <div className="w-full h-2 bg-surface-container-highest rounded-full overflow-hidden">
              <div className="h-full bg-primary transition-all duration-300" style={{ width: `${progress}%` }} />
            </div>
            <p className="text-sm font-semibold text-primary">{progress}% complete</p>
          </div>
        ) : isDragActive ? (
          <div className="flex flex-col items-center gap-1 z-10">
            <p className="font-bold text-on-surface text-xl">Drop files here!</p>
            <p className="text-on-surface-variant">Release to upload</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 z-10">
            <p className="font-bold text-on-surface text-lg">Drop files or click to upload</p>
            <p className="text-on-surface-variant text-sm mb-2">Supports CSV, Excel (.xlsx/.xls), JSON</p>
            <div className="flex gap-2">
              {['CSV', 'XLSX', 'JSON', 'XLS'].map(ext => (
                <span key={ext} className="px-2 py-1 rounded bg-surface-container-highest text-on-surface-variant text-[10px] font-bold uppercase tracking-wider border border-white/5">
                  {ext}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* List header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-outline-variant/10 pb-4">
        <div>
          <h3 className="font-bold text-2xl text-on-surface tracking-tight flex items-center gap-2">
            Your Datasets
          </h3>
          <p className="text-on-surface-variant font-medium mt-1">
            {filtered.length} dataset{filtered.length !== 1 ? 's' : ''} stored locally
          </p>
        </div>
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
          <input
            className="w-full sm:w-64 h-10 pl-9 pr-4 rounded-xl bg-surface-container border border-outline-variant/20 text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all placeholder:text-on-surface-variant/50"
            placeholder="Search datasets…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Dataset list */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
          <div className="w-20 h-20 rounded-full bg-surface-container flex items-center justify-center text-on-surface-variant mb-4 border border-outline-variant/10">
            <Database size={32} />
          </div>
          <p className="font-bold text-on-surface text-xl mb-2">No datasets found</p>
          <p className="text-on-surface-variant max-w-[250px] leading-relaxed">
            {search ? 'Try a different search term' : 'Upload your first dataset above'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filtered.map((ds) => (
            <DatasetCard
              key={ds.id}
              ds={ds}
              onDelete={() => handleDelete(ds.id, ds.name)}
              onClean={() => navigate(`/clean/${ds.id}`)}
              onExplore={() => navigate(`/explore/${ds.id}`)}
              onChat={() => navigate(`/chat/${ds.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function DatasetCard({ ds, onDelete, onClean, onExplore, onChat }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [analysisStatus, setAnalysisStatus] = useState(ds.analysis_status || null)
  const { token } = useAuthStore()

  // Poll analysis status until done or error
  useEffect(() => {
    if (!analysisStatus || analysisStatus === 'done' || analysisStatus === 'error') return
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/datasets/${ds.id}/analysis`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        if (data.status === 'done' || data.status === 'error') {
          setAnalysisStatus(data.status)
          clearInterval(interval)
          if (data.status === 'done') toast.success(`AI analysis ready for "${ds.name}"`)
        }
      } catch { clearInterval(interval) }
    }, 3000)
    return () => clearInterval(interval)
  }, [analysisStatus, ds.id, ds.name, token])

  return (
    <div className="glass-card rounded-2xl border border-white/5 flex flex-col overflow-hidden hover:border-primary/30 transition-colors animate-in slide-in-from-bottom-4 duration-500">
      <div className="p-5 flex flex-col gap-4 flex-1">
        
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center shrink-0 border border-outline-variant/10 shadow-inner">
            {fileIcon(ds.filename)}
          </div>
          <div className="flex-1 min-w-0 flex flex-col items-start gap-1">
            <p className="font-bold text-on-surface truncate w-full" title={ds.name}>{ds.name}</p>
            <p className="text-xs font-medium text-on-surface-variant truncate w-full" title={ds.filename}>{ds.filename}</p>
            <div className="mt-1"><AnalysisBadge status={analysisStatus} /></div>
          </div>
          
          <div className="relative">
            <button
              className="w-8 h-8 rounded-lg flex items-center justify-center text-on-surface-variant hover:bg-surface-container-highest hover:text-on-surface transition-colors shrink-0"
              onClick={() => setMenuOpen((v) => !v)}
            >
              <MoreHorizontal size={18} />
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 top-full mt-1 w-48 bg-surface-container-high rounded-xl border border-outline-variant/20 shadow-2xl py-1 z-50 animate-in fade-in zoom-in-95 duration-200" onClick={() => setMenuOpen(false)}>
                  <button className="w-full px-4 py-2 text-left text-sm text-on-surface hover:bg-surface-container-highest flex items-center gap-3 transition-colors" onClick={onExplore}>
                    <Eye size={16} className="text-on-surface-variant" /> Preview & Explore
                  </button>
                  <button className="w-full px-4 py-2 text-left text-sm text-on-surface hover:bg-surface-container-highest flex items-center gap-3 transition-colors" onClick={onClean}>
                    <Wand2 size={16} className="text-emerald-400" /> Clean Data
                  </button>
                  <button className="w-full px-4 py-2 text-left text-sm text-on-surface hover:bg-surface-container-highest flex items-center gap-3 transition-colors" onClick={onChat}>
                    <MessageSquare size={16} className="text-cyan-400" /> Chat with Data
                  </button>
                  <div className="my-1 border-t border-outline-variant/10" />
                  <button className="w-full px-4 py-2 text-left text-sm text-rose-400 hover:bg-rose-500/10 flex items-center gap-3 transition-colors" onClick={onDelete}>
                    <Trash2 size={16} /> Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-2 mt-2">
          <Pill label="Rows"    value={ds.rows?.toLocaleString() ?? '—'} />
          <Pill label="Columns" value={ds.columns ?? '—'}                />
          <Pill label="Size"    value={formatBytes(ds.size)}              />
          <Pill label="Type"    value={ds.type?.toUpperCase() ?? '—'}     />
        </div>

        <p className="text-[11px] font-medium text-on-surface-variant/70 mt-auto">
          Uploaded {timeAgo(ds.createdAt)}
        </p>
      </div>

      {/* Actions */}
      <div className="grid grid-cols-3 border-t border-outline-variant/10 bg-surface-container-low/50 divide-x divide-outline-variant/10">
        <button id={`btn-explore-${ds.id}`} className="flex flex-col items-center justify-center gap-1 py-3 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest transition-colors font-semibold text-[11px] uppercase tracking-wider" onClick={onExplore}>
          <Eye size={16} /> Explore
        </button>
        <button id={`btn-chat-${ds.id}`} className="flex flex-col items-center justify-center gap-1 py-3 text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10 transition-colors font-semibold text-[11px] uppercase tracking-wider" onClick={onChat}>
          <MessageSquare size={16} /> Chat
        </button>
        <button id={`btn-clean-${ds.id}`} className="flex flex-col items-center justify-center gap-1 py-3 text-primary hover:text-primary-fixed hover:bg-primary/10 transition-colors font-semibold text-[11px] uppercase tracking-wider" onClick={onClean}>
          <Wand2 size={16} /> Clean
        </button>
      </div>
    </div>
  )
}

function Pill({ label, value }) {
  return (
    <div className="flex flex-col p-2 rounded-lg bg-surface-container-low border border-white/5">
      <span className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider">{label}</span>
      <span className="text-sm font-semibold text-on-surface truncate">{value}</span>
    </div>
  )
}
