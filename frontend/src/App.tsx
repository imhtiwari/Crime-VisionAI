import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import EvidenceVault from './pages/EvidenceVault'
import ImageAnalysis from './pages/ImageAnalysis'
import VideoAnalysis from './pages/VideoAnalysis'
import AudioAnalysis from './pages/AudioAnalysis'
import Timeline from './pages/Timeline'
import Chat from './pages/Chat'
import SceneViewer from './pages/SceneViewer'
import Reports from './pages/Reports'
import Settings from './pages/Settings'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/evidence" element={<EvidenceVault />} />
          <Route path="/analysis/image" element={<ImageAnalysis />} />
          <Route path="/analysis/video" element={<VideoAnalysis />} />
          <Route path="/analysis/audio" element={<AudioAnalysis />} />
          <Route path="/timeline" element={<Timeline />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/viewer" element={<SceneViewer />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
