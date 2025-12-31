"""FastAPI application for the Resume Job Matcher."""
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, cast
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from loguru import logger

from src.database.connection import get_db, init_db
from src.database.models import (
    Candidate,
    Job,
    Application,
    WhatIfScenario,
    OptimisationRecord
)
from src.parsers.resume_parser import ResumeParser
from src.parsers.job_parser import JobParser
from src.matching.matcher import match_candidate_to_job
from src.what_if.runner import run_what_if
from src.what_if.scenario import ScenarioValidationError, normalize_scenario
from src.optimisation.runner import run_optimisation
from src.optimisation.models import OptimisationValidationError, load_optimisation_config
from src.optimisation.api_models import OptimisationRequest


# Initialize database on startup
init_db()

# Create FastAPI app
app = FastAPI(
    title="Resume Job Matcher API",
    description="API for matching candidate resumes to job descriptions",
    version="1.0.0"
)

# Allow the UI to call the API during prototyping.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Pydantic models for responses
class CandidateResponse(BaseModel):
    id: int
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    original_filename: Optional[str]
    file_type: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CandidateDetailResponse(BaseModel):
    id: int
    resume_data: dict
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    original_filename: Optional[str]
    file_type: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    id: int
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    original_filename: Optional[str]
    file_type: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class JobDetailResponse(BaseModel):
    id: int
    job_data: dict
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    original_filename: Optional[str]
    file_type: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicationResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    overall_score: Optional[float]
    must_have_skills_score: Optional[float]
    nice_to_have_skills_score: Optional[float]
    experience_score: Optional[float]
    education_score: Optional[float]
    match_data: Optional[dict]
    created_at: datetime
    candidate: Optional[CandidateResponse]
    job: Optional[JobResponse]
    
    class Config:
        from_attributes = True


class UploadResumeResponse(BaseModel):
    candidate: CandidateResponse
    application: ApplicationResponse
    message: str


class WhatIfRequest(BaseModel):
    job_id: int
    scenario_text: Optional[str] = None
    scenario: Optional[dict] = None
    match_mode: Optional[str] = None
    partial_match_weight: Optional[float] = None
    overall_score_threshold: Optional[float] = None
    include_details: Optional[bool] = False
    summary: Optional[bool] = False


class WhatIfScenarioCreateRequest(BaseModel):
    job_id: int
    name: Optional[str] = None
    scenario: dict


class WhatIfScenarioResponse(BaseModel):
    id: int
    job_id: int
    name: Optional[str]
    scenario_payload: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OptimisationCreateRequest(BaseModel):
    job_id: int
    name: Optional[str] = None
    optimisation: dict


class OptimisationRecordResponse(BaseModel):
    id: int
    job_id: int
    name: Optional[str]
    optimisation_payload: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# API Endpoints

@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Resume Job Matcher API",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/resumes/upload": "Upload resume with job_id",
            "POST /api/jobs/upload": "Upload job description",
            "GET /api/jobs": "List jobs",
            "GET /api/jobs/{job_id}": "Get job details",
            "GET /api/candidates": "List candidates",
            "GET /api/candidates/{candidate_id}": "Get candidate details",
            "GET /api/applications": "List applications",
            "GET /api/applications/{application_id}": "Get application details",
            "POST /api/what-if": "Run a what-if scenario",
            "GET /api/what-if/scenarios": "List stored what-if scenarios",
            "POST /api/what-if/scenarios": "Store a what-if scenario",
            "POST /api/optimisation": "Run an optimisation search",
            "GET /api/optimisations": "List stored optimisation configs",
            "POST /api/optimisations": "Store an optimisation config"
        }
    }


@app.post("/api/resumes/upload", response_model=UploadResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    job_id: int = Query(..., description="ID of the job to apply to"),
    db: Session = Depends(get_db)
):
    """
    Upload and parse a resume, create application, and trigger matching.
    
    Returns candidate and application with match scores.
    """
    try:
        # Check if job exists
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
        
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="Uploaded file must have a filename")
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ['.pdf', '.docx', '.txt', '.md']:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Supported types: PDF, DOCX, TXT, MD"
            )
        
        logger.info(f"Uploading resume: {file.filename}")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Parse resume
            parser = ResumeParser()
            resume_data = parser.parse_file(tmp_file_path)
            
            # Extract basic info
            basics = resume_data.get('basics', {})
            name = basics.get('name', 'Unknown')
            email = basics.get('email')
            phone = basics.get('phone')
            
            # Create candidate
            candidate = Candidate(
                resume_data=resume_data,
                name=name,
                email=email,
                phone=phone,
                original_filename=file.filename,
                file_type=file_extension[1:]  # Remove the dot
            )
            
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
            
            logger.info(f"Candidate created (ID: {candidate.id})")
            
            # Perform matching
            logger.info("Matching candidate to job...")
            job_data = cast(Dict[str, Any], job.job_data)
            match_data = match_candidate_to_job(resume_data, job_data)
            
            # Create application
            application = Application(
                candidate_id=candidate.id,
                job_id=job_id,
                match_data=match_data,
                overall_score=match_data.get('overall_score', 0),
                must_have_skills_score=match_data.get('must_have_skills', {}).get('score', 0),
                nice_to_have_skills_score=match_data.get('nice_to_have_skills', {}).get('score', 0),
                experience_score=match_data.get('minimum_years_experience', {}).get('score', 0),
                education_score=match_data.get('required_education', {}).get('score', 0)
            )
            
            db.add(application)
            db.commit()
            db.refresh(application)
            
            logger.info(f"Application created (ID: {application.id}, Score: {application.overall_score})")
            
            # Load relationships for response
            application.candidate = candidate
            application.job = job
            
            return UploadResumeResponse(
                candidate=CandidateResponse.from_orm(candidate),
                application=ApplicationResponse.from_orm(application),
                message="Resume uploaded and matched successfully"
            )
        
        finally:
            # Clean up temporary file
            Path(tmp_file_path).unlink(missing_ok=True)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/jobs/upload", response_model=JobResponse)
async def upload_job(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and parse a job description."""
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="Uploaded file must have a filename")
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ['.pdf', '.docx', '.txt', '.md']:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Supported types: PDF, DOCX, TXT, MD"
            )
        
        logger.info(f"Uploading job description: {file.filename}")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Parse job description
            parser = JobParser()
            job_data = parser.parse_file(tmp_file_path)
            
            # Extract basic info
            basics = job_data.get('basics', {})
            title = basics.get('title', 'Unknown Position')
            company = basics.get('company', 'Unknown Company')
            location_data = basics.get('location', {})
            location = location_data.get('city', '') if location_data else ''
            
            # Create job
            job = Job(
                job_data=job_data,
                title=title,
                company=company,
                location=location,
                original_filename=file.filename,
                file_type=file_extension[1:]  # Remove the dot
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            logger.info(f"Job created (ID: {job.id})")
            
            return JobResponse.from_orm(job)
        
        finally:
            # Clean up temporary file
            Path(tmp_file_path).unlink(missing_ok=True)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs", response_model=List[JobResponse])
def list_jobs(
    since: Optional[str] = Query(None, description="Filter jobs created since date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """List all jobs with optional date filter."""
    try:
        # Build query
        query = db.query(Job)
        
        if since:
            try:
                since_date = datetime.strptime(since, '%Y-%m-%d')
                query = query.filter(Job.created_at >= since_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        jobs = query.order_by(Job.created_at.desc()).all()
        
        return [JobResponse.from_orm(job) for job in jobs]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """Get a job with full structured data."""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with ID {job_id} not found")
        return JobDetailResponse.from_orm(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/candidates", response_model=List[CandidateResponse])
def list_candidates(
    since: Optional[str] = Query(None, description="Filter candidates created since date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """List all candidates with optional date filter."""
    try:
        # Build query
        query = db.query(Candidate)
        
        if since:
            try:
                since_date = datetime.strptime(since, '%Y-%m-%d')
                query = query.filter(Candidate.created_at >= since_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        candidates = query.order_by(Candidate.created_at.desc()).all()
        
        return [CandidateResponse.from_orm(candidate) for candidate in candidates]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/candidates/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db)
):
    """Get a candidate with full resume data."""
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            raise HTTPException(
                status_code=404,
                detail=f"Candidate with ID {candidate_id} not found"
            )
        return CandidateDetailResponse.from_orm(candidate)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch candidate {candidate_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/applications", response_model=List[ApplicationResponse])
def list_applications(
    since: Optional[str] = Query(None, description="Filter applications created since date (YYYY-MM-DD)"),
    min_score: Optional[float] = Query(None, description="Filter by minimum overall score (0-100)", ge=0, le=100),
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    db: Session = Depends(get_db)
):
    """List applications with optional filters."""
    try:
        # Build query
        query = db.query(Application)
        
        if since:
            try:
                since_date = datetime.strptime(since, '%Y-%m-%d')
                query = query.filter(Application.created_at >= since_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        if min_score is not None:
            query = query.filter(Application.overall_score >= min_score)
        if job_id is not None:
            query = query.filter(Application.job_id == job_id)
        
        applications = query.order_by(
            Application.job_id,
            Application.overall_score.desc(),
            Application.created_at.desc()
        ).all()
        
        return [ApplicationResponse.from_orm(app) for app in applications]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list applications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/applications/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db)
):
    """Get an application with match data."""
    try:
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            raise HTTPException(
                status_code=404,
                detail=f"Application with ID {application_id} not found"
            )
        return ApplicationResponse.from_orm(application)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch application {application_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/what-if/scenarios", response_model=List[WhatIfScenarioResponse])
def list_what_if_scenarios(
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    db: Session = Depends(get_db)
):
    """List stored what-if scenarios."""
    try:
        query = db.query(WhatIfScenario)
        if job_id is not None:
            query = query.filter(WhatIfScenario.job_id == job_id)
        scenarios = query.order_by(WhatIfScenario.created_at.desc()).all()
        return [WhatIfScenarioResponse.from_orm(item) for item in scenarios]
    except Exception as e:
        logger.error(f"Failed to list what-if scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/what-if/scenarios/{scenario_id}", response_model=WhatIfScenarioResponse)
def get_what_if_scenario(
    scenario_id: int,
    db: Session = Depends(get_db)
):
    """Get a stored what-if scenario."""
    try:
        scenario = db.query(WhatIfScenario).filter(WhatIfScenario.id == scenario_id).first()
        if not scenario:
            raise HTTPException(
                status_code=404,
                detail=f"What-if scenario {scenario_id} not found"
            )
        return WhatIfScenarioResponse.from_orm(scenario)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch what-if scenario {scenario_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/what-if/scenarios", response_model=WhatIfScenarioResponse)
def create_what_if_scenario(
    payload: WhatIfScenarioCreateRequest,
    db: Session = Depends(get_db)
):
    """Store a validated what-if scenario."""
    try:
        job = db.query(Job).filter(Job.id == payload.job_id).first()
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID {payload.job_id} not found"
            )

        try:
            normalized, _warnings = normalize_scenario(
                payload.scenario,
                job.job_data,
                strict=True
            )
        except ScenarioValidationError as exc:
            raise HTTPException(status_code=422, detail={"errors": exc.errors})

        record = WhatIfScenario(
            job_id=payload.job_id,
            name=payload.name,
            scenario_payload=normalized
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return WhatIfScenarioResponse.from_orm(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store what-if scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/optimisations", response_model=List[OptimisationRecordResponse])
def list_optimisations(
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    db: Session = Depends(get_db)
):
    """List stored optimisation configs."""
    try:
        query = db.query(OptimisationRecord)
        if job_id is not None:
            query = query.filter(OptimisationRecord.job_id == job_id)
        records = query.order_by(OptimisationRecord.created_at.desc()).all()
        return [OptimisationRecordResponse.from_orm(item) for item in records]
    except Exception as e:
        logger.error(f"Failed to list optimisations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/optimisations/{optimisation_id}", response_model=OptimisationRecordResponse)
def get_optimisation(
    optimisation_id: int,
    db: Session = Depends(get_db)
):
    """Get a stored optimisation config."""
    try:
        record = (
            db.query(OptimisationRecord)
            .filter(OptimisationRecord.id == optimisation_id)
            .first()
        )
        if not record:
            raise HTTPException(
                status_code=404,
                detail=f"Optimisation {optimisation_id} not found"
            )
        return OptimisationRecordResponse.from_orm(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch optimisation {optimisation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/optimisations", response_model=OptimisationRecordResponse)
def create_optimisation(
    payload: OptimisationCreateRequest,
    db: Session = Depends(get_db)
):
    """Store a validated optimisation config."""
    try:
        job = db.query(Job).filter(Job.id == payload.job_id).first()
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job with ID {payload.job_id} not found"
            )

        try:
            load_optimisation_config(payload.optimisation)
        except OptimisationValidationError as exc:
            raise HTTPException(status_code=422, detail={"errors": exc.errors})

        record = OptimisationRecord(
            job_id=payload.job_id,
            name=payload.name,
            optimisation_payload=payload.optimisation
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return OptimisationRecordResponse.from_orm(record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store optimisation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/what-if")
def run_what_if_scenario(
    payload: WhatIfRequest,
    db: Session = Depends(get_db)
):
    """Run a what-if scenario against a job."""
    if not payload.scenario_text and payload.scenario is None:
        raise HTTPException(
            status_code=400,
            detail="Provide scenario_text or scenario."
        )
    if payload.summary and payload.include_details:
        raise HTTPException(
            status_code=400,
            detail="summary cannot be used with include_details."
        )

    overrides = {}
    if payload.match_mode:
        overrides["match_mode"] = payload.match_mode
    if payload.partial_match_weight is not None:
        overrides["partial_match_weight"] = payload.partial_match_weight
    if payload.overall_score_threshold is not None:
        overrides["overall_score_threshold"] = payload.overall_score_threshold

    try:
        result = run_what_if(
            db,
            job_id=payload.job_id,
            scenario_text=payload.scenario_text,
            scenario_payload=payload.scenario,
            overrides=overrides,
            include_details=bool(payload.include_details),
            include_summary=bool(payload.summary)
        )
    except ScenarioValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"errors": exc.errors}
        )

    return JSONResponse(content=result)


@app.post("/api/optimisation")
def run_optimisation_search(
    payload: OptimisationRequest,
    db: Session = Depends(get_db)
):
    """Run an optimisation search against a job."""
    try:
        include_details = bool(payload.include_details)
        include_summary = bool(payload.summary)
        include_best_only = True if payload.best_only is None else bool(payload.best_only)

        result = run_optimisation(
            db,
            job_id=payload.job_id,
            optimisation_payload=payload.optimisation,
            candidate_count_override=payload.candidate_count,
            top_k_override=payload.top_k,
            include_details=include_details,
            include_summary_table=include_summary,
            include_best_only=include_best_only
        )
    except OptimisationValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"errors": exc.errors}
        )

    return JSONResponse(content=result)


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Resume Job Matcher API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
