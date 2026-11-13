// Shared helpers for every page: backend calls, login session, formatting.
// (Basic version by Mann; Manoj can extend it.)
//
// After login, login.js saves:
//   sessionStorage.ce_token  the signed token from /api/auth/login
//   sessionStorage.ce_user   JSON {user_id, name, email, role, ...}
// Every request then sends "Authorization: Bearer <token>".

const Auth = {
  token() {
    try { return sessionStorage.getItem("ce_token"); } catch { return null; }
  },

  user() {
    try { return JSON.parse(sessionStorage.getItem("ce_user") || "null"); } catch { return null; }
  },

  save(token, user) {
    try {
      sessionStorage.setItem("ce_token", token);
      sessionStorage.setItem("ce_user", JSON.stringify(user));
    } catch { /* storage blocked: login lasts until the page closes */ }
  },

  clear() {
    try {
      sessionStorage.removeItem("ce_token");
      sessionStorage.removeItem("ce_user");
    } catch { /* ignore */ }
  },

  logout(message) {
    Auth.clear();
    const q = message ? `?msg=${encodeURIComponent(message)}` : "";
    window.location.href = `/login.html${q}`;
  },

  homeFor(user) {
    return user && user.role === "student" ? "/student.html" : "/staff.html";
  },

  // Call at the top of a page: sends the user to login (or to their own
  // page) if they are not logged in with one of the allowed roles.
  requireRole(...roles) {
    const user = Auth.user();
    if (!user || !Auth.token()) { Auth.logout(); return null; }
    if (!roles.includes(user.role)) { window.location.href = Auth.homeFor(user); return null; }
    return user;
  },
};

const API = {
  // Returns parsed JSON, or throws an Error whose message is the backend's
  // "detail" text (e.g. "Not enough Samosa (only 2 left)").
  async request(method, path, { body } = {}) {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const token = Auth.token();
    if (token) headers["Authorization"] = `Bearer ${token}`;

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
      const message = (data && data.detail) || `Request failed (${res.status})`;
      // a logged-in page whose token stopped working -> back to login
      if (res.status === 401 && token && !path.startsWith("/api/auth/login")) {
        Auth.logout(message);
      }
      const err = new Error(message);
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

  // build "/path?a=1&b=2", skipping empty values
  withQuery(path, values) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(values || {})) {
      if (value !== undefined && value !== null && String(value) !== "") params.set(key, value);
    }
    const query = params.toString();
    return query ? `${path}?${query}` : path;
  },
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

function formatTime(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}
