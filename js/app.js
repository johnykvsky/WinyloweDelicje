(function () {
  "use strict";

  const MONTH_NAMES = {
    "1": "Styczeń",
    "2": "Luty",
    "3": "Marzec",
    "4": "Kwiecień",
    "5": "Maj",
    "6": "Czerwiec",
    "7": "Lipiec",
    "8": "Sierpień",
    "9": "Wrzesień",
    "10": "Październik",
    "11": "Listopad",
    "12": "Grudzień",
  };

  const THEMATIC_TITLES = new Set([
    "Uroki PRL",
    "Legendy światowego jazzu",
    "Jubileusz 100",
  ]);

  const VINYL_SVG = `
    <svg class="cover-fallback" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="2.5"/>
      <circle cx="32" cy="32" r="22" stroke="currentColor" stroke-width="1" stroke-dasharray="4 3" opacity="0.6"/>
      <circle cx="32" cy="32" r="16" stroke="currentColor" stroke-width="1" stroke-dasharray="3 3" opacity="0.6"/>
      <circle cx="32" cy="32" r="9" stroke="currentColor" stroke-width="2"/>
      <circle cx="32" cy="32" r="3" fill="currentColor"/>
    </svg>
  `;

  // Normalize string for diacritic-insensitive and case-insensitive comparison
  function normalizeStr(str) {
    if (!str) return "";
    const plMap = {
      ą: "a", ć: "c", ę: "e", ł: "l", ń: "n", ó: "o", ś: "s", ź: "z", ż: "z",
      Ą: "a", Ć: "c", Ę: "e", Ł: "l", Ń: "n", Ó: "o", Ś: "s", Ź: "z", Ż: "z",
    };
    return str
      .replace(/[’‘]/g, "'")
      .replace(/[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]/g, (ch) => plMap[ch] || ch)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Highlight matching substring (supports Polish diacritics in original text)
  function highlightMatch(text, query) {
    if (!text) return "";
    if (!query || !query.trim()) return escapeHtml(text);

    const normText = normalizeStr(text);
    const normQuery = normalizeStr(query.trim());
    if (!normQuery) return escapeHtml(text);

    const idx = normText.indexOf(normQuery);
    if (idx === -1) return escapeHtml(text);

    const before = text.slice(0, idx);
    const match = text.slice(idx, idx + normQuery.length);
    const after = text.slice(idx + normQuery.length);
    return `${escapeHtml(before)}<mark class="hl">${escapeHtml(match)}</mark>${escapeHtml(after)}`;
  }

  // Theme management
  function getSavedTheme() {
    try {
      const fromStorage = localStorage.getItem("wd_theme");
      if (fromStorage === "light" || fromStorage === "dark") return fromStorage;
    } catch (_) {}
    return "dark";
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem("wd_theme", theme);
    } catch (_) {}
  }

  const initialTheme = getSavedTheme();
  document.documentElement.setAttribute("data-theme", initialTheme);

  function initTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme") || getSavedTheme();
    document.documentElement.setAttribute("data-theme", currentTheme);
    updateThemeBtn(currentTheme);

    const btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        saveTheme(next);
        updateThemeBtn(next);
      });
    }
  }

  function updateThemeBtn(theme) {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.textContent = theme === "dark" ? "☀️ Jasny motyw" : "🌙 Ciemny motyw";
  }

  document.addEventListener("DOMContentLoaded", () => {
    initTheme();

    const listEl = document.getElementById("meetings-list");
    if (!listEl) return; // On Statystyki page

    const data = window.WINYLOWE_DATA || [];

    const selectMeetingYear = document.getElementById("filter-meeting-year");
    const inputArtist = document.getElementById("filter-artist");
    const inputAlbum = document.getElementById("filter-album");
    const selectAlbumYear = document.getElementById("filter-album-year");
    const selectGenre = document.getElementById("filter-genre");
    const checkboxSpecial = document.getElementById("filter-show-special");
    const btnReset = document.getElementById("btn-reset-filters");
    const resultsCountEl = document.getElementById("results-count");
    const activeTagsEl = document.getElementById("active-tags");

    // Populate Meeting Year options (latest to oldest)
    const meetingYears = Array.from(
      new Set(data.map((m) => m.year).filter(Boolean))
    ).sort((a, b) => Number(b) - Number(a));

    meetingYears.forEach((yr) => {
      const opt = document.createElement("option");
      opt.value = yr;
      opt.textContent = yr;
      selectMeetingYear.appendChild(opt);
    });

    // Populate Album Release Year options
    const albumYearsSet = new Set();
    const genresSet = new Set();
    data.forEach((m) => {
      (m.albums || []).forEach((a) => {
        if (a.releaseYear) albumYearsSet.add(a.releaseYear);
        if (a.genre) genresSet.add(a.genre);
      });
    });
    const albumYears = Array.from(albumYearsSet).sort((a, b) => Number(a) - Number(b));

    albumYears.forEach((yr) => {
      const opt = document.createElement("option");
      opt.value = yr;
      opt.textContent = yr;
      selectAlbumYear.appendChild(opt);
    });

    const genres = Array.from(genresSet).sort((a, b) => a.localeCompare(b, "pl"));
    if (selectGenre) {
      genres.forEach((g) => {
        const opt = document.createElement("option");
        opt.value = g;
        opt.textContent = g;
        selectGenre.appendChild(opt);
      });
    }

    function getFilterState() {
      return {
        meetingYear: selectMeetingYear.value.trim(),
        artist: inputArtist.value.trim(),
        album: inputAlbum.value.trim(),
        albumYear: selectAlbumYear.value.trim(),
        genre: selectGenre ? selectGenre.value.trim() : "",
        showSpecial: checkboxSpecial.checked,
      };
    }

    function doesAlbumMatch(alb, state) {
      const hasArtistFilter = Boolean(state.artist);
      const hasAlbumFilter = Boolean(state.album);
      const hasAlbumYearFilter = Boolean(state.albumYear);
      const hasGenreFilter = Boolean(state.genre);

      if (!hasArtistFilter && !hasAlbumFilter && !hasAlbumYearFilter && !hasGenreFilter) {
        return false;
      }

      if (hasArtistFilter) {
        const q = normalizeStr(state.artist);
        const normArtist = normalizeStr(alb.artist);
        // For thematic entries (e.g. "Uroki PRL" where artists are in album field), also check album field
        const isThematic = THEMATIC_TITLES.has(alb.artist);
        const normThematicArtists = isThematic ? normalizeStr(alb.album) : "";
        if (!normArtist.includes(q) && !normThematicArtists.includes(q)) {
          return false;
        }
      }

      if (hasAlbumFilter) {
        const q = normalizeStr(state.album);
        const normAlbum = normalizeStr(alb.album);
        // Special case for row 34 col 3 where artist+album are combined in artist column
        const normCombined = !alb.album ? normalizeStr(alb.artist) : "";
        if (!normAlbum.includes(q) && !normCombined.includes(q)) {
          return false;
        }
      }

      if (hasAlbumYearFilter) {
        if (alb.releaseYear !== state.albumYear) {
          return false;
        }
      }

      if (hasGenreFilter) {
        if (alb.genre !== state.genre) {
          return false;
        }
      }

      return true;
    }

    function renderActiveTags(state) {
      activeTagsEl.innerHTML = "";
      const tags = [];

      if (state.meetingYear) {
        tags.push({
          label: `Rok spotkania: ${state.meetingYear}`,
          clear: () => { selectMeetingYear.value = ""; render(); },
        });
      }
      if (state.artist) {
        tags.push({
          label: `Wykonawca: "${state.artist}"`,
          clear: () => { inputArtist.value = ""; render(); },
        });
      }
      if (state.album) {
        tags.push({
          label: `Album: "${state.album}"`,
          clear: () => { inputAlbum.value = ""; render(); },
        });
      }
      if (state.albumYear) {
        tags.push({
          label: `Rok wydania: ${state.albumYear}`,
          clear: () => { selectAlbumYear.value = ""; render(); },
        });
      }
      if (state.genre) {
        tags.push({
          label: `Gatunek: ${state.genre}`,
          clear: () => { if (selectGenre) selectGenre.value = ""; render(); },
        });
      }

      tags.forEach((t) => {
        const span = document.createElement("span");
        span.className = "filter-tag";
        span.innerHTML = `${escapeHtml(t.label)} <button type="button" title="Usuń filtr" aria-label="Usuń filtr">&times;</button>`;
        span.querySelector("button").addEventListener("click", t.clear);
        activeTagsEl.appendChild(span);
      });

      // Highlight active inputs
      selectMeetingYear.classList.toggle("is-active", Boolean(state.meetingYear));
      inputArtist.classList.toggle("is-active", Boolean(state.artist));
      inputAlbum.classList.toggle("is-active", Boolean(state.album));
      selectAlbumYear.classList.toggle("is-active", Boolean(state.albumYear));
      if (selectGenre) {
        selectGenre.classList.toggle("is-active", Boolean(state.genre));
      }

      btnReset.disabled = tags.length === 0;
    }

    function render() {
      const state = getFilterState();
      renderActiveTags(state);

      const hasAlbumLevelFilter = Boolean(state.artist || state.album || state.albumYear || state.genre);

      const filtered = data
        .filter((m) => {
          if (m.isSpecial && !state.showSpecial) {
            return false;
          }
          if (state.meetingYear && m.year !== state.meetingYear) {
            return false;
          }
          if (hasAlbumLevelFilter) {
            if (m.isSpecial || !m.albums || m.albums.length === 0) {
              return false;
            }
            // Check if at least one album in this meeting matches all active album-level filters
            return m.albums.some((alb) => doesAlbumMatch(alb, state));
          }
          return true;
        })
        .sort((a, b) => b.id - a.id);

      // Count active meetings vs special entries
      const regularCount = filtered.filter((m) => !m.isSpecial).length;
      const matchedAlbumsCount = hasAlbumLevelFilter
        ? filtered.reduce(
            (acc, m) => acc + (m.albums || []).filter((a) => doesAlbumMatch(a, state)).length,
            0
          )
        : 0;

      if (hasAlbumLevelFilter) {
        resultsCountEl.innerHTML = `Znaleziono <strong>${regularCount}</strong> spotkań (pasujących albumów: <strong>${matchedAlbumsCount}</strong>)`;
      } else {
        resultsCountEl.innerHTML = `Wyświetlono <strong>${regularCount}</strong> spotkań`;
      }

      if (filtered.length === 0) {
        listEl.innerHTML = `
          <div class="empty-state">
            <h3>Brak spotkań spełniających kryteria</h3>
            <p>Spróbuj zmienić wpisane frazy lub wyczyścić filtry.</p>
          </div>
        `;
        return;
      }

      const htmlParts = filtered.map((m) => {
        const monthName = MONTH_NAMES[m.month] || "";
        const dateDisplay =
          monthName && m.year
            ? `${monthName} <button type="button" class="meeting-year-btn" data-year="${escapeHtml(m.year)}" title="Filtruj spotkania z roku ${escapeHtml(m.year)}">${escapeHtml(m.year)}</button>`
            : m.year
            ? `<button type="button" class="meeting-year-btn" data-year="${escapeHtml(m.year)}">${escapeHtml(m.year)}</button>`
            : "—";

        const badges = [];
        if (m.number) {
          badges.push(`<span class="badge" title="Numer kolejny wiersza">#${escapeHtml(m.number)}</span>`);
        }
        if (m.spotkanie && !m.isSpecial) {
          badges.push(`<span class="badge badge-spotkanie" title="Numer spotkania">Spotkanie ${escapeHtml(m.spotkanie)}</span>`);
        }

        if (m.isSpecial) {
          const label =
            m.spotkanie.toLowerCase() === "pandemia"
              ? "Przerwa pandemiczna (COVID-19)"
              : m.spotkanie.toLowerCase() === "przerwa"
              ? "Przerwa w spotkaniach"
              : "Spotkanie odwołane";

          return `
            <article class="meeting-card is-special">
              <div class="meeting-meta">
                <div class="meeting-date">${dateDisplay}</div>
              </div>
              <div class="special-banner">
                <span>⚠️ ${escapeHtml(label)}</span>
              </div>
            </article>
          `;
        }

        const albumsHtml = (m.albums || [])
          .map((alb) => {
            const isMatched = hasAlbumLevelFilter && doesAlbumMatch(alb, state);
            const cardClasses = ["album-card"];
            if (hasAlbumLevelFilter) {
              cardClasses.push(isMatched ? "is-match" : "is-dimmed");
            }

            const isThematic = THEMATIC_TITLES.has(alb.artist);
            const coverHtml = alb.cover
              ? `<img src="${escapeHtml(alb.cover)}" alt="Okładka: ${escapeHtml(alb.artist)} - ${escapeHtml(alb.album)}" loading="lazy" />`
              : VINYL_SVG;

            const yearPillClasses = ["album-year-pill"];
            if (state.albumYear && alb.releaseYear === state.albumYear) {
              yearPillClasses.push("is-matched-year");
            }

            const yearBadge = alb.releaseYear
              ? `<button type="button" class="${yearPillClasses.join(" ")}" data-release-year="${escapeHtml(alb.releaseYear)}" title="Pokaż wszystkie spotkania z albumami z roku ${escapeHtml(alb.releaseYear)}">${escapeHtml(alb.releaseYear)}</button>`
              : "";

            const genreTagClasses = ["album-genre-tag"];
            if (state.genre && alb.genre === state.genre) {
              genreTagClasses.push("is-matched-genre");
            }
            let durationBadgeHtml = "";
            if (alb.durationSeconds && alb.durationSeconds > 0) {
              const mins = Math.floor(alb.durationSeconds / 60);
              const secs = String(alb.durationSeconds % 60).padStart(2, "0");
              durationBadgeHtml = `<span class="album-duration" title="Czas trwania albumu">⏱ ${mins}:${secs}</span>`;
            }
            const genreHtml =
              alb.genre || durationBadgeHtml
                ? `<div class="album-genre-row">${alb.genre ? `<button type="button" class="${genreTagClasses.join(" ")}" data-genre="${escapeHtml(alb.genre)}" title="Filtruj według gatunku: ${escapeHtml(alb.genre)}">${escapeHtml(alb.genre)}</button>` : ""}${durationBadgeHtml}</div>`
                : "";

            let titleHtml = "";
            let artistHtml = "";

            if (isThematic) {
              titleHtml = `<div class="album-artist is-thematic">${highlightMatch(alb.artist, state.artist)}</div>`;
              if (alb.album) {
                artistHtml = `<div class="album-title">${highlightMatch(alb.album, state.artist || state.album)}</div>`;
              }
            } else if (!alb.album) {
              // Artist-only entry (e.g. The Beatles, Elvis Presley) or combined string
              titleHtml = `<div class="album-title"><button type="button" class="album-artist-btn" data-artist="${escapeHtml(alb.artist)}" title="Filtruj wykonawcę: ${escapeHtml(alb.artist)}">${highlightMatch(alb.artist, state.artist || state.album)}</button></div>`;
              artistHtml = `<div class="album-artist">Wykonawca / temat spotkania</div>`;
            } else {
              titleHtml = `<div class="album-title">${highlightMatch(alb.album, state.album)}</div>`;
              artistHtml = `<div class="album-artist"><button type="button" class="album-artist-btn" data-artist="${escapeHtml(alb.artist)}" title="Filtruj wykonawcę: ${escapeHtml(alb.artist)}">${highlightMatch(alb.artist, state.artist)}</button></div>`;
            }

            return `
              <div class="${cardClasses.join(" ")}">
                <div class="cover-wrap">
                  ${coverHtml}
                </div>
                <div class="album-info">
                  <div class="album-slot-row">
                    <span class="album-slot-label">${isThematic ? "Temat specjalny" : `Płyta ${alb.slot}`}</span>
                    ${yearBadge}
                  </div>
                  ${titleHtml}
                  ${artistHtml}
                  ${genreHtml}
                </div>
              </div>
            `;
          })
          .join("");

        return `
          <article class="meeting-card">
            <div class="meeting-meta">
              <div class="meeting-date">${dateDisplay}</div>
              <div class="meeting-badges">${badges.join("")}</div>
            </div>
            <div class="meeting-albums">
              ${albumsHtml}
            </div>
          </article>
        `;
      });

      listEl.innerHTML = htmlParts.join("");
    }

    // Event listeners
    selectMeetingYear.addEventListener("change", render);
    inputArtist.addEventListener("input", render);
    inputAlbum.addEventListener("input", render);
    selectAlbumYear.addEventListener("change", render);
    if (selectGenre) {
      selectGenre.addEventListener("change", render);
    }
    checkboxSpecial.addEventListener("change", render);

    btnReset.addEventListener("click", () => {
      selectMeetingYear.value = "";
      inputArtist.value = "";
      inputAlbum.value = "";
      selectAlbumYear.value = "";
      if (selectGenre) selectGenre.value = "";
      render();
    });

    // Delegate clicks on year pills, artist names, and genre tags inside meeting cards
    listEl.addEventListener("click", (e) => {
      const relYearBtn = e.target.closest("[data-release-year]");
      if (relYearBtn) {
        const yr = relYearBtn.getAttribute("data-release-year");
        selectAlbumYear.value = selectAlbumYear.value === yr ? "" : yr;
        render();
        return;
      }

      const artistBtn = e.target.closest("[data-artist]");
      if (artistBtn) {
        const art = artistBtn.getAttribute("data-artist");
        inputArtist.value = normalizeStr(inputArtist.value.trim()) === normalizeStr(art) ? "" : art;
        render();
        return;
      }

      const genreBtn = e.target.closest("[data-genre]");
      if (genreBtn && selectGenre) {
        const g = genreBtn.getAttribute("data-genre");
        selectGenre.value = selectGenre.value === g ? "" : g;
        render();
        return;
      }

      const meetYearBtn = e.target.closest("[data-year]");
      if (meetYearBtn) {
        const yr = meetYearBtn.getAttribute("data-year");
        selectMeetingYear.value = selectMeetingYear.value === yr ? "" : yr;
        render();
      }
    });

    // Main view tab switching (Spotkania <-> Statystyki)
    const viewMeetings = document.getElementById("view-meetings");
    const viewStats = document.getElementById("view-stats");
    const mainNavLinks = document.querySelectorAll(".nav-link[data-main-tab]");

    function switchMainTab(tabName) {
      const isStats = tabName === "stats";
      if (viewMeetings) viewMeetings.hidden = isStats;
      if (viewStats) viewStats.hidden = !isStats;

      mainNavLinks.forEach((link) => {
        const active = link.getAttribute("data-main-tab") === (isStats ? "stats" : "meetings");
        link.classList.toggle("active", active);
        if (active) {
          link.setAttribute("aria-current", "page");
        } else {
          link.removeAttribute("aria-current");
        }
      });

      document.title = isStats
        ? "Winylowe Delicje — Statystyki"
        : "Winylowe Delicje — Spotkania";
    }

    document.querySelectorAll("[data-main-tab]").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        const targetTab = el.getAttribute("data-main-tab");
        switchMainTab(targetTab);
        const newHash = targetTab === "stats" ? "#statystyki" : "#spotkania";
        if (window.location.hash !== newHash) {
          try {
            history.replaceState(null, "", newHash);
          } catch (_) {}
        }
      });
    });

    // Delegate clicks on filter links inside Statystyki (e.g. href="index.html?artist=...")
    const statsRoot = document.getElementById("stats-root");
    if (statsRoot) {
      statsRoot.addEventListener("click", (e) => {
        const link = e.target.closest('a[href^="index.html?"]');
        if (!link) return;
        e.preventDefault();

        const queryStr = link.getAttribute("href").split("?")[1] || "";
        const qParams = new URLSearchParams(queryStr);

        selectMeetingYear.value = qParams.get("meetingYear") || "";
        inputArtist.value = qParams.get("artist") || "";
        inputAlbum.value = qParams.get("album") || "";
        selectAlbumYear.value = qParams.get("albumYear") || "";
        if (selectGenre) selectGenre.value = qParams.get("genre") || "";

        render();
        switchMainTab("meetings");
        try {
          history.replaceState(null, "", "#spotkania");
        } catch (_) {}
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    // Apply URL query parameters or hash if present on initial load
    const params = new URLSearchParams(window.location.search);
    if (params.get("meetingYear")) selectMeetingYear.value = params.get("meetingYear");
    if (params.get("artist")) inputArtist.value = params.get("artist");
    if (params.get("album")) inputAlbum.value = params.get("album");
    if (params.get("albumYear")) selectAlbumYear.value = params.get("albumYear");
    if (params.get("genre") && selectGenre) selectGenre.value = params.get("genre");

    if (window.location.hash === "#statystyki") {
      switchMainTab("stats");
    }

    // Initial render
    render();
  });
})();
