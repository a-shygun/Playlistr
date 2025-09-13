document.addEventListener("DOMContentLoaded", () => {
  const main = document.getElementById("main-content");

  function bindSegmentedControl() {
    const switchToggle = document.getElementById("switch");
    const topSongs = document.querySelector(".music-cols.top-songs");
    const recentSongs = document.querySelector(".music-cols.recent-songs");
    if (!switchToggle) return;
    function updateView() {
      if (switchToggle.checked) {
        recentSongs?.classList.add("active");
        topSongs?.classList.remove("active");
      } else {
        topSongs?.classList.add("active");
        recentSongs?.classList.remove("active");
      }
    }
    updateView();
    switchToggle.addEventListener("change", updateView);
  }

  function bindTrackToggles() {
    document.querySelectorAll(".toggle-more").forEach(btn => {
      btn.addEventListener("click", () => {
        const expandable = btn.closest(".record").querySelector(".expandable");
        expandable.classList.toggle("active");
        btn.classList.toggle("active");

        btn.textContent = expandable.classList.contains("active")
          ? "▲ See Less"
          : "▼ See More";
      });
    });
  }

  function bindAjaxButtons() {
    const slider = document.querySelector(".footer-slider");
    const newFooterBtns = document.querySelectorAll(".footer-toggle .btn");
    newFooterBtns.forEach(btn => {
      btn.addEventListener("click", async () => {
        const url = btn.dataset.url;
        const res = await fetch(url);
        const html = await res.text();
        main.innerHTML = html;
        bindTrackToggles();
        bindSegmentedControl();
        bindRegistrationForm();
        newFooterBtns.forEach(b => {
          b.style.color = "";
          const icon = b.querySelector("i");
          if (icon) icon.className = icon.className.replace("-fill", "-line");
        });
        slider.style.left = `${btn.offsetLeft}px`;
        btn.style.color = "var(--greyLight-1)";
        const activeIcon = btn.querySelector("i");
        if (activeIcon) activeIcon.className = activeIcon.className.replace("-line", "-fill");
      });
    });
  }

  function bindRegistrationForm() {
    const registerBtn = document.getElementById("register-btn");
    const form = document.getElementById("register-form");
    const statusMsg = document.getElementById("register-status");

    if (!registerBtn || !form || !statusMsg) return;

    registerBtn.addEventListener("click", () => {
      form.classList.toggle("hidden");
    });

    form.addEventListener("submit", (e) => {
      e.preventDefault();

      fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: document.getElementById("spotify-email").value,
          username: document.getElementById("username").value
        })
      });

      statusMsg.textContent = "Your request has been submitted! Please wait for approval.";
      statusMsg.classList.remove("hidden");
      form.reset();
      form.classList.add("hidden");
    });
  }

  bindTrackToggles();
  bindSegmentedControl();
  bindAjaxButtons();
  bindRegistrationForm();
});