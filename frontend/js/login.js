// Login and sign-up page. Owner: Mann.

const $ = (id) => document.getElementById(id);

function showMessage(text, type = "error") {
  const box = $("auth-message");
  box.textContent = text;
  box.className = `alert ${type}`;
  box.hidden = !text;
}

function showTab(name) {
  document.querySelectorAll("[data-auth-tab]").forEach((t) => {
    const active = t.dataset.authTab === name;
    t.classList.toggle("active", active);
    t.setAttribute("aria-selected", active);
  });
  $("login-form").hidden = name !== "login";
  $("signup-form").hidden = name !== "signup";
  showMessage("");
}

function goHome(user) {
  window.location.href = Auth.homeFor(user);
}

async function submit(form, path, body) {
  const btn = form.querySelector("button[type=submit]");
  btn.disabled = true;
  showMessage("");
  try {
    const result = await API.post(path, { body });
    Auth.save(result.token, result.user);
    goHome(result.user);
  } catch (err) {
    showMessage(err.message);
    btn.disabled = false;
  }
}

$("login-form").addEventListener("submit", (e) => {
  e.preventDefault();
  submit(e.target, "/api/auth/login", {
    email: $("login-email").value.trim(),
    password: $("login-password").value,
  });
});

$("signup-form").addEventListener("submit", (e) => {
  e.preventDefault();
  submit(e.target, "/api/auth/signup", {
    name: $("signup-name").value.trim(),
    email: $("signup-email").value.trim(),
    phone: $("signup-phone").value.trim(),
    password: $("signup-password").value,
  });
});

document.querySelectorAll("[data-auth-tab]").forEach((t) =>
  t.addEventListener("click", () => showTab(t.dataset.authTab)));

// ---- start ----
const msg = new URLSearchParams(window.location.search).get("msg");
if (msg) showMessage(msg, "warn");

// already logged in? check the token still works, then skip the form
if (Auth.token() && Auth.user()) {
  API.get("/api/auth/me")
    .then((user) => { Auth.save(Auth.token(), user); goHome(user); })
    .catch(() => Auth.clear());
}
