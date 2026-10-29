import { useEffect, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { Grid, OrbitControls, Text } from '@react-three/drei'
import { Box } from 'lucide-react'
import { api, errorMessage, type EvidenceItem } from '../services/api'

type Detection = { id: string; label: string; confidence: number; bbox: { x1: number; y1: number; x2: number; y2: number } }
type Analysis = { analysis_id: string; processing_status: string; result_metadata: { image?: { width: number; height: number } } | null; findings: Detection[] }

const Marker = ({ detection, imageSize, onSelect }: { detection: Detection; imageSize: { width: number; height: number }; onSelect: (item: Detection) => void }) => {
  const centerX = ((detection.bbox.x1 + detection.bbox.x2) / 2 / imageSize.width - 0.5) * 8
  const centerZ = ((detection.bbox.y1 + detection.bbox.y2) / 2 / imageSize.height - 0.5) * -6
  const width = Math.max(0.08, (detection.bbox.x2 - detection.bbox.x1) / imageSize.width * 8)
  const depth = Math.max(0.08, (detection.bbox.y2 - detection.bbox.y1) / imageSize.height * 6)
  const corners: [number, number, number][] = [[centerX-width/2,0.04,centerZ-depth/2],[centerX+width/2,0.04,centerZ-depth/2],[centerX+width/2,0.04,centerZ+depth/2],[centerX-width/2,0.04,centerZ+depth/2],[centerX-width/2,0.04,centerZ-depth/2]]
  return <group onClick={(event) => { event.stopPropagation(); onSelect(detection) }}><mesh position={[centerX,0.15,centerZ]}><sphereGeometry args={[0.09,16,16]} /><meshStandardMaterial color="#22d3ee" emissive="#083344" /></mesh><line><bufferGeometry><bufferAttribute attach="attributes-position" args={[new Float32Array(corners.flat()),3]} /></bufferGeometry><lineBasicMaterial color="#22d3ee" /></line><Text position={[centerX,0.24,centerZ]} fontSize={0.18} color="#e2e8f0" anchorX="center" anchorY="bottom">{detection.label}</Text></group>
}

const SceneViewer = () => {
  const [images, setImages] = useState<EvidenceItem[]>([])
  const [selected, setSelected] = useState<EvidenceItem | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null)
  const [error, setError] = useState('')

  useEffect(() => { api.get('/evidence', { params: { media_type: 'image', per_page: 100 } }).then((response) => setImages(response.data.evidence)).catch((err: unknown) => setError(errorMessage(err, 'Could not load image evidence.'))) }, [])

  const inspect = async (item: EvidenceItem) => {
    setSelected(item); setAnalysis(null); setSelectedDetection(null); setError('')
    try {
      const detail = await api.get<EvidenceItem>(`/evidence/${item.id}`)
      const latest = detail.data.analysis_history?.[0]
      if (!latest) return
      const result = await api.get<Analysis>(`/analysis/${latest.analysis_id}`)
      setAnalysis(result.data)
    } catch (err) { setError(errorMessage(err, 'Could not load analysis details.')) }
  }

  const imageSize = analysis?.result_metadata?.image || { width: 1, height: 1 }

  return (
    <div className="space-y-6">
      <header><p className="text-sm font-medium uppercase tracking-wider text-cyan-400">Visual inspection</p><h1 className="mt-1 text-2xl font-bold text-white">3D Scene Viewer</h1><p className="mt-2 text-sm text-gray-400">An illustrative projection of image bounding boxes onto a flat plane. It does not estimate real-world depth or positions.</p></header>
      {error && <p role="alert" className="rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
      <div className="grid gap-5 xl:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="rounded-xl border border-gray-700 bg-navy-800 p-4"><h2 className="font-semibold text-white">Analyzed images</h2><ul className="mt-3 space-y-1">{images.map((image) => <li key={image.id}><button onClick={() => void inspect(image)} className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm ${selected?.id === image.id ? 'bg-cyan-900 text-white' : 'text-gray-300 hover:bg-navy-700'}`}>{image.original_filename}</button></li>)}</ul>{!images.length && <p className="mt-3 text-sm text-gray-400">Upload an image to inspect supported scene markers.</p>}</aside>
        <section className="space-y-4">
          <div className="overflow-hidden rounded-xl border border-gray-700 bg-[#0b1220]"><div className="flex items-center justify-between border-b border-gray-700 px-4 py-3"><h2 className="font-medium text-white">Illustrative 2D projection layout</h2><button onClick={() => setSelectedDetection(null)} className="rounded border border-gray-700 px-2 py-1 text-xs text-gray-300">Reset selection</button></div><div className="h-[60vh] min-h-80"><Canvas camera={{ position: [7, 8, 10], fov: 42 }}><color attach="background" args={['#0b1220']} /><ambientLight intensity={0.8} /><directionalLight position={[5,8,5]} intensity={1.3} /><Grid args={[10,8]} position={[0,0,0]} cellColor="#1e3a50" sectionColor="#155e75" fadeDistance={15} infiniteGrid /><OrbitControls makeDefault minDistance={5} maxDistance={30} />{analysis?.findings.map((detection) => <Marker key={detection.id} detection={detection} imageSize={imageSize} onSelect={setSelectedDetection} />)}</Canvas></div></div>
          <div className="grid gap-4 md:grid-cols-2"><div className="rounded-xl border border-gray-700 bg-navy-800 p-4"><h3 className="flex items-center gap-2 font-medium text-white"><Box className="h-4 w-4 text-cyan-400" />Selected evidence</h3><p className="mt-2 text-sm text-gray-300">{selected?.original_filename || 'Choose an image to inspect its latest stored analysis.'}</p><p className="mt-1 text-xs text-gray-500">Analysis status: {analysis?.processing_status || 'No analysis loaded'}</p></div><div className="rounded-xl border border-gray-700 bg-navy-800 p-4"><h3 className="font-medium text-white">Marker details</h3>{selectedDetection ? <><p className="mt-2 text-sm text-gray-200">{selectedDetection.label} · model score {selectedDetection.confidence.toFixed(3)}</p><p className="mt-1 text-xs text-gray-400">2D source bounding box: {selectedDetection.bbox.x1.toFixed(1)}, {selectedDetection.bbox.y1.toFixed(1)} — {selectedDetection.bbox.x2.toFixed(1)}, {selectedDetection.bbox.y2.toFixed(1)}</p></> : <p className="mt-2 text-sm text-gray-400">Select an object marker in the view.</p>}<p className="mt-3 text-xs text-amber-300">No depth or room geometry is inferred from a single 2D image.</p></div></div>
          {analysis && analysis.findings.length === 0 && <p className="rounded-lg border border-amber-800 bg-amber-950/30 p-3 text-sm text-amber-200">No detections are recorded for this image. Markers are never synthesized to populate the viewer.</p>}
        </section>
      </div>
    </div>
  )
}

export default SceneViewer
