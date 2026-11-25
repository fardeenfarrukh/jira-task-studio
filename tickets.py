ISSUE_TYPES = ["Epic", "Story", "Task", "Subtask", "Bug"]
PRIORITIES = ["High", "Medium", "Low"]
CLASSIFICATIONS = [
    "Confirmed",
    "Inferred",
    "Proposed recommendation",
    "Requires clarification"
]

def _items(value):
    if isinstance(value, str):
        return [
            item.strip(" -•\t")
            for item in value.splitlines()
            if item.strip()
        ]

    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    return []

def _split_values(value):
    if isinstance(value, list):
        return _items(value)

    return [
        item.strip()
        for item in str(value or "").split(",")
        if item.strip()
    ]

def _issue_type(value):
    issue_type = str(value or "Task").strip().lower()

    aliases = {
        "sub-task": "Subtask",
        "sub task": "Subtask"
    }

    if issue_type in aliases:
        return aliases[issue_type]

    return issue_type.title()

def normalize_tickets(data, valid_ids):
    tickets = []
    warnings = []
    seen_ids = set()
    valid_ids = set(valid_ids)

    for index, row in enumerate(data.get("tickets", []), 1):
        if not isinstance(row, dict):
            warnings.append(f"Ticket {index}: invalid ticket data was skipped")
            continue

        ticket_id = str(row.get("id") or "").strip() or f"T-{index:03}"

        if ticket_id in seen_ids:
            warnings.append(f"Duplicate ticket ID '{ticket_id}' was skipped")
            continue

        seen_ids.add(ticket_id)

        issue_type = _issue_type(row.get("type"))

        if issue_type not in ISSUE_TYPES:
            warnings.append(
                f"{ticket_id}: unsupported type '{issue_type}' changed to Task"
            )
            issue_type = "Task"

        priority = str(row.get("priority") or "Medium").strip().title()

        if priority not in PRIORITIES:
            warnings.append(
                f"{ticket_id}: unsupported priority changed to Medium"
            )
            priority = "Medium"

        refs = _items(row.get("requirement_refs"))
        unknown_refs = sorted(set(refs) - valid_ids)

        if unknown_refs:
            warnings.append(
                f"{ticket_id}: removed unknown requirement references: "
                + ", ".join(unknown_refs)
            )

        classification = str(
            row.get("classification") or "Confirmed"
        ).strip()

        if classification not in CLASSIFICATIONS:
            classification = "Requires clarification"

        tickets.append({
            "id": ticket_id,
            "type": issue_type,
            "parent_id": str(row.get("parent_id") or "").strip(),
            "summary": str(row.get("summary") or "").strip(),
            "description": str(row.get("description") or "").strip(),
            "criteria": _items(row.get("acceptance_criteria")),
            "priority": priority,
            "labels": _items(row.get("labels")),
            "refs": [ref for ref in refs if ref in valid_ids],
            "classification": classification
        })

    warnings.extend(validate_tickets(tickets))

    extra_warnings = data.get("warnings", [])
    if isinstance(extra_warnings, list):
        warnings.extend(str(warning) for warning in extra_warnings)

    return tickets, sorted(set(warnings))

def editor_rows(tickets):
    return [{
        "ID": ticket["id"],
        "Type": ticket["type"],
        "Parent ID": ticket["parent_id"],
        "Summary": ticket["summary"],
        "Description": ticket["description"],
        "Acceptance Criteria": "\n".join(ticket["criteria"]),
        "Priority": ticket["priority"],
        "Labels": ", ".join(ticket["labels"]),
        "Requirement Refs": ", ".join(ticket["refs"]),
        "Classification": ticket["classification"]
    } for ticket in tickets]

def tickets_from_editor(frame):
    result = []

    for index, row in enumerate(
        frame.fillna("").to_dict(orient="records"), 1
    ):
        result.append({
            "id": str(row.get("ID") or f"MANUAL-{index:03}").strip(),
            "type": _issue_type(row.get("Type")),
            "parent_id": str(row.get("Parent ID") or "").strip(),
            "summary": str(row.get("Summary") or "").strip(),
            "description": str(row.get("Description") or "").strip(),
            "criteria": _items(row.get("Acceptance Criteria")),
            "priority": str(row.get("Priority") or "Medium").strip().title(),
            "labels": _split_values(row.get("Labels")),
            "refs": _split_values(row.get("Requirement Refs")),
            "classification": str(
                row.get("Classification") or "Confirmed"
            ).strip()
        })

    return result

def coverage_report(requirements, tickets):
    report = []

    for requirement in requirements:
        requirement_id = str(requirement.get("id", ""))

        linked_tickets = [
            ticket["id"]
            for ticket in tickets
            if requirement_id in ticket["refs"]
            and ticket["type"] != "Epic"
        ]

        report.append({
            "Requirement": requirement_id,
            "Description": requirement.get("description", ""),
            "Status": "Linked — review ticket" if linked_tickets else "Uncovered",
            "Tickets": ", ".join(linked_tickets)
        })

    return report

def validate_tickets(tickets):
    warnings = []
    ticket_ids = [ticket.get("id", "") for ticket in tickets]
    known_ids = set(ticket_ids)

    if len(ticket_ids) != len(known_ids):
        warnings.append("Duplicate ticket IDs exist.")

    tickets_by_id = {
        ticket.get("id"): ticket
        for ticket in tickets
    }

    epic_children = {
        ticket_id: []
        for ticket_id, ticket in tickets_by_id.items()
        if ticket.get("type") == "Epic"
    }

    for ticket in tickets:
        ticket_id = ticket.get("id", "")
        issue_type = ticket.get("type", "")
        parent_id = ticket.get("parent_id", "")

        if not ticket.get("summary", "").strip():
            warnings.append(f"{ticket_id}: summary is blank")

        if issue_type not in ISSUE_TYPES:
            warnings.append(f"{ticket_id}: invalid issue type")

        if ticket.get("priority") not in PRIORITIES:
            warnings.append(f"{ticket_id}: invalid priority")

        if ticket.get("classification") not in CLASSIFICATIONS:
            warnings.append(f"{ticket_id}: invalid classification")

        if issue_type == "Epic" and parent_id:
            warnings.append(f"{ticket_id}: an Epic should not have a parent")
        
        elif issue_type == "Epic":
            continue

        elif not parent_id:
            warnings.append(
                f"{ticket_id}: {issue_type} is missing a parent"
            )

        elif parent_id == ticket_id:
            warnings.append(
                f"{ticket_id}: ticket cannot be its own parent"
            )

        elif parent_id not in known_ids:
            warnings.append(
                f"{ticket_id}: parent {parent_id} does not exist"
            )

        else:
            parent = tickets_by_id[parent_id]
            parent_type = parent.get("type", "")

            if issue_type == "Subtask":
                if parent_type in ["Epic", "Subtask"]:
                    warnings.append(
                        f"{ticket_id}: a Subtask needs a Story, Task, "
                        "or Bug as its parent"
                    )

            elif parent_type != "Epic":
                warnings.append(
                    f"{ticket_id}: a {issue_type} normally belongs "
                    "under an Epic"
                )

            if parent_type == "Epic":
                epic_children[parent_id].append(ticket_id)

    # Check for Epics without actionable children.
    for epic_id, children in epic_children.items():
        if not children:
            warnings.append(
                f"{epic_id}: Epic has no child tickets"
            )

    # Check for circular parent relationships.
    for ticket in tickets:
        visited = set()
        current_id = ticket.get("id", "")

        while current_id in tickets_by_id:
            if current_id in visited:
                warnings.append(
                    f"{ticket.get('id')}: circular parent relationship detected"
                )
                break

            visited.add(current_id)
            current_id = tickets_by_id[current_id].get("parent_id", "")

    return sorted(set(warnings))
