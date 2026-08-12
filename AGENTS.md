# Repository instructions

- DSpace is the source of truth. This repository stores a rebuildable local index.
- Never add a DSpace write, submission, workflow, administration, or authentication operation without a superseding approved ADR.
- Keep `dc.subject.linguiscgroup` exactly as written.
- Preserve raw DSpace HAL+JSON alongside normalized records.
- Every synchronization change must remain incremental, idempotent, resumable, and auditable.
- Keep cataloguing rules independent from model providers.
- Add or update tests for every behavior change.
- Run development commands inside WSL from `/home/keilyn/cat`.

