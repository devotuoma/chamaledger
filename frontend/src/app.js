import { createApi } from "./api.js";
import { renderContributions } from "./views/contributions.js";
import { renderDashboard } from "./views/dashboard.js";
import { renderLoans } from "./views/loans.js";
import { renderMembers } from "./views/members.js";

const ROUTES = {
  dashboard: renderDashboard,
  members: renderMembers,
  contributions: renderContributions,
  loans: renderLoans,
};

export function createApp({ root, statusEl, api = createApi(), routes = ROUTES }) {
  function notify(message, kind) {
    statusEl.textContent = message;
    statusEl.className = kind;
    statusEl.hidden = false;
  }

  async function run(task) {
    try {
      return await task();
    } catch (error) {
      notify(error.message, "error");
      return undefined;
    }
  }

  const context = { api, notify, run };

  function navigate(name) {
    statusEl.hidden = true;
    const render = routes[name] ?? routes.dashboard;
    return run(() => render(root, context));
  }

  return { navigate, notify, run };
}

if (typeof document !== "undefined" && document.getElementById("view")) {
  const app = createApp({
    root: document.getElementById("view"),
    statusEl: document.getElementById("status"),
  });
  const go = () => app.navigate(location.hash.slice(1));
  window.addEventListener("hashchange", go);
  go();
}
