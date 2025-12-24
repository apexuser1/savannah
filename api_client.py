#!/usr/bin/env python3
"""API client entry point for the Resume Job Matcher."""
import json
import os
from datetime import datetime
from pathlib import Path

import click
import httpx
from dotenv import load_dotenv
from tabulate import tabulate


SUPPORTED_FILE_TYPES = {".pdf", ".docx", ".txt", ".md"}

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


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


def _request_json(response: httpx.Response) -> dict:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip() or "Unknown error"
        raise RuntimeError(f"API request failed ({exc.response.status_code}): {detail}") from exc
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("API response is not valid JSON") from exc


def _upload_job(client: httpx.Client, file_path: Path) -> dict:
    with file_path.open("rb") as file_handle:
        response = client.post(
            "/api/jobs/upload",
            files={"file": (file_path.name, file_handle)}
        )
    return _request_json(response)


def _upload_resume(client: httpx.Client, file_path: Path, job_id: int) -> dict:
    with file_path.open("rb") as file_handle:
        response = client.post(
            "/api/resumes/upload",
            params={"job_id": job_id},
            files={"file": (file_path.name, file_handle)}
        )
    return _request_json(response)


@click.group()
def cli():
    """API client for the Resume Job Matcher."""
    pass


@cli.command()
def init_db():
    """Validate API connectivity and database readiness."""
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=10.0) as client:
            response = client.get("/health")
        data = _request_json(response)
        status = data.get("status", "unknown")
        click.echo(f"API health: {status}")
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
def upload_job(file_path: str):
    """
    Upload and parse a job description.

    FILE_PATH: Path to the job description file (PDF, DOCX, TXT, or MD)
    """
    try:
        path = Path(file_path)
        with httpx.Client(base_url=API_BASE_URL, timeout=60.0) as client:
            job = _upload_job(client, path)

        click.echo(f"\nJob created (ID: {job.get('id')})")
        click.echo(f"  Title: {job.get('title', 'Unknown Position')}")
        click.echo(f"  Company: {job.get('company', 'Unknown Company')}")
        click.echo(f"  Location: {job.get('location') or 'N/A'}")

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
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
        path = Path(file_path)
        with httpx.Client(base_url=API_BASE_URL, timeout=120.0) as client:
            response = _upload_resume(client, path, job_id)

        candidate = response.get("candidate", {})
        application = response.get("application", {})
        match_data = application.get("match_data") or {}

        click.echo(f"\nCandidate created (ID: {candidate.get('id')})")
        click.echo(f"  Name: {candidate.get('name', 'Unknown')}")
        click.echo(f"  Email: {candidate.get('email')}")

        overall_score = _coalesce_score(application.get("overall_score"))
        must_have_score = _coalesce_score(application.get("must_have_skills_score"))
        nice_to_have_score = _coalesce_score(application.get("nice_to_have_skills_score"))
        experience_score = _coalesce_score(application.get("experience_score"))
        education_score = _coalesce_score(application.get("education_score"))

        click.echo(f"\nApplication created (ID: {application.get('id')})")
        click.echo(f"\nMatch Scores:")
        click.echo(f"  Overall Score: {overall_score:.1f}/100")
        click.echo(f"  Must-Have Skills: {must_have_score:.1f}/100")
        click.echo(f"  Nice-to-Have Skills: {nice_to_have_score:.1f}/100")
        click.echo(f"  Experience: {experience_score:.1f}/100")
        click.echo(f"  Education: {education_score:.1f}/100")
        click.echo(f"\nRecommendation: {match_data.get('recommendation', 'N/A')}")
        click.echo(f"\nSummary: {match_data.get('summary', 'N/A')}")
        click.echo(
            f"\nmust_have_skills: {match_data.get('must_have_skills', {}).get('analysis', 'N/A')}"
        )
        click.echo(
            f"\nnice_to_have_skills: {match_data.get('nice_to_have_skills', {}).get('analysis', 'N/A')}"
        )
        click.echo(
            f"\nminimum_years_experience: "
            f"{match_data.get('minimum_years_experience', {}).get('analysis', 'N/A')}"
        )
        click.echo(
            f"\nrequired_education: "
            f"{match_data.get('required_education', {}).get('analysis', 'N/A')}"
        )

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise click.Abort()


@cli.command("what-if")
@click.argument("scenario_text", required=True)
@click.argument("job_id", type=int)
@click.option("--scenario-file", type=click.Path(exists=True), help="Path to a scenario JSON file.")
@click.option("--match-mode", type=click.Choice(["full", "partial"]))
@click.option("--partial-weight", type=float)
@click.option("--threshold", type=float)
@click.option("--explain", is_flag=True, help="Include per-candidate details in the output.")
@click.option("--summary", is_flag=True, help="Output a summary table instead of JSON details.")
def what_if(scenario_text, job_id, scenario_file, match_mode, partial_weight, threshold, explain, summary):
    """Run a what-if scenario against a job."""
    if summary and explain:
        click.echo(click.style("--summary cannot be used with --explain.", fg="red"))
        raise click.Abort()

    payload = {
        "job_id": job_id,
        "include_details": explain,
        "summary": summary
    }

    if scenario_file:
        with open(scenario_file, "r", encoding="utf-8") as handle:
            payload["scenario"] = json.load(handle)
    else:
        payload["scenario_text"] = scenario_text

    if match_mode:
        payload["match_mode"] = match_mode
    if partial_weight is not None:
        payload["partial_match_weight"] = partial_weight
    if threshold is not None:
        payload["overall_score_threshold"] = threshold

    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=60.0) as client:
            response = client.post("/api/what-if", json=payload)
        result = _request_json(response)

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
        click.echo(json.dumps(result.get("normalized_scenario"), indent=2))
        click.echo("\nShock report:")
        click.echo(json.dumps(result.get("shock_report"), indent=2))

        warnings = result.get("warnings") or []
        if warnings:
            click.echo("\nWarnings:")
            for warning in warnings:
                click.echo(f"- {warning}")

        click.echo("\nSummary:")
        click.echo(json.dumps(result.get("summary", {}), indent=2))

        if explain:
            click.echo("\nCandidates:")
            click.echo(json.dumps(result.get("candidates", []), indent=2))

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise click.Abort()


@cli.command("optimisation")
@click.argument("job_id", type=int)
@click.option("--optimisation-file", required=True, type=click.Path(exists=True))
@click.option("--candidates", type=int, help="Override the target candidate count.")
@click.option("--top-k", type=int, help="Override how many results are returned.")
def optimisation(job_id, optimisation_file, candidates, top_k):
    """Run an optimisation search against a job."""
    payload = {"job_id": job_id}
    try:
        with open(optimisation_file, "r", encoding="utf-8") as handle:
            payload["optimisation"] = json.load(handle)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise click.Abort()

    if candidates is not None:
        payload["candidate_count"] = candidates
    if top_k is not None:
        payload["top_k"] = top_k

    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=60.0) as client:
            response = client.post("/api/optimisation", json=payload)
        result = _request_json(response)
        click.echo(json.dumps(result, indent=2))
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.option('--since', type=str, help='Filter jobs created since date (YYYY-MM-DD)')
def list_jobs(since: str):
    """List all jobs with optional date filter."""
    try:
        params = {}
        if since:
            params["since"] = since
        with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
            response = client.get("/api/jobs", params=params)
        jobs = _request_json(response)

        if not jobs:
            click.echo("No jobs found.")
            return

        table_data = []
        for job in jobs:
            created_at = job.get("created_at")
            if created_at:
                try:
                    created_at = datetime.fromisoformat(created_at)
                    created_display = created_at.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    created_display = created_at
            else:
                created_display = "N/A"
            table_data.append([
                job.get("id"),
                job.get("title"),
                job.get("company"),
                job.get("location") or "N/A",
                created_display
            ])

        headers = ['ID', 'Title', 'Company', 'Location', 'Created']
        click.echo(f"\nFound {len(jobs)} job(s):\n")
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.option('--since', type=str, help='Filter candidates created since date (YYYY-MM-DD)')
def list_candidates(since: str):
    """List all candidates with optional date filter."""
    try:
        params = {}
        if since:
            params["since"] = since
        with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
            response = client.get("/api/candidates", params=params)
        candidates = _request_json(response)

        if not candidates:
            click.echo("No candidates found.")
            return

        table_data = []
        for candidate in candidates:
            created_at = candidate.get("created_at")
            if created_at:
                try:
                    created_at = datetime.fromisoformat(created_at)
                    created_display = created_at.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    created_display = created_at
            else:
                created_display = "N/A"
            table_data.append([
                candidate.get("id"),
                candidate.get("name"),
                candidate.get("email") or "N/A",
                candidate.get("phone") or "N/A",
                created_display
            ])

        headers = ['ID', 'Name', 'Email', 'Phone', 'Created']
        click.echo(f"\nFound {len(candidates)} candidate(s):\n")
        click.echo(tabulate(table_data, headers=headers, tablefmt='grid'))

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.option('--since', type=str, help='Filter applications created since date (YYYY-MM-DD)')
@click.option('--min-score', type=float, help='Filter by minimum overall score (0-100)')
def list_applications(since: str, min_score: float):
    """List applications with optional filters."""
    try:
        params = {}
        if since:
            params["since"] = since
        if min_score is not None:
            params["min_score"] = min_score
        with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
            response = client.get("/api/applications", params=params)
        applications = _request_json(response)

        if not applications:
            click.echo("No applications found.")
            return

        table_data = []
        for app in applications:
            overall_score = _coalesce_score(app.get("overall_score"))
            created_at = app.get("created_at")
            if created_at:
                try:
                    created_at = datetime.fromisoformat(created_at)
                    created_display = created_at.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    created_display = created_at
            else:
                created_display = "N/A"
            recommendation = "N/A"
            match_data = app.get("match_data") or {}
            if isinstance(match_data, dict):
                recommendation = match_data.get("recommendation", "N/A")
            table_data.append([
                app.get("job_id"),
                f"{overall_score:.1f}",
                app.get("id"),
                app.get("candidate", {}).get("name") or app.get("candidate_id"),
                app.get("job", {}).get("title") or app.get("job_id"),
                app.get("job", {}).get("company") or "N/A",
                recommendation,
                created_display
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

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise click.Abort()


@cli.command()
@click.argument('directory_path', type=click.Path(exists=True, file_okay=False))
def directory_load(directory_path: str):
    """
    Load job folders and applications from a directory.

    DIRECTORY_PATH: Path containing job directories. Each job folder must include
    one job description file and an applications/ folder with resumes.
    """
    errors = []
    total_jobs = 0
    total_applications = 0

    try:
        base_dir = Path(directory_path)
        job_dirs = sorted(
            [path for path in base_dir.iterdir() if path.is_dir()],
            key=lambda path: path.name.lower()
        )

        if not job_dirs:
            errors.append(f"No job directories found in {base_dir}")
        else:
            with httpx.Client(base_url=API_BASE_URL, timeout=120.0) as client:
                for job_dir in job_dirs:
                    click.echo(f"\nProcessing job folder: {job_dir.name}")

                    try:
                        job_description = _find_job_description(job_dir)
                    except Exception as exc:
                        error_msg = f"{job_dir.name}: {exc}"
                        errors.append(error_msg)
                        continue

                    try:
                        job = _upload_job(client, job_description)
                        job_id = job.get("id")
                        total_jobs += 1
                        click.echo(
                            f"  Job created (ID: {job_id}) from {job_description.name}"
                        )
                    except Exception as exc:
                        error_msg = (
                            f"{job_dir.name}: Failed to upload job from "
                            f"{job_description.name}: {exc}"
                        )
                        errors.append(error_msg)
                        continue

                    app_dir = job_dir / "applications"
                    try:
                        application_files = _find_application_files(app_dir)
                    except Exception as exc:
                        error_msg = f"{job_dir.name}: {exc}"
                        errors.append(error_msg)
                        continue

                    if not application_files:
                        error_msg = f"{job_dir.name}: No applications found in {app_dir}"
                        errors.append(error_msg)
                        continue

                    for application_file in application_files:
                        click.echo(
                            f"  Processing application: {application_file.name}"
                        )
                        try:
                            response = _upload_resume(
                                client, application_file, job_id
                            )
                            application = response.get("application", {})
                            candidate = response.get("candidate", {})
                            total_applications += 1
                            click.echo(
                                f"    Application created (ID: {application.get('id')}) "
                                f"Candidate: {candidate.get('name', 'Unknown')}"
                            )
                        except Exception as exc:
                            error_msg = (
                                f"{job_dir.name}/{application_file.name}: {exc}"
                            )
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

    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        raise click.Abort()


if __name__ == '__main__':
    cli()
