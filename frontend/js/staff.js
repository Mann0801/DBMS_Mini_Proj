// CampusEats staff page: PIN login, tabs, Orders tab, Ingredients tab.
// Food and Stats tabs are loaded through their Manoj-owned modules below.

const REFRESH_MS = 15000;
const ACTIVE = ["placed", "accepted", "preparing", "ready"];
const NEXT_STATUS = {
  accepted: { status: "preparing", label: "Start preparing" },
  preparing: { status: "ready", label: "Mark ready" },
  ready: { status: "collected", label: "Mark collected" },
};

const $ = (id) => document.getElementById(id);

let currentTab = "orders";
let allOrders = [];
const orderErrors = {};   // order id -> last error message shown on its card
let busy = false;         // true while an order action is running
let refreshTimer = null;

// Loaders run every time a tab is opened.
const tabLoaders = {
  orders: loadOrders,
  ingredients: loadIngredients,
  food: loadFood,
  stats: loadStats,
};

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
  if (err.status === 401) {
    logout("Your PIN is no longer valid. Please log in again.");
    return;
  }
  toast(err.message, "error");
}

// ============================================================ login

async function tryLogin(pin) {
  // any staff route works as a PIN check
  await API.get("/api/staff/orders?status=placed", { staff: true, pin });
}

function showApp() {
  $("login-view").hidden = true;
  $("app-view").hidden = false;
  $("logout-btn").hidden = false;
  switchTab(currentTab);
  startAutoRefresh();
}

function logout(message) {
  API.clearPin();
  stopAutoRefresh();
  $("app-view").hidden = true;
  $("logout-btn").hidden = true;
  $("login-view").hidden = false;
  $("pin-input").value = "";
  $("pin-input").focus();
  const errBox = $("login-error");
  errBox.textContent = message || "";
  errBox.hidden = !message;
}

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const pin = $("pin-input").value.trim();
  const btn = e.submitter;
  btn.disabled = true;
  try {
    await tryLogin(pin);
    API.setPin(pin);
    $("login-error").hidden = true;
    showApp();
  } catch (err) {
    $("login-error").textContent =
      err.status === 401 ? "Wrong PIN. Try again." : err.message;
    $("login-error").hidden = false;
  } finally {
    btn.disabled = false;
  }
});

$("logout-btn").addEventListener("click", () => logout());

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
  t.addEventListener("click", () => switchTab(t.dataset.tab))
);

// ============================================================ orders tab

function startAutoRefresh() {
  stopAutoRefresh();
  refreshTimer = setInterval(() => {
    if (currentTab === "orders" && document.visibilityState === "visible" && !busy) {
      loadOrders();
    }
  }, REFRESH_MS);
}

function stopAutoRefresh() {
  clearInterval(refreshTimer);
  refreshTimer = null;
}

async function loadOrders() {
  try {
    allOrders = await API.get("/api/staff/orders", { staff: true });
    renderOrders();
    $("last-updated").textContent =
      "Updated " + new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch (err) {
    handleError(err);
  }
}

function filteredOrders() {
  const f = $("status-filter").value;
  let list;
  if (f === "all") list = allOrders;
  else if (f === "active") list = allOrders.filter((o) => ACTIVE.includes(o.status));
  else if (f === "unpaid") list = allOrders.filter((o) => o.payment_status === "unpaid" && !["placed", "rejected"].includes(o.status));
  else list = allOrders.filter((o) => o.status === f);

  // queue order (oldest first) for active work, newest first otherwise
  const oldestFirst = f === "active" || ACTIVE.includes(f);
  return [...list].sort((a, b) => (oldestFirst ? a.id - b.id : b.id - a.id));
}

function renderCounts() {
  const counts = {};
  for (const o of allOrders) counts[o.status] = (counts[o.status] || 0) + 1;
  $("order-counts").innerHTML = ACTIVE
    .map((s) => `<span class="badge ${s}">${s}: ${counts[s] || 0}</span>`)
    .join("");
}

function orderCardHtml(o) {
  const items = o.items
    .map((i) => `<li><span>${i.quantity} × ${escapeHtml(i.name)}</span><span>${formatMoney(i.line_total)}</span></li>`)
    .join("");

  const buttons = [];
  if (o.status === "placed") {
    buttons.push(`<button class="ok small" data-action="accept" data-id="${o.id}">Accept</button>`);
    buttons.push(`<button class="danger small" data-action="reject" data-id="${o.id}">Reject</button>`);
  }
  if (NEXT_STATUS[o.status]) {
    const next = NEXT_STATUS[o.status];
    buttons.push(`<button class="primary small" data-action="status" data-status="${next.status}" data-id="${o.id}">${next.label}</button>`);
  }
  if (o.payment_status === "unpaid" && !["placed", "rejected"].includes(o.status)) {
    buttons.push(`<button class="small" data-action="paid" data-id="${o.id}">Mark paid</button>`);
  }
  if (["accepted", "preparing", "ready"].includes(o.status)) {
    buttons.push(`<button class="danger small" data-action="cancel" data-id="${o.id}">Cancel</button>`);
  }

  const error = orderErrors[o.id]
    ? `<div class="alert error order-error">${escapeHtml(orderErrors[o.id])}</div>`
    : "";

  return `
    <article class="card order-card">
      <header>
        <div>
          <div class="order-id">#${o.id}</div>
          <div>${escapeHtml(o.customer_name)} <span class="muted">· ${escapeHtml(o.customer_phone)}</span></div>
          <div class="muted" style="font-size:.85rem">${formatTime(o.created_at)}</div>
        </div>
        <div class="row" style="justify-content:flex-end">
          <span class="badge ${o.status}">${o.status}</span>
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
  const base = `/api/staff/orders/${id}`;

  if (action === "reject" && !confirm(`Reject order #${id}?`)) return;
  if (action === "cancel" && !confirm(`Cancel order #${id}? Its ingredients will go back into stock.`)) return;

  busy = true;
  btn.disabled = true;
  try {
    let msg;
    if (action === "accept") {
      await API.post(`${base}/accept`, { staff: true });
      msg = `Order #${id} accepted. Stock deducted.`;
    } else if (action === "reject") {
      await API.post(`${base}/reject`, { staff: true });
      msg = `Order #${id} rejected.`;
    } else if (action === "cancel") {
      await API.post(`${base}/cancel`, { staff: true });
      msg = `Order #${id} cancelled. Stock restored.`;
    } else if (action === "status") {
      await API.patch(`${base}/status`, { staff: true, body: { status: btn.dataset.status } });
      msg = `Order #${id} is now ${btn.dataset.status}.`;
    } else if (action === "paid") {
      await API.patch(`${base}/paid`, { staff: true });
      msg = `Order #${id} marked paid.`;
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

// ============================================================ ingredients tab

async function loadIngredients() {
  try {
    const rows = await API.get("/api/staff/ingredients", { staff: true });
    renderIngredients(rows);
  } catch (err) {
    handleError(err);
  }
}

function renderIngredients(rows) {
  const low = rows.filter((r) => r.is_low);
  const alertBox = $("low-stock-alert");
  if (low.length) {
    alertBox.innerHTML =
      `<strong>Low stock (${low.length}):</strong> ` +
      low.map((r) => `${escapeHtml(r.name)} (${formatQty(r.stock)} ${escapeHtml(r.unit)})`).join(", ");
    alertBox.hidden = false;
  } else {
    alertBox.hidden = true;
  }

  $("ingredients-body").innerHTML = rows.length
    ? rows.map((r) => `
      <tr class="${r.is_low ? "low" : ""}" data-id="${r.id}">
        <td><strong>${escapeHtml(r.name)}</strong></td>
        <td class="num">${formatQty(r.stock)} ${escapeHtml(r.unit)}</td>
        <td class="num">${formatQty(r.low_stock_threshold)} ${escapeHtml(r.unit)}</td>
        <td>${r.is_low ? '<span class="badge low">Low</span>' : '<span class="badge ready">OK</span>'}</td>
        <td>
          <form class="inline-form restock-form" data-id="${r.id}" data-name="${escapeHtml(r.name)}">
            <input type="number" min="0.001" step="0.001" placeholder="Qty" required aria-label="Amount to add">
            <button type="submit" class="small">Add</button>
          </form>
        </td>
        <td><button class="small history-btn" data-id="${r.id}">History</button></td>
      </tr>`).join("")
    : `<tr><td colspan="6" class="empty">No ingredients yet.</td></tr>`;
}

$("ingredients-body").addEventListener("submit", async (e) => {
  const form = e.target.closest(".restock-form");
  if (!form) return;
  e.preventDefault();
  const input = form.querySelector("input");
  const amount = Number(input.value);
  if (!(amount > 0)) return;
  const btn = form.querySelector("button");
  btn.disabled = true;
  try {
    const ing = await API.patch(`/api/staff/ingredients/${form.dataset.id}/stock`, {
      staff: true, body: { amount },
    });
    toast(`Added ${formatQty(amount)} ${ing.unit} of ${ing.name}. Now ${formatQty(ing.stock)} ${ing.unit}.`);
    await loadIngredients();
  } catch (err) {
    handleError(err);
    btn.disabled = false;
  }
});

$("ingredients-body").addEventListener("click", async (e) => {
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
    const txns = await API.get(`/api/staff/ingredients/${btn.dataset.id}/transactions`, { staff: true });
    const body = txns.length
      ? txns.map((t) => `
          <tr>
            <td>${formatTime(t.created_at)}</td>
            <td class="num" style="color:${t.change_amount < 0 ? "var(--danger)" : "var(--ok)"}">
              ${t.change_amount > 0 ? "+" : ""}${formatQty(t.change_amount)}</td>
            <td>${escapeHtml(t.reason.replaceAll("_", " "))}</td>
            <td>${t.order_id ? "#" + t.order_id : ""}</td>
          </tr>`).join("")
      : `<tr><td colspan="4" class="muted">No stock changes yet.</td></tr>`;
    row.insertAdjacentHTML("afterend", `
      <tr class="history-row"><td colspan="6">
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

$("ingredients-refresh-btn").addEventListener("click", loadIngredients);

$("add-ingredient-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.submitter;
  btn.disabled = true;
  try {
    const ing = await API.post("/api/staff/ingredients", {
      staff: true,
      body: {
        name: $("ing-name").value.trim(),
        unit: $("ing-unit").value.trim(),
        stock: Number($("ing-stock").value),
        low_stock_threshold: Number($("ing-threshold").value),
      },
    });
    toast(`Added ${ing.name}.`);
    e.target.reset();
    await loadIngredients();
  } catch (err) {
    handleError(err);
  } finally {
    btn.disabled = false;
  }
});

// ============================================================ Manoj: food management

let foodRows = [];
let foodCategories = [];

async function loadFood() {
  try {
    [foodRows, foodCategories] = await Promise.all([
      API.get("/api/staff/food", { staff: true }), API.get("/api/categories"),
    ]);
    $("food-category").innerHTML = foodCategories.map((c) =>
      `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
    $("food-body").innerHTML = foodRows.length ? foodRows.map((f) => `
      <tr data-id="${f.id}">
        <td><strong>${escapeHtml(f.name)}</strong><div class="muted">${escapeHtml(f.description || "")}</div></td>
        <td>${escapeHtml(f.category_name)}</td><td class="num">${formatMoney(f.price)}</td>
        <td><span class="badge ${f.is_available ? "ready" : "rejected"}">${f.is_available ? "Available" : "Unavailable"}</span></td>
        <td><div class="row"><button class="small" data-food-action="edit" data-id="${f.id}">Edit</button><button class="small danger" data-food-action="delete" data-id="${f.id}">Delete</button></div></td>
      </tr>`).join("") : '<tr><td colspan="5" class="empty">No food items yet.</td></tr>';
  } catch (err) { handleError(err); }
}

function clearFoodForm() {
  $("food-form").reset();
  $("food-id").value = "";
  $("food-form-title").textContent = "Add a food item";
  $("food-save-btn").textContent = "Add food item";
  $("food-cancel-edit").hidden = true;
}

$("food-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = $("food-id").value;
  const btn = $("food-save-btn");
  btn.disabled = true;
  const body = {
    name: $("food-name").value.trim(),
    description: $("food-description").value.trim() || null,
    price: Number($("food-price").value),
    category_id: Number($("food-category").value),
    is_available: $("food-available").value === "true",
  };
  try {
    const saved = id
      ? await API.put(`/api/staff/food/${id}`, { staff: true, body })
      : await API.post("/api/staff/food", { staff: true, body });
    toast(`${saved.name} ${id ? "updated" : "added"}.`);
    clearFoodForm();
    await loadFood();
  } catch (err) { handleError(err); }
  finally { btn.disabled = false; }
});

$("food-cancel-edit").addEventListener("click", clearFoodForm);
$("food-refresh-btn").addEventListener("click", loadFood);
$("food-body").addEventListener("click", async (event) => {
  const btn = event.target.closest("button[data-food-action]");
  if (!btn) return;
  const item = foodRows.find((f) => f.id === Number(btn.dataset.id));
  if (!item) return;
  if (btn.dataset.foodAction === "edit") {
    $("food-id").value = item.id;
    $("food-name").value = item.name;
    $("food-description").value = item.description || "";
    $("food-price").value = item.price;
    $("food-category").value = item.category_id;
    $("food-available").value = String(Boolean(item.is_available));
    $("food-form-title").textContent = `Edit ${item.name}`;
    $("food-save-btn").textContent = "Save changes";
    $("food-cancel-edit").hidden = false;
    $("food-form").scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  if (!confirm(`Delete ${item.name}? Items already ordered will be made unavailable.`)) return;
  btn.disabled = true;
  try {
    const result = await API.del(`/api/staff/food/${item.id}`, { staff: true });
    toast(result.deleted ? `${item.name} deleted.` : `${item.name} has past orders and was marked unavailable.`);
    await loadFood();
  } catch (err) { handleError(err); }
});

// ============================================================ Manoj: statistics

const STAT_REPORTS = [
  ["Daily sales (7 days)", "/api/staff/stats/daily-sales"],
  ["Top items (ranked)", "/api/staff/stats/top-items"],
  ["Running sales total", "/api/staff/stats/running-total"],
  ["Sales by category", "/api/staff/stats/category-sales"],
  ["Never ordered", "/api/staff/stats/never-ordered"],
  ["Orders above average", "/api/staff/stats/above-average-orders"],
  ["Ingredients shared by dishes", "/api/staff/stats/shared-ingredients"],
  ["Ingredients used by one dish", "/api/staff/stats/single-dish-ingredients"],
  ["Item sales (including zero sales)", "/api/staff/stats/item-sales"],
  ["Sales report view", "/api/staff/stats/reports/sales"],
  ["Low stock view", "/api/staff/stats/reports/low-stock"],
  ["Unpaid orders view", "/api/staff/stats/reports/unpaid-orders"],
  ["Top items view", "/api/staff/stats/reports/top-items"],
];

function statsTable(rows) {
  if (!rows.length) return '<p class="muted">No rows to report.</p>';
  const columns = Object.keys(rows[0]);
  return `<div class="table-wrap"><table><thead><tr>${columns.map((c) => `<th>${escapeHtml(c.replaceAll("_", " "))}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${columns.map((c) => `<td>${escapeHtml(row[c])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

async function loadStats() {
  const grid = $("stats-grid");
  grid.innerHTML = STAT_REPORTS.map(([title], i) => `<article class="card stats-card"><h3>${escapeHtml(title)}</h3><div id="stat-${i}" class="muted">Loading…</div></article>`).join("");
  await Promise.all(STAT_REPORTS.map(async ([, path], i) => {
    try {
      const rows = await API.get(path, { staff: true });
      $(`stat-${i}`).innerHTML = statsTable(rows);
    } catch (err) {
      $(`stat-${i}`).innerHTML = `<div class="alert error">${escapeHtml(err.message)}</div>`;
      if (err.status === 401) handleError(err);
    }
  }));
}

$("stats-refresh-btn").addEventListener("click", loadStats);

// ============================================================ start

if (API.pin()) {
  // check the saved PIN is still right
  tryLogin(API.pin()).then(showApp).catch((err) => {
    logout(err.status === 401 ? "" : err.message);
  });
} else {
  logout();
}
