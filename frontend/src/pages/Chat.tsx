import { useEffect, useRef, useState } from 'react'
import { Bot, Plus, Send, UserRound } from 'lucide-react'
import { api, errorMessage, type EvidenceItem } from '../services/api'

type StructuredAnswer = { observations: string[]; interpretations: string[]; hypotheses: string[]; uncertainties: string[]; citations: Array<{ evidence_id: string; analysis_id: string | null; reference: string }> }
type ChatMessage = { message_id: string; role: 'user' | 'assistant'; content: string; structured: StructuredAnswer | null; created_at: string }
type Conversation = { conversation_id: string; title: string; message_count: number }

const Chat = () => {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [conversationId, setConversationId] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [evidence, setEvidence] = useState<EvidenceItem[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [question, setQuestion] = useState('')
  const [providerStatus, setProviderStatus] = useState('checking')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const messageEnd = useRef<HTMLDivElement>(null)

  const loadConversations = async () => {
    const response = await api.get('/chat/conversations')
    const list: Conversation[] = response.data.conversations
    setConversations(list)
    if (list.length && !conversationId) setConversationId(list[0].conversation_id)
    else if (!list.length) {
      const created = await api.post('/chat/conversations', { title: 'Investigation chat' })
      setConversationId(created.data.conversation_id)
      setConversations([{ ...created.data, message_count: 0 }])
    }
  }

  useEffect(() => {
    void loadConversations().catch((err: unknown) => setError(errorMessage(err, 'Could not load conversations.')))
    api.get('/evidence', { params: { per_page: 100 } }).then((response) => setEvidence(response.data.evidence)).catch(() => undefined)
    api.get('/capabilities').then((response) => setProviderStatus(response.data.modules?.llm_reasoning || 'unknown')).catch(() => setProviderStatus('backend_unavailable'))
  }, [])

  useEffect(() => {
    if (!conversationId) return
    api.get(`/chat/conversations/${conversationId}`).then((response) => setMessages(response.data.messages)).catch((err: unknown) => setError(errorMessage(err, 'Could not load this conversation.')))
  }, [conversationId])

  useEffect(() => { messageEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const createConversation = async () => {
    try {
      const response = await api.post('/chat/conversations', { title: 'Investigation chat' })
      const item = { ...response.data, message_count: 0 }
      setConversations((current) => [item, ...current])
      setConversationId(item.conversation_id)
      setMessages([])
      setError('')
    } catch (err) { setError(errorMessage(err, 'Could not start a conversation.')) }
  }

  const sendQuestion = async (event?: React.FormEvent) => {
    event?.preventDefault()
    if (!question.trim() || !conversationId || sending) return
    const submitted = question.trim()
    setQuestion('')
    setSending(true)
    setError('')
    try {
      await api.post(`/chat/conversations/${conversationId}/messages`, { message: submitted, evidence_ids: selectedIds.length ? selectedIds : undefined })
    } catch (err) {
      setError(errorMessage(err, 'The investigation assistant could not answer.'))
    } finally {
      try {
        const history = await api.get(`/chat/conversations/${conversationId}`)
        setMessages(history.data.messages)
      } catch { /* Keep the existing message list if refresh is unavailable. */ }
      setSending(false)
    }
  }

  const prompts = ['Summarize the available analysis records.', 'What information is missing from this evidence?', 'Which findings remain uncertain or unverified?']
  const providerUnavailable = providerStatus !== 'available' && providerStatus !== 'configured'

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm font-medium uppercase tracking-wider text-cyan-400">Evidence-grounded assistance</p><h1 className="mt-1 text-2xl font-bold text-white">Investigation Assistant</h1><p className="mt-2 text-sm text-gray-400">Provider status: <span className="text-gray-200">{providerStatus}</span></p></div><button onClick={() => void createConversation()} className="inline-flex items-center gap-2 rounded-lg border border-gray-600 px-3 py-2 text-sm text-gray-200 hover:bg-navy-700"><Plus className="h-4 w-4" />New conversation</button></header>
      {providerUnavailable && <p className="rounded-lg border border-amber-800 bg-amber-950/30 p-3 text-sm text-amber-200">Groq reasoning is unavailable until GROQ_API_KEY and GROQ_MODEL are configured in the backend environment.</p>}
      {error && <p role="alert" className="rounded-lg border border-amber-800 bg-amber-950/30 p-3 text-sm text-amber-200">{error}</p>}
      <div className="grid gap-5 xl:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className="rounded-xl border border-gray-700 bg-navy-800 p-4"><h2 className="text-sm font-semibold text-white">Conversation history</h2><ul className="mt-3 space-y-1">{conversations.map((item) => <li key={item.conversation_id}><button onClick={() => setConversationId(item.conversation_id)} className={`w-full rounded-lg px-3 py-2 text-left text-sm ${conversationId === item.conversation_id ? 'bg-cyan-900 text-white' : 'text-gray-300 hover:bg-navy-700'}`}>{item.title}<span className="mt-1 block text-xs text-gray-500">{item.message_count} messages</span></button></li>)}</ul><h3 className="mt-6 text-xs font-semibold uppercase tracking-wide text-gray-400">Evidence context</h3><p className="mt-1 text-xs text-gray-500">Select records or leave empty to use up to 20 recent items.</p><div className="mt-2 max-h-48 space-y-1 overflow-y-auto">{evidence.map((item) => <label key={item.id} className="flex items-start gap-2 rounded p-1.5 text-xs text-gray-300 hover:bg-navy-700"><input type="checkbox" checked={selectedIds.includes(item.id)} onChange={(event) => setSelectedIds((current) => event.target.checked ? [...current, item.id] : current.filter((id) => id !== item.id))} /><span className="truncate">{item.original_filename}</span></label>)}</div></aside>
        <section className="flex min-h-[70vh] flex-col rounded-xl border border-gray-700 bg-navy-800">
          <div className="flex-1 space-y-4 overflow-y-auto p-5">{messages.length === 0 ? <div className="mx-auto max-w-xl py-10 text-center"><Bot className="mx-auto h-9 w-9 text-cyan-400" /><h2 className="mt-3 text-lg font-semibold text-white">Ask about the records available here</h2><p className="mt-2 text-sm text-gray-400">Answers are generated only when a backend provider is configured and cite stored evidence records.</p><div className="mt-5 flex flex-wrap justify-center gap-2">{prompts.map((prompt) => <button key={prompt} onClick={() => setQuestion(prompt)} className="rounded-full border border-gray-700 px-3 py-2 text-xs text-gray-300 hover:border-cyan-600">{prompt}</button>)}</div></div> : messages.map((message) => <article key={message.message_id} className={`rounded-xl p-4 ${message.role === 'user' ? 'ml-8 bg-navy-900' : 'mr-8 border border-gray-700 bg-[#121f31]'}`}><div className="flex items-center gap-2 text-xs font-medium text-gray-400">{message.role === 'user' ? <UserRound className="h-4 w-4" /> : <Bot className="h-4 w-4 text-cyan-400" />}{message.role === 'user' ? 'Investigator question' : 'AI response'}<time className="ml-auto">{new Date(message.created_at).toLocaleString()}</time></div><p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-gray-100">{message.content}</p>{message.structured && <div className="mt-4 grid gap-3 md:grid-cols-2">{(['observations', 'interpretations', 'hypotheses', 'uncertainties'] as const).map((field) => message.structured?.[field].length ? <div key={field} className="rounded-lg bg-black/20 p-3"><h3 className="text-xs font-semibold uppercase text-cyan-200">{field}</h3><ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-gray-300">{message.structured[field].map((entry, index) => <li key={`${field}-${index}`}>{entry}</li>)}</ul></div> : null)}{message.structured.citations.length > 0 && <div className="md:col-span-2"><h3 className="text-xs font-semibold uppercase text-gray-400">Validated source references</h3><ul className="mt-2 space-y-1">{message.structured.citations.map((citation, index) => <li key={`${citation.evidence_id}-${index}`} className="text-xs text-cyan-300">Evidence {citation.evidence_id.slice(0, 8)}{citation.analysis_id ? ` · analysis ${citation.analysis_id.slice(0, 8)}` : ''} · {citation.reference}</li>)}</ul></div>}</div>}</article>)}<div ref={messageEnd} /></div>
          <form onSubmit={(event) => void sendQuestion(event)} className="border-t border-gray-700 p-4"><div className="flex items-end gap-3"><textarea rows={2} maxLength={8000} value={question} onChange={(event) => setQuestion(event.target.value)} disabled={providerUnavailable} placeholder={providerUnavailable ? 'Configure the Groq backend to enable questions…' : 'Ask about selected evidence and stored analysis…'} className="min-h-12 flex-1 resize-y rounded-lg border border-gray-700 bg-navy-900 p-3 text-sm text-white placeholder:text-gray-500 disabled:opacity-60" /><button disabled={!question.trim() || sending || providerUnavailable} className="inline-flex items-center gap-2 rounded-lg bg-cyan-700 px-4 py-3 text-sm font-medium text-white disabled:opacity-50"><Send className="h-4 w-4" />{sending ? 'Sending…' : 'Send'}</button></div><p className="mt-2 text-xs text-gray-500">Provider calls send selected evidence metadata and stored findings to Groq. Embedded evidence text is treated as untrusted input.</p></form>
        </section>
      </div>
    </div>
  )
}

export default Chat
