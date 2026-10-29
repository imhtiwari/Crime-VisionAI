import { useEffect, useMemo, useRef, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Clock3, Play, RefreshCw, Video as VideoIcon } from 'lucide-react'
import { api, errorMessage, type EvidenceItem, type ProcessingJob } from '../services/api'

type AnalysisResponse = {
  analysis_id: string
  processing_status: string
  result_metadata: {
    video?: { duration_seconds: number; fps: number; width: number; height: number; frame_count: number; sampling_interval_seconds: number }
    frames?: Array<{ frame_number: number; relative_seconds: number }>
    object_detection_status?: string
    limitations?: string[]
  } | null
  findings: Array<{ label: string; confidence: number; frame_number: number | null; timestamp: number | null }>
}

const VideoAnalysis = () => {
  const [videos, setVideos] = useState<EvidenceItem[]>([])
  const [selected, setSelected] = useState<EvidenceItem | null>(null)
  const [interval, setIntervalSeconds] = useState(30)
  const [job, setJob] = useState<ProcessingJob | null>(null)
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [error, setError] = useState('')
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    api.get('/evidence', { params: { media_type: 'video', per_page: 100 } })
      .then((response) => setVideos(response.data.evidence))
      .catch((err: unknown) => setError(errorMessage(err, 'Could not load video evidence.')))
  }, [])

  useEffect(() => {
    if (!job || ['completed', 'failed', 'cancelled'].includes(job.status)) return
    const timer = window.setInterval(() => {
      api.get<ProcessingJob>(`/jobs/${job.job_id}`).then(async (response) => {
        setJob(response.data)
        if (response.data.status === 'completed') {
          const analysis = await api.get<AnalysisResponse>(`/analysis/${response.data.analysis_id}`)
          setResult(analysis.data)
        }
      }).catch((err: unknown) => setError(errorMessage(err, 'Could not update video processing status.')))
    }, 1500)
    return () => window.clearInterval(timer)
  }, [job?.job_id, job?.status])

  const chartData = useMemo(() => {
    const counts = new Map<number, number>()
    result?.findings.forEach((finding) => {
      const frame = finding.frame_number ?? -1
      counts.set(frame, (counts.get(frame) || 0) + 1)
    })
    return [...counts.entries()].filter(([frame]) => frame >= 0).map(([frame, count]) => ({ frame: `#${frame}`, detections: count }))
  }, [result])

  const selectVideo = (video: EvidenceItem) => {
    setSelected(video)
    setResult(null)
    setJob(null)
    setError('')
    api.get('/jobs', { params: { evidence_id: video.id, limit: 1 } }).then((response) => {
      const latest = response.data.jobs?.[0] as ProcessingJob | undefined
      if (latest) {
        setJob(latest)
        if (latest.status === 'completed') api.get<AnalysisResponse>(`/analysis/${latest.analysis_id}`).then((analysis) => setResult(analysis.data))
      }
    }).catch(() => undefined)
  }

  const startAnalysis = async () => {
    if (!selected) return
    setError('')
    setResult(null)
    try {
      const response = await api.post('/analysis/video/' + selected.id, { sampling_interval_seconds: interval })
      setJob({ job_id: response.data.job_id, evidence_id: selected.id, analysis_id: response.data.analysis_id, job_type: 'video', status: 'queued', progress: 0, message: 'Queued', error: null })
    } catch (err) {
      setError(errorMessage(err, 'Could not start video processing.'))
    }
  }

  const seekTo = (seconds: number) => {
    if (videoRef.current) { videoRef.current.currentTime = seconds; void videoRef.current.play() }
  }

  return (
    <div className="space-y-6">
      <header><p className="text-sm font-medium uppercase tracking-wider text-cyan-400">Sampled-frame processing</p><h1 className="mt-1 text-2xl font-bold text-white">Video Analysis</h1><p className="mt-2 text-sm text-gray-400">Frame extraction runs as a background job. Action recognition is not enabled.</p></header>
      {error && <p role="alert" className="rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
      <div className="grid gap-5 xl:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="rounded-xl border border-gray-700 bg-navy-800 p-4"><h2 className="font-semibold text-white">Video evidence</h2><ul className="mt-3 space-y-1">{videos.map((video) => <li key={video.id}><button onClick={() => selectVideo(video)} className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm ${selected?.id === video.id ? 'bg-cyan-900 text-white' : 'text-gray-300 hover:bg-navy-700'}`}>{video.original_filename}</button></li>)}</ul>{!videos.length && <p className="mt-3 text-sm text-gray-400">Upload a supported video in the Evidence Vault.</p>}</aside>
        <section className="space-y-5">
          <div className="rounded-xl border border-gray-700 bg-navy-800 p-4">
            <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="font-semibold text-white">Source video</h2><p className="mt-1 text-xs text-gray-400">Original file remains unchanged.</p></div><div className="flex items-end gap-3"><label className="text-xs text-gray-300">Sample every (seconds)<input type="number" min="1" max="600" value={interval} onChange={(event) => setIntervalSeconds(Math.max(1, Math.min(600, Number(event.target.value) || 1)))} className="mt-1 block w-24 rounded border border-gray-700 bg-navy-900 px-2 py-1.5 text-sm text-white" /></label><button disabled={!selected || Boolean(job && ['queued', 'running'].includes(job.status))} onClick={() => void startAnalysis()} className="inline-flex items-center gap-2 rounded-lg bg-cyan-700 px-3 py-2 text-sm text-white disabled:opacity-50"><Play className="h-4 w-4" />Start sampling</button></div></div>
            {selected ? <video ref={videoRef} controls preload="metadata" className="mt-4 max-h-[60vh] w-full rounded-lg bg-black" src={`/api/v1/evidence/${selected.id}/preview`} aria-label={`Video evidence ${selected.original_filename}`} /> : <div className="mt-4 flex min-h-64 items-center justify-center rounded-lg bg-black/30 text-sm text-gray-500"><VideoIcon className="mr-2 h-5 w-5" />Select a video item</div>}
          </div>

          {job && <section aria-live="polite" className="rounded-xl border border-gray-700 bg-navy-800 p-5"><div className="flex items-center gap-3"><RefreshCw className={`h-4 w-4 text-cyan-400 ${['queued', 'running'].includes(job.status) ? 'animate-spin' : ''}`} /><h2 className="font-semibold text-white">Job {job.status}</h2></div><p className="mt-2 text-sm text-gray-300">{job.message}</p><progress className="mt-3 h-2 w-full accent-cyan-500" max={100} value={job.progress} aria-label={`Video job progress ${job.progress}%`} /><p className="mt-1 text-right text-xs text-gray-400">{job.progress}%</p>{job.error && <p className="mt-2 text-sm text-red-300">{job.error}</p>}</section>}

          {result?.result_metadata?.video && <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="font-semibold text-white">Sampled frames</h2><p className="mt-1 text-xs text-gray-400">{result.result_metadata.video.width} × {result.result_metadata.video.height} · {result.result_metadata.video.fps.toFixed(2)} fps · {result.result_metadata.video.duration_seconds.toFixed(2)} seconds</p><p className="mt-1 text-xs text-amber-300">Object detector: {result.result_metadata.object_detection_status}. Samples are not verified actions or events.</p><ul className="mt-4 max-h-72 divide-y divide-gray-700 overflow-y-auto">{result.result_metadata.frames?.map((frame) => <li key={frame.frame_number} className="flex items-center justify-between py-2 text-sm"><span className="flex items-center gap-2 text-gray-300"><Clock3 className="h-4 w-4 text-cyan-400" />Frame {frame.frame_number}</span><button onClick={() => seekTo(frame.relative_seconds)} className="text-cyan-300 hover:underline">{frame.relative_seconds.toFixed(2)}s · jump</button></li>)}</ul></section>
            <section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="font-semibold text-white">Detection frequency by sampled frame</h2>{chartData.length ? <div className="mt-4 h-56"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData}><CartesianGrid strokeDasharray="3 3" stroke="#334155" /><XAxis dataKey="frame" stroke="#94a3b8" /><YAxis allowDecimals={false} stroke="#94a3b8" /><Tooltip /><Bar dataKey="detections" fill="#06b6d4" /></BarChart></ResponsiveContainer></div> : <p className="mt-4 text-sm text-gray-400">No detections are available for this analysis. A sampled-frame analysis does not identify actions.</p>}{result.result_metadata.limitations?.map((item) => <p key={item} className="mt-3 text-xs text-gray-500">{item}</p>)}</section>
          </div>}
        </section>
      </div>
    </div>
  )
}

export default VideoAnalysis
