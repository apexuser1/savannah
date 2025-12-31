import { useEffect, useMemo, useState } from 'react'
import {
  Box,
  Chip,
  Divider,
  Drawer,
  IconButton,
  Paper,
  Stack,
  Typography
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import { useLocation, useMatch, useNavigate } from 'react-router-dom'
import { fetchApplication, fetchCandidate, fetchJob } from '../api/client'
import type { Application, Candidate, Job } from '../types'

const drawerWidth = 440

type DetailKind = 'job' | 'candidate' | 'application' | 'appraisal' | null

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

const toRecord = (value: unknown) =>
  value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}

const toStringList = (value: unknown) =>
  Array.isArray(value) ? value.filter((item) => typeof item === 'string') : []

const formatValue = (value: unknown) => {
  if (typeof value === 'number' && Number.isFinite(value)) {
    if (Number.isInteger(value)) {
      return value.toString()
    }
    return value.toFixed(1)
  }
  if (typeof value === 'string') {
    return value
  }
  return 'N/A'
}

const formatList = (value: unknown) => {
  const list = toStringList(value)
  return list.length ? list.join(', ') : 'None'
}

const JsonBlock = ({ value }: { value: Record<string, unknown> | undefined }) => (
  <Paper variant="outlined" sx={{ p: 2, bgcolor: 'background.default' }}>
    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
      {value ? JSON.stringify(value, null, 2) : 'No data available.'}
    </pre>
  </Paper>
)

const DetailDrawer = () => {
  const jobMatch = useMatch('/jobs/:jobId')
  const applicationMatch = useMatch('/applications/:applicationId')
  const appraisalMatch = useMatch('/applications/:applicationId/appraisal')
  const candidateMatch = useMatch('/candidates/:candidateId')
  const navigate = useNavigate()
  const location = useLocation()

  const detailKind: DetailKind = jobMatch
    ? 'job'
    : appraisalMatch
    ? 'appraisal'
    : applicationMatch
    ? 'application'
    : candidateMatch
    ? 'candidate'
    : null

  const detailId = useMemo(() => {
    if (jobMatch?.params.jobId) {
      return Number(jobMatch.params.jobId)
    }
    if (appraisalMatch?.params.applicationId) {
      return Number(appraisalMatch.params.applicationId)
    }
    if (applicationMatch?.params.applicationId) {
      return Number(applicationMatch.params.applicationId)
    }
    if (candidateMatch?.params.candidateId) {
      return Number(candidateMatch.params.candidateId)
    }
    return undefined
  }, [jobMatch, appraisalMatch, applicationMatch, candidateMatch])

  const [job, setJob] = useState<Job | undefined>()
  const [candidate, setCandidate] = useState<Candidate | undefined>()
  const [application, setApplication] = useState<Application | undefined>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    const loadDetail = async () => {
      if (!detailKind || !detailId) {
        return
      }
      setLoading(true)
      setError(null)
      try {
        if (detailKind === 'job') {
          const data = await fetchJob(detailId)
          if (isMounted) {
            setJob(data)
            setCandidate(undefined)
            setApplication(undefined)
          }
        } else if (detailKind === 'candidate') {
          const data = await fetchCandidate(detailId)
          if (isMounted) {
            setCandidate(data)
            setJob(undefined)
            setApplication(undefined)
          }
        } else if (detailKind === 'application' || detailKind === 'appraisal') {
          const data = await fetchApplication(detailId)
          if (isMounted) {
            setApplication(data)
            setCandidate(undefined)
            setJob(undefined)
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load data')
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    loadDetail()
    return () => {
      isMounted = false
    }
  }, [detailKind, detailId])

  const handleClose = () => {
    if (window.history.length > 1) {
      navigate(-1)
    } else {
      navigate('/', { replace: true })
    }
  }

  const title = useMemo(() => {
    if (detailKind === 'job') {
      return 'Job Detail'
    }
    if (detailKind === 'candidate') {
      return 'Candidate Detail'
    }
    if (detailKind === 'application') {
      return 'Application Detail'
    }
    if (detailKind === 'appraisal') {
      return 'Application Appraisal'
    }
    return ''
  }, [detailKind])

  const appraisalData = useMemo(() => {
    if (detailKind !== 'appraisal' || !application) {
      return null
    }
    const matchData = toRecord(application.match_data)
    const mustHave = toRecord(matchData.must_have_skills)
    const niceHave = toRecord(matchData.nice_to_have_skills)
    const experience = toRecord(matchData.minimum_years_experience)
    const education = toRecord(matchData.required_education)
    const strengths = toStringList(matchData.strengths)
    const weaknesses = toStringList(matchData.weaknesses)
    const overallScore =
      typeof matchData.overall_score === 'number'
        ? matchData.overall_score
        : application.overall_score
    return {
      matchData,
      mustHave,
      niceHave,
      experience,
      education,
      strengths,
      weaknesses,
      overallScore,
      recommendation:
        typeof matchData.recommendation === 'string'
          ? matchData.recommendation
          : 'N/A'
    }
  }, [application, detailKind])

  return (
    <Drawer
      anchor="right"
      open={Boolean(detailKind)}
      onClose={handleClose}
      sx={{
        '& .MuiDrawer-paper': {
          width: { xs: '100vw', sm: drawerWidth },
          borderLeft: '1px solid',
          borderColor: 'divider'
        }
      }}
    >
      <Box sx={{ p: 3 }}>
        <Stack direction="row" alignItems="center" spacing={2}>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6">{title}</Typography>
            <Typography variant="body2" color="text.secondary">
              {location.pathname}
            </Typography>
          </Box>
          <IconButton onClick={handleClose}>
            <CloseIcon />
          </IconButton>
        </Stack>
      </Box>
      <Divider />
      <Box sx={{ p: 3 }}>
        {loading && <Typography>Loading details...</Typography>}
        {error && (
          <Typography color="error" sx={{ mb: 2 }}>
            {error}
          </Typography>
        )}

        {!loading && !error && detailKind === 'job' && job && (
          <Stack spacing={2}>
            <Box>
              <Typography variant="subtitle2">Title</Typography>
              <Typography>{job.title || 'Untitled role'}</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2">Company</Typography>
              <Typography>{job.company || 'N/A'}</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2">Location</Typography>
              <Typography>{job.location || 'N/A'}</Typography>
            </Box>
            <JsonBlock value={job.job_data} />
          </Stack>
        )}

        {!loading && !error && detailKind === 'candidate' && candidate && (
          <Stack spacing={2}>
            <Box>
              <Typography variant="subtitle2">Name</Typography>
              <Typography>{candidate.name || 'Unknown'}</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2">Email</Typography>
              <Typography>{candidate.email || 'N/A'}</Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2">Phone</Typography>
              <Typography>{candidate.phone || 'N/A'}</Typography>
            </Box>
            <JsonBlock value={candidate.resume_data} />
          </Stack>
        )}

        {!loading && !error && detailKind === 'application' && application && (
          <Stack spacing={2}>
            <Box>
              <Typography variant="subtitle2">Application</Typography>
              <Typography>
                #{application.id} for Job #{application.job_id}
              </Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2">Candidate</Typography>
              <Typography>
                {application.candidate?.name || `#${application.candidate_id}`}
              </Typography>
            </Box>
            <Box>
              <Typography variant="subtitle2">Overall Score</Typography>
              <Typography>{application.overall_score?.toFixed(1) ?? 'N/A'}</Typography>
            </Box>
            <JsonBlock value={application.match_data as Record<string, unknown> | undefined} />
          </Stack>
        )}

        {!loading && !error && detailKind === 'appraisal' && application && (
          <Stack spacing={2}>
            <Stack spacing={1}>
              <Typography variant="subtitle2">Candidate</Typography>
              <Typography>
                {application.candidate?.name || `Candidate #${application.candidate_id}`}
              </Typography>
              {application.candidate?.email && (
                <Typography color="text.secondary">
                  {application.candidate.email}
                </Typography>
              )}
            </Stack>
            <Stack spacing={1}>
              <Typography variant="subtitle2">Job</Typography>
              <Typography>
                {application.job?.title || `Job #${application.job_id}`}
              </Typography>
              <Typography color="text.secondary">
                {application.job?.company || 'Company N/A'}
              </Typography>
            </Stack>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Chip label={`Overall: ${formatScore(appraisalData?.overallScore)}`} />
              <Chip label={`Recommendation: ${appraisalData?.recommendation ?? 'N/A'}`} />
              <Chip label={`Created: ${formatDate(application.created_at)}`} />
            </Stack>
            <Divider />

            <Stack spacing={1}>
              <Typography variant="subtitle2">Summary</Typography>
              <Typography color="text.secondary">
                {typeof appraisalData?.matchData?.summary === 'string'
                  ? appraisalData?.matchData?.summary
                  : 'No summary available.'}
              </Typography>
            </Stack>

            <Stack spacing={1}>
              <Typography variant="subtitle2">Must-have skills</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                <Chip
                  label={`Score: ${formatScore(
                    appraisalData?.mustHave?.score as number
                  )}`}
                />
                <Chip
                  label={`Full: ${
                    toStringList(appraisalData?.mustHave?.full_matches).length
                  }`}
                />
                <Chip
                  label={`Partial: ${
                    toStringList(appraisalData?.mustHave?.partial_matches).length
                  }`}
                />
                <Chip
                  label={`Missing: ${
                    toStringList(appraisalData?.mustHave?.missing_skills).length
                  }`}
                />
              </Stack>
              <Typography color="text.secondary">
                {typeof appraisalData?.mustHave?.analysis === 'string'
                  ? appraisalData?.mustHave?.analysis
                  : 'No must-have analysis available.'}
              </Typography>
              <Typography variant="caption">
                Full matches: {formatList(appraisalData?.mustHave?.full_matches)}
              </Typography>
              <Typography variant="caption">
                Partial matches: {formatList(appraisalData?.mustHave?.partial_matches)}
              </Typography>
              <Typography variant="caption">
                Missing: {formatList(appraisalData?.mustHave?.missing_skills)}
              </Typography>
            </Stack>

            <Stack spacing={1}>
              <Typography variant="subtitle2">Nice-to-have skills</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                <Chip
                  label={`Score: ${formatScore(
                    appraisalData?.niceHave?.score as number
                  )}`}
                />
                <Chip
                  label={`Full: ${
                    toStringList(appraisalData?.niceHave?.full_matches).length
                  }`}
                />
                <Chip
                  label={`Partial: ${
                    toStringList(appraisalData?.niceHave?.partial_matches).length
                  }`}
                />
                <Chip
                  label={`Missing: ${
                    toStringList(appraisalData?.niceHave?.missing_skills).length
                  }`}
                />
              </Stack>
              <Typography color="text.secondary">
                {typeof appraisalData?.niceHave?.analysis === 'string'
                  ? appraisalData?.niceHave?.analysis
                  : 'No nice-to-have analysis available.'}
              </Typography>
              <Typography variant="caption">
                Full matches: {formatList(appraisalData?.niceHave?.full_matches)}
              </Typography>
              <Typography variant="caption">
                Partial matches: {formatList(appraisalData?.niceHave?.partial_matches)}
              </Typography>
              <Typography variant="caption">
                Missing: {formatList(appraisalData?.niceHave?.missing_skills)}
              </Typography>
            </Stack>

            <Stack spacing={1}>
              <Typography variant="subtitle2">Experience</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                <Chip
                  label={`Score: ${formatScore(
                    appraisalData?.experience?.score as number
                  )}`}
                />
                <Chip
                  label={`Candidate years: ${formatValue(
                    appraisalData?.experience?.candidate_years
                  )}`}
                />
                <Chip
                  label={`Required years: ${formatValue(
                    appraisalData?.experience?.required_years
                  )}`}
                />
              </Stack>
              <Typography color="text.secondary">
                {typeof appraisalData?.experience?.analysis === 'string'
                  ? appraisalData?.experience?.analysis
                  : 'No experience analysis available.'}
              </Typography>
            </Stack>

            <Stack spacing={1}>
              <Typography variant="subtitle2">Education</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                <Chip
                  label={`Score: ${formatScore(
                    appraisalData?.education?.score as number
                  )}`}
                />
                <Chip
                  label={`Candidate: ${formatValue(
                    appraisalData?.education?.candidate_education
                  )}`}
                />
                <Chip
                  label={`Required: ${formatValue(
                    appraisalData?.education?.required_education
                  )}`}
                />
              </Stack>
              <Typography color="text.secondary">
                {typeof appraisalData?.education?.analysis === 'string'
                  ? appraisalData?.education?.analysis
                  : 'No education analysis available.'}
              </Typography>
            </Stack>

            <Stack spacing={1}>
              <Typography variant="subtitle2">Strengths</Typography>
              {appraisalData?.strengths.length ? (
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {appraisalData.strengths.map((item) => (
                    <Chip key={item} label={item} size="small" />
                  ))}
                </Stack>
              ) : (
                <Typography color="text.secondary">No strengths listed.</Typography>
              )}
            </Stack>

            <Stack spacing={1}>
              <Typography variant="subtitle2">Risks / gaps</Typography>
              {appraisalData?.weaknesses.length ? (
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {appraisalData.weaknesses.map((item) => (
                    <Chip key={item} label={item} size="small" />
                  ))}
                </Stack>
              ) : (
                <Typography color="text.secondary">No gaps listed.</Typography>
              )}
            </Stack>
          </Stack>
        )}
      </Box>
    </Drawer>
  )
}

export default DetailDrawer
