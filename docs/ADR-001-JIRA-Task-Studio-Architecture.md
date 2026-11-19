# ADR-001: JIRA Task Studio – Technology and Integration Approach

**Date:** November 18, 2026  
**Status:** Accepted – Proof of Concept

## 1. Context

The objective of JIRA Task Studio is to reduce the manual effort involved in translating project scopes into structured JIRA tickets.

Project requirements are often provided in business-level documents that need to be reviewed, understood, and divided into smaller, manageable development tasks before they can be entered into JIRA.

This process can involve significant manual effort, particularly when identifying requirements, organizing work into Epics and Stories, defining acceptance criteria, and establishing ticket relationships.

The proposed solution is a lightweight application that uses Google's Gemini API to analyze project scope documents and generate structured JIRA tickets for human review and export.

## 2. Decision

A Python-based application using Streamlit and the Google Gemini API was selected for the initial proof of concept.

The application follows a modular structure to keep its implementation simple and maintainable while separating the main responsibilities.

**Selected technologies:**

| Component | Technology |
|---|---|
| Programming Language | Python |
| Application Framework | Streamlit |
| AI Integration | Google Gemini API |
| Data Processing | Pandas |
| Input Formats | PDF, TXT, Markdown, and pasted text |
| Output Format | JIRA-compatible CSV |
| Initial Execution | Local environment |

The application is organized into the following core modules:

- `app.py` – Application interface and workflow.
- `ai.py` – Gemini integration, project analysis, and ticket generation.
- `tickets.py` – Ticket processing, normalization, and validation.
- `jira_csv.py` – JIRA-oriented CSV generation and export.

## 3. Proposed Workflow

The application follows a straightforward project-to-ticket workflow:

1. **Project Scope Input:** The user uploads a project scope document or pastes its contents into the application.
2. **AI Analysis:** Gemini identifies project objectives, requirements, deliverables, technologies, exclusions, dependencies, and areas requiring clarification.
3. **Ticket Generation:** The application uses the analysis to generate a structured hierarchy of proposed Epics, Stories, Tasks, and Subtasks where appropriate.
4. **Review and Validation:** The user reviews and edits the generated tickets before export.
5. **CSV Export:** The application generates a single CSV file containing the proposed tickets and their associated parent relationships.
6. **JIRA Import:** The CSV can be imported into a compatible JIRA project using the appropriate CSV import workflow and field mappings.

Human review is retained before tickets are exported. The application is intended to assist with initial project planning rather than make final development or resource-allocation decisions.

## 4. Alternatives Considered

**React and Node.js**

A separate frontend and backend architecture was considered. However, it would introduce additional development overhead and infrastructure for a proof of concept whose primary purpose is demonstrating AI-assisted analysis and ticket generation.

**Direct JIRA REST API Integration**

Direct integration would allow the application to create tickets within JIRA without requiring a manual CSV upload. This was deferred to keep the initial implementation lightweight and avoid requiring JIRA credentials, authentication configuration, and project-specific permissions before the workflow has been validated.

**JSON Export**

JSON was considered as an additional export format. However, CSV was selected as the sole export format because the immediate objective is to transfer generated tickets into JIRA rather than support multiple downstream integrations.

## 5. Consequences

**Benefits**

- Reduces the amount of code and infrastructure required for the initial implementation.
- Allows rapid development and iteration.
- Uses Gemini to assist with interpreting project requirements and decomposing work.
- Produces structured tickets that can be reviewed and edited before export.
- Supports a straightforward transfer of generated tickets into JIRA through CSV import.
- Keeps the application modular so additional functionality can be introduced later.

**Limitations**

- Ticket quality and requirement coverage depend on the accuracy of the AI-generated analysis.
- Generated tickets require human review before being used in an actual development project.
- CSV import compatibility depends on the destination JIRA configuration, available permissions, and field mappings.
- Preservation of Epic and parent-child relationships must be validated against the target JIRA import workflow.
- The current proof of concept does not create tickets directly through the JIRA REST API.
- The application has not yet undergone production security, deployment, or enterprise integration reviews.

## 6. Future Considerations

Following successful validation of the proof of concept, potential improvements include:

- Improving requirement extraction, coverage, and ticket-generation accuracy.
- Adding more comprehensive dependency and project timeline analysis.
- Introducing direct JIRA REST API integration.
- Improving handling of temporary Gemini API failures.
- Establishing an approved approach for processing internal project documents.
- Evaluating deployment and security requirements for potential team adoption.

These improvements will be considered based on feedback and the results of further testing.

## 7. Final Decision

Python, Streamlit, and the Google Gemini API were selected as the foundation for JIRA Task Studio's initial proof of concept.

CSV export was selected as the initial JIRA integration approach to demonstrate how project scope analysis and ticket generation could reduce manual ticket preparation.

The application will remain a lightweight, locally runnable prototype until its accuracy, usefulness, and compatibility with the team's JIRA environment have been evaluated.