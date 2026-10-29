import { useEffect, useState } from 'react'
import { Download, FileText, RefreshCw } from 'lucide-react'
import { api, errorMessage, type EvidenceItem } from '../services/api'

type ReportItem = { report_id: string; title: string; status: string; evidence_ids: string[]; created_at: string; download_url: string }

const Reports = () => {
  const [evidence, setEvidence] = useState<EvidenceItem[]>([])
  const [reports, setReports] = useState<ReportItem[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [title, setTitle] = useState('Forensic Evidence Report')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = async () => {
    try {
      const [evidenceResponse, reportsResponse] = await Promise.all([api.get('/evidence', { params: { per_page: 100 } }), api.get('/reports')])
      setEvidence(evidenceResponse.data.evidence)
      setReports(reportsResponse.data.reports)
      setError('')
    } catch (err) { setError(errorMessage(err, 'Could not load report records.')) }
  }

  useEffect(() => { void load() }, [])

  const generate = async (event: React.FormEvent) => {
    event.preventDefault()
    setGenerating(true)
    setError(''); setNotice('')
    try {
      const response = await api.post('/reports', { title, evidence_ids: selectedIds.length ? selectedIds : undefined })
      setNotice(`Report ${response.data.report_id} was generated from stored records.`)
      await load()
    } catch (err) { setError(errorMessage(err, 'Could not generate the PDF report.')) }
    finally { setGenerating(false) }
  }

  return (
    <div className="space-y-6">
      <header><p className="text-sm font-medium uppercase tracking-wider text-cyan-400">Stored-record export</p><h1 className="mt-1 text-2xl font-bold text-white">Forensic Reports</h1><p className="mt-2 text-sm text-gray-400">Reports reflect recorded evidence, analysis methods, transcript segments, and limitations as stored.</p></header>
      {error && <p role="alert" className="rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
      {notice && <p role="status" className="rounded-lg border border-emerald-800 bg-emerald-950/30 p-3 text-sm text-emerald-200">{notice}</p>}
      <form onSubmit={(event) => void generate(event)} className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="font-semibold text-white">Include evidence</h2><p className="mt-1 text-sm text-gray-400">Select no items to include all stored evidence (up to 100 records).</p><div className="mt-4 max-h-80 divide-y divide-gray-700 overflow-y-auto">{evidence.map((item) => <label key={item.id} className="flex items-start gap-3 py-3 text-sm"><input type="checkbox" checked={selectedIds.includes(item.id)} onChange={(event) => setSelectedIds((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} /><span className="min-w-0 flex-1"><span className="block truncate font-medium text-gray-100">{item.original_filename}</span><span className="mt-1 block text-xs text-gray-400">{item.media_type} · {item.processing_status} · {item.id.slice(0, 8)}</span></span></label>)}</div>{!evidence.length && <p className="mt-4 text-sm text-gray-400">Upload evidence before generating a report.</p>}</section>
        <aside className="h-fit rounded-xl border border-gray-700 bg-navy-800 p-5"><FileText className="h-6 w-6 text-cyan-400" /><h2 className="mt-3 font-semibold text-white">Generate PDF</h2><label className="mt-4 block text-xs text-gray-300">Report title<input required maxLength={255} value={title} onChange={(event) => setTitle(event.target.value)} className="mt-1 w-full rounded border border-gray-700 bg-navy-900 px-3 py-2 text-sm text-white" /></label><button disabled={generating || evidence.length === 0} className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-700 px-3 py-2 text-sm font-medium text-white disabled:opacity-50">{generating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}{generating ? 'Generating…' : 'Generate report'}</button><p className="mt-3 text-xs leading-relaxed text-gray-500">Includes hashes, analysis status, available detections and transcript segments, timeline entries, and limitations. Does not create signatures or official certifications.</p></aside>
      </form>
      <section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="font-semibold text-white">Generated reports</h2>{reports.length ? <ul className="mt-3 divide-y divide-gray-700">{reports.map((report) => <li key={report.report_id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="font-medium text-gray-100">{report.title}</p><p className="mt-1 text-xs text-gray-400">{report.status} · {new Date(report.created_at).toLocaleString()} · {report.evidence_ids.length} evidence records</p></div><a href={report.download_url} className="inline-flex items-center gap-2 rounded border border-gray-600 px-3 py-2 text-sm text-cyan-300 hover:bg-navy-700"><Download className="h-4 w-4" />Download PDF</a></li>)}</ul> : <p className="mt-3 text-sm text-gray-400">No reports have been generated.</p>}</section>
    </div>
  )
}

export default Reports
