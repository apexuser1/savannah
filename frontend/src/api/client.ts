import type {
  Application,
  Candidate,
  Job,
  OptimisationRecord,
  OptimisationResult,
  SummaryRow,
  WhatIfResult,
  WhatIfScenario
} from '../types'

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL?.toString()
const API_BASE_URL = rawBaseUrl ? rawBaseUrl.replace(/\/$/, '') : ''

class ApiError extends Error {
  status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.status = status
  }
}

const buildQuery = (params: Record<string, string | number | undefined>) => {
  const entries = Object.entries(params).filter(([, value]) => value !== undefined && value !== '')
  if (!entries.length) {
    return ''
  }
  const query = new URLSearchParams()
  entries.forEach(([key, value]) => query.append(key, String(value)))
  return `?${query.toString()}`
}

const requestJson = async <T>(
  path: string,
  options?: RequestInit
): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {})
    },
    ...options
  })

  if (!response.ok) {
    const message = await response.text()
    throw new ApiError(message || 'Request failed', response.status)
  }

  return (await response.json()) as T
}

export const fetchJobs = (params: { since?: string } = {}) =>
  requestJson<Job[]>(`/api/jobs${buildQuery(params)}`)

export const fetchJob = (jobId: number) =>
  requestJson<Job>(`/api/jobs/${jobId}`)

export const fetchCandidates = (params: { since?: string } = {}) =>
  requestJson<Candidate[]>(`/api/candidates${buildQuery(params)}`)

export const fetchCandidate = (candidateId: number) =>
  requestJson<Candidate>(`/api/candidates/${candidateId}`)

export const fetchApplications = (params: {
  since?: string
  min_score?: number
  job_id?: number
} = {}) => requestJson<Application[]>(`/api/applications${buildQuery(params)}`)

export const fetchApplication = (applicationId: number) =>
  requestJson<Application>(`/api/applications/${applicationId}`)

export const fetchWhatIfScenarios = (params: { job_id?: number } = {}) =>
  requestJson<WhatIfScenario[]>(`/api/what-if/scenarios${buildQuery(params)}`)

export const saveWhatIfScenario = (payload: {
  job_id: number
  name?: string
  scenario: Record<string, unknown>
}) =>
  requestJson<WhatIfScenario>('/api/what-if/scenarios', {
    method: 'POST',
    body: JSON.stringify(payload)
  })

export const runWhatIf = (payload: {
  job_id: number
  scenario_text?: string
  scenario?: Record<string, unknown>
  match_mode?: string
  partial_match_weight?: number
  overall_score_threshold?: number
  include_details?: boolean
  summary?: boolean
}) =>
  requestJson<WhatIfResult>('/api/what-if', {
    method: 'POST',
    body: JSON.stringify(payload)
  })

export const fetchOptimisations = (params: { job_id?: number } = {}) =>
  requestJson<OptimisationRecord[]>(`/api/optimisations${buildQuery(params)}`)

export const saveOptimisation = (payload: {
  job_id: number
  name?: string
  optimisation: Record<string, unknown>
}) =>
  requestJson<OptimisationRecord>('/api/optimisations', {
    method: 'POST',
    body: JSON.stringify(payload)
  })

export const runOptimisation = (payload: {
  job_id: number
  optimisation: Record<string, unknown>
  candidate_count?: number
  top_k?: number
  include_details?: boolean
  summary?: boolean
  best_only?: boolean
}) =>
  requestJson<OptimisationResult>('/api/optimisation', {
    method: 'POST',
    body: JSON.stringify(payload)
  })

export type { ApiError, SummaryRow }
