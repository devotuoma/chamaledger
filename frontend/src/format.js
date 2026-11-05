const CURRENCY = "UGX";

export function money(amount) {
  return `${CURRENCY} ${Number(amount).toLocaleString("en-US")}`;
}

export function percent(share) {
  return `${(Number(share) * 100).toFixed(1)}%`;
}

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

export function today() {
  return new Date().toISOString().slice(0, 10);
}
