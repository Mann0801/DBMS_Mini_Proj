// Student menu, cart, checkout, and order tracking.
const $ = (id) => document.getElementById(id);
let menuItems = [];
const cart = new Map();
let menuTimer;

async function loadCategories() {
  const rows = await API.get("/api/categories");
  $("category-filter").innerHTML = '<option value="">All categories</option>' +
    rows.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
}

async function loadMenu() {
  const message = $("menu-message");
  message.hidden = true;
  const menuPath = API.withQuery("/api/menu", {
    q: $("menu-search").value.trim(), category: $("category-filter").value,
  });
  try {
    menuItems = await API.get(menuPath);
    const allowed = await DishDetails.allowedIds();  // (Mann) MongoDB diet filters
    if (allowed) menuItems = menuItems.filter((item) => allowed.has(item.id));
    renderMenu();
  } catch (err) {
    message.textContent = err.message;
    message.hidden = false;
    $("menu-grid").replaceChildren();
  }
}

function renderMenu() {
  $("menu-grid").innerHTML = menuItems.length ? menuItems.map((item) => `
    <article class="card food-card">
      <div class="row"><span class="badge">${escapeHtml(item.category_name)}</span><span class="spacer"></span><strong>${formatMoney(item.price)}</strong></div>
      <h2>${escapeHtml(item.name)}</h2>
      <p class="muted">${escapeHtml(item.description || "A fresh canteen favourite.")}</p>
      ${DishDetails.chips(item.id)}
      <button class="primary" data-add="${item.id}">Add to cart</button>
    </article>`).join("") : '<div class="card empty">No available dishes match your search.</div>';
}

function renderCart() {
  const lines = [...cart.values()];
  $("cart-items").innerHTML = lines.length ? lines.map(({ item, quantity }) => `
    <div class="cart-line">
      <div><strong>${escapeHtml(item.name)}</strong><div class="muted">${formatMoney(item.price)} each</div></div>
      <div class="quantity-control">
        <button type="button" aria-label="Remove one ${escapeHtml(item.name)}" data-cart="remove" data-id="${item.id}">−</button>
        <span>${quantity}</span>
        <button type="button" aria-label="Add one ${escapeHtml(item.name)}" data-cart="add" data-id="${item.id}">+</button>
      </div>
    </div>`).join("") : '<p class="muted">Your cart is empty.</p>';
  const total = lines.reduce((sum, line) => sum + Number(line.item.price) * line.quantity, 0);
  $("cart-total").textContent = formatMoney(total);
  $("checkout-form").querySelector('button[type="submit"]').disabled = !lines.length;
}

function changeCart(item, delta) {
  const line = cart.get(item.id) || { item, quantity: 0 };
  line.quantity += delta;
  if (line.quantity > 10) line.quantity = 10;
  if (line.quantity <= 0) cart.delete(item.id);
  else cart.set(item.id, line);
  renderCart();
}

$("menu-grid").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-add]");
  if (!button) return;
  const item = menuItems.find((row) => row.id === Number(button.dataset.add));
  if (item) changeCart(item, 1);
});

$("cart-items").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-cart]");
  if (!button) return;
  const line = cart.get(Number(button.dataset.id));
  if (line) changeCart(line.item, button.dataset.cart === "add" ? 1 : -1);
});

$("menu-filters").addEventListener("submit", (event) => { event.preventDefault(); loadMenu(); });
$("category-filter").addEventListener("change", loadMenu);
$("menu-search").addEventListener("input", () => {
  clearTimeout(menuTimer);
  menuTimer = setTimeout(loadMenu, 250);
});

$("checkout-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  const notice = $("checkout-message");
  notice.hidden = true;
  button.disabled = true;
  try {
    const order = await API.post("/api/orders", { body: {
      name: $("customer-name").value.trim(),
      phone: $("customer-phone").value.trim(),
      items: [...cart.values()].map(({ item, quantity }) => ({ food_item_id: item.id, quantity })),
    }});
    cart.clear();
    renderCart();
    notice.className = "alert success";
    notice.innerHTML = `Order placed. Your order number is <strong>#${Number(order.id)}</strong>. Save it to track your order.`;
    notice.hidden = false;
    $("track-order-id").value = order.id;
    $("track-phone").value = $("customer-phone").value.trim();
  } catch (err) {
    notice.className = "alert error";
    notice.textContent = err.message;
    notice.hidden = false;
  } finally {
    button.disabled = cart.size === 0;
  }
});

$("track-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const result = $("track-result");
  result.textContent = "Looking up your order…";
  const id = encodeURIComponent($("track-order-id").value);
  const phone = encodeURIComponent($("track-phone").value.trim());
  try {
    const order = await API.get(`/api/orders/${id}?phone=${phone}`);
    result.innerHTML = `<div class="alert success"><strong>Order #${Number(order.id)} — ${escapeHtml(order.status)}</strong><br>${formatMoney(order.total)} · ${formatTime(order.created_at)}<ul>${order.items.map((item) => `<li>${Number(item.quantity)} × ${escapeHtml(item.name)}</li>`).join("")}</ul></div>`;
  } catch (err) {
    result.innerHTML = `<div class="alert error">${escapeHtml(err.message)}</div>`;
  }
});

// (Mann) MongoDB diet filters
["veg-only", "avoid-allergen", "max-spice"].forEach((id) =>
  $(id).addEventListener("change", loadMenu));

renderCart();
Promise.all([loadCategories(), DishDetails.load().then(loadMenu)]).catch((err) => {
  $("menu-message").textContent = err.message;
  $("menu-message").hidden = false;
});
