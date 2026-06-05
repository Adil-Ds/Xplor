import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import TopBar from './TopBar'

export default function AppShell() {
  return (
    <div className="flex min-h-screen overflow-x-hidden bg-background">
      <Sidebar />

      <div className="ml-64 flex-grow flex flex-col relative h-screen">
        <TopBar />

        <main className="flex-grow overflow-y-auto flex flex-col custom-scrollbar">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
