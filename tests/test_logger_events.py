from jasper.observability.logger import SessionLogger


def test_task_completed_event_has_description():
    """Regression: TASK_COMPLETED must include description for board rendering."""
    captured = []

    class CapturingLogger(SessionLogger):
        def log(self, event_type, payload):
            captured.append((event_type, payload))

    logger = CapturingLogger()

    logger.log(
        "TASK_COMPLETED",
        {
            "task_id": "abc",
            "status": "completed",
            "description": "Fetch income statement for AAPL",
        },
    )

    completed_events = [p for e, p in captured if e == "TASK_COMPLETED"]
    assert len(completed_events) == 1
    assert "description" in completed_events[0], (
        "TASK_COMPLETED payload must include 'description' for RichLogger board rendering"
    )
    assert completed_events[0]["description"] != ""
