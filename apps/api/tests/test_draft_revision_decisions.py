import uuid

from cataloging_api.drafts.decisions import decision_fingerprint


def test_draft_decision_fingerprint_is_stable() -> None:
    item_uuid = uuid.uuid4()
    draft_id = uuid.uuid4()
    revision_id = uuid.uuid4()
    payload = {
        "item_uuid": item_uuid,
        "draft_id": draft_id,
        "revision_id": revision_id,
        "decision": "approved",
        "reviewer": "Yissel",
        "note": "Evidencia revisada.",
        "validation_override": False,
    }

    assert decision_fingerprint(**payload) == decision_fingerprint(**payload)


def test_draft_decision_fingerprint_tracks_material_changes() -> None:
    base = {
        "item_uuid": uuid.uuid4(),
        "draft_id": uuid.uuid4(),
        "revision_id": uuid.uuid4(),
        "decision": "approved",
        "reviewer": "Yissel",
        "note": "Evidencia revisada.",
        "validation_override": False,
    }
    changed_decision = {**base, "decision": "rejected"}
    changed_override = {**base, "validation_override": True}

    assert (
        len(
            {
                decision_fingerprint(**base),
                decision_fingerprint(**changed_decision),
                decision_fingerprint(**changed_override),
            }
        )
        == 3
    )
