/* App Fee Waiver – small progressive enhancements (the site also works without JavaScript). */
(function () {
  "use strict";

  // Mobile menu
  var menuButton = document.querySelector("[data-menu-button]");
  var menu = document.getElementById("mobile-menu");
  if (menuButton && menu) {
    var setOpen = function (open) {
      menu.hidden = !open;
      menuButton.setAttribute("aria-expanded", open ? "true" : "false");
      menuButton.setAttribute("aria-label", open ? "Close menu" : "Open menu");
      menuButton.querySelector("[data-menu-open]").hidden = open;
      menuButton.querySelector("[data-menu-close]").hidden = !open;
    };
    menuButton.addEventListener("click", function () { setOpen(menu.hidden); });
    menu.addEventListener("click", function (e) { if (e.target.closest("a")) setOpen(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") setOpen(false); });
  }

  // Grey placeholder text for unselected dropdowns
  document.querySelectorAll("select.input").forEach(function (select) {
    var update = function () { select.classList.toggle("is-empty", !select.value); };
    select.addEventListener("change", update);
    update();
  });

  // Moving testimonies: pause while a finger is on them (phones have no hover)
  document.querySelectorAll("[data-marquee]").forEach(function (m) {
    m.addEventListener("touchstart", function () { m.classList.add("is-paused"); }, { passive: true });
    m.addEventListener("touchend", function () { setTimeout(function () { m.classList.remove("is-paused"); }, 1500); });
  });

  // Testimony photos that fail to load fall back to initials
  document.querySelectorAll("img[data-avatar-fallback]").forEach(function (img) {
    img.addEventListener("error", function () {
      var span = document.createElement("span");
      span.className = "h-[52px] w-[52px] rounded-full bg-navy-900 text-white font-semibold flex items-center justify-center shrink-0";
      span.textContent = img.getAttribute("data-avatar-fallback");
      span.setAttribute("aria-hidden", "true");
      img.replaceWith(span);
    });
  });

  // "Join the Community" pop-up
  var modal = document.getElementById("join");
  if (modal) {
    var opener = null;
    var openModal = function (trigger) {
      opener = trigger || null;
      modal.classList.add("is-open");
      document.body.classList.add("modal-open");
      var first = modal.querySelector("[data-join-body]:not([hidden]) input.input, [data-join-success]:not([hidden])");
      if (first) setTimeout(function () { first.focus(); }, 30);
    };
    var closeModal = function () {
      modal.classList.remove("is-open");
      document.body.classList.remove("modal-open");
      if (location.hash === "#join" || /[?&]joined=1/.test(location.search)) {
        history.replaceState(null, "", location.pathname);
      }
      if (opener) opener.focus();
    };
    document.addEventListener("click", function (e) {
      var link = e.target.closest("[data-join-open]");
      if (link) {
        e.preventDefault();
        openModal(link);
        return;
      }
      if (e.target.closest("[data-join-close]")) {
        e.preventDefault();
        closeModal();
      }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && modal.classList.contains("is-open")) closeModal();
    });
    if (location.hash === "#join" || modal.classList.contains("is-open")) openModal();
  }

  // Registration form: submit without leaving the page
  var form = document.querySelector("[data-join-form]");
  if (!form) return;
  var button = form.querySelector("[data-join-button]");
  var label = button.querySelector("[data-label]");
  var formError = form.querySelector("[data-form-error]");

  function clearErrors() {
    form.querySelectorAll("[data-field]").forEach(function (field) {
      field.classList.remove("has-error");
      var p = field.querySelector("[data-error]");
      if (p) p.textContent = "";
    });
    formError.textContent = "";
  }

  function showErrors(errors) {
    var first = null;
    Object.keys(errors).forEach(function (name) {
      var field = form.querySelector('[data-field="' + name + '"]');
      if (!field) { formError.textContent = errors[name][0]; return; }
      field.classList.add("has-error");
      field.querySelector("[data-error]").textContent = errors[name][0];
      if (!first) first = field.querySelector("input, select");
    });
    if (first) first.focus();
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    clearErrors();
    // Quick client-side checks (the server validates again)
    var missing = {};
    ["full_name", "email", "country", "current_level"].forEach(function (name) {
      var el = form.elements[name];
      if (!el.value.trim()) missing[name] = ["This field is required."];
    });
    var email = form.elements.email;
    if (email.value && !email.checkValidity()) missing.email = ["Enter a valid email address."];
    if (Object.keys(missing).length) { showErrors(missing); return; }

    button.disabled = true;
    label.textContent = "Sending…";
    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { "x-requested-with": "fetch" },
      credentials: "same-origin",
    })
      .then(function (response) {
        return response.text().then(function (text) {
          var data = {};
          try { data = JSON.parse(text); } catch (e) { data = { ok: false, message: text }; }
          return { status: response.status, data: data };
        });
      })
      .then(function (result) {
        if (result.data.ok) {
          document.querySelector("[data-join-body]").hidden = true;
          var success = document.querySelector("[data-join-success]");
          success.hidden = false;
          success.focus();
          return;
        }
        if (result.data.errors) showErrors(result.data.errors);
        else formError.textContent = result.data.message || "Something went wrong. Please try again.";
      })
      .catch(function () {
        formError.textContent = "We couldn't reach the server. Check your connection and try again.";
      })
      .finally(function () {
        button.disabled = false;
        label.textContent = "Join the Community";
      });
  });
})();
