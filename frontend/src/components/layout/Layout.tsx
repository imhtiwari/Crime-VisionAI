import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  FolderOpen, 
  Image as ImageIcon, 
  Video, 
  Mic, 
  Clock, 
  MessageSquare, 
  Box, 
  FileText, 
  Settings,
  Menu,
  X,
  Activity,
  Server
} from 'lucide-react'

const Layout = ({ children }: { children: React.ReactNode }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const location = useLocation()
  const [backendStatus, setBackendStatus] = useState<'connected' | 'disconnected'>('disconnected')
  const [modelStatus, setModelStatus] = useState('checking')

  useEffect(() => {
    let active = true
    const checkBackend = async () => {
      try {
        const [health, capabilities] = await Promise.all([
          fetch('/api/v1/health'),
          fetch('/api/v1/capabilities'),
        ])
        if (active) {
          setBackendStatus(health.ok ? 'connected' : 'disconnected')
          const data = await capabilities.json()
          setModelStatus(data.modules?.object_detection || 'unknown')
        }
      } catch {
        if (active) {
          setBackendStatus('disconnected')
          setModelStatus('unavailable')
        }
      }
    }
    void checkBackend()
    const timer = window.setInterval(checkBackend, 30000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Overview' },
    { path: '/evidence', icon: FolderOpen, label: 'Evidence Vault' },
    { path: '/analysis/image', icon: ImageIcon, label: 'Image Analysis' },
    { path: '/analysis/video', icon: Video, label: 'Video Analysis' },
    { path: '/analysis/audio', icon: Mic, label: 'Audio Analysis' },
    { path: '/timeline', icon: Clock, label: 'Forensic Timeline' },
    { path: '/chat', icon: MessageSquare, label: 'AI Assistant' },
    { path: '/viewer', icon: Box, label: '3D Scene Viewer' },
    { path: '/reports', icon: FileText, label: 'Reports' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <div className="flex h-screen bg-navy-900">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-16'} bg-navy-800 border-r border-gray-700 transition-all duration-300 flex flex-col`}>
        {/* Logo */}
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-cyan-500 rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            {sidebarOpen && (
              <div>
                <h1 className="text-white font-bold text-lg">CrimeVision AI</h1>
                <p className="text-gray-400 text-xs">Forensic Analysis</p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2 overflow-y-auto">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-cyan-600 text-white'
                        : 'text-gray-300 hover:bg-navy-700'
                    }`}
                  >
                    <Icon className="w-5 h-5 flex-shrink-0" />
                    {sidebarOpen && <span className="text-sm">{item.label}</span>}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Status */}
        <div className="p-4 border-t border-gray-700">
          {sidebarOpen && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs">
                <Server className="w-4 h-4" />
                <span className="text-gray-400">Backend:</span>
                <span className={`${
                  backendStatus === 'connected' ? 'text-green-400' : 'text-red-400'
                }`}>
                  {backendStatus}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <Activity className="w-4 h-4" />
                <span>Object detection: {modelStatus}</span>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-navy-800 border-b border-gray-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-navy-700 rounded-lg transition-colors"
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-400">Workspace: Default</div>
              <div className="w-8 h-8 bg-cyan-600 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-medium">U</span>
              </div>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}

export default Layout
