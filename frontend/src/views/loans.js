import { escapeHtml, money, today } from "../format.js";
import { newReference } from "./contributions.js";

function loanStatus(loan) {
  if (loan.closed_on) return `Closed ${escapeHtml(loan.closed_on)}`;
  if (loan.days_late > 0) return `<span class="badge-late">Late: ${loan.days_late} days</span>`;
  return `Due ${escapeHtml(loan.due_on)}`;
}

function row(loan, names) {
  const repay = loan.closed_on
    ? ""
    : `<form class="repay" data-loan="${loan.id}">
        <input name="amount" type="number" min="1" max="${loan.outstanding}" step="1" required aria-label="Repayment amount" />
        <button type="submit">Repay</button>
      </form>`;
  return `<tr>
    <td>${escapeHtml(names.get(loan.member_id) ?? "Unknown")}</td>
    <td class="money">${money(loan.total_due)}</td>
    <td class="money">${money(loan.outstanding)}</td>
    <td>${loanStatus(loan)}</td>
    <td>${repay}</td>
  </tr>`;
}

export async function renderLoans(root, context) {
  const { api, notify, run } = context;
  const [members, loans] = await Promise.all([api.members(), api.loans()]);
  const names = new Map(members.map((member) => [member.id, member.full_name]));
  const options = members
    .filter((member) => member.active)
    .map(
      (member) =>
        `<option value="${member.id}">${escapeHtml(member.full_name)} (limit ${money(member.savings * 3)})</option>`,
    )
    .join("");

  root.innerHTML = `
    <h2>Loans</h2>
    <form class="card" id="loan-form">
      <label>Member <select name="member_id" required>${options}</select></label>
      <label>Principal (UGX) <input name="principal" type="number" min="1" step="1" required /></label>
      <label>Flat interest (%) <input name="rate" type="number" min="0" max="100" step="0.5" value="10" required /></label>
      <label>Due date <input name="due_on" type="date" required /></label>
      <button type="submit">Issue loan</button>
    </form>
    <div class="table-wrap"><table>
      <thead><tr><th>Member</th><th class="money">Total due</th><th class="money">Outstanding</th><th>Status</th><th>Repayment</th></tr></thead>
      <tbody>${loans.map((loan) => row(loan, names)).join("") || '<tr><td colspan="5">No loans yet.</td></tr>'}</tbody>
    </table></div>`;

  root.querySelector("#loan-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(event.target);
    return run(async () => {
      await api.issueLoan({
        member_id: Number(data.get("member_id")),
        principal: Number(data.get("principal")),
        interest_rate_bps: Math.round(Number(data.get("rate")) * 100),
        issued_on: today(),
        due_on: data.get("due_on"),
      });
      await renderLoans(root, context);
      notify("Loan issued.", "success");
    });
  });

  root.querySelectorAll("form.repay").forEach((form) => {
    let pendingReference = null;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const button = form.querySelector("button");
      if (button.disabled) return undefined;
      button.disabled = true;
      pendingReference ??= newReference();
      const amount = Number(new FormData(form).get("amount"));
      return run(async () => {
        try {
          await api.recordRepayment(form.dataset.loan, {
            amount,
            paid_on: today(),
            reference: pendingReference,
          });
          await renderLoans(root, context);
          notify("Repayment recorded.", "success");
        } finally {
          button.disabled = false;
        }
      });
    });
  });
}
