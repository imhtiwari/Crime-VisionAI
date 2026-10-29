import { useEffect, useState } from 'react'
import { Image as ImageIcon, Play, RefreshCw } from 'lucide-react'
import { api, errorMessage, type EvidenceItem } from '../services/api'

type Detection = { label: string; confidence: number; bbox: { x1: number; y1: number; x2: number; y2: number } }
type ImageResult = {
  analysis_id: string
  evidence_id: string
  status: string
  image_metadata: { format: string; width: number; height: number }
  detector: { model: string | null; status: string; detections: Detection[] }
  caption: { status: string; text: string | null; model: string | null }
  artifacts: Array<{ kind: string; download_url: string }>
  warnings: string[]
}

const ImageAnalysis = () => {
  const [images, setImages] = useState<EvidenceItem[]>([])
  const [selected, setSelected] = useState<EvidenceItem | null>(null)
  const [result, setResult] = useState<ImageResult | null>(null)
  const [threshold, setThreshold] = useState(0.5)
  const [showBoxes, setShowBoxes] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/evidence', { params: { media_type: 'image', per_page: 100 } })
      .then((response) => setImages(response.data.evidence))
      .catch((err: unknown) => setError(errorMessage(err, 'Could not load images.')))
  }, [])

  const runAnalysis = async () => {
    if (!selected) return
    setLoading(true)
    setError('')
    try {
      const response = await api.post<ImageResult>(`/analysis/image/${selected.id}`, { confidence_threshold: threshold })
      setResult(response.data)
    } catch (err) {
      setError(errorMessage(err, 'Image analysis could not be completed.'))
    } finally {
      setLoading(false)
    }
  }

  const imageUrl = selected ? `/api/v1/evidence/${selected.id}/preview` : ''

  return (
    <div className="space-y-6">
      <header><p className="text-sm font-medium uppercase tracking-wider text-cyan-400">Preliminary analysis</p><h1 className="mt-1 text-2xl font-bold text-white">Image Analysis</h1><p className="mt-2 text-sm text-gray-400">Inspect source imagery and any predictions returned by the configured local model.</p></header>
      {error && <p role="alert" className="rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
      <div className="grid gap-5 xl:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="rounded-xl border border-gray-700 bg-navy-800 p-4">
          <h2 className="font-semibold text-white">Image evidence</h2>
          <ul className="mt-3 max-h-[65vh] space-y-1 overflow-y-auto">
            {images.map((image) => <li key={image.id}><button onClick={() => { setSelected(image); setResult(null) }} className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm ${selected?.id === image.id ? 'bg-cyan-900 text-white' : 'text-gray-300 hover:bg-navy-700'}`}>{image.original_filename}</button></li>)}
          </ul>
          {!images.length && <p className="mt-3 text-sm text-gray-400">Upload an image in the Evidence Vault to begin.</p>}
        </aside>

        <section className="min-w-0 space-y-5">
          <div className="rounded-xl border border-gray-700 bg-navy-800 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h2 className="font-semibold text-white">Source image</h2><p className="mt-1 text-xs text-gray-400">Original file is served read-only.</p></div>
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-2 text-xs text-gray-300">Score threshold <input type="range" min="0" max="1" step="0.05" value={threshold} onChange={(event) => setThreshold(Number(event.target.value))} /><span className="w-10 text-right">{threshold.toFixed(2)}</span></label>
                <label className="flex items-center gap-2 text-xs text-gray-300"><input type="checkbox" checked={showBoxes} onChange={(event) => setShowBoxes(event.target.checked)} />Show boxes</label>
                <button disabled={!selected || loading} onClick={() => void runAnalysis()} className="inline-flex items-center gap-2 rounded-lg bg-cyan-700 px-3 py-2 text-sm font-medium text-white hover:bg-cyan-600 disabled:opacity-50">{loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}{loading ? 'Analyzing…' : 'Run analysis'}</button>
              </div>
            </div>
            <div className="mt-4 flex min-h-64 items-center justify-center overflow-hidden rounded-lg bg-black/30 p-3">
              {!selected ? <div className="text-center text-gray-500"><ImageIcon className="mx-auto h-8 w-8" /><p className="mt-2 text-sm">Select an image from evidence.</p></div> : (
                <div className="relative inline-block leading-none">
                  <img src={imageUrl} alt={`Evidence image ${selected.original_filename}`} className="block max-h-[65vh] max-w-full object-contain" />
                  {showBoxes && result?.detector.detections.map((detection, index) => <div key={`${detection.label}-${index}`} className="pointer-events-none absolute border-2 border-cyan-300" style={{ left: `${100 * detection.bbox.x1 / result.image_metadata.width}%`, top: `${100 * detection.bbox.y1 / result.image_metadata.height}%`, width: `${100 * (detection.bbox.x2 - detection.bbox.x1) / result.image_metadata.width}%`, height: `${100 * (detection.bbox.y2 - detection.bbox.y1) / result.image_metadata.height}%` }} />)}
                </div>
              )}
            </div>
          </div>

          {result && <div className="grid gap-5 lg:grid-cols-2">
            <div className="rounded-xl border border-gray-700 bg-navy-800 p-5">
              <h2 className="font-semibold text-white">Analysis status: <span className="text-cyan-300">{result.status}</span></h2>
              <p className="mt-1 text-xs text-gray-400">Model: {result.detector.model || 'not configured'} · Detector status: {result.detector.status}</p>
              <p className="mt-4 text-sm text-gray-300">{result.image_metadata.format} · {result.image_metadata.width} × {result.image_metadata.height} pixels</p>
              <h3 className="mt-5 text-sm font-semibold text-white">Object detections</h3>
              {result.detector.detections.length ? <ul className="mt-2 divide-y divide-gray-700">{result.detector.detections.map((item, index) => <li key={`${item.label}-${index}`} className="flex justify-between gap-4 py-2 text-sm"><span className="text-gray-200">{item.label}</span><span className="text-gray-400">model score {item.confidence.toFixed(3)}</span></li>)}</ul> : <p className="mt-2 text-sm text-gray-400">No predictions available from a configured detector.</p>}
              <p className="mt-4 text-xs text-amber-300">Model scores are not probabilities of criminal activity. Automated outputs are preliminary and require human review.</p>
            </div>
            <div className="rounded-xl border border-gray-700 bg-navy-800 p-5">
              <h2 className="font-semibold text-white">Scene caption</h2>
              <p className="mt-2 text-xs text-gray-400">{result.caption.status} · {result.caption.model || 'no caption model configured'}</p>
              <p className="mt-3 text-sm text-gray-200">{result.caption.text || 'Captioning is unavailable until a compatible local model and weights are configured.'}</p>
              <h3 className="mt-5 text-sm font-semibold text-white">Analysis notes</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-gray-400">{result.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
              {result.artifacts.map((artifact) => <a key={artifact.kind} className="mt-4 inline-flex text-sm text-cyan-300 underline" href={artifact.download_url}>Download annotated derivative</a>)}
            </div>
          </div>}
        </section>
      </div>
    </div>
  )
}

export default ImageAnalysis
