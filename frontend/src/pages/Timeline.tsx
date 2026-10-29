import { useCallback, useEffect, useState } from 'react'
import { Clock3, Plus, ShieldCheck } from 'lucide-react'
import { api, errorMessage, type EvidenceItem } from '../services/api'

type TimelineEvent = {
  event_id: string
  evidence_id: string | null
  title: string
  description: string
  category: string
  source_type: string
  verification_status: string
  occurred_at: string | null
  relative_seconds: number | null
  time_basis: string
}

const Timeline = () => {
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [evidence, setEvidence] = useState<EvidenceItem[]>([])
  const [source, setSource] = useState('')
  const [category, setCategory] = useState('')
  const [annotationCategory, setAnnotationCategory] = useState('investigator_note')
  const [error, setError] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [selectedEvidence, setSelectedEvidence] = useState('')
  const [relativeSeconds, setRelativeSeconds] = useState('')
  const [saving, setSaving] = useState(false)

  const loadEvents = useCallback(async () => {
    try {
      const response = await api.get('/timeline', { params: { source_type: source || undefined, category: category || undefined } })
      setEvents(response.data.events)
      setError('')
    } catch (err) { setError(errorMessage(err, 'Could not load timeline events.')) }
  }, [category, source])

  useEffect(() => { void loadEvents() }, [loadEvents])
  useEffect(() => { api.get('/evidence', { params: { per_page: 100 } }).then((response) => setEvidence(response.data.evidence)).catch(() => undefined) }, [])

  const addEvent = async (event: React.FormEvent) => {
    event.preventDefault()
    setSaving(true)
    try {
      await api.post('/timeline/events', {
        title,
        description,
        category: annotationCategory,
        evidence_id: selectedEvidence || undefined,
        relative_seconds: relativeSeconds ? Number(relativeSeconds) : undefined,
        time_basis: relativeSeconds ? 'media_relative' : 'unknown',
      })
      setTitle(''); setDescription(''); setRelativeSeconds('')
      await loadEvents()
    } catch (err) { setError(errorMessage(err, 'Could not save the investigator annotation.')) }
    finally { setSaving(false) }
  }

  const markReviewed = async (item: TimelineEvent) => {
    try {
      await api.patch(`/timeline/events/${item.event_id}`, { verification_status: item.verification_status === 'verified' ? 'unverified' : 'verified' })
      await loadEvents()
    } catch (err) { setError(errorMessage(err, 'Could not update review status.')) }
  }

  return (
    <div className="space-y-6">
      <header><p className="text-sm font-medium uppercase tracking-wider text-cyan-400">Source-linked records</p><h1 className="mt-1 text-2xl font-bold text-white">Forensic Timeline</h1><p className="mt-2 text-sm text-gray-400">Media-relative timestamps are kept separate from clock time. Timeline entries do not infer synchronization between evidence items.</p></header>
      {error && <p role="alert" className="rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold text-white">Recorded events</h2><p className="text-xs text-gray-400">{events.length} entries</p></div><div className="flex gap-2"><select aria-label="Filter by source" value={source} onChange={(event) => setSource(event.target.value)} className="rounded-lg border border-gray-700 bg-navy-900 px-3 py-2 text-sm text-gray-200"><option value="">All sources</option><option value="investigator_annotation">Investigator</option><option value="verbatim_transcription">Transcript</option><option value="extracted_metadata">Extracted metadata</option></select><input aria-label="Filter by category" value={category} onChange={(event) => setCategory(event.target.value)} placeholder="Category" className="w-32 rounded-lg border border-gray-700 bg-navy-900 px-3 py-2 text-sm text-white placeholder:text-gray-500" /></div></div>
          {events.length === 0 ? <p className="mt-6 text-sm text-gray-400">No events match these filters. Add an investigator annotation or process media to create source-linked records.</p> : <ol className="mt-5 space-y-4">{events.map((item) => <li key={item.event_id} className="relative rounded-lg border border-gray-700 bg-navy-900 p-4"><div className="flex flex-wrap items-start justify-between gap-2"><div className="flex items-start gap-3"><Clock3 aria-hidden="true" className="mt-0.5 h-4 w-4 text-cyan-400" /><div><h3 className="font-medium text-white">{item.title}</h3><p className="mt-1 text-sm text-gray-300">{item.description}</p></div></div><button onClick={() => void markReviewed(item)} className="inline-flex items-center gap-1 rounded border border-gray-700 px-2 py-1 text-xs text-gray-300 hover:border-cyan-700"><ShieldCheck className="h-3.5 w-3.5" />{item.verification_status}</button></div><div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 pl-7 text-xs text-gray-500"><span>{item.occurred_at ? new Date(item.occurred_at).toLocaleString() : item.relative_seconds !== null ? `${item.relative_seconds.toFixed(2)}s · ${item.time_basis}` : 'Time unknown'}</span><span>{item.category}</span><span>{item.source_type}</span>{item.evidence_id && <a className="text-cyan-300 hover:underline" href="/evidence">Open evidence vault · {item.evidence_id.slice(0, 8)}</a>}</div></li>)}</ol>}
        </section>
        <form onSubmit={(event) => void addEvent(event)} className="h-fit rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="flex items-center gap-2 font-semibold text-white"><Plus className="h-4 w-4 text-cyan-400" />Investigator annotation</h2><p className="mt-2 text-xs text-gray-400">Saved as unverified until reviewed.</p><label className="mt-4 block text-xs text-gray-300">Title<input required maxLength={255} value={title} onChange={(event) => setTitle(event.target.value)} className="mt-1 w-full rounded border border-gray-700 bg-navy-900 px-3 py-2 text-sm text-white" /></label><label className="mt-3 block text-xs text-gray-300">Description<textarea required maxLength={5000} value={description} onChange={(event) => setDescription(event.target.value)} rows={4} className="mt-1 w-full rounded border border-gray-700 bg-navy-900 px-3 py-2 text-sm text-white" /></label><label className="mt-3 block text-xs text-gray-300">Category<input maxLength={50} value={annotationCategory} onChange={(event) => setAnnotationCategory(event.target.value)} className="mt-1 w-full rounded border border-gray-700 bg-navy-900 px-3 py-2 text-sm text-white" /></label><label className="mt-3 block text-xs text-gray-300">Linked evidence<select value={selectedEvidence} onChange={(event) => setSelectedEvidence(event.target.value)} className="mt-1 w-full rounded border border-gray-700 bg-navy-900 px-3 py-2 text-sm text-white"><option value="">No linked evidence</option>{evidence.map((item) => <option key={item.id} value={item.id}>{item.original_filename}</option>)}</select></label><label className="mt-3 block text-xs text-gray-300">Media-relative timestamp (seconds, optional)<input type="number" min="0" step="0.01" value={relativeSeconds} onChange={(event) => setRelativeSeconds(event.target.value)} className="mt-1 w-full rounded border border-gray-700 bg-navy-900 px-3 py-2 text-sm text-white" /></label><button disabled={saving} className="mt-4 w-full rounded-lg bg-cyan-700 px-3 py-2 text-sm font-medium text-white disabled:opacity-50">{saving ? 'Saving…' : 'Add annotation'}</button></form>
      </div>
    </div>
  )
}

export default Timeline
