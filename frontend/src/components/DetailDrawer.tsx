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

type DetailKind = 'job' | 'candidate' | 'resume' | 'application' | 'appraisal' | null

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

const toRecordList = (value: unknown) =>
  Array.isArray(value)
    ? (value.filter(
        (item) => item && typeof item === 'object' && !Array.isArray(item)
      ) as Record<string, unknown>[])
    : []

const toText = (value: unknown) =>
  typeof value === 'string' ? value.trim() : ''

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

const formatLocation = (value: unknown) => {
  const location = toRecord(value)
  const parts = [
    toText(location.address),
    toText(location.city),
    toText(location.region),
    toText(location.countryCode)
  ].filter(Boolean)
  return parts.join(', ')
}

const formatResumeDate = (value: string) =>
  /^\d{4}(-\d{2})?$/.test(value) ? value : formatDate(value)

const formatDateRange = (start: unknown, end: unknown) => {
  const startText = toText(start)
  const endText = toText(end)
  if (!startText && !endText) {
    return 'Dates N/A'
  }
  if (startText && !endText) {
    return `${formatResumeDate(startText)} - Present`
  }
  if (!startText && endText) {
    return formatResumeDate(endText)
  }
  return `${formatResumeDate(startText)} - ${formatResumeDate(endText)}`
}

const collectSkillHighlights = (
  skills: Record<string, unknown>[],
  limit = 12
) => {
  const items: string[] = []
  skills.forEach((skill) => {
    const name = toText(skill.name)
    const keywords = toStringList(skill.keywords)
    if (keywords.length) {
      items.push(...keywords)
    } else if (name) {
      items.push(name)
    }
  })
  return Array.from(new Set(items)).slice(0, limit)
}

const formatEducationTitle = (entry: Record<string, unknown>) => {
  const studyType = toText(entry.studyType)
  const area = toText(entry.area)
  if (studyType && area) {
    return `${studyType} in ${area}`
  }
  return studyType || area || 'Education'
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
  const resumeMatch = useMatch('/candidates/:candidateId/resume')
  const candidateMatch = useMatch('/candidates/:candidateId')
  const navigate = useNavigate()
  const location = useLocation()

  const detailKind: DetailKind = jobMatch
    ? 'job'
    : appraisalMatch
    ? 'appraisal'
    : applicationMatch
    ? 'application'
    : resumeMatch
    ? 'resume'
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
    if (resumeMatch?.params.candidateId) {
      return Number(resumeMatch.params.candidateId)
    }
    if (candidateMatch?.params.candidateId) {
      return Number(candidateMatch.params.candidateId)
    }
    return undefined
  }, [jobMatch, appraisalMatch, applicationMatch, resumeMatch, candidateMatch])

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
        } else if (detailKind === 'candidate' || detailKind === 'resume') {
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
    if (detailKind === 'resume') {
      return 'Candidate Resume'
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

  const resumeData = useMemo(() => {
    if (!candidate) {
      return null
    }
    const resume = toRecord(candidate.resume_data)
    const basics = toRecord(resume.basics)
    return {
      resume,
      basics,
      profiles: toRecordList(basics.profiles),
      work: toRecordList(resume.work),
      education: toRecordList(resume.education),
      skills: toRecordList(resume.skills),
      certificates: toRecordList(resume.certificates),
      projects: toRecordList(resume.projects),
      awards: toRecordList(resume.awards),
      publications: toRecordList(resume.publications),
      languages: toRecordList(resume.languages),
      interests: toRecordList(resume.interests),
      references: toRecordList(resume.references)
    }
  }, [candidate])

  const resumeBasics = resumeData?.basics ?? {}
  const resumeWork = resumeData?.work ?? []
  const resumeEducation = resumeData?.education ?? []
  const resumeSkills = resumeData?.skills ?? []
  const resumeCertificates = resumeData?.certificates ?? []
  const resumeProjects = resumeData?.projects ?? []
  const resumeAwards = resumeData?.awards ?? []
  const resumePublications = resumeData?.publications ?? []
  const resumeLanguages = resumeData?.languages ?? []
  const resumeInterests = resumeData?.interests ?? []
  const resumeReferences = resumeData?.references ?? []

  const candidateName = candidate?.name || toText(resumeBasics.name) || 'Unknown'
  const candidateLabel = toText(resumeBasics.label)
  const candidateEmail = candidate?.email || toText(resumeBasics.email)
  const candidatePhone = candidate?.phone || toText(resumeBasics.phone)
  const candidateLocation = formatLocation(resumeBasics.location)
  const candidateWebsite = toText(resumeBasics.url)
  const candidateSummary = toText(resumeBasics.summary)

  const contactItems = [
    candidateEmail ? `Email: ${candidateEmail}` : '',
    candidatePhone ? `Phone: ${candidatePhone}` : '',
    candidateLocation ? `Location: ${candidateLocation}` : '',
    candidateWebsite ? `Website: ${candidateWebsite}` : ''
  ].filter(Boolean)

  const profileLabels = resumeData
    ? resumeData.profiles
        .map((profile) => {
          const network = toText(profile.network)
          const username = toText(profile.username)
          const url = toText(profile.url)
          if (network && username) {
            return `${network}: ${username}`
          }
          if (network && url) {
            return `${network}: ${url}`
          }
          if (url) {
            return url
          }
          return network
        })
        .filter(Boolean)
    : []

  const skillHighlights = collectSkillHighlights(resumeSkills)
  const recentWork = resumeWork.slice(0, 2)
  const latestEducation = resumeEducation[0]
  const resumeAvailable = Object.keys(candidate?.resume_data ?? {}).length > 0

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

        {!loading && !error && detailKind === 'resume' && candidate && (
          <Stack spacing={2}>
            <Stack spacing={0.5}>
              <Typography variant="subtitle2">Name</Typography>
              <Typography>{candidateName}</Typography>
              {candidateLabel && (
                <Typography color="text.secondary">{candidateLabel}</Typography>
              )}
            </Stack>
            <Stack spacing={0.5}>
              <Typography variant="subtitle2">Contact</Typography>
              {contactItems.length ? (
                contactItems.map((item) => (
                  <Typography key={item} color="text.secondary">
                    {item}
                  </Typography>
                ))
              ) : (
                <Typography color="text.secondary">
                  No contact details listed.
                </Typography>
              )}
              {profileLabels.length ? (
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  {profileLabels.map((label, index) => (
                    <Chip key={`${label}-${index}`} label={label} size="small" />
                  ))}
                </Stack>
              ) : (
                <Typography color="text.secondary">No profiles listed.</Typography>
              )}
            </Stack>
            <Divider />

            {!resumeAvailable ? (
              <Typography color="text.secondary">
                Resume data is not available for this candidate.
              </Typography>
            ) : (
              <>
                <Stack spacing={1}>
                  <Typography variant="subtitle2">Summary</Typography>
                  <Typography color="text.secondary">
                    {candidateSummary || 'No summary available.'}
                  </Typography>
                </Stack>

                <Stack spacing={1}>
                  <Typography variant="subtitle2">Skills</Typography>
                  {resumeSkills.length ? (
                    <Stack spacing={1}>
                      {resumeSkills.map((skill, index) => {
                        const name = toText(skill.name) || 'Skills'
                        const level = toText(skill.level)
                        const keywords = toStringList(skill.keywords)
                        return (
                          <Stack key={`${name}-${index}`} spacing={0.5}>
                            <Typography variant="body2" fontWeight={600}>
                              {name}
                            </Typography>
                            {level && (
                              <Typography variant="caption" color="text.secondary">
                                {level}
                              </Typography>
                            )}
                            {keywords.length ? (
                              <Stack direction="row" spacing={1} flexWrap="wrap">
                                {keywords.map((keyword, keywordIndex) => (
                                  <Chip
                                    key={`${name}-${keyword}-${keywordIndex}`}
                                    label={keyword}
                                    size="small"
                                  />
                                ))}
                              </Stack>
                            ) : (
                              <Typography color="text.secondary">
                                No skills listed.
                              </Typography>
                            )}
                          </Stack>
                        )
                      })}
                    </Stack>
                  ) : (
                    <Typography color="text.secondary">No skills listed.</Typography>
                  )}
                </Stack>

                <Stack spacing={1}>
                  <Typography variant="subtitle2">Work experience</Typography>
                  {resumeWork.length ? (
                    <Stack spacing={1.5}>
                      {resumeWork.map((role, index) => {
                        const company = toText(role.name)
                        const position = toText(role.position)
                        const summary = toText(role.summary)
                        const highlights = toStringList(role.highlights)
                        const title =
                          position || company
                            ? `${position || 'Role'}${company ? ` at ${company}` : ''}`
                            : 'Role'
                        return (
                          <Stack key={`${company}-${position}-${index}`} spacing={0.5}>
                            <Typography variant="body2" fontWeight={600}>
                              {title}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {formatDateRange(role.startDate, role.endDate)}
                            </Typography>
                            {summary && (
                              <Typography color="text.secondary">
                                {summary}
                              </Typography>
                            )}
                            {highlights.length ? (
                              <Box component="ul" sx={{ m: 0, pl: 3 }}>
                                {highlights.map((item, highlightIndex) => (
                                  <Box
                                    component="li"
                                    key={`${item}-${highlightIndex}`}
                                    sx={{ color: 'text.secondary' }}
                                  >
                                    <Typography variant="body2" color="text.secondary">
                                      {item}
                                    </Typography>
                                  </Box>
                                ))}
                              </Box>
                            ) : null}
                          </Stack>
                        )
                      })}
                    </Stack>
                  ) : (
                    <Typography color="text.secondary">
                      No work history listed.
                    </Typography>
                  )}
                </Stack>

                <Stack spacing={1}>
                  <Typography variant="subtitle2">Education</Typography>
                  {resumeEducation.length ? (
                    <Stack spacing={1}>
                      {resumeEducation.map((entry, index) => {
                        const institution = toText(entry.institution)
                        const score = toText(entry.score)
                        const courses = toStringList(entry.courses)
                        return (
                          <Stack key={`${institution}-${index}`} spacing={0.5}>
                            <Typography variant="body2" fontWeight={600}>
                              {formatEducationTitle(entry)}
                            </Typography>
                            {institution && (
                              <Typography color="text.secondary">
                                {institution}
                              </Typography>
                            )}
                            <Typography variant="caption" color="text.secondary">
                              {formatDateRange(entry.startDate, entry.endDate)}
                            </Typography>
                            {score && (
                              <Typography variant="caption" color="text.secondary">
                                Score: {score}
                              </Typography>
                            )}
                            {courses.length ? (
                              <Typography variant="caption" color="text.secondary">
                                Courses: {courses.join(', ')}
                              </Typography>
                            ) : null}
                          </Stack>
                        )
                      })}
                    </Stack>
                  ) : (
                    <Typography color="text.secondary">
                      No education entries listed.
                    </Typography>
                  )}
                </Stack>

                <Stack spacing={1}>
                  <Typography variant="subtitle2">Projects</Typography>
                  {resumeProjects.length ? (
                    <Stack spacing={1.5}>
                      {resumeProjects.map((project, index) => {
                        const name = toText(project.name) || 'Project'
                        const description = toText(project.description)
                        const highlights = toStringList(project.highlights)
                        const keywords = toStringList(project.keywords)
                        const roles = toStringList(project.roles)
                        const url = toText(project.url)
                        return (
                          <Stack key={`${name}-${index}`} spacing={0.5}>
                            <Typography variant="body2" fontWeight={600}>
                              {name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {formatDateRange(project.startDate, project.endDate)}
                            </Typography>
                            {url && (
                              <Typography variant="caption" color="text.secondary">
                                {url}
                              </Typography>
                            )}
                            {description && (
                              <Typography color="text.secondary">
                                {description}
                              </Typography>
                            )}
                            {highlights.length ? (
                              <Box component="ul" sx={{ m: 0, pl: 3 }}>
                                {highlights.map((item, highlightIndex) => (
                                  <Box
                                    component="li"
                                    key={`${item}-${highlightIndex}`}
                                    sx={{ color: 'text.secondary' }}
                                  >
                                    <Typography variant="body2" color="text.secondary">
                                      {item}
                                    </Typography>
                                  </Box>
                                ))}
                              </Box>
                            ) : null}
                            {keywords.length ? (
                              <Stack direction="row" spacing={1} flexWrap="wrap">
                                {keywords.map((keyword, keywordIndex) => (
                                  <Chip
                                    key={`${name}-${keyword}-${keywordIndex}`}
                                    label={keyword}
                                    size="small"
                                  />
                                ))}
                              </Stack>
                            ) : null}
                            {roles.length ? (
                              <Typography variant="caption" color="text.secondary">
                                Roles: {roles.join(', ')}
                              </Typography>
                            ) : null}
                          </Stack>
                        )
                      })}
                    </Stack>
                  ) : (
                    <Typography color="text.secondary">
                      No projects listed.
                    </Typography>
                  )}
                </Stack>

                <Stack spacing={1}>
                  <Typography variant="subtitle2">Certifications</Typography>
                  {resumeCertificates.length ? (
                    <Stack spacing={1}>
                      {resumeCertificates.map((cert, index) => {
                        const name = toText(cert.name) || 'Certification'
                        const issuer = toText(cert.issuer)
                        const date = toText(cert.date)
                        const url = toText(cert.url)
                        return (
                          <Stack key={`${name}-${index}`} spacing={0.25}>
                            <Typography variant="body2" fontWeight={600}>
                              {name}
                            </Typography>
                            {issuer && (
                              <Typography color="text.secondary">
                                {issuer}
                              </Typography>
                            )}
                            {date && (
                              <Typography variant="caption" color="text.secondary">
                                {formatResumeDate(date)}
                              </Typography>
                            )}
                            {url && (
                              <Typography variant="caption" color="text.secondary">
                                {url}
                              </Typography>
                            )}
                          </Stack>
                        )
                      })}
                    </Stack>
                  ) : (
                    <Typography color="text.secondary">
                      No certifications listed.
                    </Typography>
                  )}
                </Stack>

                <Stack spacing={1}>
                  <Typography variant="subtitle2">Awards</Typography>
                  {resumeAwards.length ? (
                    <Stack spacing={1}>
                      {resumeAwards.map((award, index) => {
                        const title = toText(award.title) || 'Award'
                        const awarder = toText(award.awarder)
                        const date = toText(award.date)
                        const summary = toText(award.summary)
                        return (
                          <Stack key={`${title}-${index}`} spacing={0.25}>
                            <Typography variant="body2" fontWeight={600}>
                              {title}
                            </Typography>
                            {awarder && (
                              <Typography color="text.secondary">
                                {awarder}
                              </Typography>
                            )}
                            {date && (
                              <Typography variant="caption" color="text.secondary">
                                {formatResumeDate(date)}
                              </Typography>
                            )}
                            {summary && (
                              <Typography color="text.secondary">
                                {summary}
                              </Typography>
                            )}
                          </Stack>
                        )
                      })}
                    </Stack>
                  ) : (
                    <Typography color="text.secondary">No awards listed.</Typography>
                  )}
                </Stack>

                <Stack spacing={1}>
                  <Typography variant="subtitle2">Publications</Typography>
                  {resumePublications.length ? (
                    <Stack spacing={1}>
                      {resumePublications.map((publication, index) => {
                        const name = toText(publication.name) || 'Publication'
                        const publisher = toText(publication.publisher)
                        const releaseDate = toText(publication.releaseDate)
                        const summary = toText(publication.summary)
                        const url = toText(publication.url)
                        return (
                          <Stack key={`${name}-${index}`} spacing={0.25}>
                            <Typography variant="body2" fontWeight={600}>
                              {name}
                            </Typography>
                            {publisher && (
                              <Typography color="text.secondary">
                                {publisher}
                              </Typography>
                            )}
                            {releaseDate && (
                              <Typography variant="caption" color="text.secondary">
                                {formatResumeDate(releaseDate)}
                              </Typography>
                            )}
                            {url && (
                              <Typography variant="caption" color="text.secondary">
                                {url}
                              </Typography>
                            )}
                            {summary && (
                              <Typography color="text.secondary">
                                {summary}
                              </Typography>
                            )}
                          </Stack>
                        )
                      })}
                    </Stack>
                  ) : (
                    <Typography color="text.secondary">
                      No publications listed.
                    </Typography>
                  )}
                </Stack>

                <Stack spacing={1}>
                  <Typography variant="subtitle2">Languages</Typography>
                  {resumeLanguages.length ? (
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      {resumeLanguages.map((language, index) => {
                        const name = toText(language.language)
                        const fluency = toText(language.fluency)
                        if (!name) {
                          return null
                        }
                        const label = fluency ? `${name} (${fluency})` : name
                        return label ? (
                          <Chip key={`${label}-${index}`} label={label} size="small" />
                        ) : null
                      })}
                    </Stack>
                  ) : (
                    <Typography color="text.secondary">
                      No languages listed.
                    </Typography>
                  )}
                </Stack>

                <Stack spacing={1}>
                  <Typography variant="subtitle2">Interests</Typography>
                  {resumeInterests.length ? (
                    <Stack spacing={0.75}>
                      {resumeInterests.map((interest, index) => {
                        const name = toText(interest.name)
                        const keywords = toStringList(interest.keywords)
                        return (
                          <Stack key={`${name}-${index}`} spacing={0.25}>
                            <Typography variant="body2" fontWeight={600}>
                              {name || 'Interest'}
                            </Typography>
                            {keywords.length ? (
                              <Typography variant="caption" color="text.secondary">
                                {keywords.join(', ')}
                              </Typography>
                            ) : null}
                          </Stack>
                        )
                      })}
                    </Stack>
                  ) : (
                    <Typography color="text.secondary">
                      No interests listed.
                    </Typography>
                  )}
                </Stack>

                <Stack spacing={1}>
                  <Typography variant="subtitle2">References</Typography>
                  {resumeReferences.length ? (
                    <Stack spacing={1}>
                      {resumeReferences.map((reference, index) => {
                        const name = toText(reference.name)
                        const refText = toText(reference.reference)
                        return (
                          <Stack key={`${name}-${index}`} spacing={0.25}>
                            <Typography variant="body2" fontWeight={600}>
                              {name || 'Reference'}
                            </Typography>
                            {refText && (
                              <Typography color="text.secondary">
                                {refText}
                              </Typography>
                            )}
                          </Stack>
                        )
                      })}
                    </Stack>
                  ) : (
                    <Typography color="text.secondary">
                      No references listed.
                    </Typography>
                  )}
                </Stack>
              </>
            )}
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
