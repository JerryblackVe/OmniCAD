# AGENTS.md — manual para agentes IA que programan en OmniCAD

## Qué es OmniCAD
CAD 3D paramétrico en Python (PySide6 + OpenGL, kernel OpenCascade vía `cadquery-ocp`), inspirado en
Fusion 360. Re-implementación limpia: timeline de operaciones con parámetros, bocetos con solver de
restricciones, archivos `.omnicad` (ZIP con receta JSON). Python 3.12. Repo público:
https://github.com/JerryblackVe/OmniCAD (GPL-3.0 o posterior).
Nota: se llamaba FusionClone hasta el 2026-10-09; los `.fclone` viejos se siguen abriendo.

## Reglas absolutas
- Se puede usar el análisis de programas de referencia (Fusion 360, Rhino, Grasshopper…) guardado en
  `analisis auto/` (fuera de git) como INSPIRACIÓN para mejorar OmniCAD (ideas, casos límite, comportamiento): se escribe todo desde cero, sin copiar código. Código GPL
  (p. ej. Blender) también, citando el origen.
- TODO en español: código, docstrings, comentarios, mensajes de error, nombres.
- No gastar en APIs pagas sin pedido explícito del usuario. No instalar paquetes sin permiso.
- Git: no commitear ni hacer `push` si no te lo piden. Nunca subir `privado/`, `analisis/` ni `evidencias/`
  (están en `.gitignore`: no los fuerces con `git add -f`).
- Todo dentro de la carpeta del repo. Unidades: milímetros y grados.
- Otros agentes trabajan EN PARALELO: tocá solo los archivos que te asignaron; si necesitás un cambio
  en otro, anotalo en el informe, no lo hagas.
- No digas "listo" sin correr la verificación y pegar su salida real.
- Usar SIEMPRE la skill `/ponytail` en todo proceso de código donde sea útil o necesario
  (escribir, arreglar, refactorizar, elegir dependencias): el cambio más chico que resuelve la
  tarea completa, sin sobre-ingeniería; y la skill `/ponytail-review` antes de dar por terminado
  un cambio de código (lógica, seguridad, carga real, tests, y que cada línea sea necesaria).
- Errores del núcleo: `raise geo.ErrorGeometria("mensaje claro en español")`
  (`from . import geometria as geo` dentro de `nucleo`).
- Funciones PURAS del núcleo: reciben formas OCC, arrays numpy, `geo.Plano` o números; devuelven formas
  OCC (o dicts). Sin Qt y sin timeline. Docstring: a qué comando de Fusion equivale.
- OCP: los métodos estáticos llevan sufijo `_s` (p. ej. `BRepGProp.VolumeProperties_s`).
- Para replicar un comando de otro programa, mirá su documentación pública y el análisis de
  `analisis auto/`, y replicá sus opciones y su comportamiento.

## Seguridad
- Nunca commitear secretos (tokens, claves, contraseñas): van en variables de entorno; `.env*` ya está
  en `.gitignore`. Si un secreto se subió por accidente, avisalo: hay que revocarlo (borrarlo del
  historial no alcanza).
- Validar toda entrada de archivo: un `.omnicad` (o un STEP/SVG/DXF importado) es un archivo de OTRO:
  tope de tamaño por miembro del ZIP (`io_archivos/proyecto.py` › `TOPE_MIEMBRO_ZIP`) y nunca
  `extractall` con rutas sin sanear.
- Lo que manda un agente o un archivo no llega a `eval`/`exec` fuera de los lugares designados.
  `execute_code` es una excepción BY DESIGN: corre con transacción atómica, timeout y en UN hilo —
  no le armes caminos que salteen eso.
- El servidor MCP con `--http` y el puente en vivo escuchan SOLO en 127.0.0.1 y exigen token
  (`mcp_http.json` / `puente.json`): no los expongas a la red, no los reenvíes ni los loguees.
- Al tocar el arranque del servidor o el protocolo de red, dejá el test que pruebe el rechazo sin
  token (patrón: `tests/test_servidor_mcp.py`).
- Subir solo con la CI verde: ruff, pytest y el escaneo de secretos del workflow (nada se empuja
  «para ver si anda»).

## Mapa de carpetas
| Ruta | Qué hay |
|---|---|
| `clon/OmniCAD.py` | Entrada de la app |
| `clon/omnicad/nucleo/` | Geometría OCC pura: `geometria.py` (estilo de referencia), sólidos, chapa, malla, superficies, análisis, fijaciones |
| `clon/omnicad/timeline/` | Parámetros, `documento.py`, `operaciones.py` (base) y `ops_*.py` (una familia de operaciones por archivo) |
| `clon/omnicad/restricciones/` | Boceto 2D y solver (scipy) |
| `clon/omnicad/io_archivos/` | `.omnicad`, STL/OBJ/STEP, DXF, SVG, autoguardado |
| `clon/omnicad/grafo/` | Programación visual sin ventana (árboles de datos, nodos, motor); doc en `docs/grafo.md` |
| `clon/omnicad/ui/` | PySide6: `ventana.py`, `cinta.py`, `visor3d.py`, paneles, boceto en 3D |
| `clon/omnicad/ui/comandos/` | Un módulo por familia de comandos con diálogo (`CATALOGO`) |
| `clon/tests/` | pytest (un `test_*.py` por área) |
| `docs/` | Índice de todo en `docs/README.md`. Estado (bugs, faltantes, mejoras) en `docs/seguimiento/`; especificación de faltantes en `brechas_*.md`; planes `plan_*.md`; `agentes/` (MCP y CLI) |
| `ejemplos/agentes/` | Ejemplos ejecutables para agentes (batch, script, receta) |
| `.claude/skills/omnicad/` | Skill `omnicad` para agentes (la instala `omnicad setup`) |
| `scripts/` | Utilidades: capturas de pantalla de OmniCAD; `turno.py` (comandos pesados de a uno) |
| `PROJECT_LOG.md` | Bitácora (Registro) y "Lecciones aprendidas" |

**`nucleo/`, `timeline/`, `restricciones/` e `io_archivos/` NO importan Qt** (comprobado: cero
`PySide`/`QtCore`/`QtGui` ahí). Mantenelo: solo `ui/` conoce Qt.

## Cómo correr la app
Desde `clon/`, con el Python del venv: `.venv/Scripts/python.exe` en Windows, `.venv/bin/python` en Linux y macOS
(en Linux, las librerías del sistema que pide Qt están en el README › Instalación (Linux)):
- `OmniCAD.py` abre la app; `OmniCAD.py proyecto.omnicad` abre un proyecto.
- `OmniCAD.py --ejemplo` abre con el modelo de ejemplo.
- `OmniCAD.py --prueba-humo` prueba automática de la interfaz (sale con 0 si pasa).

## Cómo verificar
Desde `clon/` (shell Bash; en Linux, `.venv/bin/python` en lugar de `.venv/Scripts/python.exe`):
```
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest -q
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe OmniCAD.py --prueba-humo
```
El criterio de ruff (F, B023, B905) vive en `clon/pyproject.toml` › `[tool.ruff.lint]`: `ruff check .` lo
toma solo de ahí, sin `--select`.
**Memoria:** la suite completa y la prueba de humo (abren ventanas OpenGL) usan mucha memoria: se corren de a
UNA a la vez. Si sos uno de varios agentes en paralelo, corré solo tus archivos de test; la suite completa y la
humo las corre el orquestador (cuatro corridas a la vez colgaron una PC de 13 GB). Con varios agentes, cada
comando pesado va con turno (uno a la vez en toda la PC; corta a los 900 s; en Windows, tope de 3 GB de memoria):
`.venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe -m pytest tests/test_x.py -q`
(cada pytest reserva ~1 GB aunque use 350 MB de RAM).
**Prueba de humo:** no uses el ratón sobre su ventana mientras corre: varios pasos mueven el cursor REAL con `QTest.mouseMove`. Para un paso nuevo que solo necesita que el widget vea el ratón, usá `_mover` (movimiento simulado, no depende del cursor real).
Una prueba suelta: `pytest tests/<archivo>.py -q`. Cada función del núcleo lleva al menos una prueba con
un resultado numérico (volumen, área, caja envolvente) y `geo.es_valida(forma)`; rápidas (< 3 s).

**Definición de terminado**: ruff limpio, pytest verde, prueba de humo OK (la UI se toca → obligatoria),
entrada nueva en `PROJECT_LOG.md`, `docs/seguimiento/` al día (lo resuelto, borrado; lo nuevo, agregado) y lección
anotada si hubo un error verificable. Sin archivos sueltos: nada de informes, capturas o temporales en la raíz.

## Receta A: agregar una operación al timeline
Modelo: `OpFijacion` en `clon/omnicad/timeline/ops_fijacion.py`; base `Operacion` en `timeline/operaciones.py`.
1. En un `ops_*.py` (nuevo o existente), subclase de `Operacion` con: `TIPO` (clave única de la receta),
   `ETIQUETA`, `ICONO` (símbolo de una letra), `PARAMS` (dict de valores por defecto, serializable a JSON),
   `EXPRESIONES` (claves de `p` que son expresiones y pueden usar parámetros).
2. `ejecutar(self, estado, ctx)`: lee `self.p`, evalúa con `ctx.evaluar(expr)`, resuelve referencias con
   `_resolver(ref, estado)`, crea cuerpos con `estado.nuevo_cuerpo(...)` o `aplicar_resultado(...)`.
   Errores: `raise ErrorOperacion("mensaje en español")`. NUNCA modificar `self.p` al ejecutar (ver lecciones).
3. Si depende de otros pasos, sobrescribir `dependencias()` (ver `OpPlano`).
4. Al final del módulo: `registrar_operacion(MiOp)`.
5. Archivo `ops_*.py` nuevo: agregarlo al `from . import (ops_chapa, ...)` al pie de `operaciones.py`
   (línea ~649), o la receta no lo carga.
6. Prueba en `clon/tests/` (patrón de `tests/test_fijaciones.py`) y, si tiene diálogo, receta B.

## Receta B: agregar un comando a la interfaz
Modelo: `InsertarFijacion` en `clon/omnicad/ui/comandos/fijacion.py`; base `Comando` en `ui/comando.py`.
1. Clase `Comando` con `CLAVE`, `TITULO`, `ICONO`, `CLASE_OP` (la operación que crea/edita), `AYUDA`.
2. `campos(ctx)` devuelve campos de `ui/comando.py`: `Seleccion`, `Expresion`, `Opciones`, `Casilla`,
   `Entero`, `Texto`, `Info` (`visible_si=` para mostrar según otros valores).
3. `construir(v, ctx)` valida (`exigir(...)`) y devuelve `self.crear_op(MiOp, v, ctx, **params)`;
   `desde_op` carga los valores al editar (doble clic en el timeline vía `POR_TIPO`).
4. Registrar: `registrar(MiComando)` al final; módulo nuevo → agregarlo al import de
   `ui/comandos/__init__.py`. La ventana crea una `QAction` por cada clave de `CATALOGO`.
5. Botón en la cinta: `_i("Texto", "clave")` en el grupo/pestaña de `ui/cinta.py` (p. ej. `INSERTAR`).
   Sin clave el ítem queda GRISADO: regla de honestidad, nunca un botón activo que no hace nada.
6. Ícono: función en `ui/iconos_extra.py` y su entrada en el dict de íconos (ver `_fijacion`).
7. Prueba en `tests/test_comandos*.py` y correr la prueba de humo.

## Herramientas para agentes (MCP y CLI)
Documentación completa: [docs/agentes/README.md](docs/agentes/README.md) (conectar un agente, CLI, guía de diseño,
modo en vivo y la lista de herramientas). Plan y estado: [docs/plan_mcp_cli.md](docs/plan_mcp_cli.md).
`clon/omnicad/api/`, sin Qt y sin `mcp`, es el catálogo ÚNICO del que salen el MCP (`omnicad-mcp`), la CLI (`omnicad`) y la doc.

**Receta C: agregar una herramienta** (detalle en el docstring de `api/registro.py`):
1. Escribí una función en `api/herramientas_<grupo>.py` con `@herramienta("nombre_snake", "grupo", "descripción", modifica=...)`. Los módulos `herramientas_*` se registran solos.
2. El primer argumento es la `Sesion`. Los demás llevan anotación de tipo (`str`, `int`, `float`, `bool`, `list[...]`, `dict`, `Literal[...]`, `X | None`, `Expr`) y son opcionales si tienen valor por defecto.
3. Docstring: una línea `parametro: descripción` por cada parámetro. Los tests exigen todas.
4. Idiomas:
   - nombres de herramientas, parámetros y claves del resultado en inglés;
   - textos en español.
5. Para fallar: `error("KIND", "mensaje", *pistas)`. Un kind nuevo se agrega en `errores.PISTAS`. Para avisar sin fallar: `sesion.avisar(texto)`.
6. Para buscar pasos o cuerpos: `sesion.paso(ref)` y `sesion.cuerpo(ref)`, que aceptan id o nombre.
7. `modifica=True` hace la llamada atómica y la convierte en UN paso de deshacer (`Sesion.transaccion`).
8. Para llamar una herramienta: `api.llamar(sesion, "nombre", {...})`. Siempre devuelve `{"ok": ...}` y nunca lanza.
9. Regenerar la doc: `omnicad tools --markdown --output docs/agentes/herramientas.md` (desde la raíz del repo).
   El archivo es generado: no se edita a mano, y `tests/test_doc_agentes.py` falla si quedó viejo.

## Registrar el trabajo
**Pendientes: una sola fuente de verdad.** Todo lo que falta resolver vive en `docs/seguimiento/` (`bugs.md`,
`faltantes.md`, `mejoras.md`; método en su `README.md`). Las listas tienen SOLO lo pendiente. Reglas:
- Antes de decir qué está hecho o qué falta, se comprueba en el código y los tests: el log y la memoria envejecen.
- Bug, faltante o mejora nueva: fila nueva en su lista con el siguiente ID libre.
- **Al resolverse, la fila se borra** en el mismo commit que el arreglo (también su ficha de «Detalle» y su ID en
  las tablas del `README.md` de seguimiento), y el Registro de `PROJECT_LOG.md` anota el ID y la prueba que lo cubre.
  `tests/test_seguimiento.py` falla si queda una fila con estado de cerrado o si una evidencia nombra un test que
  no existe.
- Los `docs/brechas_*.md` y `docs/plan_*.md` son especificación: no llevan estados que contradigan el seguimiento.
- Documento nuevo, movido o borrado: se actualiza `docs/README.md` (índice) en el mismo commit.

**Hoja de ruta pública:** el README (sección «Hoja de ruta», y su par en `README.en.md`) resume por tema lo que
falta para que cualquiera pueda tomar algo. Cuando un tema entero se termina o aparece uno nuevo en el
seguimiento, se actualizan los dos README en el mismo turno (una línea por tema, sin detalle técnico).

En `PROJECT_LOG.md`, al terminar:
- **Registro** (sección `## Registro`, una viñeta por tarea):
  `- **AAAA-MM-DD · Fase/tema.** Qué se hizo, archivos clave, verificación (pytest N OK, humo N/N, ruff limpio), bugs hallados y corregidos.`
- **Lección** (sección `## Lecciones aprendidas`, solo con señal verificable: corrección del usuario,
  test que falló, hallazgo con archivo y línea):
  `- [AAAA-MM-DD] Regla accionable en una línea. · Evidencia: test/archivo/comando que lo prueba.`
- Antes de aplicar una lección que nombra un archivo, función o flag, comprobá que siga existiendo.
- Informe final al orquestador: firma de cada función pública, una línea de qué hace, limitaciones honestas
  y salida real de pytest y ruff.
