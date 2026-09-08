# Evidence workspace integration check

The fixture API is local and synthetic. It records the last copy request in
memory and never accesses DSpace or PostgreSQL.

Use the repository's locked web dependencies and an existing Playwright
installation with Chromium. axe-core is already transitive in the lockfile.
No package.json or lockfile changes are needed.

Run development commands from WSL as required by AGENTS.md. In separate terminals:

1. Start the fixture API: node apps/web/tests/evidence-fixture-server.mjs.
2. Start the web app on port 18080 with CATALOG_API_URL=http://127.0.0.1:18081,
   NEXT_PUBLIC_CATALOG_API_URL=http://localhost:18081 and a non-production
   CATALOG_REVIEW_TOKEN. For example use the existing next dev command with
   --port 18080.
3. Run node apps/web/tests/evidence-workspace.mjs. If Playwright is installed
   outside the repo, set PLAYWRIGHT_MODULE to its absolute module directory.
   WORKSPACE_EVIDENCE_DIR optionally saves responsive screenshots.

The script checks inspection vs selection, ineligible candidates, filtered
selection retention, native dialog keyboard containment and return focus,
light/dark reflow, contrast, stale/unlinked/empty states, remote error
messages and attributed/versioned copy requests against the fixture API.

The 720x450 viewport is a reduced-width reflow check, not proof of real
200% browser zoom. NVDA voice output remains a separate manual check.
The fixture workflow is not a replacement for backend integration tests.
