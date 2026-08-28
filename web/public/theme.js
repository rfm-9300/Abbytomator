/* Theme switcher and small UI behaviors — thebots.lab design system.
   Loaded synchronously in <head> so the theme applies before first paint.
   Preference persists per browser in localStorage ("light" | "dark").
   First visit follows prefers-color-scheme. */
(function () {
  const KEY = "uiTheme";
  const root = document.documentElement;

  function preferred() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function stored() {
    const value = localStorage.getItem(KEY);
    return value === "dark" || value === "light" ? value : null;
  }

  function current() {
    return root.dataset.theme === "dark" ? "dark" : "light";
  }

  function apply(theme) {
    root.dataset.theme = theme;
    const btn = document.getElementById("btn-theme");
    if (!btn) return;
    const nextLabel = theme === "dark" ? "Light theme" : "Dark theme";
    btn.title = nextLabel;
    btn.setAttribute("aria-label", nextLabel);
    btn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
  }

  apply(stored() || preferred());

  function resetFileLabel(input) {
    if (!input) return;
    const label = input.closest(".file") && input.closest(".file").querySelector("[data-file-name]");
    if (!label) return;
    label.textContent = "No file chosen";
    label.classList.remove("file__name--set");
  }

  function formatTimes() {
    document.querySelectorAll("time[data-time][datetime]").forEach((el) => {
      const raw = el.getAttribute("datetime");
      if (!raw) return;
      const date = new Date(raw);
      if (Number.isNaN(date.getTime())) return;
      const now = Date.now();
      const delta = (now - date.getTime()) / 1000;
      const sameDay = date.toDateString() === new Date().toDateString();
      if (delta < 45) {
        el.textContent = "Just now";
      } else if (sameDay) {
        el.textContent = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      } else if (delta < 86400 * 6) {
        el.textContent = date.toLocaleString([], {
          weekday: "short",
          hour: "2-digit",
          minute: "2-digit",
        });
      } else {
        el.textContent = date.toLocaleString([], {
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
        });
      }
    });
  }

  function initTabs(rootEl) {
    const tabs = Array.prototype.slice.call(rootEl.querySelectorAll("[data-tab]"));
    const panels = Array.prototype.slice.call(rootEl.querySelectorAll("[data-panel]"));
    if (!tabs.length) return;

    function select(name) {
      tabs.forEach((tab) => {
        const on = tab.getAttribute("data-tab") === name;
        tab.setAttribute("aria-selected", on ? "true" : "false");
        tab.tabIndex = on ? 0 : -1;
      });
      panels.forEach((panel) => {
        panel.hidden = panel.getAttribute("data-panel") !== name;
      });
      if (rootEl.hasAttribute("data-clear-hidden")) {
        panels.forEach((panel) => {
          if (panel.hidden) {
            panel.querySelectorAll("input, select, textarea").forEach((field) => {
              if (field.type === "file") {
                field.value = "";
                resetFileLabel(field);
              } else if (field.type === "checkbox" || field.type === "radio") {
                return;
              } else {
                field.value = "";
              }
            });
          }
        });
      }
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => select(tab.getAttribute("data-tab")));
    });

    rootEl.addEventListener("keydown", (event) => {
      if (!event.target.closest("[data-tab]")) return;
      const currentTab = event.target.closest("[data-tab]");
      const index = tabs.indexOf(currentTab);
      if (index < 0) return;
      if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        event.preventDefault();
        const next = event.key === "ArrowRight"
          ? (index + 1) % tabs.length
          : (index - 1 + tabs.length) % tabs.length;
        tabs[next].focus();
        select(tabs[next].getAttribute("data-tab"));
      }
    });

    const form = rootEl.closest("form");
    if (form && rootEl.hasAttribute("data-clear-hidden")) {
      form.addEventListener("submit", () => {
        const active = rootEl.querySelector('[aria-selected="true"]');
        const name = active ? active.getAttribute("data-tab") : "url";
        const transcript = form.querySelector("#transcript_source");
        if (name === "url") {
          const video = form.querySelector("#video");
          if (video) {
            video.value = "";
            resetFileLabel(video);
          }
        } else {
          const url = form.querySelector("#url");
          if (url) url.value = "";
          if (transcript) transcript.value = "whisper";
        }
      });
    }

    const selected = tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0];
    select(selected.getAttribute("data-tab"));
  }

  function initBusyForms() {
    document.querySelectorAll("form[data-busy]").forEach((form) => {
      form.addEventListener("submit", () => {
        const button = form.querySelector('button[type="submit"], .btn--primary');
        if (!button || button.disabled) return;
        button.disabled = true;
        button.classList.add("is-busy");
        const label = form.getAttribute("data-busy");
        if (label) button.textContent = label;
      });
    });
  }

  function initRowLinks() {
    document.querySelectorAll("tr[data-href]").forEach((row) => {
      row.addEventListener("click", (event) => {
        if (event.target.closest("a, button, input, label, form")) return;
        const href = row.getAttribute("data-href");
        if (href) window.location.href = href;
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    apply(current());
    document.getElementById("btn-theme")?.addEventListener("click", () => {
      const next = current() === "dark" ? "light" : "dark";
      localStorage.setItem(KEY, next);
      apply(next);
    });

    document.querySelectorAll(".file__input").forEach((input) => {
      const label = input.closest(".file")?.querySelector("[data-file-name]");
      if (!label) return;
      const sync = () => {
        const file = input.files && input.files[0];
        label.textContent = file ? file.name : "No file chosen";
        label.classList.toggle("file__name--set", Boolean(file));
      };
      input.addEventListener("change", sync);
      sync();
    });

    document.querySelectorAll("[data-tabs]").forEach(initTabs);
    initBusyForms();
    initRowLinks();
    initCopyButtons();
    formatTimes();
  });

  function initCopyButtons() {
    document.addEventListener("click", (event) => {
      const btn = event.target.closest("[data-copy]");
      if (!btn) return;
      const selector = btn.getAttribute("data-copy");
      const target = selector ? document.querySelector(selector) : null;
      const text = ((target && (target.value || target.textContent)) || "").trim();
      if (!text) return;
      const previous = btn.textContent;
      const done = () => {
        btn.textContent = "Copied";
        window.setTimeout(() => {
          btn.textContent = previous;
        }, 1400);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(() => {});
      }
    });
  }
})();
