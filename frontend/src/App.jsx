import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from './store/authStore'
import AppShell from './components/layout/AppShell'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import DatasetsPage from './pages/DatasetsPage'
import CleanPage from './pages/CleanPage'
import ExplorePage from './pages/ExplorePage'
import DashboardPage from './pages/DashboardPage'
import ReportsPage from './pages/ReportsPage'
import SettingsPage from './pages/SettingsPage'
import ChatPage from './pages/ChatPage'

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-elevated)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--text-sm)',
          },
          success: { iconTheme: { primary: 'var(--accent-emerald)', secondary: 'var(--bg-elevated)' } },
          error:   { iconTheme: { primary: 'var(--accent-rose)',    secondary: 'var(--bg-elevated)' } },
        }}
      />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }>
          <Route index element={<Navigate to="/home" replace />} />
          <Route path="home"       element={<HomePage />} />
          <Route path="datasets"   element={<DatasetsPage />} />
          <Route path="clean/:id"  element={<CleanPage />} />
          <Route path="explore/:id" element={<ExplorePage />} />
          <Route path="dashboard"  element={<DashboardPage />} />
          <Route path="reports"    element={<ReportsPage />} />
          <Route path="settings"   element={<SettingsPage />} />
          <Route path="chat/:id"   element={<ChatPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/home" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
