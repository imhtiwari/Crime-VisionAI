import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, AudioLines, FileText, Image as ImageIcon, Video, FolderOpen } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, errorMessage, type ProcessingJob } from '../services/api'

type DashboardResponse = {
  statistics: { total_evidence: number; evidence_by_type: Record<string, number>; images_analyzed: number; videos_processed: number; audio_transcribed: number; reports_generated: number; pending_jobs: number }
  recent_evidence: Array<{ id: string; original_filename: string; media_type: string; processing_status: string; upload_timestamp: string }>
  recent_analyses: Array<{ analysis_id: string; evidence_id: string; analysis_type: string; processing_status: string; creation_timestamp: string; completion_timestamp: string | null }>
  recent_jobs: ProcessingJob[]
  timeline_activity: Array<{ date: string; events: number }>
}

const Dashboard = () => {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<DashboardResponse>('/dashboard').then((response) => setData(response.data)).catch((err: unknown) => setError(errorMessage(err, 'Could not load dashboard records.')))
  }, [])

  const stats = data?.statistics
  const cards = [
    { label: 'Evidence items', value: stats?.total_evidence, icon: FolderOpen },
    { label: 'Images analyzed', value: stats?.images_analyzed, icon: ImageIcon },
    { label: 'Videos processed', value: stats?.videos_processed, icon: Video },
    { label: 'Audio transcribed', value: stats?.audio_transcribed, icon: AudioLines },
    { label: 'Reports generated', value: stats?.reports_generated, icon: FileText },
    { label: 'Active jobs', value: stats?.pending_jobs, icon: Activity },
  ]

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm font-medium uppercase tracking-wider text-cyan-400">Investigation workspace</p><h1 className="mt-1 text-2xl font-bold text-white">Overview</h1><p className="mt-2 text-sm text-gray-400">Activity and totals calculated from stored evidence, analysis, job, and report records.</p></div><Link to="/evidence" className="rounded-lg bg-cyan-700 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-600">Upload evidence</Link></header>
      {error && <p role="alert" className="rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
      <section aria-label="Investigation statistics" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{cards.map(({ label, value, icon: Icon }) => <article key={label} className="rounded-xl border border-gray-700 bg-navy-800 p-5"><div className="flex items-center gap-3 text-cyan-400"><Icon aria-hidden="true" className="h-5 w-5" /><h2 className="text-sm font-medium text-gray-300">{label}</h2></div><p className="mt-4 text-3xl font-semibold text-white">{value ?? (data ? 0 : '—')}</p></article>)}</section>

      <div className="grid gap-5 xl:grid-cols-2"><section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="font-semibold text-white">Evidence by media type</h2>{data && !stats?.total_evidence ? <p className="mt-5 text-sm text-gray-400">No evidence records are stored yet.</p> : <div className="mt-4 h-52"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data ? Object.entries(stats?.evidence_by_type || {}).map(([media_type, count]) => ({ media_type, count })) : []}><CartesianGrid strokeDasharray="3 3" stroke="#334155" /><XAxis dataKey="media_type" stroke="#94a3b8" /><YAxis allowDecimals={false} stroke="#94a3b8" /><Tooltip /><Area type="monotone" dataKey="count" stroke="#22d3ee" fill="#0891b2" fillOpacity={0.2} /></AreaChart></ResponsiveContainer></div>}</section>
        <section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="font-semibold text-white">Recorded timeline activity</h2><p className="mt-1 text-xs text-gray-400">Entries created per day, based on this application’s record timestamps.</p>{data && !data.timeline_activity.some((day) => day.events) ? <p className="mt-5 text-sm text-gray-400">No activity has been recorded yet.</p> : <div className="mt-4 h-52"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data?.timeline_activity || []}><CartesianGrid strokeDasharray="3 3" stroke="#334155" /><XAxis dataKey="date" tickFormatter={(value: string) => value.slice(5)} stroke="#94a3b8" /><YAxis allowDecimals={false} stroke="#94a3b8" /><Tooltip /><Area type="monotone" dataKey="events" stroke="#38bdf8" fill="#0284c7" fillOpacity={0.2} /></AreaChart></ResponsiveContainer></div>}</section></div>

      <div className="grid gap-5 xl:grid-cols-2"><section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><div className="flex items-center justify-between"><h2 className="font-semibold text-white">Recent evidence</h2><Link to="/evidence" className="text-xs text-cyan-300 hover:underline">Open vault</Link></div>{data?.recent_evidence.length ? <ul className="mt-3 divide-y divide-gray-700">{data.recent_evidence.map((item) => <li key={item.id} className="flex items-center justify-between gap-3 py-3"><div className="min-w-0"><p className="truncate text-sm text-gray-100">{item.original_filename}</p><p className="mt-1 text-xs text-gray-500">{item.media_type} · {new Date(item.upload_timestamp).toLocaleString()}</p></div><span className="shrink-0 rounded-full bg-gray-700 px-2 py-1 text-xs text-gray-300">{item.processing_status}</span></li>)}</ul> : <p className="mt-4 text-sm text-gray-400">{data ? 'No evidence items yet.' : 'Loading evidence…'}</p>}</section>
        <section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="font-semibold text-white">Recent analysis activity</h2>{data?.recent_analyses.length ? <ul className="mt-3 divide-y divide-gray-700">{data.recent_analyses.map((item) => <li key={item.analysis_id} className="flex items-center justify-between gap-3 py-3"><div><p className="text-sm text-gray-100">{item.analysis_type.replace(/_/g, ' ')}</p><p className="mt-1 text-xs text-gray-500">{new Date(item.creation_timestamp).toLocaleString()} · evidence {item.evidence_id.slice(0, 8)}</p></div><span className="text-xs text-gray-300">{item.processing_status}</span></li>)}</ul> : <p className="mt-4 text-sm text-gray-400">{data ? 'No analysis activity yet.' : 'Loading analysis records…'}</p>}</section></div>
      <section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><div className="flex items-center justify-between"><h2 className="font-semibold text-white">Processing jobs</h2><span className="text-xs text-gray-500">{data?.recent_jobs.length ?? 0} recent</span></div>{data?.recent_jobs.length ? <ul className="mt-3 divide-y divide-gray-700">{data.recent_jobs.map((job) => <li key={job.job_id} className="flex flex-wrap items-center justify-between gap-2 py-3"><div><p className="text-sm text-gray-100">{job.job_type.replace(/_/g, ' ')}</p><p className="mt-1 text-xs text-gray-500">{job.message || job.status} · {job.progress}%</p></div><span className="rounded-full bg-gray-700 px-2 py-1 text-xs text-gray-300">{job.status}</span></li>)}</ul> : <p className="mt-4 text-sm text-gray-400">{data ? 'No processing jobs yet.' : 'Loading jobs…'}</p>}</section>
      <p className="text-xs text-gray-500">Automated outputs are preliminary and require human review. They do not establish identity, intent, or guilt.</p>
    </div>
  )
}

export default Dashboard
