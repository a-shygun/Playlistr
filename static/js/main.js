


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
        expandable.classList.toggle("show");
        btn.classList.toggle("toggle");

        btn.textContent = expandable.classList.contains("show")
          ? "▲ See Less"
          : "▼ See More";
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

  function renderBarChart(canvasId, dataKey, datasetKey, color='#1DB954', horizontal=false) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    fetch('/user_plot_data')
      .then(response => response.json())
      .then(data => {
        const dataset = data[dataKey][datasetKey];
        const labels = Object.keys(dataset);
        const counts = Object.values(dataset);

        const ctx = canvas.getContext('2d');
        new Chart(ctx, {
          type: 'bar',
          data: {
            labels: labels,
            datasets: [{
              label: 'Playcount',
              data: counts,
              backgroundColor: color,
              borderColor: color,
              borderWidth: 1
            }]
          },
          options: {
            indexAxis: horizontal ? 'y' : 'x', // horizontal if true
            maintainAspectRatio: false,
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } }
          }
        });
      })
      .catch(err => console.error(`Failed to load plot JSON for ${canvasId}:`, err));
  }

  // -----------------------------
  // Header AJAX buttons
  // -----------------------------
  function bindAjaxButtons() {
    const slider = document.querySelector(".header-slider");
    const newHeaderBtns = document.querySelectorAll(".header-toggle .btn");
    const main = document.getElementById("main-content")

    const paddingTop = 10 // or the top value for the slider div

    const firstBtn = newHeaderBtns[0];
    firstBtn.style.color = "var(--text-color-alt)";
    const firstIcon = firstBtn.querySelector("i");
    if (firstIcon) firstIcon.className = firstIcon.className.replace("-line", "-fill");

    slider.style.top = `${paddingTop}px`;
    

    newHeaderBtns.forEach((btn, index) => {
      btn.addEventListener("click", async e => {
        
        e.preventDefault()
        const url = btn.dataset.url;
        if (!url) return; 

        const res = await fetch(url);
        const html = await res.text();
        main.innerHTML = html;

        bindTrackToggles();
        bindSegmentedControl();
        bindRegistrationForm();
        renderBarChart('genresBarChart', 'wordcloud_genres', 'top_genres', '#1DB954');
        renderBarChart('artistsBarChart', 'wordcloud_artists', 'top_artists', '#1DB954');
        renderBarChart('playcountBarChart', 'playcount_distribution', 'top_playlists', '#1DB954');

        newHeaderBtns.forEach(b => {
          b.style.color = "";
          const icon = b.querySelector("i");
          if (icon) icon.className = icon.className.replace("-fill", "-line");
        });

        slider.style.top = `${index * (60 + 10) + paddingTop}px`; // nav item width, gap, father div padding
        btn.style.color = "var(--text-color-alt)";
        const activeIcon = btn.querySelector("i");
        activeIcon.className = activeIcon.className.replace("-line", "-fill");
      });
    });
  }

  const navHam = document.getElementById("nav-ham");
  const dropdownContent = document.querySelector(".dropdown-content");
  if (navHam && dropdownContent) {
    navHam.addEventListener("click", (e) => {
      e.stopPropagation()
      navHam.classList.toggle("toggle");
      dropdownContent.classList.toggle("show");
    });
    document.addEventListener("click", (e) => {
      if (!dropdownContent.contains(e.target) && !navHam.contains(e.target)) {
        dropdownContent.classList.remove("show");
        navHam.classList.remove("toggle");
      }
    });
  }
  


  bindTrackToggles();
  bindSegmentedControl();
  bindRegistrationForm();
  bindAjaxButtons();
});

function toggleThemeColors() {
  const root = document.documentElement;
  const btnText = document.querySelector('#theme-btn span');

  const isDark = root.classList.toggle('dark');
  btnText.textContent = isDark ? "Light" : "Dark";
}


