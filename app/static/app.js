"use strict";
const $ = (id) => document.getElementById(id);
const state = { all: [], results: [], album: "", song: null, liked: false, mode: "related", view: "katalog", tab: "home",
  searchSeq: 0, selectSeq: 0, matchSeq: 0, changed: false, status: null, writeTrace: [], homeGenre: "",
  stationArtist: "", playlists: [], playlistId: "" };
const audio = $("audio");
let noticeTimer;

// The highlight is decorative. Touch and reduced-motion modes use a fixed reflection.
const hoverLight = matchMedia("(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)");
let litSurface = null;

function clearLight() {
  if (!litSurface) return;
  litSurface.style.removeProperty("--light-x");
  litSurface.style.removeProperty("--light-y");
  litSurface = null;
}

document.addEventListener("pointermove", event => {
  const surface = hoverLight.matches && event.pointerType !== "touch" ? event.target.closest(".glass") : null;
  if (surface !== litSurface) clearLight();
  if (!surface) return;
  litSurface = surface;
  const bounds = surface.getBoundingClientRect();
  surface.style.setProperty("--light-x", Math.round(event.clientX - bounds.left) + "px");
  surface.style.setProperty("--light-y", Math.round(event.clientY - bounds.top) + "px");
}, {passive: true});
document.documentElement.addEventListener("pointerleave", clearLight);
hoverLight.addEventListener("change", clearLight);

const laptop = matchMedia("(min-width: 960px)");
function placeSearch() {
  const field = $("searchBox");
  const heading = $(laptop.matches ? state.view : "katalog").querySelector(".heading") || $("browseHeading");
  const restoreFocus = document.activeElement === $("search");
  field.hidden = state.tab === "station" || state.tab === "playlist" || (!laptop.matches && state.tab !== "search");
  if (field.parentElement !== heading) {
    heading.append(field);
    if (restoreFocus && !field.hidden) $("search").focus({preventScroll:true});
  }
}
function arrangeLayout() {
  const profileLocation = document.querySelector(laptop.matches ? ".main-nav" : "#koleksi .heading");
  profileLocation.append($("profileLink"));
  $(laptop.matches ? "desktopRailSlot" : "mobileRailSlot").append($("discovery"));
  placeSearch();
}
arrangeLayout();
laptop.addEventListener("change", arrangeLayout);

function element(tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}
function say(message, error = false) {
  clearTimeout(noticeTimer);
  $("notice").textContent = message;
  $("notice").hidden = !message;
  $("notice").className = error ? "error" : "";
  if (message && !error) noticeTimer = setTimeout(() => say(""), 2600);
}
function run(action) {
  return (...args) => Promise.resolve().then(() => action(...args)).catch(e => say(e.message, true));
}
async function api(path, method = "GET", data) {
  const options = {method, cache:"no-store"};
  if (data !== undefined) {
    options.headers = {"Content-Type":"application/json"};
    options.body = JSON.stringify(data);
  }
  const res = await fetch("/api/" + path, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const error = new Error(body.error || "Permintaan gagal. Muat ulang untuk mencoba lagi.");
    error.status = res.status;
    throw error;
  }
  return res.status === 204 ? null : res.json();
}
function trace(lines) {
  $("trace").replaceChildren(...lines.map(line => {
    const [store, message] = line.split(" · ");
    const li = element("li", undefined, store === "Neo4j" ? "neo" : "");
    li.append(element("b", store), document.createTextNode(" · " + message));
    return li;
  }));
}
function empty(msg) { return element("p", msg, "empty"); }
function action(label, handler, cls = "small-btn") {
  const b = element("button", label, cls);
  b.type = "button";
  b.onclick = run(handler);
  return b;
}
function artwork(cover, cls = "") {
  const art = element("span", undefined, "art " + cover + (cls ? " " + cls : ""));
  art.setAttribute("aria-hidden", "true");
  return art;
}
function homeFilter(label, genre) {
  const button = action(label, () => {
    state.homeGenre = genre;
    renderHome();
  }, "home-filter");
  button.setAttribute("aria-pressed", String(state.homeGenre === genre));
  return button;
}
function quickPick(song) {
  const button = action("", () => selectSong(song), "quick-pick");
  button.setAttribute("aria-label", "Putar " + song.title + " oleh " + song.artist);
  button.append(artwork(song.cover, "quick-art"), element("strong", song.title), element("span", song.artist));
  return button;
}
function releaseCard(song) {
  const button = action("", () => selectSong(song), "release-card");
  button.setAttribute("aria-label", "Putar album " + song.album + " oleh " + song.artist);
  button.append(artwork(song.cover, "release-art"), element("strong", song.album), element("span", song.artist));
  return button;
}
function stationTheme(artist) {
  return [...artist].reduce((sum, character) => sum + character.codePointAt(0), 0) % 4;
}
function songsByArtist(artist) {
  return state.all.filter(song => (song.artists || [song.artist]).includes(artist));
}
function openStation(artist) {
  const route = "station/" + encodeURIComponent(artist);
  if (location.hash.slice(1) === route) showPage();
  else location.hash = route;
}
function stationCard([artist, songs]) {
  const first = songs[0];
  const button = action("", () => openStation(artist), "station-card station-" + stationTheme(artist));
  button.setAttribute("aria-label", "Buka stasiun " + artist);
  const visual = element("span", undefined, "station-art");
  visual.append(...songs.slice(0, 3).map(song => artwork(song.cover, "station-cover")));
  visual.append(element("strong", artist));
  button.append(visual, element("strong", artist + " Radio"),
    element("span", first.genre + " · " + songs.length + " lagu"));
  return button;
}
function renderHome() {
  const songs = state.all.filter(song => !state.homeGenre || song.genre === state.homeGenre);
  const filters = [["Semua", ""], ...[...new Set(state.all.map(song => song.genre))].map(genre => [genre, genre])];
  $("homeFilters").replaceChildren(...filters.map(([label, genre]) => homeFilter(label, genre)));
  $("quickPicks").replaceChildren(...songs.slice(0, 6).map(quickPick));

  const albums = [];
  const seenAlbums = new Set();
  for (const song of songs) {
    if (seenAlbums.has(song.album)) continue;
    seenAlbums.add(song.album);
    albums.push(song);
  }
  $("homeReleases").replaceChildren(...albums.slice(0, 8).map(releaseCard));

  const byArtist = new Map();
  for (const song of songs) {
    for (const artist of song.artists || [song.artist]) {
      const group = byArtist.get(artist) || [];
      group.push(song);
      byArtist.set(artist, group);
    }
  }
  const stations = [...byArtist.entries()]
    .sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]))
    .slice(0, 8);
  $("homeStations").replaceChildren(...stations.map(stationCard));
}
function durationLabel(song) {
  const seconds = Math.round((song.original_duration_ms || song.seconds * 1000) / 1000);
  return Math.floor(seconds / 60) + ":" + String(seconds % 60).padStart(2, "0");
}
function stationSongRow(song, artist, index) {
  const current = !$("player").hidden && song._id === state.song?._id;
  const button = action("", () => selectSong(song), "station-song" + (current ? " current" : ""));
  button.setAttribute("aria-label", "Putar " + song.title + " oleh " + song.artist);
  button.append(element("span", String(index + 1), "station-number"), artwork(song.cover, "station-song-art"));
  const copy = element("span", undefined, "station-song-copy");
  copy.append(element("strong", song.title), element("small", song.artist));
  button.append(copy, element("span", song.album, "station-album"), element("span", durationLabel(song), "station-duration"));
  return button;
}
function renderStationTracks(artist) {
  const songs = songsByArtist(artist);
  $("stationTracks").replaceChildren(...songs.map((song, index) => stationSongRow(song, artist, index)));
}
function renderStation(artist) {
  const songs = songsByArtist(artist);
  if (!songs.length) {
    location.hash = "home";
    return;
  }
  state.stationArtist = artist;
  const genres = [...new Set(songs.map(song => song.genre))];
  const hero = $("stationHero");
  hero.className = "station-hero station-" + stationTheme(artist);
  const heroSongs = Array.from({length: 3}, (_, index) => songs[index % songs.length]);
  $("stationHeroArt").replaceChildren(...heroSongs.map(song => artwork(song.cover, "station-hero-cover")));
  $("stationDetailTitle").textContent = artist + " Radio";
  $("stationDescription").textContent = "Pilihan katalog yang menampilkan " + artist + " sebagai artis utama atau kolaborator.";
  $("stationMeta").textContent = songs.length + " lagu · " + genres.join(" · ");
  $("stationToolbarTitle").textContent = artist + " Radio";
  $("stationPlay").setAttribute("aria-label", "Putar " + artist + " Radio");
  renderStationTracks(artist);
}
function songRow(song, reason = "", current = false) {
  const b = action("", async () => {
    if (state.view !== "katalog") location.hash = "home";
    await selectSong(song);
  }, "track" + (current ? " current" : ""));
  b.setAttribute("aria-label", "Putar " + song.title + " · " + (reason || song.artist));
  const thumb = element("span", undefined, "art thumb " + song.cover);
  thumb.setAttribute("aria-hidden", "true");
  const copy = element("span", undefined, "song-copy");
  copy.append(element("strong", song.title), element("small", reason || song.artist));
  b.append(thumb, copy, element("span", "0:" + song.seconds, "track-end"));
  return b;
}
function visibleSongs() {
  return state.results.filter(s => !state.album || s.album === state.album);
}
function showTracks() {
  const songs = visibleSongs();
  const awaitingQuery = state.tab === "search" && !$("search").value.trim() && !$("genres").value;
  $("tracks").hidden = awaitingQuery;
  $("searchEmpty").hidden = !awaitingQuery;
  $("tracks").replaceChildren(...songs.map(s => songRow(s, "", !$("player").hidden && s._id === state.song?._id)));
  if (!songs.length) $("tracks").append(empty("Tidak ada lagu yang cocok."));
}
function showAlbums() {
  const seen = new Set();
  const tiles = [];
  for (const song of state.results) {
    if (seen.has(song.album)) continue;
    seen.add(song.album);
    const tile = action("", () => {
      state.album = state.album === song.album ? "" : song.album;
      for (const item of $("albums").children) {
        item.setAttribute("aria-pressed", String(item.dataset.album === state.album));
      }
      showTracks();
    }, "album");
    tile.dataset.album = song.album;
    tile.setAttribute("aria-pressed", String(state.album === song.album));
    const caption = element("span", undefined, "album-caption glass");
    caption.append(element("strong", song.album), element("small", song.artist));
    tile.append(element("span", undefined, "art album-art " + song.cover), caption);
    tiles.push(tile);
  }
  $("albums").replaceChildren(...tiles);
  $("albums").hidden = state.tab === "search" || !tiles.length;
}
async function search() {
  const seq = ++state.searchSeq;
  const params = new URLSearchParams({q:state.tab === "search" ? $("search").value : "", genre:$("genres").value});
  const data = await api("catalog?" + params);
  if (seq !== state.searchSeq) return;
  state.results = data.songs;
  state.album = "";
  showTracks(); showAlbums();
  if (state.tab === "search" || $("genres").value) trace(data.trace);
}
function outputLike() {
  $("like").setAttribute("aria-pressed", String(state.liked));
  $("like").setAttribute("aria-label", state.liked ? "Batalkan suka" : "Suka");
  $("like").title = state.liked ? "Batalkan suka" : "Suka";
}
async function selectSong(song, play = true) {
  const seq = ++state.selectSeq;
  state.song = song;
  state.mode = "related";
  state.writeTrace = [];
  say("");
  document.body.dataset.sleeve = song.cover;
  $("featureTitle").textContent = song.title;
  $("featureMeta").textContent = song.artist;
  $("like").disabled = true;
  state.liked = false;
  outputLike();
  $("play").disabled = $("prev").disabled = $("next").disabled = $("seek").disabled = false;
  $("seek").max = song.seconds;
  audio.src = song.audio;
  // Start audio in the click gesture, before waiting for either database.
  const playback = play ? audio.play() : Promise.resolve();
  const likeStatus = api("songs/" + song._id).then(detail => {
    if (seq !== state.selectSeq) return;
    state.liked = detail.liked;
    outputLike();
    $("like").disabled = false;
  });
  playerTime();
  try {
    await Promise.all([playback, likeStatus, matches()]);
  } catch (error) {
    if (seq !== state.selectSeq || error.name === "AbortError") return;
    if (play && audio.paused) hidePlayer();
    throw error;
  }
}
async function matches() {
  const seq = ++state.matchSeq;
  const personal = state.mode === "recommend";
  $("relatedTab").setAttribute("aria-pressed", String(!personal));
  $("recTab").setAttribute("aria-pressed", String(personal));
  const area = $("matches");
  if (!personal && !state.song) {
    area.replaceChildren(empty("Putar lagu untuk melihat lagu terkait."));
    return;
  }
  try {
    const data = await api(personal ? "recommendations" : "songs/" + state.song._id + "/related");
    if (seq !== state.matchSeq) return;
    const rows = data.songs.map(s => songRow(s, "Terhubung lewat " + s.reasons.join(" dan ")));
    area.replaceChildren(...(rows.length ? rows : [empty(personal ?
      "Sukai lagu untuk melihat rekomendasi." : "Belum ada lagu terkait.")]));
    trace([...(personal ? state.writeTrace : []), ...data.trace]);
  } catch(e) {
    if (seq !== state.matchSeq) return;
    area.replaceChildren(empty(e.message));
    trace(personal ? state.writeTrace : []);
  }
}
async function changeLike() {
  const id = state.song._id;
  $("like").disabled = true;
  try {
    const data = await api("songs/" + id + "/like", "PUT", {liked: !state.liked});
    if (state.song._id !== id) return;
    state.liked = data.liked;
    state.changed = true;
    state.mode = "recommend";
    state.writeTrace = data.trace;
    outputLike();
    say(state.status?.graph === false ? "Tersimpan. Menunggu sinkronisasi." : "");
    await matches();
    await statusUpdate();
  } finally {
    $("like").disabled = false;
  }
}
let statusRequest = false;
async function statusUpdate() {
  if (statusRequest) return;
  statusRequest = true;
  try {
    const data = await api("status");
    const old = state.status;
    state.status = data;
    $("sync").textContent = "MongoDB aktif · Neo4j " + (data.graph ? "siap" : "menunggu") +
      " · " + data.pending + " tertunda";
    const graphChanged = !old || data.graph !== old.graph;
    const delivered = data.graph && !data.pending && (state.changed || old?.pending);
    if ((state.view === "katalog" || laptop.matches) && (graphChanged || delivered)) {
      state.changed = false;
      await matches();
    }
  } catch(e) {
    $("sync").textContent = e.message;
  } finally { statusRequest = false; }
}
function playerTime() {
  const seconds = Math.floor(audio.currentTime || 0);
  const duration = state.song?.seconds || 12;
  $("seek").value = audio.currentTime || 0;
  $("seek").style.setProperty("--played", (100 * Number($("seek").value) / duration) + "%");
  $("time").textContent = "0:" + String(seconds).padStart(2, "0") + " / 0:" + (state.song?.seconds || 12);
  $("seek").setAttribute("aria-valuetext", $("time").textContent);
  $("playShape").setAttribute("href", audio.paused ? "#i-play" : "#i-pause");
  $("play").setAttribute("aria-label", audio.paused ? "Putar sampel" : "Jeda sampel");
  $("play").title = $("play").getAttribute("aria-label");
}
async function skip(step) {
  if (state.tab === "station" && state.stationArtist) {
    const queue = songsByArtist(state.stationArtist);
    const index = queue.findIndex(song => song._id === state.song?._id);
    await selectSong(queue[(index + step + queue.length) % queue.length], !audio.paused);
    renderStationTracks(state.stationArtist);
    return;
  }
  if (state.tab === "playlist" && state.playlistId) {
    const record = state.playlists.find(playlist => playlist._id === state.playlistId);
    const queue = record ? record.songs.map(id => state.all.find(song => song._id === id)).filter(Boolean) : [];
    if (queue.length) {
      const current = queue.findIndex(song => song._id === state.song?._id);
      const index = current < 0 ? 0 : (current + step + queue.length) % queue.length;
      await selectSong(queue[index], !audio.paused);
      renderPlaylistTracks(record);
    }
    return;
  }
  const filtered = visibleSongs();
  const inList = filtered.some(s => s._id === state.song?._id);
  const queue = inList ? filtered : state.all;
  const index = queue.findIndex(s => s._id === state.song?._id);
  await selectSong(queue[(index + step + queue.length) % queue.length], !audio.paused);
  showTracks();
}
$("prev").onclick = run(() => skip(-1));
$("next").onclick = run(() => skip(1));
$("play").onclick = run(async () => { if (audio.paused) await audio.play(); else audio.pause(); });
function hidePlayer() {
  $("player").hidden = true;
  showTracks();
  if (state.tab === "station") renderStationTracks(state.stationArtist);
  if (state.tab === "playlist") {
    const record = state.playlists.find(playlist => playlist._id === state.playlistId);
    if (record) renderPlaylistTracks(record);
  }
}
audio.onplaying = () => {
  $("player").hidden = false;
  playerTime();
  showTracks();
  if (state.tab === "station") renderStationTracks(state.stationArtist);
  if (state.tab === "playlist") {
    const record = state.playlists.find(playlist => playlist._id === state.playlistId);
    if (record) renderPlaylistTracks(record);
  }
};
audio.ontimeupdate = audio.onplay = audio.onpause = playerTime;
audio.onended = () => { playerTime(); hidePlayer(); };
audio.onerror = () => { hidePlayer(); say("Sampel audio tidak dapat dimuat.", true); };
$("seek").oninput = () => { if (audio.readyState) audio.currentTime = Number($("seek").value); };
$("like").onclick = run(changeLike);
$("recTab").onclick = run(async () => { state.mode = "recommend"; await matches(); });
$("relatedTab").onclick = run(async () => { state.mode = "related"; state.writeTrace = []; await matches(); });
$("search").oninput = run(() => {
  if (state.tab !== "search") location.hash = "search";
  else return search();
});
$("genres").onchange = run(search);
$("stationBack").onclick = () => { location.hash = "home"; };
$("playlistBack").onclick = () => { location.hash = "library"; };
$("stationPlay").onclick = run(async () => {
  const songs = songsByArtist(state.stationArtist);
  if (songs.length) await selectSong(songs[0]);
});

function playlistSongs(record) {
  return record.songs.map(id => state.all.find(song => song._id === id)).filter(Boolean);
}
function playlistArtwork(record, cls = "") {
  const box = element("span", undefined, "playlist-artwork" + (cls ? " " + cls : ""));
  const songs = playlistSongs(record);
  if (songs.length) {
    const tiles = Array.from({length: 4}, (_, index) => songs[index % songs.length]);
    box.append(...tiles.map(song => artwork(song.cover, "playlist-art-tile")));
  } else {
    const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    icon.setAttribute("aria-hidden", "true");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", "#i-note");
    icon.append(use);
    box.append(icon);
  }
  return box;
}
function librarySongCard(song) {
  const button = action("", () => selectSong(song), "library-song-card");
  button.setAttribute("aria-label", "Putar " + song.title);
  button.append(artwork(song.cover, "library-card-art"), element("strong", song.title), element("span", song.artist));
  return button;
}
function playlistLibraryCard(record) {
  const link = element("a", undefined, "playlist-library-card");
  link.href = "#playlist/" + encodeURIComponent(record._id);
  link.setAttribute("aria-label", "Buka playlist " + record.name);
  link.append(playlistArtwork(record, "playlist-library-art"), element("strong", record.name),
    element("span", record.songs.length + " lagu · Playlist pribadi"));
  return link;
}
function renderPlaylistLibrary() {
  $("playlists").replaceChildren(...state.playlists.map(playlistLibraryCard));
  if (!state.playlists.length) $("playlists").append(empty("Belum ada playlist. Buat playlist pertamamu."));
}
function sidebarPlaylist(record) {
  const link = element("a", undefined, "sidebar-playlist");
  link.href = "#playlist/" + encodeURIComponent(record._id);
  link.dataset.playlistId = record._id;
  link.setAttribute("aria-label", "Buka playlist " + record.name);
  const icon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  icon.setAttribute("aria-hidden", "true");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", "#i-note");
  icon.append(use);
  link.append(icon, element("span", record.name));
  return link;
}
function showSidebarPlaylists(playlists) {
  const section = $("sidebarPlaylists");
  section.hidden = !playlists.length;
  const sorted = [...playlists].sort((a, b) => a.name.localeCompare(b.name));
  $("sidebarPlaylistList").replaceChildren(...sorted.map(sidebarPlaylist));
  for (const link of $("sidebarPlaylistList").children) {
    if (state.tab === "playlist" && link.dataset.playlistId === state.playlistId) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
}
async function persistPlaylist(record, name, songs, message) {
  try {
    const updated = await api("playlists/" + record._id, "PUT", {name, songs, version:record.version});
    state.playlists = state.playlists.map(playlist => playlist._id === updated._id ? updated : playlist)
      .sort((a, b) => a.name.localeCompare(b.name));
    renderPlaylistLibrary();
    showSidebarPlaylists(state.playlists);
    if (state.tab === "playlist") renderPlaylistDetail(updated);
    say(message);
    return updated;
  } catch (error) {
    if (error.status === 409 || error.status === 404) await loadPlaylists();
    throw error;
  }
}
function playlistTrackRow(song, record, index) {
  const row = element("article", undefined, "playlist-detail-row" +
    (!$("player").hidden && song._id === state.song?._id ? " current" : ""));
  const play = action("", () => selectSong(song), "playlist-track-main");
  play.setAttribute("aria-label", "Putar " + song.title);
  const copy = element("span", undefined, "playlist-track-copy");
  copy.append(element("strong", song.title), element("small", song.artist));
  play.append(element("span", String(index + 1), "playlist-track-number"), artwork(song.cover, "playlist-track-art"), copy,
    element("span", song.album, "playlist-track-album"), element("span", durationLabel(song), "playlist-track-duration"));
  const controls = element("div", undefined, "playlist-row-actions");
  const move = async offset => {
    const songs = [...record.songs];
    [songs[index], songs[index + offset]] = [songs[index + offset], songs[index]];
    await persistPlaylist(record, record.name, songs, "Urutan lagu diperbarui.");
  };
  if (index > 0) controls.append(action("Naik", () => move(-1), "playlist-row-button"));
  if (index < record.songs.length - 1) controls.append(action("Turun", () => move(1), "playlist-row-button"));
  controls.append(action("Keluarkan", () => persistPlaylist(record, record.name,
    record.songs.filter(id => id !== song._id), "Lagu dikeluarkan dari playlist."), "playlist-row-button remove"));
  row.append(play, controls);
  return row;
}
function renderPlaylistTracks(record) {
  const songs = playlistSongs(record);
  $("playlistDetailTracks").replaceChildren(...songs.map((song, index) => playlistTrackRow(song, record, index)));
  if (!songs.length) $("playlistDetailTracks").append(empty("Playlist ini masih kosong."));
}
function renderPlaylistSuggestions(record) {
  const term = $("playlistSongSearch").value.trim().toLocaleLowerCase();
  const candidates = state.all.filter(song => !record.songs.includes(song._id) &&
    (!term || [song.title, song.artist, song.album, song.genre].some(value => value.toLocaleLowerCase().includes(term)))).slice(0, 8);
  $("playlistSuggestions").replaceChildren(...candidates.map(song => {
    const item = element("article", undefined, "playlist-suggestion");
    const copy = element("span", undefined, "playlist-suggestion-copy");
    copy.append(element("strong", song.title), element("small", song.artist + " · " + song.album));
    item.append(artwork(song.cover, "playlist-suggestion-art"), copy,
      action("Tambahkan", () => persistPlaylist(record, record.name, [...record.songs, song._id],
        "Lagu ditambahkan ke playlist."), "small-btn"));
    return item;
  }));
  if (!candidates.length) $("playlistSuggestions").append(empty(term ? "Tidak ada lagu yang cocok." : "Semua lagu sudah ada di playlist."));
}
function renderPlaylistDetail(record) {
  state.playlistId = record._id;
  $("playlistCover").replaceChildren(...playlistArtwork(record).childNodes);
  $("playlistDetailTitle").textContent = record.name;
  $("playlistDetailMeta").textContent = "Pendengar Demo · " + record.songs.length + " lagu";
  $("playlistNameInput").value = record.name;
  $("playlistRenameForm").hidden = true;
  $("playlistPlay").disabled = !record.songs.length;
  $("playlistPlay").setAttribute("aria-label", "Putar playlist " + record.name);
  $("playlistSongSearch").value = "";
  renderPlaylistTracks(record);
  renderPlaylistSuggestions(record);
  showSidebarPlaylists(state.playlists);
  $("playlistPlay").onclick = run(async () => {
    const first = playlistSongs(record)[0];
    if (first) await selectSong(first);
  });
  $("playlistRename").onclick = () => {
    $("playlistRenameForm").hidden = !$("playlistRenameForm").hidden;
    if (!$("playlistRenameForm").hidden) $("playlistNameInput").focus({preventScroll:true});
  };
  $("playlistRenameForm").onsubmit = event => {
    event.preventDefault();
    run(() => persistPlaylist(record, $("playlistNameInput").value.trim(), record.songs, "Nama playlist diperbarui."))();
  };
  $("playlistSongSearch").oninput = () => renderPlaylistSuggestions(record);
  $("playlistDelete").onclick = () => {
    $("deleteName").textContent = record.name;
    const dialog = $("confirmDelete");
    dialog.returnValue = "";
    dialog.onclose = run(async () => {
      if (dialog.returnValue !== "delete") return;
      await api("playlists/" + record._id, "DELETE", {name:record.name, songs:record.songs, version:record.version});
      state.playlists = state.playlists.filter(playlist => playlist._id !== record._id);
      renderPlaylistLibrary();
      showSidebarPlaylists(state.playlists);
      location.hash = "library";
      say("Playlist dihapus.");
    });
    dialog.showModal();
  };
}
async function loadPlaylists() {
  const data = await api("playlists");
  state.playlists = [...data.playlists].sort((a, b) => a.name.localeCompare(b.name));
  renderPlaylistLibrary();
  showSidebarPlaylists(state.playlists);
  const current = state.playlists.find(playlist => playlist._id === state.playlistId);
  if (state.tab === "playlist" && current) renderPlaylistDetail(current);
}
$("newPlaylist").onsubmit = (e) => {
  e.preventDefault();
  const submit = $("newPlaylist").querySelector("button");
  if (submit.disabled) return;
  submit.disabled = true;
  run(async () => {
    try {
      const record = await api("playlists", "POST", {name:$("newName").value});
      $("newPlaylist").reset();
      state.playlists = [...state.playlists, record].sort((a, b) => a.name.localeCompare(b.name));
      renderPlaylistLibrary();
      showSidebarPlaylists(state.playlists);
      location.hash = "playlist/" + encodeURIComponent(record._id);
    } finally { submit.disabled = false; }
  })();
};
$("profile").onsubmit = (e) => {
  e.preventDefault();
  run(async () => {
    const data = await api("profile", "PUT", {name:$("displayName").value, bio:$("bio").value});
    $("displayName").value = data.name; $("bio").value = data.bio; say("Profil tersimpan.");
  })();
};
async function showPage() {
  const hash = location.hash.slice(1);
  let stationArtist = "";
  let playlistId = "";
  if (hash.startsWith("station/")) {
    try { stationArtist = decodeURIComponent(hash.slice(8)); }
    catch { stationArtist = ""; }
  }
  if (hash.startsWith("playlist/")) {
    try { playlistId = decodeURIComponent(hash.slice(9)); }
    catch { playlistId = ""; }
  }
  const requestedTab = hash === "katalog" ? "home" : hash === "koleksi" ? "library" : hash;
  const tab = stationArtist ? "station" : playlistId ? "playlist" : requestedTab;
  const pages = {home:"katalog", search:"katalog", station:"katalog", playlist:"playlistView", library:"koleksi", create:"create", profil:"profil"};
  if (state.tab === "search" && tab !== "search") $("search").value = "";
  state.tab = Object.hasOwn(pages, tab) ? tab : "home";
  state.view = pages[state.tab];
  const isStation = state.tab === "station";
  const isPlaylist = state.tab === "playlist";
  if (isPlaylist) state.playlistId = playlistId;
  document.body.dataset.tab = isStation ? "home" : state.tab;
  const isSearch = state.tab === "search";
  const isHome = state.tab === "home";
  $("browseTitle").textContent = isSearch ? "Search" : "Home";
  document.querySelectorAll(".page").forEach(p => p.hidden = p.id !== state.view);
  $("browseHeading").hidden = isStation;
  $("homeFeed").hidden = !isHome;
  $("stationDetail").hidden = !isStation;
  $("catalogContent").hidden = !isSearch;
  placeSearch();
  document.querySelectorAll(".main-nav > a, .profile-button").forEach(a => {
    const activeTab = isStation ? "home" : isPlaylist ? "library" : state.tab;
    if (a.hash.slice(1) === activeTab) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  window.scrollTo(0, 0);
  say("");
  if (state.view === "katalog") {
    $("genres").value = "";
    state.album = "";
    if (isStation) {
      ++state.searchSeq;
      state.results = state.all;
      renderStation(stationArtist);
    } else if (isSearch) {
      $("albums").hidden = true;
      $("search").focus({preventScroll:true});
      await search();
    } else {
      ++state.searchSeq;
      state.results = state.all;
      renderHome();
      await matches();
    }
  }
  if (state.tab === "create") $("newName").focus({preventScroll:true});
  if (isPlaylist) {
    await loadPlaylists();
    const record = state.playlists.find(playlist => playlist._id === playlistId);
    if (!record) location.hash = "library";
    else renderPlaylistDetail(record);
  } else if (state.view === "profil") {
    const data = await api("profile"); $("displayName").value = data.name; $("bio").value = data.bio;
  } else if (state.view === "koleksi") {
    const [likes] = await Promise.all([api("likes"), loadPlaylists()]);
    $("favorites").replaceChildren(...likes.songs.map(librarySongCard));
    if (!likes.songs.length) $("favorites").append(empty("Lagu yang kamu sukai akan muncul di sini."));
  }
}
async function init() {
  const data = await api("catalog");
  state.all = state.results = data.songs;
  $("genres").append(...data.genres.map(g => new Option(g, g)));
  renderHome();
  showTracks(); showAlbums();
  trace(data.trace);
  window.addEventListener("hashchange", run(showPage));
  await showPage();
  if (state.view !== "koleksi" && state.tab !== "playlist") await loadPlaylists();
  await statusUpdate();
  setInterval(statusUpdate, 2000);
}
run(init)();
