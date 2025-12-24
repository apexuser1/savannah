from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.connection import Base
from src.database.models import Job, Candidate, Application
from src.what_if.runner import run_what_if
from src.what_if.scenario import DEFAULT_SCENARIO

from tests.conftest import deep_copy, make_job_data, make_match_data, make_resume_data


def test_run_what_if_returns_summary_table():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        job_data = make_job_data()
        job = Job(
            job_data=job_data,
            title="DevOps",
            company="CloudScale",
            location="Remote",
            original_filename="job.txt",
            file_type="txt"
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        resume_data = make_resume_data()
        candidate = Candidate(
            resume_data=resume_data,
            name="Alex",
            email="alex@example.com",
            phone="555-0100",
            original_filename="resume.txt",
            file_type="txt"
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        match_data = make_match_data(
            must_full=["Skill A"],
            must_partial=["Skill B"],
            must_missing=["Skill C", "Skill D"],
            nice_full=[],
            nice_partial=[],
            nice_missing=["Skill E", "Skill F"]
        )

        application = Application(
            candidate_id=candidate.id,
            job_id=job.id,
            match_data=match_data,
            overall_score=40.0,
            must_have_skills_score=20.0,
            nice_to_have_skills_score=0.0,
            experience_score=100.0,
            education_score=50.0
        )
        db.add(application)
        db.commit()
        db.refresh(application)

        scenario_payload = deep_copy(DEFAULT_SCENARIO)
        scenario_payload["scenario"]["education_required_override"] = False

        result = run_what_if(
            db,
            job_id=job.id,
            scenario_payload=scenario_payload,
            include_summary=True
        )

        assert result["job_id"] == job.id
        assert result["summary_table"]
        assert result["summary_table"][0]["candidate"] == "Alex"
    finally:
        db.close()
