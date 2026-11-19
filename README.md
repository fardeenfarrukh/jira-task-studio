# JIRA Task Studio — Lean Python POC

A small local app that turns a project PDF or pasted brief into editable Jira tickets and one CSV export.

## Files

```text
app.py       Streamlit interface and workflow
ai.py        Gemini prompts, PDF input and model calls
tickets.py   Ticket cleanup, editing, basic coverage and checks
jira_csv.py  Jira CSV generation with parent references
```

## Run on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
streamlit run app.py
```

Put your Gemini API key in `.env`, then open the local URL Streamlit prints (usually `http://localhost:8501`).

## Workflow

1. Upload a PDF/TXT/Markdown file or paste the project scope.
2. Analyze requirements with Gemini.
3. Review the requirements and exclusions.
4. Generate and edit Epics, Stories, Tasks, Subtasks and justified Bugs.
5. Review requirement links and warnings.
6. Download one Jira-oriented CSV.

## Jira import note

The CSV has one row per work item and local IDs for the `Parent` relationships. To preserve hierarchy, use Jira's administrator **External System Import → CSV** route where available, map the columns to the destination project's fields, and confirm the mapping with a test import. Jira permissions and project configuration vary. This POC does not connect to Jira directly.

[Atlassian CSV import guidance](https://support.atlassian.com/jira-cloud-administration/docs/import-data-from-a-csv-file/)

## Notes

- This is a prototype, not production software.
- The coverage table reports which requirements are linked to non-Epic tickets; it does not prove the linked ticket fully satisfies the requirement. Review the content.
- Use non-confidential sample documents unless the organization approves sending project data to the Gemini API account being used.
- Keep `.env` private and never commit your API key.
