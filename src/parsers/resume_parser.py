"""Resume parser - extracts resume data into JSON Resume format."""
from pathlib import Path
from typing import Dict, Any
import PyPDF2
import pdfplumber
from docx import Document
from loguru import logger

RESUME_SCHEMA = {
    "type": "object",
    "properties": {
        "basics": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"]},
                "label": {"type": ["string", "null"]},
                "email": {"type": ["string", "null"]},
                "phone": {"type": ["string", "null"]},
                "url": {"type": ["string", "null"]},
                "summary": {"type": ["string", "null"]},
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
                "profiles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "network": {"type": ["string", "null"]},
                            "username": {"type": ["string", "null"]},
                            "url": {"type": ["string", "null"]}
                        },
                        "required": ["network", "username", "url"]
                    }
                }
            },
            "required": ["name", "label", "email", "phone", "url", "summary", "location", "profiles"]
        },
        "work": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "position": {"type": ["string", "null"]},
                    "startDate": {"type": ["string", "null"]},
                    "endDate": {"type": ["string", "null"]},
                    "summary": {"type": ["string", "null"]},
                    "highlights": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["name", "position", "startDate", "endDate", "summary", "highlights"]
            }
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": ["string", "null"]},
                    "area": {"type": ["string", "null"]},
                    "studyType": {"type": ["string", "null"]},
                    "startDate": {"type": ["string", "null"]},
                    "endDate": {"type": ["string", "null"]},
                    "score": {"type": ["string", "null"]},
                    "courses": {"type": "array", "items": {"type": "string"}}
                },
                "required": [
                    "institution",
                    "area",
                    "studyType",
                    "startDate",
                    "endDate",
                    "score",
                    "courses"
                ]
            }
        },
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "level": {"type": ["string", "null"]},
                    "keywords": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["name", "level", "keywords"]
            }
        },
        "certificates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "date": {"type": ["string", "null"]},
                    "issuer": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]}
                },
                "required": ["name", "date", "issuer", "url"]
            }
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                    "highlights": {"type": "array", "items": {"type": "string"}},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                    "startDate": {"type": ["string", "null"]},
                    "endDate": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                    "roles": {"type": "array", "items": {"type": "string"}}
                },
                "required": [
                    "name",
                    "description",
                    "highlights",
                    "keywords",
                    "startDate",
                    "endDate",
                    "url",
                    "roles"
                ]
            }
        },
        "awards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": ["string", "null"]},
                    "date": {"type": ["string", "null"]},
                    "awarder": {"type": ["string", "null"]},
                    "summary": {"type": ["string", "null"]}
                },
                "required": ["title", "date", "awarder", "summary"]
            }
        },
        "publications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "publisher": {"type": ["string", "null"]},
                    "releaseDate": {"type": ["string", "null"]},
                    "url": {"type": ["string", "null"]},
                    "summary": {"type": ["string", "null"]}
                },
                "required": ["name", "publisher", "releaseDate", "url", "summary"]
            }
        },
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
        },
        "interests": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "keywords": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["name", "keywords"]
            }
        },
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "reference": {"type": ["string", "null"]}
                },
                "required": ["name", "reference"]
            }
        }
    },
    "required": [
        "basics",
        "work",
        "education",
        "skills",
        "certificates",
        "projects",
        "awards",
        "publications",
        "languages",
        "interests",
        "references"
    ]
}


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
        
        prompt = f"""You are a resume parsing assistant. Extract facts from the resume text and format them according to the JSON Resume schema (jsonresume.org).

Resume Text:
{text}

Extraction rules:
- Use only information explicitly stated; do not infer or assume.
- If a field is missing, use null or an empty array.
- Dates: use YYYY-MM-DD when available; use YYYY-MM or YYYY if only partial dates are present; otherwise null. Do not estimate dates.
- Preserve each work, education, and project entry as separate items.
- Skills: use section headings if present; otherwise use a single "Skills" group and list all skills found.
- If a summary/objective is present, copy it; otherwise leave summary null.

Return data using the structured output schema."""

        try:
            resume_data = llm_client.call_llm(
                prompt,
                temperature=0.3,
                context="resume parsing",
                schema=RESUME_SCHEMA,
                function_name="parse_resume"
            )

            if not isinstance(resume_data, dict):
                raise ValueError("LLM response was not a JSON object.")

            logger.info("Successfully parsed resume into JSON Resume format")
            return resume_data
        except Exception as e:
            logger.error(f"Failed to parse LLM response as structured data: {e}")
            
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
