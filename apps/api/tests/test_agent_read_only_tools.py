import inspect

from cataloging_api.agent import tools as agent_tools
from cataloging_api.agent.tools import TOOLS

FORBIDDEN_WRITE_CALLS = (
    "record_review_decision",
    "create_draft",
    "append_draft_revision",
    "decide_draft_revision",
    "replace_active_vocabulary",
    "persist_current_suggestions",
    "record_suggestion_decision",
    "upsert_item",
    "upsert_collection",
    "mark_missing_inactive",
)


def test_agent_tools_module_never_references_a_write_function() -> None:
    """VERTICAL-015 acceptance criterion 2: the agent never invokes a write
    endpoint, directly or indirectly. A source scan of the tools module (the
    only place tool handlers are wired) is a cheap, durable guard against a
    future tool accidentally importing a mutation."""
    source = inspect.getsource(agent_tools)
    for forbidden in FORBIDDEN_WRITE_CALLS:
        assert forbidden not in source, f"agent/tools.py must never reference {forbidden}"


def test_every_registered_tool_has_a_handler_and_schema() -> None:
    assert len(TOOLS) >= 9
    for tool in TOOLS:
        assert tool.name
        assert tool.description
        assert tool.input_schema.get("type") == "object"
        assert callable(tool.handler)


def test_agent_can_read_the_master_cataloging_contract() -> None:
    names = {tool.name for tool in TOOLS}
    assert "get_cataloging_contract" in names
