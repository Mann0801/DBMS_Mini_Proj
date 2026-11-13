// Manoj's staff reporting tab.
const MENU_STAT_REPORTS = [
  ["Daily sales (last 7 days)", "/api/staff/stats/daily-sales"],
  ["Top-selling items", "/api/staff/stats/top-items"],
  ["Running sales total", "/api/staff/stats/running-total"],
  ["Sales per category", "/api/staff/stats/category-sales"],
  ["Items never ordered", "/api/staff/stats/never-ordered"],
  ["Orders above average", "/api/staff/stats/above-average-orders"],
  ["Items both students ordered", "/api/staff/stats/student-items/both"],
  ["Items A ordered but B did not", "/api/staff/stats/student-items/a-only"],
  ["Top spenders per category", "/api/staff/stats/top-spenders-by-category"],
  ["Available items view", "/api/staff/stats/reports/available-items"],
  ["Paid sales report view", "/api/staff/stats/reports/sales"],
  ["Low stock view", "/api/staff/stats/reports/low-stock"],
  ["Unpaid orders view", "/api/staff/stats/reports/unpaid-orders"],
];

function reportTable(rows) {
  if (!rows.length) return '<p class="muted">No rows to report.</p>';
  const columns = Object.keys(rows[0]);
  return `<div class="table-wrap"><table><thead><tr>${columns.map((c) => `<th>${escapeHtml(c.replaceAll("_", " "))}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${columns.map((c) => `<td>${escapeHtml(row[c])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

async function loadStatsTab() {
  const grid = $("stats-grid");
  let students = [];
  try { students = await API.get("/api/staff/students"); }
  catch (err) { handleError(err); }
  const options = students.map((s) => `<option value="${s.user_id}">${escapeHtml(s.name)}</option>`).join("");
  grid.innerHTML = MENU_STAT_REPORTS.map(([title, path], i) => `
    <article class="card stats-card"><h3>${escapeHtml(title)}</h3>
      ${path.includes("student-items") ? `<div class="form-grid">
        <div><label for="report-a-${i}">Student A</label><select id="report-a-${i}">${options}</select></div>
        <div><label for="report-b-${i}">Student B</label><select id="report-b-${i}">${options}</select></div>
        <button class="small" data-run-report="${i}">Run query</button>
      </div>` : ""}
      <div id="report-result-${i}" class="muted">${path.includes("student-items") ? "Choose two students and run the query." : "Loading…"}</div>
    </article>`).join("");
  if (students.length > 1) {
    MENU_STAT_REPORTS.forEach(([, path], i) => {
      if (path.includes("student-items")) $(`report-b-${i}`).value = String(students[1].user_id);
    });
  }
  await Promise.all(MENU_STAT_REPORTS.map(async ([, path], i) => {
    if (path.includes("student-items")) return;
    try { $(`report-result-${i}`).innerHTML = reportTable(await API.get(path)); }
    catch (err) { $(`report-result-${i}`).innerHTML = `<div class="alert error">${escapeHtml(err.message)}</div>`; }
  }));
}

$("stats-grid").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-run-report]");
  if (!button) return;
  const i = Number(button.dataset.runReport);
  if ($(`report-a-${i}`).value === $(`report-b-${i}`).value) {
    $(`report-result-${i}`).textContent = "Choose two different students";
    return;
  }
  const url = API.withQuery(MENU_STAT_REPORTS[i][1], {
    student_a: $(`report-a-${i}`).value, student_b: $(`report-b-${i}`).value,
  });
  button.disabled = true;
  try { $(`report-result-${i}`).innerHTML = reportTable(await API.get(url)); }
  catch (err) { $(`report-result-${i}`).innerHTML = `<div class="alert error">${escapeHtml(err.message)}</div>`; }
  finally { button.disabled = false; }
});

$("stats-refresh-btn").addEventListener("click", loadStatsTab);
tabLoaders.stats = loadStatsTab;
