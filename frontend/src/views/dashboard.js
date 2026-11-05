import { money, percent } from "../format.js";

export async function renderDashboard(root, { api }) {
  const data = await api.dashboard();
  const stats = [
    ["Active members", data.member_count.toLocaleString("en-US")],
    ["Total savings", money(data.total_savings)],
    ["Loans outstanding", money(data.loans_outstanding)],
    ["Portfolio at risk (PAR30)", percent(data.par30)],
  ];
  root.innerHTML = `
    <h2>Group position</h2>
    <dl class="stats">
      ${stats.map(([label, value]) => `<div class="stat"><dt>${label}</dt><dd>${value}</dd></div>`).join("")}
    </dl>`;
}
