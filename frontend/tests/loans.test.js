import assert from "node:assert/strict";
import { test } from "node:test";

import { renderLoans } from "../src/views/loans.js";
import { flush, setup, submit } from "./helpers.js";

const MEMBER = { id: 1, full_name: "Auma Test", phone: "+256700000003", active: true, savings: 100 };
const loan = (overrides = {}) => ({
  id: 5,
  member_id: 1,
  principal: 100,
  interest_rate_bps: 1000,
  issued_on: "2026-01-01",
  due_on: "2026-02-01",
  closed_on: null,
  total_due: 110,
  outstanding: 110,
  days_late: 0,
  ...overrides,
});
const context = (api) => ({ api, notify: () => {}, run: (task) => task() });
const baseApi = (loans) => ({ members: async () => [MEMBER], loans: async () => loans });

test("an overdue loan says so in words, not only colour", async () => {
  const { root } = setup();
  await renderLoans(root, context(baseApi([loan({ days_late: 45 })])));
  assert.match(root.querySelector(".badge-late").textContent, /Late: 45 days/);
});

test("a closed loan offers no repayment form", async () => {
  const { root } = setup();
  await renderLoans(root, context(baseApi([loan({ closed_on: "2026-02-01", outstanding: 0 })])));
  assert.equal(root.querySelector("form.repay"), null);
});

test("the percentage rate is sent as basis points", async () => {
  const { root, window } = setup();
  const calls = [];
  const api = { ...baseApi([]), issueLoan: async (data) => calls.push(data) };
  await renderLoans(root, context(api));
  const form = root.querySelector("#loan-form");
  form.elements.principal.value = "100";
  form.elements.rate.value = "12.5";
  form.elements.due_on.value = "2027-01-01";
  submit(window, form);
  await flush();
  assert.equal(calls[0].interest_rate_bps, 1250);
});

test("a repayment retry reuses its reference", async () => {
  const { root, statusEl, window } = setup();
  const references = [];
  const api = {
    ...baseApi([loan()]),
    recordRepayment: async (_, data) => {
      references.push(data.reference);
      throw new Error("Network down");
    },
  };
  const swallow = { api, notify: () => {}, run: (task) => task().catch(() => {}) };
  await renderLoans(root, swallow);
  assert.equal(statusEl.hidden, true);
  const form = root.querySelector("form.repay");
  form.elements.amount.value = "10";
  submit(window, form);
  await flush();
  submit(window, form);
  await flush();
  assert.equal(references.length, 2);
  assert.equal(references[0], references[1]);
});
