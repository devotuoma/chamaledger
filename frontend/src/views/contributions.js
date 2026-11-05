import { escapeHtml, money, today } from "../format.js";

export function newReference() {
  return `WEB-${crypto.randomUUID()}`;
}

function row(contribution, names) {
  return `<tr>
    <td>${escapeHtml(contribution.paid_on)}</td>
    <td>${escapeHtml(names.get(contribution.member_id) ?? "Unknown")}</td>
    <td>${escapeHtml(contribution.reference)}</td>
    <td class="money">${money(contribution.amount)}</td>
  </tr>`;
}

export async function renderContributions(root, context) {
  const { api, notify, run } = context;
  const [members, contributions] = await Promise.all([api.members(), api.contributions()]);
  const names = new Map(members.map((member) => [member.id, member.full_name]));
  const options = members
    .filter((member) => member.active)
    .map((member) => `<option value="${member.id}">${escapeHtml(member.full_name)}</option>`)
    .join("");

  root.innerHTML = `
    <h2>Contributions</h2>
    <form class="card" id="contribution-form">
      <label>Member <select name="member_id" required>${options}</select></label>
      <label>Amount (UGX) <input name="amount" type="number" min="1" step="1" required /></label>
      <label>Date paid <input name="paid_on" type="date" value="${today()}" required /></label>
      <label>Mobile money reference (optional) <input name="reference" maxlength="64" /></label>
      <button type="submit">Record contribution</button>
    </form>
    <div class="table-wrap"><table>
      <thead><tr><th>Date</th><th>Member</th><th>Reference</th><th class="money">Amount</th></tr></thead>
      <tbody>${contributions.map((c) => row(c, names)).join("") || '<tr><td colspan="4">No contributions yet.</td></tr>'}</tbody>
    </table></div>`;

  const form = root.querySelector("#contribution-form");
  const button = form.querySelector("button");
  // Kept across failed attempts so that a retry can never record the payment twice.
  let pendingReference = null;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (button.disabled) return undefined;
    button.disabled = true;
    const data = new FormData(form);
    pendingReference = data.get("reference") || pendingReference || newReference();
    return run(async () => {
      try {
        await api.recordContribution({
          member_id: Number(data.get("member_id")),
          amount: Number(data.get("amount")),
          paid_on: data.get("paid_on"),
          reference: pendingReference,
        });
        await renderContributions(root, context);
        notify("Contribution recorded.", "success");
      } finally {
        button.disabled = false;
      }
    });
  });
}
