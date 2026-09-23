/*
 * Pantalla de juego (Alpine.js).
 * El servidor valida cada jugada: la solución nunca llega al navegador.
 * Las peticiones se envían en fila, una detrás de otra, y el estado que
 * devuelve el servidor manda sobre el local.
 */
function juegoSudoku(datos) {
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]").value;
  const dadas = [...datos.puzzle].map((v) => v !== "0");

  return {
    tablero: [...datos.partida.tablero].map(Number),
    notas: datos.partida.notas || {},
    errores: datos.partida.errores,
    vidas: datos.partida.vidas,
    pistas: datos.partida.pistas,
    segundos: datos.partida.segundos,
    estado: datos.partida.estado,
    vidasTotales: datos.vidasTotales,
    recordAnterior: datos.recordAnterior,
    sel: 0,
    modoNotas: false,
    pausado: false,
    finAbierto: false,
    error: null, // { celda, valor }
    acierto: null,
    aviso: "",
    historial: [],
    cola: Promise.resolve(),

    init() {
      const primeraVacia = this.tablero.findIndex((v) => v === 0);
      this.sel = primeraVacia >= 0 ? primeraVacia : 40;
      this.finAbierto = this.estado !== "en_curso";
      setInterval(() => this.tic(), 1000);
      setInterval(() => this.guardarTiempo(), 20000);
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) this.guardarTiempo(true);
      });
      window.addEventListener("keydown", (e) => this.teclado(e));
    },

    // ---------- Derivados ----------
    get fila() { return Math.floor(this.sel / 9); },
    get col() { return this.sel % 9; },
    get valorSel() {
      if (this.error && this.error.celda === this.sel) return 0;
      return this.tablero[this.sel];
    },
    get enCurso() { return this.estado === "en_curso"; },
    get reloj() { return formatoTiempo(this.segundos); },
    get cuenta() {
      const c = Array(10).fill(0);
      this.tablero.forEach((v) => v && c[v]++);
      return c;
    },
    get nuevoRecord() {
      return this.estado === "ganada" && (this.recordAnterior == null || this.segundos < this.recordAnterior);
    },

    clases(i) {
      const f = Math.floor(i / 9), c = i % 9;
      const zona = f === this.fila || c === this.col ||
        (Math.floor(f / 3) === Math.floor(this.fila / 3) && Math.floor(c / 3) === Math.floor(this.col / 3));
      const v = this.tablero[i];
      return {
        dada: dadas[i],
        zona: zona,
        igual: this.valorSel && v === this.valorSel,
        sel: i === this.sel,
        error: this.error && this.error.celda === i,
        acierto: this.acierto === i,
      };
    },
    texto(i) {
      if (this.error && this.error.celda === i) return this.error.valor;
      return this.tablero[i] || "";
    },
    notasDe(i) {
      if (this.tablero[i] || (this.error && this.error.celda === i)) return null;
      const n = this.notas[String(i)];
      return n && n.length ? n : null;
    },
    etiqueta(i) {
      const v = this.tablero[i];
      return `Fila ${Math.floor(i / 9) + 1}, columna ${(i % 9) + 1}: ${v ? v : "vacía"}${dadas[i] ? " (del enunciado)" : ""}`;
    },

    // ---------- Reloj ----------
    tic() {
      if (this.enCurso && !this.pausado && !document.hidden) this.segundos++;
    },
    guardarTiempo(alSalir = false) {
      if (!this.enCurso) return;
      if (alSalir) {
        fetch(datos.urls.tiempo, {
          method: "POST",
          keepalive: true,
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
          body: JSON.stringify({ segundos: this.segundos }),
        }).catch(() => {});
      } else {
        this.enviar("tiempo", {});
      }
    },

    // ---------- Comunicación con el servidor ----------
    enviar(accion, cuerpo) {
      const peticion = this.cola.then(async () => {
        try {
          const res = await fetch(datos.urls[accion], {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
            body: JSON.stringify({ ...cuerpo, segundos: this.segundos }),
          });
          if (res.redirected) {
            window.location.href = res.url; // la sesión ha caducado
            return null;
          }
          if (!res.ok) throw new Error(res.status);
          const r = await res.json();
          this.sincronizar(r.partida);
          this.aviso = "";
          return r;
        } catch (e) {
          this.aviso = "No se ha podido guardar. Comprueba tu conexión.";
          return null;
        }
      });
      this.cola = peticion.catch(() => {});
      return peticion;
    },
    sincronizar(p) {
      this.tablero = [...p.tablero].map(Number);
      this.notas = p.notas || {};
      this.errores = p.errores;
      this.vidas = p.vidas;
      this.pistas = p.pistas;
      this.segundos = Math.max(this.segundos, p.segundos);
      if (p.estado !== this.estado) {
        this.estado = p.estado;
        if (p.estado !== "en_curso") {
          this.segundos = p.segundos;
          setTimeout(() => (this.finAbierto = true), 450);
        }
      }
    },

    // ---------- Acciones ----------
    elegir(i) {
      this.sel = i;
      this.error = null;
    },
    mover(df, dc) {
      const f = (this.fila + df + 9) % 9, c = (this.col + dc + 9) % 9;
      this.elegir(f * 9 + c);
    },

    async poner(n) {
      const i = this.sel;
      if (!this.enCurso || this.pausado || dadas[i]) return;
      if (this.modoNotas) {
        if (this.tablero[i]) return;
        const antes = this.notas[String(i)] || [];
        const despues = antes.includes(n) ? antes.filter((x) => x !== n) : [...antes, n].sort();
        this.notas = { ...this.notas, [i]: despues };
        this.historial.push({ tipo: "notas", celda: i, antes });
        this.enviar("notas", { celda: i, notas: despues });
        return;
      }
      if (this.tablero[i] === n) return;
      this.error = null;
      const r = await this.enviar("jugada", { celda: i, numero: n });
      if (!r) return;
      if (r.correcto) {
        this.historial.push({ tipo: "poner", celda: i });
        this.acierto = i;
        setTimeout(() => (this.acierto = null), 500);
      } else if (r.correcto === false) {
        this.error = { celda: i, valor: n };
        if (navigator.vibrate) navigator.vibrate(120);
      }
    },

    borrar() {
      const i = this.sel;
      if (!this.enCurso || this.pausado || dadas[i]) return;
      this.error = null;
      const valor = this.tablero[i];
      const notas = this.notas[String(i)] || [];
      if (!valor && !notas.length) return;
      this.historial.push({ tipo: "borrar", celda: i, valor, notas });
      this.enviar("borrar", { celda: i });
    },

    deshacer() {
      if (!this.enCurso || this.pausado) return;
      const h = this.historial.pop();
      if (!h) return;
      this.sel = h.celda;
      this.error = null;
      if (h.tipo === "notas") {
        this.enviar("notas", { celda: h.celda, notas: h.antes });
      } else if (h.tipo === "poner") {
        this.enviar("borrar", { celda: h.celda });
      } else if (h.tipo === "borrar") {
        if (h.valor) this.enviar("jugada", { celda: h.celda, numero: h.valor });
        if (h.notas.length) this.enviar("notas", { celda: h.celda, notas: h.notas });
      }
    },

    async pista() {
      if (!this.enCurso || this.pausado) return;
      this.error = null;
      const r = await this.enviar("pista", { celda: this.sel });
      if (r && r.pista) {
        this.sel = r.pista.celda;
        this.acierto = r.pista.celda;
        setTimeout(() => (this.acierto = null), 500);
        this.historial = this.historial.filter((h) => h.celda !== r.pista.celda);
      }
    },

    pausar() {
      if (!this.enCurso) return;
      this.pausado = !this.pausado;
      if (this.pausado) this.guardarTiempo();
    },

    teclado(e) {
      if (e.target.closest("input, textarea, select") || e.altKey || e.metaKey) return;
      if (e.ctrlKey) {
        if (e.key.toLowerCase() === "z") { e.preventDefault(); this.deshacer(); }
        return;
      }
      const k = e.key;
      if (/^[1-9]$/.test(k)) { e.preventDefault(); this.poner(Number(k)); }
      else if (k === "Backspace" || k === "Delete" || k === "0") { e.preventDefault(); this.borrar(); }
      else if (k === "ArrowUp") { e.preventDefault(); this.mover(-1, 0); }
      else if (k === "ArrowDown") { e.preventDefault(); this.mover(1, 0); }
      else if (k === "ArrowLeft") { e.preventDefault(); this.mover(0, -1); }
      else if (k === "ArrowRight") { e.preventDefault(); this.mover(0, 1); }
      else if (k.toLowerCase() === "n") { this.modoNotas = !this.modoNotas; }
      else if (k.toLowerCase() === "p") { this.pausar(); }
      else if (k === "Escape") { this.finAbierto = false; this.pausado = false; }
    },
  };
}

function formatoTiempo(s) {
  s = Math.max(0, Math.floor(s));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), seg = s % 60;
  const dos = (x) => String(x).padStart(2, "0");
  return h ? `${h}:${dos(m)}:${dos(seg)}` : `${dos(m)}:${dos(seg)}`;
}
