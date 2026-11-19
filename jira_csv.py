import csv
import io

def make_jira_csv(tickets):
    tickets_by_id = {ticket["id"]: ticket for ticket in tickets}

    ordered_tickets = []
    completed_ids = set()
    pending_tickets = list(tickets)

    while pending_tickets:
        ready_tickets = [
            ticket for ticket in pending_tickets
            if not ticket["parent_id"]
            or ticket["parent_id"] in completed_ids
            or ticket["parent_id"] not in tickets_by_id
        ]

        if not ready_tickets:
            ready_tickets = [pending_tickets[0]]

        for ticket in ready_tickets:
            ordered_tickets.append(ticket)
            completed_ids.add(ticket["id"])
            pending_tickets.remove(ticket)

    import_ids = {
        ticket["id"]: str(index)
        for index, ticket in enumerate(ordered_tickets, 1)
    }

    columns = [
        "Work item ID",
        "Work type",
        "Summary",
        "Description",
        "Priority",
        "Labels",
        "Parent"
    ]

    csv_output = io.StringIO(newline="")
    csv_writer = csv.DictWriter(csv_output, fieldnames=columns)
    csv_writer.writeheader()

    for ticket in ordered_tickets:
        description_parts = [ticket["description"]]
        if ticket["criteria"]:
            acceptance_criteria = "\n".join(
                f"- {criterion}" for criterion in ticket["criteria"]
            )
            description_parts.append(
                "Acceptance Criteria:\n" + acceptance_criteria
            )

        if ticket["refs"]:
            description_parts.append(
                "Source Requirements: " + ", ".join(ticket["refs"])
            )

        if ticket["classification"] != "Confirmed":
            description_parts.append(
                "Classification: " + ticket["classification"]
            )

        csv_writer.writerow({
            "Work item ID": import_ids[ticket["id"]],
            "Work type": "Sub-task" if ticket["type"] == "Subtask" else ticket["type"],
            "Summary": ticket["summary"],
            "Description": "\n\n".join(
                part for part in description_parts if part
            ),
            "Priority": ticket["priority"],
            "Labels": ", ".join(ticket["labels"]),
            "Parent": import_ids.get(ticket["parent_id"], "")
        })

    return csv_output.getvalue().encode("utf-8-sig")

        
