import json
import re
import time
import random

from google.genai import types

MAX_ATTEMPTS = 5
RETRY_DELAYS = (3, 6, 12, 20)

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

RETRYABLE_STATUS_NAMES = {
    "DEADLINE_EXCEEDED",
    "INTERNAL",
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE"
}

ANALYSIS_PROMPT = """Analyze the complete project scope and extract its requirements.

Return valid JSON only, using this structure:
{
  "project_name": "",
  "objective": "",
  "requirements": [
    {
      "id": "REQ-001",
      "description": "",
      "source_section": "",
      "classification": "Confirmed",
      "priority": "High"
    }
  ],
  "exclusions": [],
  "technology": [],
  "questions": []
}

Instructions:
- Review objectives, deliverables, inclusions, success criteria, technologies, constraints, and final deliverables.
- Identify all meaningful functional and non-functional requirements.
- Assign sequential IDs: REQ-001, REQ-002, REQ-003, etc.
- Classify requirements as Confirmed or Inferred.
- Assign High, Medium, or Low priority based on importance and project impact.
- Record the source section for traceability when identifiable.
- Keep explicitly excluded features separate from requirements.
- List technologies explicitly mentioned or clearly established in the scope.
- Identify important missing information as clarification questions.
- Do not invent features, technical decisions, or requirements.
- Avoid duplicate or overlapping requirements.
- Preserve important business rules, constraints, and success criteria.

Project name: {project_name}
"""

TICKET_PROMPT = """Create a practical, complete, and well-organized JIRA development backlog using the project analysis below.

Return valid JSON only, using this structure:
{
  "tickets": [
    {
      "id": "T-001",
      "type": "Epic",
      "parent_id": "",
      "summary": "",
      "description": "",
      "acceptance_criteria": [],
      "priority": "High",
      "labels": [],
      "requirement_refs": [],
      "classification": "Confirmed"
    }
  ],
  "warnings": []
}

Allowed ticket types: Epic, Story, Task, Subtask, Bug.
Allowed priorities: High, Medium, Low.
Allowed classifications: Confirmed, Inferred, Proposed recommendation, Requires clarification.

1. BACKLOG STRUCTURE AND DECOMPOSITION

- Use Epics for major project work areas or functional domains.
- Use Stories for meaningful user-facing features and capabilities.
- Use Tasks for technical implementation, infrastructure, integrations, and supporting work.
- Use Subtasks only when a Story or Task genuinely requires further breakdown.
- Do not create Bugs for hypothetical problems.
- Epics organize work; they must not replace actionable implementation tickets.
- Every Epic representing actual project work must have appropriate child Stories or Tasks.
- Break major functional modules into separate meaningful Stories where appropriate.
- Create separate technical Tasks for substantial infrastructure and implementation work.
- If frontend, backend, testing, deployment, documentation, or handover are substantial work areas, represent them with appropriate actionable tickets and Epics where justified.
- Every Story and Task should normally have a parent Epic.
- Verify that every parent_id references an existing valid parent.
- Do not create unnecessary hierarchy, arbitrary ticket counts, duplicate work, or excessive fragmentation.
- The final backlog must be understandable as an actionable development plan, not just a list of high-level ideas.

2. FRONTEND AND BACKEND IMPLEMENTATION

- Identify frontend and backend responsibilities separately whenever both are required.
- Create explicit frontend implementation Stories or Tasks using the specified frontend technology.
- Frontend implementation must cover actual application development, including relevant screens, components, forms, navigation, and user interactions.
- UI/UX design, wireframes, and prototypes do not count as completed frontend implementation.
- Create explicit backend implementation Stories or Tasks using the specified programming language and framework where applicable.
- Backend work must represent actual business logic, services, APIs, and integrations required by the scope.
- API documentation or planning does not replace API implementation.
- Include frontend-to-backend API integration where required.
- Do not combine substantial frontend and backend implementation into one vague ticket.
- Verify that each major specified frontend and backend technology has corresponding implementation work.

3. TECHNICAL IMPLEMENTATION

- Use the technologies explicitly specified in the project analysis.
- Represent relevant programming languages, frameworks, databases, platforms, and integrations in implementation tickets.
- Include database schema design, implementation, and integration where required.
- Include API development, request validation, error handling, and integration where required.
- Include authentication, authorization, and security controls when specified.
- Include deployment configuration, environment setup, and infrastructure work where required.
- Do not invent cloud services, libraries, infrastructure, or technical decisions that the scope does not establish.
- Put unresolved technical decisions in clarification questions or warnings rather than presenting assumptions as confirmed decisions.

4. FUNCTIONAL REQUIREMENTS AND WORKFLOWS

- Represent every major deliverable and functional module in the scope.
- Break substantial modules into meaningful implementation work.
- Include important workflows, business rules, validation, constraints, and success criteria.
- Pay particular attention to explicit deliverables and operational requirements.
- Do not create tickets for excluded features.
- For scheduling and booking systems, distinguish resource availability management from appointment booking.
- Where required, cover working schedules, availability checks, booking validation, conflict prevention, rescheduling, and cancellation.
- Represent both frontend and backend responsibilities for these workflows where applicable.
- When resource or staff availability is required, explicitly include schedule management and availability checking.
- A resource profile or double-booking prevention alone does not represent complete availability management.

5. TESTING AND QUALITY ASSURANCE

- Include appropriate unit, integration, functional, and security testing based on the project scope.
- Cover important business rules, validation, workflows, and success criteria.
- Include frontend and backend testing where applicable.
- Include deployment verification and acceptance testing where required.
- Do not represent all QA work through one generic testing ticket when specific testing activities are necessary.

6. TIMELINE AND MILESTONES

- Reflect project phases, milestones, and timelines from the analysis in relevant ticket descriptions or labels where useful.
- Do not invent dates, deadlines, sprint assignments, or estimates.
- Do not create separate tickets solely to represent dates or timeline entries.

7. DOCUMENTATION AND HANDOVER

- Include requirements, technical, API, setup, deployment, and user documentation where required.
- Distinguish documentation activities from implementation work.
- Include handover activities when they are explicit project deliverables.

8. ACCEPTANCE CRITERIA AND TICKET QUALITY

- Write clear, specific, and testable acceptance criteria.
- Describe observable outcomes rather than vague statements such as "works correctly" or "is user-friendly."
- Include relevant validation rules, expected behavior, and constraints.
- Explain the purpose and expected implementation outcome in each ticket description.
- Use concise, descriptive summaries.
- Avoid duplicate tickets, unnecessary fragmentation, and excessive detail.
- Prefer a manageable number of meaningful tickets over an unnecessarily large backlog.
- Make tickets understandable to both technical and non-technical reviewers.

9. REQUIREMENT TRACEABILITY

- Use the exact requirement IDs supplied in the project analysis.
- Link each ticket only to requirements it directly implements, supports, or verifies.
- A requirement may be linked to multiple tickets when separate implementation or testing work is necessary.
- Do not assign unrelated requirement references merely to increase coverage.
- Ensure every requirement is covered by at least one appropriate ticket or explicitly identified in warnings.
- Never silently omit a requirement.

10. CLASSIFICATION, ASSUMPTIONS, AND WARNINGS

- Use Confirmed for work directly supported by the project scope.
- Use Inferred for work reasonably implied by the requirements but not explicitly stated.
- Use Proposed recommendation for useful additional work that is not an established requirement.
- Use Requires clarification when an important decision or detail is missing.
- Do not invent assignees, estimates, story points, dates, or unconfirmed technical decisions.
- Record important unresolved questions, assumptions, and uncovered requirements in warnings.
- Do not turn every missing detail into a ticket.
- Do not present proposed recommendations or inferred work as confirmed requirements.

11. FINAL BACKLOG VALIDATION

Before returning the JSON, verify that:

- All major deliverables and requirements are represented.
- Every requirement is linked to appropriate work or identified in warnings.
- Frontend and backend implementation are explicitly represented where applicable.
- The specified technology stack is reflected in implementation tickets.
- Important business rules, workflows, and success criteria have corresponding work.
- Testing, deployment, documentation, and handover are covered where required.
- Excluded features and unsupported assumptions have not been introduced.
- Every major project work area has actionable child tickets.
- Every Story and Task has an appropriate parent Epic unless there is a clear reason otherwise.
- No required deliverable is represented only in an Epic description.
- No important functional requirement is represented only by a broad or generic ticket.
- All parent references are valid.
- Ticket summaries, descriptions, acceptance criteria, classifications, and requirement references are complete and consistent.

Return only the JSON object. Do not include Markdown fences or explanatory text.

PROJECT ANALYSIS:
{analysis}
"""

def _json_response(response_text):
    if not response_text:
        raise ValueError("Gemini returned an empty response.")

    cleaned_text = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        response_text.strip(), 
        flags=re.I
    )

    try:
        parsed_data = json.loads(cleaned_text)
    except json.JSONDecodeError:
        start = cleaned_text.find("{")
        end = cleaned_text.rfind("}")

        if start == -1 or end <= start:
            raise ValueError("Gemini did not return valid JSON.")

        parsed_data = json.loads(cleaned_text[start:end + 1])

    if not isinstance(parsed_data, dict):
        raise ValueError("Gemini response must be a JSON object.")

    return parsed_data

def _is_retryable_error(error):
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True

    status_values = [
        getattr(error, "code", None),
        getattr(error, "status_code", None),
        getattr(error, "status", None)
    ]

    response = getattr(error, "response", None)

    if response is not None:
        status_values.append(
            getattr(response, "status_code", None)
        )

    for status in status_values:
        if status is None:
            continue

        try:
            if int(status) in RETRYABLE_STATUS_CODES:
                return True
        except (TypeError, ValueError):
            pass

        if str(status).upper() in RETRYABLE_STATUS_NAMES:
            return True

    error_text = str(error).upper()

    for status_name in RETRYABLE_STATUS_NAMES:
        if status_name in error_text:
            return True

    if re.search(r"\b(408|429|500|502|503|504)\b", error_text):
        return True

    connection_errors = [
        "CONNECTION RESET",
        "CONNECTION REFUSED",
        "TIMED OUT",
        "TEMPORARY FAILURE",
        "NETWORK IS UNREACHABLE"
    ]

    return any(message in error_text for message in connection_errors)

def _ask_gemini(
    gemini_client, 
    model_name, 
    prompt, 
    pdf_data=None,
    progress_callback=None
):
    prompt_parts = [prompt]

    if pdf_data:
        prompt_parts.append(
            types.Part.from_bytes(
                data=pdf_data,
                mime_type="application/pdf"
            )
        )

    for attempt in range(MAX_ATTEMPTS):

        if progress_callback:
            progress_callback(
                f"Contacting Gemini — attempt {attempt + 1} of {MAX_ATTEMPTS}..."
            )

        try:
            api_response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt_parts,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            
            return _json_response(api_response.text)

        except Exception as error:

            if not _is_retryable_error(error):
                raise

            if attempt == MAX_ATTEMPTS - 1:
                raise RuntimeError(
                    f"Gemini request failed after {MAX_ATTEMPTS} attempts. "
                    "The service may be temporarily overloaded or rate-limited. "
                    "Please wait a few minutes before trying again. "
                    f"Last error: {error}"
                ) from error

            delay = RETRY_DELAYS[attempt] + random.uniform(0, 1.5)

            if progress_callback:
                progress_callback(
                    "Gemini is temporarily unavailable. "
                    f"Retrying in {delay:.1f} seconds "
                    f"(attempt {attempt + 2} of {MAX_ATTEMPTS})."
                )

            time.sleep(delay)

    raise RuntimeError("Gemini request failed.")

def analyze_scope(
        gemini_client, 
        model_name, 
        project_name, 
        uploaded_file, 
        scope_text
):
    analysis_prompt = ANALYSIS_PROMPT.replace(
        "{project_name}",
        project_name or "Not provided"
    )

    pdf_data = None

    if uploaded_file:
        file_data = uploaded_file.getvalue()

        if uploaded_file.name.lower().endswith(".pdf"):
            pdf_data = file_data
        else:
            analysis_prompt += "\n\nUPLOADED SCOPE:\n"
            analysis_prompt += file_data.decode(
                "utf-8-sig", 
                errors="replace"
            )

    if scope_text.strip():
        analysis_prompt += "\n\nADDITIONAL SCOPE TEXT:\n"
        analysis_prompt += scope_text.strip()

    analysis_result = _ask_gemini(
        gemini_client,
        model_name,
        analysis_prompt,
        pdf_data
    )

    for field in (
        "requirements", 
        "exclusions", 
        "technology", 
        "questions"
    ):
        if not isinstance(analysis_result.get(field), list):
            analysis_result[field] = []

    return analysis_result

def generate_tickets(
        gemini_client, 
        model_name, 
        project_analysis,
        progress_callback=None
):
    ticket_prompt = TICKET_PROMPT.replace(
        "{analysis}",
        json.dumps(project_analysis, ensure_ascii=False)
    )

    ticket_result = _ask_gemini(
        gemini_client,
        model_name,
        ticket_prompt,
        progress_callback=progress_callback
    )

    if not isinstance(ticket_result.get("tickets"), list):
        raise ValueError(
            "Gemini did not return a valid ticket list. Please try again."
        )

    return ticket_result