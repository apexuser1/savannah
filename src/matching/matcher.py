"""LLM-based matching service for candidates and jobs."""
import json
from typing import Dict, Any
from loguru import logger

from src.config import Config


class LLMClient:
    """Client for calling LLM APIs (OpenAI or OpenRouter)."""
    
    def __init__(self):
        """Initialize the LLM client."""
        Config.validate()
        self.provider = Config.LLM_PROVIDER
        
        if self.provider == "openai":
            import openai
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            self.model = Config.OPENAI_MODEL
        elif self.provider == "openrouter":
            import openai
            self.client = openai.OpenAI(
                base_url=Config.OPENROUTER_BASE_URL,
                api_key=Config.OPENROUTER_API_KEY
            )
            self.model = Config.OPENROUTER_MODEL
        else:
            raise ValueError(f"Invalid LLM provider: {self.provider}")
        
        logger.info(f"Initialized LLM client with provider: {self.provider}, model: {self.model}")
    
    def call_llm(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """
        Call the LLM API with a prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            temperature: Temperature for response generation
            max_tokens: Maximum tokens in response
            
        Returns:
            The LLM response text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides structured, accurate responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise


class CandidateJobMatcher:
    """Match candidates to jobs using LLM analysis."""
    
    def __init__(self):
        """Initialize the matcher."""
        self.llm_client = LLMClient()
    
    def match(self, candidate_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Match a candidate to a job and generate detailed scores.
        
        Args:
            candidate_data: Structured candidate data (JSON Resume format)
            job_data: Structured job data
            
        Returns:
            Dictionary with match scores and analysis
        """
        logger.info("Starting candidate-job matching...")
        
        # Create matching prompt
        prompt = self._create_matching_prompt(candidate_data, job_data)
        
        # Call LLM
        response = self.llm_client.call_llm(prompt, temperature=0.3, max_tokens=2000)
        
        try:
            # Parse JSON response
            match_data = json.loads(response)
            logger.info(f"Match completed. Overall score: {match_data.get('overall_score', 'N/A')}")
            return match_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"LLM response: {response[:500]}")
            
            # Return default scores if parsing fails
            return {
                "overall_score": 0,
                "must_have_skills": {"score": 0, "analysis": "Parsing error"},
                "nice_to_have_skills": {"score": 0, "analysis": "Parsing error"},
                "minimum_years_experience": {"score": 0, "analysis": "Parsing error"},
                "required_education": {"score": 0, "analysis": "Parsing error"},
                "summary": "Failed to generate match analysis due to parsing error",
                "strengths": [],
                "weaknesses": [],
                "recommendation": "Unable to provide recommendation"
            }
    
    def _create_matching_prompt(self, candidate_data: Dict[str, Any], job_data: Dict[str, Any]) -> str:
        """Create the prompt for LLM matching."""
        
        prompt = f"""You are an expert recruiter. Analyze the following candidate and job description to determine how well they match.

CANDIDATE DATA (JSON Resume format):
{json.dumps(candidate_data, indent=2)}

JOB DESCRIPTION DATA:
{json.dumps(job_data, indent=2)}

Please analyze the match and provide scores (0-100) for each of the following categories:

1. **must_have_skills**: How well does the candidate match the required/must-have skills?
2. **nice_to_have_skills**: How well does the candidate match the preferred/nice-to-have skills?
3. **minimum_years_experience**: Does the candidate meet the minimum years of experience requirement?
4. **required_education**: Does the candidate meet the education requirements?

For each category, provide:
- A score from 0-100 (0 = no match, 100 = perfect match)
- A brief analysis explaining the score
- Specific evidence from the candidate's profile

Also provide:
- An **overall_score** (0-100) representing the overall match quality
- A **summary** of the match (2-3 sentences)
- **strengths**: List of candidate's strengths for this role (array of strings)
- **weaknesses**: List of gaps or areas where candidate doesn't match (array of strings)
- A **recommendation**: "Highly Recommended", "Recommended", "Consider", or "Not Recommended"

Return your analysis in the following JSON format:

{{
  "overall_score": 85,
  "must_have_skills": {{
    "score": 90,
    "analysis": "Candidate has strong proficiency in...",
    "matched_skills": ["Skill 1", "Skill 2"],
    "missing_skills": ["Skill 3"]
  }},
  "nice_to_have_skills": {{
    "score": 75,
    "analysis": "Candidate has experience with...",
    "matched_skills": ["Skill A", "Skill B"],
    "missing_skills": ["Skill C"]
  }},
  "minimum_years_experience": {{
    "score": 100,
    "analysis": "Candidate has X years of relevant experience...",
    "candidate_years": 8,
    "required_years": 5
  }},
  "required_education": {{
    "score": 100,
    "analysis": "Candidate holds a...",
    "candidate_education": "Master's in Computer Science",
    "required_education": "Bachelor's in Computer Science or related field"
  }},
  "summary": "This candidate is a strong match for the position...",
  "strengths": [
    "Strength 1",
    "Strength 2",
    "Strength 3"
  ],
  "weaknesses": [
    "Gap 1",
    "Gap 2"
  ],
  "recommendation": "Highly Recommended"
}}

Return ONLY the JSON object, no additional text or explanation. Be objective and thorough in your analysis."""

        return prompt


def match_candidate_to_job(candidate_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to match a candidate to a job.
    
    Args:
        candidate_data: Structured candidate data
        job_data: Structured job data
        
    Returns:
        Match data with scores
    """
    matcher = CandidateJobMatcher()
    return matcher.match(candidate_data, job_data)
