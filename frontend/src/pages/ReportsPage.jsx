import { useState, useRef } from 'react'
import {
  FileText, Plus, Trash2, Download, Share2, Eye,
  BarChart3, Copy, Check, Calendar, FileSpreadsheet, X
} from 'lucide-react'
import { useDashboardStore } from '../store/dashboardStore'
import { useDatasetStore } from '../store/datasetStore'
import { formatDate, uuid, timeAgo } from '../utils/helpers'
import toast from 'react-hot-toast'

export default function ReportsPage() {
  const { dashboards } = useDashboardStore()
  const { datasets }   = useDatasetStore()
  const [reports, setReports]     = useState([])
  const [showNew, setShowNew]     = useState(false)
  const [form, setForm]           = useState({ title: '', description: '', dashboardId: '', datasetId: '' })
  const [copiedLink, setCopiedLink] = useState(null)

  const handleCreate = () => {
    if (!form.title.trim()) { toast.error('Enter a title'); return }
    const report = {
      id:          uuid(),
      title:       form.title.trim(),
      description: form.description.trim(),
      dashboardId: form.dashboardId,
      datasetId:   form.datasetId,
      shareToken:  uuid().slice(0, 12),
      createdAt:   new Date().toISOString(),
    }
    setReports(prev => [report, ...prev])
    setForm({ title:'', description:'', dashboardId:'', datasetId:'' })
    setShowNew(false)
    toast.success('Report created')
  }

  const handleDelete = (id) => {
    setReports(prev => prev.filter(r => r.id !== id))
    toast.success('Report deleted')
  }

  const handleCopyLink = (token) => {
    const link = `${window.location.origin}/report/${token}`
    navigator.clipboard.writeText(link).then(() => {
      setCopiedLink(token)
      toast.success('Share link copied')
      setTimeout(() => setCopiedLink(null), 2000)
    })
  }

  const handleExportReport = async (report) => {
    const dash = dashboards.find(d => d.id === report.dashboardId)
    const ds   = datasets.find(d => d.id === report.datasetId)
    const html = buildReportHTML(report, dash, ds)
    const blob = new Blob([html], { type: 'text/html' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = `${report.title.replace(/\\s+/g,'_')}.html`; a.click()
    URL.revokeObjectURL(url)
    toast.success('Report exported as HTML')
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-surface-container-low animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="flex items-center justify-between px-8 bg-surface-container-low/80 backdrop-blur-xl border-b border-outline-variant/10 shrink-0 h-20 z-20 relative shadow-sm">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shadow-inner">
            <FileText size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-on-surface leading-none mb-1">Reports</h1>
            <p className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">{reports.length} report{reports.length!==1?'s':''} created</p>
          </div>
        </div>
        <button
          className="h-10 px-5 rounded-xl bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-all flex items-center gap-2 shadow-lg shadow-primary/20 hover:scale-105 active:scale-95"
          onClick={() => setShowNew(v=>!v)}
        >
          <Plus size={16} /> New Report
        </button>
      </div>

      <div className="flex-1 overflow-auto p-6 md:p-8">
        <div className="max-w-6xl mx-auto w-full flex flex-col gap-6">

          {/* New report form */}
          {showNew && (
            <div className="glass-card rounded-2xl p-6 border border-white/10 shadow-xl relative overflow-hidden animate-in slide-in-from-top-4 duration-300 z-10">
              <button 
                className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-lg hover:bg-surface-container text-on-surface-variant hover:text-on-surface transition-colors"
                onClick={()=>setShowNew(false)}
              >
                <X size={16} />
              </button>
              
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-primary/10 rounded-xl text-primary"><Plus size={20} /></div>
                <h3 className="text-xl font-black text-on-surface tracking-tight">Create New Report</h3>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div className="flex flex-col gap-2 md:col-span-2">
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider pl-1">Report Title</label>
                  <input 
                    className="h-12 px-4 rounded-xl bg-surface-container-high border border-outline-variant/20 text-on-surface focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all shadow-inner" 
                    value={form.title} 
                    onChange={e=>setForm(p=>({...p,title:e.target.value}))} 
                    placeholder="E.g., Q1 Sales Analysis" 
                    autoFocus
                  />
                </div>
                
                <div className="flex flex-col gap-2 md:col-span-2">
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider pl-1">Description (optional)</label>
                  <textarea 
                    className="p-4 rounded-xl bg-surface-container-high border border-outline-variant/20 text-on-surface focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all shadow-inner resize-none h-24" 
                    value={form.description} 
                    onChange={e=>setForm(p=>({...p,description:e.target.value}))} 
                    placeholder="Brief description of this report's contents..." 
                  />
                </div>
                
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider pl-1 flex items-center gap-2">
                    <BarChart3 size={12} className="text-indigo-400" /> Attached Dashboard
                  </label>
                  <div className="relative">
                    <select 
                      className="w-full h-12 px-4 appearance-none rounded-xl bg-surface-container-high border border-outline-variant/20 text-on-surface font-semibold focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all shadow-inner" 
                      value={form.dashboardId} 
                      onChange={e=>setForm(p=>({...p,dashboardId:e.target.value}))}
                    >
                      <option value="">None Selected</option>
                      {dashboards.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </div>
                  </div>
                </div>
                
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-on-surface-variant uppercase tracking-wider pl-1 flex items-center gap-2">
                    <FileSpreadsheet size={12} className="text-cyan-400" /> Attached Dataset
                  </label>
                  <div className="relative">
                    <select 
                      className="w-full h-12 px-4 appearance-none rounded-xl bg-surface-container-high border border-outline-variant/20 text-on-surface font-semibold focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all shadow-inner" 
                      value={form.datasetId} 
                      onChange={e=>setForm(p=>({...p,datasetId:e.target.value}))}
                    >
                      <option value="">None Selected</option>
                      {datasets.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}
                    </select>
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-outline-variant/10">
                <button className="h-10 px-6 rounded-xl font-bold text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors" onClick={()=>setShowNew(false)}>Cancel</button>
                <button className="h-10 px-6 rounded-xl bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-colors shadow-lg shadow-primary/20" onClick={handleCreate}>Generate Report</button>
              </div>
            </div>
          )}

          {/* Reports list */}
          {reports.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center border-2 border-dashed border-outline-variant/20 rounded-3xl bg-surface-container-low/50 max-w-3xl mx-auto w-full animate-in zoom-in-95 duration-500">
              <div className="w-20 h-20 rounded-full bg-surface-container-high flex items-center justify-center mb-6 shadow-inner">
                <FileText size={32} className="text-on-surface-variant/50" />
              </div>
              <h2 className="text-2xl font-black text-on-surface tracking-tight mb-2">No reports yet</h2>
              <p className="text-on-surface-variant max-w-md mx-auto mb-8">Create a report to bundle dashboards and datasets into a shareable HTML document.</p>
              <button
                className="h-12 px-6 rounded-xl bg-surface-container border border-outline-variant/20 text-on-surface font-bold text-sm hover:bg-surface-container-highest transition-all flex items-center gap-2 shadow-sm"
                onClick={() => setShowNew(true)}
              >
                <Plus size={18} className="text-primary" /> Create First Report
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {reports.map(report => {
                const dash = dashboards.find(d=>d.id===report.dashboardId)
                const ds   = datasets.find(d=>d.id===report.datasetId)
                return (
                  <div key={report.id} className="glass-card rounded-2xl flex flex-col border border-white/5 shadow-md hover:shadow-xl hover:border-outline-variant/30 transition-all group overflow-hidden animate-in fade-in zoom-in-95 duration-300">
                    
                    <div className="p-6 pb-4">
                      <div className="flex items-start justify-between mb-4">
                        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center shadow-inner shrink-0">
                          <FileText size={20} />
                        </div>
                        <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider bg-surface-container-highest text-on-surface-variant border border-outline-variant/10 font-mono">
                          {report.shareToken}
                        </span>
                      </div>
                      
                      <h3 className="font-bold text-lg text-on-surface mb-1 truncate" title={report.title}>{report.title}</h3>
                      {report.description ? (
                        <p className="text-sm text-on-surface-variant line-clamp-2 leading-relaxed h-10">{report.description}</p>
                      ) : (
                        <p className="text-sm text-on-surface-variant/50 italic h-10">No description provided</p>
                      )}
                    </div>

                    <div className="px-6 py-3 bg-surface-container-highest/30 border-y border-outline-variant/5 flex flex-col gap-2">
                      {dash ? (
                        <div className="flex items-center gap-2 text-xs font-semibold text-on-surface">
                          <BarChart3 size={14} className="text-indigo-400" />
                          <span className="truncate">{dash.name}</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-xs font-semibold text-on-surface-variant/50">
                          <BarChart3 size={14} /> None attached
                        </div>
                      )}
                      
                      {ds ? (
                        <div className="flex items-center gap-2 text-xs font-semibold text-on-surface">
                          <FileSpreadsheet size={14} className="text-cyan-400" />
                          <span className="truncate">{ds.name}</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-xs font-semibold text-on-surface-variant/50">
                          <FileSpreadsheet size={14} /> None attached
                        </div>
                      )}
                    </div>

                    <div className="p-4 mt-auto flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">
                        <Calendar size={12} />
                        {timeAgo(report.createdAt)}
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <button
                          className="w-8 h-8 rounded-lg flex items-center justify-center bg-surface-container hover:bg-primary/10 text-on-surface-variant hover:text-primary transition-colors tooltip-trigger"
                          onClick={() => handleCopyLink(report.shareToken)}
                          title="Copy Share Link"
                        >
                          {copiedLink === report.shareToken ? <Check size={14} className="text-emerald-400"/> : <Share2 size={14}/>}
                        </button>
                        <button
                          className="w-8 h-8 rounded-lg flex items-center justify-center bg-surface-container hover:bg-surface-container-highest text-on-surface-variant hover:text-on-surface transition-colors"
                          onClick={() => handleExportReport(report)}
                          title="Download HTML"
                        >
                          <Download size={14}/>
                        </button>
                        <button
                          className="w-8 h-8 rounded-lg flex items-center justify-center bg-surface-container hover:bg-rose-500/10 text-on-surface-variant hover:text-rose-400 transition-colors ml-1 border border-transparent hover:border-rose-500/20"
                          onClick={() => handleDelete(report.id)}
                          title="Delete Report"
                        >
                          <Trash2 size={14}/>
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function buildReportHTML(report, dash, ds) {
  const widgetSummary = dash?.widgets?.map(w => `<li style="margin: 8px 0; color: #cbd5e1; padding-left: 12px; border-left: 2px solid #6366f1;"><strong style="color: #f8fafc;">${w.title}</strong> <span style="font-size: 12px; color: #64748b; background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; margin-left: 6px;">${w.type}</span></li>`).join('') || '<li>No widgets</li>'
  const stats = ds ? `<p style="margin-top: 12px; font-size: 15px;"><strong>Dataset:</strong> <span style="color: #38bdf8;">${ds.name}</span> <br/><span style="color: #94a3b8; font-size: 14px; margin-top: 4px; display: inline-block;">${ds.rows?.toLocaleString()} rows · ${ds.columns} columns</span></p>` : ''
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>${report.title} — Xplor Report</title>
  <style>
    body { font-family: 'Inter', system-ui, sans-serif; background: #0a0b10; color: #f1f5f9; padding: 0; margin: 0; line-height: 1.6; }
    .container { max-width: 800px; margin: 40px auto; padding: 40px; background: #13141f; border: 1px solid rgba(255,255,255,0.05); border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); }
    .header { margin-bottom: 32px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 24px; }
    h1 { font-size: 36px; font-weight: 900; margin: 0 0 12px 0; letter-spacing: -0.02em; background: linear-gradient(to right, #818cf8, #22d3ee); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    p.desc { color: #cbd5e1; font-size: 18px; margin: 0 0 16px 0; }
    ul { margin: 16px 0; padding-left: 0; list-style: none; }
    .badge { display:inline-block; padding:4px 12px; background:rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.2); border-radius:999px; font-size:12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color:#818cf8; margin-right:8px; }
    .section { background: rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.05); border-radius:16px; padding:24px; margin:24px 0; }
    h3 { margin: 0 0 16px 0; font-size: 18px; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 8px; }
    .footer { color:#64748b; font-size:13px; margin-top:40px; text-align: center; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>${report.title}</h1>
      ${report.description ? `<p class="desc">${report.description}</p>` : ''}
      <div style="margin-top: 16px;">
        <span class="badge">Generated by Xplor</span>
        <span class="badge" style="background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); color: #cbd5e1;">${new Date().toLocaleDateString()}</span>
      </div>
    </div>
    
    ${ds ? `<div class="section"><h3>📊 Attached Dataset</h3>${stats}</div>` : ''}
    ${dash ? `<div class="section"><h3>📈 Attached Dashboard: ${dash.name}</h3><ul>${widgetSummary}</ul></div>` : ''}
    
    <div class="footer">
      <p><strong>Xplor Data Intelligence Platform</strong></p>
      <p style="font-family: monospace; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 8px; display: inline-block; border: 1px solid rgba(255,255,255,0.05);">Share token: ${report.shareToken}</p>
    </div>
  </div>
</body>
</html>`
}
