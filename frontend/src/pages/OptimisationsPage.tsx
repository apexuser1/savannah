
import { useEffect, useMemo, useState, type MouseEvent } from 'react'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControlLabel,
  IconButton,
  Menu,
  MenuItem,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  ToggleButton,
  ToggleButtonGroup,
  Typography
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import { useLocation, useNavigate, type Location } from 'react-router-dom'
import {
  fetchApplication,
  fetchJobs,
  fetchOptimisations,
  runOptimisation,
  saveOptimisation
} from '../api/client'
import type { Job, OptimisationRecord, OptimisationResult, SummaryRow } from '../types'

type RelaxationOption = {
  value: string
  label: string
  help: string
}

const RELAXATION_OPTIONS: RelaxationOption[] = [
  {
    value: 'remove_nice_to_have',
    label: 'Remove nice-to-have skills',
    help: 'Drop nice-to-have skills from requirements so candidates are not penalized for missing them.'
  },
  {
    value: 'demote_must_to_nice',
    label: 'Demote must-have to nice-to-have',
    help: 'Move a required skill into the nice-to-have list.'
  },
  {
    value: 'remove_must_have',
    label: 'Remove must-have skills',
    help: 'Remove a required skill entirely so it no longer blocks candidates.'
  },
  {
    value: 'lower_min_years',
    label: 'Lower minimum years',
    help: 'Lower the minimum years of experience required.'
  },
  {
    value: 'disable_education',
    label: 'Disable education requirement',
    help: 'Ignore education requirements when scoring candidates.'
  },
  {
    value: 'allow_partials',
    label: 'Allow partial matches',
    help: 'Switch match mode to partial_ok so partial skill matches count.'
  },
  {
    value: 'increase_partial_weight',
    label: 'Increase partial weight',
    help: 'Increase partial_match_weight so partial matches contribute more to coverage and score.'
  },
  {
    value: 'lower_coverage_min',
    label: 'Lower must-have coverage',
    help: 'Lower the must-have coverage minimum so fewer must-haves are required.'
  },
  {
    value: 'lower_threshold',
    label: 'Lower overall score threshold',
    help: 'Lower the overall score threshold used to pass candidates.'
  },
  {
    value: 'weights_override',
    label: 'Override weights',
    help: 'Apply a custom weight mix for must-have, nice-to-have, experience, and education.'
  }
]

const steps = [
  'Select job',
  'Strategy',
  'Relaxations & limits',
  'Review & run'
]

const formatScore = (value?: number) =>
  typeof value === 'number' ? value.toFixed(1) : 'N/A'

const formatCost = (value?: number) =>
  typeof value === 'number' ? value.toFixed(2) : 'N/A'

const formatDate = (value?: string) => {
  if (!value) return 'N/A'
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

const parseDateValue = (value?: string) => {
  if (!value) {
    return 0
  }
  const time = Date.parse(value)
  return Number.isNaN(time) ? 0 : time
}

const toRecord = (value: unknown) =>
  value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}

const toStringList = (value: unknown) =>
  Array.isArray(value) ? value.filter((item) => typeof item === 'string') : []

const toNumber = (value: unknown, fallback: number) =>
  typeof value === 'number' && !Number.isNaN(value) ? value : fallback

const normalizeRelaxations = (value: unknown) => {
  if (!Array.isArray(value)) {
    return RELAXATION_OPTIONS.map((option) => option.value)
  }
  const allowed = new Set(RELAXATION_OPTIONS.map((option) => option.value))
  const cleaned = toStringList(value).map((item) => item.trim().toLowerCase())
  return cleaned.filter((item) => allowed.has(item))
}

const OptimisationsPage = () => {
  const [jobs, setJobs] = useState<Job[]>([])
  const [optimisations, setOptimisations] = useState<OptimisationRecord[]>([])
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('')
  const [scenarioName, setScenarioName] = useState('')
  const [activeStep, setActiveStep] = useState(0)
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as { backgroundLocation?: Location } | null
  const modalState = { backgroundLocation: state?.backgroundLocation ?? location }

  const [candidateTarget, setCandidateTarget] = useState(10)
  const [topK, setTopK] = useState(5)

  const [strategyName, setStrategyName] = useState<'greedy' | 'beam' | 'monte_carlo'>(
    'greedy'
  )
  const [beamWidth, setBeamWidth] = useState(5)
  const [maxRuns, setMaxRuns] = useState(200)
  const [seed, setSeed] = useState('')

  const [maxTotalChanges, setMaxTotalChanges] = useState(3)
  const [limitSkillChanges, setLimitSkillChanges] = useState(true)
  const [maxSkillChanges, setMaxSkillChanges] = useState(2)
  const [allowedRelaxations, setAllowedRelaxations] = useState<string[]>(
    () => RELAXATION_OPTIONS.map((option) => option.value)
  )
  const [minYearsMin, setMinYearsMin] = useState(0)
  const [minYearsStep, setMinYearsStep] = useState(1)
  const [thresholdMin, setThresholdMin] = useState(40)
  const [thresholdStep, setThresholdStep] = useState(5)

  const [result, setResult] = useState<OptimisationResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [contextMenu, setContextMenu] = useState<{
    mouseX: number
    mouseY: number
    row?: SummaryRow
  } | null>(null)

  useEffect(() => {
    let isMounted = true
    const load = async () => {
      try {
        const [jobData, optimisationData] = await Promise.all([
          fetchJobs(),
          fetchOptimisations()
        ])
        if (isMounted) {
          setJobs(jobData)
          setOptimisations(optimisationData)
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load data')
        }
      }
    }
    load()
    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    if (selectedJobId) {
      setResult(null)
    }
  }, [selectedJobId])

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === Number(selectedJobId)),
    [jobs, selectedJobId]
  )

  const selectedRelaxations = useMemo(
    () =>
      RELAXATION_OPTIONS.filter((option) =>
        allowedRelaxations.includes(option.value)
      ),
    [allowedRelaxations]
  )

  const relaxationLabelMap = useMemo(() => {
    return new Map(RELAXATION_OPTIONS.map((option) => [option.value, option.label]))
  }, [])

  const strategyOptions = useMemo(() => {
    if (strategyName === 'beam') {
      return { beam_width: beamWidth }
    }
    if (strategyName === 'monte_carlo') {
      const options: Record<string, number> = { max_runs: maxRuns }
      const seedValue = Number(seed)
      if (seed !== '' && Number.isFinite(seedValue)) {
        options.seed = seedValue
      }
      return options
    }
    return {}
  }, [strategyName, beamWidth, maxRuns, seed])

  const optimisationPayload = useMemo(() => {
    const constraints: Record<string, unknown> = {
      max_total_changes: maxTotalChanges,
      allowed_relaxations: allowedRelaxations,
      min_years_override: {
        min: minYearsMin,
        step: minYearsStep
      },
      overall_score_threshold: {
        min: thresholdMin,
        step: thresholdStep
      }
    }
    if (limitSkillChanges) {
      constraints.max_skill_changes = maxSkillChanges
    }

    return {
      target: {
        candidate_count: candidateTarget,
        mode: 'at_least'
      },
      strategy: {
        name: strategyName,
        options: strategyOptions
      },
      constraints,
      top_k: topK
    }
  }, [
    candidateTarget,
    strategyName,
    strategyOptions,
    maxTotalChanges,
    allowedRelaxations,
    minYearsMin,
    minYearsStep,
    thresholdMin,
    thresholdStep,
    limitSkillChanges,
    maxSkillChanges,
    topK
  ])

  const candidateTargetValid = Number.isFinite(candidateTarget) && candidateTarget > 0
  const topKValid = Number.isFinite(topK) && topK > 0

  const handleRun = async (
    payloadOptimisation?: Record<string, unknown>,
    jobOverride?: number
  ) => {
    const jobIdValue = jobOverride ?? selectedJobId
    if (!jobIdValue) {
      setError('Select a job before running an optimisation.')
      return
    }
    if (!payloadOptimisation && (!candidateTargetValid || !topKValid)) {
      setError('Target and top-k must be positive numbers.')
      return
    }
    setRunning(true)
    setError(null)
    try {
      const payload = {
        job_id: Number(jobIdValue),
        optimisation: payloadOptimisation ?? optimisationPayload,
        summary: true,
        include_details: false,
        best_only: true
      }
      const data = await runOptimisation(payload)
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Optimisation failed')
    } finally {
      setRunning(false)
    }
  }

  const handleSave = async () => {
    if (!selectedJobId) {
      setError('Select a job before saving.')
      return
    }
    if (!candidateTargetValid || !topKValid) {
      setError('Target and top-k must be positive numbers.')
      return
    }
    try {
      const saved = await saveOptimisation({
        job_id: Number(selectedJobId),
        name: scenarioName || undefined,
        optimisation: optimisationPayload
      })
      setOptimisations((prev) => [saved, ...prev])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save optimisation')
    }
  }

  const handleEditOptimisation = (optimisation: OptimisationRecord) => {
    const payload = toRecord(optimisation.optimisation_payload)
    const targetBlock = toRecord(payload.target)
    const strategyBlock = toRecord(payload.strategy)
    const constraintsBlock = toRecord(payload.constraints)
    const optionsBlock = toRecord(strategyBlock.options)

    setSelectedJobId(optimisation.job_id)
    setScenarioName(optimisation.name || '')
    setActiveStep(0)
    setAdvancedOpen(false)
    setResult(null)
    setError(null)
    setRunning(false)

    setCandidateTarget(toNumber(targetBlock.candidate_count, 10))
    setTopK(toNumber(payload.top_k, 5))

    const strategyNameRaw =
      typeof strategyBlock.name === 'string'
        ? strategyBlock.name.trim().toLowerCase()
        : ''
    if (
      strategyNameRaw === 'greedy' ||
      strategyNameRaw === 'beam' ||
      strategyNameRaw === 'monte_carlo'
    ) {
      setStrategyName(strategyNameRaw)
    } else {
      setStrategyName('greedy')
    }

    setBeamWidth(toNumber(optionsBlock.beam_width, 5))
    setMaxRuns(toNumber(optionsBlock.max_runs, 200))
    if (typeof optionsBlock.seed === 'number' && Number.isFinite(optionsBlock.seed)) {
      setSeed(String(optionsBlock.seed))
    } else {
      setSeed('')
    }

    const maxTotal = toNumber(constraintsBlock.max_total_changes, 3)
    setMaxTotalChanges(maxTotal > 0 ? maxTotal : 3)

    const maxSkill = constraintsBlock.max_skill_changes
    if (typeof maxSkill === 'number' && maxSkill > 0) {
      setLimitSkillChanges(true)
      setMaxSkillChanges(maxSkill)
    } else {
      setLimitSkillChanges(false)
      setMaxSkillChanges(2)
    }

    setAllowedRelaxations(normalizeRelaxations(constraintsBlock.allowed_relaxations))

    const minYearsBlock = toRecord(constraintsBlock.min_years_override)
    setMinYearsMin(toNumber(minYearsBlock.min, 0))
    setMinYearsStep(toNumber(minYearsBlock.step, 1))

    const thresholdBlock = toRecord(constraintsBlock.overall_score_threshold)
    setThresholdMin(toNumber(thresholdBlock.min, 40))
    setThresholdStep(toNumber(thresholdBlock.step, 5))
  }

  const resultRows = result?.results ?? []
  const bestResult = resultRows[0]
  const bestSummaryTable = (bestResult?.summary_table as SummaryRow[] | undefined) ?? []
  const baselineSummary = result?.baseline?.summary as
    | { average_score?: number }
    | undefined

  const handleContextMenu = (event: MouseEvent, row: SummaryRow) => {
    event.preventDefault()
    setContextMenu({
      mouseX: event.clientX + 2,
      mouseY: event.clientY - 6,
      row
    })
  }

  const handleMenuClose = () => {
    setContextMenu(null)
  }

  const handleShowJob = () => {
    if (selectedJobId) {
      navigate(`/jobs/${selectedJobId}`, { state: modalState })
    }
    handleMenuClose()
  }

  const handleShowApplication = (suffix = '') => {
    const applicationId = contextMenu?.row?.id
    if (typeof applicationId === 'number') {
      navigate(`/applications/${applicationId}${suffix}`, { state: modalState })
    }
    handleMenuClose()
  }

  const handleShowCandidate = async (showResume: boolean) => {
    const applicationId = contextMenu?.row?.id
    handleMenuClose()
    if (typeof applicationId !== 'number') {
      return
    }
    try {
      const application = await fetchApplication(applicationId)
      if (application.candidate_id) {
        navigate(
          `/candidates/${application.candidate_id}${
            showResume ? '/resume' : ''
          }`,
          { state: modalState }
        )
      } else {
        setError('Candidate not available for this application.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load candidate')
    }
  }

  const storedRows = useMemo(() => {
    return [...optimisations]
      .sort((a, b) => {
        const dateDiff = parseDateValue(b.created_at) - parseDateValue(a.created_at)
        if (dateDiff !== 0) {
          return dateDiff
        }
        return (b.id ?? 0) - (a.id ?? 0)
      })
      .slice(0, 10)
  }, [optimisations])

  const canContinue =
    activeStep === 0
      ? Boolean(selectedJobId) && candidateTargetValid && topKValid
      : true

  const formatValue = (value: unknown) => {
    if (typeof value === 'number' && Number.isFinite(value)) {
      if (Number.isInteger(value)) {
        return value.toString()
      }
      return value.toFixed(2)
    }
    if (typeof value === 'string') {
      return value
    }
    return 'N/A'
  }

  const buildRelaxationDescription = (change?: {
    type?: string
    detail?: Record<string, unknown>
    cost?: number
  }) => {
    if (!change?.type) {
      return 'Unknown relaxation.'
    }
    const detail = change.detail ?? {}
    const costSuffix =
      typeof change.cost === 'number' ? ` (cost ${formatCost(change.cost)})` : ''

    switch (change.type) {
      case 'remove_nice_to_have':
        return `Removed nice-to-have skill: ${formatValue(detail.skill)}${costSuffix}`
      case 'demote_must_to_nice':
        return `Demoted must-have to nice-to-have: ${formatValue(detail.skill)}${costSuffix}`
      case 'remove_must_have':
        return `Removed must-have skill: ${formatValue(detail.skill)}${costSuffix}`
      case 'lower_min_years':
        return `Lowered minimum years from ${formatValue(detail.from)} to ${formatValue(
          detail.to
        )}${costSuffix}`
      case 'disable_education':
        return `Disabled education requirement${costSuffix}`
      case 'allow_partials':
        return `Allowed partial matches (match_mode set to partial_ok)${costSuffix}`
      case 'increase_partial_weight':
        return `Increased partial match weight from ${formatValue(
          detail.from
        )} to ${formatValue(detail.to)}${costSuffix}`
      case 'lower_coverage_min':
        return `Lowered must-have coverage minimum from ${formatValue(
          detail.from
        )} to ${formatValue(detail.to)}${costSuffix}`
      case 'lower_threshold':
        return `Lowered overall score threshold from ${formatValue(
          detail.from
        )} to ${formatValue(detail.to)}${costSuffix}`
      case 'weights_override': {
        const weights = detail.weights as Record<string, unknown> | undefined
        if (!weights) {
          return `Applied scoring weight override${costSuffix}`
        }
        const summary = [
          `must_have ${formatValue(weights.must_have)}`,
          `nice_to_have ${formatValue(weights.nice_to_have)}`,
          `experience ${formatValue(weights.experience)}`,
          `education ${formatValue(weights.education)}`
        ].join(', ')
        return `Applied scoring weight override: ${summary}${costSuffix}`
      }
      default:
        return `Applied relaxation: ${change.type}${costSuffix}`
    }
  }

  const renderChanges = (
    changes?: Array<{ type?: string; detail?: Record<string, unknown>; cost?: number }>
  ) => {
    if (!changes?.length) {
      return 'None'
    }
    return (
      <Stack direction="row" spacing={1} flexWrap="wrap">
        {changes.map((change, index) => {
          const label =
            relaxationLabelMap.get(change.type ?? '') ?? 'Unknown relaxation'
          const description = buildRelaxationDescription(change)
          return (
            <Tooltip key={`${change.type ?? 'change'}-${index}`} title={description} arrow>
              <Chip
                icon={<InfoOutlinedIcon fontSize="small" />}
                label={label}
                size="small"
              />
            </Tooltip>
          )
        })}
      </Stack>
    )
  }

  return (
    <Stack spacing={2.5}>
      <Paper sx={{ p: 3 }}>
        <Stack spacing={2.5}>
          <Typography variant="h6">Optimisation Builder</Typography>
          <Stepper activeStep={activeStep} alternativeLabel>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          {activeStep === 0 && (
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2}>
                  <Typography variant="subtitle1">Select the target job</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Pick the job and define the target candidate count. These values
                    become the goal for the optimiser.
                  </Typography>
                  <Stack direction="row" spacing={1.5} flexWrap="wrap">
                    <TextField
                      select
                      label="Job"
                      value={selectedJobId}
                      onChange={(event) =>
                        setSelectedJobId(Number(event.target.value))
                      }
                      size="small"
                      InputLabelProps={{ shrink: true }}
                      SelectProps={{ displayEmpty: true }}
                      sx={{ minWidth: 240 }}
                    >
                      <MenuItem value="">Select a job</MenuItem>
                      {jobs.map((job) => (
                        <MenuItem key={job.id} value={job.id}>
                          {job.title || `Job #${job.id}`} ({job.company || 'N/A'})
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      label="Optimisation name"
                      value={scenarioName}
                      onChange={(event) => setScenarioName(event.target.value)}
                      size="small"
                      InputLabelProps={{ shrink: true }}
                      sx={{ minWidth: 240 }}
                    />
                    <TextField
                      label="Target candidates"
                      type="number"
                      value={candidateTarget}
                      onChange={(event) =>
                        setCandidateTarget(Number(event.target.value))
                      }
                      size="small"
                      InputLabelProps={{ shrink: true }}
                      inputProps={{ min: 1 }}
                      sx={{ width: 180 }}
                    />
                    <TextField
                      label="Top results"
                      type="number"
                      value={topK}
                      onChange={(event) => setTopK(Number(event.target.value))}
                      size="small"
                      InputLabelProps={{ shrink: true }}
                      inputProps={{ min: 1 }}
                      sx={{ width: 160 }}
                    />
                  </Stack>
                  {selectedJob && (
                    <Stack spacing={1}>
                      <Typography variant="subtitle2">Job snapshot</Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        <Chip label={selectedJob.title || `Job #${selectedJob.id}`} />
                        <Chip label={selectedJob.company || 'Company N/A'} />
                        <Chip label={selectedJob.location || 'Location N/A'} />
                      </Stack>
                    </Stack>
                  )}
                </Stack>
              </CardContent>
            </Card>
          )}

          {activeStep === 1 && (
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2.5}>
                  <Box>
                    <Typography variant="subtitle1">Choose a strategy</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Select how the optimiser explores relaxations and tune the
                      strategy-specific controls.
                    </Typography>
                    <ToggleButtonGroup
                      value={strategyName}
                      exclusive
                      onChange={(_, value) => value && setStrategyName(value)}
                      size="small"
                      sx={{ mt: 1 }}
                    >
                      <ToggleButton value="greedy">Greedy</ToggleButton>
                      <ToggleButton value="beam">Beam</ToggleButton>
                      <ToggleButton value="monte_carlo">Monte Carlo</ToggleButton>
                    </ToggleButtonGroup>
                  </Box>

                  {strategyName === 'greedy' && (
                    <Box>
                      <Typography variant="subtitle2">Greedy search</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Tries the best single relaxation at each step until the
                        target is reached or changes are exhausted.
                      </Typography>
                    </Box>
                  )}
                  {strategyName === 'beam' && (
                    <Box>
                      <Typography variant="subtitle2">Beam width</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Explore the top N relaxation paths at each step.
                      </Typography>
                      <TextField
                        label="Beam width"
                        type="number"
                        value={beamWidth}
                        onChange={(event) => setBeamWidth(Number(event.target.value))}
                        size="small"
                        InputLabelProps={{ shrink: true }}
                        inputProps={{ min: 1 }}
                        sx={{ width: 160, mt: 1 }}
                      />
                    </Box>
                  )}
                  {strategyName === 'monte_carlo' && (
                    <Box>
                      <Typography variant="subtitle2">Monte Carlo sampling</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Sample random relaxation sequences for broader exploration.
                      </Typography>
                      <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mt: 1 }}>
                        <TextField
                          label="Max runs"
                          type="number"
                          value={maxRuns}
                          onChange={(event) =>
                            setMaxRuns(Number(event.target.value))
                          }
                          size="small"
                          InputLabelProps={{ shrink: true }}
                          inputProps={{ min: 1 }}
                          sx={{ width: 160 }}
                        />
                        <TextField
                          label="Seed (optional)"
                          type="number"
                          value={seed}
                          onChange={(event) => setSeed(event.target.value)}
                          size="small"
                          InputLabelProps={{ shrink: true }}
                          sx={{ width: 160 }}
                        />
                      </Stack>
                    </Box>
                  )}
                </Stack>
              </CardContent>
            </Card>
          )}

          {activeStep === 2 && (
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2.5}>
                  <Box>
                    <Typography variant="subtitle1">Relaxations</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Choose which relaxations are allowed. If you clear the list,
                      the optimiser will default to all options.
                    </Typography>
                    <Autocomplete
                      multiple
                      options={RELAXATION_OPTIONS}
                      value={selectedRelaxations}
                      onChange={(_, value) =>
                        setAllowedRelaxations(value.map((option) => option.value))
                      }
                      isOptionEqualToValue={(option, value) =>
                        option.value === value.value
                      }
                      getOptionLabel={(option) => option.label}
                      renderOption={(props, option) => (
                        <li {...props}>
                          <Stack
                            direction="row"
                            spacing={1}
                            alignItems="flex-start"
                            justifyContent="space-between"
                            sx={{ width: '100%' }}
                          >
                            <Box>
                              <Typography variant="body2">{option.label}</Typography>
                              <Typography variant="caption" color="text.secondary">
                                {option.help}
                              </Typography>
                            </Box>
                            <Tooltip title={option.help} arrow>
                              <IconButton
                                size="small"
                                aria-label={`Info about ${option.label}`}
                                onMouseDown={(event) => event.preventDefault()}
                                onClick={(event) => event.stopPropagation()}
                              >
                                <InfoOutlinedIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Stack>
                        </li>
                      )}
                      renderTags={(value, getTagProps) =>
                        value.map((option, index) => {
                          const { key, ...chipProps } = getTagProps({ index })
                          return (
                            <Tooltip key={key} title={option.help} arrow>
                              <Chip
                                icon={<InfoOutlinedIcon fontSize="small" />}
                                label={option.label}
                                {...chipProps}
                              />
                            </Tooltip>
                          )
                        })
                      }
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Allowed relaxations"
                          helperText="Defaults to all relaxations if left empty."
                          InputLabelProps={{
                            ...params.InputLabelProps,
                            shrink: true
                          }}
                        />
                      )}
                    />
                  </Box>

                  <Box>
                    <Typography variant="subtitle1">Change limits</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Control how many relaxations can be applied.
                    </Typography>
                    <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mt: 1 }}>
                      <TextField
                        label="Max total changes"
                        type="number"
                        value={maxTotalChanges}
                        onChange={(event) =>
                          setMaxTotalChanges(Number(event.target.value))
                        }
                        size="small"
                        InputLabelProps={{ shrink: true }}
                        inputProps={{ min: 1 }}
                        sx={{ width: 180 }}
                      />
                      <FormControlLabel
                        control={
                          <Switch
                            checked={limitSkillChanges}
                            onChange={(event) =>
                              setLimitSkillChanges(event.target.checked)
                            }
                          />
                        }
                        label="Limit skill changes"
                      />
                      {limitSkillChanges && (
                        <TextField
                          label="Max skill changes"
                          type="number"
                          value={maxSkillChanges}
                          onChange={(event) =>
                            setMaxSkillChanges(Number(event.target.value))
                          }
                          size="small"
                          InputLabelProps={{ shrink: true }}
                          inputProps={{ min: 1 }}
                          sx={{ width: 180 }}
                        />
                      )}
                    </Stack>
                  </Box>

                  <Divider />

                  <Box>
                    <Typography variant="subtitle1">Experience range</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Allow the optimiser to lower minimum years within a range.
                    </Typography>
                    <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mt: 1 }}>
                      <TextField
                        label="Min years (min)"
                        type="number"
                        value={minYearsMin}
                        onChange={(event) => setMinYearsMin(Number(event.target.value))}
                        size="small"
                        InputLabelProps={{ shrink: true }}
                        inputProps={{ min: 0 }}
                        sx={{ width: 160 }}
                      />
                      <TextField
                        label="Min years step"
                        type="number"
                        value={minYearsStep}
                        onChange={(event) =>
                          setMinYearsStep(Number(event.target.value))
                        }
                        size="small"
                        InputLabelProps={{ shrink: true }}
                        inputProps={{ min: 0 }}
                        sx={{ width: 160 }}
                      />
                    </Stack>
                  </Box>

                  <Box>
                    <Typography variant="subtitle1">Score threshold range</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Allow the optimiser to lower the pass threshold.
                    </Typography>
                    <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mt: 1 }}>
                      <TextField
                        label="Threshold (min)"
                        type="number"
                        value={thresholdMin}
                        onChange={(event) =>
                          setThresholdMin(Number(event.target.value))
                        }
                        size="small"
                        InputLabelProps={{ shrink: true }}
                        inputProps={{ min: 0, max: 100 }}
                        sx={{ width: 160 }}
                      />
                      <TextField
                        label="Threshold step"
                        type="number"
                        value={thresholdStep}
                        onChange={(event) =>
                          setThresholdStep(Number(event.target.value))
                        }
                        size="small"
                        InputLabelProps={{ shrink: true }}
                        inputProps={{ min: 1 }}
                        sx={{ width: 160 }}
                      />
                    </Stack>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          )}

          {activeStep === 3 && (
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2}>
                  <Typography variant="subtitle1">Optimisation summary</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Review the configuration before saving or running.
                  </Typography>
                  <Stack spacing={1}>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Job</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {selectedJob?.title || 'Select a job'}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Optimisation name</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {scenarioName || 'Untitled'}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Target candidates</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {candidateTarget}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Top results</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {topK}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Strategy</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {strategyName}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Allowed relaxations</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {allowedRelaxations.length || RELAXATION_OPTIONS.length}
                      </Typography>
                    </Stack>
                  </Stack>

                  <Accordion
                    expanded={advancedOpen}
                    onChange={(_, expanded) => setAdvancedOpen(expanded)}
                  >
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="subtitle2">Advanced JSON preview</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Paper
                        variant="outlined"
                        sx={{ p: 2, bgcolor: 'background.default' }}
                      >
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                          {JSON.stringify(optimisationPayload, null, 2)}
                        </pre>
                      </Paper>
                    </AccordionDetails>
                  </Accordion>
                </Stack>
              </CardContent>
            </Card>
          )}

          {error && <Typography color="error">{error}</Typography>}

          <Stack direction="row" spacing={1.5} justifyContent="space-between">
            <Button
              variant="text"
              disabled={activeStep === 0}
              onClick={() => setActiveStep((prev) => prev - 1)}
            >
              Back
            </Button>
            <Stack direction="row" spacing={1.5}>
              {activeStep < steps.length - 1 ? (
                <Button
                  variant="contained"
                  onClick={() => setActiveStep((prev) => prev + 1)}
                  disabled={!canContinue}
                >
                  Next
                </Button>
              ) : (
                <>
                  <Button
                    variant="outlined"
                    onClick={handleSave}
                    disabled={!selectedJobId || !candidateTargetValid || !topKValid}
                  >
                    Save optimisation
                  </Button>
                  <Button
                    variant="contained"
                    onClick={() => handleRun()}
                    disabled={!selectedJobId || running || !candidateTargetValid || !topKValid}
                  >
                    Run optimisation
                  </Button>
                </>
              )}
            </Stack>
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h6">Optimisation Results</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Chip
              label={`Target: ${
                result?.target?.candidate_count ?? candidateTarget ?? 'N/A'
              }`}
            />
            <Chip
              label={`Baseline: ${result?.baseline?.candidate_count ?? 'N/A'}`}
            />
            <Chip label={`Top results: ${resultRows.length}`} />
            <Chip
              label={`Baseline avg: ${formatScore(baselineSummary?.average_score)}`}
            />
          </Stack>
          <Divider />

          <Typography variant="subtitle1">Top results</Typography>
          <TableContainer sx={{ overflowX: 'hidden' }}>
            <Table size="small" sx={{ tableLayout: 'fixed' }}>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ width: '10%' }}>Rank</TableCell>
                  <TableCell sx={{ width: '20%' }}>Candidates</TableCell>
                  <TableCell sx={{ width: '15%' }}>Cost</TableCell>
                  <TableCell sx={{ width: '15%' }}>Avg score</TableCell>
                  <TableCell sx={{ width: '40%' }}>Relaxations</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {resultRows.map((entry, index) => {
                  const summary = entry.summary as { average_score?: number } | undefined
                  return (
                    <TableRow key={`${entry.candidate_count ?? 'row'}-${index}`}>
                      <TableCell>{index + 1}</TableCell>
                      <TableCell>{entry.candidate_count ?? 'N/A'}</TableCell>
                      <TableCell>{formatCost(entry.cost)}</TableCell>
                      <TableCell>{formatScore(summary?.average_score)}</TableCell>
                      <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                        {renderChanges(entry.changes)}
                      </TableCell>
                    </TableRow>
                  )
                })}
                {!resultRows.length && (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography color="text.secondary">
                        Run an optimisation to see candidate totals.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <Divider />
          <Typography variant="subtitle1">Best result summary</Typography>
          <TableContainer sx={{ overflowX: 'hidden' }}>
            <Table size="small" sx={{ tableLayout: 'fixed' }}>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ width: '35%' }}>Candidate</TableCell>
                  <TableCell sx={{ width: '15%' }}>Original</TableCell>
                  <TableCell sx={{ width: '15%' }}>Optimised</TableCell>
                  <TableCell sx={{ width: '20%' }}>Recommendation</TableCell>
                  <TableCell sx={{ width: '15%' }}>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {bestSummaryTable.map((row, index) => (
                  <TableRow
                    key={`${row.id ?? index}`}
                    hover
                    onContextMenu={(event) => handleContextMenu(event, row)}
                    sx={{ cursor: 'context-menu' }}
                  >
                    <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                      <Typography variant="body2" fontWeight={600}>
                        {row.candidate || 'Unknown'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        App #{row.id ?? 'N/A'}
                      </Typography>
                    </TableCell>
                    <TableCell>{formatScore(row.original_score)}</TableCell>
                    <TableCell>{formatScore(row.scenario_score)}</TableCell>
                    <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                      {row.recommendation || 'N/A'}
                    </TableCell>
                    <TableCell>{formatDate(row.created)}</TableCell>
                  </TableRow>
                ))}
                {!bestSummaryTable.length && (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography color="text.secondary">
                        No summary table available yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Stack>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h6">Saved Optimisations</Typography>
          <Divider />
          <TableContainer sx={{ overflowX: 'hidden' }}>
            <Table size="small" sx={{ tableLayout: 'fixed' }}>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ width: '40%' }}>Name</TableCell>
                  <TableCell sx={{ width: '20%' }}>Job</TableCell>
                  <TableCell sx={{ width: '20%' }}>Created</TableCell>
                  <TableCell sx={{ width: '20%' }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {storedRows.map((optimisation) => (
                  <TableRow key={optimisation.id}>
                    <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                      <Typography variant="body2" fontWeight={600}>
                        {optimisation.name || `Optimisation #${optimisation.id}`}
                      </Typography>
                    </TableCell>
                    <TableCell>Job #{optimisation.job_id}</TableCell>
                    <TableCell>{formatDate(optimisation.created_at)}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={1}>
                        <Button
                          size="small"
                          onClick={() =>
                            handleRun(
                              optimisation.optimisation_payload,
                              optimisation.job_id
                            )
                          }
                        >
                          Run
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => handleEditOptimisation(optimisation)}
                        >
                          Edit
                        </Button>
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
                {!storedRows.length && (
                  <TableRow>
                    <TableCell colSpan={4}>
                      <Typography color="text.secondary">
                        No saved optimisations yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Stack>
      </Paper>

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
        <MenuItem disabled={!selectedJobId} onClick={handleShowJob}>
          Show job
        </MenuItem>
        <MenuItem
          disabled={typeof contextMenu?.row?.id !== 'number'}
          onClick={() => handleShowCandidate(false)}
        >
          Show candidate
        </MenuItem>
        <MenuItem
          disabled={typeof contextMenu?.row?.id !== 'number'}
          onClick={() => handleShowCandidate(true)}
        >
          Show resume
        </MenuItem>
        <MenuItem
          disabled={typeof contextMenu?.row?.id !== 'number'}
          onClick={() => handleShowApplication('')}
        >
          Show application
        </MenuItem>
        <MenuItem
          disabled={typeof contextMenu?.row?.id !== 'number'}
          onClick={() => handleShowApplication('/appraisal')}
        >
          Show appraisal
        </MenuItem>
      </Menu>
    </Stack>
  )
}

export default OptimisationsPage
