import { useEffect, useMemo, useState, type MouseEvent } from 'react'
import {
  Chip,
  Divider,
  FormControl,
  InputLabel,
  Menu,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography
} from '@mui/material'
import { useNavigate, useParams } from 'react-router-dom'
import {
  fetchApplications,
  fetchJobs,
  fetchWhatIfScenarios,
  runWhatIf
} from '../api/client'
import { useScenario } from '../context/ScenarioContext'
import type { Application, Job, SummaryRow, WhatIfScenario } from '../types'

interface ApplicationRow extends Application {
  scenario_score?: number
}

const formatDate = (value?: string) => {
  if (!value) {
    return 'N/A'
  }
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) {
    return value
  }
  return new Intl.DateTimeFormat('en-GB', {
    year: 'numeric',
    month: 'short',
    day: '2-digit'
  }).format(date)
}

const DashboardPage = () => {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const { appliedScenario, applyScenario, clearScenario } = useScenario()

  const [jobs, setJobs] = useState<Job[]>([])
  const [applications, setApplications] = useState<Application[]>([])
  const [jobsLoading, setJobsLoading] = useState(false)
  const [appsLoading, setAppsLoading] = useState(false)
  const [jobsError, setJobsError] = useState<string | null>(null)
  const [appsError, setAppsError] = useState<string | null>(null)
  const [scenarioError, setScenarioError] = useState<string | null>(null)
  const [scenarioLoading, setScenarioLoading] = useState(false)
  const [scenarioRunning, setScenarioRunning] = useState(false)

  const [selectedJobId, setSelectedJobId] = useState<number | undefined>(
    jobId ? Number(jobId) : undefined
  )

  const [jobSearch, setJobSearch] = useState('')
  const [jobSince, setJobSince] = useState('')

  const [appSince, setAppSince] = useState('')
  const [appMinScore, setAppMinScore] = useState('')
  const [appMinScenarioScore, setAppMinScenarioScore] = useState('')
  const [recommendationFilter, setRecommendationFilter] = useState('all')
  const [whatIfScenarios, setWhatIfScenarios] = useState<WhatIfScenario[]>([])
  const [selectedScenarioId, setSelectedScenarioId] = useState<number | ''>('')

  const [contextMenu, setContextMenu] = useState<{
    mouseX: number
    mouseY: number
    job?: Job
    application?: ApplicationRow
  } | null>(null)

  useEffect(() => {
    let isMounted = true
    const loadJobs = async () => {
      setJobsLoading(true)
      setJobsError(null)
      try {
        const data = await fetchJobs()
        if (isMounted) {
          setJobs(data)
        }
      } catch (err) {
        if (isMounted) {
          setJobsError(err instanceof Error ? err.message : 'Failed to load jobs')
        }
      } finally {
        if (isMounted) {
          setJobsLoading(false)
        }
      }
    }
    loadJobs()
    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    if (jobId) {
      setSelectedJobId(Number(jobId))
    }
  }, [jobId])

  useEffect(() => {
    let isMounted = true
    const loadApplications = async () => {
      if (!selectedJobId) {
        setApplications([])
        return
      }
      setAppsLoading(true)
      setAppsError(null)
      try {
        const data = await fetchApplications({ job_id: selectedJobId })
        if (isMounted) {
          setApplications(data)
        }
      } catch (err) {
        if (isMounted) {
          setAppsError(
            err instanceof Error ? err.message : 'Failed to load applications'
          )
        }
      } finally {
        if (isMounted) {
          setAppsLoading(false)
        }
      }
    }
    loadApplications()
    return () => {
      isMounted = false
    }
  }, [selectedJobId])

  useEffect(() => {
    let isMounted = true
    const loadScenarios = async () => {
      if (!selectedJobId) {
        setWhatIfScenarios([])
        setSelectedScenarioId('')
        setScenarioError(null)
        setScenarioLoading(false)
        setScenarioRunning(false)
        setAppMinScenarioScore('')
        clearScenario()
        return
      }
      setScenarioLoading(true)
      setScenarioError(null)
      try {
        const data = await fetchWhatIfScenarios({ job_id: selectedJobId })
        if (isMounted) {
          setWhatIfScenarios(data)
          setSelectedScenarioId('')
          setAppMinScenarioScore('')
          clearScenario()
        }
      } catch (err) {
        if (isMounted) {
          setScenarioError(
            err instanceof Error ? err.message : 'Failed to load scenarios'
          )
        }
      } finally {
        if (isMounted) {
          setScenarioLoading(false)
        }
      }
    }
    loadScenarios()
    return () => {
      isMounted = false
    }
  }, [selectedJobId, clearScenario])

  const scenarioScores = useMemo(() => {
    if (!appliedScenario || !appliedScenario.summaryTable) {
      return new Map<number, SummaryRow>()
    }
    const map = new Map<number, SummaryRow>()
    appliedScenario.summaryTable.forEach((row) => {
      if (row.id) {
        map.set(row.id, row)
      }
    })
    return map
  }, [appliedScenario])

  const jobMatchForScenario =
    appliedScenario && appliedScenario.jobId === selectedJobId

  const applicationRows = useMemo<ApplicationRow[]>(() => {
    return applications.map((app) => {
      const scenarioRow = scenarioScores.get(app.id)
      return {
        ...app,
        scenario_score: scenarioRow?.scenario_score
      }
    })
  }, [applications, scenarioScores])

  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      const matchesSearch =
        !jobSearch ||
        [job.title, job.company, job.location]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes(jobSearch.toLowerCase())
      const matchesSince = !jobSince || (job.created_at ?? '') >= jobSince
      return matchesSearch && matchesSince
    })
  }, [jobs, jobSearch, jobSince])

  const filteredApplications = useMemo(() => {
    return applicationRows.filter((app) => {
      const matchesSince = !appSince || (app.created_at ?? '') >= appSince
      const minScoreValue = Number(appMinScore)
      const matchesMinScore =
        !appMinScore ||
        (typeof app.overall_score === 'number' &&
          app.overall_score >= minScoreValue)
      const minScenarioValue = Number(appMinScenarioScore)
      const matchesScenarioScore =
        !appMinScenarioScore ||
        (typeof app.scenario_score === 'number' &&
          app.scenario_score >= minScenarioValue)
      const recommendation =
        (app.match_data as { recommendation?: string } | undefined)?.recommendation ??
        'N/A'
      const matchesRecommendation =
        recommendationFilter === 'all' || recommendation === recommendationFilter

      return (
        matchesSince &&
        matchesMinScore &&
        matchesScenarioScore &&
        matchesRecommendation
      )
    })
  }, [
    applicationRows,
    appSince,
    appMinScore,
    appMinScenarioScore,
    recommendationFilter
  ])

  const recommendationOptions = useMemo(() => {
    const set = new Set<string>()
    applications.forEach((app) => {
      const recommendation =
        (app.match_data as { recommendation?: string } | undefined)
          ?.recommendation ?? 'N/A'
      set.add(recommendation)
    })
    return Array.from(set).sort()
  }, [applications])

  const handleJobSelect = (job: Job) => {
    setSelectedJobId(job.id)
  }

  const handleContextMenu = (
    event: MouseEvent,
    payload: { job?: Job; application?: ApplicationRow }
  ) => {
    event.preventDefault()
    setContextMenu({
      mouseX: event.clientX + 2,
      mouseY: event.clientY - 6,
      ...payload
    })
  }

  const handleMenuClose = () => {
    setContextMenu(null)
  }

  const handleScenarioChange = async (rawValue: unknown) => {
    const scenarioId =
      rawValue === '' ? '' : Number.isNaN(Number(rawValue)) ? '' : Number(rawValue)
    setSelectedScenarioId(scenarioId)
    setScenarioError(null)
    if (!scenarioId) {
      setAppMinScenarioScore('')
      clearScenario()
      return
    }
    if (!selectedJobId) {
      setScenarioError('Select a job before running a scenario.')
      return
    }
    const scenario = whatIfScenarios.find((item) => item.id === scenarioId)
    if (!scenario) {
      setScenarioError('Scenario not found for this job.')
      clearScenario()
      return
    }
    setScenarioRunning(true)
    try {
      const data = await runWhatIf({
        job_id: Number(selectedJobId),
        scenario: scenario.scenario_payload,
        summary: true
      })
      applyScenario({
        type: 'what-if',
        jobId: Number(selectedJobId),
        label: scenario.name || `Scenario #${scenario.id}`,
        summaryTable: (data.summary_table ?? []) as SummaryRow[]
      })
    } catch (err) {
      setScenarioError(err instanceof Error ? err.message : 'Scenario failed')
      clearScenario()
    } finally {
      setScenarioRunning(false)
    }
  }

  const selectedJob = jobs.find((job) => job.id === selectedJobId)

  return (
    <Stack spacing={2.5}>
      <Stack spacing={2}>
        <Paper sx={{ p: 3, minHeight: 420 }}>
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="h6">Jobs</Typography>
              <Chip
                size="small"
                label={`${filteredJobs.length} found`}
                variant="outlined"
              />
            </Stack>
            <Stack direction="row" spacing={1.5} flexWrap="wrap">
              <TextField
                label="Search jobs"
                value={jobSearch}
                onChange={(event) => setJobSearch(event.target.value)}
                size="small"
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 200, flexGrow: 1 }}
              />
              <TextField
                label="Created since"
                type="date"
                value={jobSince}
                onChange={(event) => setJobSince(event.target.value)}
                InputLabelProps={{ shrink: true }}
                size="small"
              />
            </Stack>
            {appliedScenario && (
              <Stack direction="row" spacing={1} alignItems="center">
                <Chip
                  color="secondary"
                  label={`${appliedScenario.type.toUpperCase()}: ${appliedScenario.label}`}
                  onDelete={clearScenario}
                />
                <Typography variant="body2" color="text.secondary">
                  Applied to Job #{appliedScenario.jobId}
                </Typography>
              </Stack>
            )}
            <Divider />
            {jobsError && (
              <Typography color="error">{jobsError}</Typography>
            )}
            {jobsLoading ? (
              <Typography color="text.secondary">Loading jobs...</Typography>
            ) : (
              <TableContainer sx={{ maxHeight: 360, overflowX: 'hidden' }}>
                <Table size="small" sx={{ tableLayout: 'fixed' }}>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ width: '40%' }}>Title</TableCell>
                      <TableCell sx={{ width: '25%' }}>Company</TableCell>
                      <TableCell sx={{ width: '20%' }}>Location</TableCell>
                      <TableCell sx={{ width: '15%' }}>Created</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredJobs.map((job) => (
                      <TableRow
                        key={job.id}
                        hover
                        selected={job.id === selectedJobId}
                        onClick={() => handleJobSelect(job)}
                        onContextMenu={(event) =>
                          handleContextMenu(event, { job })
                        }
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                          <Typography variant="body2" fontWeight={600}>
                            {job.title || 'Untitled role'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            #{job.id}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                          {job.company || 'N/A'}
                        </TableCell>
                        <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                          {job.location || 'N/A'}
                        </TableCell>
                        <TableCell>{formatDate(job.created_at)}</TableCell>
                      </TableRow>
                    ))}
                    {!filteredJobs.length && (
                      <TableRow>
                        <TableCell colSpan={4}>
                          <Typography color="text.secondary">
                            No jobs match the filters.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Stack>
        </Paper>

        <Paper sx={{ p: 3, minHeight: 460 }}>
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="h6">Applications</Typography>
              <Chip
                size="small"
                label={`${filteredApplications.length} shown`}
                variant="outlined"
              />
              {selectedJob && (
                <Chip
                  size="small"
                  color="secondary"
                  label={`Job #${selectedJob.id}`}
                />
              )}
            </Stack>
            <Stack direction="row" spacing={1.5} flexWrap="wrap">
              <TextField
                label="Created since"
                type="date"
                value={appSince}
                onChange={(event) => setAppSince(event.target.value)}
                InputLabelProps={{ shrink: true }}
                size="small"
              />
              <TextField
                label="Min Score"
                type="number"
                value={appMinScore}
                onChange={(event) => setAppMinScore(event.target.value)}
                size="small"
                InputLabelProps={{ shrink: true }}
                inputProps={{ min: 0, max: 100 }}
                sx={{ minWidth: 140 }}
              />
              <TextField
                label="Min Scenario"
                type="number"
                value={appMinScenarioScore}
                onChange={(event) => setAppMinScenarioScore(event.target.value)}
                size="small"
                InputLabelProps={{ shrink: true }}
                inputProps={{ min: 0, max: 100 }}
                disabled={!jobMatchForScenario}
                sx={{ minWidth: 160 }}
              />
              <TextField
                select
                label="What-if Scenario"
                value={selectedScenarioId}
                onChange={(event) =>
                  handleScenarioChange(event.target.value)
                }
                size="small"
                InputLabelProps={{ shrink: true }}
                SelectProps={{ displayEmpty: true }}
                disabled={!selectedJobId || scenarioLoading}
                sx={{ minWidth: 220 }}
              >
                <MenuItem value="">None</MenuItem>
                {whatIfScenarios.map((scenario) => (
                  <MenuItem key={scenario.id} value={scenario.id}>
                    {scenario.name || `Scenario #${scenario.id}`}
                  </MenuItem>
                ))}
              </TextField>
              <FormControl size="small" sx={{ minWidth: 160 }}>
                <InputLabel shrink>Recommendation</InputLabel>
                <Select
                  value={recommendationFilter}
                  label="Recommendation"
                  onChange={(event) => setRecommendationFilter(event.target.value)}
                >
                  <MenuItem value="all">All</MenuItem>
                  {recommendationOptions.map((option) => (
                    <MenuItem key={option} value={option}>
                      {option}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
            {scenarioLoading && selectedJob && (
              <Typography color="text.secondary">Loading scenarios...</Typography>
            )}
            {scenarioRunning && (
              <Typography color="text.secondary">Running scenario...</Typography>
            )}
            {scenarioError && <Typography color="error">{scenarioError}</Typography>}
            {appliedScenario && !jobMatchForScenario && (
              <Typography color="text.secondary">
                Applied scenario is for Job #{appliedScenario.jobId}. Select that
                job to see scenario scores.
              </Typography>
            )}
            <Divider />
            {!selectedJob && (
              <Typography color="text.secondary">
                Select a job to load applications.
              </Typography>
            )}
            {appsError && <Typography color="error">{appsError}</Typography>}
            {appsLoading && selectedJob ? (
              <Typography color="text.secondary">Loading applications...</Typography>
            ) : selectedJob ? (
              <TableContainer sx={{ maxHeight: 420, overflowX: 'hidden' }}>
                <Table size="small" sx={{ tableLayout: 'fixed' }}>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ width: '35%' }}>Candidate</TableCell>
                      <TableCell sx={{ width: '15%' }}>Original</TableCell>
                      <TableCell sx={{ width: '15%' }}>Scenario</TableCell>
                      <TableCell sx={{ width: '20%' }}>Recommendation</TableCell>
                      <TableCell sx={{ width: '15%' }}>Created</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredApplications.map((app) => {
                      const recommendation =
                        (app.match_data as { recommendation?: string } | undefined)
                          ?.recommendation ?? 'N/A'
                      return (
                        <TableRow
                          key={app.id}
                          hover
                          onContextMenu={(event) =>
                            handleContextMenu(event, { application: app })
                          }
                          sx={{ cursor: 'context-menu' }}
                        >
                          <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                            <Typography variant="body2" fontWeight={600}>
                              {app.candidate?.name || `Candidate #${app.candidate_id}`}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              App #{app.id}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {typeof app.overall_score === 'number'
                              ? app.overall_score.toFixed(1)
                              : 'N/A'}
                          </TableCell>
                          <TableCell>
                            {typeof app.scenario_score === 'number'
                              ? app.scenario_score.toFixed(1)
                              : '—'}
                          </TableCell>
                          <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                            {recommendation}
                          </TableCell>
                          <TableCell>{formatDate(app.created_at)}</TableCell>
                        </TableRow>
                      )
                    })}
                    {!filteredApplications.length && (
                      <TableRow>
                        <TableCell colSpan={5}>
                          <Typography color="text.secondary">
                            No applications match the filters.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : null}
          </Stack>
        </Paper>
      </Stack>

      <Menu
        open={Boolean(contextMenu)}
        onClose={handleMenuClose}
        anchorReference="anchorPosition"
        anchorPosition={
          contextMenu
            ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
            : undefined
        }
      >
        <MenuItem
          disabled={!contextMenu?.job && !contextMenu?.application?.job_id}
          onClick={() => {
            const jobIdValue =
              contextMenu?.job?.id ?? contextMenu?.application?.job_id
            if (jobIdValue) {
              navigate(`/jobs/${jobIdValue}`)
            }
            handleMenuClose()
          }}
        >
          Show job
        </MenuItem>
        <MenuItem
          disabled={!contextMenu?.application?.candidate_id}
          onClick={() => {
            const candidateIdValue = contextMenu?.application?.candidate_id
            if (candidateIdValue) {
              navigate(`/candidates/${candidateIdValue}`)
            }
            handleMenuClose()
          }}
        >
          Show candidate
        </MenuItem>
        <MenuItem
          disabled={!contextMenu?.application?.candidate_id}
          onClick={() => {
            const candidateIdValue = contextMenu?.application?.candidate_id
            if (candidateIdValue) {
              navigate(`/candidates/${candidateIdValue}/resume`)
            }
            handleMenuClose()
          }}
        >
          Show resume
        </MenuItem>
        <MenuItem
          disabled={!contextMenu?.application?.id}
          onClick={() => {
            const applicationIdValue = contextMenu?.application?.id
            if (applicationIdValue) {
              navigate(`/applications/${applicationIdValue}`)
            }
            handleMenuClose()
          }}
        >
          Show application
        </MenuItem>
        <MenuItem
          disabled={!contextMenu?.application?.id}
          onClick={() => {
            const applicationIdValue = contextMenu?.application?.id
            if (applicationIdValue) {
              navigate(`/applications/${applicationIdValue}/appraisal`)
            }
            handleMenuClose()
          }}
        >
          Show appraisal
        </MenuItem>
      </Menu>
    </Stack>
  )
}

export default DashboardPage
