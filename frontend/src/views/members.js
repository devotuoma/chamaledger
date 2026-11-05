import { escapeHtml, money } from "../format.js";

function row(member) {
  const action = member.active
    ? `<button class="secondary" data-deactivate="${member.id}">Deactivate</button>`
    : "Inactive";
  return `<tr>
    <td>${escapeHtml(member.full_name)}</td>
    <td>${escapeHtml(member.phone)}</td>
    <td class="money">${money(member.savings)}</td>
    <td>${action}</td>
  </tr>`;
}

export async function renderMembers(root, context) {
  const { api, notify, run } = context;
  const members = await api.members();
  root.innerHTML = `
    <h2>Members</h2>
    <form class="card" id="member-form">
      <label>Full name <input name="full_name" required minlength="2" maxlength="120" /></label>
      <label>Phone (international format) <input name="phone" required placeholder="+256700000001" /></label>
      <button type="submit">Add member</button>
    </form>
    <div class="table-wrap"><table>
      <thead><tr><th>Name</th><th>Phone</th><th class="money">Savings</th><th>Status</th></tr></thead>
      <tbody>${members.map(row).join("") || '<tr><td colspan="4">No members yet.</td></tr>'}</tbody>
    </table></div>`;

  root.querySelector("#member-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    return run(async () => {
      await api.createMember({ full_name: form.get("full_name"), phone: form.get("phone") });
      await renderMembers(root, context);
      notify("Member added.", "success");
    });
  });

  root.querySelectorAll("[data-deactivate]").forEach((button) => {
    button.addEventListener("click", () =>
      run(async () => {
        await api.deactivateMember(button.dataset.deactivate);
        await renderMembers(root, context);
        notify("Member deactivated.", "success");
      }),
    );
  });
}
