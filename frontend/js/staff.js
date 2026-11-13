// CampusEats staff page. Owner: Mann.
// Shell (login check, tabs, messages) + Orders, Stock and Admin tabs.
// Other tabs live in their own files and register a loader:
//   staff-details.js  tabLoaders.details  (Mann, MongoDB)
//   staff-menu.js     tabLoaders.menu     (TODO Manoj)
//   staff-stats.js    tabLoaders.stats    (TODO Manoj)
// Shared globals for those files: $, toast, handleError, tabLoaders, me.

const REFRESH_MS = 15000;
const ACTIVE = ["placed", "preparing", "ready"];
const NEXT_STATUS = {
  placed: { status: "preparing", label: "Start preparing" },
  preparing: { status: "ready", label: "Mark ready" },
  ready: { status: "completed", label: "Mark collected" },
};

const $ = (id) => document.getElementById(id);
const tabLoaders = {};

const me = Auth.requireRole("staff", "admin");   // redirects if not staff/admin

let currentTab = "orders";
let allOrders = [];
const orderErrors = {};     // order id -> last error shown on its card
let busy = false;           // true while an order action runs
let refreshTimer = null;

// ============================================================ messages

let toastTimer = null;
function toast(message, type = "success") {
  const el = $("toast");
  el.textContent = message;
  el.className = `alert toast ${type}`;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, type === "error" ? 6000 : 3000);
}

function handleError(err) {
  // a 401 already sends the user back to the login page (api.js)
  if (err.status !== 401) toast(err.message, "error");
}

// ============================================================ tabs

function switchTab(name) {
  currentTab = name;
  document.querySelectorAll(".tab").forEach((t) => {
    const active = t.dataset.tab === name;
    t.classList.toggle("active", active);
    t.setAttribute("aria-selected", active);
  });
  document.querySelectorAll("main#app-view > section").forEach((s) => {
    s.hidden = s.id !== `tab-${name}`;
  });
  if (tabLoaders[name]) tabLoaders[name]();
}

document.querySelectorAll(".tab").forEach((t) =>
  t.addEventListener("click", () => switchTab(t.dataset.tab)));

$("logout-btn").addEventListener("click", () => Auth.logout());

// ============================================================ orders tab

tabLoaders.orders = loadOrders;

async function loadOrders() {
  try {
    allOrders = await API.get("/api/staff/orders");
    renderOrders();
    $("last-updated").textContent = "Updated " + new Date().toLocaleTimeString("en-IN",
      { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch (err) {
    handleError(err);
  }
}

function filteredOrders() {
  const f = $("status-filter").value;
  let list;
  if (f === "all") list = allOrders;
  // "needs action": still being made, or collected but not paid yet
  else if (f === "active") list = allOrders.filter((o) =>
    ACTIVE.includes(o.status) || (o.status === "completed" && o.payment_status === "unpaid"));
  else if (f === "unpaid") list = allOrders.filter((o) =>
    o.payment_status === "unpaid" && o.status !== "cancelled");
  else list = allOrders.filter((o) => o.status === f);

  const oldestFirst = f === "active" || ACTIVE.includes(f);   // a queue reads oldest first
  return [...list].sort((a, b) => (oldestFirst ? a.order_id - b.order_id : b.order_id - a.order_id));
}

function renderCounts() {
  const counts = {};
  for (const o of allOrders) counts[o.status] = (counts[o.status] || 0) + 1;
  const unpaid = allOrders.filter((o) => o.status === "completed" && o.payment_status === "unpaid").length;
  $("order-counts").innerHTML = ACTIVE
    .map((s) => `<span class="badge ${s}">${s}: ${counts[s] || 0}</span>`)
    .join("") + `<span class="badge unpaid">collected, unpaid: ${unpaid}</span>`;
}

function orderCardHtml(o) {
  const items = o.items.map((i) =>
    `<li><span>${i.quantity} × ${escapeHtml(i.name)}</span><span>${formatMoney(i.line_total)}</span></li>`).join("");

  const buttons = [];
  if (NEXT_STATUS[o.status]) {
    const next = NEXT_STATUS[o.status];
    buttons.push(`<button class="primary small" data-action="status" data-status="${next.status}" data-id="${o.order_id}">${next.label}</button>`);
  }
  if (o.payment_status === "unpaid" && o.status !== "cancelled") {
    buttons.push(`<button class="ok small" data-action="paid" data-id="${o.order_id}">Mark paid</button>`);
  }
  if (ACTIVE.includes(o.status)) {
    buttons.push(`<button class="danger small" data-action="cancel" data-id="${o.order_id}">Cancel</button>`);
  }
  const error = orderErrors[o.order_id]
    ? `<div class="alert error order-error">${escapeHtml(orderErrors[o.order_id])}</div>` : "";

  return `
    <article class="card order-card">
      <header>
        <div>
          <div class="order-id">#${o.order_id}</div>
          <div>${escapeHtml(o.student_name)} <span class="muted">· ${escapeHtml(o.student_phone || "")}</span></div>
          <div class="muted small-text">${formatTime(o.created_at)}</div>
        </div>
        <div class="row" style="justify-content:flex-end">
          <span class="badge ${o.status}">${o.status === "completed" ? "collected" : o.status}</span>
          <span class="badge ${o.payment_status}">${o.payment_status}</span>
        </div>
      </header>
      <ul class="order-items">${items}</ul>
      <div class="order-total"><span>Total</span><span>${formatMoney(o.total)}</span></div>
      ${error}
      <div class="order-actions">${buttons.join("")}</div>
    </article>`;
}

function renderOrders() {
  renderCounts();
  const list = filteredOrders();
  $("orders-list").innerHTML = list.length
    ? list.map(orderCardHtml).join("")
    : `<div class="card empty" style="grid-column:1/-1">No orders here.</div>`;
}

async function runOrderAction(btn) {
  const id = btn.dataset.id;
  const action = btn.dataset.action;
  if (action === "cancel" && !confirm(`Cancel order #${id}? Its stock will go back.`)) return;

  busy = true;
  btn.disabled = true;
  try {
    let msg;
    if (action === "status") {
      await API.patch(`/api/staff/orders/${id}/status`, { body: { status: btn.dataset.status } });
      msg = `Order #${id} is now ${btn.dataset.status === "completed" ? "collected" : btn.dataset.status}.`;
    } else if (action === "paid") {
      await API.patch(`/api/staff/orders/${id}/paid`);
      msg = `Order #${id} marked paid.`;
    } else if (action === "cancel") {
      await API.post(`/api/staff/orders/${id}/cancel`);
      msg = `Order #${id} cancelled. Stock restored.`;
    }
    delete orderErrors[id];
    toast(msg);
  } catch (err) {
    if (err.status !== 401) orderErrors[id] = err.message;
    handleError(err);
  } finally {
    busy = false;
    await loadOrders();
  }
}

$("orders-list").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-action]");
  if (btn) runOrderAction(btn);
});
$("status-filter").addEventListener("change", renderOrders);
$("refresh-btn").addEventListener("click", loadOrders);

function startAutoRefresh() {
  clearInterval(refreshTimer);
  refreshTimer = setInterval(() => {
    if (currentTab === "orders" && document.visibilityState === "visible" && !busy) loadOrders();
  }, REFRESH_MS);
}

// ============================================================ stock tab

tabLoaders.stock = loadStock;

async function loadStock() {
  try {
    renderStock(await API.get("/api/staff/stock"));
  } catch (err) {
    handleError(err);
  }
}

function renderStock(rows) {
  const low = rows.filter((r) => r.is_low);
  const alertBox = $("low-stock-alert");
  alertBox.hidden = !low.length;
  alertBox.innerHTML = low.length
    ? `<strong>Low stock (${low.length}):</strong> ` +
      low.map((r) => `${escapeHtml(r.name)} (${r.current_stock} left)`).join(", ")
    : "";

  $("stock-body").innerHTML = rows.length ? rows.map((r) => `
    <tr class="${r.is_low ? "low" : ""}" data-id="${r.item_id}">
      <td><strong>${escapeHtml(r.name)}</strong><div class="muted small-text">${escapeHtml(r.category)}</div></td>
      <td class="num"><strong>${r.current_stock}</strong></td>
      <td class="num">${r.low_stock_threshold}</td>
      <td class="num">${r.sold_last_7_days}</td>
      <td>${r.status === "sold_out" ? '<span class="badge low">Sold out</span>'
            : r.is_low ? '<span class="badge low">Low</span>' : '<span class="badge ready">OK</span>'}</td>
      <td>
        <form class="inline-form stock-form" data-id="${r.item_id}">
          <input type="number" step="1" min="1" max="1000" placeholder="Qty" required aria-label="Quantity">
          <select aria-label="Reason">
            <option value="restock">+ Restock</option>
            <option value="wastage">− Wastage</option>
            <option value="correction">− Correction</option>
          </select>
          <button type="submit" class="small">Apply</button>
        </form>
      </td>
      <td><button class="small history-btn" data-id="${r.item_id}">History</button></td>
    </tr>`).join("")
    : `<tr><td colspan="7" class="empty">No dishes yet.</td></tr>`;
}

$("stock-body").addEventListener("submit", async (e) => {
  const form = e.target.closest(".stock-form");
  if (!form) return;
  e.preventDefault();
  const qty = Number(form.querySelector("input").value);
  const reason = form.querySelector("select").value;
  if (!(qty > 0)) return;
  const amount = reason === "restock" ? qty : -qty;
  const btn = form.querySelector("button");
  btn.disabled = true;
  try {
    const item = await API.patch(`/api/staff/stock/${form.dataset.id}`, { body: { amount, reason } });
    toast(`${item.name}: ${amount > 0 ? "+" : ""}${amount} (${reason}). Now ${item.current_stock}.`);
    await loadStock();
  } catch (err) {
    handleError(err);
    btn.disabled = false;
  }
});

$("stock-body").addEventListener("click", async (e) => {
  const btn = e.target.closest(".history-btn");
  if (!btn) return;
  const row = btn.closest("tr");
  const next = row.nextElementSibling;
  if (next && next.classList.contains("history-row")) {   // toggle off
    next.remove();
    btn.textContent = "History";
    return;
  }
  try {
    const txns = await API.get(`/api/staff/stock/${btn.dataset.id}/history`);
    const body = txns.length ? txns.map((t) => `
      <tr>
        <td>${formatTime(t.created_at)}</td>
        <td class="num" style="color:${t.change_amount < 0 ? "var(--danger)" : "var(--ok)"}">
          ${t.change_amount > 0 ? "+" : ""}${t.change_amount}</td>
        <td>${escapeHtml(t.reason.replaceAll("_", " "))}</td>
        <td>${t.order_id ? "#" + t.order_id : ""}</td>
      </tr>`).join("")
      : `<tr><td colspan="4" class="muted">No stock changes yet.</td></tr>`;
    row.insertAdjacentHTML("afterend", `
      <tr class="history-row"><td colspan="7">
        <table class="history">
          <thead><tr><th>When</th><th class="num">Change</th><th>Reason</th><th>Order</th></tr></thead>
          <tbody>${body}</tbody>
        </table>
      </td></tr>`);
    btn.textContent = "Hide";
  } catch (err) {
    handleError(err);
  }
});

$("stock-refresh-btn").addEventListener("click", loadStock);

// ============================================================ admin tab

tabLoaders.admin = loadUsers;

async function loadUsers() {
  try {
    const users = await API.get(API.withQuery("/api/admin/users", { role: $("user-role-filter").value }));
    $("users-body").innerHTML = users.map((u) => `
      <tr>
        <td><strong>${escapeHtml(u.name)}</strong></td>
        <td>${escapeHtml(u.email)}</td>
        <td><span class="badge">${escapeHtml(u.role)}</span></td>
        <td>${escapeHtml(u.phone || "—")}</td>
        <td class="small-text">${formatTime(u.created_at)}</td>
        <td>${u.is_active ? '<span class="badge ready">Active</span>' : '<span class="badge rejected">Disabled</span>'}</td>
        <td>${u.user_id === me.user_id ? '<span class="muted small-text">you</span>'
              : `<button class="small ${u.is_active ? "danger" : ""}" data-user="${u.user_id}" data-active="${!u.is_active}">
                   ${u.is_active ? "Disable" : "Enable"}</button>`}</td>
      </tr>`).join("") || `<tr><td colspan="7" class="empty">No users.</td></tr>`;
  } catch (err) {
    handleError(err);
  }
}

$("users-body").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-user]");
  if (!btn) return;
  const enable = btn.dataset.active === "true";
  if (!enable && !confirm("Disable this account? They will be logged out.")) return;
  btn.disabled = true;
  try {
    const u = await API.patch(`/api/admin/users/${btn.dataset.user}/active`, { body: { is_active: enable } });
    toast(`${u.name} ${u.is_active ? "enabled" : "disabled"}.`);
    await loadUsers();
  } catch (err) {
    handleError(err);
    btn.disabled = false;
  }
});

$("user-role-filter").addEventListener("change", loadUsers);

$("staff-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.submitter;
  btn.disabled = true;
  try {
    const u = await API.post("/api/admin/staff", { body: {
      name: $("new-staff-name").value.trim(),
      email: $("new-staff-email").value.trim(),
      phone: $("new-staff-phone").value.trim() || null,
      password: $("new-staff-password").value,
    }});
    toast(`Staff account created for ${u.name}.`);
    e.target.reset();
    await loadUsers();
  } catch (err) {
    handleError(err);
  } finally {
    btn.disabled = false;
  }
});

// ============================================================ start

if (me) {
  $("who").textContent = `${me.name} · ${me.role}`;
  document.querySelector('.tab[data-tab="admin"]').hidden = me.role !== "admin";
  $("app-view").hidden = false;
  // other tab files load after this one; open the first tab once they have
  window.addEventListener("DOMContentLoaded", () => switchTab(currentTab));
  startAutoRefresh();
}
