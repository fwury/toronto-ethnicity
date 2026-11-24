/* Toronto ethnic origin dot map: MapLibre basemaps + deck.gl dots. */
(async function () {
  "use strict";

  // ------------------------------------------------------------------ basemaps
  const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
  const CARTO_LABELS = (v) => ["a", "b", "c", "d"].map((s) => `https://${s}.basemaps.cartocdn.com/${v}/{z}/{x}/{y}@2x.png`);
  const BASEMAPS = [
    { id: "paper", name: "Paper", style: "styles/paper.json", swatch: "linear-gradient(135deg,#f4f0e6 60%,#cbd8da 60%)" },
    { id: "positron", name: "Positron", style: "https://tiles.openfreemap.org/styles/positron", swatch: "linear-gradient(135deg,#fafaf8 60%,#d4dadc 60%)" },
    { id: "liberty", name: "Liberty", style: "https://tiles.openfreemap.org/styles/liberty", swatch: "linear-gradient(135deg,#f0ede4 45%,#c8e2c0 45% 70%,#a0c8f0 70%)" },
    { id: "voyager", name: "Voyager", style: "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json", swatch: "linear-gradient(135deg,#f5f3ef 55%,#f2d6a6 55% 70%,#d5e8eb 70%)" },
    { id: "dark", name: "Dark", dark: true, style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json", swatch: "linear-gradient(135deg,#1b1d22 60%,#0e0f12 60%)" },
    {
      id: "satellite", name: "Satellite", dark: true, swatch: "linear-gradient(135deg,#3d4a37,#6b6f5c 50%,#2a3640)",
      style: {
        version: 8,
        sources: {
          esri: { type: "raster", tiles: [ESRI], tileSize: 256, maxzoom: 19, attribution: "Imagery © Esri, Maxar, Earthstar Geographics" },
          labels: { type: "raster", tiles: CARTO_LABELS("dark_only_labels"), tileSize: 256, attribution: "Labels © CARTO, © OpenStreetMap contributors" },
        },
        layers: [
          { id: "esri", type: "raster", source: "esri", paint: { "raster-saturation": -0.35, "raster-brightness-max": 0.75 } },
          { id: "labels", type: "raster", source: "labels" },
        ],
      },
    },
    {
      id: "blank", name: "Blank", swatch: "#f7f4ec",
      style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#f7f4ec" } }] },
    },
    {
      id: "night", name: "Night", dark: true, swatch: "#111317",
      style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#111317" } }] },
    },
  ];

  // ---------------------------------------------------------------------- state
  const $ = (s) => document.querySelector(s);
  const store = {
    get(k, d) { try { const v = localStorage.getItem("teo:" + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem("teo:" + k, JSON.stringify(v)); } catch (e) { /* ignore */ } },
  };
  const state = {
    basemap: store.get("basemap", "paper"),
    labels: store.get("labels", true),
    colorBy: store.get("colorBy", "sub"),
    size: store.get("size", 4),
    opacity: store.get("opacity", 0.85),
  };
  if (!BASEMAPS.find((b) => b.id === state.basemap)) state.basemap = "paper";

  // ----------------------------------------------------------------------- data
  const loading = $("#loading");
  let meta, N, positions, originOf;
  try {
    meta = await (await fetch("data/meta.json")).json();
    let buf = new Uint8Array(await (await fetch("data/dots.bin.gz")).arrayBuffer());
    if (buf[0] === 0x1f && buf[1] === 0x8b) {
      const stream = new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"));
      buf = new Uint8Array(await new Response(stream).arrayBuffer());
    }
    N = meta.count;
    const qx = new Uint16Array(buf.buffer, buf.byteOffset, N);
    const qy = new Uint16Array(buf.buffer, buf.byteOffset + 2 * N, N);
    originOf = new Uint8Array(buf.buffer, buf.byteOffset + 4 * N, N);
    const [x0, y0, x1, y1] = meta.bbox;
    const sx = (x1 - x0) / 65535, sy = (y1 - y0) / 65535;
    positions = new Float32Array(2 * N);
    for (let i = 0; i < N; i++) {
      positions[2 * i] = x0 + qx[i] * sx;
      positions[2 * i + 1] = y0 + qy[i] * sy;
    }
  } catch (err) {
    loading.textContent = "Could not load the map data. " + err.message;
    loading.classList.add("error");
    throw err;
  }

  const O = meta.origins.length;
  const visible = new Uint8Array(O).fill(1);
  const savedHidden = store.get("hidden", []);
  savedHidden.forEach((name) => {
    const i = meta.origins.findIndex((o) => o.name === name);
    if (i >= 0) visible[i] = 0;
  });

  const hex = (h) => [1, 3, 5].map((k) => parseInt(h.slice(k, k + 2), 16));
  function originColors() {
    const dark = BASEMAPS.find((b) => b.id === state.basemap).dark;
    return meta.origins.map((o) => {
      const sub = meta.subs[o.sub];
      let c = hex(state.colorBy === "broad" ? meta.broads[sub.broad].color : sub.color);
      if (dark) c = c.map((v) => Math.round(v + (255 - v) * 0.28));
      return c;
    });
  }

  let colors = new Uint8Array(4 * N), filter = new Float32Array(N);
  function rebuildColors() {
    const oc = originColors();
    colors = new Uint8Array(4 * N);
    for (let i = 0; i < N; i++) {
      const c = oc[originOf[i]];
      colors[4 * i] = c[0]; colors[4 * i + 1] = c[1]; colors[4 * i + 2] = c[2]; colors[4 * i + 3] = 255;
    }
  }
  function rebuildFilter() {
    filter = new Float32Array(N);
    let shown = 0;
    for (let i = 0; i < N; i++) { const v = visible[originOf[i]]; filter[i] = v; shown += v; }
    $("#visible-count").textContent =
      `${shown.toLocaleString()} dots shown · about ${(shown * meta.dot).toLocaleString()} responses`;
    store.set("hidden", meta.origins.filter((o, i) => !visible[i]).map((o) => o.name));
  }

  // ------------------------------------------------------------------------ map
  const bb = meta.bbox;
  const map = new maplibregl.Map({
    container: "map",
    style: styleFor(state.basemap),
    center: [-79.39, 43.705],
    zoom: window.innerWidth < 720 ? 9.4 : 10.3,
    minZoom: 7,
    maxZoom: 18,
    maxBounds: [[bb[0] - 0.6, bb[1] - 0.4], [bb[2] + 0.6, bb[3] + 0.4]],
    attributionControl: { compact: true, customAttribution: "Census data: Statistics Canada" },
    hash: true,
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-right");

  function styleFor(id) { return BASEMAPS.find((b) => b.id === id).style; }

  // Dots go under the first label layer so place names stay readable.
  function labelLayerId() {
    const layers = map.getStyle().layers || [];
    const sym = layers.find((l) => l.type === "symbol" || l.id === "labels");
    return sym ? sym.id : undefined;
  }
  function applyLabels() {
    for (const l of map.getStyle().layers || []) {
      if (l.type === "symbol" || l.id === "labels") map.setLayoutProperty(l.id, "visibility", state.labels ? "visible" : "none");
    }
  }

  let beforeId;
  function dotLayer() {
    return new deck.ScatterplotLayer({
      id: "dots",
      beforeId,
      data: {
        length: N,
        attributes: {
          getPosition: { value: positions, size: 2 },
          getFillColor: { value: colors, size: 4, normalized: true },
          getFilterValue: { value: filter, size: 1 },
        },
      },
      radiusUnits: "meters",
      getRadius: 1,
      radiusScale: state.size,
      radiusMinPixels: 0.35 + state.size * 0.06,
      radiusMaxPixels: 40,
      opacity: state.opacity,
      stroked: false,
      antialiasing: true,
      pickable: true,
      extensions: [new deck.DataFilterExtension({ filterSize: 1 })],
      filterRange: [0.5, 1.5],
      parameters: { depthWriteEnabled: false },
    });
  }

  const overlay = new deck.MapboxOverlay({
    interleaved: true,
    layers: [],
    getTooltip: ({ index }) => {
      if (index < 0) return null;
      const o = meta.origins[originOf[index]], s = meta.subs[o.sub], b = meta.broads[s.broad];
      return { html: `<b>${o.name}</b><br><span>${s.name === o.name ? b.name : s.name + " · " + b.name}</span>`, className: "tooltip" };
    },
  });
  map.addControl(overlay);
  const render = () => overlay.setProps({ layers: [dotLayer()] });

  map.on("style.load", () => {
    beforeId = labelLayerId();
    applyLabels();
    render();
  });

  rebuildColors();
  rebuildFilter();
  map.once("load", () => loading.classList.add("done"));

  // --------------------------------------------------------------- controls
  const bmWrap = $("#basemaps");
  BASEMAPS.forEach((b) => {
    const btn = document.createElement("button");
    btn.setAttribute("role", "radio");
    btn.setAttribute("aria-checked", String(b.id === state.basemap));
    btn.innerHTML = `<span class="sw" style="background:${b.swatch}"></span><span class="t">${b.name}</span>`;
    btn.onclick = () => {
      if (state.basemap === b.id) return;
      const wasDark = !!BASEMAPS.find((x) => x.id === state.basemap).dark;
      state.basemap = b.id; store.set("basemap", b.id);
      bmWrap.querySelectorAll("button").forEach((x) => x.setAttribute("aria-checked", String(x === btn)));
      if (wasDark !== !!b.dark) rebuildColors();
      map.setStyle(b.style);
    };
    bmWrap.appendChild(btn);
  });

  $("#labels").checked = state.labels;
  $("#labels").onchange = (e) => { state.labels = e.target.checked; store.set("labels", state.labels); applyLabels(); };

  document.querySelectorAll(".seg button").forEach((btn) => {
    btn.classList.toggle("on", btn.dataset.color === state.colorBy);
    btn.onclick = () => {
      state.colorBy = btn.dataset.color; store.set("colorBy", state.colorBy);
      document.querySelectorAll(".seg button").forEach((x) => x.classList.toggle("on", x === btn));
      rebuildColors(); render(); paintSwatches();
    };
  });

  $("#size").value = state.size;
  $("#size").oninput = (e) => { state.size = +e.target.value; store.set("size", state.size); render(); };
  $("#opacity").value = state.opacity;
  $("#opacity").oninput = (e) => { state.opacity = +e.target.value; store.set("opacity", state.opacity); render(); };

  // ------------------------------------------------------------------- legend
  const fmt = (n) => n >= 10000 ? Math.round(n / 1000).toLocaleString() + "k" : n.toLocaleString();
  const subOrigins = meta.subs.map(() => []);
  meta.origins.forEach((o, i) => subOrigins[o.sub].push(i));
  subOrigins.forEach((list) => list.sort((a, b) => meta.origins[b].dots - meta.origins[a].dots));
  const broadSubs = meta.broads.map(() => []);
  meta.subs.forEach((s, i) => broadSubs[s.broad].push(i));

  const tree = $("#tree");
  const nodes = []; // {el, input, origins:[...], kind, name, swatch, color()}

  function makeNode(kind, name, originIdx, colorFn) {
    const li = document.createElement("li");
    li.className = `node ${kind} collapsed`;
    const line = document.createElement("div");
    line.className = "line";
    const caret = document.createElement("button");
    caret.className = "caret"; caret.textContent = "▶"; caret.setAttribute("aria-label", "Expand " + name);
    caret.setAttribute("aria-expanded", "false");
    const input = document.createElement("input");
    input.type = "checkbox"; input.setAttribute("aria-label", "Show " + name);
    const sw = document.createElement("span");
    sw.className = "sw-dot";
    const label = document.createElement("span");
    label.className = "name"; label.textContent = name; label.title = name;
    const n = document.createElement("span");
    n.className = "n";
    n.textContent = fmt(originIdx.reduce((s, i) => s + meta.origins[i].dots, 0) * meta.dot);
    const only = document.createElement("button");
    only.className = "only"; only.textContent = "only";
    line.append(caret, input);
    if (kind !== "origin") line.append(sw);
    line.append(label, only, n);
    li.append(line);
    const node = { li, input, sw, origins: originIdx, kind, name, colorFn, caret };
    const toggleOpen = () => {
      const open = li.classList.toggle("collapsed") === false;
      caret.setAttribute("aria-expanded", String(open));
    };
    caret.onclick = toggleOpen;
    label.onclick = () => (kind === "origin" ? input.click() : toggleOpen());
    input.onchange = () => { originIdx.forEach((i) => (visible[i] = input.checked ? 1 : 0)); changed(); };
    only.onclick = () => { visible.fill(0); originIdx.forEach((i) => (visible[i] = 1)); changed(); };
    nodes.push(node);
    return node;
  }

  meta.broads.forEach((b, bi) => {
    const bOrigins = broadSubs[bi].flatMap((si) => subOrigins[si]);
    const bn = makeNode("broad", b.name, bOrigins, () => b.color);
    const ul = document.createElement("ul");
    broadSubs[bi].forEach((si) => {
      const s = meta.subs[si];
      const sn = makeNode("sub", s.name, subOrigins[si], () => (state.colorBy === "broad" ? b.color : s.color));
      const ul2 = document.createElement("ul");
      if (subOrigins[si].length > 1) {
        subOrigins[si].forEach((oi) => ul2.append(makeNode("origin", meta.origins[oi].name, [oi], null).li));
      } else {
        sn.caret.classList.add("hidden");
      }
      sn.li.append(ul2);
      ul.append(sn.li);
    });
    bn.li.append(ul);
    tree.append(bn.li);
  });

  function paintSwatches() { nodes.forEach((n) => n.colorFn && (n.sw.style.background = n.colorFn())); }
  function syncChecks() {
    nodes.forEach((n) => {
      const on = n.origins.filter((i) => visible[i]).length;
      n.input.checked = on === n.origins.length;
      n.input.indeterminate = on > 0 && on < n.origins.length;
    });
  }
  function changed() { syncChecks(); rebuildFilter(); render(); }
  paintSwatches();
  syncChecks();

  $("#all").onclick = () => { visible.fill(1); changed(); };
  $("#none").onclick = () => { visible.fill(0); changed(); };

  const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  $("#search").oninput = (e) => {
    const q = norm(e.target.value.trim());
    const lis = [...tree.querySelectorAll("li")];
    if (!q) {
      lis.forEach((li) => { li.classList.remove("nomatch"); if (!li.classList.contains("broad")) li.classList.add("collapsed"); });
      tree.querySelectorAll(".broad").forEach((li) => li.classList.add("collapsed"));
      return;
    }
    const match = new Set();
    nodes.forEach((n) => {
      if (norm(n.name).includes(q)) {
        let el = n.li;
        while (el && el !== tree) { if (el.tagName === "LI") match.add(el); el = el.parentElement; }
        n.li.querySelectorAll("li").forEach((c) => match.add(c));
      }
    });
    lis.forEach((li) => {
      li.classList.toggle("nomatch", !match.has(li));
      li.classList.toggle("collapsed", !match.has(li));
    });
  };

  // About: list origins that cannot be mapped at this level
  const um = meta.unmapped.slice().sort((a, b) => b.cma_responses - a.cma_responses);
  $("#unmapped").innerHTML = `<p class="unmapped"><strong>Not mapped</strong> (not published for small areas; Toronto CMA responses): ` +
    um.map((u) => `${u.name} ${u.cma_responses.toLocaleString()}`).join(", ") + ".</p>";

  // Mobile panel toggle
  $("#panel-toggle").onclick = () => {
    const closed = $("#panel").classList.toggle("closed");
    $("#panel-toggle").setAttribute("aria-expanded", String(!closed));
    $("#panel-toggle").textContent = closed ? "Layers" : "Hide";
  };
  if (window.innerWidth < 720) $("#panel-toggle").textContent = "Hide";
})();
