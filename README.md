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
