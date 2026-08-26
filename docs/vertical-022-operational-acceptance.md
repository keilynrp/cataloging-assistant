# VERTICAL-022 — Operational acceptance

## Status

**Accepted / operationalized**

Acceptance date: **2026-08-26**

VERTICAL-022 is considered operationally accepted after completing the governed production activation sequence and proving a subsequent independent synchronization cycle can inherit the approved effective contract without automatic promotion or DSpace writes.

This record complements `docs/vertical-022-activation-runbook.md`. The runbook remains the operational procedure; this document records the production evidence used to accept the vertical.

## Accepted runtime contract

```text
runtime contract = dspace-cataloger-v3.9.1
DSpace version   = 7.6.6
```

Authoritative pilot reconciliation:

```text
traditionalpageone = 44 bindings
traditionalpagetwo = 12 bindings
total bindings      = 56
unique metadata     = 54
metadata registry   = 292 fields
```

The final live-vs-runtime baseline diagnostic reported:

```text
binding_count          = 56
expected_binding_count = 56
mismatch_count         = 0
mismatch_dimensions    = {}
```

## Governed baseline evidence

Initial production baseline snapshot:

```text
snapshot_id = 5e2bda33-0636-4bc7-977e-ceb17a0a9890
status      = ACTIVE
```

Observed semantic hash:

```text
9d7dc71d4d99dc60f45cb998aca50a649e498d1efa5259427c5bf0050a44ef41
```

Approved effective / governed hash:

```text
336972fc4461fce821ef8f9625087de864102ce2b2e7d411cd0daadaf3d9014d
```

Authoritative evidence anchors:

```text
source export semantic hash:
8260b2023b7b417f3056d3724664869f96cb613371c673517d6b7400af2a0b1c

56/56 reconciliation hash:
5b549a16307354b84b9327325532755877a622e323573616e92c8a0dee93ea92
```

The governed HTTP 204 resolution left the snapshot in `BASELINE_REVIEW_REQUIRED` before explicit human approval. Approval then promoted that exact effective hash to `ACTIVE`.

## Resolution inheritance proof

A subsequent independent synchronization cycle produced:

```text
run_id               = 776b254a-3bc8-4278-b514-6d7164451f40
snapshot_id          = 94c6f921-ced4-4d8f-ae4b-e62e7e5bad4a
snapshot_status      = NO_CHANGE
contract_health      = SYNCED
resolution_inherited = true
effective_hash       = 336972fc4461fce821ef8f9625087de864102ce2b2e7d411cd0daadaf3d9014d
governed_hash        = 336972fc4461fce821ef8f9625087de864102ce2b2e7d411cd0daadaf3d9014d
```

The `active_snapshot_id` remained the explicitly approved baseline rather than the new `NO_CHANGE` snapshot. This is the expected governance behavior: exact reconciliation may inherit authoritative resolution evidence, but it does not automatically promote a new ACTIVE baseline.

## Scheduler wrapper acceptance

Repository-managed operational wrapper:

```text
scripts/dspace-contract-sync.sh
```

The wrapper was added through PR #46 and deployed to the Dokploy/VPS environment. A production smoke test completed with:

```text
contract_health      = SYNCED
snapshot_status      = NO_CHANGE
resolution_inherited = true
exit                  = 0
```

Smoke-test synchronization evidence:

```text
run_id      = 158bae75-785a-4bc8-852f-46e7bdb443cd
snapshot_id = a5e61ee1-b109-499c-82e3-bee00e795ee6
```

The wrapper executes only:

```bash
docker compose run --rm api python -m cataloging_api.dspace.contract_job
```

It does not approve, resolve, or promote snapshots; does not write to DSpace; does not run a scheduler loop inside FastAPI; and propagates the contract job exit code.

## Accepted safety invariants

Operational acceptance depends on the following invariants remaining true:

- DSpace contract synchronization is read-only; authentication is the only DSpace POST involved.
- Raw HAL+JSON and observed semantic hashes remain immutable.
- HTTP 204 from `traditional/sections` is treated as unobservable evidence, never as an empty form.
- A baseline becomes `ACTIVE` only through explicit human approval.
- Resolution inheritance requires exact reconciliation with the approved effective contract.
- Failed observations never replace or invalidate the last ACTIVE baseline.
- Scheduler execution never performs approval, evidence resolution, or promotion.
- Drift or failed inheritance must surface as `DRIFT_DETECTED` / `REVIEW_REQUIRED`, not as automatic adoption.

## Operational acceptance criteria

VERTICAL-022 is accepted because all of the following were demonstrated in production:

1. Authenticated read-only contract collection completed against DSpace 7.6.6.
2. The live submission contract reconciled 56/56 against the runtime master contract.
3. The known HTTP 204 surface was resolved through explicit governed evidence, not inferred as empty.
4. The effective contract hash was approved by a human and became the sole ACTIVE baseline.
5. Global health reported `SYNCED` after approval.
6. A later independent run returned `NO_CHANGE`, inherited resolution evidence, and preserved the ACTIVE baseline.
7. The repository-managed scheduler wrapper ran successfully in the deployed Dokploy/VPS environment with exit code 0.
8. No automatic DSpace write, baseline approval, or promotion path was introduced.

## Ongoing operating condition

The vertical remains operationally accepted while scheduled observations continue to preserve the safety invariants above. Any future `DRIFT_DETECTED`, `REVIEW_REQUIRED`, authentication/network failure, registry mismatch, form-binding mismatch, active-definition change, or multiple-ACTIVE anomaly requires human investigation under the activation runbook before any new baseline is approved.

The scheduler itself is operational infrastructure, not governance authority: disabling it must leave snapshots, raw evidence, change history, and the last ACTIVE baseline intact.
