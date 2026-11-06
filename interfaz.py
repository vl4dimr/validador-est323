# -*- coding: utf-8 -*-
"""La interfaz del validador: una página en el navegador, en vez de equipos.csv y el Excel.

    python interfaz.py        (o doble clic en Interfaz.bat)

Levanta un servidor solo en esta máquina (127.0.0.1), abre el navegador, y ahí se pega el
enlace del repositorio y se pulsa «Revisar». Por debajo corre el mismo revisar.py: clona en
clones/01_<marca>/, lee el log, corre las pruebas y deja la salida en logs/01.txt. Una
revisión a la vez. No necesita nada fuera de Python.
"""
import json
import socket
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import revisar as rv

EJEMPLO = ("Estante", "https://github.com/vl4dimr/estante-practica9")
TRABAJO = {"estado": "libre", "marca": "", "enlace": "", "res": None, "log": "", "error": ""}
CANDADO = threading.Lock()

PAGINA = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Validador de la Práctica 9 · EST323</title>
<style>
  :root { --tinta:#1b1d21; --gris:#6b6e75; --linea:#d9dce3; --fondo:#f6f7f9; --azul:#1d4ed8; --verde:#15803d; --rojo:#b91c1c; --ambar:#b45309; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--fondo); color:var(--tinta); font:16px/1.5 system-ui, "Segoe UI", sans-serif; }
  main { max-width:900px; margin:0 auto; padding:28px 16px 60px; }
  h1 { font-size:26px; margin:0 0 4px; } h1 small { color:var(--gris); font-weight:normal; font-size:15px; display:block; }
  h2 { font-size:17px; margin:0 0 10px; color:var(--azul); }
  p.intro { color:var(--gris); margin:6px 0 18px; }
  .tarjeta { background:#fff; border:1px solid var(--linea); border-radius:12px; padding:18px 20px; margin:0 0 16px; }
  form { display:grid; grid-template-columns:1fr 2fr auto; gap:10px; }
  input { font:inherit; padding:10px 12px; border:1px solid var(--linea); border-radius:8px; width:100%; }
  button { font:inherit; font-weight:600; padding:10px 18px; border:0; border-radius:8px; background:var(--azul); color:#fff; cursor:pointer; }
  button[disabled] { background:#9db0e8; cursor:wait; }
  a.ejemplo { font-size:14px; color:var(--azul); }
  .estado { color:var(--gris); margin-top:10px; font-size:15px; }
  .nota { font-size:34px; font-weight:700; } .nota small { font-size:15px; color:var(--gris); font-weight:normal; }
  .barra { display:grid; grid-template-columns:230px 1fr 130px; gap:10px; align-items:center; margin:7px 0; font-size:15px; }
  .barra .pista { height:10px; background:#e8eaef; border-radius:5px; overflow:hidden; }
  .barra .lleno { height:100%; background:var(--azul); }
  .barra.selee .lleno { background:#c8cbd3; } .barra.selee .pts { color:var(--gris); }
  .barra .pts { text-align:right; font-variant-numeric:tabular-nums; }
  ul.faltas { padding-left:0; list-style:none; margin:0; } ul.faltas li { padding:6px 0 6px 28px; position:relative; border-top:1px solid var(--linea); }
  ul.faltas li:first-child { border-top:0; } ul.faltas li::before { content:"✗"; position:absolute; left:4px; color:var(--rojo); font-weight:700; }
  .bien { color:var(--verde); font-weight:600; }
  table { width:100%; border-collapse:collapse; font-size:15px; } td { padding:6px 8px; border-top:1px solid var(--linea); vertical-align:top; }
  td:first-child { color:var(--gris); width:200px; } tr:first-child td { border-top:0; }
  .verde { color:var(--verde); font-weight:600; } .rojo { color:var(--rojo); font-weight:600; } .ambar { color:var(--ambar); font-weight:600; }
  details summary { cursor:pointer; color:var(--azul); } pre { background:#111827; color:#e5e7eb; padding:12px; border-radius:8px; font-size:12.5px; overflow:auto; max-height:420px; }
  .oculto { display:none; }
  @media (max-width:640px) { form { grid-template-columns:1fr; } .barra { grid-template-columns:1fr; gap:3px; } .barra .pts { text-align:left; } td:first-child { width:auto; } }
</style>
</head>
<body>
<main>
  <h1>Validador de la Práctica 9 <small>EST323 · Ingeniería de Software II · el mismo programa con el que se revisan los repositorios</small></h1>
  <p class="intro">Pegue el enlace de su repositorio de GitHub. El programa lo clona en esta máquina, lee el log, cuenta ramas y merges, busca las pruebas y el acta, y corre las pruebas. Tarda uno o dos minutos.</p>

  <div class="tarjeta">
    <form id="f">
      <input id="marca" placeholder="Marca del equipo" autocomplete="off">
      <input id="enlace" placeholder="https://github.com/usuario/repositorio" autocomplete="off" required>
      <button id="boton" type="submit">Revisar</button>
    </form>
    <div style="margin-top:8px"><a class="ejemplo" href="#" id="ejemplo">Probar primero con el ejemplo del curso (Estante)</a></div>
    <div class="estado" id="estado"></div>
  </div>

  <div id="resultado" class="oculto">
    <div class="tarjeta">
      <h2 id="titulo"></h2>
      <div class="nota" id="nota"></div>
      <div id="barras"></div>
      <p style="color:var(--gris);font-size:14px;margin:10px 0 0">Es una estimación con lo que se ve en el repositorio. Lo que se marca «se lee» lo pone el profesor leyendo el código, y lo que lea puede bajar o subir la nota.</p>
    </div>
    <div class="tarjeta"><h2>Lo que falta</h2><div id="faltas"></div></div>
    <div class="tarjeta"><h2>Lo que dice el repositorio</h2><table id="datos"></table></div>
    <div class="tarjeta"><details><summary>La salida de las pruebas (logs/01.txt)</summary><pre id="log"></pre></details></div>
  </div>
</main>
<script>
const $ = id => document.getElementById(id);
$("ejemplo").onclick = e => { e.preventDefault(); $("marca").value = "Estante"; $("enlace").value = "__EJEMPLO__"; };
let reloj = null;
$("f").onsubmit = async e => {
  e.preventDefault();
  const r = await fetch("/revisar", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ marca: $("marca").value, enlace: $("enlace").value }) });
  const j = await r.json();
  if (j.error) { $("estado").textContent = j.error; return; }
  $("boton").disabled = true; $("resultado").classList.add("oculto");
  const inicio = Date.now();
  $("estado").textContent = "Clonando y corriendo las pruebas…";
  reloj = setInterval(async () => {
    const seg = Math.round((Date.now() - inicio) / 1000);
    $("estado").textContent = "Clonando y corriendo las pruebas… " + seg + " s";
    const t = await (await fetch("/estado")).json();
    if (t.estado === "corriendo") return;
    clearInterval(reloj); $("boton").disabled = false;
    if (t.estado === "error") { $("estado").textContent = "Se rompió el programa: " + t.error; return; }
    $("estado").textContent = "Listo en " + seg + " s.";
    mostrar(t);
  }, 2000);
};
function fila(tabla, k, v, clase) { const tr = tabla.insertRow(); tr.insertCell().textContent = k; const c = tr.insertCell(); c.textContent = v; if (clase) c.className = clase; }
function mostrar(t) {
  const r = t.res; $("resultado").classList.remove("oculto");
  $("titulo").textContent = (t.marca || "Su repositorio") + " · " + t.enlace;
  const barras = $("barras"), faltas = $("faltas"), datos = $("datos"); barras.innerHTML = ""; faltas.innerHTML = ""; datos.innerHTML = "";
  if (r["Clonó"] !== "sí") {
    $("nota").textContent = "No se pudo clonar";
    faltas.textContent = r["Observación"] || "Revise el enlace. Si el repositorio es privado, git le va a pedir su usuario en la consola donde corre este programa.";
    $("log").textContent = ""; return;
  }
  $("nota").innerHTML = ""; $("nota").append(r["Nota estimada"] + " ", Object.assign(document.createElement("small"), { textContent: "de los " + r["Visible"] + " puntos que se ven aquí · la parte del repositorio vale 20" }));
  for (const [nombre, p, m] of r["Partes"]) {
    const b = document.createElement("div"); b.className = "barra" + (p === null ? " selee" : "");
    const n = document.createElement("div"); n.textContent = nombre;
    const pista = document.createElement("div"); pista.className = "pista"; const lleno = document.createElement("div"); lleno.className = "lleno"; lleno.style.width = (p === null ? 100 : 100 * p / m) + "%"; pista.append(lleno);
    const pts = document.createElement("div"); pts.className = "pts"; pts.textContent = p === null ? (nombre.startsWith("Pruebas") ? "? / " + m + " (no se corrió aquí)" : "se lee / " + m) : p + " / " + m + (nombre.startsWith("Integración") ? " (+1 se lee)" : "");
    b.append(n, pista, pts); barras.append(b);
  }
  const lista = (r["Lo que falta"] || "").split("\n").filter(x => x.trim());
  if (!lista.length) faltas.innerHTML = '<span class="bien">✓ No falta nada de lo que se revisa aquí.</span>';
  else { const ul = document.createElement("ul"); ul.className = "faltas"; for (const x of lista) { const li = document.createElement("li"); li.textContent = x.replace(/^•\s*/, ""); ul.append(li); } faltas.append(ul); }
  const est = r["Estado"], clase = { verde: "verde", rojo: "rojo" }[est] || "ambar";
  let pruebas = est; if (est === "verde") pruebas = "verde · " + r["Pasan"] + " pasan"; if (est === "rojo") pruebas = "rojo · " + r["Pasan"] + " pasan, " + r["Fallan"] + " fallan"; if (est === "a mano") pruebas = "no se corren aquí (" + (r["Comando"] || r["Stack"]) + ")";
  fila(datos, "Pruebas", pruebas, clase);
  if (r["Observación"]) fila(datos, "Por qué", r["Observación"]);
  fila(datos, "Autores en el log", r["Autores"] + " · " + (r["Commits por autor"] || ""));
  fila(datos, "Commits", r["Commits"] + " en total · " + r["Commits desde el 30/10"] + " desde el 30/10 · último: " + r["Último commit"]);
  fila(datos, "Ramas", r["Ramas"] + " · " + (r["Cuáles"] || ""));
  fila(datos, "Merges", String(r["Merges"]));
  fila(datos, "Archivos de prueba", String(r["Archivos de prueba"]));
  fila(datos, "Acta de aceptación", r["Acta"] || "no está", r["Acta"] ? "" : "rojo");
  fila(datos, ".gitignore", r["gitignore"], r["gitignore"] === "sí" ? "" : "rojo");
  fila(datos, "Basura subida", r["Basura subida"] || "ninguna", r["Basura subida"] ? "rojo" : "");
  fila(datos, "Mensajes flojos", r["Mensajes flojos"] + (r["Ejemplos flojos"] ? " · " + r["Ejemplos flojos"] : ""));
  fila(datos, "Stack", r["Stack"] || "no reconocido");
  $("log").textContent = t.log || "(sin salida)";
}
</script>
</body>
</html>
""".replace("__EJEMPLO__", EJEMPLO[1])


def correr(marca, enlace):
    """Corre revisar.py en un hilo y deja el resultado en TRABAJO."""
    try:
        rv.CLONES.mkdir(exist_ok=True)
        res, _ = rv.revisar({"mesa": "1", "marca": marca, "enlace": enlace, "stack": ""})
        archivo = rv.LOGS / "01.txt"
        log = archivo.read_text(encoding="utf-8", errors="replace")[-20000:] if archivo.exists() else ""
        TRABAJO.update({"estado": "listo", "res": res, "log": log})
    except Exception as e:                                      # el navegador lo muestra, el programa sigue vivo
        TRABAJO.update({"estado": "error", "error": repr(e)[:500]})


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, *args):                               # sin ruido en la consola
        pass

    def responder(self, cuerpo, tipo="application/json; charset=utf-8", codigo=200):
        datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        if self.path == "/":
            self.responder(PAGINA.encode("utf-8"), "text/html; charset=utf-8")
        elif self.path.startswith("/estado"):
            self.responder(TRABAJO)
        elif self.path == "/favicon.ico":                       # para que el navegador no anote un 404
            self.send_response(204)
            self.end_headers()
        else:
            self.responder({"error": "no existe"}, codigo=404)

    def do_POST(self):
        if self.path != "/revisar":
            return self.responder({"error": "no existe"}, codigo=404)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            cuerpo = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            cuerpo = {}
        enlace = (cuerpo.get("enlace") or "").strip()
        marca = (cuerpo.get("marca") or "").strip() or "equipo"
        if not enlace:
            return self.responder({"error": "Falta el enlace del repositorio."}, codigo=400)
        with CANDADO:
            if TRABAJO["estado"] == "corriendo":
                return self.responder({"error": "Ya hay una revisión corriendo; espere a que termine."}, codigo=409)
            TRABAJO.update({"estado": "corriendo", "marca": marca, "enlace": enlace, "res": None, "log": "", "error": ""})
        threading.Thread(target=correr, args=(marca, enlace), daemon=True).start()
        self.responder({"ok": True})


def puerto_libre(preferido=8765):
    for p in (preferido, 0):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return s.getsockname()[1]
            except OSError:
                continue
    return 0


def main():
    puerto = puerto_libre(int(sys.argv[1]) if len(sys.argv) > 1 else 8765)   # python interfaz.py 9000, si el 8765 está ocupado
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    direccion = "http://127.0.0.1:%d" % puerto
    print("Validador de la Práctica 9 · abra en el navegador:", direccion)
    print("Para apagarlo, cierre esta ventana o pulse Ctrl + C.")
    threading.Timer(0.8, webbrowser.open, (direccion,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
