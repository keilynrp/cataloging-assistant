import assert from "node:assert/strict";
import test from "node:test";

import nextConfig from "../next.config.ts";

test("Server Actions accept the documented PDF evidence limit", () => {
  assert.equal(nextConfig.experimental?.serverActions?.bodySizeLimit, "25mb");
});
