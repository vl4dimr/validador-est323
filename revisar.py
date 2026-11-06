# -*- coding: utf-8 -*-
"""Revisor de la Práctica 9: clona los repositorios de los equipos y saca lo que se califica.

    python revisar.py [equipos.csv]        (o doble clic en Revisar.bat)

Lee equipos.csv (mesa, marca, enlace, stack), clona cada repositorio en clones/ y, por equipo:
  - del log: autores, commits por autor, commits desde la sesión 10, ramas, merges, mensajes flojos
  - del árbol: .gitignore, basura subida (bases de datos, node_modules, vendor, venv), archivos
    de prueba, el acta de aceptación
  - las pruebas, solo donde no hay que instalar nada raro: Node (node --test o npm test) y
    Python (pytest). Laravel, Django, Java y PHP quedan «a mano» (en esta máquina no hay PHP, Django ni Maven).
Deja Revision_Practica9.xlsx (hojas «Equipos» y «Commits») y logs/<mesa>.txt con la salida tal
cual de las pruebas. Ojo: correr las pruebas es correr el código de ellos en esta máquina.
"""
import csv
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = Path(__file__).resolve().parent
CLONES = AQUI / "clones"
LOGS = AQUI / "logs"
SESION = "2026-10-30"                      # desde cuándo cuentan los commits de la Práctica 9
TIEMPO = 240                               # segundos por comando
FLOJO = re.compile(r"^(cambios?|final\d*|update[sd]?|fix(es)?|test|asd+|prueba|arreglos?|subida|commit|init(ial)?|wip|listo|ok|\W*)$", re.I)
BASURA = re.compile(r"(^|/)(node_modules|venv|\.venv|env|__pycache__)(/|$)|(^|/)vendor/(autoload\.php|composer/)|\.(db|sqlite3?|db-journal)$", re.I)
PRUEBAS = re.compile(r"(\.test\.[cm]?[jt]s$|(^|/)tests?(/|\.py$)|(^|/)test_[^/]*\.py$|Test\.php$|_test\.go$|\.spec\.[cm]?[jt]s$)", re.I)
ACTA = re.compile(r"acepta", re.I)
# La rúbrica de la parte del repositorio (la misma de las fichas de observaciones): suma 20.
CRITERIOS = [("Ramas y merge", 4), ("Trabajan los tres", 4), ("Pruebas que corren", 4),
             ("Integración por HTTP", 3), ("Orden del repositorio", 3), ("Innovación en el código", 2)]
# Señales de que una prueba le habla al servidor por HTTP y no solo a una función.
HTTP_EN_PRUEBAS = re.compile(r"fetch\(|supertest|test_client|TestClient|MockMvc|WebTestClient|RestTemplate|axios|"
                             r"HttpClient|requests\.(get|post)|http://|https://|\.(get|post)\(['\"]/", re.I)


def correr(cmd, cwd, tiempo=TIEMPO):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=tiempo, shell=isinstance(cmd, str))
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        return -1, "SE PASÓ DEL TIEMPO (%d s)\n%s" % (tiempo, (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or ""))
    except FileNotFoundError as e:
        return -2, "NO ESTÁ INSTALADO: %s" % e


def git(repo, *args):
    codigo, salida = correr(["git", "-c", "core.quotepath=off"] + list(args), repo)
    return salida if codigo == 0 else ""


def borrar(carpeta):
    def quitar_solo_lectura(func, ruta, _):
        Path(ruta).chmod(stat.S_IWRITE)
        func(ruta)
    if carpeta.exists():
        shutil.rmtree(carpeta, onexc=quitar_solo_lectura)


def normalizar(enlace):
    e = enlace.strip().rstrip("/")
    e = re.sub(r"/(tree|blob)/.*$", "", e)
    return e


def clonar(enlace, destino):
    # REVISAR_SIN_CLONAR=1 reusa el clon que ya está (útil si un repositorio pesado se corta al bajar)
    if os.environ.get("REVISAR_SIN_CLONAR") and (destino / ".git").is_dir():
        return True, "se reusó el clon existente"
    borrar(destino)
    if "github.com" in enlace and shutil.which("gh"):
        codigo, salida = correr(["gh", "repo", "clone", enlace, str(destino)], AQUI)
    else:
        codigo, salida = correr(["git", "clone", enlace, str(destino)], AQUI)
    return codigo == 0, salida


def raiz_proyecto(repo):
    """Si el proyecto no está en la raíz del repositorio, busca una carpeta adentro que lo tenga."""
    marcas = ("package.json", "artisan", "manage.py", "pom.xml", "build.gradle", "composer.json",
              "requirements.txt", "pyproject.toml", "pruebas", "tests", "test")
    if any((repo / m).exists() for m in marcas):
        return repo
    for sub in sorted(p for p in repo.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if any((sub / m).exists() for m in marcas):
            return sub
    return repo


def detectar_stack(raiz):
    if (raiz / "artisan").exists():
        return "laravel"
    if (raiz / "manage.py").exists():
        return "django"
    if (raiz / "pom.xml").exists() or (raiz / "build.gradle").exists():
        return "java"
    if (raiz / "package.json").exists() or list(raiz.glob("**/*.test.*js"))[:1]:
        return "node"
    if (raiz / "requirements.txt").exists() or (raiz / "pyproject.toml").exists() or list(raiz.glob("**/test_*.py"))[:1]:
        return "python"
    if (raiz / "composer.json").exists() or list(raiz.glob("*.php"))[:1]:
        return "php"
    return "otro"


def pista(salida):
    """Una línea que explique por qué no corrió, para la columna Observación."""
    reglas = [
        (r"no existe el rol|role .* does not exist|ECONNREFUSED|Access denied for user|Can't connect to MySQL|password authentication failed",
         "Las pruebas que tocan la base necesitan su PostgreSQL/MySQL levantado: correr a mano o pedirles SQLite en memoria para las pruebas."),
        (r"No module named '([\w.]+)'", "Falta instalar el módulo de Python «{0}» (no está en esta máquina)."),
        (r"Cannot find (?:package|module) '([^']+)'", "Falta la dependencia «{0}»: no está en el package.json que se instala."),
        (r"async def functions are not natively supported", "Pruebas async sin pytest-asyncio en requirements."),
    ]
    for patron, texto in reglas:
        m = re.search(patron, salida)
        if m:
            return texto.format(*m.groups())
    return ""


def correr_pruebas(raiz, stack):
    """Devuelve (comando, pasan, fallan, estado, salida). estado: verde · rojo · a mano · no corrió."""
    if stack == "node":
        paquete = raiz / "package.json"
        cmd = ["node", "--test"]
        if paquete.exists():
            try:
                pj = json.loads(paquete.read_text(encoding="utf-8"))
            except Exception:
                pj = {}
            deps = pj.get("dependencies") or pj.get("devDependencies") or pj.get("workspaces")
            if deps and not (raiz / "node_modules").exists():
                correr(["npm.cmd" if sys.platform == "win32" else "npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"], raiz)
            prueba = (pj.get("scripts") or {}).get("test", "")
            if prueba and "no test specified" not in prueba:
                cmd = ["npm.cmd" if sys.platform == "win32" else "npm", "test"]
        codigo, salida = correr(cmd, raiz)
        m_pasa, m_falla = re.search(r"ℹ pass (\d+)", salida), re.search(r"ℹ fail (\d+)", salida)
        if m_pasa and m_falla:
            p, f = int(m_pasa.group(1)), int(m_falla.group(1))
            return " ".join(cmd), p, f, "verde" if f == 0 and p > 0 else "rojo" if f else "sin pruebas", salida
        m = re.search(r"Tests:?\s+(?:(\d+) failed[,|\s]+)?(\d+) passed", salida)   # jest («Tests: 1 failed, 2 passed») / vitest («Tests  2 failed | 82 passed»)
        if m:
            f, p = int(m.group(1) or 0), int(m.group(2))
            return " ".join(cmd), p, f, "verde" if f == 0 else "rojo", salida
        return " ".join(cmd), "", "", "no corrió" if codigo != 0 else "sin pruebas", salida
    if stack == "python":
        # si el repositorio tiene su propio venv (hecho a mano con sus requirements), se usa ese Python
        venv = raiz / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        cmd = [str(venv) if venv.exists() else sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        codigo, salida = correr(cmd, raiz)
        # solo la línea final («== 1 failed, 15 passed, 10 errors in 151.50s ==»): las líneas de log del
        # código de ellos también dicen «error» (psycopg: «pool.py:680 error connecting») y engañaban la cuenta
        resumen = re.findall(r"^(?:=+ )?([^\n=]*\b(?:passed|failed|error|skipped)[^\n=]*?) in [\d.]+s", salida, re.M)
        resumen = resumen[-1] if resumen else ""
        p = sum(int(x) for x in re.findall(r"(\d+) passed", resumen))
        f = sum(int(x) for x in re.findall(r"(\d+) failed", resumen)) + sum(int(x) for x in re.findall(r"(\d+) error", resumen))
        if p or f:
            return "python -m pytest", p, f, "verde" if f == 0 else "rojo", salida
        return "python -m pytest", "", "", "no corrió" if codigo not in (0, 5) else "sin pruebas", salida
    if stack in ("laravel", "django"):
        return {"laravel": "php artisan test", "django": "python manage.py test"}[stack], "", "", "a mano", "Laravel/Django: correr a mano (hace falta PHP o Django instalados)."
    if stack in ("java", "php"):
        return {"java": "mvn test", "php": "phpunit"}[stack], "", "", "a mano", "Java/PHP: correr a mano (en esta máquina no hay Maven ni PHP)."
    return "", "", "", "a mano", "Stack no reconocido."


def puntaje_estimado(res, archivos, pruebas, destino):
    """La nota que se puede estimar sin leer el código, criterio por criterio, con la rúbrica de CRITERIOS.

    Cuatro criterios salen enteros del log y del árbol. «Integración por HTTP» llega hasta 2 (que la prueba
    le pegue al servidor se ve; que pruebe algo de verdad se lee). «Innovación» no se ve: la pone el profesor.
    Devuelve (detalle, nota, nota_maxima_estimable, partes); partes es [(criterio, puntos o None, máximo), …]."""
    ramas, merges, autores = res.get("Ramas") or 0, res.get("Merges") or 0, res.get("Autores") or 0
    p_ramas = min(2, max(0, ramas - 1)) + min(2, merges)        # hasta 2 por ramas además de main, hasta 2 por merges
    p_tres = {0: 0, 1: 0, 2: 2}.get(autores, 4)
    if autores >= 3:
        cuentas = [int(x.rsplit(":", 1)[1]) for x in (res.get("Commits por autor") or "").split("; ") if ":" in x]
        if cuentas and min(cuentas) * 10 < sum(cuentas):          # alguien con menos del 10 % de los commits
            p_tres = 3
    estado, pasan, fallan = res.get("Estado"), res.get("Pasan") or 0, res.get("Fallan") or 0
    if estado == "verde":
        p_pruebas = 4 if pasan >= 5 else 3
    elif estado == "rojo":
        p_pruebas = 2 if pasan > fallan else 1
    elif estado == "a mano":
        p_pruebas = None                                            # no se corrieron aquí
    else:
        p_pruebas = 0
    http = False
    for a in pruebas[:40]:
        try:
            http = bool(HTTP_EN_PRUEBAS.search((destino / a).read_text(encoding="utf-8", errors="replace")[:200000]))
        except OSError:
            pass
        if http:
            break
    p_http = 2 if http else 0
    readme = any("/" not in a and a.lower().startswith("readme") for a in archivos)
    p_orden = int(readme) + int(res.get("gitignore") == "sí") + int(not res.get("Basura subida"))
    partes = [("Ramas y merge", p_ramas, 4), ("Trabajan los tres", p_tres, 4), ("Pruebas que corren", p_pruebas, 4),
              ("Integración por HTTP", p_http, 3), ("Orden del repositorio", p_orden, 3), ("Innovación en el código", None, 2)]
    detalle, nota, maximo = [], 0, 0
    for nombre, p, m in partes:
        if p is None:
            detalle.append("%s ?/%d (%s)" % (nombre, m, "no se corrió aquí" if nombre.startswith("Pruebas") else "se lee"))
        else:
            nota += p
            maximo += m
            detalle.append("%s %d/%d%s" % (nombre, p, m, " (el tercero se lee)" if nombre.startswith("Integración") else ""))
    return " · ".join(detalle), nota, maximo, partes


def faltas(res):
    """Lo que le falta al equipo respecto a lo que pide la Práctica 9, en frases que se entienden solas."""
    f = []
    if res.get("Autores", 0) < 3:
        f.append("En el log hay %s autor(es) y tienen que aparecer los tres, cada uno desde su propia cuenta "
                 "(git config user.name y user.email, con el correo de GitHub)." % res.get("Autores", 0))
    if res.get("Ramas", 0) < 3:
        f.append("Hay %s rama(s). Se pidió una rama por integrante, además de main." % res.get("Ramas", 0))
    if not res.get("Merges"):
        f.append("No hay ningún merge: las ramas no se juntaron a main (pull request o git merge).")
    if not res.get("Commits desde el 30/10"):
        f.append("No hay commits desde el 30/10.")
    estado = res.get("Estado", "")
    if estado == "sin pruebas":
        f.append("No se encontraron pruebas que correr (node --test, npm test o pytest).")
    elif estado == "rojo":
        f.append("%s prueba(s) fallan: la salida completa está en logs/." % res.get("Fallan", "?"))
    elif estado == "no corrió":
        f.append("Las pruebas no corrieron. %s" % (res.get("Observación") or "Mire logs/."))
    elif estado == "a mano" and res.get("Comando"):
        f.append("Las pruebas de %s no se corren aquí: córranlas ustedes con «%s» y guarden la salida en el README."
                 % (res.get("Stack"), res["Comando"]))
    elif estado == "a mano":
        f.append("No reconocí el proyecto: en la raíz no hay package.json, requirements.txt, pom.xml ni composer.json.")
    if not res.get("Archivos de prueba"):
        f.append("No hay archivos de prueba (tests/, test_*.py, *.test.js o parecidos).")
    if not res.get("Acta"):
        f.append("No está el acta de aceptación: un archivo con «acepta» en el nombre, por ejemplo docs/acta_aceptacion.md.")
    if res.get("gitignore") == "no":
        f.append("No hay .gitignore.")
    if res.get("Basura subida"):
        f.append("Subieron cosas que no van en Git: %s. Sáquenlas del repositorio y pónganlas en .gitignore." % res["Basura subida"])
    if res.get("Mensajes flojos"):
        f.append("%s mensaje(s) de commit flojos (%s): un commit dice qué cambió y por qué." % (res["Mensajes flojos"], res.get("Ejemplos flojos", "")))
    if res.get("Observación", "").startswith("Subieron el proyecto comprimido"):
        f.append(res["Observación"] + " Descompriman y suban la carpeta.")
    return f


def revisar(fila):
    mesa, marca, enlace = fila["mesa"].strip(), fila["marca"].strip(), normalizar(fila["enlace"])
    res = {"Mesa": mesa, "Marca": marca, "Enlace": enlace}
    destino = CLONES / ("%s_%s" % (mesa.zfill(2), re.sub(r"[^\w-]+", "_", marca) or "equipo"))
    print("· Mesa %s · %s" % (mesa, marca or enlace))
    ok, salida = clonar(enlace, destino)
    if not ok:
        res.update({"Clonó": "no", "Estado": "no clonó", "Observación": salida.strip()[-300:]})
        return res, []
    res["Clonó"] = "sí"
    # --- el log ------------------------------------------------------------ #
    git(destino, "fetch", "--all", "-q")
    commits = []
    for linea in git(destino, "log", "--all", "--format=%h%x09%an%x09%ad%x09%P%x09%s", "--date=short").splitlines():
        partes = linea.split("\t")
        if len(partes) == 5:
            commits.append({"hash": partes[0], "autor": partes[1], "fecha": partes[2], "merge": len(partes[3].split()) > 1, "mensaje": partes[4]})
    autores = {}
    for c in commits:
        autores[c["autor"]] = autores.get(c["autor"], 0) + 1
    ramas = [r.strip().replace("origin/", "") for r in git(destino, "branch", "-r").splitlines() if "->" not in r]
    flojos = [c["mensaje"] for c in commits if not c["merge"] and (len(c["mensaje"].strip()) < 10 or FLOJO.match(c["mensaje"].strip()))]
    ultimo = commits[0] if commits else {"fecha": "", "hash": ""}
    res.update({
        "Autores": len(autores),
        "Commits por autor": "; ".join("%s: %d" % (a, n) for a, n in sorted(autores.items(), key=lambda x: -x[1])),
        "Commits": len(commits),
        "Commits desde el 30/10": sum(1 for c in commits if c["fecha"] >= SESION),
        "Ramas": len(ramas), "Cuáles": ", ".join(ramas),
        "Merges": sum(1 for c in commits if c["merge"]),
        "Mensajes flojos": len(flojos), "Ejemplos flojos": " | ".join(flojos[:4]),
        "Último commit": "%s %s" % (ultimo["fecha"], ultimo["hash"]),
    })
    # --- el árbol ----------------------------------------------------------- #
    archivos = git(destino, "ls-files").splitlines()
    res["gitignore"] = "sí" if ".gitignore" in archivos or any(a.endswith("/.gitignore") for a in archivos) else "no"
    basura = sorted({a.split("/")[0] if BASURA.search(a) and "/" in a and BASURA.search(a).start() == 0 else a for a in archivos if BASURA.search(a)})
    res["Basura subida"] = ", ".join(basura[:5]) + (" …" if len(basura) > 5 else "")
    pruebas = [a for a in archivos if PRUEBAS.search(a)]
    res["Archivos de prueba"] = len(pruebas)
    res["Acta"] = ", ".join(a for a in archivos if ACTA.search(Path(a).name))[:80]
    # --- las pruebas -------------------------------------------------------- #
    raiz = raiz_proyecto(destino)
    stack = (fila.get("stack") or "").strip().lower() or detectar_stack(raiz)
    res["Stack"] = stack
    comando, pasan, fallan, estado, salida = correr_pruebas(raiz, stack)
    obs = pista(salida) if estado in ("rojo", "no corrió") else ""
    if not obs and any(a.lower().endswith((".zip", ".rar")) for a in archivos) and len(archivos) < 10:
        obs = "Subieron el proyecto comprimido (%s), no el código." % ", ".join(a for a in archivos if a.lower().endswith((".zip", ".rar")))
    res.update({"Comando": comando, "Pasan": pasan, "Fallan": fallan, "Estado": estado, "Observación": obs})
    LOGS.mkdir(exist_ok=True)
    (LOGS / ("%s.txt" % mesa.zfill(2))).write_text("%s · %s\n%s\n%s\n\n%s" % (mesa, marca, enlace, " ".join(comando.split()), salida), encoding="utf-8")
    print("   %d autores · %d ramas · %d merges · pruebas: %s%s" % (len(autores), len(ramas), res["Merges"], estado,
                                                                     " (%s/%s)" % (pasan, fallan) if pasan != "" else ""))
    lista = faltas(res)
    res["Lo que falta"] = "\n".join("• " + x for x in lista)
    for x in lista:
        print("   falta: " + x)
    if not lista:
        print("   no falta nada de lo que se revisa aquí")
    detalle, nota, maximo, partes = puntaje_estimado(res, archivos, pruebas, destino)
    res.update({"Puntaje estimado": detalle, "Nota estimada": nota, "Visible": maximo, "Partes": partes})   # Partes y Visible no van al Excel: los usa interfaz.py
    print("   nota estimada: %d de los %d puntos que se ven aquí (sobre 20) · %s" % (nota, maximo, detalle))
    return res, [{"Mesa": mesa, "Marca": marca, **c} for c in commits]


def excel(filas, commits, destino):
    columnas = ["Mesa", "Marca", "Stack", "Clonó", "Estado", "Pasan", "Fallan", "Autores", "Commits por autor", "Commits",
                "Commits desde el 30/10", "Ramas", "Cuáles", "Merges", "gitignore", "Basura subida", "Archivos de prueba",
                "Acta", "Mensajes flojos", "Ejemplos flojos", "Último commit", "Comando", "Enlace", "Observación", "Lo que falta",
                "Puntaje estimado", "Nota estimada", "Nota", "Para decirles"]
    anchos = [6, 16, 9, 7, 10, 7, 7, 8, 34, 8, 10, 7, 30, 8, 9, 26, 9, 22, 9, 36, 18, 22, 40, 36, 60, 60, 9, 7, 40]
    colores = {"verde": "DCFCE7", "rojo": "FEE2E2", "a mano": "FEF3C7", "no clonó": "FEE2E2", "no corrió": "FEE2E2", "sin pruebas": "FEF3C7"}
    wb = Workbook()
    ws = wb.active
    ws.title = "Equipos"
    borde = Border(*(Side(style="thin", color="CBD5E1"),) * 4)

    def cabecera(hoja, titulos, anchos_):
        hoja.append(titulos)
        for j, (t, w) in enumerate(zip(titulos, anchos_), 1):
            c = hoja.cell(1, j)
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="16203A")
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
            hoja.column_dimensions[c.column_letter].width = w
        hoja.row_dimensions[1].height = 32
        hoja.freeze_panes = "C2"

    cabecera(ws, columnas, anchos)
    for f in filas:
        ws.append([f.get(c, "") for c in columnas])
        r = ws.max_row
        for j in range(1, len(columnas) + 1):
            c = ws.cell(r, j)
            c.border = borde
            c.alignment = Alignment(wrap_text=True, vertical="top")
        estado = ws.cell(r, columnas.index("Estado") + 1)
        if estado.value in colores:
            estado.fill = PatternFill("solid", fgColor=colores[estado.value])
            estado.font = Font(bold=True)
        for nombre in ("Nota", "Para decirles"):
            ws.cell(r, columnas.index(nombre) + 1).fill = PatternFill("solid", fgColor="FFF2C2")
    ws2 = wb.create_sheet("Commits")
    cabecera(ws2, ["Mesa", "Marca", "Hash", "Autor", "Fecha", "Merge", "Mensaje"], [6, 16, 10, 22, 11, 7, 90])
    for c in commits:
        ws2.append([c["Mesa"], c["Marca"], c["hash"], c["autor"], c["fecha"], "sí" if c["merge"] else "", c["mensaje"]])
    ws2.auto_filter.ref = ws2.dimensions
    wb.save(destino)


def main():
    archivo = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI / "equipos.csv"
    with open(archivo, encoding="utf-8-sig", newline="") as f:
        equipos = [fila for fila in csv.DictReader(f) if (fila.get("enlace") or "").strip()]
    if not equipos:
        print("No hay enlaces en", archivo.name)
        return
    CLONES.mkdir(exist_ok=True)
    print("%d equipos · %s\n" % (len(equipos), datetime.now().strftime("%d/%m/%Y %H:%M")))
    filas, commits = [], []
    for fila in equipos:
        try:
            res, cs = revisar(fila)
        except Exception as e:                                  # un repositorio raro no detiene a los demás
            res, cs = {"Mesa": fila.get("mesa", ""), "Marca": fila.get("marca", ""), "Enlace": fila.get("enlace", ""),
                       "Clonó": "?", "Estado": "error", "Observación": repr(e)[:300]}, []
            print("   ERROR:", e)
        filas.append(res)
        commits.extend(cs)
    destino = AQUI / ("Revision_Practica9.xlsx" if archivo.name == "equipos.csv" else "Revision_%s.xlsx" % archivo.stem)
    excel(filas, commits, destino)
    print("\nListo:", destino.name, "· la salida de cada corrida está en logs/")


if __name__ == "__main__":
    main()
