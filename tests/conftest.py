import json
from datetime import datetime


def deep_copy(value):
    return json.loads(json.dumps(value))


def make_job_data():
    return {
        "requirements": {
            "must_have_skills": ["Skill A", "Skill B", "Skill C", "Skill D"],
            "nice_to_have_skills": ["Skill E", "Skill F"],
            "minimum_years_experience": 3,
            "required_education": {
                "level": "Bachelor's degree",
                "field": "Computer Science or related",
                "required": True
            }
        }
    }


def make_match_bucket(full, partial, missing):
    return {
        "score": 0,
        "analysis": "Test analysis",
        "matched_skills": list(full) + list(partial),
        "missing_skills": list(missing),
        "full_matches": list(full),
        "partial_matches": list(partial)
    }


def make_match_data(must_full, must_partial, must_missing, nice_full, nice_partial, nice_missing):
    return {
        "overall_score": 0,
        "must_have_skills": make_match_bucket(must_full, must_partial, must_missing),
        "nice_to_have_skills": make_match_bucket(nice_full, nice_partial, nice_missing),
        "minimum_years_experience": {
            "score": 0,
            "analysis": "Experience analysis",
            "candidate_years": 3,
            "required_years": 3
        },
        "required_education": {
            "score": 0,
            "analysis": "Education analysis",
            "candidate_education": None,
            "required_education": None
        },
        "summary": "Summary",
        "strengths": [],
        "weaknesses": [],
        "recommendation": "Consider"
    }


def make_resume_data(degree="Bachelor's degree", field="Computer Science"):
    return {
        "education": [
            {
                "studyType": degree,
                "area": field
            }
        ]
    }


class Dummy:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def make_application(application_id, candidate_name, job_title, company, match_data, overall_score):
    candidate = Dummy(id=application_id, name=candidate_name, resume_data=make_resume_data())
    job = Dummy(title=job_title, company=company)
    return Dummy(
        id=application_id,
        candidate=candidate,
        job=job,
        match_data=match_data,
        overall_score=overall_score,
        created_at=datetime(2024, 1, application_id, 12, 0, 0)
    )
