/* App Fee Waiver – small progressive enhancements. Every feature also works without JavaScript. */
(function () {
  "use strict";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function toast(message) {
    var box = document.getElementById("js-toast");
    if (!box) return;
    box.querySelector("[data-toast-text]").textContent = message;
    box.classList.remove("hidden");
    clearTimeout(box._timer);
    box._timer = setTimeout(function () { box.classList.add("hidden"); }, 3000);
  }

  // Like / save toggles: <form data-toggle> ... <button class="toggle-btn" aria-pressed>
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form.matches("form[data-toggle]")) return;
    event.preventDefault();
    var button = form.querySelector("button");
    button.disabled = true;
    fetch(form.action, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken(), "x-requested-with": "fetch" },
      credentials: "same-origin",
    })
      .then(function (response) {
        if (response.status === 401) {
          window.location.href = form.dataset.loginUrl || "/accounts/login/";
          return null;
        }
        if (!response.ok) {
          return response.text().then(function (text) { throw new Error(text || "Something went wrong."); });
        }
        return response.json();
      })
      .then(function (data) {
        if (!data) return;
        button.setAttribute("aria-pressed", data.active ? "true" : "false");
        var label = button.querySelector("[data-label]");
        if (label && button.dataset.onLabel) {
          label.textContent = data.active ? button.dataset.onLabel : button.dataset.offLabel;
        }
        var count = button.querySelector("[data-count]");
        if (count && typeof data.count === "number") count.textContent = data.count;
        if (form.dataset.toggle === "save") toast(data.active ? "Saved" : "Removed from saved");
      })
      .catch(function (error) { toast(error.message.slice(0, 140)); })
      .finally(function () { button.disabled = false; });
  });

  // Share buttons: native share sheet on phones, copy link elsewhere.
  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-share-url]");
    if (!button) return;
    event.preventDefault();
    var url = new URL(button.dataset.shareUrl, window.location.origin).href;
    var title = button.dataset.shareTitle || document.title;
    if (navigator.share) {
      navigator.share({ title: title, url: url }).catch(function () {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(function () { toast("Link copied to clipboard"); });
    } else {
      window.prompt("Copy this link:", url);
    }
  });

  // Dismissible messages
  document.addEventListener("click", function (event) {
    var close = event.target.closest("[data-dismiss]");
    if (close) close.closest("[data-dismissible]").remove();
  });
  setTimeout(function () {
    document.querySelectorAll("[data-autohide]").forEach(function (el) { el.remove(); });
  }, 7000);
})();

/* Application checklist: remembered in this browser only (no account data is stored). */
window.afwChecklist = function (keys) {
  var storageKey = "afw-checklist-v1";
  var saved = {};
  try { saved = JSON.parse(window.localStorage.getItem(storageKey) || "{}") || {}; } catch (e) { saved = {}; }
  var state = {};
  keys.forEach(function (key) { state[key] = !!saved[key]; });
  return {
    done: state,
    get count() { var self = this; return keys.filter(function (k) { return self.done[k]; }).length; },
    total: keys.length,
    toggle: function (key) {
      this.done[key] = !this.done[key];
      try { window.localStorage.setItem(storageKey, JSON.stringify(this.done)); } catch (e) { /* storage unavailable */ }
    },
  };
};
