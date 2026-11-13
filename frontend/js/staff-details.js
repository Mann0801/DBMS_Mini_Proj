// Staff "Dish Details" tab: read, update and delete MongoDB documents.
// Owner: Mann. Loaded after staff.js and uses its helpers
// ($, toast, handleError, tabLoaders).

const ALLERGENS = ["gluten", "dairy", "nuts", "peanuts", "egg", "soy"];
const DIET_LABEL = { veg: "Veg", vegan: "Vegan", egg: "Egg", "non-veg": "Non-veg" };

let detailDishes = [];          // from MariaDB (/api/staff/food)
let detailDocs = new Map();     // from MongoDB (/api/food-details)
let editingFoodId = null;

tabLoaders.details = loadDetails;

$("det-allergens").innerHTML = ALLERGENS.map((a) => `
  <label class="check"><input type="checkbox" value="${a}"> ${a}</label>`).join("");

async function loadDetails() {
  try {
    const [dishes, docs, summary] = await Promise.all([
      API.get("/api/staff/food", { staff: true }),
      API.get("/api/food-details"),
      API.get("/api/staff/food-details/summary", { staff: true }),
    ]);
    detailDishes = dishes;
    detailDocs = new Map(docs.map((d) => [d.food_item_id, d]));
    renderDetailsSummary(summary);
    renderDetails();
  } catch (err) {
    handleError(err);
    $("details-body").innerHTML =
      `<tr><td colspan="8" class="empty">${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderDetailsSummary(s) {
  const diet = s.by_dietary.map((d) =>
    `<span class="badge ready">${escapeHtml(DIET_LABEL[d.dietary] || d.dietary)}: ${d.dishes}</span>`);
  const allergens = s.by_allergen.map((a) =>
    `<span class="badge unpaid">${escapeHtml(a.allergen)}: ${a.dishes}</span>`);
  $("details-summary").innerHTML = [
    `<span class="badge">${s.total} documents</span>`, ...diet, ...allergens,
    `<span class="badge preparing">specials: ${s.specials}</span>`,
  ].join("");
}

function tagChips(d) {
  return d.tags.map((t) => `
    <span class="chip">${escapeHtml(t)}
      <button type="button" class="chip-x" title="Remove tag ($pull)"
              data-det-action="untag" data-id="${d.food_item_id}" data-tag="${escapeHtml(t)}">×</button>
    </span>`).join("");
}

function renderDetails() {
  $("details-body").innerHTML = detailDishes.map((f) => {
    const d = detailDocs.get(f.id);
    if (!d) {
      return `<tr data-id="${f.id}">
        <td><strong>${escapeHtml(f.name)}</strong></td>
        <td colspan="6" class="muted">No details in MongoDB yet</td>
        <td><button class="small" data-det-action="edit" data-id="${f.id}">Add</button></td>
      </tr>`;
    }
    const extra = Object.entries(d.extra || {})
      .map(([k, v]) => `${escapeHtml(k)}: ${escapeHtml(Array.isArray(v) ? v.join(", ") : v)}`).join("<br>");
    const special = d.special && d.special.note
      ? `${escapeHtml(d.special.note)}
         <button class="small" data-det-action="clear-special" data-id="${f.id}">Clear</button>`
      : '<span class="muted">—</span>';
    return `<tr data-id="${f.id}">
      <td><strong>${escapeHtml(f.name)}</strong></td>
      <td><span class="diet-dot ${d.dietary === "egg" ? "egg" : d.dietary === "non-veg" ? "nonveg" : "veg"}"></span>
          ${escapeHtml(DIET_LABEL[d.dietary] || d.dietary)}</td>
      <td>${d.spice_level ? "🌶".repeat(d.spice_level) : '<span class="muted">0</span>'}</td>
      <td>${d.allergens.length ? escapeHtml(d.allergens.join(", ")) : '<span class="muted">none</span>'}</td>
      <td>${tagChips(d) || '<span class="muted">—</span>'}</td>
      <td>${special}</td>
      <td class="muted small-text">${extra || "—"}</td>
      <td><div class="row">
        <button class="small" data-det-action="edit" data-id="${f.id}">Edit</button>
        <button class="small danger" data-det-action="delete" data-id="${f.id}">Delete</button>
      </div></td>
    </tr>`;
  }).join("") || `<tr><td colspan="8" class="empty">No dishes.</td></tr>`;
}

function openDetailsForm(foodId) {
  editingFoodId = foodId;
  const dish = detailDishes.find((f) => f.id === foodId);
  const d = detailDocs.get(foodId);
  $("details-form-title").textContent = `${d ? "Edit" : "Add"} details: ${dish ? dish.name : "#" + foodId}`;
  $("det-dietary").value = d ? d.dietary : "veg";
  $("det-spice").value = d ? String(d.spice_level) : "0";
  $("det-calories").value = d && d.calories != null ? d.calories : "";
  $("det-tags").value = d ? d.tags.join(", ") : "";
  $("det-special").value = d && d.special ? d.special.note : "";
  document.querySelectorAll("#det-allergens input").forEach((box) => {
    box.checked = !!d && d.allergens.includes(box.value);
  });
  const extraKeys = d ? Object.keys(d.extra || {}) : [];
  $("det-extra").textContent = extraKeys.length
    ? `Other fields kept as they are: ${extraKeys.join(", ")}` : "";
  $("det-extra").hidden = !extraKeys.length;
  $("details-form").hidden = false;
  $("details-form").scrollIntoView({ behavior: "smooth", block: "start" });
}

$("details-body").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-det-action]");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const action = btn.dataset.detAction;
  const base = `/api/staff/food-details/${id}`;

  if (action === "edit") { openDetailsForm(id); return; }
  if (action === "delete" && !confirm("Delete this dish's details from MongoDB?")) return;

  btn.disabled = true;
  try {
    if (action === "delete") {
      await API.del(base, { staff: true });
      toast("Details deleted from MongoDB.");
    } else if (action === "clear-special") {
      await API.patch(`${base}/special`, { staff: true, body: { note: null } });
      toast("Special cleared.");
    } else if (action === "untag") {
      await API.del(`${base}/tags/${encodeURIComponent(btn.dataset.tag)}`, { staff: true });
      toast(`Tag "${btn.dataset.tag}" removed.`);
    }
    await loadDetails();
  } catch (err) {
    handleError(err);
    btn.disabled = false;
  }
});

$("details-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (editingFoodId == null) return;
  const btn = e.submitter;
  btn.disabled = true;
  const calories = $("det-calories").value;
  const body = {
    dietary: $("det-dietary").value,
    spice_level: Number($("det-spice").value),
    calories: calories === "" ? null : Number(calories),
    tags: $("det-tags").value.split(",").map((t) => t.trim()).filter(Boolean),
    allergens: [...document.querySelectorAll("#det-allergens input:checked")].map((b) => b.value),
    special_note: $("det-special").value.trim() || null,
  };
  try {
    await API.put(`/api/staff/food-details/${editingFoodId}`, { staff: true, body });
    toast("Saved to MongoDB.");
    $("details-form").hidden = true;
    editingFoodId = null;
    await loadDetails();
  } catch (err) {
    handleError(err);
  } finally {
    btn.disabled = false;
  }
});

$("details-cancel").addEventListener("click", () => {
  $("details-form").hidden = true;
  editingFoodId = null;
});
$("details-refresh-btn").addEventListener("click", loadDetails);
