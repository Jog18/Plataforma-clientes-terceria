// Dashboard de calidad HBPO.
//
// Pide los registros limpios a /api/datos y calcula aquí KPIs, pareto,
// tendencias y tablas, para que los filtros respondan al instante.
//
// Seguridad: todo texto que viene de la hoja (partes, defectos, comentarios,
// seriales) se mete al DOM con textContent o como nodos; nunca con innerHTML.
// Las gráficas SVG se construyen con createElementNS por la misma razón.
//
// Reglas de negocio (ya aplicadas por el backend en cada fila):
//   scrap = nok, retrabajo = insp (todo lo inspeccionado se retrabaja),
//   ok = insp - nok.

(function () {
  "use strict";

  // ---- utilidades de DOM -------------------------------------------------

  var $ = function (id) { return document.getElementById(id); };
  var NS = "http://www.w3.org/2000/svg";

  // h("td", {class: "x"}, "texto", nodo, ...) -> elemento HTML con hijos.
  function h(tag, attrs) {
    var el = document.createElement(tag);
    aplicar(el, attrs);
    for (var i = 2; i < arguments.length; i++) agregar(el, arguments[i]);
    return el;
  }

  // s("rect", {x: 1, ...}, "texto") -> elemento SVG.
  function s(tag, attrs) {
    var el = document.createElementNS(NS, tag);
    aplicar(el, attrs);
    for (var i = 2; i < arguments.length; i++) agregar(el, arguments[i]);
    return el;
  }

  function aplicar(el, attrs) {
    if (!attrs) return;
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === undefined || v === null || v === false) return;
      if (k === "class") el.setAttribute("class", v);
      else if (k === "tip") el._tip = v;             // datos del tooltip (no HTML)
      else if (k === "onclick") el.addEventListener("click", v);
      else el.setAttribute(k, String(v));
    });
  }

  function agregar(el, hijo) {
    if (hijo === undefined || hijo === null || hijo === false) return;
    if (Array.isArray(hijo)) { hijo.forEach(function (x) { agregar(el, x); }); return; }
    el.appendChild(typeof hijo === "object" ? hijo : document.createTextNode(String(hijo)));
  }

  function vaciar(el) { while (el.firstChild) el.removeChild(el.firstChild); }
  function poner(el, hijo) { vaciar(el); agregar(el, hijo); }

  // ---- formato ------------------------------------------------------------

  var MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  var fmt = function (n) { return Math.round(n).toLocaleString("es-MX"); };
  var pct = function (n, dig) {
    if (dig === undefined) dig = 2;
    return (n * 100).toLocaleString("es-MX", { minimumFractionDigits: dig, maximumFractionDigits: dig }) + "%";
  };
  var mesCorto = function (m) { var p = m.split("-"); return MESES[+p[1] - 1] + " " + p[0].slice(2); };
  var mesLargo = function (m) {
    var p = m.split("-"), n = MESES[+p[1] - 1];
    return n.charAt(0).toUpperCase() + n.slice(1) + " " + p[0];
  };
  var fechaLbl = function (f) { var p = f.split("-"); return p[2] + "/" + p[1] + "/" + p[0]; };
  var diaCorto = function (f) { var p = f.split("-"); return p[2] + "/" + p[1]; };
  // Clave para ordenar por fecha y hora reales: "2026-10-02 08:21:42". Se rellena la
  // hora con ceros porque como texto "8:21:42" quedaría después de "13:03:42".
  var claveFechaHora = function (r) {
    var p = (r.hora || "").split(":").map(function (x) { return ("0" + x).slice(-2); });
    while (p.length < 3) p.push("00");
    return r.fechaReal + " " + p.slice(0, 3).join(":");
  };
  var ratio = function (a, b) { return b ? a / b : 0; };
  var suma = function (arr, k) { return arr.reduce(function (a, r) { return a + r[k]; }, 0); };

  function niceMax(v) {
    if (v <= 0) return 1;
    var p = Math.pow(10, Math.floor(Math.log10(v))), n = v / p;
    var m = n <= 1 ? 1 : n <= 1.2 ? 1.2 : n <= 1.5 ? 1.5 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 3 ? 3 : n <= 4 ? 4 : n <= 5 ? 5 : n <= 6 ? 6 : n <= 8 ? 8 : 10;
    return m * p;
  }

  // Barra con esquinas redondeadas arriba (dir "up") o a la derecha (dir "right").
  function barra(x, y, w, hh, r, dir) {
    if (hh <= 0 || w <= 0) return "";
    if (dir === "up") {
      r = Math.min(r, w / 2, hh);
      return "M" + x + "," + (y + hh) + " V" + (y + r) + " Q" + x + "," + y + " " + (x + r) + "," + y +
        " H" + (x + w - r) + " Q" + (x + w) + "," + y + " " + (x + w) + "," + (y + r) + " V" + (y + hh) + " Z";
    }
    r = Math.min(r, hh / 2, w);
    return "M" + x + "," + y + " H" + (x + w - r) + " Q" + (x + w) + "," + y + " " + (x + w) + "," + (y + r) +
      " V" + (y + hh - r) + " Q" + (x + w) + "," + (y + hh) + " " + (x + w - r) + "," + (y + hh) + " H" + x + " Z";
  }

  // ---- tooltip ------------------------------------------------------------

  var tip = $("tip");
  function mostrarTip(datos, e) {
    // datos = {titulo, filas: [[etiqueta, valor], ...]}
    vaciar(tip);
    agregar(tip, h("b", null, datos.titulo));
    datos.filas.forEach(function (f) {
      agregar(tip, h("div", { class: "row" }, h("span", null, f[0]), h("span", null, f[1])));
    });
    tip.style.display = "block";
    moverTip(e);
  }
  function moverTip(e) {
    var w = tip.offsetWidth, hh = tip.offsetHeight, x = e.clientX + 14, y = e.clientY + 14;
    if (x + w > innerWidth - 8) x = e.clientX - w - 14;
    if (y + hh > innerHeight - 8) y = e.clientY - hh - 14;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  }
  function ocultarTip() { tip.style.display = "none"; }
  function conTip(el) {
    el.addEventListener("mouseenter", function (e) { mostrarTip(el._tip, e); });
    el.addEventListener("mousemove", moverTip);
    el.addEventListener("mouseleave", ocultarTip);
    return el;
  }

  // ---- estado ---------------------------------------------------------------

  var D = null;        // paquete de /api/datos
  var ROWS = [];       // filas con campos derivados
  var DEF = [];        // catálogo de defectos
  var TURNOS = [];
  var PARTES = [];
  var meses = [];
  var state = { anio: "", mes: "", dia: "", turno: "", parte: "", def: "" };
  var detLimit = 100;

  function estado(texto, tipo) {
    var el = $("estado");
    el.textContent = texto || "";
    el.className = "estado" + (texto ? " visible" : "") + (tipo ? " " + tipo : "");
  }

  // ---- carga de datos ---------------------------------------------------------

  // forzar = true (botón Actualizar): el servidor lee la hoja de Google de nuevo
  // en lugar de usar su copia de hasta 5 minutos. La recarga automática no fuerza.
  function cargar(forzar) {
    estado(forzar ? "Leyendo la hoja de Google…" : "Cargando datos de la hoja…");
    $("btnActualizar").disabled = true;
    return fetch(forzar ? "/api/datos?refrescar=1" : "/api/datos", { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        if (r.status === 401) { window.location.replace("/login"); return null; }
        if (!r.ok) {
          return r.json().catch(function () { return {}; }).then(function (j) {
            throw new Error(typeof j.detail === "string" ? j.detail : "El servidor respondió " + r.status);
          });
        }
        return r.json();
      })
      .then(function (paquete) {
        if (!paquete) return;
        preparar(paquete);
        estado("");
        render();
      })
      .catch(function (err) {
        estado("No se pudieron cargar los datos: " + err.message, "error");
      })
      .then(function () { $("btnActualizar").disabled = false; });
  }

  function preparar(paquete) {
    D = paquete;
    DEF = paquete.defectos || [];
    TURNOS = paquete.turnos || [];
    PARTES = paquete.partes || [];
    var idx = {}; DEF.forEach(function (d, i) { idx[d] = i; });

    ROWS = (paquete.filas || []).map(function (r) {
      // d[i] = piezas con el defecto i en este registro.
      var d = new Array(DEF.length).fill(0);
      (r.defectos || []).forEach(function (x) {
        var i = idx[x.defecto]; if (i !== undefined) d[i] += x.cantidad || 0;
      });
      var insp = r.insp || 0, nok = r.nok || 0;
      // "fecha" es el día de producción (de 6:00 a 5:59): con él se agrupa y
      // filtra todo el tablero. "fechaReal" es la fecha de captura de la hoja.
      var dia = r.dia_produccion || r.fecha;
      return {
        id: r.id, fecha: dia, fechaReal: r.fecha, anio: dia.slice(0, 4), mes: dia.slice(0, 7),
        hora: r.hora || "", turno: r.turno || "", parte: r.parte || "", serial: r.serial || "",
        insp: insp, nok: nok, scrap: r.scrap, rw: r.retrabajo, ok: r.ok,
        comentarios: r.comentarios || "", defectos: r.defectos || [], d: d,
        val: nok > insp ? "REVISAR" : (insp === 0 ? "SIN INSPECCIÓN" : "OK")
      };
    });

    meses = unicos(ROWS.map(function (r) { return r.mes; }));
    llenarFiltros();

    var titulo = "TABLERO DE CALIDAD — INSPECCIÓN " + (paquete.cliente || "");
    $("titulo").textContent = titulo; document.title = "Tablero de Calidad — " + (paquete.cliente || "");
    if (ROWS.length) {
      var f0 = ROWS[0].fecha, f1 = ROWS[ROWS.length - 1].fecha;
      ROWS.forEach(function (r) { if (r.fecha < f0) f0 = r.fecha; if (r.fecha > f1) f1 = r.fecha; });
      poner($("subtitulo"), ["Periodo: ", h("b", null, fechaLbl(f0)), " al ", h("b", null, fechaLbl(f1)),
        "  |  Registros: ", h("b", null, fmt(ROWS.length)),
        h("span", { class: "solo-pantalla" }, "  |  Fuente: Google Sheets en vivo"),
        h("span", { class: "solo-impresion" }, "  |  Consultado: ", h("b", { id: "consultado" }, ahoraLbl()))]);
      var ultimo = ROWS.reduce(function (a, r) { return claveFechaHora(r) > claveFechaHora(a) ? r : a; }, ROWS[0]);
      $("pieIzq").textContent = "Último registro " + fechaLbl(ultimo.fechaReal) + " " + ultimo.hora + " · día de 6:00 a 5:59 · datos leídos " +
        (paquete.generado || "").replace("T", " ").slice(0, 16) +
        (paquete.descartados ? " · " + fmt(paquete.descartados) + " filas descartadas por falta de ID o fecha" : "");
    } else {
      $("subtitulo").textContent = "La hoja no tiene registros todavía.";
      $("pieIzq").textContent = "";
    }
  }

  function unicos(arr) {
    var v = {}; arr.forEach(function (x) { if (x) v[x] = true; });
    return Object.keys(v).sort();
  }

  // ---- filtros -----------------------------------------------------------------

  function opciones(select, valores, etiqueta) {
    while (select.options.length > 1) select.remove(1);
    valores.forEach(function (v) { select.add(new Option(etiqueta ? etiqueta(v) : v, v)); });
  }

  function llenarFiltros() {
    opciones($("fAnio"), unicos(ROWS.map(function (r) { return r.anio; })));
    opciones($("fMes"), meses, mesLargo);
    opciones($("fTurno"), TURNOS);
    opciones($("fDef"), DEF.map(function (_, i) { return String(i); }), function (i) { return DEF[+i]; });
    var dl = $("partesList"); vaciar(dl);
    PARTES.forEach(function (p) { dl.appendChild(h("option", { value: p })); });
  }

  ["fAnio", "fMes", "fTurno", "fDef"].forEach(function (id) {
    $(id).addEventListener("change", function () {
      state[id.slice(1).toLowerCase()] = $(id).value;
      if (id === "fMes" || id === "fAnio") state.dia = "";
      render();
    });
  });
  $("fParte").addEventListener("change", function () { state.parte = $("fParte").value.trim(); render(); });
  $("fParte").addEventListener("input", function () { if ($("fParte").value === "") { state.parte = ""; render(); } });
  $("btnReset").addEventListener("click", function () { limpiarFiltros(); render(); });
  function limpiarFiltros() { Object.keys(state).forEach(function (k) { state[k] = ""; }); }

  function setFilter(k, v) {
    state[k] = (state[k] === v ? "" : v);
    if (k === "mes" && state.mes) { state.anio = ""; state.dia = ""; }
    if (k === "dia" && state.dia) { state.mes = ""; state.anio = ""; }
    render();
  }

  function filtrados() {
    var parteQ = state.parte.toUpperCase();
    return ROWS.filter(function (r) {
      return (!state.anio || r.anio === state.anio) && (!state.mes || r.mes === state.mes) &&
        (!state.dia || r.fecha === state.dia) && (!state.turno || r.turno === state.turno) &&
        (!parteQ || r.parte.toUpperCase().indexOf(parteQ) !== -1) &&
        (state.def === "" || r.d[+state.def] > 0);
    });
  }

  function sincronizarControles() {
    $("fAnio").value = state.anio; $("fMes").value = state.mes; $("fTurno").value = state.turno; $("fDef").value = state.def;
    if (document.activeElement !== $("fParte")) $("fParte").value = state.parte;
    var chips = [];
    var chip = function (k, texto) {
      chips.push(h("span", { class: "chip" }, texto,
        h("button", { type: "button", title: "Quitar", onclick: function () { state[k] = ""; render(); } }, "×")));
    };
    if (state.anio) chip("anio", "Año: " + state.anio);
    if (state.mes) chip("mes", "Mes: " + mesLargo(state.mes));
    if (state.dia) chip("dia", "Día: " + fechaLbl(state.dia));
    if (state.turno) chip("turno", "Turno: " + state.turno);
    if (state.parte) chip("parte", "Parte: " + state.parte);
    if (state.def !== "") chip("def", "Defecto: " + DEF[+state.def]);
    poner($("chips"), chips.length ? chips : h("span", { class: "hint" }, "Sin filtros: se muestran todos los registros de la hoja."));
  }

  // ---- piezas comunes de gráficas ------------------------------------------------

  function lienzo(W, H) { return s("svg", { viewBox: "0 0 " + W + " " + H }); }
  function rejilla(svg, mL, cw, mT, ch, etiqueta) {
    for (var g = 0; g <= 4; g++) {
      var y = mT + ch - ch * g / 4;
      svg.appendChild(s("line", { x1: mL, x2: mL + cw, y1: y, y2: y, stroke: "var(--grid)" }));
      svg.appendChild(s("text", { x: mL - 6, y: y + 4, "text-anchor": "end", class: "lbl" }, etiqueta(g / 4)));
    }
  }
  function tabla(encabezados, filas, total) {
    var thead = h("thead", null, h("tr", null, encabezados.map(function (e) { return h("th", null, e); })));
    var tbody = h("tbody", null, filas);
    if (total) tbody.appendChild(h("tr", { class: "total" }, total.map(function (c) { return h("td", null, c); })));
    return h("table", null, thead, tbody);
  }
  function filaClick(celdas, activa, onclick) {
    return h("tr", { class: "clickable" + (activa ? " active" : ""), onclick: onclick },
      celdas.map(function (c) { return typeof c === "object" && c && c.nodeType ? c : h("td", null, c); }));
  }
  function vacio(texto) { return h("div", { class: "empty" }, texto); }

  // ---- KPIs ---------------------------------------------------------------------

  function renderKpis(F) {
    var insp = suma(F, "insp"), ok = suma(F, "ok"), scrap = suma(F, "scrap"), rw = suma(F, "rw");
    var pS = ratio(scrap, insp), ftt = ratio(ok, insp);
    var porDef = DEF.map(function (n, i) { return [n, F.reduce(function (a, r) { return a + r.d[i]; }, 0)]; })
      .sort(function (a, b) { return b[1] - a[1]; });
    var top = porDef[0] || ["—", 0];
    var partes = unicos(F.map(function (r) { return r.parte; })).length;
    var rev = F.filter(function (r) { return r.val === "REVISAR"; }).length;
    var ultimo = F.length ? F.reduce(function (a, r) { return claveFechaHora(r) > claveFechaHora(a) ? r : a; }, F[0]) : null;

    var k = [
      ["Piezas inspeccionadas", fmt(insp), fmt(F.length) + " registros", "hero accent"],
      ["Piezas OK", fmt(ok), "", ""],
      ["Scrap (pzs NOK)", fmt(scrap), "Piezas rechazadas", "accent"],
      ["% Scrap", pct(pS), "", ""],
      ["PPM Scrap", fmt(pS * 1e6), "Partes por millón", ""],
      ["FTT (% OK)", pct(ftt), "First Time Through", ""],
      ["Defecto principal", top[0], "Más piezas en el periodo", "small"],
      ["Pzs defecto principal", fmt(top[1]), scrap ? pct(ratio(top[1], scrap), 1) + " del scrap" : "—", ""],
      ["N° de partes distintas", fmt(partes), "", ""],
      ["Filas a revisar", fmt(rev), "", rev ? "warn" : ""],
      ["Último registro", ultimo ? fechaLbl(ultimo.fechaReal) : "—", ultimo ? (ultimo.hora + " · turno " + ultimo.turno) : "", "small"]
    ];
    poner($("kpis"), k.map(function (x) {
      var small = x[3].indexOf("small") !== -1;
      return h("div", { class: "kpi " + x[3].replace("small", "") },
        h("div", { class: "l" }, x[0]), h("div", { class: "v" + (small ? " small" : "") }, x[1]), h("div", { class: "d" }, x[2]));
    }));
    return { insp: insp, ok: ok, scrap: scrap, rw: rw };
  }

  // ---- Pareto -------------------------------------------------------------------

  function renderPareto(F) {
    var data = DEF.map(function (n, i) {
      return { n: n, i: i, v: F.reduce(function (a, r) { return a + r.d[i]; }, 0) };
    }).sort(function (a, b) { return b.v - a.v; });
    var total = suma(data, "v"), acc = 0;
    data.forEach(function (d) { acc += d.v; d.acc = ratio(acc, total); d.p = ratio(d.v, total); });
    var shown = data.filter(function (d) { return d.v > 0; });

    var W = 620, H = 300, mL = 40, mR = 44, mT = 14, mB = 78, cw = W - mL - mR, ch = H - mT - mB;
    if (!shown.length) {
      poner($("chPareto"), vacio("Sin defectos en la selección"));
    } else {
      var max = niceMax(shown[0].v), step = cw / shown.length, bw = Math.min(24, step * 0.7);
      var svg = lienzo(W, H);
      rejilla(svg, mL, cw, mT, ch, function (f) { return fmt(max * f); });
      for (var g = 0; g <= 4; g++) svg.appendChild(s("text", { x: mL + cw + 8, y: mT + ch - ch * g / 4 + 4, class: "lbl" }, (25 * g) + "%"));
      var pts = [];
      shown.forEach(function (d, j) {
        var x = mL + step * j + (step - bw) / 2, hh = ch * d.v / max, y = mT + ch - hh;
        var activa = state.def === String(d.i);
        svg.appendChild(conTip(s("path", {
          d: barra(x, y, bw, hh, 4, "up"), fill: activa ? "var(--s7)" : "var(--s1)", style: "cursor:pointer",
          onclick: function () { setFilter("def", String(d.i)); },
          tip: { titulo: d.n, filas: [["Piezas", fmt(d.v)], ["% del total", pct(d.p, 1)], ["% acumulado", pct(d.acc, 1)]] }
        })));
        if (j < 3) svg.appendChild(s("text", { x: x + bw / 2, y: y - 5, "text-anchor": "middle", class: "lbl strong" }, fmt(d.v)));
        var lx = x + bw / 2, lbl = d.n.length > 14 ? d.n.slice(0, 13) + "…" : d.n;
        svg.appendChild(s("text", { x: lx, y: mT + ch + 10, transform: "rotate(-40 " + lx + " " + (mT + ch + 10) + ")", "text-anchor": "end", class: "lbl chica" }, lbl));
        pts.push([x + bw / 2, mT + ch - ch * d.acc]);
      });
      svg.appendChild(s("path", { d: "M" + pts.map(function (p) { return p.join(","); }).join(" L"), fill: "none", stroke: "var(--s7)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
      pts.forEach(function (p) { svg.appendChild(s("circle", { cx: p[0], cy: p[1], r: 4, fill: "var(--s7)", stroke: "var(--surface)", "stroke-width": 2 })); });
      var y80 = mT + ch * 0.2;
      svg.appendChild(s("line", { x1: mL, x2: mL + cw, y1: y80, y2: y80, stroke: "var(--s7)", "stroke-dasharray": "3 4", opacity: 0.5 }));
      svg.appendChild(s("text", { x: mL + 4, y: y80 - 4, class: "lbl chica" }, "80%"));
      poner($("chPareto"), svg);
    }
    poner($("tbPareto"), tabla(["Defecto", "Piezas", "% del total", "% acumulado"],
      data.map(function (d) {
        return filaClick([d.n, fmt(d.v), pct(d.p, 1), pct(d.acc, 1)], state.def === String(d.i), function () { setFilter("def", String(d.i)); });
      }), ["TOTAL", fmt(total), "100.0%", ""]));
  }

  // ---- Tendencias (por día y por mes) ---------------------------------------------

  function serie(F, claves, clave) {
    var by = {}; claves.forEach(function (k) { by[k] = { k: k, insp: 0, scrap: 0, n: 0 }; });
    F.forEach(function (r) { var b = by[r[clave]]; if (b) { b.insp += r.insp; b.scrap += r.scrap; b.n++; } });
    return claves.map(function (k) { var b = by[k]; b.pS = ratio(b.scrap, b.insp); return b; });
  }

  function graficaTendencia(contenedor, data, etiqueta, etiquetaLarga, filtro, activo) {
    if (!data.length) { poner(contenedor, vacio("Sin registros")); return; }
    var W = 620, H = 300, mL = 48, mR = 24, mT = 14, mB = 34, cw = W - mL - mR, ch = H - mT - mB;
    var maxP = niceMax(Math.max(0.01, Math.max.apply(null, data.map(function (d) { return d.pS; }))) * 1.05);
    var maxI = niceMax(Math.max(1, Math.max.apply(null, data.map(function (d) { return d.insp; }))));
    var n = data.length, step = cw / Math.max(n, 1);
    var X = function (j) { return mL + step * j + step / 2; }, Y = function (v) { return mT + ch - ch * v / maxP; };
    var svg = lienzo(W, H);
    rejilla(svg, mL, cw, mT, ch, function (f) { return pct(maxP * f, maxP >= 0.1 ? 0 : 1); });
    data.forEach(function (d, j) {
      var bw = Math.min(24, step * 0.6), hh = ch * d.insp / maxI;
      svg.appendChild(s("rect", { x: X(j) - bw / 2, y: mT + ch - hh, width: bw, height: hh, fill: activo === d.k ? "var(--s1-soft)" : "var(--grid)", rx: 3 }));
    });
    if (n >= 2) svg.appendChild(s("path", { d: "M" + data.map(function (d, j) { return X(j) + "," + Y(d.pS); }).join(" L"), fill: "none", stroke: "var(--s1)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    var cada = n <= 12 ? 1 : Math.ceil(n / 12);
    data.forEach(function (d, j) {
      svg.appendChild(s("circle", { cx: X(j), cy: Y(d.pS), r: 4, fill: "var(--s1)", stroke: "var(--surface)", "stroke-width": 2 }));
      if (j % cada === 0 || j === n - 1) svg.appendChild(s("text", { x: X(j), y: mT + ch + 16, "text-anchor": "middle", class: "lbl chica" + (activo === d.k ? " strong" : "") }, etiqueta(d.k)));
      svg.appendChild(conTip(s("rect", {
        x: X(j) - step / 2, y: mT, width: step, height: ch, fill: "transparent", style: "cursor:pointer",
        onclick: function () { setFilter(filtro, d.k); },
        tip: { titulo: etiquetaLarga(d.k), filas: [["Inspeccionadas", fmt(d.insp)], ["Scrap", fmt(d.scrap) + " (" + pct(d.pS) + ")"], ["Registros", fmt(d.n)]] }
      })));
    });
    poner(contenedor, svg);
  }

  function tablaTendencia(contenedor, data, etiquetaLarga, filtro, activo) {
    var T = { insp: suma(data, "insp"), scrap: suma(data, "scrap"), n: suma(data, "n") };
    poner(contenedor, tabla(["Periodo", "Registros", "Inspeccionadas", "Scrap", "% Scrap"],
      data.map(function (d) {
        return filaClick([etiquetaLarga(d.k), fmt(d.n), fmt(d.insp), fmt(d.scrap), pct(d.pS)], activo === d.k, function () { setFilter(filtro, d.k); });
      }), ["TOTAL", fmt(T.n), fmt(T.insp), fmt(T.scrap), pct(ratio(T.scrap, T.insp))]));
  }

  function renderDia(F) {
    var dias = unicos(F.map(function (r) { return r.fecha; }));
    if (!state.dia) dias = dias.slice(-31);
    var data = serie(F, dias, "fecha");
    graficaTendencia($("chDia"), data, diaCorto, fechaLbl, "dia", state.dia);
    tablaTendencia($("tbDia"), data.slice().reverse(), fechaLbl, "dia", state.dia);
  }

  function renderMes(F) {
    var ms = state.mes ? [state.mes] : meses.filter(function (m) { return !state.anio || m.indexOf(state.anio) === 0; });
    var data = serie(F, ms, "mes");
    graficaTendencia($("chMes"), data, mesCorto, mesLargo, "mes", state.mes);
    tablaTendencia($("tbMes"), data, mesLargo, "mes", state.mes);
  }

  // ---- Turno ----------------------------------------------------------------------

  function renderTurno(F) {
    var data = TURNOS.map(function (tn) {
      var R = F.filter(function (r) { return r.turno === tn; });
      var insp = suma(R, "insp"), scrap = suma(R, "scrap");
      return { tn: tn, insp: insp, scrap: scrap, pS: ratio(scrap, insp), n: R.length };
    });
    var shown = data.filter(function (d) { return d.n > 0; });
    if (!shown.length) {
      poner($("chTurno"), vacio("Sin registros"));
    } else {
      var W = 620, H = 240, mL = 48, mR = 16, mT = 14, mB = 30, cw = W - mL - mR, ch = H - mT - mB;
      var max = niceMax(Math.max(0.01, Math.max.apply(null, shown.map(function (d) { return d.pS; }))) * 1.05);
      var step = cw / shown.length, bw = Math.min(40, step * 0.4);
      var svg = lienzo(W, H);
      rejilla(svg, mL, cw, mT, ch, function (f) { return pct(max * f, max >= 0.1 ? 0 : 1); });
      shown.forEach(function (d, j) {
        var cx = mL + step * j + step / 2, hh = ch * d.pS / max, activa = state.turno === d.tn;
        svg.appendChild(conTip(s("path", {
          d: barra(cx - bw / 2, mT + ch - hh, bw, hh, 4, "up"), fill: activa ? "var(--s7)" : "var(--s1)", style: "cursor:pointer",
          onclick: function () { setFilter("turno", d.tn); },
          tip: { titulo: "Turno " + d.tn, filas: [["Inspeccionadas", fmt(d.insp)], ["Scrap", fmt(d.scrap) + " (" + pct(d.pS) + ")"], ["Registros", fmt(d.n)]] }
        })));
        if (d.pS > 0) svg.appendChild(s("text", { x: cx, y: mT + ch - hh - 5, "text-anchor": "middle", class: "lbl chica" }, pct(d.pS, 1)));
        svg.appendChild(s("text", { x: cx, y: mT + ch + 16, "text-anchor": "middle", class: "lbl" + (activa ? " strong" : "") }, d.tn));
      });
      poner($("chTurno"), svg);
    }
    var T = { insp: suma(data, "insp"), scrap: suma(data, "scrap") };
    poner($("tbTurno"), tabla(["Turno", "Registros", "Inspeccionadas", "Scrap", "% Scrap"],
      data.map(function (d) {
        return filaClick([d.tn, fmt(d.n), fmt(d.insp), fmt(d.scrap), pct(d.pS)], state.turno === d.tn, function () { setFilter("turno", d.tn); });
      }), ["TOTAL", fmt(F.length), fmt(T.insp), fmt(T.scrap), pct(ratio(T.scrap, T.insp))]));
  }

  // ---- Top 15 partes ---------------------------------------------------------------

  function renderTop(F, tot) {
    var by = {};
    F.forEach(function (r) { var b = by[r.parte] || (by[r.parte] = { p: r.parte, insp: 0, scrap: 0, n: 0 }); b.insp += r.insp; b.scrap += r.scrap; b.n++; });
    var data = Object.keys(by).map(function (k) { var b = by[k]; b.pS = ratio(b.scrap, b.insp); b.share = ratio(b.scrap, tot.scrap); return b; })
      .sort(function (a, b) { return b.scrap - a.scrap || b.insp - a.insp; }).slice(0, 15);
    if (!data.length) {
      poner($("chTop"), vacio("Sin registros"));
    } else {
      var rowH = 22, W = 620, mL = 150, mR = 70, mT = 6, H = mT + rowH * data.length + 6, cw = W - mL - mR;
      var max = niceMax(Math.max(1, Math.max.apply(null, data.map(function (d) { return d.scrap; }))));
      var svg = lienzo(W, H);
      for (var g = 1; g <= 4; g++) { var x = mL + cw * g / 4; svg.appendChild(s("line", { x1: x, x2: x, y1: mT, y2: H - 6, stroke: "var(--grid)" })); }
      data.forEach(function (d, j) {
        var y = mT + rowH * j + 4, w = cw * d.scrap / max, activa = state.parte === d.p;
        svg.appendChild(conTip(s("rect", {
          x: 0, y: y - 4, width: W, height: rowH, fill: activa ? "var(--s1-soft)" : "transparent", rx: 4, style: "cursor:pointer",
          onclick: function () { setFilter("parte", d.p); },
          tip: { titulo: d.p, filas: [["Inspeccionadas", fmt(d.insp)], ["Scrap", fmt(d.scrap) + " (" + pct(d.pS) + ")"], ["% del scrap total", pct(d.share, 1)], ["Registros", fmt(d.n)]] }
        })));
        svg.appendChild(s("text", { x: mL - 8, y: y + 11, "text-anchor": "end", class: "lbl" + (activa ? " strong" : ""), style: "pointer-events:none" }, d.p));
        svg.appendChild(s("path", { d: barra(mL, y, w, 14, 4, "right"), fill: activa ? "var(--s7)" : "var(--s1)", style: "pointer-events:none" }));
        svg.appendChild(s("text", { x: mL + w + 6, y: y + 11, class: "lbl strong", style: "pointer-events:none" }, fmt(d.scrap) + " · " + pct(d.pS, 1)));
      });
      poner($("chTop"), svg);
    }
    poner($("tbTop"), tabla(["#", "Número de parte", "Registros", "Inspeccionadas", "Scrap", "% Scrap", "% del scrap total"],
      data.map(function (d, j) {
        return filaClick([String(j + 1), h("td", { class: "izq" }, d.p), fmt(d.n), fmt(d.insp), fmt(d.scrap), pct(d.pS), pct(d.share, 1)],
          state.parte === d.p, function () { setFilter("parte", d.p); });
      })));
  }

  // ---- Validación --------------------------------------------------------------------

  function renderVal(F) {
    var cats = [["OK", "var(--s3)", "ok"], ["REVISAR", "var(--warn)", "rev"], ["SIN INSPECCIÓN", "#9ca3af", "sin"]];
    var data = cats.map(function (c) { return { n: c[0], c: c[1], cls: c[2], v: F.filter(function (r) { return r.val === c[0]; }).length }; });
    var total = F.length || 1, W = 620, H = 54, x = 0;
    var svg = lienzo(W, H);
    data.forEach(function (d) {
      var w = W * d.v / total;
      if (w > 0) svg.appendChild(conTip(s("rect", {
        x: x + (x ? 1 : 0), y: 8, width: Math.max(0, w - (x ? 1 : 0)), height: 20, fill: d.c, rx: 3,
        tip: { titulo: d.n, filas: [["Registros", fmt(d.v) + " (" + pct(d.v / total, 1) + ")"]] }
      })));
      x += w;
    });
    svg.appendChild(s("text", { x: 0, y: 46, class: "lbl" }, fmt(F.length) + " registros · OK " + pct(data[0].v / total, 1) + " · Revisar " + fmt(data[1].v) + " · Sin inspección " + fmt(data[2].v)));
    poner($("chVal"), svg);

    var rev = F.filter(function (r) { return r.val !== "OK"; }).slice(0, 200);
    var filas = rev.length ? rev.map(function (r) {
      return h("tr", null, h("td", null, fechaLbl(r.fechaReal)), h("td", null, r.hora), h("td", null, r.turno), h("td", { class: "izq" }, r.parte),
        h("td", null, fmt(r.insp)), h("td", null, fmt(r.nok)), h("td", null, pill(r.val)));
    }) : [h("tr", null, h("td", { colspan: 7, style: "text-align:center;color:var(--ink-3)" }, "Todas las filas de la selección están OK"))];
    poner($("tbVal"), tabla(["Fecha", "Hora", "Turno", "Parte", "Inspec.", "NOK", "Estado"], filas));
  }

  function pill(val) {
    return h("span", { class: "pill " + (val === "OK" ? "ok" : val === "REVISAR" ? "rev" : "sin") }, val);
  }

  // ---- Detalle ------------------------------------------------------------------------

  function renderDet(F) {
    var rows = F.slice().sort(function (a, b) { return claveFechaHora(b).localeCompare(claveFechaHora(a)); }).slice(0, detLimit);
    $("detCap").textContent = fmt(F.length) + " registros en la selección · mostrando " + fmt(rows.length) + " (más recientes primero)";
    $("btnMore").style.display = F.length > detLimit ? "" : "none";
    var filas = rows.map(function (r) {
      var defs = r.defectos.map(function (d) { return d.defecto + (d.cantidad > 1 ? " ×" + d.cantidad : ""); }).join(", ");
      return h("tr", null,
        h("td", null, fechaLbl(r.fechaReal)), h("td", null, r.hora), h("td", null, r.turno),
        h("td", { class: "izq" }, r.parte), h("td", { class: "izq" }, r.serial),
        h("td", null, fmt(r.insp)), h("td", null, fmt(r.nok)), h("td", null, fmt(r.ok)), h("td", null, pct(ratio(r.nok, r.insp))),
        h("td", { class: "texto" }, defs), h("td", { class: "texto" }, r.comentarios), h("td", null, pill(r.val)));
    });
    poner($("tbDet"), tabla(["Fecha", "Hora", "Turno", "Número de parte", "Serial", "Inspeccionadas", "NOK (scrap)", "Piezas OK", "% Scrap", "Defectos", "Comentarios", "Validación"], filas));
  }
  $("btnMore").addEventListener("click", function () { detLimit += 200; renderDet(filtrados()); });

  // ---- CSV ------------------------------------------------------------------------------

  function csvCelda(v) {
    var t = String(v === undefined || v === null ? "" : v);
    return /[",\n;]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
  }
  // El CSV se pide por un solo día o por un rango de días. Opcionalmente se
  // aplican también los filtros del tablero que no son de fecha.
  function filasCsv(desde, hasta, conFiltros) {
    var parteQ = state.parte.toUpperCase();
    return ROWS.filter(function (r) {
      if (r.fecha < desde || r.fecha > hasta) return false;
      if (!conFiltros) return true;
      return (!state.turno || r.turno === state.turno) &&
        (!parteQ || r.parte.toUpperCase().indexOf(parteQ) !== -1) &&
        (state.def === "" || r.d[+state.def] > 0);
    });
  }
  function descargarCsv(F, nombre) {
    var head = ["ID", "DIA PRODUCCION", "FECHA", "HORA", "TURNO", "NUMERO DE PARTE", "SERIAL", "PIEZAS INSP", "PIEZAS NOK", "PIEZAS OK", "% SCRAP"].concat(DEF, ["COMENTARIOS", "VALIDACION"]);
    var lines = [head.map(csvCelda).join(",")];
    F.forEach(function (r) {
      lines.push([r.id, r.fecha, r.fechaReal, r.hora, r.turno, r.parte, r.serial, r.insp, r.nok, r.ok, ratio(r.nok, r.insp).toFixed(4)]
        .concat(r.d, [r.comentarios, r.val]).map(csvCelda).join(","));
    });
    var blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = nombre;
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }
  function modoCsv() { return document.querySelector('input[name="csvModo"]:checked').value; }
  function ajustarModoCsv() {
    var rango = modoCsv() === "rango";
    $("csvHastaCaja").hidden = !rango;
    $("csvDesdeLbl").textContent = rango ? "Desde" : "Día";
    $("csvAviso").hidden = true;
  }
  Array.prototype.forEach.call(document.querySelectorAll('input[name="csvModo"]'), function (el) {
    el.addEventListener("change", ajustarModoCsv);
  });
  $("btnCsv").addEventListener("click", function () {
    if (!ROWS.length) return;
    var f0 = ROWS[0].fecha, f1 = ROWS[0].fecha;
    ROWS.forEach(function (r) { if (r.fecha < f0) f0 = r.fecha; if (r.fecha > f1) f1 = r.fecha; });
    ["csvDesde", "csvHasta"].forEach(function (id) { $(id).min = f0; $(id).max = f1; });
    if (!$("csvDesde").value) $("csvDesde").value = state.dia || f1;
    if (!$("csvHasta").value) $("csvHasta").value = f1;
    ajustarModoCsv();
    $("dlgCsv").showModal();
  });
  $("csvCancelar").addEventListener("click", function () { $("dlgCsv").close(); });
  $("formCsv").addEventListener("submit", function (e) {
    var rango = modoCsv() === "rango";
    var desde = $("csvDesde").value, hasta = rango ? $("csvHasta").value : desde;
    var aviso = "";
    if (!desde || !hasta) aviso = "Elige las fechas.";
    else if (hasta < desde) aviso = "La fecha final es anterior a la inicial.";
    var F = aviso ? [] : filasCsv(desde, hasta, $("csvFiltros").checked);
    if (!aviso && !F.length) aviso = "No hay registros en esas fechas.";
    if (aviso) {
      e.preventDefault();
      $("csvAviso").textContent = aviso; $("csvAviso").hidden = false;
      return;
    }
    var cliente = D && D.cliente ? D.cliente.toLowerCase() : "datos";
    descargarCsv(F, "inspeccion_" + cliente + "_" + desde + (rango && hasta !== desde ? "_a_" + hasta : "") + ".csv");
  });

  // ---- botones de cabecera ----------------------------------------------------------------

  // En el reporte impreso, "Consultado" lleva la fecha y hora en que se genera.
  function ahoraLbl() {
    var d = new Date(), dos = function (n) { return (n < 10 ? "0" : "") + n; };
    return dos(d.getDate()) + "/" + dos(d.getMonth() + 1) + "/" + d.getFullYear() + " " + dos(d.getHours()) + ":" + dos(d.getMinutes());
  }
  window.addEventListener("beforeprint", function () {
    var c = $("consultado");
    if (c) c.textContent = ahoraLbl();
  });
  $("btnImprimir").addEventListener("click", function () { window.print(); });
  $("btnActualizar").addEventListener("click", function () { cargar(true); });
  $("btnSalir").addEventListener("click", function () {
    fetch("/api/logout", { method: "POST", credentials: "same-origin" })
      .catch(function () { })
      .then(function () { window.location.replace("/login"); });
  });

  fetch("/api/yo", { credentials: "same-origin" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (yo) { if (yo) $("quien").textContent = yo.usuario; })
    .catch(function () { });

  // ---- render --------------------------------------------------------------------------------

  function render() {
    sincronizarControles();
    var F = filtrados();
    var tot = renderKpis(F);
    renderPareto(F); renderDia(F); renderMes(F); renderTurno(F); renderTop(F, tot); renderVal(F);
    detLimit = 100; renderDet(F);
  }

  cargar(false);
  // La caché del backend dura 5 minutos; recargar en ese ritmo mantiene el tablero al día.
  setInterval(function () { cargar(false); }, 5 * 60 * 1000);
})();
