// Manoj's staff menu tab. The staff shell exposes $ and tabLoaders.
let menuRows = [];

async function loadMenuTab() {
  try {
    [menuRows, menuCategories] = await Promise.all([
      API.get("/api/staff/menu"), API.get("/api/menu/categories"),
    ]);
    $("menu-category-options").innerHTML = menuCategories.map((c) => `<option value="${escapeHtml(c)}"></option>`).join("");
    $("menu-body").innerHTML = menuRows.length ? menuRows.map((item) => `
      <tr><td><strong>${escapeHtml(item.name)}</strong><div class="muted">${escapeHtml(item.description || "")}</div></td>
        <td>${escapeHtml(item.category)}</td><td class="num">${formatMoney(item.price)}</td><td>${Number(item.current_stock)}</td>
        <td><span class="badge ${escapeHtml(item.status)}">${escapeHtml(item.status.replaceAll("_", " "))}</span></td>
        <td><div class="row"><button class="small" data-menu-edit="${item.item_id}">Edit</button><button class="small danger" data-menu-delete="${item.item_id}">Delete / delist</button></div></td></tr>
    `).join("") : '<tr><td colspan="6" class="empty">No menu items yet.</td></tr>';
  } catch (err) { handleError(err); }
}

let menuCategories = [];
function resetMenuForm() {
  $("menu-form").reset();
  $("menu-item-id").value = "";
  $("menu-form-title").textContent = "Add a menu item";
  $("menu-save-btn").textContent = "Add menu item";
  $("menu-cancel-edit").hidden = true;
  $("menu-stock-field").hidden = false;
  $("menu-threshold-field").hidden = false;
  $("menu-status").disabled = true;
}

$("menu-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = $("menu-item-id").value;
  const button = $("menu-save-btn"); button.disabled = true;
  const item = {
    name: $("menu-name").value.trim(), description: $("menu-description").value.trim() || null,
    category: $("menu-category").value.trim(), price: Number($("menu-price").value),
    current_stock: Number($("menu-stock").value), low_stock_threshold: Number($("menu-threshold").value),
    status: $("menu-status").value,
  };
  try {
    const saved = id
      ? await API.put(`/api/staff/menu/${id}`, { body: { name: item.name, description: item.description, category: item.category, price: item.price, status: item.status } })
      : await API.post("/api/staff/menu", { body: item });
    toast(`${saved.name} ${id ? "updated" : "added"}.`);
    resetMenuForm(); await loadMenuTab();
  } catch (err) { handleError(err); }
  finally { button.disabled = false; }
});

$("menu-cancel-edit").addEventListener("click", resetMenuForm);
$("menu-refresh-btn").addEventListener("click", loadMenuTab);
$("menu-body").addEventListener("click", async (event) => {
  const edit = event.target.closest("[data-menu-edit]");
  const del = event.target.closest("[data-menu-delete]");
  if (edit) {
    const item = menuRows.find((row) => row.item_id === Number(edit.dataset.menuEdit));
    if (!item) return;
    $("menu-item-id").value = item.item_id; $("menu-name").value = item.name;
    $("menu-description").value = item.description || ""; $("menu-category").value = item.category;
    $("menu-price").value = item.price; $("menu-status").value = item.status;
    $("menu-status").disabled = false; $("menu-stock-field").hidden = true; $("menu-threshold-field").hidden = true;
    $("menu-form-title").textContent = `Edit ${item.name}`; $("menu-save-btn").textContent = "Save changes";
    $("menu-cancel-edit").hidden = false; $("menu-form").scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  if (!del) return;
  const item = menuRows.find((row) => row.item_id === Number(del.dataset.menuDelete));
  if (!item || !confirm(`Delete or delist ${item.name}? Items with order history will be delisted.`)) return;
  del.disabled = true;
  try {
    const result = await API.del(`/api/staff/menu/${item.item_id}`);
    toast(result.deleted ? `${item.name} deleted.` : `${item.name} was delisted because it has order history.`);
    await loadMenuTab();
  } catch (err) { handleError(err); del.disabled = false; }
});

resetMenuForm();
tabLoaders.menu = loadMenuTab;
