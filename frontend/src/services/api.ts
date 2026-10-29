import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000,
})

export type EvidenceItem = {
  id: string
  original_filename: string
  media_type: 'image' | 'audio' | 'video'
  file_size: number
  upload_timestamp: string
  processing_status: string
  file_hash?: string
  analysis_history?: Array<{
    analysis_id: string
    analysis_type: string
    processing_status: string
    creation_timestamp: string
    completion_timestamp: string | null
  }>
}

export type ProcessingJob = {
  job_id: string
  evidence_id: string
  analysis_id: string
  job_type: 'audio' | 'video'
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  message: string | null
  error: string | null
}

export function errorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { error?: string } | undefined
    return data?.error || fallback
  }
  return error instanceof Error ? error.message : fallback
}
