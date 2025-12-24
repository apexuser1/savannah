"""CLI commands for the Resume Job Matcher."""
import json
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
from src.what_if.runner import run_what_if
from src.what_if.scenario import ScenarioValidationError
from src.optimisation.runner import run_optimisation
from src.optimisation.models import OptimisationValidationError

SUPPORTED_FILE_TYPES = {".pdf", ".docx", ".txt", ".md"}


def _coalesce_score(value):
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _find_job_description(job_dir: Path) -> Path:
    candidates = sorted(
        [
            path for path in job_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_FILE_TYPES
        ],
        key=lambda path: path.name.lower()
    )
    if not candidates:
        raise ValueError(f"No job description file found in {job_dir}")
    if len(candidates) > 1:
        names = ", ".join(path.name for path in candidates)
        raise ValueError(f"Multiple job description files found in {job_dir}: {names}")
    return candidates[0]


def _find_application_files(app_dir: Path) -> list[Path]:
    if not app_dir.is_dir():
        raise ValueError(f"Applications folder not found: {app_dir}")
    return sorted(
        [
            path for path in app_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_FILE_TYPES
        ],
        key=lambda path: path.name.lower()
    )


def _create_job_from_file(db, file_path: Path) -> Job:
    parser = JobParser()
    job_data = parser.parse_file(str(file_path))

    basics = job_data.get('basics', {})
    title = basics.get('title', 'Unknown Position')
    company = basics.get('company', 'Unknown Company')
    location_data = basics.get('location', {})
    location = location_data.get('city', '') if location_data else ''

    job = Job(
        job_data=job_data,
        title=title,
        company=company,
        location=location,
        original_filename=file_path.name,
        file_type=file_path.suffix.lower()[1:]
    )

    db.add(job)
    try:
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        raise

    return job


def _create_application_from_file(db, file_path: Path, job: Job):
    parser = ResumeParser()
    resume_data = parser.parse_file(str(file_path))

    basics = resume_data.get('basics', {})
    name = basics.get('name', 'Unknown')
    email = basics.get('email')
    phone = basics.get('phone')

    candidate = Candidate(
        resume_data=resume_data,
        name=name,
        email=email,
        phone=phone,
        original_filename=file_path.name,
        file_type=file_path.suffix.lower()[1:]
    )

    db.add(candidate)
    try:
        db.commit()
        db.refresh(candidate)
    except Exception:
        db.rollback()
        raise

    match_data = match_candidate_to_job(resume_data, job.job_data)

    overall_score = _coalesce_score(match_data.get('overall_score'))
    must_have_score = _coalesce_score(match_data.get('must_have_skills', {}).get('score'))
    nice_to_have_score = _coalesce_score(match_data.get('nice_to_have_skills', {}).get('score'))
    experience_score = _coalesce_score(match_data.get('minimum_years_experience', {}).get('score'))
    education_score = _coalesce_score(match_data.get('required_education', {}).get('score'))

    application = Application(
        candidate_id=candidate.id,
        job_id=job.id,
        match_data=match_data,
        overall_score=overall_score,
        must_have_skills_score=must_have_score,
        nice_to_have_skills_score=nice_to_have_score,
        experience_score=experience_score,
        education_score=education_score
    )

    db.add(application)
    try:
        db.commit()
        db.refresh(application)
    except Exception:
        db.rollback()
        raise

    return candidate, application, match_data


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
@click.argument('directory_path', type=click.Path(exists=True, file_okay=False))
def directory_load(directory_path: str):
    """
    Load job folders and applications from a directory.

    DIRECTORY_PATH: Path containing job directories. Each job folder must include
    one job description file and an applications/ folder with resumes.
    """
    db = None
    errors = []
    total_jobs = 0
    total_applications = 0

    try:
        init_database()
        db = get_db_session()

        base_dir = Path(directory_path)
        if (base_dir / "applications").is_dir():
            job_dirs = [base_dir]
        else:
            job_dirs = sorted(
                [path for path in base_dir.iterdir() if path.is_dir()],
                key=lambda path: path.name.lower()
            )

        if not job_dirs:
            errors.append(f"No job directories found in {base_dir}")
        else:
            for job_dir in job_dirs:
                click.echo(f"\nProcessing job folder: {job_dir.name}")

                try:
                    job_description = _find_job_description(job_dir)
                except Exception as exc:
                    error_msg = f"{job_dir.name}: {exc}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

                try:
                    job = _create_job_from_file(db, job_description)
                    total_jobs += 1
                    click.echo(
                        f"  Job created (ID: {job.id}) from {job_description.name}"
                    )
                except Exception as exc:
                    error_msg = (
                        f"{job_dir.name}: Failed to create job from "
                        f"{job_description.name}: {exc}"
                    )
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

                app_dir = job_dir / "applications"
                try:
                    application_files = _find_application_files(app_dir)
                except Exception as exc:
                    error_msg = f"{job_dir.name}: {exc}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

                if not application_files:
                    error_msg = f"{job_dir.name}: No applications found in {app_dir}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

                for application_file in application_files:
                    click.echo(
                        f"  Processing application: {application_file.name}"
                    )
                    try:
                        candidate, application, _ = _create_application_from_file(
                            db, application_file, job
                        )
                        total_applications += 1
                        click.echo(
                            f"    Application created (ID: {application.id}) "
                            f"Candidate: {candidate.name}"
                        )
                    except Exception as exc:
                        error_msg = (
                            f"{job_dir.name}/{application_file.name}: {exc}"
                        )
                        logger.error(error_msg)
                        errors.append(error_msg)

        click.echo("\nSummary:")
        click.echo(f"jobs: {total_jobs}")
        click.echo(f"applications: {total_applications}")
        if errors:
            click.echo(f"status: errors: {len(errors)}")
            for error in errors:
                click.echo(f"  {error}")
        else:
            click.echo("status: success")

    except click.Abort:
        raise
    except Exception as e:
        logger.error(f"Failed to load directory: {e}")
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise click.Abort()
    finally:
        if db is not None:
            db.close()


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
        
        applications = query.order_by(
            Application.job_id,
            Application.overall_score.desc(),
            Application.created_at.desc()
        ).all()
        
        if not applications:
            click.echo("No applications found.")
            return
        
        # Format as table
        table_data = []
        for app in applications:
            overall_score = _coalesce_score(app.overall_score)
            table_data.append([
                app.job_id,
                f"{overall_score:.1f}",
                app.id,
                app.candidate.name,
                app.job.title,
                app.job.company,
                app.match_data.get('recommendation', 'N/A') if app.match_data else 'N/A',
                app.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        headers = [
            'Job ID',
            'Score',
            'Application ID',
            'Candidate',
            'Job Title',
            'Company',
            'Recommendation',
            'Created'
        ]
        click.echo(f"\nFound {len(applications)} application(s):\n")
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        db.close()
        
    except Exception as e:
        logger.error(f"Failed to list applications: {e}")
        click.echo(click.style(f"✗ Error: {e}", fg="red"))
        raise click.Abort()


@cli.command("what-if")
@click.argument("scenario_text", required=True)
@click.argument("job_id", type=int)
@click.option("--scenario-file", type=click.Path(exists=True), help="Path to a scenario JSON file (skips LLM parsing).")
@click.option("--match-mode", type=click.Choice(["full", "partial"]), help="Use full-only matches or allow partial matches.")
@click.option("--partial-weight", type=float, help="Weight for partial matches when match-mode is partial.")
@click.option("--threshold", type=float, help="Overall score threshold for pass/fail.")
@click.option("--explain", is_flag=True, help="Include per-candidate details in the output.")
@click.option("--summary", is_flag=True, help="Output a summary table instead of JSON details.")
def what_if(scenario_text, job_id, scenario_file, match_mode, partial_weight, threshold, explain, summary):
    """Run a what-if scenario against an existing job."""
    db = None
    try:
        if summary and explain:
            click.echo(click.style("--summary cannot be used with --explain.", fg="red"))
            raise click.Abort()

        init_database()
        db = get_db_session()

        scenario_payload = None
        if scenario_file:
            with open(scenario_file, "r", encoding="utf-8") as handle:
                scenario_payload = json.load(handle)
        elif not scenario_text:
            click.echo(click.style("Scenario text or --scenario-file is required.", fg="red"))
            raise click.Abort()

        overrides = {}
        if match_mode:
            overrides["match_mode"] = match_mode
        if partial_weight is not None:
            overrides["partial_match_weight"] = partial_weight
        if threshold is not None:
            overrides["overall_score_threshold"] = threshold

        result = run_what_if(
            db,
            job_id=job_id,
            scenario_text=None if scenario_payload else scenario_text,
            scenario_payload=scenario_payload,
            overrides=overrides,
            include_details=explain,
            include_summary=summary
        )

        if summary:
            summary_table = result.get("summary_table", [])
            if not summary_table:
                click.echo("No applications found.")
                return

            table_data = []
            for row in summary_table:
                original_score = _coalesce_score(row.get("original_score"))
                scenario_score = _coalesce_score(row.get("scenario_score"))
                table_data.append(
                    [
                        row.get("id"),
                        row.get("candidate"),
                        row.get("job_title"),
                        row.get("company"),
                        row.get("recommendation", "N/A"),
                        row.get("created", ""),
                        f"{original_score:.1f}",
                        f"{scenario_score:.1f}"
                    ]
                )

            headers = [
                "ID",
                "Candidate",
                "Job Title",
                "Company",
                "Recommendation",
                "Created",
                "Original Score",
                "Scenario Score"
            ]
            click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))
            return

        click.echo("Normalized scenario:")
        click.echo(json.dumps(result["normalized_scenario"], indent=2))
        click.echo("\nShock report:")
        click.echo(json.dumps(result["shock_report"], indent=2))

        warnings = result.get("warnings") or []
        if warnings:
            click.echo("\nWarnings:")
            for warning in warnings:
                click.echo(f"- {warning}")

        summary = result.get("summary", {})
        click.echo("\nSummary:")
        click.echo(json.dumps(summary, indent=2))

        if explain:
            click.echo("\nCandidates:")
            click.echo(json.dumps(result.get("candidates", []), indent=2))

    except ScenarioValidationError as exc:
        click.echo(click.style("Scenario validation failed:", fg="red"))
        for error in exc.errors:
            click.echo(click.style(f"- {error}", fg="red"))
        raise click.Abort()
    except Exception as exc:
        logger.error(f"What-if failed: {exc}")
        click.echo(click.style(f"Error: {exc}", fg="red"))
        raise click.Abort()
    finally:
        if db is not None:
            db.close()


@cli.command("optimisation")
@click.argument("job_id", type=int)
@click.option(
    "--optimisation-file",
    required=True,
    type=click.Path(exists=True),
    help="Path to an optimisation JSON file."
)
@click.option(
    "--candidates",
    type=int,
    help="Override the target candidate count."
)
@click.option(
    "--top-k",
    type=int,
    help="Override how many results are produced (API only)."
)
@click.option(
    "--detail",
    is_flag=True,
    help="Include JSON detail output after the summary table."
)
def optimisation(job_id, optimisation_file, candidates, top_k, detail):
    """Run an optimisation search to reach a candidate target."""
    db = None
    try:
        init_database()
        db = get_db_session()

        with open(optimisation_file, "r", encoding="utf-8") as handle:
            optimisation_payload = json.load(handle)

        result = run_optimisation(
            db,
            job_id=job_id,
            optimisation_payload=optimisation_payload,
            candidate_count_override=candidates,
            top_k_override=top_k,
            include_details=True,
            include_summary_table=True,
            include_best_only=True
        )

        results = result.get("results", [])
        if not results:
            click.echo("No optimisation results found.")
            return

        best = results[0]
        summary_table = best.get("summary_table", [])
        if not summary_table:
            click.echo("No applications found.")
            return

        table_data = []
        for row in summary_table:
            original_score = _coalesce_score(row.get("original_score"))
            scenario_score = _coalesce_score(row.get("scenario_score"))
            table_data.append(
                [
                    row.get("id"),
                    row.get("candidate"),
                    row.get("job_title"),
                    row.get("company"),
                    row.get("recommendation", "N/A"),
                    row.get("created", ""),
                    f"{original_score:.1f}",
                    f"{scenario_score:.1f}"
                ]
            )

        headers = [
            "ID",
            "Candidate",
            "Job Title",
            "Company",
            "Recommendation",
            "Created",
            "Original Score",
            "Scenario Score"
        ]
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

        if detail:
            click.echo("\nCandidates:")
            click.echo(json.dumps(best.get("candidates", []), indent=2))

    except OptimisationValidationError as exc:
        click.echo(click.style("Optimisation validation failed:", fg="red"))
        for error in exc.errors:
            click.echo(click.style(f"- {error}", fg="red"))
        raise click.Abort()
    except Exception as exc:
        logger.error(f"Optimisation failed: {exc}")
        click.echo(click.style(f"Error: {exc}", fg="red"))
        raise click.Abort()
    finally:
        if db is not None:
            db.close()


if __name__ == '__main__':
    cli()
