"use strict";
const $ = (id) => document.getElementById(id);
let user;
user = Auth.user();
if (!user || user.role !== "student" || !Auth.token()) location.replace("/login.html");

let menuItems = [];
const cart = new Map();
let menuTimer;
$("welcome-name").textContent = user?.name || "";

async function loadCategories() {
  const rows = await API.get("/api/menu/categories");
  $("category-filter").innerHTML = '<option value="">All categories</option>' +
    rows.map((c) => `<option>${escapeHtml(c)}</option>`).join("");
}

async function loadMenu() {
  const notice = $("menu-message"); notice.hidden = true;
  try {
    const path = API.withQuery("/api/menu", { q: $("menu-search").value.trim(), category: $("category-filter").value });
    menuItems = await API.get(path); renderMenu();
  } catch (err) { notice.textContent = err.message; notice.hidden = false; $("menu-grid").replaceChildren(); }
}

function renderMenu() {
  $("menu-grid").innerHTML = menuItems.length ? menuItems.map((item) => {
    const soldOut = item.status !== "available" || Number(item.current_stock) < 1;
    const stock = Number(item.current_stock);
    return `<article class="card food-card ${soldOut ? "sold-out" : ""}">
      <div class="row"><span class="badge">${escapeHtml(item.category)}</span><span class="spacer"></span><strong>${formatMoney(item.price)}</strong></div>
      <h2>${escapeHtml(item.name)}</h2><p class="muted">${escapeHtml(item.description || "Freshly prepared at the canteen.")}</p>
      ${!soldOut && stock <= Number(item.low_stock_threshold) ? `<p class="stock-note">Only ${stock} left</p>` : ""}
      <button class="primary" data-add="${item.item_id}" ${soldOut ? "disabled" : ""}>${soldOut ? "Sold out" : "Add to cart"}</button>
    </article>`;
  }).join("") : '<div class="card empty">No available dishes match your search.</div>';
}

function renderCart() {
  const lines = [...cart.values()];
  $("cart-items").innerHTML = lines.length ? lines.map(({ item, quantity }) => `
    <div class="cart-line"><div><strong>${escapeHtml(item.name)}</strong><div class="muted">${formatMoney(item.price)} each</div></div>
    <div class="quantity-control"><button data-cart="remove" data-id="${item.item_id}" aria-label="Remove one">−</button>
    <span>${quantity}</span><button data-cart="add" data-id="${item.item_id}" aria-label="Add one" ${quantity >= Math.min(10, item.current_stock) ? "disabled" : ""}>+</button></div></div>`).join("") : '<p class="muted">Your cart is empty.</p>';
  $("cart-total").textContent = formatMoney(lines.reduce((sum, x) => sum + Number(x.item.price) * x.quantity, 0));
  $("checkout-button").disabled = !lines.length;
}

function changeCart(item, delta) {
  const line = cart.get(item.item_id) || { item, quantity: 0 };
  line.quantity = Math.min(Math.min(10, Number(item.current_stock)), line.quantity + delta);
  if (line.quantity <= 0) cart.delete(item.item_id); else cart.set(item.item_id, line);
  renderCart();
}

$("menu-grid").addEventListener("click", (e) => {
  const button = e.target.closest("[data-add]"); if (!button) return;
  const item = menuItems.find((x) => x.item_id === Number(button.dataset.add)); if (item) changeCart(item, 1);
});
$("cart-items").addEventListener("click", (e) => {
  const button = e.target.closest("[data-cart]"); if (!button) return;
  const line = cart.get(Number(button.dataset.id)); if (line) changeCart(line.item, button.dataset.cart === "add" ? 1 : -1);
});
$("menu-search").addEventListener("input", () => { clearTimeout(menuTimer); menuTimer = setTimeout(loadMenu, 250); });
$("category-filter").addEventListener("change", loadMenu);
$("menu-filters").addEventListener("submit", (e) => { e.preventDefault(); loadMenu(); });

$("checkout-form").addEventListener("submit", async (e) => {
  e.preventDefault(); const notice = $("checkout-message"); notice.hidden = true;
  $("checkout-button").disabled = true;
  try {
    const order = await API.post("/api/orders", { body: { items: [...cart.values()].map(({ item, quantity }) => ({ item_id: item.item_id, quantity })) } });
    cart.clear(); renderCart();
    notice.className = "alert success";
    notice.textContent = `Order #${order.order_id ?? order.id} placed. Pay at the counter when collecting.`;
    notice.hidden = false; await loadOrders();
  } catch (err) { notice.className = "alert error"; notice.textContent = err.message; notice.hidden = false; }
  finally { renderCart(); }
});

async function loadOrders() {
  try {
    const orders = await API.get("/api/orders/mine");
    $("orders-list").innerHTML = orders.length ? orders.map((o) => `<article class="card order-history">
      <div class="row"><strong>Order #${Number(o.order_id)}</strong><span class="badge ${escapeHtml(o.status)}">${escapeHtml(o.status)}</span><span class="badge ${escapeHtml(o.payment_status)}">${escapeHtml(o.payment_status)}</span><span class="spacer"></span><strong>${formatMoney(o.total)}</strong></div>
      <p class="muted">${(o.items || []).map((i) => `${Number(i.quantity)} × ${escapeHtml(i.name)}`).join(" · ")}</p>
      ${o.status === "placed" ? `<button class="small danger" data-cancel="${Number(o.order_id)}">Cancel order</button>` : ""}</article>`).join("") : '<p class="muted">You have no orders yet.</p>';
  } catch (err) { $("orders-list").innerHTML = `<div class="alert error">${escapeHtml(err.message)}</div>`; }
}
$("orders-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-cancel]"); if (!btn) return;
  btn.disabled = true;
  try { await API.post(`/api/orders/${btn.dataset.cancel}/cancel`); await loadOrders(); await loadMenu(); }
  catch (err) { btn.disabled = false; alert(err.message); }
});
$("logout-btn").addEventListener("click", () => Auth.logout());

renderCart();
Promise.all([loadCategories(), loadMenu(), loadOrders()]).catch((err) => { $("menu-message").textContent = err.message; $("menu-message").hidden = false; });
