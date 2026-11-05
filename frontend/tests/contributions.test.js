import assert from "node:assert/strict";
import { test } from "node:test";

import { createApp } from "../src/app.js";
import { renderContributions } from "../src/views/contributions.js";
import { flush, setup, submit } from "./helpers.js";

const MEMBER = { id: 7, full_name: "Atieno Test", phone: "+256700000002", active: true, savings: 0 };

function fakeApi(recordContribution) {
  return { members: async () => [MEMBER], contributions: async () => [], recordContribution };
}

function fill(form) {
  form.elements.amount.value = "5000";
  form.elements.paid_on.value = "2026-03-01";
}

test("a blank reference is generated and the values are sent as numbers", async () => {
  const { root, statusEl, window } = setup();
  const calls = [];
  const app = createApp({ root, statusEl });
  const context = { api: fakeApi(async (data) => calls.push(data)), notify: app.notify, run: app.run };
  await renderContributions(root, context);
  const form = root.querySelector("#contribution-form");
  fill(form);
  submit(window, form);
  await flush();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].member_id, 7);
  assert.equal(calls[0].amount, 5000);
  assert.match(calls[0].reference, /^WEB-[0-9a-f-]{36}$/);
  assert.match(statusEl.textContent, /recorded/);
});

test("a double submit sends one request", async () => {
  const { root, statusEl, window } = setup();
  let release;
  const calls = [];
  const record = (data) => {
    calls.push(data);
    return new Promise((resolve) => {
      release = resolve;
    });
  };
  const app = createApp({ root, statusEl });
  await renderContributions(root, { api: fakeApi(record), notify: app.notify, run: app.run });
  const form = root.querySelector("#contribution-form");
  fill(form);
  submit(window, form);
  submit(window, form);
  assert.equal(calls.length, 1);
  release();
  await flush();
});

test("a retry after a failure reuses the same reference and shows the error", async () => {
  const { root, statusEl, window } = setup();
  const references = [];
  const record = async (data) => {
    references.push(data.reference);
    if (references.length === 1) throw new Error("Could not reach the server.");
  };
  const app = createApp({ root, statusEl });
  await renderContributions(root, { api: fakeApi(record), notify: app.notify, run: app.run });
  const form = root.querySelector("#contribution-form");
  fill(form);
  submit(window, form);
  await flush();
  assert.equal(statusEl.className, "error");
  submit(window, form);
  await flush();
  assert.equal(references.length, 2);
  assert.equal(references[0], references[1]);
  assert.equal(statusEl.className, "success");
});

test("inactive members cannot be selected", async () => {
  const { root } = setup();
  const inactive = { ...MEMBER, id: 8, full_name: "Gone Test", active: false };
  const api = { members: async () => [MEMBER, inactive], contributions: async () => [] };
  await renderContributions(root, { api, notify: () => {}, run: (task) => task() });
  const options = [...root.querySelectorAll("select option")].map((option) => option.value);
  assert.deepEqual(options, ["7"]);
});
