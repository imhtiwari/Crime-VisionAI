import { useCallback, useEffect, useState } from 'react'
import { FileAudio, FileImage, FileVideo, Search, Upload } from 'lucide-react'
import { api, errorMessage, type EvidenceItem } from '../services/api'

type EvidenceResponse = { evidence: EvidenceItem[]; total: number; pages: number; current_page: number }

const formatBytes = (size: number) => {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

const EvidenceVault = () => {
  const [items, setItems] = useState<EvidenceItem[]>([])
  const [selected, setSelected] = useState<EvidenceItem | null>(null)
  const [search, setSearch] = useState('')
  const [mediaType, setMediaType] = useState('')
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [supportedFormats, setSupportedFormats] = useState<string[]>([])

  const loadItems = useCallback(async () => {
    setLoading(true)
    try {
      const response = await api.get<EvidenceResponse>('/evidence', {
        params: { page, per_page: 20, search: search || undefined, media_type: mediaType || undefined },
      })
      setItems(response.data.evidence)
      setTotal(response.data.total)
      setPages(Math.max(1, response.data.pages))
      setError('')
    } catch (err) {
      setError(errorMessage(err, 'Could not load evidence from the backend.'))
    } finally {
      setLoading(false)
    }
  }, [mediaType, page, search])

  useEffect(() => { void loadItems() }, [loadItems])
  useEffect(() => {
    api.get('/capabilities').then((response) => {
      const formats = response.data.supported_formats || {}
      setSupportedFormats([...(formats.images ?? []), ...(formats.audio ?? []), ...(formats.videos ?? [])])
    }).catch(() => setSupportedFormats(['jpg', 'jpeg', 'png', 'bmp', 'webp']))
  }, [])
  const extensions = supportedFormats.map((extension) => `.${extension}`).join(',')

  const inspectEvidence = async (item: EvidenceItem) => {
    try {
      const response = await api.get<EvidenceItem>(`/evidence/${item.id}`)
      setSelected(response.data)
      setError('')
    } catch (err) {
      setError(errorMessage(err, 'Could not load evidence details.'))
    }
  }

  const uploadFiles = async (files: FileList | File[]) => {
    const selectedFiles = Array.from(files)
    if (!selectedFiles.length) return
    setUploading(true)
    setError('')
    setNotice('')
    const successes: string[] = []
    const failures: string[] = []
    for (const file of selectedFiles) {
      const form = new FormData()
      form.append('file', file)
      try {
        const response = await api.post('/evidence/upload', form)
        successes.push(response.data.original_filename)
      } catch (err) {
        failures.push(`${file.name}: ${errorMessage(err, 'Upload failed.')}`)
      }
    }
    if (successes.length) setNotice(`Uploaded ${successes.length} evidence file${successes.length === 1 ? '' : 's'}.`)
    if (failures.length) setError(failures.join(' '))
    setUploading(false)
    setPage(1)
    await loadItems()
    if (selected && successes.includes(selected.original_filename)) {
      const matching = items.find((item) => item.original_filename === selected.original_filename)
      if (matching) await inspectEvidence(matching)
    }
  }

  const handleUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) void uploadFiles(event.target.files)
    event.target.value = ''
  }

  const fileIcon = (type: EvidenceItem['media_type']) => {
    const Icon = type === 'image' ? FileImage : type === 'audio' ? FileAudio : FileVideo
    return <Icon aria-hidden="true" className="h-5 w-5 text-cyan-400" />
  }

  return (
    <div className="space-y-6">
      <header>
        <p className="text-sm font-medium uppercase tracking-wider text-cyan-400">Evidence management</p>
        <h1 className="mt-1 text-2xl font-bold text-white">Evidence Vault</h1>
        <p className="mt-2 text-sm text-gray-400">Original image, audio, and video files are stored unchanged and indexed by SHA-256.</p>
      </header>

      {error && <p role="alert" className="rounded-lg border border-red-700 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
      {notice && <p role="status" className="rounded-lg border border-emerald-800 bg-emerald-950/30 p-3 text-sm text-emerald-200">{notice}</p>}

      <label
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center transition-colors ${dragging ? 'border-cyan-400 bg-cyan-950/30' : 'border-gray-600 bg-navy-800 hover:border-cyan-600'}`}
        onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); void uploadFiles(event.dataTransfer.files) }}
      >
        <Upload aria-hidden="true" className="h-7 w-7 text-cyan-400" />
        <span className="mt-3 font-medium text-white">{uploading ? 'Uploading evidence…' : 'Drop files here or browse'}</span>
        <span className="mt-1 text-xs text-gray-400">Accepted formats: {supportedFormats.join(', ') || 'loading backend capabilities…'}</span>
        <input className="sr-only" type="file" multiple accept={extensions || undefined} disabled={uploading || !supportedFormats.length} onChange={handleUpload} />
      </label>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 rounded-xl border border-gray-700 bg-navy-800">
          <div className="flex flex-col gap-3 border-b border-gray-700 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div><h2 className="font-semibold text-white">Evidence items</h2><p className="text-xs text-gray-400">{total} record{total === 1 ? '' : 's'}</p></div>
            <div className="flex flex-wrap gap-2">
              <label className="relative">
                <Search aria-hidden="true" className="absolute left-3 top-2.5 h-4 w-4 text-gray-500" />
                <input aria-label="Search evidence filenames" value={search} onChange={(event) => { setPage(1); setSearch(event.target.value) }} placeholder="Search files" className="w-48 rounded-lg border border-gray-700 bg-navy-900 py-2 pl-9 pr-3 text-sm text-white placeholder:text-gray-500" />
              </label>
              <select aria-label="Filter evidence by media type" value={mediaType} onChange={(event) => { setPage(1); setMediaType(event.target.value) }} className="rounded-lg border border-gray-700 bg-navy-900 px-3 py-2 text-sm text-gray-200">
                <option value="">All media</option><option value="image">Images</option><option value="video">Videos</option><option value="audio">Audio</option>
              </select>
            </div>
          </div>
          {loading ? <p className="p-6 text-sm text-gray-400">Loading evidence…</p> : items.length === 0 ? <p className="p-6 text-sm text-gray-400">No matching evidence records.</p> : (
            <ul className="divide-y divide-gray-700">
              {items.map((item) => (
                <li key={item.id}>
                  <button type="button" onClick={() => void inspectEvidence(item)} className={`flex w-full items-center gap-3 p-4 text-left hover:bg-navy-700 ${selected?.id === item.id ? 'bg-navy-700' : ''}`}>
                    {fileIcon(item.media_type)}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-white">{item.original_filename}</span>
                      <span className="mt-1 block text-xs text-gray-400">{item.media_type} · {formatBytes(item.file_size)} · {new Date(item.upload_timestamp).toLocaleString()}</span>
                    </span>
                    <span className="shrink-0 rounded-full bg-gray-700 px-2.5 py-1 text-xs text-gray-200">{item.processing_status}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="flex items-center justify-between border-t border-gray-700 p-3 text-sm text-gray-300">
            <span>Page {page} of {pages}</span>
            <div className="flex gap-2"><button disabled={page <= 1} onClick={() => setPage(page - 1)} className="rounded border border-gray-700 px-3 py-1 disabled:opacity-40">Previous</button><button disabled={page >= pages} onClick={() => setPage(page + 1)} className="rounded border border-gray-700 px-3 py-1 disabled:opacity-40">Next</button></div>
          </div>
        </div>

        <aside aria-label="Selected evidence details" className="rounded-xl border border-gray-700 bg-navy-800 p-5">
          {!selected ? <p className="text-sm text-gray-400">Select an evidence item to inspect its recorded metadata and analysis history.</p> : <>
            <h2 className="break-words text-lg font-semibold text-white">{selected.original_filename}</h2>
            <dl className="mt-4 space-y-3 text-sm">
              <div><dt className="text-xs uppercase text-gray-500">Evidence ID</dt><dd className="mt-1 break-all font-mono text-gray-200">{selected.id}</dd></div>
              <div><dt className="text-xs uppercase text-gray-500">SHA-256</dt><dd className="mt-1 break-all font-mono text-gray-200">{selected.file_hash}</dd></div>
              <div><dt className="text-xs uppercase text-gray-500">Uploaded</dt><dd className="mt-1 text-gray-200">{new Date(selected.upload_timestamp).toLocaleString()}</dd></div>
              <div><dt className="text-xs uppercase text-gray-500">Processing</dt><dd className="mt-1 text-gray-200">{selected.processing_status}</dd></div>
            </dl>
            <a className="mt-5 inline-flex rounded-lg border border-cyan-700 px-3 py-2 text-sm text-cyan-300 hover:bg-cyan-950/40" href={`/api/v1/evidence/${selected.id}/download`}>Download original</a>
            <h3 className="mt-6 font-medium text-white">Analysis history</h3>
            {selected.analysis_history?.length ? <ul className="mt-2 space-y-2">{selected.analysis_history.map((analysis) => <li key={analysis.analysis_id} className="rounded-lg bg-navy-900 p-3 text-xs text-gray-300"><p>{analysis.analysis_type} · {analysis.processing_status}</p><p className="mt-1 text-gray-500">{new Date(analysis.creation_timestamp).toLocaleString()}</p></li>)}</ul> : <p className="mt-2 text-sm text-gray-400">No analysis runs recorded.</p>}
          </>}
        </aside>
      </section>
    </div>
  )
}

export default EvidenceVault
