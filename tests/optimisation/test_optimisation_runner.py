from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.connection import Base
from src.database.models import Job, Candidate, Application
from src.optimisation.runner import run_optimisation

from tests.conftest import make_job_data, make_match_data, make_resume_data


def test_run_optimisation_finds_relaxation():
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
        candidate_1 = Candidate(
            resume_data=resume_data,
            name="Alex",
            email="alex@example.com",
            phone="555-0100",
            original_filename="resume.txt",
            file_type="txt"
        )
        candidate_2 = Candidate(
            resume_data=resume_data,
            name="Jamie",
            email="jamie@example.com",
            phone="555-0200",
            original_filename="resume2.txt",
            file_type="txt"
        )
        db.add(candidate_1)
        db.add(candidate_2)
        db.commit()
        db.refresh(candidate_1)
        db.refresh(candidate_2)

        match_data_pass = make_match_data(
            must_full=["Skill A", "Skill B", "Skill C", "Skill D"],
            must_partial=[],
            must_missing=[],
            nice_full=[],
            nice_partial=[],
            nice_missing=["Skill E", "Skill F"]
        )
        match_data_fail = make_match_data(
            must_full=["Skill A", "Skill B", "Skill C"],
            must_partial=[],
            must_missing=["Skill D"],
            nice_full=[],
            nice_partial=[],
            nice_missing=["Skill E", "Skill F"]
        )

        app_1 = Application(
            candidate_id=candidate_1.id,
            job_id=job.id,
            match_data=match_data_pass,
            overall_score=60.0,
            must_have_skills_score=100.0,
            nice_to_have_skills_score=0.0,
            experience_score=100.0,
            education_score=100.0
        )
        app_2 = Application(
            candidate_id=candidate_2.id,
            job_id=job.id,
            match_data=match_data_fail,
            overall_score=40.0,
            must_have_skills_score=75.0,
            nice_to_have_skills_score=0.0,
            experience_score=100.0,
            education_score=100.0
        )
        db.add(app_1)
        db.add(app_2)
        db.commit()

        optimisation_payload = {
            "target": {"candidate_count": 2},
            "strategy": {"name": "beam"},
            "constraints": {
                "max_total_changes": 1,
                "allowed_relaxations": ["remove_must_have"]
            }
        }

        result = run_optimisation(
            db,
            job_id=job.id,
            optimisation_payload=optimisation_payload
        )

        assert result["baseline"]["candidate_count"] == 1
        best = result["results"][0]
        assert best["candidate_count"] == 2
        assert any(change["type"] == "remove_must_have" for change in best["changes"])
    finally:
        db.close()
