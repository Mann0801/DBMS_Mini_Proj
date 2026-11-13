// Dish details from MongoDB, shown on the student menu. Owner: Mann.
// student.js calls DishDetails.load(), DishDetails.allowedIds() and
// DishDetails.chips(id). If MongoDB is down, the menu still works:
// it just shows no tags and the diet filters do nothing.

const DishDetails = {
  byId: new Map(),
  available: false,

  async load() {
    try {
      const docs = await API.get("/api/food-details");
      DishDetails.byId = new Map(docs.map((d) => [d.food_item_id, d]));
      DishDetails.available = true;
    } catch {
      DishDetails.available = false;
    }
  },

  // Ask MongoDB which dishes match the diet filters.
  // Returns a Set of food ids, or null when no filter is set.
  async allowedIds() {
    if (!DishDetails.available) return null;
    const veg = document.getElementById("veg-only")?.checked;
    const avoid = document.getElementById("avoid-allergen")?.value;
    const spice = document.getElementById("max-spice")?.value;
    if (!veg && !avoid && spice === "") return null;
    const docs = await API.get(API.withQuery("/api/food-details", {
      dietary: veg ? "veg" : "", exclude_allergen: avoid, max_spice: spice,
    }));
    return new Set(docs.map((d) => d.food_item_id));
  },

  chips(foodId) {
    const d = DishDetails.byId.get(foodId);
    if (!d) return "";
    const diet = {
      veg: ["veg", "Veg"], vegan: ["veg", "Vegan"], egg: ["egg", "Egg"], "non-veg": ["nonveg", "Non-veg"],
    }[d.dietary] || ["veg", d.dietary];
    const spice = d.spice_level > 0 ? `<span class="chip">${"🌶".repeat(d.spice_level)}</span>` : "";
    const allergens = d.allergens.length
      ? `<div class="muted small-text">Contains: ${d.allergens.map(escapeHtml).join(", ")}</div>` : "";
    const special = d.special && d.special.note
      ? `<div class="special-note">★ ${escapeHtml(d.special.note)}</div>` : "";
    const tags = d.tags.slice(0, 2).map((t) => `<span class="chip">${escapeHtml(t)}</span>`).join("");
    return `
      <div class="dish-chips">
        <span class="diet-dot ${diet[0]}" title="${escapeHtml(diet[1])}"></span>
        <span class="chip">${escapeHtml(diet[1])}</span>${spice}${tags}
      </div>${allergens}${special}`;
  },
};
