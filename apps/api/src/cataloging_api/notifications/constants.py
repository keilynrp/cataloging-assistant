import uuid

# Fixed, deterministic identifier for the single approved P0 recipient. Personal
# fan-out (per-catalogador recipient_id) is out of scope until session identity exists.
PILOT_RECIPIENT_ID = uuid.uuid5(
    uuid.NAMESPACE_URL, "urn:cataloging-api:recipients:pilot-catalogers"
)


class EventType:
    SYNC_COMPLETED = "sync.completed"
    SYNC_FAILED = "sync.failed"
    ITEMS_CHANGED = "items.changed"
    DIAGNOSTICS_CHANGED = "diagnostics.changed"
    DRAFT_STALE = "draft.stale"
    REVIEW_DEFERRED = "review.deferred"
    SUGGESTION_PENDING = "suggestion.pending"
    VOCABULARY_PROMOTED = "vocabulary.promoted"
    # P2 (NTF-012): periodic digest, built from the P0 catalog below. Not part
    # of the approved P0 catalog itself, kept out of P0_EVENT_TYPES so that set
    # stays a faithful record of what VERTICAL-014's P0 decisions approved.
    DIGEST_SUMMARY = "digest.summary"


P0_EVENT_TYPES = frozenset(
    {
        EventType.SYNC_COMPLETED,
        EventType.SYNC_FAILED,
        EventType.ITEMS_CHANGED,
        EventType.DIAGNOSTICS_CHANGED,
        EventType.DRAFT_STALE,
        EventType.REVIEW_DEFERRED,
        EventType.SUGGESTION_PENDING,
        EventType.VOCABULARY_PROMOTED,
    }
)

# Every event type a recipient may see or mute, including later additions on
# top of the approved P0 catalog.
KNOWN_EVENT_TYPES = P0_EVENT_TYPES | {EventType.DIGEST_SUMMARY}
