import assert from "node:assert/strict";
import { test } from "node:test";

import { createApi } from "../src/api.js";

const respond = (status, body) => async () => new Response(JSON.stringify(body), { status });

test("returns the parsed body on success", async () => {
  const api = createApi(respond(200, { member_count: 3 }));
  assert.deepEqual(await api.dashboard(), { member_count: 3 });
});

test("surfaces the server's message on a conflict", async () => {
  const api = createApi(respond(409, { detail: "Already exists" }));
  await assert.rejects(api.members(), { message: "Already exists", status: 409 });
});

test("flattens validation errors into a readable message", async () => {
  const detail = [{ loc: ["body", "phone"], msg: "bad format" }];
  const api = createApi(respond(422, { detail }));
  await assert.rejects(api.members(), { message: "phone: bad format" });
});

test("explains network failure in plain language", async () => {
  const api = createApi(async () => {
    throw new TypeError("fetch failed");
  });
  await assert.rejects(api.members(), /Could not reach the server/);
});

test("handles an error response that is not JSON", async () => {
  const api = createApi(async () => new Response("<html>502</html>", { status: 502 }));
  await assert.rejects(api.members(), { message: "Request failed (502)", status: 502 });
});
