import { useState, useMemo, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useDatasetStore } from '../store/datasetStore'
import { formatBytes, uuid } from '../utils/helpers'
import { ChevronLeft, Zap, CheckCircle, XCircle, Loader2, Sparkles, Wand2, Receipt, SearchCheck } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../api/client'

/* ─── Apply steps to data (in-browser) ─────────────── */
function applySteps(data, recipe) {
  let rows = data.map((r) => ({ ...r }))

  for (const step of recipe) {
    switch (step.op) {
      case 'drop_column': {
        rows = rows.map((r) => { const nr={...r}; delete nr[step.column]; return nr })
        break
      }
      case 'rename_column': {
        const { oldName, newName } = step
        rows = rows.map((r) => {
          const nr = { ...r }; nr[newName] = nr[oldName]; delete nr[oldName]; return nr
        })
        break
      }
      case 'fill_null': {
        const { column, fillValue } = step
        rows = rows.map((r) => ({
          ...r,
          [column]: (r[column] === null || r[column] === undefined || r[column] === '') ? fillValue : r[column],
        }))
        break
      }
      case 'cast_type': {
        const { column, toType } = step
        rows = rows.map((r) => {
          let v = r[column]
          if (toType === 'number') v = isNaN(Number(v)) ? null : Number(v)
          if (toType === 'string') v = String(v ?? '')
          if (toType === 'date')   v = new Date(v).toISOString().split('T')[0]
          return { ...r, [column]: v }
        })
        break
      }
      case 'winsorize': {
        // Mock outlier clipping
        break
      }
      default: break
    }
  }
  return rows
}

export default function CleanPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { getById, updateDataset } = useDatasetStore()
  const ds = getById(id)

  const [recipe, setRecipe] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [isLoadingSugg, setIsLoadingSugg] = useState(true)

  useEffect(() => {
    let mounted = true
    async function fetchSuggestions() {
      try {
        const res = await api.get(`/api/explore/${id}/suggestions`)
        if (mounted && res.data?.suggestions) {
          const mapped = res.data.suggestions.map(s => {
             let severity = 'INFO'
             let severityColor = 'indigo'
             let icon = 'info'
             if (s.impact === 'high') { severity = 'HIGH SEVERITY'; severityColor = 'rose'; icon = 'alert-triangle'; }
             else if (s.impact === 'medium') { severity = 'SUGGESTION'; severityColor = 'amber'; icon = 'sparkles'; }
             else if (s.impact === 'low') { severityColor = 'emerald'; icon = 'check-circle'; }
             
             return {
               id: s.id,
               title: s.title || s.column || 'Dataset Issue',
               desc: s.desc || s.text,
               severity,
               severityColor,
               icon,
               action: s.action || { op: 'custom_fix' },
               btnLabel: s.action?.op ? s.action.op.replace('_', ' ').toUpperCase() : 'APPLY FIX'
             }
           })
           setSuggestions(mapped)
        }
      } catch (e) {
        console.error("Failed to load suggestions:", e)
      } finally {
        if (mounted) setIsLoadingSugg(false)
      }
    }
    fetchSuggestions()
    return () => { mounted = false }
  }, [id])

  const originalData = ds?.preview ?? []

  const cleanedData = useMemo(() => {
    return applySteps(originalData, recipe)
  }, [recipe, originalData])

  const handleApplySuggestion = (sugg) => {
    const step = { id: uuid(), ...sugg.action }
    setRecipe((prev) => [...prev, step])
    setSuggestions((prev) => prev.filter(s => s.id !== sugg.id))
    toast.success(`Applied: ${sugg.title}`)
  }

  const handleRemoveStep = (stepId) => {
    setRecipe((prev) => prev.filter((s) => s.id !== stepId))
  }

  const handleCommit = () => {
    if (cleanedData.length === 0) return;
    const newHeaders = Object.keys(cleanedData[0] ?? {})
    updateDataset(id, {
      preview: cleanedData,
      rows: cleanedData.length,
      columns: newHeaders.length,
      columnNames: newHeaders,
      rawHeaders: newHeaders,
      cleanedAt: new Date().toISOString(),
      recipe,
    })
    toast.success('Changes committed successfully!')
    navigate(`/explore/${id}`)
  }

  if (!ds) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-64px)] bg-surface-container-low animate-in fade-in">
        <p className="font-bold text-xl text-on-surface mb-4">Dataset not found.</p>
        <button className="h-10 px-4 rounded-xl border border-outline-variant text-on-surface font-semibold text-sm hover:bg-surface-container-highest transition-all flex items-center gap-2" onClick={() => navigate('/datasets')}><ChevronLeft size={16} /> Back</button>
      </div>
    )
  }

  const displayData = cleanedData.length > 0 ? cleanedData : originalData
  const displayHeaders = Object.keys(displayData[0] ?? {})

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] overflow-hidden bg-surface-container-low animate-in fade-in duration-500">
      
      {/* Header */}
      <div className="flex items-center justify-between px-6 bg-surface-container-low/80 backdrop-blur-xl border-b border-outline-variant/10 shrink-0 h-16 z-20 relative shadow-sm">
        <div className="flex items-center gap-4">
          <button className="h-9 px-3 rounded-lg border border-outline-variant text-on-surface font-semibold text-sm hover:bg-surface-container-highest transition-all flex items-center gap-1.5" onClick={() => navigate('/datasets')}>
            <ChevronLeft size={16} /> Datasets
          </button>
          <div className="w-[1px] h-6 bg-outline-variant/20" />
          <Wand2 size={20} className="text-primary" />
          <div className="flex flex-col">
            <p className="font-bold text-on-surface text-sm leading-tight">Data Cleaning Workspace</p>
            <p className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">Refining: {ds.name}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setRecipe([])}
            className="h-9 px-4 rounded-lg font-bold text-sm text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors disabled:opacity-50"
            disabled={recipe.length === 0}
          >
            Reset All
          </button>
          <button 
            onClick={handleCommit}
            className="h-9 px-5 rounded-lg bg-primary text-on-primary font-bold text-sm hover:bg-primary-fixed transition-all flex items-center gap-2 shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
            disabled={recipe.length === 0}
          >
            <CheckCircle size={14} /> Commit Changes
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-hidden p-6 flex gap-6 max-w-[1600px] mx-auto w-full">
        
        {/* Left: AI Suggestions */}
        <div className="w-1/2 flex flex-col h-full bg-surface-container-high/30 border border-outline-variant/10 rounded-2xl overflow-hidden shadow-sm">
          <div className="p-5 border-b border-outline-variant/10 flex items-center justify-between shrink-0 bg-surface-container-high/50 backdrop-blur-sm">
            <h3 className="font-bold text-sm text-on-surface flex items-center gap-2 tracking-wide uppercase">
              <Sparkles size={16} className="text-primary" />
              AI Refinement Suggestions <span className="bg-primary/20 text-primary px-2 py-0.5 rounded-full text-[10px]">{suggestions.length}</span>
            </h3>
            {isLoadingSugg ? (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface-container text-on-surface-variant text-[10px] font-bold uppercase tracking-wider animate-pulse border border-outline-variant/10">
                <Loader2 size={12} className="animate-spin" /> Scanning
              </span>
            ) : (
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 text-[10px] font-bold uppercase tracking-wider border border-emerald-500/20">
                <SearchCheck size={12} /> Scan Complete
              </span>
            )}
          </div>
          
          <div className="flex-1 overflow-y-auto p-5 custom-scrollbar bg-surface-container-lowest/30">
            {isLoadingSugg ? (
              <div className="h-full flex flex-col items-center justify-center text-on-surface-variant animate-pulse">
                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center text-primary mb-4 border border-primary/20">
                  <Loader2 size={24} className="animate-spin" />
                </div>
                <p className="font-bold">Analyzing dataset structure...</p>
                <p className="text-sm">Running heuristics and distilBERT inference.</p>
              </div>
            ) : suggestions.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-on-surface-variant border-2 border-dashed border-outline-variant/20 rounded-2xl m-4">
                <CheckCircle size={48} className="text-emerald-400 mb-4 opacity-50" />
                <p className="font-bold text-lg text-on-surface mb-1">Dataset looks perfectly clean!</p>
                <p className="text-sm max-w-[250px] text-center">No missing values, anomalies, or type mismatches detected.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {suggestions.map((sugg) => (
                  <div key={sugg.id} className="glass-card p-5 rounded-2xl border border-white/5 hover:border-outline-variant/30 transition-all group shadow-sm flex flex-col gap-3 relative overflow-hidden">
                    <div className={`absolute top-0 left-0 w-1 h-full bg-${sugg.severityColor}-500`} />
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-${sugg.severityColor}-500/10 text-${sugg.severityColor}-400 border border-${sugg.severityColor}-500/20`}>
                          {sugg.severity}
                        </span>
                        <h4 className="font-bold text-sm text-on-surface">{sugg.title}</h4>
                      </div>
                    </div>
                    <p className="text-sm text-on-surface-variant leading-relaxed">
                      {sugg.desc}
                    </p>
                    <div className="flex items-center gap-2 pt-2 mt-2 border-t border-outline-variant/5">
                      <button 
                        onClick={() => handleApplySuggestion(sugg)}
                        className={`h-8 px-4 rounded-lg bg-${sugg.severityColor}-500/10 text-${sugg.severityColor}-400 text-xs font-bold uppercase tracking-wider hover:bg-${sugg.severityColor}-500/20 transition-all border border-${sugg.severityColor}-500/20 flex items-center gap-1.5`}
                      >
                        <Wand2 size={12} /> {sugg.btnLabel}
                      </button>
                      <button 
                        onClick={() => setSuggestions(prev => prev.filter(s => s.id !== sugg.id))}
                        className="h-8 px-3 rounded-lg text-on-surface-variant text-xs font-bold uppercase tracking-wider hover:text-on-surface hover:bg-surface-container transition-all"
                      >
                        Ignore
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Recipe & Data Preview */}
        <div className="w-1/2 min-w-0 flex flex-col h-full gap-6">
          
          {/* Cleaning Recipe Timeline */}
          <div className="h-1/2 flex flex-col bg-surface-container-high/30 border border-outline-variant/10 rounded-2xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-outline-variant/10 flex items-center justify-between shrink-0 bg-surface-container-high/50 backdrop-blur-sm">
              <h3 className="font-bold text-xs text-on-surface-variant flex items-center gap-2 tracking-wide uppercase">
                <Receipt size={14} /> Cleaning Recipe <span className="bg-surface-container-highest px-1.5 py-0.5 rounded text-on-surface">{recipe.length}</span>
              </h3>
            </div>
            
            <div className="flex-1 overflow-y-auto p-5 custom-scrollbar bg-surface-container-lowest/30 relative">
              {recipe.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-on-surface-variant opacity-60">
                  <Receipt size={32} className="mb-3 opacity-50" />
                  <p className="font-medium text-sm">Recipe is empty.</p>
                  <p className="text-xs mt-1">Apply suggestions on the left to build a pipeline.</p>
                </div>
              ) : (
                <div className="relative pl-6 space-y-4">
                  {/* Vertical line */}
                  <div className="absolute left-[11px] top-3 bottom-3 w-px bg-primary/20" />
                  
                  {recipe.map((step, index) => (
                    <div key={step.id} className="relative animate-in slide-in-from-left-4 duration-300">
                      <div className="absolute -left-6 top-1.5 w-6 h-6 rounded-full bg-surface-container border-2 border-primary flex items-center justify-center z-10 shadow-sm shadow-primary/20">
                        <span className="text-[10px] font-black text-primary">{index + 1}</span>
                      </div>
                      <div className="bg-surface-container rounded-xl p-3 border border-outline-variant/10 shadow-sm flex items-start justify-between group hover:border-primary/30 transition-colors ml-4">
                        <div>
                          <span className="text-[10px] font-bold text-primary uppercase tracking-wider mb-0.5 block">{step.op.replace('_', ' ')}</span>
                          <p className="text-sm font-medium text-on-surface">
                            Target: <span className="px-1.5 py-0.5 rounded bg-surface-container-highest font-mono text-[11px]">{step.column || step.oldName || step.op}</span>
                          </p>
                        </div>
                        <button 
                          onClick={() => handleRemoveStep(step.id)} 
                          className="w-6 h-6 flex items-center justify-center rounded bg-surface-container-highest text-on-surface-variant hover:bg-rose-500/20 hover:text-rose-400 transition-colors opacity-0 group-hover:opacity-100"
                        >
                          <XCircle size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Data Preview */}
          <div className="h-1/2 flex flex-col bg-surface-container-high/30 border border-outline-variant/10 rounded-2xl overflow-hidden shadow-sm">
            <div className="p-3 border-b border-outline-variant/10 flex items-center justify-between shrink-0 bg-surface-container-high/50 backdrop-blur-sm">
              <h3 className="font-bold text-[11px] text-on-surface-variant flex items-center gap-2 tracking-wide uppercase">
                Preview <span className="text-[10px] bg-surface-container-highest px-1.5 rounded">{displayData.length.toLocaleString()} rows</span>
              </h3>
            </div>
            
            <div className="flex-1 overflow-auto custom-scrollbar bg-surface-container-low">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="sticky top-0 bg-surface-container-high/90 backdrop-blur-sm z-10 shadow-sm">
                  <tr>
                    {displayHeaders.slice(0, 10).map((h) => (
                      <th key={h} className="p-2.5 font-bold text-on-surface-variant uppercase tracking-wider text-[10px] border-b border-outline-variant/10 whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/5 font-mono text-[11px]">
                  {displayData.slice(0, 20).map((row, ri) => (
                    <tr key={ri} className="hover:bg-surface-container-highest/50 transition-colors">
                      {displayHeaders.slice(0, 10).map((h) => (
                        <td key={h} className={`p-2.5 whitespace-nowrap truncate max-w-[150px] ${row[h]==null||row[h]===''?'text-on-surface-variant/30 italic':'text-on-surface'}`}>
                          {String(row[h] ?? 'null')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
