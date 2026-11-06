# Validador de la Práctica 9 · EST323

Es el mismo programa con el que se revisan los repositorios de la Práctica 9
(«Integración, aceptación y Git»). Córranlo sobre su propio repositorio **antes** de
entregar: les dice qué falta, en palabras, y lo pueden arreglar con tiempo.

No califica. Mira lo que se puede mirar en automático: el log de Git, el árbol de
archivos y si las pruebas corren. Lo demás (que la prueba de integración pruebe algo de
verdad, que el acta la haya ejecutado otra mesa, la innovación) se revisa leyendo.

## Qué necesitan en su máquina

- **Python 3.10 o más nuevo** y `pip install -r requirements.txt` (instala `openpyxl`).
- **Git** en la línea de comandos.
- Lo que use su proyecto para sus pruebas: **Node** si es Node, **pytest** si es Python.
  Laravel, Django, Java y PHP no se corren aquí: el programa lo marca «a mano» y ustedes
  corren sus pruebas con su herramienta.
- Si su repositorio es privado, `git clone` les va a pedir su usuario de GitHub. También
  pueden poner la ruta de una carpeta local en vez del enlace, pero lo que se revisa es
  **lo que está en GitHub**, así que conviene probar con el enlace.

## Primero, con el ejemplo del curso

`equipos.csv` ya trae en la fila 0 el ejemplo resuelto de la sesión 10, la biblioteca
«Estante»: https://github.com/vl4dimr/estante-practica9. Es un repositorio como el que se
les pide: tres autores en el log, una rama por integrante (`integracion`, `controlador`,
`aceptacion`) juntadas a `main`, pruebas de integración por HTTP en `pruebas/`, el acta en
`pruebas/aceptacion.md`, README y `.gitignore`.

Corran `Revisar.bat` sin cambiar nada. Tiene que salir esto:

```
· Mesa 0 · Estante
   3 autores · 4 ramas · 3 merges · pruebas: verde (13/0)
   no falta nada de lo que se revisa aquí
   nota estimada: 17 de los 18 puntos que se ven aquí (sobre 20) · Ramas y merge 4/4 · Trabajan los tres 4/4 · Pruebas que corren 4/4 · Integración por HTTP 2/3 (el tercero se lee) · Orden del repositorio 3/3 · Innovación en el código ?/2 (se lee)
```

Si sale eso, el programa funciona en su máquina. Entren a `clones/00_Estante/` y miren
cómo está hecho: `git log --all --graph --oneline` muestra las ramas y los merges;
`pruebas/recorrido.test.mjs` arma el servidor con `crearServidor(bd)` y le hace pedidos
con `fetch`; `pruebas/aceptacion.md` tiene los escenarios Dado / Cuando / Entonces y quién
los ejecutó.

## Después, con el suyo

1. Abran `equipos.csv` con el Bloc de notas o Excel y pongan en la fila 1 su marca y el
   enlace de su repositorio. La columna `stack` puede quedar vacía: el programa lo detecta.
   Pueden dejar la fila del ejemplo o borrarla.

   ```
   mesa,marca,enlace,stack
   0,Estante,https://github.com/vl4dimr/estante-practica9,
   1,MiMarca,https://github.com/usuario/mi-repositorio,
   ```

2. Doble clic en `Revisar.bat` (o `python revisar.py` en la consola). Clona el repositorio
   en `clones/`, lee el log, cuenta ramas y merges, busca los archivos de prueba y el acta,
   y corre las pruebas. Tarda uno o dos minutos.

3. Lean la consola. Al final de su equipo sale una lista `falta:` con cada cosa que
   encontró. Si dice «no falta nada de lo que se revisa aquí», lo automático está bien.
   El detalle queda en `Revision_Practica9.xlsx` (hoja «Equipos», columna «Lo que falta»)
   y la salida completa de las pruebas en `logs/01.txt`.

Cada corrida vuelve a clonar desde cero, así que siempre revisa lo último que subieron.

## Qué revisa y cómo se arregla

| Lo que mira | Lo que se pidió | Si falta |
|---|---|---|
| **Autores** en el log | Los tres integrantes con commits | Cada uno hace commits desde su propia máquina con `git config user.name` y `user.email` (el correo de su cuenta de GitHub). Que uno suba el trabajo de los otros no cuenta. |
| **Ramas** | Una rama por integrante, además de `main` | `git checkout -b nombre-de-la-rama`, trabajar ahí, `git push -u origin nombre-de-la-rama`. |
| **Merges** | Las ramas se juntaron a `main` | Pull request en GitHub y botón «Merge», o `git merge` desde `main`. Si hay conflicto, se resuelve: no se borran archivos para que «no moleste». |
| **Pruebas** | Corren y pasan: `node --test`, `npm test` o `pytest` | Verde: todas pasan. Rojo: alguna falla, miren `logs/`. «Sin pruebas»: no encontró ninguna. «No corrió»: falta instalar algo o la base de datos no está; el programa dice qué. |
| **Archivos de prueba** | Existen (`tests/`, `test_*.py`, `*.test.js`…) | Escríbanlas. La de integración por HTTP arma el servidor y le hace pedidos de verdad. |
| **Acta de aceptación** | Un archivo con «acepta» en el nombre | Por ejemplo `docs/acta_aceptacion.md`, con sus casos Dado / Cuando / Entonces y quién de la otra mesa los ejecutó. |
| **.gitignore** | Existe | Un `.gitignore` para su lenguaje (hay plantillas en github.com/github/gitignore). |
| **Basura subida** | No hay `node_modules`, `venv`, `vendor`, bases `.db` ni `__pycache__` en Git | `git rm -r --cached carpeta`, agregarla a `.gitignore`, commit. |
| **Mensajes flojos** | Los commits dicen qué cambió y por qué | «cambios», «final», «asd» no dicen nada. «Valida el correo al registrar (CP-09)» sí. |
| **Proyecto comprimido** | El código, no un ZIP | GitHub no es para guardar un ZIP. Descompriman y suban la carpeta. |

Lo que el programa **no ve** y también se califica: que la prueba de integración pase por
HTTP contra el servidor armado con la base; que el acta la haya ejecutado otra mesa; el
orden del repositorio (README que diga qué es y cómo se levanta); y la innovación en el código.

## La nota estimada

La parte del repositorio vale 20 puntos, con esta rúbrica. El programa estima lo que puede
ver y lo imprime criterio por criterio (también va en el Excel, columnas «Puntaje
estimado» y «Nota estimada»).

| Criterio | Puntos | Cómo lo estima el programa |
|---|---|---|
| Ramas y merge | 4 | Hasta 2 por las ramas además de `main` (una por integrante) y hasta 2 por los merges a `main`. |
| Trabajan los tres | 4 | Tres autores en el log: 4. Dos: 2. Uno: 0. Si alguien tiene menos del 10 % de los commits, 3. |
| Pruebas que corren | 4 | Verde con 5 o más pruebas: 4. Verde con menos: 3. Rojo: 1 (o 2 si pasan más de las que fallan). Sin pruebas o no corrió: 0. Java, PHP, Laravel y Django: «?», porque aquí no se corren. |
| Integración por HTTP | 3 | Hasta 2 si alguna prueba le habla al servidor (`fetch`, `supertest`, `test_client`, `MockMvc`…). El tercer punto, que la prueba pruebe algo que importa, se lee. |
| Orden del repositorio | 3 | 1 por el README, 1 por el `.gitignore`, 1 por no tener basura subida. |
| Innovación en el código | 2 | No se ve: la pone el profesor leyendo el código. |

Es una **estimación**, no la nota. Lo que se lee después puede bajarla: una contraseña
escrita en el código, una base que no se puede crear desde el repositorio, una prueba que
no prueba nada, o tres autores en el log donde uno solo hizo el trabajo. Y puede subirla:
la innovación y el tercer punto de integración solo se dan leyendo.

## Antes de subir cualquier cosa

Ningún archivo con contraseñas, claves de API, `.env`, bases de datos con datos de
personas, DNI ni fotos de documentos va al repositorio, ni público ni privado. Si ya lo
subieron, no basta con borrarlo: queda en la historia. Cambien la clave y pidan ayuda para
limpiar la historia.

## Un aviso

El programa corre las pruebas de su propio proyecto en su máquina, como las correrían
ustedes. Si se lo prestan a otra mesa, están corriendo código ajeno: mírenlo antes.
