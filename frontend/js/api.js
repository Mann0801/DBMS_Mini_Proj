// Shared helpers for talking to the backend. Used by student.js and staff.js.
// (Basic version by Mann; Manoj can extend it.)

const API = {
  pin() {
    try { return sessionStorage.getItem("staffPin"); } catch { return null; }
  },

  setPin(pin) {
    try { sessionStorage.setItem("staffPin", pin); } catch { /* storage blocked */ }
  },

  clearPin() {
    try { sessionStorage.removeItem("staffPin"); } catch { /* storage blocked */ }
  },

  // Every call returns parsed JSON, or throws an Error whose message is the
  // backend's "detail" text (e.g. "Not enough Paneer to accept this order").
  async request(method, path, { body, staff = false, pin } = {}) {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (staff) headers["X-Staff-Pin"] = pin ?? API.pin() ?? "";

    let res;
    try {
      res = await fetch(path, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch {
      throw new Error("Cannot reach the server. Is it running?");
    }

    let data = null;
    try { data = await res.json(); } catch { /* empty body */ }

    if (!res.ok) {
      const err = new Error((data && data.detail) || `Request failed (${res.status})`);
      err.status = res.status;
      throw err;
    }
    return data;
  },

  get(path, opts) { return API.request("GET", path, opts); },
  post(path, opts) { return API.request("POST", path, opts); },
  patch(path, opts) { return API.request("PATCH", path, opts); },
  put(path, opts) { return API.request("PUT", path, opts); },
  del(path, opts) { return API.request("DELETE", path, opts); },
};

// ---- small formatting helpers ----

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatMoney(n) {
  return "₹" + Number(n || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function formatQty(n) {
  return Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 3 });
}

function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

// Manoj's student menu helper: append only non-empty query values safely.
API.withQuery = function (path, values) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values || {})) {
    if (value !== undefined && value !== null && String(value) !== "") params.set(key, value);
  }
  const query = params.toString();
  return query ? `${path}?${query}` : path;
};
