import json
import re

from google.genai import types

ANALYSIS_PROMPT = """Read the full project scope and identify its requirements.

Return JSON only with:
project_name, objective, requirements, exclusions, technology, questions.

Each requirement must include:
id (REQ-001, REQ-002, etc.), description, source_section,
classification (Confirmed or Inferred), priority (High, Medium, Low).

Use the objectives, deliverables, inclusions, success criteria, technologies, and final deliverables.

Keep exclusions separate. Do not invent features or details. Include questions where important information is missing.
Avoid duplicate requirements.

Project name: {project_name}
"""

TICKET_PROMPT = """Create a practical JIRA ticket plan from the project analysis.

Return JSON only:
{"tickets":[{"id":"T-001", "type":"Epic|Story|Task|Subtask|Bug","parent_id":"","summary":"","description":"","acceptance_criteria":["..."],"priority":"High|Medium|Low","labels":[],"requirement_refs":["REQ-001"],"classification":"Confirmed|Inferred|Proposed recommendation|Requires clarification"}],"warnings":[]}

Guidelines:
- Use Epics for major work areas, Stories for features, and Tasks for technical work.
- Use Subtasks only when necessary.
- Stories and Tasks should normally belong to an Epic.
- Do not create Bugs for hypothetical problems.
- Cover frontend, backend, database, APIs, testing, deployment, and documentation where required.
- Link requirements to actual implementation or testing tickets.
- Do not create tickets for excluded features.
- Do not invent assignees, estimates, story points, or dates.
- Distinguish confirmed work from assumptions and recommendations.
- Use testable acceptance criteria.
- Avoid duplicates and unnecessary small tasks.
- Ensure every requirement is covered or listed in warnings.

Project analysis:
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

def _ask_gemini(gemini_client, model_name, prompt, pdf_data=None):
    prompt_parts = [prompt]

    if pdf_data:
        prompt_parts.append(
            types.Part.from_bytes(
                data=pdf_data,
                mime_type="application/pdf"
            )
        )

    api_response = gemini_client.models.generate_content(
        model=model_name,
        contents=prompt_parts,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2
        )
    )

    return _json_response(api_response.text)

def analyze_scope(gemini_client, model_name, project_name, uploaded_file, scope_text):
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
            analysis_prompt += "\n\nUploaded scope:\n"
            analysis_prompt += file_data.decode("utf-8-sig", errors="replace")

    if scope_text.strip():
        analysis_prompt += "\n\nAdditional scope text:\n"
        analysis_prompt += scope_text.strip()

    analysis_result = _ask_gemini(
        gemini_client,
        model_name,
        analysis_prompt,
        pdf_data
    )

    for field in ("requirements", "exclusions", "technology", "questions"):
        if not isinstance(analysis_result.get(field), list):
            analysis_result[field] = []

    return analysis_result

def generate_tickets(gemini_client, model_name, project_analysis):
    ticket_prompt = TICKET_PROMPT.replace(
        "{analysis}",
        json.dumps(project_analysis, ensure_ascii=False)
    )

    ticket_result = _ask_gemini(
        gemini_client,
        model_name,
        ticket_prompt
    )

    if not isinstance(ticket_result.get("tickets"), list):
        raise ValueError("Gemini did not return a valid ticket list. Please try again.")

    return ticket_result