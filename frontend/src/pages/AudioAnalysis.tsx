import { useEffect, useState } from 'react'
import { AudioLines, Play, RefreshCw, Search } from 'lucide-react'
import { api, errorMessage, type EvidenceItem, type ProcessingJob } from '../services/api'

type TranscriptSegment = { start_seconds: number; end_seconds: number; text: string; language: string | null; language_probability: number | null }
type TranscriptResponse = { analysis_id: string; status: string; metadata: { language: string | null; language_probability: number | null } | null; segments: TranscriptSegment[] }

const AudioAnalysis = () => {
  const [recordings, setRecordings] = useState<EvidenceItem[]>([])
  const [selected, setSelected] = useState<EvidenceItem | null>(null)
  const [job, setJob] = useState<ProcessingJob | null>(null)
  const [transcript, setTranscript] = useState<TranscriptResponse | null>(null)
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/evidence', { params: { media_type: 'audio', per_page: 100 } })
      .then((response) => setRecordings(response.data.evidence))
      .catch((err: unknown) => setError(errorMessage(err, 'Could not load audio evidence.')))
  }, [])

  useEffect(() => {
    if (!job || ['completed', 'failed', 'cancelled'].includes(job.status)) return
    const timer = window.setInterval(() => {
      api.get<ProcessingJob>(`/jobs/${job.job_id}`).then((response) => {
        setJob(response.data)
        if (['completed', 'failed'].includes(response.data.status) && selected) {
          api.get<TranscriptResponse>(`/analysis/audio/${selected.id}/transcript`).then((result) => setTranscript(result.data)).catch(() => undefined)
        }
      }).catch((err: unknown) => setError(errorMessage(err, 'Could not update transcription status.')))
    }, 1500)
    return () => window.clearInterval(timer)
  }, [job?.job_id, job?.status, selected])

  const chooseRecording = (recording: EvidenceItem) => {
    setSelected(recording)
    setTranscript(null)
    setJob(null)
    setError('')
    api.get(`/analysis/audio/${recording.id}/transcript`).then((response) => setTranscript(response.data)).catch(() => undefined)
    api.get('/jobs', { params: { evidence_id: recording.id, limit: 1 } }).then((response) => {
      const latest = response.data.jobs?.[0] as ProcessingJob | undefined
      if (latest) setJob(latest)
    }).catch(() => undefined)
  }

  const startTranscription = async () => {
    if (!selected) return
    setError('')
    setTranscript(null)
    try {
      const response = await api.post(`/analysis/audio/${selected.id}`)
      setJob({ job_id: response.data.job_id, evidence_id: selected.id, analysis_id: response.data.analysis_id, job_type: 'audio', status: 'queued', progress: 0, message: 'Queued', error: null })
    } catch (err) {
      setError(errorMessage(err, 'Could not start transcription.'))
    }
  }

  const visibleSegments = transcript?.segments.filter((segment) => segment.text.toLowerCase().includes(search.toLowerCase())) || []

  return (
    <div className="space-y-6">
      <header><p className="text-sm font-medium uppercase tracking-wider text-cyan-400">Verbatim transcription</p><h1 className="mt-1 text-2xl font-bold text-white">Audio Analysis</h1><p className="mt-2 text-sm text-gray-400">Transcript words remain the model output; summaries and witness claims are not treated as verified facts.</p></header>
      {error && <p role="alert" className="rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
      <div className="grid gap-5 xl:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="rounded-xl border border-gray-700 bg-navy-800 p-4"><h2 className="font-semibold text-white">Audio evidence</h2><ul className="mt-3 space-y-1">{recordings.map((recording) => <li key={recording.id}><button onClick={() => chooseRecording(recording)} className={`w-full truncate rounded-lg px-3 py-2 text-left text-sm ${selected?.id === recording.id ? 'bg-cyan-900 text-white' : 'text-gray-300 hover:bg-navy-700'}`}>{recording.original_filename}</button></li>)}</ul>{!recordings.length && <p className="mt-3 text-sm text-gray-400">Upload WAV audio or supported codecs shown by capabilities.</p>}</aside>
        <section className="space-y-5">
          <div className="rounded-xl border border-gray-700 bg-navy-800 p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-semibold text-white">Audio source</h2><p className="mt-1 text-xs text-gray-400">Original recording is served read-only.</p></div><button disabled={!selected || Boolean(job && ['queued', 'running'].includes(job.status))} onClick={() => void startTranscription()} className="inline-flex items-center gap-2 rounded-lg bg-cyan-700 px-3 py-2 text-sm text-white disabled:opacity-50"><Play className="h-4 w-4" />Transcribe</button></div>
            {selected ? <audio controls preload="metadata" className="mt-4 w-full" src={`/api/v1/evidence/${selected.id}/preview`}>Audio playback is not supported by this browser.</audio> : <div className="mt-4 flex min-h-32 items-center justify-center rounded-lg bg-black/20 text-sm text-gray-500"><AudioLines className="mr-2 h-5 w-5" />Select an audio recording</div>}
          </div>

          {job && <section aria-live="polite" className="rounded-xl border border-gray-700 bg-navy-800 p-5"><div className="flex items-center gap-3"><RefreshCw className={`h-4 w-4 text-cyan-400 ${['queued', 'running'].includes(job.status) ? 'animate-spin' : ''}`} /><h2 className="font-semibold text-white">Transcription job {job.status}</h2></div><p className="mt-2 text-sm text-gray-300">{job.message}</p><progress className="mt-3 h-2 w-full accent-cyan-500" max={100} value={job.progress} aria-label={`Transcription progress ${job.progress}%`} />{job.error && <p className="mt-2 text-sm text-amber-300">{job.error}</p>}</section>}

          {transcript && <section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold text-white">Transcript</h2><p className="mt-1 text-xs text-gray-400">Status: {transcript.status}{transcript.metadata?.language ? ` · Language: ${transcript.metadata.language}` : ''}</p></div><label className="relative"><Search aria-hidden="true" className="absolute left-3 top-2.5 h-4 w-4 text-gray-500" /><input value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search transcript" placeholder="Search transcript" className="w-56 rounded-lg border border-gray-700 bg-navy-900 py-2 pl-9 pr-3 text-sm text-white placeholder:text-gray-500" /></label></div>
            {transcript.status !== 'completed' && <p className="mt-4 rounded bg-amber-950/40 p-3 text-sm text-amber-200">Transcription is unavailable or incomplete. Configure Faster-Whisper and its local model weights to transcribe this recording.</p>}
            {transcript.status === 'completed' && <><p className="mt-3 text-xs text-amber-300">Model transcription is verbatim output and may contain errors. No speaker identity is inferred.</p><div className="mt-4 divide-y divide-gray-700">{visibleSegments.map((segment, index) => <p key={`${segment.start_seconds}-${index}`} className="py-3 text-sm leading-relaxed text-gray-200"><span className="mr-3 font-mono text-xs text-cyan-300">{segment.start_seconds.toFixed(2)}–{segment.end_seconds.toFixed(2)}s</span>{segment.text}</p>)}</div><button onClick={() => { const text = visibleSegments.map((segment) => `[${segment.start_seconds.toFixed(2)}s] ${segment.text}`).join('\n'); const blob = new Blob([text], { type: 'text/plain;charset=utf-8' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = `transcript-${selected?.id}.txt`; anchor.click(); URL.revokeObjectURL(url) }} className="mt-4 rounded-lg border border-gray-600 px-3 py-2 text-sm text-gray-200 hover:bg-navy-700">Export visible transcript</button></>}
          </section>}
        </section>
      </div>
    </div>
  )
}

export default AudioAnalysis
