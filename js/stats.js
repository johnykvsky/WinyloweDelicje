(function () {
  "use strict";

  const THEMATIC_TITLES = new Set([
    "Uroki PRL",
    "Legendy światowego jazzu",
    "Jubileusz 100",
  ]);

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Canonicalize album entry so punctuation differences (e.g. curly vs straight apostrophe)
  // or shortened titles (Jeff Wayne's War of the Worlds) count as the same unique album
  function extractCanonicalAlbums(albEntry) {
    const art = (albEntry.artist || "").trim();
    const alb = (albEntry.album || "").trim();
    const yr = (albEntry.releaseYear || "").trim();
    const genre = (albEntry.genre || "").trim();
    const cover = albEntry.cover || null;

    if (THEMATIC_TITLES.has(art)) {
      return [];
    }

    // Special row 34 col 3: "Bielsko biała - Dire straits, Brothers in arms"
    if (art.toLowerCase().includes("dire straits") && !alb) {
      return [
        {
          artist: "Dire Straits",
          album: "Brothers in Arms",
          releaseYear: "1985",
          genre: genre || "Rock",
          cover: cover,
        },
      ];
    }

    // Special row 34 col 1: "Za słowem biegnę do Ciebie, Memento z banalnym tryptykiem"
    if (art === "SBB" && alb.includes("Memento") && alb.includes("biegnę")) {
      return [
        {
          artist: "SBB",
          album: "Ze słowem biegnę do Ciebie",
          releaseYear: "1977",
          genre: genre || "Rock progresywny",
          cover: cover,
        },
        {
          artist: "SBB",
          album: "Memento z banalnym tryptykiem",
          releaseYear: "1981",
          genre: genre || "Rock progresywny",
          cover: null,
        },
      ];
    }

    // Skip artist-only thematic entries without a specific album
    if (!alb) {
      return [];
    }

    let cArtist = art;
    if (cArtist === "Czesław Niemen oraz Akwarele") {
      cArtist = "Czesław Niemen";
    }

    let cAlbum = alb.replace(/’/g, "'");
    if (cArtist === "Jeff Wayne" && cAlbum.includes("War of the Worlds")) {
      cAlbum = "Jeff Wayne’s Musical Version of The War of the Worlds";
    }
    if (cArtist === "Steven Wilson" && cAlbum.toLowerCase().includes("raven that refused to sing")) {
      cAlbum = "The Raven That Refused to Sing (and Other Stories)";
    }

    return [
      {
        artist: cArtist,
        album: cAlbum,
        releaseYear: yr,
        genre: genre || "Inne",
        cover: cover,
      },
    ];
  }

  function extractCanonicalArtistPlays(albEntry) {
    const art = (albEntry.artist || "").trim();
    const alb = (albEntry.album || "").trim();
    if (!art || THEMATIC_TITLES.has(art)) {
      return [];
    }
    if (art.toLowerCase().includes("dire straits") && !alb) {
      return ["Dire Straits"];
    }
    if (art === "SBB" && alb.includes("Memento") && alb.includes("biegnę")) {
      return ["SBB", "SBB"];
    }
    if (art === "Czesław Niemen oraz Akwarele") {
      return ["Czesław Niemen"];
    }
    if (art === "Beth Hart & Joe Bonamassa") {
      return ["Beth Hart & Joe Bonamassa"];
    }
    return [art];
  }

  document.addEventListener("DOMContentLoaded", () => {
    const rootEl = document.getElementById("stats-root");
    if (!rootEl) return;

    const data = window.WINYLOWE_DATA || [];
    const regularMeetings = data.filter((m) => !m.isSpecial);

    // 1. Collect unique albums & play counts
    const uniqueAlbumsMap = new Map(); // key: lower(artist||album)
    const artistStatsMap = new Map(); // key: artist name -> { artist, plays, uniqueAlbums: Set }

    regularMeetings.forEach((m) => {
      (m.albums || []).forEach((albEntry) => {
        // Artist play counts
        const playedArtists = extractCanonicalArtistPlays(albEntry);
        playedArtists.forEach((artName) => {
          if (!artistStatsMap.has(artName)) {
            artistStatsMap.set(artName, {
              artist: artName,
              plays: 0,
              uniqueAlbums: new Set(),
            });
          }
          artistStatsMap.get(artName).plays += 1;
        });

        // Album stats
        const canonicalList = extractCanonicalAlbums(albEntry);
        canonicalList.forEach((ca) => {
          const key = `${ca.artist.toLowerCase()}||${ca.album.toLowerCase()}`;
          if (!uniqueAlbumsMap.has(key)) {
            uniqueAlbumsMap.set(key, {
              artist: ca.artist,
              album: ca.album,
              releaseYear: ca.releaseYear,
              genre: ca.genre,
              cover: ca.cover,
              count: 0,
              meetings: [],
            });
          }
          const rec = uniqueAlbumsMap.get(key);
          rec.count += 1;
          if (!rec.cover && ca.cover) rec.cover = ca.cover;
          if (!rec.releaseYear && ca.releaseYear) rec.releaseYear = ca.releaseYear;
          rec.meetings.push(`${m.month ? m.month.padStart(2, "0") + "." : ""}${m.year}`);

          if (artistStatsMap.has(ca.artist)) {
            artistStatsMap.get(ca.artist).uniqueAlbums.add(ca.album.toLowerCase());
          }
        });
      });
    });

    const uniqueAlbums = Array.from(uniqueAlbumsMap.values());

    // --- STAT 1: Decades (Unique albums per decade) ---
    const decadesMap = new Map();
    uniqueAlbums.forEach((a) => {
      const yrNum = parseInt(a.releaseYear, 10);
      if (!isNaN(yrNum) && yrNum > 1900) {
        const dec = Math.floor(yrNum / 10) * 10;
        decadesMap.set(dec, (decadesMap.get(dec) || 0) + 1);
      }
    });
    const decadesList = Array.from(decadesMap.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([dec, count]) => ({
        decade: `${dec}s`,
        labelPl: dec >= 2000 ? `Lata ${dec}–${dec + 9}` : `Lata ${String(dec).slice(2)}. (${dec}s)`,
        count,
      }));
    const maxDecadeCount = Math.max(1, ...decadesList.map((d) => d.count));

    // --- STAT 2: Release Years (Unique albums per year) ---
    const yearsMap = new Map();
    uniqueAlbums.forEach((a) => {
      if (a.releaseYear) {
        yearsMap.set(a.releaseYear, (yearsMap.get(a.releaseYear) || 0) + 1);
      }
    });
    const yearsListChrono = Array.from(yearsMap.entries())
      .sort((a, b) => Number(a[0]) - Number(b[0]))
      .map(([year, count]) => ({ year, count }));
    const yearsListByCount = [...yearsListChrono].sort(
      (a, b) => b.count - a.count || Number(a.year) - Number(b.year)
    );
    const maxYearCount = Math.max(1, ...yearsListChrono.map((y) => y.count));

    // --- STAT 3: Most Played Artists (plays > 1, descending) ---
    const mostPlayedArtists = Array.from(artistStatsMap.values())
      .filter((a) => a.plays > 1)
      .sort((a, b) => b.plays - a.plays || a.artist.localeCompare(b.artist, "pl"));
    const maxArtistPlays = Math.max(1, ...mostPlayedArtists.map((a) => a.plays));

    // --- STAT 4: Most Replayed Albums (count > 1, descending) ---
    const replayedAlbums = uniqueAlbums
      .filter((a) => a.count > 1)
      .sort(
        (a, b) =>
          b.count - a.count ||
          a.artist.localeCompare(b.artist, "pl") ||
          a.album.localeCompare(b.album, "pl")
      );

    // --- STAT 5: Music Genre Stats (Unique albums per genre) ---
    const genreMap = new Map();
    uniqueAlbums.forEach((a) => {
      const g = a.genre || "Inne";
      genreMap.set(g, (genreMap.get(g) || 0) + 1);
    });
    const genreList = Array.from(genreMap.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "pl"))
      .map(([genre, count]) => ({
        genre,
        count,
        pct: ((count / uniqueAlbums.length) * 100).toFixed(1),
      }));
    const maxGenreCount = Math.max(1, ...genreList.map((g) => g.count));

    // Render KPI Summary + Tabs + Sections
    const totalPlays = uniqueAlbums.reduce((acc, a) => acc + a.count, 0);
    const totalSeconds = regularMeetings.reduce(
      (acc, m) =>
        acc + (m.albums || []).reduce((s, a) => s + (Number(a.durationSeconds) || 0), 0),
      0
    );

    function formatDaysHoursMinSec(sec) {
      const days = Math.floor(sec / 86400);
      const rem1 = sec % 86400;
      const hours = Math.floor(rem1 / 3600);
      const rem2 = rem1 % 3600;
      const minutes = Math.floor(rem2 / 60);
      const seconds = rem2 % 60;
      return `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }

    const formattedTotalTime = formatDaysHoursMinSec(totalSeconds);
    const totalMinutesRounded = Math.round(totalSeconds / 60);

    function renderYearsChart(sortMode) {
      const list = sortMode === "count" ? yearsListByCount : yearsListChrono;
      return list
        .map((item) => {
          const pct = Math.round((item.count / maxYearCount) * 100);
          return `
            <a href="index.html?albumYear=${encodeURIComponent(item.year)}" class="year-bar-row" title="Kliknij, aby zobaczyć spotkania z albumami z roku ${escapeHtml(item.year)}">
              <span class="year-bar-label">${escapeHtml(item.year)}</span>
              <div class="year-bar-track">
                <div class="year-bar-fill" style="width: ${pct}%"></div>
              </div>
              <span class="year-bar-value">${item.count}</span>
            </a>
          `;
        })
        .join("");
    }

    rootEl.innerHTML = `
      <!-- KPI Summary Cards -->
      <div class="stats-kpi-grid">
        <div class="kpi-card">
          <span class="kpi-value">${regularMeetings.length}</span>
          <span class="kpi-label">Spotkań</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-value">${totalPlays}</span>
          <span class="kpi-label">Płyt</span>
        </div>
        <div class="kpi-card" title="${formattedTotalTime}">
          <span class="kpi-value">${String(totalMinutesRounded).replace(/\B(?=(\d{3})+(?!\d))/g, " ")}</span>
          <span class="kpi-label">Minut grania</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-value">${uniqueAlbums.length}</span>
          <span class="kpi-label">Albumów</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-value">${artistStatsMap.size}</span>
          <span class="kpi-label">Wykonawców</span>
        </div>
      </div>

      <!-- Section Tabs -->
      <div class="stats-tabs" role="tablist" aria-label="Kategorie statystyk">
        <button type="button" class="stats-tab active" data-tab="all">Wszystkie</button>
        <button type="button" class="stats-tab" data-tab="decades">1. Dekady</button>
        <button type="button" class="stats-tab" data-tab="years">2. Roczniki płyt</button>
        <button type="button" class="stats-tab" data-tab="artists">3. Najczęstsi wykonawcy</button>
        <button type="button" class="stats-tab" data-tab="albums">4. Powtarzane albumy</button>
        <button type="button" class="stats-tab" data-tab="genres">5. Gatunki muzyczne</button>
      </div>

      <div class="stats-sections">
        <!-- 1. DECADES GRAPH -->
        <section class="stats-card" data-section="decades">
          <div class="stats-card-header">
            <div>
              <h2>1. Dekady</h2>
              <p class="stats-subtitle">Liczba unikalnych albumów wydanych w poszczególnych dekadach</p>
            </div>
          </div>
          <div class="decade-chart">
            ${decadesList
              .map((d) => {
                const pct = Math.round((d.count / maxDecadeCount) * 100);
                const share = ((d.count / uniqueAlbums.length) * 100).toFixed(1);
                return `
                  <div class="chart-row">
                    <div class="chart-label-col">
                      <span class="chart-label-main">${escapeHtml(d.decade)}</span>
                      <span class="chart-label-sub">${escapeHtml(d.labelPl)}</span>
                    </div>
                    <div class="chart-bar-wrap">
                      <div class="chart-bar-fill" style="width: ${pct}%"></div>
                    </div>
                    <div class="chart-value-col">
                      <strong>${d.count}</strong>
                      <span class="chart-pct">(${share}%)</span>
                    </div>
                  </div>
                `;
              })
              .join("")}
          </div>
        </section>

        <!-- 5. GENRES GRAPH -->
        <section class="stats-card" data-section="genres">
          <div class="stats-card-header">
            <div>
              <h2>5. Gatunki muzyczne</h2>
              <p class="stats-subtitle">Podział ${uniqueAlbums.length} unikalnych albumów według gatunku muzycznego (kliknij gatunek, aby filtrować spotkania)</p>
            </div>
          </div>
          <div class="genre-chart">
            ${genreList
              .map((g) => {
                const pct = Math.round((g.count / maxGenreCount) * 100);
                return `
                  <a href="index.html?genre=${encodeURIComponent(g.genre)}" class="chart-row chart-row-link" title="Zobacz spotkania z gatunkiem: ${escapeHtml(g.genre)}">
                    <div class="chart-label-col">
                      <span class="chart-label-main">${escapeHtml(g.genre)}</span>
                    </div>
                    <div class="chart-bar-wrap">
                      <div class="chart-bar-fill genre-bar-fill" style="width: ${pct}%"></div>
                    </div>
                    <div class="chart-value-col">
                      <strong>${g.count}</strong>
                      <span class="chart-pct">(${g.pct}%)</span>
                    </div>
                  </a>
                `;
              })
              .join("")}
          </div>
        </section>

        <!-- 2. RELEASE YEARS GRAPH -->
        <section class="stats-card stats-card-full" data-section="years">
          <div class="stats-card-header">
            <div>
              <h2>2. Roczniki wydania albumów</h2>
              <p class="stats-subtitle">Liczba unikalnych albumów z danego roku wydania (kliknij słupek, aby wyświetlić spotkania z tym rocznikiem)</p>
            </div>
            <div class="sort-toggle-group">
              <button type="button" class="btn-sort active" data-year-sort="chrono">Wg roku</button>
              <button type="button" class="btn-sort" data-year-sort="count">Wg liczby płyt</button>
            </div>
          </div>
          <div id="years-chart-container" class="years-chart-grid">
            ${renderYearsChart("chrono")}
          </div>
        </section>

        <!-- 3. MOST PLAYED ARTISTS LIST -->
        <section class="stats-card" data-section="artists">
          <div class="stats-card-header">
            <div>
              <h2>3. Najczęściej odtwarzani wykonawcy</h2>
              <p class="stats-subtitle">Łączna liczba odtworzonych płyt wykonawcy na spotkaniach (powyżej 1 odtworzenia)</p>
            </div>
          </div>
          <div class="ranked-list">
            ${mostPlayedArtists
              .map((item, idx) => {
                const pct = Math.round((item.plays / maxArtistPlays) * 100);
                const uniqCount = item.uniqueAlbums.size;
                return `
                  <a href="index.html?artist=${encodeURIComponent(item.artist)}" class="ranked-item" title="Zobacz wszystkie spotkania z wykonawcą: ${escapeHtml(item.artist)}">
                    <span class="rank-num">${idx + 1}.</span>
                    <div class="ranked-main">
                      <div class="ranked-top-row">
                        <span class="ranked-title">${escapeHtml(item.artist)}</span>
                        <span class="ranked-meta">${uniqCount > 0 ? `unikalnych płyt: ${uniqCount}` : ""}</span>
                      </div>
                      <div class="ranked-bar-track">
                        <div class="ranked-bar-fill" style="width: ${pct}%"></div>
                      </div>
                    </div>
                    <span class="rank-count-badge">${item.plays}×</span>
                  </a>
                `;
              })
              .join("")}
          </div>
        </section>

        <!-- 4. MOST REPLAYED ALBUMS LIST -->
        <section class="stats-card" data-section="albums">
          <div class="stats-card-header">
            <div>
              <h2>4. Najczęściej powtarzane albumy</h2>
              <p class="stats-subtitle">Albumy, które gościły na spotkaniach więcej niż 1 raz (${replayedAlbums.length} albumów)</p>
            </div>
          </div>
          <div class="replayed-albums-list">
            ${replayedAlbums
              .map((alb, idx) => {
                const coverHtml = alb.cover
                  ? `<img src="${escapeHtml(alb.cover)}" alt="${escapeHtml(alb.album)}" loading="lazy" />`
                  : "";
                return `
                  <a href="index.html?album=${encodeURIComponent(alb.album)}" class="replayed-album-item" title="Zobacz spotkania z albumem: ${escapeHtml(alb.album)}">
                    <span class="rank-num">${idx + 1}.</span>
                    <div class="replayed-cover">
                      ${coverHtml}
                    </div>
                    <div class="replayed-info">
                      <div class="replayed-title">${escapeHtml(alb.album)}</div>
                      <div class="replayed-artist">${escapeHtml(alb.artist)}</div>
                      <div class="replayed-badges">
                        ${alb.releaseYear ? `<span class="badge">${escapeHtml(alb.releaseYear)}</span>` : ""}
                        ${alb.genre ? `<span class="badge">${escapeHtml(alb.genre)}</span>` : ""}
                        <span class="replayed-dates">Spotkania: ${escapeHtml(alb.meetings.join(", "))}</span>
                      </div>
                    </div>
                    <span class="rank-count-badge">${alb.count}×</span>
                  </a>
                `;
              })
              .join("")}
          </div>
        </section>
      </div>
    `;

    // Tab switching logic
    const tabBtns = rootEl.querySelectorAll(".stats-tab");
    const sections = rootEl.querySelectorAll("[data-section]");
    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.getAttribute("data-tab");
        tabBtns.forEach((b) => b.classList.toggle("active", b === btn));
        sections.forEach((sec) => {
          if (target === "all") {
            sec.style.display = "";
            sec.classList.remove("stats-card-single");
          } else {
            const match = sec.getAttribute("data-section") === target;
            sec.style.display = match ? "" : "none";
            sec.classList.toggle("stats-card-single", match);
          }
        });
      });
    });

    // Release Year sort toggle
    const sortBtns = rootEl.querySelectorAll("[data-year-sort]");
    const yearsContainer = document.getElementById("years-chart-container");
    sortBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.getAttribute("data-year-sort");
        sortBtns.forEach((b) => b.classList.toggle("active", b === btn));
        yearsContainer.innerHTML = renderYearsChart(mode);
      });
    });
  });
})();
