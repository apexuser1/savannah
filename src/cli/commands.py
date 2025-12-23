"""CLI commands for the Resume Job Matcher."""
import click
from datetime import datetime
from pathlib import Path
from loguru import logger
from tabulate import tabulate

from src.database.connection import init_db as init_database, get_db_session
from src.database.models import Candidate, Job, Application
from src.parsers.resume_parser import ResumeParser
from src.parsers.job_parser import JobParser
from src.matching.matcher import match_candidate_to_job


def _coalesce_score(value):
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


@click.group()
def cli():
    """Resume Job Matcher - CLI for managing resumes, jobs, and applications."""
    pass


@cli.command()
def init_db():
    """Initialize the database and create tables."""
    try:
        init_database()
        click.echo(click.style("✓ Database initialized successfully!", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Failed to initialize database: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.argument('job_id', type=int)
def upload_resume(file_path: str, job_id: int):
    """
    Upload and parse a resume, create application, and trigger matching.
    
    FILE_PATH: Path to the resume file (PDF, DOCX, TXT, or MD)
    JOB_ID: ID of the job to apply to
    """
    try:
        # Initialize database
        init_database()
        db = get_db_session()
        
        # Check if job exists
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            click.echo(click.style(f"✗ Job with ID {job_id} not found", fg="red"))
            raise click.Abort()
        
        click.echo(f"Parsing resume: {file_path}")
        
        # Parse resume
        parser = ResumeParser()
        resume_data = parser.parse_file(file_path)
        
        # Extract basic info for quick access
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
            original_filename=Path(file_path).name,
            file_type=Path(file_path).suffix.lower()[1:]  # Remove the dot
        )
        
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
        
        click.echo(click.style(f"✓ Candidate created (ID: {candidate.id})", fg="green"))
        click.echo(f"  Name: {name}")
        click.echo(f"  Email: {email}")
        
        # Perform matching
        click.echo("\nMatching candidate to job...")
        match_data = match_candidate_to_job(resume_data, job.job_data)

        overall_score = _coalesce_score(match_data.get('overall_score'))
        must_have_score = _coalesce_score(match_data.get('must_have_skills', {}).get('score'))
        nice_to_have_score = _coalesce_score(match_data.get('nice_to_have_skills', {}).get('score'))
        experience_score = _coalesce_score(match_data.get('minimum_years_experience', {}).get('score'))
        education_score = _coalesce_score(match_data.get('required_education', {}).get('score'))
        
        # Create application
        application = Application(
            candidate_id=candidate.id,
            job_id=job_id,
            match_data=match_data,
            overall_score=overall_score,
            must_have_skills_score=must_have_score,
            nice_to_have_skills_score=nice_to_have_score,
            experience_score=experience_score,
            education_score=education_score
        )
        
        db.add(application)
        db.commit()
        db.refresh(application)
        
        click.echo(click.style(f"\n✓ Application created (ID: {application.id})", fg="green"))
        click.echo(f"\nMatch Scores:")
        click.echo(f"  Overall Score: {overall_score:.1f}/100")
        click.echo(f"  Must-Have Skills: {must_have_score:.1f}/100")
        click.echo(f"  Nice-to-Have Skills: {nice_to_have_score:.1f}/100")
        click.echo(f"  Experience: {experience_score:.1f}/100")
        click.echo(f"  Education: {education_score:.1f}/100")
        click.echo(f"\nRecommendation: {match_data.get('recommendation', 'N/A')}")
        click.echo(f"\nSummary: {match_data.get('summary', 'N/A')}")
        click.echo(f"\nmust_have_skills: {match_data.get('must_have_skills', {}).get('analysis', 'N/A')}")
        click.echo(f"\nnice_to_have_skills: {match_data.get('nice_to_have_skills', {}).get('analysis', 'N/A')}")
        click.echo(
            f"\nminimum_years_experience: "
            f"{match_data.get('minimum_years_experience', {}).get('analysis', 'N/A')}"
        )
        click.echo(
            f"\nrequired_education: "
            f"{match_data.get('required_education', {}).get('analysis', 'N/A')}"
        )
        
        db.close()
        
    except Exception as e:
        logger.error(f"Failed to upload resume: {e}")
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
def upload_job(file_path: str):
    """
    Upload and parse a job description.
    
    FILE_PATH: Path to the job description file (PDF, DOCX, TXT, or MD)
    """
    try:
        # Initialize database
        init_database()
        db = get_db_session()
        
        click.echo(f"Parsing job description: {file_path}")
        
        # Parse job description
        parser = JobParser()
        job_data = parser.parse_file(file_path)
        
        # Extract basic info for quick access
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
            original_filename=Path(file_path).name,
            file_type=Path(file_path).suffix.lower()[1:]  # Remove the dot
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        click.echo(click.style(f"\n✓ Job created (ID: {job.id})", fg="green"))
        click.echo(f"  Title: {title}")
        click.echo(f"  Company: {company}")
        click.echo(f"  Location: {location}")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Failed to upload job: {e}")
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.option('--since', type=str, help='Filter jobs created since date (YYYY-MM-DD)')
def list_jobs(since: str):
    """List all jobs with optional date filter."""
    try:
        init_database()
        db = get_db_session()
        
        # Build query
        query = db.query(Job)
        
        if since:
            try:
                since_date = datetime.strptime(since, '%Y-%m-%d')
                query = query.filter(Job.created_at >= since_date)
            except ValueError:
                click.echo(click.style("✗ Invalid date format. Use YYYY-MM-DD", fg="red"))
                raise click.Abort()
        
        jobs = query.order_by(Job.created_at.desc()).all()
        
        if not jobs:
            click.echo("No jobs found.")
            return
        
        # Format as table
        table_data = []
        for job in jobs:
            table_data.append([
                job.id,
                job.title,
                job.company,
                job.location or 'N/A',
                job.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        headers = ['ID', 'Title', 'Company', 'Location', 'Created']
        click.echo(f"\nFound {len(jobs)} job(s):\n")
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        db.close()
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.option('--since', type=str, help='Filter candidates created since date (YYYY-MM-DD)')
def list_candidates(since: str):
    """List all candidates with optional date filter."""
    try:
        init_database()
        db = get_db_session()
        
        # Build query
        query = db.query(Candidate)
        
        if since:
            try:
                since_date = datetime.strptime(since, '%Y-%m-%d')
                query = query.filter(Candidate.created_at >= since_date)
            except ValueError:
                click.echo(click.style("✗ Invalid date format. Use YYYY-MM-DD", fg="red"))
                raise click.Abort()
        
        candidates = query.order_by(Candidate.created_at.desc()).all()
        
        if not candidates:
            click.echo("No candidates found.")
            return
        
        # Format as table
        table_data = []
        for candidate in candidates:
            table_data.append([
                candidate.id,
                candidate.name,
                candidate.email or 'N/A',
                candidate.phone or 'N/A',
                candidate.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        headers = ['ID', 'Name', 'Email', 'Phone', 'Created']
        click.echo(f"\nFound {len(candidates)} candidate(s):\n")
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        db.close()
        
    except Exception as e:
        logger.error(f"Failed to list candidates: {e}")
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.option('--since', type=str, help='Filter applications created since date (YYYY-MM-DD)')
@click.option('--min-score', type=float, help='Filter by minimum overall score (0-100)')
def list_applications(since: str, min_score: float):
    """List applications with optional filters."""
    try:
        init_database()
        db = get_db_session()
        
        # Build query
        query = db.query(Application).join(Candidate).join(Job)
        
        if since:
            try:
                since_date = datetime.strptime(since, '%Y-%m-%d')
                query = query.filter(Application.created_at >= since_date)
            except ValueError:
                click.echo(click.style("✗ Invalid date format. Use YYYY-MM-DD", fg="red"))
                raise click.Abort()
        
        if min_score is not None:
            query = query.filter(Application.overall_score >= min_score)
        
        applications = query.order_by(Application.created_at.desc()).all()
        
        if not applications:
            click.echo("No applications found.")
            return
        
        # Format as table
        table_data = []
        for app in applications:
            overall_score = _coalesce_score(app.overall_score)
            table_data.append([
                app.id,
                app.candidate.name,
                app.job.title,
                app.job.company,
                f"{overall_score:.1f}",
                app.match_data.get('recommendation', 'N/A') if app.match_data else 'N/A',
                app.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        headers = ['ID', 'Candidate', 'Job Title', 'Company', 'Score', 'Recommendation', 'Created']
        click.echo(f"\nFound {len(applications)} application(s):\n")
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        db.close()
        
    except Exception as e:
        logger.error(f"Failed to list applications: {e}")
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        raise click.Abort()


if __name__ == '__main__':
    cli()
