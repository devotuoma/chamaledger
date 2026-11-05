import assert from "node:assert/strict";
import { test } from "node:test";

import { escapeHtml, money, percent } from "../src/format.js";

test("money groups thousands and names the currency", () => {
  assert.equal(money(1250000), "UGX 1,250,000");
});

test("percent turns a share into one decimal place", () => {
  assert.equal(percent(0.25), "25.0%");
  assert.equal(percent(0), "0.0%");
});

test("escapeHtml neutralises markup in user input", () => {
  assert.equal(escapeHtml(`<img src=x onerror="a">`), "&lt;img src=x onerror=&quot;a&quot;&gt;");
});
