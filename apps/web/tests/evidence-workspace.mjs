// Run with an existing Playwright installation; does not add project dependencies.
// Start fixture server on 18081 and Next on 18080 with CATALOG_API_URL pointing to it.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE ?? "playwright");
const browser = await chromium.launch({ headless: true });
const origin = process.env.WORKSPACE_TEST_URL ?? "http://localhost:18080";
const nominal = origin + "/evidence/11111111-1111-4111-8111-111111111111";
const page = await browser.newPage();
page.setDefaultNavigationTimeout(180000);
const evidenceDir = process.env.WORKSPACE_EVIDENCE_DIR;
if (evidenceDir) await mkdir(evidenceDir, { recursive: true });
try {
  await page.goto(nominal);
  const cta = page.getByRole("button", { name: "Copiar selección al borrador", exact: true });
  assert.equal(await cta.isEnabled(), false);
  const checkboxes = page.getByRole("checkbox");
  assert.equal(await checkboxes.count(), 3);
  assert.equal(await checkboxes.nth(1).isEnabled(), false);
  assert.equal(await checkboxes.nth(2).isEnabled(), false);
  await page.getByRole("button", { name: /Familia lingüística.*Maya/ }).click();
  assert.equal(await checkboxes.nth(0).isChecked(), false);
  await page.getByRole("complementary", { name: "Contexto y QA" }).getByText("Familia: Maya", { exact: true }).waitFor();
  await checkboxes.nth(0).check();
  assert.equal(await cta.isEnabled(), true);
  await page.getByRole("searchbox", { name: "Filtrar candidatos" }).fill("Título");
  await cta.press("Enter");
  const modal = page.getByRole("dialog");
  await modal.waitFor();
  assert.match(await modal.innerText(), /Maya/);
  for (const key of ["Tab", "Shift+Tab"]) {
    for (let n = 0; n < 8; n++) {
      await page.keyboard.press(key);
      assert.equal(await page.evaluate(() => document.querySelector("dialog").contains(document.activeElement)), true);
    }
  }
  await page.keyboard.press("Escape");
  assert.equal(await cta.evaluate(el => el === document.activeElement), true);
  await cta.press("Space");
  await modal.getByRole("button", { name: "Cancelar", exact: true }).click();
  assert.equal(await cta.evaluate(el => el === document.activeElement), true);
  await page.getByRole("searchbox", { name: "Filtrar candidatos" }).fill("");
  assert.equal(await checkboxes.nth(0).isChecked(), true);
  await cta.click();
  await modal.getByRole("button", { name: "Cerrar revisión", exact: true }).click();
  assert.equal(await cta.evaluate(el => el === document.activeElement), true);
  for (const [width, height] of [[1440,900], [768,1024], [390,844], [720,450]]) {
    await page.setViewportSize({ width, height });
    for (const theme of ["light", "dark"]) {
      if (theme === "dark") await page.getByRole("button", { name: /modo oscuro/i }).click();
      const metrics = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
      assert.equal(metrics.scroll <= metrics.client, true, JSON.stringify(metrics));
      console.log(JSON.stringify({ viewport: [width, height], theme, ...metrics }));
      if (evidenceDir) await page.screenshot({ path: evidenceDir + "/" + width + "-" + theme + ".png", fullPage: true });
      await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
      const axeResult = await page.evaluate(async () => {
        return window.axe.run(document.querySelector("[data-evidence-workspace]"), {
          runOnly: { type: "rule", values: ["color-contrast"] },
        });
      });
      console.log(JSON.stringify({ viewport: [width, height], theme, contrastViolations: axeResult.violations }));
      assert.equal(axeResult.violations.length, 0, "Workspace contrast violations");
      if (theme === "dark") await page.getByRole("button", { name: /modo claro/i }).click();
    }
  }
  await page.goto(origin + "/evidence/stale");
  assert.equal(await cta.isEnabled(), false);
  assert.equal(await page.locator('button[type="submit"]', { hasText: "Subir PDF" }).isEnabled(), false);
  await page.goto(origin + "/evidence/unlinked");
  assert.equal(await cta.isEnabled(), false);
  await page.goto(origin + "/evidence/empty");
  await page.getByText("Todavía no hay fuentes.", { exact: false }).waitFor();
  await page.goto(nominal + "?remote=remote_target_not_public");
  await page.getByRole("status").filter({ hasText: "no pública" }).waitFor();
  await page.getByRole("checkbox").nth(0).check();
  await cta.click();
  await modal.getByLabel("Catalogador", { exact: true }).fill("Prueba automatizada");
  await modal.getByLabel("Justificación").fill("Revisión de evidencia controlada");
  await modal.getByRole("button", { name: "Confirmar copia al borrador" }).click();
  await page.getByRole("status").filter({ hasText: "copiaron a una revisión" }).waitFor();
  const payload = await (await fetch("http://localhost:18081/__copy")).json();
  assert.deepEqual(payload.candidate_ids, ["33333333-3333-4333-8333-000000000001"]);
  assert.equal(payload.expected_version, 7);
  assert.equal(payload.author, "Prueba automatizada");
  console.log("PASS: inspection, eligibility, filtering, keyboard, modal, reflow, stale, empty, error message and attributed copy");
} finally { await browser.close(); }
