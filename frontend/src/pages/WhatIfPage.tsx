import { useEffect, useMemo, useRef, useState, type MouseEvent } from 'react'
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
  Menu,
  MenuItem,
  Paper,
  Radio,
  RadioGroup,
  Slider,
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
  ToggleButton,
  ToggleButtonGroup,
  Typography
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { useLocation, useNavigate, type Location } from 'react-router-dom'
import {
  fetchApplication,
  fetchJob,
  fetchJobs,
  fetchWhatIfScenarios,
  runWhatIf,
  saveWhatIfScenario
} from '../api/client'
import type { Job, SummaryRow, WhatIfResult, WhatIfScenario } from '../types'

const formatScore = (value?: number) =>
  typeof value === 'number' ? value.toFixed(1) : 'N/A'

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

const DEFAULT_WEIGHTS = {
  must_have: 45,
  nice_to_have: 20,
  experience: 20,
  education: 15
}

const toRecord = (value: unknown) =>
  value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}

const toStringList = (value: unknown) =>
  Array.isArray(value) ? value.filter((item) => typeof item === 'string') : []

const toNumber = (value: unknown, fallback: number) =>
  typeof value === 'number' && !Number.isNaN(value) ? value : fallback

const steps = [
  'Select job',
  'Skills adjustments',
  'Experience & education',
  'Matching & scoring',
  'Review & run'
]

const WhatIfPage = () => {
  const [jobs, setJobs] = useState<Job[]>([])
  const [scenarios, setScenarios] = useState<WhatIfScenario[]>([])
  const [jobDetail, setJobDetail] = useState<Job | null>(null)
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('')
  const [scenarioName, setScenarioName] = useState('')
  const [activeStep, setActiveStep] = useState(0)
  const skipResetRef = useRef(false)
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as { backgroundLocation?: Location } | null
  const modalState = { backgroundLocation: state?.backgroundLocation ?? location }

  const [skillsAddMust, setSkillsAddMust] = useState<string[]>([])
  const [skillsAddNice, setSkillsAddNice] = useState<string[]>([])
  const [skillsRemoveMust, setSkillsRemoveMust] = useState<string[]>([])
  const [skillsRemoveNice, setSkillsRemoveNice] = useState<string[]>([])

  const [useJobMinYears, setUseJobMinYears] = useState(true)
  const [minYearsOverride, setMinYearsOverride] = useState(0)
  const [educationOverride, setEducationOverride] = useState<
    'default' | 'required' | 'not_required'
  >('default')

  const [matchMode, setMatchMode] = useState<'full_only' | 'partial_ok'>(
    'partial_ok'
  )
  const [partialWeight, setPartialWeight] = useState(0.5)
  const [mustHaveGate, setMustHaveGate] = useState<'coverage_min' | 'all'>(
    'coverage_min'
  )
  const [coverageMin, setCoverageMin] = useState(1.0)
  const [includeNice, setIncludeNice] = useState(true)
  const [threshold, setThreshold] = useState(50)
  const [customWeights, setCustomWeights] = useState(false)
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS)

  const [result, setResult] = useState<WhatIfResult | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
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
        const [jobData, scenarioData] = await Promise.all([
          fetchJobs(),
          fetchWhatIfScenarios()
        ])
        if (isMounted) {
          setJobs(jobData)
          setScenarios(scenarioData)
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
    let isMounted = true
    const loadJob = async () => {
      if (!selectedJobId) {
        setJobDetail(null)
        return
      }
      try {
        const job = await fetchJob(Number(selectedJobId))
        if (isMounted) {
          setJobDetail(job)
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load job detail')
        }
      }
    }
    loadJob()
    return () => {
      isMounted = false
    }
  }, [selectedJobId])

  useEffect(() => {
    if (!selectedJobId) {
      return
    }
    if (skipResetRef.current) {
      skipResetRef.current = false
      return
    }
    setSkillsAddMust([])
    setSkillsAddNice([])
    setSkillsRemoveMust([])
    setSkillsRemoveNice([])
    setUseJobMinYears(true)
    setMinYearsOverride(jobMinYears)
    setEducationOverride('default')
  }, [selectedJobId])

  const requirements = useMemo(() => {
    const jobData = jobDetail?.job_data as { requirements?: Record<string, unknown> } | undefined
    return jobData?.requirements ?? {}
  }, [jobDetail])

  const mustHaveSkills = useMemo(() => {
    const raw = requirements?.must_have_skills
    return Array.isArray(raw) ? raw.filter((item) => typeof item === 'string') : []
  }, [requirements])

  const niceToHaveSkills = useMemo(() => {
    const raw = requirements?.nice_to_have_skills
    return Array.isArray(raw) ? raw.filter((item) => typeof item === 'string') : []
  }, [requirements])

  const skillOptions = useMemo(() => {
    const combined = [...mustHaveSkills, ...niceToHaveSkills]
    return Array.from(new Set(combined)).sort()
  }, [mustHaveSkills, niceToHaveSkills])

  const jobMinYears = useMemo(() => {
    const value = requirements?.minimum_years_experience
    return typeof value === 'number' ? value : 0
  }, [requirements])

  useEffect(() => {
    if (!selectedJobId || !useJobMinYears) {
      return
    }
    setMinYearsOverride(jobMinYears)
  }, [selectedJobId, jobMinYears, useJobMinYears])

  const educationRequirement = useMemo(() => {
    const requiredEducation = requirements?.required_education as
      | { required?: boolean; level?: string; field?: string }
      | undefined
    return {
      required: Boolean(requiredEducation?.required),
      level: requiredEducation?.level,
      field: requiredEducation?.field
    }
  }, [requirements])

  const weightsSum =
    weights.must_have + weights.nice_to_have + weights.experience + weights.education
  const weightsValid = !customWeights || Math.abs(weightsSum - 100) < 0.01

  const scenarioPayload = useMemo(() => {
    return {
      scenario: {
        min_years_override: useJobMinYears ? null : minYearsOverride,
        education_required_override:
          educationOverride === 'default'
            ? null
            : educationOverride === 'required',
        skills_add: {
          must_have: skillsAddMust,
          nice_to_have: skillsAddNice
        },
        skills_remove: {
          must_have: skillsRemoveMust,
          nice_to_have: skillsRemoveNice
        }
      },
      evaluation: {
        match_mode: matchMode,
        partial_match_weight: matchMode === 'partial_ok' ? partialWeight : null,
        must_have_gate_mode: mustHaveGate,
        must_have_coverage_min: mustHaveGate === 'coverage_min' ? coverageMin : null,
        include_nice_to_have: includeNice,
        weights_override: customWeights ? weights : null
      },
      optimization: {
        objective: 'maximize_candidate_count',
        overall_score_threshold: threshold
      }
    }
  }, [
    useJobMinYears,
    minYearsOverride,
    educationOverride,
    skillsAddMust,
    skillsAddNice,
    skillsRemoveMust,
    skillsRemoveNice,
    matchMode,
    partialWeight,
    mustHaveGate,
    coverageMin,
    includeNice,
    customWeights,
    weights,
    threshold
  ])

  const summaryTable = result?.summary_table ?? []
  const selectedJob = jobs.find((job) => job.id === Number(selectedJobId))

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

  const handleRun = async (
    payloadScenario?: Record<string, unknown>,
    jobOverride?: number
  ) => {
    const jobIdValue = jobOverride ?? selectedJobId
    if (!jobIdValue) {
      setError('Select a job before running a scenario.')
      return
    }
    setRunning(true)
    setError(null)
    try {
      const payload = {
        job_id: Number(jobIdValue),
        summary: true,
        scenario: payloadScenario ?? scenarioPayload
      }
      const data = await runWhatIf(payload)
      setResult(data)
      setWarnings(data.warnings ?? [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scenario failed')
    } finally {
      setRunning(false)
    }
  }

  const handleSave = async () => {
    if (!selectedJobId) {
      setError('Select a job before saving.')
      return
    }
    try {
      const payloadScenario =
        (result?.normalized_scenario as Record<string, unknown> | undefined) ??
        scenarioPayload
      const saved = await saveWhatIfScenario({
        job_id: Number(selectedJobId),
        name: scenarioName || undefined,
        scenario: payloadScenario
      })
      setScenarios((prev) => [saved, ...prev])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save scenario')
    }
  }

  const handleEditScenario = (scenario: WhatIfScenario) => {
    const payload = toRecord(scenario.scenario_payload)
    const scenarioBlock = toRecord(payload.scenario)
    const evaluationBlock = toRecord(payload.evaluation)
    const optimizationBlock = toRecord(payload.optimization)

    skipResetRef.current = scenario.job_id !== selectedJobId
    setSelectedJobId(scenario.job_id)
    setScenarioName(scenario.name || '')
    setActiveStep(0)
    setAdvancedOpen(false)
    setResult(null)
    setWarnings([])
    setError(null)

    const minYearsOverrideRaw = scenarioBlock.min_years_override
    const hasMinYearsOverride = typeof minYearsOverrideRaw === 'number'
    setUseJobMinYears(!hasMinYearsOverride)
    setMinYearsOverride(hasMinYearsOverride ? minYearsOverrideRaw : 0)

    const educationOverrideRaw = scenarioBlock.education_required_override
    if (educationOverrideRaw === true) {
      setEducationOverride('required')
    } else if (educationOverrideRaw === false) {
      setEducationOverride('not_required')
    } else {
      setEducationOverride('default')
    }

    const skillsAddBlock = toRecord(scenarioBlock.skills_add)
    const skillsRemoveBlock = toRecord(scenarioBlock.skills_remove)
    setSkillsAddMust(toStringList(skillsAddBlock.must_have))
    setSkillsAddNice(toStringList(skillsAddBlock.nice_to_have))
    setSkillsRemoveMust(toStringList(skillsRemoveBlock.must_have))
    setSkillsRemoveNice(toStringList(skillsRemoveBlock.nice_to_have))

    const matchModeRaw = evaluationBlock.match_mode
    const matchModeValue =
      matchModeRaw === 'full_only'
        ? 'full_only'
        : matchModeRaw === 'partial_ok'
        ? 'partial_ok'
        : matchModeRaw === 'full'
        ? 'full_only'
        : matchModeRaw === 'partial'
        ? 'partial_ok'
        : 'partial_ok'
    setMatchMode(matchModeValue)
    setPartialWeight(toNumber(evaluationBlock.partial_match_weight, 0.5))

    const gateModeRaw = evaluationBlock.must_have_gate_mode
    setMustHaveGate(gateModeRaw === 'all' ? 'all' : 'coverage_min')
    setCoverageMin(toNumber(evaluationBlock.must_have_coverage_min, 1.0))
    setIncludeNice(
      typeof evaluationBlock.include_nice_to_have === 'boolean'
        ? evaluationBlock.include_nice_to_have
        : true
    )

    const weightsOverride = toRecord(evaluationBlock.weights_override)
    const hasWeightsOverride =
      typeof weightsOverride.must_have === 'number' &&
      typeof weightsOverride.nice_to_have === 'number' &&
      typeof weightsOverride.experience === 'number' &&
      typeof weightsOverride.education === 'number'
    if (hasWeightsOverride) {
      setCustomWeights(true)
      setWeights({
        must_have: weightsOverride.must_have as number,
        nice_to_have: weightsOverride.nice_to_have as number,
        experience: weightsOverride.experience as number,
        education: weightsOverride.education as number
      })
    } else {
      setCustomWeights(false)
      setWeights(DEFAULT_WEIGHTS)
    }

    setThreshold(toNumber(optimizationBlock.overall_score_threshold, 50))
  }

  const storedRows = useMemo(() => {
    return [...scenarios]
      .sort((a, b) => {
        const dateDiff = parseDateValue(b.created_at) - parseDateValue(a.created_at)
        if (dateDiff !== 0) {
          return dateDiff
        }
        return (b.id ?? 0) - (a.id ?? 0)
      })
      .slice(0, 10)
  }, [scenarios])

  const canContinue =
    activeStep === 0 ? Boolean(selectedJobId) : activeStep === 3 ? weightsValid : true

  return (
    <Stack spacing={2.5}>
      <Paper sx={{ p: 3 }}>
        <Stack spacing={2.5}>
          <Typography variant="h6">What-if Scenario Builder</Typography>
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
                    Pick a job to unlock its requirements. The builder only allows
                    skills already present in the job definition.
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
                      label="Scenario name"
                      value={scenarioName}
                      onChange={(event) => setScenarioName(event.target.value)}
                      size="small"
                      InputLabelProps={{ shrink: true }}
                      sx={{ minWidth: 240 }}
                    />
                  </Stack>
                  {selectedJob && (
                    <Stack spacing={1}>
                      <Typography variant="subtitle2">Baseline snapshot</Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        <Chip label={`Must-have: ${mustHaveSkills.length}`} />
                        <Chip label={`Nice-to-have: ${niceToHaveSkills.length}`} />
                        <Chip label={`Min years: ${jobMinYears}`} />
                        <Chip
                          label={`Education required: ${
                            educationRequirement.required ? 'Yes' : 'No'
                          }`}
                        />
                        {educationRequirement.level && (
                          <Chip label={`Level: ${educationRequirement.level}`} />
                        )}
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
                <Stack spacing={2}>
                  <Typography variant="subtitle1">Edit skills</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Choose skills to add or remove. Only skills in the job's
                    requirement lists are available.
                  </Typography>
                  <Stack spacing={2}>
                    <Autocomplete
                      multiple
                      options={skillOptions}
                      value={skillsAddMust}
                      onChange={(_, value) => setSkillsAddMust(value)}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Add must-have skills"
                          helperText="Use to promote or reinforce must-haves."
                          InputLabelProps={{
                            ...params.InputLabelProps,
                            shrink: true
                          }}
                        />
                      )}
                      filterSelectedOptions
                    />
                    <Autocomplete
                      multiple
                      options={skillOptions}
                      value={skillsAddNice}
                      onChange={(_, value) => setSkillsAddNice(value)}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Add nice-to-have skills"
                          helperText="Use to soften requirements or add desirables."
                          InputLabelProps={{
                            ...params.InputLabelProps,
                            shrink: true
                          }}
                        />
                      )}
                      filterSelectedOptions
                    />
                    <Autocomplete
                      multiple
                      options={mustHaveSkills}
                      value={skillsRemoveMust}
                      onChange={(_, value) => setSkillsRemoveMust(value)}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Remove must-have skills"
                          helperText="Use to relax strict requirements."
                          InputLabelProps={{
                            ...params.InputLabelProps,
                            shrink: true
                          }}
                        />
                      )}
                      filterSelectedOptions
                    />
                    <Autocomplete
                      multiple
                      options={niceToHaveSkills}
                      value={skillsRemoveNice}
                      onChange={(_, value) => setSkillsRemoveNice(value)}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Remove nice-to-have skills"
                          helperText="Use to reduce bonus skills."
                          InputLabelProps={{
                            ...params.InputLabelProps,
                            shrink: true
                          }}
                        />
                      )}
                      filterSelectedOptions
                    />
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          )}
          {activeStep === 2 && (
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2.5}>
                  <Box>
                    <Typography variant="subtitle1">Experience</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Override minimum years or keep the job baseline.
                    </Typography>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={useJobMinYears}
                          onChange={(event) =>
                            setUseJobMinYears(event.target.checked)
                          }
                        />
                      }
                      label="Use job default"
                    />
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Slider
                        value={minYearsOverride}
                        onChange={(_, value) =>
                          setMinYearsOverride(value as number)
                        }
                        min={0}
                        max={40}
                        step={1}
                        valueLabelDisplay="auto"
                        disabled={useJobMinYears}
                        sx={{ flexGrow: 1 }}
                      />
                      <TextField
                        label="Min years"
                        type="number"
                        size="small"
                        value={minYearsOverride}
                        onChange={(event) =>
                          setMinYearsOverride(Number(event.target.value))
                        }
                        disabled={useJobMinYears}
                        InputLabelProps={{ shrink: true }}
                        sx={{ width: 120 }}
                      />
                    </Stack>
                  </Box>

                  <Box>
                    <Typography variant="subtitle1">Education requirement</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Keep the job requirement, force a requirement, or disable it.
                    </Typography>
                    <ToggleButtonGroup
                      value={educationOverride}
                      exclusive
                      onChange={(_, value) =>
                        value && setEducationOverride(value)
                      }
                      size="small"
                    >
                      <ToggleButton value="default">Use job default</ToggleButton>
                      <ToggleButton value="required">Require</ToggleButton>
                      <ToggleButton value="not_required">Not required</ToggleButton>
                    </ToggleButtonGroup>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          )}

          {activeStep === 3 && (
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2.5}>
                  <Box>
                    <Typography variant="subtitle1">Match mode</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Full-only enforces strict matches; partials allow softer matches.
                    </Typography>
                    <ToggleButtonGroup
                      value={matchMode}
                      exclusive
                      onChange={(_, value) => value && setMatchMode(value)}
                      size="small"
                    >
                      <ToggleButton value="full_only">Full only</ToggleButton>
                      <ToggleButton value="partial_ok">Allow partials</ToggleButton>
                    </ToggleButtonGroup>
                    <Stack direction="row" spacing={2} alignItems="center" sx={{ mt: 1 }}>
                      <Typography variant="body2" sx={{ minWidth: 140 }}>
                        Partial weight
                      </Typography>
                      <Slider
                        value={partialWeight}
                        onChange={(_, value) => setPartialWeight(value as number)}
                        min={0}
                        max={1}
                        step={0.1}
                        valueLabelDisplay="auto"
                        disabled={matchMode === 'full_only'}
                        sx={{ flexGrow: 1 }}
                      />
                    </Stack>
                  </Box>

                  <Box>
                    <Typography variant="subtitle1">Must-have gate</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Require every must-have, or enforce coverage minimum.
                    </Typography>
                    <RadioGroup
                      value={mustHaveGate}
                      onChange={(event) =>
                        setMustHaveGate(event.target.value as 'coverage_min' | 'all')
                      }
                      row
                    >
                      <FormControlLabel
                        value="coverage_min"
                        control={<Radio />}
                        label="Coverage minimum"
                      />
                      <FormControlLabel
                        value="all"
                        control={<Radio />}
                        label="All must-haves"
                      />
                    </RadioGroup>
                    <Stack direction="row" spacing={2} alignItems="center" sx={{ mt: 1 }}>
                      <Typography variant="body2" sx={{ minWidth: 140 }}>
                        Coverage min
                      </Typography>
                      <Slider
                        value={coverageMin}
                        onChange={(_, value) => setCoverageMin(value as number)}
                        min={0}
                        max={1}
                        step={0.1}
                        valueLabelDisplay="auto"
                        disabled={mustHaveGate === 'all'}
                        sx={{ flexGrow: 1 }}
                      />
                    </Stack>
                  </Box>

                  <Box>
                    <Typography variant="subtitle1">Scoring controls</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Decide whether nice-to-haves contribute to the final score.
                    </Typography>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={includeNice}
                          onChange={(event) =>
                            setIncludeNice(event.target.checked)
                          }
                        />
                      }
                      label="Include nice-to-have skills"
                    />
                  </Box>

                  <Box>
                    <Typography variant="subtitle1">Score threshold</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Minimum overall score to count as a pass.
                    </Typography>
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Slider
                        value={threshold}
                        onChange={(_, value) => setThreshold(value as number)}
                        min={0}
                        max={100}
                        step={5}
                        valueLabelDisplay="auto"
                        sx={{ flexGrow: 1 }}
                      />
                      <TextField
                        label="Threshold"
                        type="number"
                        size="small"
                        value={threshold}
                        onChange={(event) =>
                          setThreshold(Number(event.target.value))
                        }
                        InputLabelProps={{ shrink: true }}
                        sx={{ width: 120 }}
                      />
                    </Stack>
                  </Box>

                  <Box>
                    <Typography variant="subtitle1">Advanced weights</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Override scoring weights when you need custom emphasis.
                    </Typography>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={customWeights}
                          onChange={(event) =>
                            setCustomWeights(event.target.checked)
                          }
                        />
                      }
                      label="Use custom weights"
                    />
                    {customWeights && (
                      <Stack direction="row" spacing={2} flexWrap="wrap">
                        <TextField
                          label="Must-have"
                          type="number"
                          size="small"
                          value={weights.must_have}
                          onChange={(event) =>
                            setWeights((prev) => ({
                              ...prev,
                              must_have: Number(event.target.value)
                            }))
                          }
                          InputLabelProps={{ shrink: true }}
                        />
                        <TextField
                          label="Nice-to-have"
                          type="number"
                          size="small"
                          value={weights.nice_to_have}
                          onChange={(event) =>
                            setWeights((prev) => ({
                              ...prev,
                              nice_to_have: Number(event.target.value)
                            }))
                          }
                          InputLabelProps={{ shrink: true }}
                        />
                        <TextField
                          label="Experience"
                          type="number"
                          size="small"
                          value={weights.experience}
                          onChange={(event) =>
                            setWeights((prev) => ({
                              ...prev,
                              experience: Number(event.target.value)
                            }))
                          }
                          InputLabelProps={{ shrink: true }}
                        />
                        <TextField
                          label="Education"
                          type="number"
                          size="small"
                          value={weights.education}
                          onChange={(event) =>
                            setWeights((prev) => ({
                              ...prev,
                              education: Number(event.target.value)
                            }))
                          }
                          InputLabelProps={{ shrink: true }}
                        />
                        <Chip
                          label={`Total: ${weightsSum}`}
                          color={weightsValid ? 'default' : 'warning'}
                        />
                      </Stack>
                    )}
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          )}

          {activeStep === 4 && (
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2}>
                  <Typography variant="subtitle1">Scenario summary</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Review the changes that will be applied before running or saving.
                  </Typography>
                  <Stack spacing={1}>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Job</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {selectedJob?.title || 'Select a job'}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Scenario name</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {scenarioName || 'Untitled'}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Min years override</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {useJobMinYears ? `Use job (${jobMinYears})` : minYearsOverride}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Education override</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {educationOverride === 'default'
                          ? 'Use job default'
                          : educationOverride === 'required'
                          ? 'Require education'
                          : 'No education required'}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Skill adjustments</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        +{skillsAddMust.length + skillsAddNice.length} / -
                        {skillsRemoveMust.length + skillsRemoveNice.length}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Match mode</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {matchMode === 'full_only' ? 'Full only' : 'Partial ok'}
                      </Typography>
                    </Stack>
                    <Stack direction="row" spacing={1} justifyContent="space-between">
                      <Typography variant="body2">Threshold</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {threshold}
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
                          {JSON.stringify(scenarioPayload, null, 2)}
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
                    disabled={!selectedJobId || !weightsValid}
                  >
                    Save scenario
                  </Button>
                  <Button
                    variant="contained"
                    onClick={() => handleRun()}
                    disabled={!selectedJobId || running || !weightsValid}
                  >
                    Run scenario
                  </Button>
                </>
              )}
            </Stack>
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h6">Scenario Results</Typography>
          {warnings.length > 0 && (
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {warnings.map((warning) => (
                <Chip key={warning} size="small" label={warning} />
              ))}
            </Stack>
          )}
          <Divider />
          <TableContainer sx={{ overflowX: 'hidden' }}>
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
                {summaryTable.map((row, index) => (
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
                {!summaryTable.length && (
                  <TableRow>
                    <TableCell colSpan={5}>
                      <Typography color="text.secondary">
                        Run a scenario to see summary scores.
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
          <Typography variant="h6">Saved Scenarios</Typography>
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
                {storedRows.map((scenario) => (
                  <TableRow key={scenario.id}>
                    <TableCell sx={{ whiteSpace: 'normal', wordBreak: 'break-word' }}>
                      <Typography variant="body2" fontWeight={600}>
                        {scenario.name || `Scenario #${scenario.id}`}
                      </Typography>
                    </TableCell>
                    <TableCell>Job #{scenario.job_id}</TableCell>
                    <TableCell>{formatDate(scenario.created_at)}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={1}>
                        <Button
                          size="small"
                          onClick={() =>
                            handleRun(scenario.scenario_payload, scenario.job_id)
                          }
                        >
                          Run
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => handleEditScenario(scenario)}
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
                        No saved scenarios yet.
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

export default WhatIfPage
