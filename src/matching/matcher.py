"""LLM-based matching service for candidates and jobs."""
import json
from typing import Dict, Any, Optional
from loguru import logger

from src.config import Config

MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_score": {"type": "number", "minimum": 0, "maximum": 100},
        "must_have_skills": {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "analysis": {"type": "string", "minLength": 1},
                "matched_skills": {"type": "array", "items": {"type": "string"}},
                "missing_skills": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["score", "analysis", "matched_skills", "missing_skills"]
        },
        "nice_to_have_skills": {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "analysis": {"type": "string", "minLength": 1},
                "matched_skills": {"type": "array", "items": {"type": "string"}},
                "missing_skills": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["score", "analysis", "matched_skills", "missing_skills"]
        },
        "minimum_years_experience": {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "analysis": {"type": "string", "minLength": 1},
                "candidate_years": {"type": "number", "minimum": 0},
                "required_years": {"type": "number", "minimum": 0}
            },
            "required": ["score", "analysis", "candidate_years", "required_years"]
        },
        "required_education": {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "analysis": {"type": "string", "minLength": 1},
                "candidate_education": {"type": ["string", "null"]},
                "required_education": {"type": ["string", "null"]}
            },
            "required": ["score", "analysis", "candidate_education", "required_education"]
        },
        "summary": {"type": "string", "minLength": 1},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "weaknesses": {"type": "array", "items": {"type": "string"}},
        "recommendation": {
            "type": "string",
            "enum": ["Highly Recommended", "Recommended", "Consider", "Not Recommended"]
        }
    },
    "required": [
        "overall_score",
        "must_have_skills",
        "nice_to_have_skills",
        "minimum_years_experience",
        "required_education",
        "summary",
        "strengths",
        "weaknesses",
        "recommendation"
    ]
}


class LLMClient:
    """Client for calling LLM APIs (OpenAI or OpenRouter)."""
    
    def __init__(self, model: Optional[str] = None):
        """Initialize the LLM client."""
        Config.validate()
        self.provider = Config.LLM_PROVIDER
        
        if self.provider == "openai":
            import openai
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            self.model = model or Config.OPENAI_MODEL
        elif self.provider == "openrouter":
            import openai
            self.client = openai.OpenAI(
                base_url=Config.OPENROUTER_BASE_URL,
                api_key=Config.OPENROUTER_API_KEY
            )
            self.model = model or Config.OPENROUTER_MODEL
        else:
            raise ValueError(f"Invalid LLM provider: {self.provider}")
        
        logger.info(f"Initialized LLM client with provider: {self.provider}, model: {self.model}")

    def _token_param_name(self) -> str:
        if self.provider != "openai":
            return "max_tokens"

        model = (self.model or "").lower()
        if model.startswith(("gpt-5", "gpt-4.1", "o1", "o3")):
            return "max_completion_tokens"
        return "max_tokens"

    def _is_unsupported_param_error(self, error: Exception, param_name: str) -> bool:
        message = str(error).lower()
        return "unsupported parameter" in message and param_name in message

    def _create_completion(
        self,
        messages: list,
        temperature: float,
        max_tokens: int,
        **extra_params: Any
    ):
        token_param = self._token_param_name()
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            **extra_params
        }
        params[token_param] = max_tokens

        try:
            return self.client.chat.completions.create(**params)
        except Exception as e:
            if self.provider == "openai" and self._is_unsupported_param_error(e, token_param):
                alt_param = "max_completion_tokens" if token_param == "max_tokens" else "max_tokens"
                params.pop(token_param, None)
                params[alt_param] = max_tokens
                return self.client.chat.completions.create(**params)
            raise

    def _normalize_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        def normalize(node: Any) -> Any:
            if isinstance(node, dict):
                normalized = {key: normalize(value) for key, value in node.items()}
                node_type = normalized.get("type")
                is_object = node_type == "object" or (
                    isinstance(node_type, list) and "object" in node_type
                )
                if is_object:
                    normalized["additionalProperties"] = False

                for key in ("properties", "items", "anyOf", "oneOf", "allOf"):
                    if key in normalized:
                        normalized[key] = normalize(normalized[key])
                return normalized
            if isinstance(node, list):
                return [normalize(item) for item in node]
            return node

        return normalize(schema)
    
    def call_llm(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        context: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        function_name: Optional[str] = None
    ) -> Any:
        """
        Call the LLM API with a prompt.
        
        Args:
            prompt: The prompt to send to the LLM
            temperature: Temperature for response generation
            max_tokens: Maximum tokens in response
            context: Optional label describing the call site
            schema: JSON schema describing structured output
            function_name: Function name for tool-based structured output
            
        Returns:
            The LLM response text or structured output
        """
        try:
            if schema:
                if context:
                    logger.debug("LLM prompt ({}):\n{}", context, prompt)
                else:
                    logger.debug("LLM prompt:\n{}", prompt)
                tool_name = function_name or "structured_output"

                if self.provider == "openai":
                    normalized_schema = self._normalize_schema(schema)
                    response = self._create_completion(
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a helpful assistant that provides structured, accurate responses."
                            },
                            {"role": "user", "content": prompt}
                        ],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": tool_name,
                                "schema": normalized_schema,
                                "strict": True
                            }
                        }
                    )

                    content = response.choices[0].message.content or ""
                    if context:
                        logger.debug("LLM raw response ({}):\n{}", context, content)
                    else:
                        logger.debug("LLM raw response:\n{}", content)

                    try:
                        parsed = json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON schema response: {e}")
                        logger.debug("Raw response: {}", content)
                        raise

                    if context:
                        logger.info("LLM structured response ({}):\n{}", context, json.dumps(parsed, indent=2))
                    else:
                        logger.info("LLM structured response:\n{}", json.dumps(parsed, indent=2))

                    return parsed

                response = self._create_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that provides structured, accurate responses."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=[
                        {
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "description": "Return data that matches the provided JSON schema.",
                                "parameters": schema
                            }
                        }
                    ],
                    tool_choice={"type": "function", "function": {"name": tool_name}}
                )

                message = response.choices[0].message
                tool_calls = getattr(message, "tool_calls", None) or []
                if not tool_calls:
                    raise ValueError("LLM did not return a tool call.")

                arguments = tool_calls[0].function.arguments
                if context:
                    logger.debug("LLM raw response ({}):\n{}", context, arguments)
                else:
                    logger.debug("LLM raw response:\n{}", arguments)

                try:
                    parsed = json.loads(arguments)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool arguments as JSON: {e}")
                    logger.debug("Tool arguments: {}", arguments)
                    raise

                if context:
                    logger.info("LLM structured response ({}):\n{}", context, json.dumps(parsed, indent=2))
                else:
                    logger.info("LLM structured response:\n{}", json.dumps(parsed, indent=2))

                return parsed

            if context:
                logger.info("LLM prompt ({}):\n{}", context, prompt)
            else:
                logger.info("LLM prompt:\n{}", prompt)

            response = self._create_completion(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides structured, accurate responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content.strip()
            if context:
                logger.info("LLM response ({}):\n{}", context, content)
            else:
                logger.info("LLM response:\n{}", content)
            return content
        
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise


class CandidateJobMatcher:
    """Match candidates to jobs using LLM analysis."""
    
    def __init__(self):
        """Initialize the matcher."""
        self.llm_client = LLMClient(model=Config.MATCH_MODEL)

    def _is_non_empty_string(self, value: Any) -> bool:
        return isinstance(value, str) and value.strip() != ""

    def _is_number(self, value: Any) -> bool:
        return isinstance(value, (int, float))

    def _is_valid_match_data(self, match_data: Dict[str, Any]) -> bool:
        if not isinstance(match_data, dict):
            return False

        if not self._is_number(match_data.get("overall_score")):
            return False

        if not self._is_non_empty_string(match_data.get("summary")):
            return False

        if match_data.get("recommendation") not in {
            "Highly Recommended",
            "Recommended",
            "Consider",
            "Not Recommended"
        }:
            return False

        for key in ("must_have_skills", "nice_to_have_skills"):
            bucket = match_data.get(key)
            if not isinstance(bucket, dict):
                return False
            if not self._is_number(bucket.get("score")):
                return False
            if not self._is_non_empty_string(bucket.get("analysis")):
                return False

        experience = match_data.get("minimum_years_experience")
        if not isinstance(experience, dict):
            return False
        if not self._is_number(experience.get("score")):
            return False
        if not self._is_non_empty_string(experience.get("analysis")):
            return False
        if not self._is_number(experience.get("candidate_years")):
            return False
        if not self._is_number(experience.get("required_years")):
            return False

        education = match_data.get("required_education")
        if not isinstance(education, dict):
            return False
        if not self._is_number(education.get("score")):
            return False
        if not self._is_non_empty_string(education.get("analysis")):
            return False

        return True
    
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
        last_error = None
        for attempt, temperature in enumerate((0.3, 0.0), start=1):
            context = "candidate-job matching" if attempt == 1 else "candidate-job matching retry"
            try:
                match_data = self.llm_client.call_llm(
                    prompt,
                    temperature=temperature,
                    max_tokens=2000,
                    context=context,
                    schema=MATCH_SCHEMA,
                    function_name="match_candidate_to_job"
                )
            except Exception as e:
                last_error = e
                logger.warning(f"LLM match call failed on attempt {attempt}: {e}")
                continue

            if not isinstance(match_data, dict):
                last_error = ValueError("LLM response was not a JSON object.")
                logger.warning(f"LLM returned non-JSON match data on attempt {attempt}.")
                continue

            if self._is_valid_match_data(match_data):
                logger.info(f"Match completed. Overall score: {match_data.get('overall_score', 'N/A')}")
                return match_data

            last_error = ValueError("LLM response missing required fields.")
            logger.warning(f"LLM returned incomplete match data on attempt {attempt}.")

        logger.error(f"Failed to get structured LLM response: {last_error}")

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
        
        prompt = f"""You are an expert technical recruiter. Evaluate candidate–job fit fairly and precisely, using ONLY the provided data.

    CANDIDATE DATA (JSON Resume format):
    {json.dumps(candidate_data, indent=2)}

    JOB DESCRIPTION DATA (parsed JSON):
    {json.dumps(job_data, indent=2)}

    The job requirements are located at:
    - job_data["requirements"]["must_have_skills"]      # list of required skill/experience statements
    - job_data["requirements"]["nice_to_have_skills"]  # list of preferred skill/experience statements
    - job_data["requirements"]["minimum_years_experience"]  # integer
    - job_data["requirements"]["required_education"]        # object with level/field/required

    You MUST base your reasoning only on evidence present in candidate_data. Do NOT assume skills or experience that are not explicitly mentioned.

    =====================
    SCORING RULES
    =====================

    1) must_have_skills

    Compare each string in job_data["requirements"]["must_have_skills"] to the candidate’s skills and experience.

    For each must-have requirement:
    - Mark it as a FULL MATCH if there is clear, direct evidence or a very close synonym / concrete example in candidate_data.
    Examples:
    - "Strong proficiency in Python for backend development" is a FULL MATCH if candidate’s work history or skills show substantial Python backend development (e.g., Python + Flask/Django building APIs or services).
    - "Deep knowledge of PostgreSQL including query optimization and schema design" is at least a PARTIAL MATCH if the candidate has designed PostgreSQL schemas, migrated to PostgreSQL, or optimized PostgreSQL queries; it can be FULL MATCH if evidence suggests strong ongoing usage and optimization.
    - "Proven expertise in designing and implementing REST APIs" is a FULL MATCH if the candidate has clearly built REST APIs, especially with performance/scale metrics.
    - Mark it as a PARTIAL MATCH if there is some clearly related experience but less extensive or clearly less senior than the requirement wording.
    - Example: requirement says "Production experience with Kubernetes orchestration and deployment" and candidate only mentions a small Kubernetes personal project → PARTIAL MATCH.
    - Mark it as MISSING only if there is no relevant evidence at all in candidate_data.
    - When a requirement is broad, treat specific concrete usage as satisfying it:
    - Example: "Experience with AWS cloud services" is a FULL MATCH if candidate mentions using AWS EC2, S3, RDS, ECS, Lambda, etc., in work or projects.
    - Example: "Strong background in CI/CD pipelines" is at least a PARTIAL MATCH if candidate clearly participates in automated build/deploy processes, even if no specific tool names are given.

    Scoring for must_have_skills:
    - Let requirements = job_data["requirements"]["must_have_skills"] (a list of strings).
    - If this list is empty or missing:
    - must_have_skills.score = 50
    - must_have_skills.matched_skills = []
    - must_have_skills.missing_skills = []
    - must_have_skills.analysis = explain that must-have requirements are not specified.
    - Else:
    - Let N = number of must-have requirements.
    - Let M = number of FULL MATCH items.
    - Let P = number of PARTIAL MATCH items.
    - Compute: must_have_skills.score = round(100 * (M + 0.5 * P) / N)
    - IMPORTANT:
        - If there is at least one FULL MATCH or PARTIAL MATCH, the score MUST be > 0.
        - If must_have_skills.matched_skills is not empty, you MUST NOT say in the analysis that "all must-have requirements are missing".
    - Output:
    - must_have_skills.matched_skills: list of requirement strings from job_data["requirements"]["must_have_skills"] that are FULL MATCH or PARTIAL MATCH.
    - must_have_skills.missing_skills: list of requirement strings that are MISSING (no evidence).
    - must_have_skills.analysis:
        - Concise explanation of which requirements are fully met, which are partially met (and why), and which are missing.
        - Explicitly state how many are FULL MATCH, how many are PARTIAL MATCH, and how many are MISSING.

    2) nice_to_have_skills

    Compare each string in job_data["requirements"]["nice_to_have_skills"] to candidate_data, using the same FULL / PARTIAL / MISSING definitions.

    Examples with this job structure:
    - "Experience with AWS cloud services (EC2, S3, RDS, Lambda, ECS)":
    - If candidate mentions using EC2 and S3, treat this as at least a PARTIAL MATCH, and likely a FULL MATCH if used in real projects.
    - "Experience building and maintaining microservices architecture":
    - If candidate only worked on monolithic apps with no microservices mention, mark as MISSING.

    Scoring for nice_to_have_skills:
    - Let requirements = job_data["requirements"]["nice_to_have_skills"] (a list of strings).
    - If this list is empty or missing:
    - nice_to_have_skills.score = 50
    - nice_to_have_skills.matched_skills = []
    - nice_to_have_skills.missing_skills = []
    - nice_to_have_skills.analysis = explain that nice-to-have requirements are not specified.
    - Else:
    - Let N = number of nice-to-have requirements.
    - Let M = FULL MATCH count.
    - Let P = PARTIAL MATCH count.
    - nice_to_have_skills.score = round(100 * (M + 0.5 * P) / N)
    - If there is at least one FULL MATCH or PARTIAL MATCH, the score MUST be > 0.
    - If nice_to_have_skills.matched_skills is not empty, you MUST NOT say in the analysis that "all nice-to-have requirements are missing".
    - Output:
    - nice_to_have_skills.matched_skills: requirement strings from job_data["requirements"]["nice_to_have_skills"] that are FULL MATCH or PARTIAL MATCH.
    - nice_to_have_skills.missing_skills: requirement strings that are MISSING.
    - nice_to_have_skills.analysis:
        - Concise explanation grounded in evidence.
        - Explicitly state how many are FULL MATCH, how many are PARTIAL MATCH, and how many are MISSING.

    IMPORTANT:
    - Never write that the candidate has "no experience" with a technology if there is any evidence of it. Instead, describe it as "basic", "limited", or "partial" experience and treat it as PARTIAL MATCH.
    - For broad requirements like "Experience with AWS cloud services", treat concrete usage (e.g., "Deployed apps to AWS EC2 and stored files in S3") as satisfying that requirement.

    3) minimum_years_experience

    - Read required_years from job_data["requirements"]["minimum_years_experience"].
    - If this value is missing or null, treat required_years as 0.
    - Derive candidate_years from candidate_data["work"]:
    - Use explicit startDate and endDate values.
    - If endDate is null or missing, treat it as the current date and compute duration up to now.
    - Sum durations across roles or use the continuous timeline (whichever is more appropriate given the data) to estimate total professional experience in years. You may approximate to one decimal place.
    - If dates are entirely missing/unclear, set candidate_years = 0 and explain this.
    - If the candidate’s self-stated years of experience (e.g., in basics.summary) conflicts with the date-based calculation:
    - You MUST use the **date-based calculation** as candidate_years for scoring.
    - Briefly mention the discrepancy in minimum_years_experience.analysis.
    - If required_years == 0:
    - minimum_years_experience.score = 50
    - analysis: explain that minimum years requirement is not stated.
    - Else:
    - minimum_years_experience.score = min(100, round(100 * candidate_years / required_years))
    - Output:
    - minimum_years_experience.candidate_years: numeric estimate (using the rule above)
    - minimum_years_experience.required_years: value from job_data["requirements"]["minimum_years_experience"]
    - minimum_years_experience.analysis: explain how you derived candidate_years, how it compares to required_years, and mention any discrepancy with self-stated years.

    4) required_education

    - Read required_education from job_data["requirements"]["required_education"] (object).
    - If this object is missing or "required" is false:
        - required_education.score = 50
        - analysis: explain that no strict education requirement is stated.
    - If it is present and required:
        - Compare candidate_data["education"] entries to:
        - required_education["level"] (e.g., "Bachelor's degree")
        - required_education["field"] (e.g., "Computer Science, Software Engineering, or related technical field").
    - Scoring:
    - If the candidate clearly meets or exceeds the required level and the field is clearly related, score = 100.
    - If the candidate clearly does NOT meet the level (e.g., no degree, or only high school when a Bachelor’s is required), score = 0.
    - If it is ambiguous (e.g., related-sounding field but not clearly listed, or unclear level), score = 50 and explain why.
    - Output:
    - required_education.score
    - required_education.analysis: concise explanation referencing the candidate’s actual education entries and the requirement.
    - required_education.candidate_education: short summary string of the candidate’s highest relevant education.
    - required_education.required_education: short summary string of the job’s required education.

    5) overall_score

    - Compute as weighted average of component scores:
    - must_have_skills.score: weight 45
    - nice_to_have_skills.score: weight 20
    - minimum_years_experience.score: weight 20
    - required_education.score: weight 15
    - overall_score = round(weighted_average, 1) and must be between 0 and 100.
    - Ensure that overall_score logically reflects the narrative:
    - If multiple must-haves are clearly matched, the overall_score should not be extremely low.
    - If most must-haves are missing, the overall_score should be low.

    6) recommendation

    You MUST follow these thresholds exactly based on overall_score:
    - If overall_score >= 85: recommendation = "Highly Recommended"
    - Else if overall_score >= 70: recommendation = "Recommended"
    - Else if overall_score >= 50: recommendation = "Consider"
    - Else: recommendation = "Not Recommended"

    The recommendation MUST be consistent with overall_score.

    =====================
    GENERAL GUIDELINES
    =====================

    - Search for evidence across ALL parts of candidate_data:
    - basics, skills, work (position, summary, highlights), projects, education, certifications, interests.
    - Strengths:
    - List 2–5 concise strengths grounded in job requirements and candidate evidence
        (e.g., tech stack matches, years of experience, concrete achievements, relevant domains, cloud experience).
    - Weaknesses:
    - List 2–5 concise weaknesses / risk factors grounded in job requirements
        (e.g., missing Kubernetes, no microservices experience, short on years, not yet senior/lead, missing CI/CD).
    - Do NOT invent tools, technologies, responsibilities, or achievements not present in candidate_data.
    - Be explicit when experience is limited or partial instead of claiming “no experience” where some evidence exists.

    Return the result using this structured schema:
    - overall_score (number)
    - must_have_skills: {{
        "score": number,
        "analysis": string,
        "matched_skills": [strings from job_data.requirements.must_have_skills],
        "missing_skills": [strings from job_data.requirements.must_have_skills]
    }}
    - nice_to_have_skills: same structure using job_data.requirements.nice_to_have_skills
    - minimum_years_experience: {{
        "score": number,
        "analysis": string,
        "candidate_years": number,
        "required_years": number
    }}
    - required_education: {{
        "score": number,
        "analysis": string,
        "candidate_education": string or null,
        "required_education": string or null
    }}
    - summary: string (brief overall assessment)
    - strengths: [string]
    - weaknesses: [string]
    - recommendation: string (one of: "Highly Recommended", "Recommended", "Consider", "Not Recommended")"""
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
