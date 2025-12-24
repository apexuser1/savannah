# Resume Job Matcher

A Python-based system for matching candidate resumes to job descriptions with AI-powered scoring.

## Features

- 📄 **Resume Parsing**: Parse PDF, DOCX, TXT, and MD files into JSON Resume format (jsonresume.org schema)
- 💼 **Job Description Parsing**: Extract structured data from job postings
- 🤖 **LLM-Powered Matching**: Automatic candidate-job matching with detailed scoring using OpenAI or OpenRouter
- 🗄️ **PostgreSQL Storage**: Store candidates, jobs, and applications with match data
- 💻 **CLI Interface**: Command-line tools for managing the system
- 🌐 **REST API**: FastAPI-based REST API for programmatic access
- 📊 **Detailed Scoring**: Match scores for skills, experience, education, and overall fit
- **What-if Analysis**: Run scenario-based matching with strict, explainable rules

## Project Structure

```
resume-job-matcher/
├── .env.example              # Environment variables template
├── .gitignore
├── requirements.txt          # Python dependencies
├── README.md
├── cli.py                    # CLI entry point
├── api.py                    # API server entry point
└── src/
    ├── config.py             # Configuration management
    ├── database/
    │   ├── models.py         # SQLAlchemy models
    │   └── connection.py     # Database connection
    ├── parsers/
    │   ├── resume_parser.py  # Resume parsing (PDF, DOCX, TXT, MD)
    │   └── job_parser.py     # Job description parsing
    ├── matching/
    │   └── matcher.py        # LLM matching logic
    ├── api/
    │   └── app.py            # FastAPI application
    └── cli/
        └── commands.py       # Click CLI commands
```

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database (e.g., Neon, local PostgreSQL, or any PostgreSQL provider)
- OpenAI API key or OpenRouter API key

## Installation

### 1. Clone or download this project

```bash
cd resume-job-matcher
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@host:port/database

# LLM Provider Configuration
LLM_PROVIDER=openai  # Options: "openai" or "openrouter"

# OpenAI Configuration (if using OpenAI)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# OpenRouter Configuration (if using OpenRouter)
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=openai/gpt-4-turbo-preview

# Logging
LOG_LEVEL=INFO
```

**Getting a PostgreSQL database:**
- **Neon** (Free tier available): https://neon.tech/
- **Supabase** (Free tier available): https://supabase.com/
- **ElephantSQL** (Free tier available): https://www.elephantsql.com/
- **Local PostgreSQL**: Install PostgreSQL on your machine

### 5. Initialize the database

```bash
python cli.py init-db
```

This will create all necessary tables (candidates, jobs, applications).

## Usage

### CLI Commands

#### Initialize Database
```bash
python cli.py init-db
```

#### Upload a Job Description
```bash
python cli.py upload-job path/to/job_description.pdf
```

Supported formats: PDF, DOCX, TXT, MD

Example output:
```
Parsing job description: job_description.pdf
✓ Job created (ID: 1)
  Title: Senior Software Engineer
  Company: Tech Corp
  Location: San Francisco
```

#### Upload a Resume (creates application and generates match scores)
```bash
python cli.py upload-resume path/to/resume.pdf <job_id>
```

Example:
```bash
python cli.py upload-resume john_doe_resume.pdf 1
```

Example output:
```
Parsing resume: john_doe_resume.pdf
✓ Candidate created (ID: 1)
  Name: John Doe
  Email: john.doe@email.com

Matching candidate to job...

✓ Application created (ID: 1)

Match Scores:
  Overall Score: 85.0/100
  Must-Have Skills: 90.0/100
  Nice-to-Have Skills: 75.0/100
  Experience: 100.0/100
  Education: 100.0/100

  Recommendation: Highly Recommended

  Summary: This candidate is a strong match for the position...
```

#### List Jobs
```bash
# List all jobs
python cli.py list-jobs

# Filter by date
python cli.py list-jobs --since 2024-01-01
```

#### List Candidates
```bash
# List all candidates
python cli.py list-candidates

# Filter by date
python cli.py list-candidates --since 2024-01-01
```

#### List Applications
```bash
# List all applications
python cli.py list-applications

# Filter by date
python cli.py list-applications --since 2024-01-01

# Filter by minimum score
python cli.py list-applications --min-score 80

# Combine filters
python cli.py list-applications --since 2024-01-01 --min-score 75
```

#### What-if Analysis
Run scenario-based matching with a strict, explainable ruleset.

Basic scenario text:
```bash
python cli.py what-if "require all skills and 3+ years" 13 --match-mode full --threshold 50
```

Scenario file (skip LLM parsing):
```bash
python cli.py what-if "-" 13 --scenario-file scenario.json --match-mode partial --partial-weight 0.5 --explain
```

Scenario JSON example:
```json
{
  "scenario": {
    "min_years_override": 3,
    "education_required_override": null,
    "skills_add": {
      "must_have": [],
      "nice_to_have": ["Experience with AWS cloud services (EC2, S3, RDS, Lambda, ECS)"]
    },
    "skills_remove": {
      "must_have": [],
      "nice_to_have": []
    }
  },
  "evaluation": {
    "match_mode": "partial_ok",
    "partial_match_weight": 0.5,
    "must_have_gate_mode": "coverage_min",
    "must_have_coverage_min": 1.0,
    "include_nice_to_have": true,
    "weights_override": null
  },
  "optimization": {
    "objective": "maximize_candidate_count",
    "overall_score_threshold": 50
  }
}
```

Validation notes:
- Unknown skills are rejected unless they already exist in the job requirements.
- weights_override must sum to 100.
- match_mode must be full or partial.
- full-only mode requires match_data with full/partial matches; re-run matching for older applications.

### REST API

#### Start the API Server
```bash
python api.py
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI): `http://localhost:8000/docs`

#### API Endpoints

**Root**
```
GET /
```

**Upload Resume**
```
POST /api/resumes/upload
Content-Type: multipart/form-data

Parameters:
- file: Resume file (PDF, DOCX, TXT, MD)
- job_id: ID of the job to apply to

Response:
{
  "candidate": {
    "id": 1,
    "name": "John Doe",
    "email": "john.doe@email.com",
    ...
  },
  "application": {
    "id": 1,
    "overall_score": 85.0,
    "must_have_skills_score": 90.0,
    "match_data": { ... },
    ...
  },
  "message": "Resume uploaded and matched successfully"
}
```

**Upload Job Description**
```
POST /api/jobs/upload
Content-Type: multipart/form-data

Parameters:
- file: Job description file (PDF, DOCX, TXT, MD)

Response:
{
  "id": 1,
  "title": "Senior Software Engineer",
  "company": "Tech Corp",
  "location": "San Francisco",
  ...
}
```

**List Jobs**
```
GET /api/jobs?since=2024-01-01

Response:
[
  {
    "id": 1,
    "title": "Senior Software Engineer",
    "company": "Tech Corp",
    ...
  }
]
```

**List Candidates**
```
GET /api/candidates?since=2024-01-01

Response:
[
  {
    "id": 1,
    "name": "John Doe",
    "email": "john.doe@email.com",
    ...
  }
]
```

**List Applications**
```
GET /api/applications?since=2024-01-01&min_score=80

Response:
[
  {
    "id": 1,
    "candidate_id": 1,
    "job_id": 1,
    "overall_score": 85.0,
    "match_data": { ... },
    ...
  }
]
```

**What-if Scenario**
```
POST /api/what-if
Content-Type: application/json

Request:
{
  "job_id": 13,
  "scenario_text": "require all skills and 3+ years",
  "match_mode": "full",
  "overall_score_threshold": 50,
  "include_details": false
}

Response:
{
  "job_id": 13,
  "normalized_scenario": { ... },
  "shock_report": { ... },
  "warnings": [],
  "summary": { ... }
}
```
Optional fields:
- `summary`: when true, include a `summary_table` with Original Score and Scenario Score.
- `include_details`: when true, include per-candidate details (cannot be combined with `summary`).

**Health Check**
```
GET /health
```

### Example cURL Commands

**Upload a job:**
```bash
curl -X POST "http://localhost:8000/api/jobs/upload" \
  -F "file=@job_description.pdf"
```

**Upload a resume:**
```bash
curl -X POST "http://localhost:8000/api/resumes/upload?job_id=1" \
  -F "file=@resume.pdf"
```

**List applications with score filter:**
```bash
curl "http://localhost:8000/api/applications?min_score=80"
```

**Run a what-if scenario:**
```bash
curl -X POST "http://localhost:8000/api/what-if" \
  -H "Content-Type: application/json" \
  -d '{"job_id":13,"scenario_text":"require all skills and 3+ years","match_mode":"full","overall_score_threshold":50}'
```

## Database Schema

### Candidates Table
- Stores structured resume data in JSON Resume format
- Fields: id, resume_data (JSON), name, email, phone, original_filename, file_type, created_at, updated_at

### Jobs Table
- Stores structured job descriptions
- Fields: id, job_data (JSON), title, company, location, original_filename, file_type, created_at, updated_at

### Applications Table
- Links candidates to jobs with match scores
- Fields: id, candidate_id, job_id, match_data (JSON), overall_score, must_have_skills_score, nice_to_have_skills_score, experience_score, education_score, created_at, updated_at

## Match Scoring

The LLM analyzes candidates and jobs to generate scores (0-100) for:

1. **Must-Have Skills**: Match against required technical skills
2. **Nice-to-Have Skills**: Match against preferred skills
3. **Minimum Years Experience**: Whether candidate meets experience requirements
4. **Required Education**: Whether candidate meets education requirements
5. **Overall Score**: Comprehensive match score

The match data also includes:
- Detailed analysis for each category
- List of matched and missing skills
- Full and partial match breakdown for must-have and nice-to-have skills
- Candidate strengths and weaknesses
- Hiring recommendation (Highly Recommended, Recommended, Consider, Not Recommended)
- Summary narrative

## JSON Resume Format

The system uses the JSON Resume schema (jsonresume.org) for structured candidate data:

```json
{
  "basics": {
    "name": "John Doe",
    "label": "Software Engineer",
    "email": "john@example.com",
    "phone": "+1-555-0100",
    "summary": "Experienced software engineer...",
    "location": { ... },
    "profiles": [ ... ]
  },
  "work": [ ... ],
  "education": [ ... ],
  "skills": [ ... ],
  "certificates": [ ... ],
  "projects": [ ... ],
  ...
}
```

## Configuration Options

### LLM Providers

**OpenAI** (recommended):
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
```

**OpenRouter** (access to multiple models):
```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-4-turbo-preview
```

### Supported File Formats

- **PDF**: Parsed using pdfplumber or PyPDF2
- **DOCX**: Parsed using python-docx
- **TXT**: Plain text files
- **MD**: Markdown files

## Troubleshooting

### Database Connection Issues
- Verify your `DATABASE_URL` is correct
- Ensure your PostgreSQL database is accessible
- Check firewall settings if using a remote database

### LLM API Issues
- Verify your API key is correct
- Check you have sufficient API credits
- Ensure you're using a supported model

### File Parsing Issues
- Ensure files are not corrupted
- Try converting to a different format
- Check file permissions

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Activate your virtual environment
- Try reinstalling dependencies

## Development

### Running Tests
```bash
# Add your tests here
python -m pytest tests/
```

### Code Style
The project follows PEP 8 style guidelines.

## License

This is a Proof of Concept (POC) project. Adjust licensing as needed for your use case.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs` when running the API
3. Check log output for detailed error messages

## Future Enhancements

Potential improvements for production use:
- Add authentication and authorization
- Implement rate limiting
- Add batch processing for multiple resumes
- Create web UI interface
- Add email notifications
- Implement caching for faster responses
- Add unit and integration tests
- Support for additional file formats
- Advanced filtering and search capabilities
- Export match results to PDF/Excel
- Candidate ranking and comparison features

## What-if CLI Guide

This section provides end-to-end CLI examples and a reference for scenario parameters.

### Quick Start Examples

Basic what-if using free-text scenario parsing:
```bash
python cli.py what-if "require all skills and 3+ years" 13 --match-mode full --threshold 50
```

Allow partial matches with a custom partial weight:
```bash
python cli.py what-if "3+ years and allow partials" 13 --match-mode partial --partial-weight 0.5 --threshold 50
```

Skip LLM parsing and pass a scenario JSON file:
```bash
python cli.py what-if "-" 13 --scenario-file scenario.json --match-mode partial --partial-weight 0.5
```

Show per-candidate breakdowns:
```bash
python cli.py what-if "require all skills" 13 --match-mode full --explain
```

Summary table output (replaces JSON detail):
```bash
python cli.py what-if "3+ years and allow partials" 18 --match-mode partial --partial-weight 0.5 --threshold 50 --summary
```

### Scenario Text Guide

The scenario text is parsed into a strict schema. The parser only recognizes the directives below, and skills must come from the job's existing requirement lists. Unknown directives or skills are rejected.

Recognized directives (examples -> JSON field):
- "3+ years", "minimum 4 years", "set min years to 2" -> `scenario.min_years_override`
- "ignore education", "education not required" -> `scenario.education_required_override = false`
- "require all skills", "all must-haves" -> `evaluation.must_have_gate_mode = all` (and implies full-only)
- "allow partial matches", "partials ok" -> `evaluation.match_mode = partial_ok`
- "must-have coverage 0.8", "80% must-have coverage" -> `evaluation.must_have_coverage_min`
- "exclude nice-to-haves", "ignore nice-to-have" -> `evaluation.include_nice_to_have = false`
- "add Redis to must-haves", "remove Kubernetes" -> `scenario.skills_add` / `scenario.skills_remove`
- "weights must-have 50, experience 30, education 20" -> `evaluation.weights_override`
- "minimum score 60", "threshold 60" -> `optimization.overall_score_threshold`

If you need exact control, use a scenario JSON file instead of free text.

### Parameter Reference

CLI flags:
- `scenario_text`: Free-text scenario description parsed by the LLM.
- `job_id`: Job ID to evaluate against.
- `--scenario-file`: Path to a scenario JSON file; skips LLM parsing.
- `--match-mode`: `full` counts only FULL matches; `partial` counts PARTIAL matches using `--partial-weight` when computing coverage and scores.
- `--partial-weight`: Weight for partial matches when `--match-mode partial` is used (0.0 to 1.0).
- `--threshold`: Overall score threshold for pass/fail (0 to 100).
- `--explain`: Include per-candidate details in the output.
- `--summary`: Output a list-applications style table with Original Score and Scenario Score (cannot be combined with `--explain`).

Match levels:
- **FULL match**: Clear, direct evidence in the resume that satisfies the requirement (exact skill or close synonym with concrete use).
- **PARTIAL match**: Related or limited evidence that is relevant but not as strong or complete as the requirement.
- **MISSING**: No relevant evidence found for the requirement.

Scenario JSON parameters:
- `scenario.min_years_override`: Override minimum years of experience (0 to 40, or null to use job default).
- `scenario.education_required_override`: Override education requirement (true/false, or null to use job default).
- `scenario.skills_add.must_have`: Add skills to must-have requirements (list of job-defined skills).
- `scenario.skills_add.nice_to_have`: Add skills to nice-to-have requirements (list of job-defined skills).
- `scenario.skills_remove.must_have`: Remove skills from must-have requirements.
- `scenario.skills_remove.nice_to_have`: Remove skills from nice-to-have requirements.
- `evaluation.match_mode`: `full_only` uses only FULL matches for coverage and scoring; `partial_ok` includes PARTIAL matches at the configured weight.
- `evaluation.partial_match_weight`: Partial match weight used when `partial_ok` is selected.
- `evaluation.must_have_gate_mode`: `all` (every must-have must be satisfied) or `coverage_min`.
- `evaluation.must_have_coverage_min`: Minimum coverage (0.0 to 1.0) when using `coverage_min`.
- `evaluation.include_nice_to_have`: Whether nice-to-have skills contribute to overall score.
- `evaluation.weights_override`: Optional weights object with `must_have`, `nice_to_have`, `experience`, `education` that sums to 100.
- `optimization.objective`: Currently `maximize_candidate_count`.
- `optimization.overall_score_threshold`: Pass/fail threshold for optimization (0 to 100).

### Example Scenario JSON
```json
{
  "scenario": {
    "min_years_override": 3,
    "education_required_override": null,
    "skills_add": {
      "must_have": [],
      "nice_to_have": []
    },
    "skills_remove": {
      "must_have": [],
      "nice_to_have": []
    }
  },
  "evaluation": {
    "match_mode": "partial_ok",
    "partial_match_weight": 0.5,
    "must_have_gate_mode": "coverage_min",
    "must_have_coverage_min": 1.0,
    "include_nice_to_have": true,
    "weights_override": null
  },
  "optimization": {
    "objective": "maximize_candidate_count",
    "overall_score_threshold": 50
  }
}
```

### Validation Behavior
- Unknown skills are rejected unless they already exist in the job requirements.
- `weights_override` must sum to 100.
- `match_mode` must be `full` or `partial` (CLI) and `full_only` or `partial_ok` (JSON).
- Full-only mode requires match_data that includes full/partial breakdowns; older applications must be re-matched.

## Optimisation (Goal Seeking)

The optimiser searches for minimal relaxations to reach a target candidate count. It only relaxes constraints (no adding requirements).

### Quick Start

```bash
python cli.py optimisation 13 --optimisation-file optimisation.json --candidates 10
```

The CLI prints a summary table first (same shape as `--summary`). Use `--detail` to append JSON candidate details for the best result.

### Optimisation JSON Example

```json
{
  "target": { "candidate_count": 10, "mode": "at_least" },
  "strategy": {
    "name": "beam",
    "options": { "beam_width": 5 }
  },
  "constraints": {
    "max_total_changes": 3,
    "allowed_relaxations": [
      "remove_nice_to_have",
      "demote_must_to_nice",
      "remove_must_have",
      "lower_min_years",
      "disable_education",
      "lower_threshold"
    ],
    "min_years_override": { "min": 0, "step": 1 },
    "overall_score_threshold": { "min": 40, "step": 5 },
    "max_skill_changes": 2
  },
  "costs": {
    "remove_nice_to_have": 1,
    "demote_must_to_nice": 2,
    "remove_must_have": 3,
    "lower_min_years": 1,
    "disable_education": 2,
    "lower_threshold": 1
  },
  "top_k": 5
}
```

Notes:
- `job_id` is provided via the CLI/API, not inside the optimisation file.
- `candidate_count` can be overridden on the CLI/API to reuse the same file for different targets.
- Relaxations are applied one skill at a time; nice-to-have skills are considered first.

### Strategies and Options

Available strategies (with options and defaults):
- `greedy`: no options. Tries the best single relaxation at each step until the target is met or max changes are used.
- `beam`: options: `beam_width` (default 5). Explores the top N candidates at each step.
- `monte_carlo`: options: `max_runs` (default 200), `seed` (optional). Randomly samples relaxation sequences.

Algorithm notes:
- Greedy: fast, deterministic, and locally optimal; it may miss better multi-step paths that require a temporary dip.
- Beam: balances speed and breadth by keeping the best N partial solutions at each step; higher `beam_width` increases quality and cost.
- Monte Carlo: explores diverse combinations stochastically; useful when the search space is large or non-linear, and a `seed` makes runs repeatable.

Example: greedy (no options)
```json
{
  "strategy": { "name": "greedy" }
}
```

Example: beam search (custom width)
```json
{
  "strategy": { "name": "beam", "options": { "beam_width": 10 } }
}
```

Example: monte carlo (runs + seed)
```json
{
  "strategy": { "name": "monte_carlo", "options": { "max_runs": 500, "seed": 42 } }
}
```

## Optimisation (Goal Seeking) - Descriptions

### Greedy Strategy
Identifier: `greedy`

Options: none

Core idea: At each step, apply the single best available relaxation, given the current state.

How it works:
- Start from the current configuration.
- Evaluate all immediately available relaxations.
- Select the relaxation that gives the largest improvement in the objective.
- Apply it.
- Repeat until:
  - The target is met, or
  - No relaxation yields improvement, or
  - The maximum number of allowed changes/steps is reached.

Characteristics:
- Deterministic: Given the same starting point and constraints, it always produces the same sequence of changes.
- Myopic / locally optimal: Optimizes only for the next step and never looks ahead multiple steps.
- Very fast: Minimal bookkeeping; only one candidate path is considered at any time.

When to use greedy:
- The search space is small or relatively smooth (local choices are usually good globally).
- You care about speed and predictability more than global optimality.
- You are prototyping, running quick what-if analyses, or want a baseline for comparison.
- You need stable results for regression testing or CI pipelines.

Advantages:
- Simple to reason about and debug.
- Minimal computation and memory overhead.
- Results are easy to explain ("we always picked the best next move").

Limitations:
- Can get stuck in local optima if the globally optimal path requires a short-term worse move.
- Does not explore alternative paths once it finds a locally attractive one.
- Not ideal for highly non-linear or rugged search spaces.

### Beam Search Strategy
Identifier: `beam`

Options:
- `beam_width` (default: 5) - the maximum number of top partial solutions kept at each depth.

Core idea: Like a wider greedy search; it considers the best few paths in parallel instead of committing to a single one.

How it works:
- Initialize the beam with the starting configuration.
- For each step:
  - For every configuration in the current beam, generate all valid next-step relaxations.
  - Combine all resulting candidates into a single pool.
  - Score each candidate using your objective.
  - Keep only the top `beam_width` candidates (the new beam).
- Continue until:
  - At least one beam element meets the target, or
  - The maximum depth / number of changes is reached, or
  - No new candidates are generated.

Characteristics:
- Deterministic, as long as scoring is deterministic and ties are handled consistently.
- Breadth-aware: Considers multiple promising directions simultaneously.
- More computationally expensive than greedy, but usually far cheaper than exhaustive search.
- Quality and cost scale with `beam_width`.

When to use beam:
- You want a better trade-off between solution quality and runtime compared to greedy.
- The search space is complex enough that a single greedy path often misses good solutions.
- There are many interacting relaxations where order matters.
- You need determinism for reproducibility but also want some exploration.

Tuning `beam_width`:
- `beam_width = 1`: behaves like greedy.
- `beam_width` around 3-10: good starting range with modest overhead.
- `beam_width > 20`: consider only if the search space is huge and compute is available.

Advantages:
- Often finds better solutions than greedy at the same depth.
- Deterministic and relatively straightforward to reason about.
- Balances exploration (multiple paths) and exploitation (top scoring).

Limitations:
- Runtime grows with `beam_width` and branching factor.
- Still heuristic; no global optimality guarantee unless the beam is extremely wide.
- Requires tuning `beam_width` for your problem scale.

### Monte Carlo Strategy
Identifier: `monte_carlo`

Options:
- `max_runs` (default: 200) - maximum number of random sequences to explore.
- `seed` (optional) - if set, makes sampling and results repeatable.

Core idea: Explore many random sequences of relaxations and keep track of the best outcome.

How it works:
- For each run:
  - Start from the initial configuration.
  - Repeatedly choose a valid relaxation (optionally weighted), apply it, and update the configuration.
  - Stop early if the target is met or the maximum depth is reached.
  - Record the final configuration and its score.
- After `max_runs`, return the best configuration found across all runs.

Characteristics:
- Stochastic: runs can differ unless a `seed` is set.
- Exploratory: samples broadly rather than traversing systematically.
- Flexible: handles large, irregular, or discontinuous search spaces.

When to use monte_carlo:
- The search space is very large or highly non-linear.
- You want broad exploration and can accept stochastic outcomes.
- You want quick "good enough" answers rather than strict optimality.

Tuning `max_runs`:
- 50-100: quick exploratory runs.
- 200 (default): balanced default.
- 500+: use when runs are cheap and you need higher-quality approximations.

Using `seed`:
- Set `seed` for reproducibility in debugging, demos, or regression tests.
- Leave `seed` unset to explore different regions on each run.

Advantages:
- Simple to scale (runs can be parallelized).
- Handles complex constraints and interactions.
- Can discover high-quality solutions missed by structured search.

Limitations:
- No guarantee of global optimality in a finite number of runs.
- Quality depends on `max_runs` and the sampling policy.
- Less predictable convergence quality than deterministic strategies.

### Choosing the Right Strategy

Decision guide:
- Need speed and determinism, search is simple or small? Use `greedy`.
- Want better quality than greedy but still deterministic? Use `beam` with moderate `beam_width` (5-10).
- Search is very large/irregular and exploration matters? Use `monte_carlo` with a reasonable `max_runs` (around 200).

Combined approach:
- Start with `greedy` for a fast baseline.
- Move to `beam` if greedy underperforms.
- Use `monte_carlo` for deeper exploration once you know approximate regions of interest.

### Optimisation Parameters

- `target.candidate_count`: Desired count of passed candidates (can be overridden via CLI/API).
- `strategy.name`: `beam`, `greedy`, or `monte_carlo`.
- `strategy.options`: Strategy-specific options (beam: `beam_width`; monte_carlo: `max_runs`, `seed`).
- `constraints.max_total_changes`: Maximum number of relaxation steps.
- `constraints.allowed_relaxations`: Which relaxation types are allowed.
- `constraints.max_skill_changes`: Cap on total skill edits.
- `constraints.min_years_override`: Range for lowering min years (`min`, `step`).
- `constraints.overall_score_threshold`: Range for lowering threshold (`min`, `step`).
- `constraints.partial_match_weight`: Range for increasing partial weight (`max`, `step`).
- `constraints.must_have_coverage_min`: Range for lowering coverage (`min`, `step`).
- `costs`: Per-relaxation cost used to minimize change.
- `top_k`: Number of results returned by the API.

### Optimisation API

```
POST /api/optimisation
```

Request:
```json
{
  "job_id": 13,
  "optimisation": { ... },
  "candidate_count": 10,
  "top_k": 5
}
```

Response:
```json
{
  "job_id": 13,
  "target": { "candidate_count": 10, "mode": "at_least" },
  "baseline": {
    "candidate_count": 4,
    "summary": { ... }
  },
  "results": [
    {
      "candidate_count": 10,
      "cost": 2,
      "changes": [ ... ],
      "normalized_scenario": { ... },
      "shock_report": { ... },
      "summary": { ... }
    }
  ]
}
```
