import { useEffect, useState } from 'react'
import { Activity, Cpu, HardDrive, ShieldAlert } from 'lucide-react'
import { api, errorMessage } from '../services/api'

type Capabilities = {
  status: string
  modules: Record<string, string>
  models: Record<string, string | null>
  supported_formats: Record<string, string[]>
  limits: Record<string, number>
}

const Settings = () => {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { api.get<Capabilities>('/capabilities').then((response) => setCapabilities(response.data)).catch((err: unknown) => setError(errorMessage(err, 'Could not load backend capabilities.'))) }, [])

  return (
    <div className="space-y-6">
      <header><p className="text-sm font-medium uppercase tracking-wider text-cyan-400">Local configuration</p><h1 className="mt-1 text-2xl font-bold text-white">Settings & Capabilities</h1><p className="mt-2 text-sm text-gray-400">Provider and model readiness reported by the connected backend. Secrets and filesystem paths are not returned.</p></header>
      {error && <p role="alert" className="rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
      {!capabilities && !error && <p className="text-sm text-gray-400">Checking backend capabilities…</p>}
      {capabilities && <>
        <div className="grid gap-4 md:grid-cols-3"><article className="rounded-xl border border-gray-700 bg-navy-800 p-5"><Activity className="h-5 w-5 text-cyan-400" /><h2 className="mt-3 text-sm text-gray-400">Backend</h2><p className="mt-1 font-semibold text-white">{capabilities.status}</p></article><article className="rounded-xl border border-gray-700 bg-navy-800 p-5"><HardDrive className="h-5 w-5 text-cyan-400" /><h2 className="mt-3 text-sm text-gray-400">Maximum upload size</h2><p className="mt-1 font-semibold text-white">{capabilities.limits.max_upload_size_mb} MB</p></article><article className="rounded-xl border border-gray-700 bg-navy-800 p-5"><ShieldAlert className="h-5 w-5 text-amber-400" /><h2 className="mt-3 text-sm text-gray-400">Forensic safeguards</h2><p className="mt-1 text-sm text-gray-200">Automated outputs are preliminary; investigator review is required.</p></article></div>
        <div className="grid gap-5 lg:grid-cols-2"><section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="flex items-center gap-2 font-semibold text-white"><Cpu className="h-4 w-4 text-cyan-400" />Analysis modules</h2><dl className="mt-4 divide-y divide-gray-700">{Object.entries(capabilities.modules).map(([name, status]) => <div key={name} className="flex justify-between gap-3 py-3 text-sm"><dt className="text-gray-300">{name.replace(/_/g, ' ')}</dt><dd className={['ready', 'available', 'configured', 'frame_sampling_available', 'metadata_and_detection'].includes(status) ? 'text-emerald-300' : 'text-amber-300'}>{status}</dd></div>)}</dl></section><section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="font-semibold text-white">Models and supported formats</h2><dl className="mt-4 space-y-3 text-sm">{Object.entries(capabilities.models).map(([name, value]) => <div key={name}><dt className="text-xs uppercase text-gray-500">{name}</dt><dd className="mt-1 text-gray-200">{value || 'Not configured'}</dd></div>)}{Object.entries(capabilities.supported_formats).map(([name, value]) => <div key={name}><dt className="text-xs uppercase text-gray-500">{name}</dt><dd className="mt-1 text-gray-200">{value.length ? value.join(', ') : 'No formats enabled'}</dd></div>)}</dl></section></div>
        <section className="rounded-xl border border-gray-700 bg-navy-800 p-5"><h2 className="font-semibold text-white">Optional local AI setup</h2><p className="mt-2 text-sm text-gray-300">Vision and speech models are loaded only from configured local model folders. Ordinary application startup does not download model weights.</p><p className="mt-2 text-sm text-gray-400">Install the optional `backend/requirements-vision.txt` or `backend/requirements-audio.txt` only when you have compatible model weights available. Set `DETECTION_MODEL_PATH`, `CAPTION_MODEL_PATH`, or `WHISPER_MODEL_PATH` in the backend environment. Groq uses backend-only `GROQ_API_KEY` and `GROQ_MODEL` settings.</p></section>
      </>}
    </div>
  )
}

export default Settings
