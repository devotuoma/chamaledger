export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function describe(detail, status) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => `${item.loc?.at(-1) ?? "field"}: ${item.msg}`).join("; ");
  }
  return `Request failed (${status})`;
}

export function createApi(fetchFn = (...args) => globalThis.fetch(...args)) {
  async function request(path, options = {}) {
    let response;
    try {
      response = await fetchFn(`/api${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
    } catch {
      throw new ApiError("Could not reach the server. Check your connection and retry.", 0);
    }
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new ApiError(describe(body?.detail, response.status), response.status);
    return body;
  }

  const post = (path, data) =>
    request(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });

  return {
    dashboard: () => request("/dashboard"),
    members: () => request("/members"),
    createMember: (data) => post("/members", data),
    deactivateMember: (id) => post(`/members/${id}/deactivate`),
    contributions: () => request("/contributions"),
    recordContribution: (data) => post("/contributions", data),
    loans: () => request("/loans"),
    issueLoan: (data) => post("/loans", data),
    recordRepayment: (id, data) => post(`/loans/${id}/repayments`, data),
  };
}
