"""Resume parser - extracts resume data into JSON Resume format."""
import json
from pathlib import Path
from typing import Dict, Any
import PyPDF2
import pdfplumber
from docx import Document
from loguru import logger

from src.config import Config


class ResumeParser:
    """Parse resume files into JSON Resume format (jsonresume.org)."""
    
    def __init__(self):
        """Initialize the resume parser."""
        pass
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a resume file and return structured data in JSON Resume format.
        
        Args:
            file_path: Path to the resume file
            
        Returns:
            Dictionary in JSON Resume format
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_extension = file_path.suffix.lower()
        logger.info(f"Parsing resume: {file_path.name} (type: {file_extension})")
        
        # Extract text based on file type
        if file_extension == '.pdf':
            text = self._extract_text_from_pdf(file_path)
        elif file_extension == '.docx':
            text = self._extract_text_from_docx(file_path)
        elif file_extension in ['.txt', '.md']:
            text = self._extract_text_from_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        logger.info(f"Extracted {len(text)} characters from resume")
        
        # Use LLM to parse text into JSON Resume format
        resume_data = self._parse_text_to_json_resume(text)
        
        return resume_data
    
    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        text = ""
        
        try:
            # Try pdfplumber first (better text extraction)
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
            # Fallback to PyPDF2
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
    
    def _parse_text_to_json_resume(self, text: str) -> Dict[str, Any]:
        """
        Use LLM to parse resume text into JSON Resume format.
        
        Args:
            text: Raw resume text
            
        Returns:
            Dictionary in JSON Resume format
        """
        from src.matching.matcher import LLMClient
        
        llm_client = LLMClient()
        
        prompt = f"""You are a resume parsing assistant. Extract information from the following resume text and format it according to the JSON Resume schema (jsonresume.org).

Resume Text:
{text}

Please extract and structure the information into the following JSON Resume format. If a field is not found, use null or an empty array as appropriate:

{{
  "basics": {{
    "name": "Full Name",
    "label": "Job Title/Role",
    "email": "email@example.com",
    "phone": "Phone number",
    "url": "Personal website or portfolio URL",
    "summary": "Professional summary or objective",
    "location": {{
      "address": "Street address",
      "city": "City",
      "countryCode": "US",
      "region": "State/Province"
    }},
    "profiles": [
      {{
        "network": "LinkedIn/GitHub/Twitter",
        "username": "username",
        "url": "profile URL"
      }}
    ]
  }},
  "work": [
    {{
      "name": "Company name",
      "position": "Job title",
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD or null if current",
      "summary": "Job description",
      "highlights": ["Achievement 1", "Achievement 2"]
    }}
  ],
  "education": [
    {{
      "institution": "School name",
      "area": "Major/Field of study",
      "studyType": "Degree type (Bachelor, Master, PhD, etc.)",
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD",
      "score": "GPA or grade",
      "courses": ["Course 1", "Course 2"]
    }}
  ],
  "skills": [
    {{
      "name": "Skill category (e.g., Programming, Languages)",
      "level": "Proficiency level (Beginner, Intermediate, Advanced, Expert)",
      "keywords": ["Skill 1", "Skill 2", "Skill 3"]
    }}
  ],
  "certificates": [
    {{
      "name": "Certificate name",
      "date": "YYYY-MM-DD",
      "issuer": "Issuing organization",
      "url": "Certificate URL"
    }}
  ],
  "projects": [
    {{
      "name": "Project name",
      "description": "Project description",
      "highlights": ["Achievement 1", "Achievement 2"],
      "keywords": ["Technology 1", "Technology 2"],
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD or null if ongoing",
      "url": "Project URL",
      "roles": ["Role in project"]
    }}
  ],
  "awards": [
    {{
      "title": "Award title",
      "date": "YYYY-MM-DD",
      "awarder": "Organization",
      "summary": "Award description"
    }}
  ],
  "publications": [
    {{
      "name": "Publication title",
      "publisher": "Publisher",
      "releaseDate": "YYYY-MM-DD",
      "url": "Publication URL",
      "summary": "Publication description"
    }}
  ],
  "languages": [
    {{
      "language": "Language name",
      "fluency": "Fluency level (Native, Fluent, Professional, Intermediate, Basic)"
    }}
  ],
  "interests": [
    {{
      "name": "Interest area",
      "keywords": ["Keyword 1", "Keyword 2"]
    }}
  ],
  "references": [
    {{
      "name": "Reference name",
      "reference": "Reference description"
    }}
  ]
}}

Return ONLY the JSON object, no additional text or explanation. Ensure all dates are in YYYY-MM-DD format or YYYY-MM if day is unknown. If exact dates are not available, use your best estimate based on typical durations."""

        response = llm_client.call_llm(prompt, temperature=0.3)
        
        try:
            # Parse JSON from response
            resume_data = json.loads(response)
            logger.info("Successfully parsed resume into JSON Resume format")
            return resume_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"LLM response: {response[:500]}")
            
            # Return a minimal valid JSON Resume structure
            return {
                "basics": {
                    "name": "Unknown",
                    "email": None,
                    "summary": text[:500]  # Use first 500 chars as fallback
                },
                "work": [],
                "education": [],
                "skills": []
            }
