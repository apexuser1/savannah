export interface Candidate {
  id: number
  name?: string
  email?: string
  phone?: string
  original_filename?: string
  file_type?: string
  created_at?: string
  updated_at?: string
  resume_data?: Record<string, unknown>
}

export interface Job {
  id: number
  title?: string
  company?: string
  location?: string
  original_filename?: string
  file_type?: string
  created_at?: string
  updated_at?: string
  job_data?: Record<string, unknown>
}

export interface Application {
  id: number
  candidate_id: number
  job_id: number
  overall_score?: number
  must_have_skills_score?: number
  nice_to_have_skills_score?: number
  experience_score?: number
  education_score?: number
  match_data?: Record<string, unknown>
  created_at?: string
  candidate?: Candidate
  job?: Job
}

export interface SummaryRow {
  id?: number
  candidate?: string
  job_title?: string
  company?: string
  recommendation?: string
  created?: string
  original_score?: number
  scenario_score?: number
}

export interface WhatIfScenario {
  id: number
  job_id: number
  name?: string
  scenario_payload: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export interface OptimisationRecord {
  id: number
  job_id: number
  name?: string
  optimisation_payload: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export interface WhatIfResult {
  job_id?: number
  normalized_scenario?: Record<string, unknown>
  summary?: Record<string, unknown>
  warnings?: string[]
  summary_table?: SummaryRow[]
}

export interface OptimisationResultEntry {
  candidate_count?: number
  cost?: number
  summary?: Record<string, unknown>
  summary_table?: SummaryRow[]
  candidates?: Record<string, unknown>[]
  changes?: Array<{
    type?: string
    detail?: Record<string, unknown>
    cost?: number
  }>
  shock_report?: Record<string, unknown>
  normalized_scenario?: Record<string, unknown>
}

export interface OptimisationResult {
  job_id?: number
  target?: {
    candidate_count?: number
    mode?: string
  }
  baseline?: {
    candidate_count?: number
    summary?: Record<string, unknown>
  }
  results?: OptimisationResultEntry[]
}

export type AppliedScenarioType = 'what-if' | 'optimisation'

export interface AppliedScenario {
  type: AppliedScenarioType
  jobId: number
  label: string
  summaryTable: SummaryRow[]
}
