import { NavLink, useLocation } from 'react-router-dom'
import { useDatasetStore } from '../../store/datasetStore'
import toast from 'react-hot-toast'

export default function TopBar() {
  const location = useLocation()
  const { datasets } = useDatasetStore()
  
  // Extract base route and possible dataset ID (e.g., /clean/123 -> base=/clean, id=123)
  const pathParts = location.pathname.split('/')
  const baseRoute = '/' + (pathParts[1] || '')
  
  // If we don't have a datasetId in the URL, try to fallback to the first dataset available
  // This prevents the buttons from feeling "broken" if the user hasn't explicitly selected one from Overview.
  const urlDatasetId = pathParts[2] || null
  const defaultDatasetId = datasets.length > 0 ? datasets[0].id : null
  const datasetId = urlDatasetId || defaultDatasetId

  const handleNavClick = (e, targetName) => {
    if (!datasetId) {
      e.preventDefault()
      toast.error(`Please upload or select a dataset from the Overview to use ${targetName}.`)
    }
  }

  const getLinkTo = (targetBase) => {
    return datasetId ? `${targetBase}/${datasetId}` : '/datasets'
  }

  return (
    <header className="sticky top-0 z-50 flex justify-between items-center px-8 w-full h-16 bg-surface-container/70 backdrop-blur-xl border-b border-outline-variant/10">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-6">
          <NavLink 
            to="/datasets"
            className={`font-body-base text-sm font-semibold transition-colors duration-200 ${baseRoute === '/datasets' || baseRoute === '/home' ? 'text-primary border-b-2 border-primary pb-1' : 'text-on-surface-variant hover:text-primary'}`}
          >
            Overview
          </NavLink>
          <NavLink 
            to={getLinkTo('/clean')}
            onClick={(e) => handleNavClick(e, 'Clean')}
            className={`font-body-base text-sm font-semibold transition-colors duration-200 ${baseRoute === '/clean' ? 'text-primary border-b-2 border-primary pb-1' : 'text-on-surface-variant hover:text-primary'}`}
          >
            Clean
          </NavLink>
          <NavLink 
            to={getLinkTo('/chat')}
            onClick={(e) => handleNavClick(e, 'Chat')}
            className={`font-body-base text-sm font-semibold transition-colors duration-200 ${baseRoute === '/chat' ? 'text-primary border-b-2 border-primary pb-1' : 'text-on-surface-variant hover:text-primary'}`}
          >
            Chat
          </NavLink>
          <NavLink 
            to={getLinkTo('/explore')}
            onClick={(e) => handleNavClick(e, 'Explore')}
            className={`font-body-base text-sm font-semibold transition-colors duration-200 ${baseRoute === '/explore' ? 'text-primary border-b-2 border-primary pb-1' : 'text-on-surface-variant hover:text-primary'}`}
          >
            Explore
          </NavLink>
        </div>
      </div>
      
      <div className="flex items-center gap-4">
        {/* Sync Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-container-high border border-outline-variant/20 shadow-inner">
          <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></div>
          <span className="text-[11px] font-label-caps text-cyan-400 uppercase tracking-wider">Local Sync: Online</span>
        </div>
        
        {/* Topbar actions */}
        <div className="flex items-center gap-2 text-on-surface-variant">
          <button className="p-2 hover:bg-surface-container-highest hover:text-primary rounded-full transition-all active:scale-95">
            <span className="material-symbols-outlined text-[20px]">account_tree</span>
          </button>
          <button className="p-2 hover:bg-surface-container-highest hover:text-primary rounded-full transition-all active:scale-95">
            <span className="material-symbols-outlined text-[20px]">settings</span>
          </button>
        </div>
      </div>
    </header>
  )
}
