import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai

from ai import analyze_scope, generate_tickets
from jira_csv import make_jira_csv
from tickets import (
    ISSUE_TYPES,
    PRIORITIES,
    editor_rows,
    normalize_tickets,
    tickets_from_editor,
    coverage_report,
    validate_tickets
)

load_dotenv()
st.set_page_config(page_title="JIRA Task Studio", page_icon="🧭", layout="wide")
st.title("JIRA Task Studio")
st.caption("Turn a project scope into reviewed JIRA tickets and one import-ready CSV.")

with st.sidebar:
    st.subheader("Gemini settings")
    api_key = st.text_input("Gemini API key", value=os.getenv("GEMINI_API_KEY", ""), type="password")
    model = st.text_input("Gemini model", value=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
    st.caption("The key is used by the server-side Python app. Do not commit it to Git.")

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "tickets" not in st.session_state:
    st.session_state.tickets = None

if "ticket_version" not in st.session_state:
    st.session_state.ticket_version = 0

if "ai_warnings" not in st.session_state:
    st.session_state.ai_warnings = []

st.subheader("1. Add project scope")
project_name = st.text_input("Project name (optional)")
upload = st.file_uploader("Upload PDF, TXT or Markdown", type=["pdf", "txt", "md"])
scope_text = st.text_area("Or paste the project scope", height=130)

if st.button("Analyze project scope", type="primary", disabled=not api_key.strip() or (not upload and not scope_text.strip())):
    try:
        with st.spinner("Gemini is extracting the project requirements..."):
            st.session_state.analysis = analyze_scope(
                genai.Client(api_key=api_key),
                model,
                project_name,
                upload,
                scope_text
            )
            st.session_state.tickets = None
            st.session_state.ai_warnings = []
        st.success("Scope analysis complete.")
    except Exception as exc:
        st.error(f"Analysis failed: {exc}")

analysis = st.session_state.analysis
if analysis:
    st.divider()
    st.subheader("2. Review extracted requirements")
    st.write(f"**{analysis.get('project_name') or project_name or 'Project'}**")
    st.write(analysis.get("objective", ""))
    requirements = analysis.get("requirements", [])
    st.metric("Requirements identified", len(requirements))
    st.dataframe(pd.DataFrame(requirements), use_container_width=True, hide_index=True)
    with st.expander("Exclusions, technology and questions"):
        st.markdown("**Excluded scope**")
        st.write(analysis.get("exclusions", []) or "None identified")
        st.markdown("**Technology mentioned in the scope**")
        st.write(analysis.get("technology", []) or "None identified")
        st.markdown("**Clarification questions**")
        st.write(analysis.get("questions", []) or "None identified")

    if st.button(
        "Generate JIRA tickets",
        type="primary",
        disabled=not api_key.strip() or not model.strip()
    ):
        try:
            with st.spinner("Gemini is breaking the scope into Epics and tickets..."):
                raw = generate_tickets(genai.Client(api_key=api_key), model, analysis)
                valid_ids = {str(r.get("id")) for r in requirements if r.get("id")}
                st.session_state.tickets, st.session_state.ai_warnings = normalize_tickets(raw, valid_ids)
                st.session_state.ticket_version += 1
            st.success(f"Generated {len(st.session_state.tickets)} tickets.")
        except Exception as exc:
            st.error(f"Ticket generation failed: {exc}")

if st.session_state.tickets is not None:
    st.divider()
    st.subheader("3. Review and edit tickets")
    counts = pd.Series([t["type"] for t in st.session_state.tickets]).value_counts().to_dict()
    cols = st.columns(len(ISSUE_TYPES))
    for col, kind in zip(cols, ISSUE_TYPES):
        col.metric(kind + "s", counts.get(kind, 0))

    edited = st.data_editor(
        pd.DataFrame(editor_rows(st.session_state.tickets)),
        key=f"ticket_editor_{st.session_state.ticket_version}",
        use_container_width=True, hide_index=True, num_rows="dynamic", height=480,
        column_config={
            "Type": st.column_config.SelectboxColumn(options=ISSUE_TYPES, required=True),
            "Priority": st.column_config.SelectboxColumn(options=PRIORITIES),
            "Description": st.column_config.TextColumn(width="large"),
            "Acceptance Criteria": st.column_config.TextColumn(width="large", help="One criterion per line."),
        },
    )
    current = tickets_from_editor(edited)
    report = coverage_report(requirements, current)
    warnings = list(st.session_state.get("ai_warnings", [])) + validate_tickets(current)

    st.subheader("4. Requirement coverage")
    coverage_df = pd.DataFrame(report)
    if not coverage_df.empty:
        covered = (coverage_df["Status"] == "Linked — review ticket").sum()
        a, b = st.columns(2)
        a.metric("Requirements linked to tickets", int(covered))
        b.metric("Requirements not linked", int(len(report) - covered))
        st.dataframe(coverage_df, use_container_width=True, hide_index=True)
    if warnings:
        st.warning("Review the warnings above before importing this CSV into Jira.")
        with st.expander(f"Warnings to review ({len(warnings)})", expanded=True):
            for warning in warnings:
                st.warning(warning)

    st.subheader("5. Download Jira CSV")
    st.caption("Review the tickets and hierarchy before downloading. Jira may require an initial field-mapping step; hierarchy import depends on your Jira permissions and project configuration.")
    st.download_button(
        "Download Jira import CSV", make_jira_csv(current),
        file_name="jira_task_studio_import.csv", mime="text/csv", type="primary", use_container_width=True,
    )
    with st.expander("Jira import notes"):
        st.markdown("""
        For an import that preserves Epic → Story/Task → Sub-task relationships, use Jira's administrator **External System Import → CSV** route where available. Map **Work item ID**, **Work type**, **Parent**, **Summary**, **Description**, **Priority**, and **Labels** to the destination project's fields. The simpler self-service importer may not preserve multi-level hierarchy. The exact process depends on your Jira deployment, project configuration, and permissions.

        [Atlassian CSV import guidance](https://support.atlassian.com/jira-cloud-administration/docs/import-data-from-a-csv-file/)
        """)

st.caption("Proof of concept · Gemini analysis · CSV export · No live Jira connection")
