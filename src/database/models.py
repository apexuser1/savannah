"""SQLAlchemy database models."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from src.database.connection import Base


class Candidate(Base):
    """Candidate model - stores structured resume data in JSON Resume format."""
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # JSON Resume format data
    resume_data = Column(JSON, nullable=False)  # Full JSON Resume schema
    
    # Extracted fields for quick access (denormalized)
    name = Column(String, index=True)
    email = Column(String, index=True)
    phone = Column(String)
    
    # Metadata
    original_filename = Column(String)
    file_type = Column(String)  # pdf, docx, txt, md
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = relationship("Application", back_populates="candidate")
    
    def __repr__(self):
        return f"<Candidate(id={self.id}, name='{self.name}', email='{self.email}')>"


class Job(Base):
    """Job model - stores structured job descriptions."""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Job data corresponding to JSON Resume format
    job_data = Column(JSON, nullable=False)  # Structured job description
    
    # Extracted fields for quick access (denormalized)
    title = Column(String, index=True)
    company = Column(String, index=True)
    location = Column(String)
    
    # Metadata
    original_filename = Column(String)
    file_type = Column(String)  # txt, md, pdf, docx
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = relationship("Application", back_populates="job")
    
    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}')>"


class Application(Base):
    """Application model - links candidates to jobs with match scores."""
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    
    # Match data (JSON format with detailed scores)
    match_data = Column(JSON)  # Contains all match scores and analysis
    
    # Overall match score (0-100) - denormalized for quick filtering
    overall_score = Column(Float, index=True)
    
    # Individual scores (0-100) - denormalized for quick access
    must_have_skills_score = Column(Float)
    nice_to_have_skills_score = Column(Float)
    experience_score = Column(Float)
    education_score = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    
    def __repr__(self):
        return f"<Application(id={self.id}, candidate_id={self.candidate_id}, job_id={self.job_id}, score={self.overall_score})>"
