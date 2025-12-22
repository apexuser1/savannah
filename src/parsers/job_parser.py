"""Job description parser - extracts job data into structured format."""
import json
from pathlib import Path
from typing import Dict, Any
import PyPDF2
import pdfplumber
from docx import Document
from loguru import logger


class JobParser:
    """Parse job description files into structured format."""
    
    def __init__(self):
        """Initialize the job parser."""
        pass
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a job description file and return structured data.
        
        Args:
            file_path: Path to the job description file
            
        Returns:
            Dictionary with structured job data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = file_path.suffix.lower()
        logger.info(f"Parsing job description: {file_path.name} (type: {file_extension})")
        
        # Extract text based on file type
        if file_extension == '.pdf':
            text = self._extract_text_from_pdf(file_path)
        elif file_extension == '.docx':
            text = self._extract_text_from_docx(file_path)
        elif file_extension in ['.txt', '.md']:
            text = self._extract_text_from_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        logger.info(f"Extracted {len(text)} characters from job description")
        
        # Use LLM to parse text into structured format
        job_data = self._parse_text_to_structured_job(text)
        
        return job_data
    
    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        text = ""
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except Exception as e2:
                logger.error(f"Failed to extract text from PDF: {e2}")
                raise
        
        return text.strip()
    
    def _extract_text_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    
    def _extract_text_from_text(self, file_path: Path) -> str:
        """Extract text from TXT or MD file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        return text.strip()
    
    def _parse_text_to_structured_job(self, text: str) -> Dict[str, Any]:
        """
        Use LLM to parse job description text into structured format.
        
        Args:
            text: Raw job description text
            
        Returns:
            Dictionary with structured job data
        """
        from src.matching.matcher import LLMClient
        
        llm_client = LLMClient()
        
        prompt = f"""You are a job description parsing assistant. Extract information from the following job description and structure it in a format that corresponds to the JSON Resume schema for easy matching.

Job Description:
{text}

Please extract and structure the information into the following JSON format. If a field is not found, use null or an empty array as appropriate:

{{
  "basics": {{
    "title": "Job title",
    "company": "Company name",
    "location": {{
      "address": "Street address if provided",
      "city": "City",
      "countryCode": "US",
      "region": "State/Province"
    }},
    "url": "Job posting URL or company website",
    "summary": "Brief job summary or company description"
  }},
  "description": "Full job description",
  "responsibilities": [
    "Responsibility 1",
    "Responsibility 2",
    "Responsibility 3"
  ],
  "requirements": {{
    "must_have_skills": [
      "Required skill 1",
      "Required skill 2",
      "Required skill 3"
    ],
    "nice_to_have_skills": [
      "Preferred skill 1",
      "Preferred skill 2"
    ],
    "minimum_years_experience": 5,
    "required_education": {{
      "level": "Bachelor's/Master's/PhD/High School/etc.",
      "field": "Computer Science/Engineering/Business/etc.",
      "required": true
    }},
    "certifications": [
      "Certification 1",
      "Certification 2"
    ],
    "languages": [
      {{
        "language": "Language name",
        "fluency": "Required fluency level"
      }}
    ]
  }},
  "compensation": {{
    "salary_range": {{
      "min": 100000,
      "max": 150000,
      "currency": "USD"
    }},
    "salary_text": "Salary range as text if specific numbers not available",
    "equity": true,
    "benefits": [
      "Health insurance",
      "401k",
      "Remote work"
    ]
  }},
  "employment_type": "Full-time/Part-time/Contract/Internship",
  "remote_policy": "Remote/Hybrid/On-site",
  "department": "Department name",
  "reports_to": "Reporting position",
  "team_size": 10,
  "application_deadline": "YYYY-MM-DD",
  "posted_date": "YYYY-MM-DD"
}}

Return ONLY the JSON object, no additional text or explanation. Extract as much information as possible from the job description. If specific information is not available, use reasonable defaults or null."""

        response = llm_client.call_llm(prompt, temperature=0.3)
        
        try:
            # Parse JSON from response
            job_data = json.loads(response)
            logger.info("Successfully parsed job description into structured format")
            return job_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"LLM response: {response[:500]}")
            
            # Return a minimal valid structure
            return {
                "basics": {
                    "title": "Unknown Position",
                    "company": "Unknown Company"
                },
                "description": text[:1000],  # Use first 1000 chars as fallback
                "requirements": {
                    "must_have_skills": [],
                    "nice_to_have_skills": [],
                    "minimum_years_experience": 0,
                    "required_education": None
                }
            }
