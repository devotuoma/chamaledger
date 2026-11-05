import assert from "node:assert/strict";
import { test } from "node:test";

import { createApp } from "../src/app.js";
import { renderDashboard } from "../src/views/dashboard.js";
import { renderMembers } from "../src/views/members.js";
import { flush, setup, submit } from "./helpers.js";

const context = (api) => ({
  api,
  notify: () => {},
  run: (task) => task(),
});

test("dashboard renders the API figures", async () => {
  const { root } = setup();
  const api = {
    dashboard: async () => ({
      member_count: 2,
      total_savings: 150000,
      loans_outstanding: 40000,
      par30: 0.125,
    }),
  };
  await renderDashboard(root, context(api));
  assert.match(root.textContent, /UGX 150,000/);
  assert.match(root.textContent, /12\.5%/);
});

test("member names are escaped, so markup in a name cannot run", async () => {
  const { root } = setup();
  const members = [{ id: 1, full_name: "<b>x</b>", phone: "+256700000001", active: true, savings: 0 }];
  await renderMembers(root, context({ members: async () => members }));
  assert.equal(root.querySelector("tbody b"), null);
  assert.match(root.textContent, /<b>x<\/b>/);
});

test("adding a member posts the form and refreshes the list", async () => {
  const { root, window } = setup();
  const members = [];
  const api = {
    members: async () => members,
    createMember: async (data) => {
      members.push({ id: 1, active: true, savings: 0, ...data });
    },
  };
  await renderMembers(root, context(api));
  const form = root.querySelector("#member-form");
  form.elements.full_name.value = "Nakato Test";
  form.elements.phone.value = "+256700000009";
  submit(window, form);
  await flush();
  assert.match(root.querySelector("tbody").textContent, /Nakato Test/);
});

test("an API failure is shown to the user instead of a blank page", async () => {
  const { root, statusEl } = setup();
  const routes = {
    dashboard: async () => {
      throw new Error("Could not reach the server.");
    },
  };
  const app = createApp({ root, statusEl, api: {}, routes });
  await app.navigate("dashboard");
  assert.equal(statusEl.hidden, false);
  assert.equal(statusEl.className, "error");
  assert.match(statusEl.textContent, /Could not reach/);
});
