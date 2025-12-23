"""Job description parser - extracts job data into structured format."""
from pathlib import Path
from typing import Dict, Any
import PyPDF2
import pdfplumber
from docx import Document
from loguru import logger

JOB_SCHEMA = {
    "type": "object",
    "properties": {
        "basics": {
            "type": "object",
            "properties": {
                "title": {"type": ["string", "null"]},
                "company": {"type": ["string", "null"]},
                "location": {
                    "type": "object",
                    "properties": {
                        "address": {"type": ["string", "null"]},
                        "city": {"type": ["string", "null"]},
                        "countryCode": {"type": ["string", "null"]},
                        "region": {"type": ["string", "null"]}
                    },
                    "required": ["address", "city", "countryCode", "region"]
                },
                "url": {"type": ["string", "null"]},
                "summary": {"type": ["string", "null"]}
            },
            "required": ["title", "company", "location", "url", "summary"]
        },
        "description": {"type": ["string", "null"]},
        "responsibilities": {"type": "array", "items": {"type": "string"}},
        "requirements": {
            "type": "object",
            "properties": {
                "must_have_skills": {"type": "array", "items": {"type": "string"}},
                "nice_to_have_skills": {"type": "array", "items": {"type": "string"}},
                "minimum_years_experience": {"type": ["number", "null"]},
                "required_education": {
                    "type": "object",
                    "properties": {
                        "level": {"type": ["string", "null"]},
                        "field": {"type": ["string", "null"]},
                        "required": {"type": ["boolean", "null"]}
                    },
                    "required": ["level", "field", "required"]
                },
                "certifications": {"type": "array", "items": {"type": "string"}},
                "languages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "language": {"type": ["string", "null"]},
                            "fluency": {"type": ["string", "null"]}
                        },
                        "required": ["language", "fluency"]
                    }
                }
            },
            "required": [
                "must_have_skills",
                "nice_to_have_skills",
                "minimum_years_experience",
                "required_education",
                "certifications",
                "languages"
            ]
        },
        "compensation": {
            "type": "object",
            "properties": {
                "salary_range": {
                    "type": "object",
                    "properties": {
                        "min": {"type": ["number", "null"]},
                        "max": {"type": ["number", "null"]},
                        "currency": {"type": ["string", "null"]}
                    },
                    "required": ["min", "max", "currency"]
                },
                "salary_text": {"type": ["string", "null"]},
                "equity": {"type": ["boolean", "null"]},
                "benefits": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["salary_range", "salary_text", "equity", "benefits"]
        },
        "employment_type": {"type": ["string", "null"]},
        "remote_policy": {"type": ["string", "null"]},
        "department": {"type": ["string", "null"]},
        "reports_to": {"type": ["string", "null"]},
        "team_size": {"type": ["number", "null"]},
        "application_deadline": {"type": ["string", "null"]},
        "posted_date": {"type": ["string", "null"]}
    },
    "required": [
        "basics",
        "description",
        "responsibilities",
        "requirements",
        "compensation",
        "employment_type",
        "remote_policy",
        "department",
        "reports_to",
        "team_size",
        "application_deadline",
        "posted_date"
    ]
}


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
        
        prompt = f"""You are a recruitment analyst extracting a structured job profile for matching.

Job Description:
{text}

Extraction rules:
- Use only information explicitly stated in the text; do not infer or assume.
- If a field is missing, use null or an empty array.
- Set "description" to the full job description text (lightly cleaned if needed).
- Responsibilities should be short verb phrases.
- Skills: put hard requirements in must_have_skills and preferences in nice_to_have_skills.
- minimum_years_experience must be a number; use the stated value or 0 if not specified.
- Only set location, compensation, employment_type, remote_policy, dates, and education if explicitly stated.
- Do not set countryCode unless the country is explicitly mentioned.

Return data using the structured output schema."""

        try:
            job_data = llm_client.call_llm(
                prompt,
                temperature=0.3,
                context="job parsing",
                schema=JOB_SCHEMA,
                function_name="parse_job_description"
            )

            if not isinstance(job_data, dict):
                raise ValueError("LLM response was not a JSON object.")

            logger.info("Successfully parsed job description into structured format")
            return job_data
        except Exception as e:
            logger.error(f"Failed to parse LLM response as structured data: {e}")
            
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
