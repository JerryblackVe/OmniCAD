# Coordinación de OmniCAD: procedimientos

Procedimientos completos que antes vivían en `CLAUDE.md` (movidos el 2026-11-13 por el plan de reorganización que aprobó Gerardo; el texto es el mismo, sin cambios). `CLAUDE.md` deja la regla corta y enlaza acá.

## Dónde se trabaja: main vive en la VPS de Google (Gerardo, 2026-11-11)
- `main` vive en `omnicad-vps` (Google Cloud, Ubuntu 24.04, 8 núcleos AMD, 32 GB), en `/home/mosos/OmniCAD`. Las sesiones de
  código se abren ahí: app de Claude › entorno SSH `mosos@34.66.139.76`, carpeta `/home/mosos/OmniCAD`. La PC de Gerardo
  sigue `vps/main` (remoto `vps`) y sirve para abrir la app y probar a mano la ventana de Windows.
- En Linux: `.venv/bin/python` en lugar de `.venv/Scripts/python.exe`; lo que abre ventanas va con `xvfb-run -a`. Los
  worktrees quedan al lado (`~/OmniCAD-<ID>`, `scripts/worktree_item.sh`). Rust ya está instalado (`omnicad._rs`).
- Gasto: tope de Gerardo USD 290/mes (presupuesto «OmniCAD VPS tope 290» con alertas). Cambiar la máquina o sumar algo
  que suba el costo pide su OK. La VPS no suma cupo de Claude.
- La regla de memoria de la PC (13 GB, `main.log`) no aplica en la VPS: ahí se mira `free -g`.
- OpenCode 1.19.5 instalado en la VPS (`~/.opencode/bin/opencode`, pedido de Gerardo 2026-11-11); cuentas y los 276 modelos de la PC ya copiados (`~/.config/opencode/opencode.json`, `auth.json`; MCP: remotos + `omnicad`).
- Ver videos (skill `watch`, modo local): ffmpeg, yt-dlp (`~/.local/bin`, con pipx) y Deno (`~/.deno/bin`) instalados en la VPS (2026-11-11).
- Capacidad medida (2026-11-11): un pytest pesado ocupa 1,5 GB y ~3 núcleos; la humo, 1,1 GB. El rendimiento tope llega
  con 3-4 corridas a la vez (8 a la vez no rinde más y rompe B-222). Cada sesión de Claude ocupa ~0,35 GB. La memoria
  no limita: el límite es el CPU.
- Tests de a 3 con `scripts/turno.py` (`OMNICAD_TURNOS=3` en `~/.claude/settings.json` de la VPS, no en el repo: la PC
  sigue de a 1). El cupo lo maneja Gerardo. La tabla de sesiones vive solo en `CLAUDE.md`.
- El `push` a GitHub sigue siendo solo con su pedido (remoto `origin` de la VPS; acceso con `gh` de la cuenta JerryblackVe desde el 2026-11-11, token en `~/.config/gh/hosts.yml`, nunca en el repo).

## Página de seguimiento (Artifact de claude.ai)
- Gerardo ve los pendientes en una página: <https://claude.ai/artifact/4oDQpqbDYfnnsmBREjDRbp> («Seguimiento
  OmniCAD», tipo Dashboard, privada hasta que él la comparta). Muestra bugs, faltantes y mejoras con filtros,
  lo último resuelto y los prompts para agentes. **No es fuente de verdad**: la fuente sigue siendo
  `docs/seguimiento/` y los documentos de cada prompt.
- **Prompt nuevo:** se guarda en su documento (`## Prompt para el agente`) y se suma a la tabla «Prompts guardados»
  de `docs/seguimiento/README.md`, en el mismo turno. `tests/test_seguimiento.py` falla si queda afuera.
- **Prompt hecho:** cuando el coordinador revisa y cierra el trabajo de un prompt, borra su sección `## Prompt para el agente`
  (o el documento entero si era solo el prompt) y su fila de «Prompts guardados», y refresca `datasets/prompts`: la
  página muestra solo prompts por hacer o por revisar.
- **No se actualiza sola.** Quien cierra una tanda (el coordinador) la refresca, sin esperar el push:
  1. `python scripts/seguimiento_json.py <carpeta_temporal>` escribe `seguimiento.json`, `resueltos.json`,
     `prompts.json` y `agenda.json` (pendientes de `docs/seguimiento/`, las últimas 25 entradas del Registro de `PROJECT_LOG.md` y
     los prompts guardados).
  2. Subir cada archivo con la herramienta `Artifact` (`url` de la página, `asset: true`, `file_path`; uno por llamada).
  3. Con `ArtifactData` `update`, poner el `source` completo (`format`, `kind`, `name` y la `url` nueva `/_blob/...`) y `updated` = `{at, by}` en `datasets/seguimiento`,
     `datasets/resueltos`, `datasets/prompts` y `datasets/agenda`. Las tarjetas, las tablas y el gráfico se recalculan solos.
- **Agenda (`docs/seguimiento/agenda.md`):** tareas que Gerardo programa para una fecha («agendá X para el
  viernes»). Solo él las pide; el coordinador anota la fila (siguiente AG-n, fecha `AAAA-MM-DD` o «A definir»)
  y refresca la página en ese turno. **Al empezar cada sesión, el coordinador lee la agenda y avisa en una línea
  lo que vence hoy o ya venció.** Hecha la tarea, la fila se borra y va al Registro de `PROJECT_LOG.md`.
- La página no se vuelve a escribir salvo que Gerardo pida un cambio de diseño (documento `files/index.html`).
- Si se pierde el acceso al Artifact, se vuelve a crear desde la herramienta `Artifact` con el tipo Dashboard:
  datasets `seguimiento`, `resueltos`, `prompts` y `agenda` como archivos JSON y las calcs `resumen`, `total` y `por_tema`.

## Regla estricta: toda prueba se hace como un usuario humano habitual
- Al probar la app (a mano, con QTest, MCP en vivo o computer use) se simula a una persona que la usa todos los días:
  movimientos y clics de mouse (elegir en el visor, arrastrar asas, hover, doble clic), botones, Enter, Esc, Tab, y
  **teclear en los campos donde se escriben valores y textos** (unidades, expresiones, vacío, 0, negativo, enormes),
  mirando dónde aparece lo escrito y qué mensaje sale. Llamar a la API o poner un valor por código no reemplaza esto.
- Eventos simulados al widget, nunca el cursor real. Detalle y modelos: skill `omnicad-test`, sección 4b.
- **Una prueba de la app está completa solo si cubre TODO esto** (lo que no se pudo se dice con ⚠):
  1. Cada botón de la cinta y de cada pestaña (clic real) y cada ítem de sus menús.
  2. Cada comando: elegir con el visor, teclear valores en el campo, vista previa, Aceptar, reabrir para editar,
     deshacer, Enter, Esc, Tab.
  3. Cada campo de valor: unidades, coma decimal, expresiones, vacío, 0, negativo, enorme, pegar; ver dónde se
     escribe, el rojo y el mensaje.
  4. Asas de arrastre (arrastrar, pasar por cero, caja de valor al lado).
  5. Timeline (clic, doble clic, clic derecho, botones, marcador), navegador (clic, doble clic, clic derecho) y
     visor (rueda, órbita, desplazar, clic derecho = menú radial).
  6. Atajos de teclado (disparan lo que dicen y no se repiten) y menús.
  7. Guardar, cerrar, reabrir, deshacer y rehacer en cadena.
  8. Ventana chica (1024x640 y 800x520): el panel con Aceptar/Cancelar tiene que entrar.
  9. Una pieza real de principio a fin cambiando una cota, con capturas que se miran de verdad.
  10. Que no se escape ninguna excepción dentro de un slot de Qt.
- **Está automatizado** en `scripts/prueba_ui/` (arnés, escena, un script por pieza): desde `clon/`,
  `.venv/Scripts/python.exe ../scripts/prueba_ui/todo.py [pieza ...]` corre todo de a uno con `turno.py` y deja
  registros y capturas en `evidencias/ui_<hoy>/`. Cubre 1 a 10: el 9 (pieza completa) es la pieza `pieza_completa` (boceto con cotas, extruir, empalme, agujero, cambiar una cota dos veces, guardar y reabrir, deshacer y rehacer en cadena).
  Piezas: la lista vive solo en `PIEZAS` de `scripts/prueba_ui/todo.py`.
  `todo.py` corre por defecto con la ventana **transparente y sin foco** (`--ventana minimizada`, variable
  `OMNICAD_PRUEBA_VENTANA`): no aparece nada ni se roba el foco, así que Gerardo puede usar la PC. Con
  `--ventana visible` la ventana se ve y toma el foco: ahí no se usa el mouse ni el teclado. Sin la variable, el arnés
  sigue en `visible`. Lo que necesita el foco real de Windows (la pieza `registro_uso` y el chequeo de Ctrl+Mayús+A
  de `asistente`) se saltea con ⚠ en minimizada y exige `--ventana visible`: con la PC en uso se corre al final.
  La lista de esas piezas vive solo en `PIEZAS_CON_FOCO_REAL` de `scripts/prueba_ui/todo.py`.

## Recurso indispensable: documentación oficial de Fusion 360 (con imágenes)
- **Fusion de verdad, desde la VPS (2026-11-12).** Fusion solo corre en la PC de Gerardo y se abre solo para comparar. Su MCP
  (`fusion360`, `http://127.0.0.1:27182/mcp`) ya está en `~/.claude.json` de la VPS y llega por un túnel que corre EN LA PC:
  `ssh -N -o ServerAliveInterval=30 -o ExitOnForwardFailure=yes -R 127.0.0.1:27182:127.0.0.1:27182 mosos@34.66.139.76`
  (nunca abrir el puerto en el firewall de Google). Prueba: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:27182/mcp`
  (000 = túnel caído o Fusion cerrado). Abrir Fusion y prender el túnel se pide al chat de la PC o a Gerardo; con la PC
  apagada, la sesión anota el caso para comparar después y sigue. Para saber cómo funciona un comando alcanza la ayuda de abajo.
- Está descargada completa en **`docs/fusion_docs/`** (3473 artículos distintos, 8659 imágenes; 4,4 GB; **no se sube
  a git**, está en `.gitignore`). Es la fuente de verdad de **cómo funciona Fusion**.
- **Se consulta SIEMPRE antes de corregir un bug o agregar un faltante** que replique un comando de Fusion: qué
  opciones tiene, cómo se comporta, qué muestra. No se programa de memoria ni se adivina.
- **Cómo encontrar un artículo (no recorrer carpetas a ojo)**, con `clon/.venv/bin/python scripts/fusion_docs.py` (en Windows, `clon/.venv/Scripts/python.exe`):
  - `buscar <palabras> [-s carpeta]`: texto completo, todas las palabras (prefijos valen); devuelve título, miga de
    pan oficial (libro › capítulo), ruta y fragmento. Ej.: `buscar split body`, `buscar mitered -s fusion-patch`.
  - `ver "<título o parte del nombre>" [-s carpeta]`: el artículo sin la cabecera de «Share» y con las rutas absolutas
    de sus imágenes (se miran con Read). Si el título está en dos carpetas (p. ej. «Thread reference» en `fusion-model`
    y `fusion-cam`) lista las dos: repetir con `-s`.
  - `docs/fusion_docs/indice/<carpeta>.md`: el árbol oficial de cada libro. Se lee entero para saber TODO lo que
    Fusion tiene de un tema (es lo que se usa para comparar una pestaña contra OmniCAD).
  - `mapa`: la tabla de abajo. Si falta `_indice.db` (se borró): `fusion_docs.py construir` (30 s).
- **Dónde está cada pestaña** (carpeta dentro de `contenido/`):

  | OmniCAD / Fusion | Carpeta |
  |---|---|
  | Boceto | `fusion-sketch` |
  | SÓLIDO, **PLÁSTICO** (reglas), construir, inspeccionar (cebra, curvatura), insertar, seleccionar, parámetros, materiales | `fusion-model` |
  | **SUPERFICIE** (en la ayuda se llama «Patch») | `fusion-patch` |
  | MALLA · FORMA (T-Splines) · CHAPA | `fusion-mesh` · `fusion-sculpt` · `fusion-sheet-metal` |
  | Ensamblar (uniones, movimiento) · Configuraciones · Diseños (navegador, historial, lista de materiales) | `fusion-assemble` · `fusion-configurations` · `fusion-designs` |
  | DIBUJO · RENDERIZAR · ANIMACIÓN · SIMULACIÓN · FABRICACIÓN · ELECTRÓNICA · GENERATIVO | `fusion-drawing` · `fusion-render` · `fusion-animate` · `fusion-simulate` · `fusion-cam` · `fusion-ecad` · `fusion-generativedesign` |
  | Interfaz, atajos, preferencias | `fusion-getstarted` |

  Trampas: **`fusion-visor` duplica casi todo lo demás: ignorarlo** (el índice ya lo descarta). `fusion-import` NO es
  importar archivos: son hubs y proyectos (igual que `fusion-manage`, `fusion-extensions`, `fusion-cloudcredits`).
  Las listas «Pages in this section» de los `.md` apuntan todas al padre: usar el índice.
- Cobertura no garantizada (contenido dinámico o no enlazado puede faltar; hay 335 errores de descarga): si un
  artículo no está, decirlo y recurrir a `analisis/fusion_doc/paginas/` (copia de solo texto) o a
  `privado/scripts/ayuda_fusion.py`. Los briefs a sub-sesiones y a OpenCode deben nombrar esta carpeta **y el
  comando `scripts/fusion_docs.py buscar`**.

## Cómo correr un plan por fases en loop, sin que el usuario apruebe nada
Para encadenar fases (p. ej. `docs/plan_boceto.md`) sin que Gerardo esté presente:
- **El chat coordinador ya corre en `bypassPermissions`**: sus comandos no piden permiso. Lo que SÍ pide
  aprobación y corta el loop es **borrar sesiones** (tarjeta en todos los modos) y **abrir sesiones nuevas desde un
  aviso automático** (solo se puede proponer una tarjeta). Por eso **no se borran ni se abren sesiones entre fases**.
- **OBLIGATORIO (Gerardo, 2026-10-31): no pedirle permiso para abrir sesiones.** Prohibido preguntarle si se abre una
  sesión y hacerle aprobar una tarjeta que se puede evitar. El coordinador reusa las sesiones que ya existen
  (`clear_session` + `SendMessage`, sin tarjeta) y llama a `start_session` solo si no queda ninguna para reusar, con
  `mcp__ccd_session__start_session` permitido en `.claude/settings.local.json`. Si aun así la app muestra su tarjeta,
  no hay ajuste que la apague desde acá: se le avisa en una línea.
- **Reusar UNA sesión de ejecución**: al cerrar una fase y commitearla, vaciarla con `clear_session` (en bypass no
  pide aprobación) y mandarle el brief de la fase siguiente con `SendMessage` (anda desde un aviso automático). El
  brief tiene que ser autocontenido (el clear borra el contexto). Se borra la sesión solo al terminar el plan o si
  Gerardo lo pide. La primera sesión la inicia Gerardo con un clic en la tarjeta.
- **Implementar en OpenCode con GPT-6.1 Sol** (`openai/gpt-6.1-sol --variant high`): la sesión orquesta con
  `/orquestador-opencode` y manda corridas chicas (una tarea por corrida) con **`timeout 1500`**; respaldo con `cp`
  antes de cada una. Si una corrida se cuelga (log en 0 bytes, sin CPU ni archivos tocados) o Sol se queda sin cupo,
  se corta solo ese proceso (por hora de inicio) y la pieza la hace Claude (Opus alto). Una sesión inactiva no
  detecta un cuelgue: el coordinador mira el log y los archivos a los ~25 min.
- **Cierre de cada fase (lo hace el coordinador, no la sesión):** `ruff check .` limpio; **suite completa** con
  `scripts/turno.py` en dos mitades (corta a los 900 s): la lista de `tests/test_*.py` ordenada, primera y segunda
  mitad; la prueba de humo si se tocó la UI. Fallos en tests lejanos son regresiones reales: devolverlos a la
  sesión. Recién con todo verde: `git add` explícito (sin `docs/fusion_docs/`, que está ignorada) y commit; el
  `push` solo si Gerardo lo pide. El brief siguiente nombra `docs/fusion_docs/` y exige `ponytail` y
  `ponytail-review`.
- Los informes llegan solos como avisos; no sondear. El estado de cada fase vive en `docs/seguimiento/`.
- **Un ítem cerrado antes del siguiente (Gerardo, 2026-11-06).** Con un agente que arregla varios ítems en la misma
  carpeta, cada ítem termina entero (arreglo → tests → commit) antes de lanzar la corrida del siguiente. Nunca quedan
  dos ítems sin commitear juntos: si un test falla no se sabe cuál lo rompió. Si la fila de tests está ocupada, la
  corrida siguiente espera; si hay que paralelizar, cada ítem va en su propio worktree: `bash scripts/worktree_item.sh
  crear <ID>` crea la rama `item/<ID>` y la carpeta `<repo>-<ID>` (usa el `clon/.venv` del repo principal) y, ya
  fusionada la rama, `bash scripts/worktree_item.sh borrar <ID>` borra las dos.

## Caza automática de errores
- `scripts/caza/` es un programa que busca errores solo, sin modelos ni red: cadenas de operaciones con medidas
  relativas a la pieza, contratos de cada herramienta, archivos alterados, eventos al azar en la ventana y rendimiento.
  Doce jueces automáticos deciden si la pieza quedó bien. Especificación: `docs/plan_caza_errores.md`.
- Comandos, desde `clon/` con el Python del venv:
  - `../scripts/caza/cazar.py rapida`: antes de cada versión (10 min).
  - `../scripts/caza/cazar.py noche --horas 7`: cuando Gerardo lo pida o después de una tanda grande.
  - `../scripts/caza/cazar.py tema empalme`: después de tocar una operación (5 min).
  - `../scripts/caza/cazar.py repetir <firma>`: comprueba un arreglo.
- Hace fila con `scripts/turno.py`, usa solo carpetas temporales y sigue donde estaba si se corta.
- El informe sale en `evidencias/caza_<fecha>/informe.md`. Lo lee quien coordina (Haiku o Sonnet bajo): carga las filas
  en `docs/seguimiento/`, suma la firma a `scripts/caza/conocidos.json` y el caso mínimo a `clon/tests/corpus_caza/`.
  Lo que quedó «sin confirmar» se confirma solo en la corrida siguiente.

## Regla estricta: memoria de la PC (Gerardo, 2026-11-08: «no puede volver a pasar»)
- El 2026-11-07 a las 23:32 la app de Claude se cayó por memoria (9,8 GB de 13: 4 sesiones, OpenCode y varios pytest)
  y la noche se perdió hasta las 06:40.
- **Como mucho 2 sesiones de ejecución trabajando a la vez** (más el coordinador). Las sesiones terminadas o en
  pausa se archivan, porque cada proceso ocupa memoria aunque esté quieto.
- **El coordinador mide la memoria en cada vigilancia**: última línea `process-memory` de
  `%LOCALAPPDATA%/Claude/logs/main.log` (`tree_rss_sum`) más la libre de Windows. Si esa línea tiene más de 30 min
  (el log deja de escribirse a veces: 2026-11-08 quedó en las 18:03), sumar la memoria de los procesos `claude`,
  `node` y `python` (`Get-Process`, columna WS). Si la app pasa de 8 GB o
  quedan menos de 2 GB libres, frena una sesión (`stop_session` y el mensaje «pausa por memoria») antes de lanzar nada.
- Una sola corrida pesada por vez en toda la PC: `scripts/turno.py`, y nunca dos OpenCode.

## Regla estricta: aviso de contexto al 65 % (Gerardo, 2026-11-05; 65 % desde 2026-11-11)
- El coordinador mira cuánto lleva lleno su contexto (`get_usage` con `session_id: "self"`) cada vez que cierra una
  tarea o una tanda, y antes de lanzar otra.
- **Al llegar al 60 %, avisa en una línea que se acerca al límite.** **Al llegar al 65 %, no arranca nada nuevo:**
  1. guarda todo: commit de lo verificado; `docs/seguimiento/`, `PROJECT_LOG.md`, la lista nocturna y la página de
     seguimiento al día;
  2. escribe una nota de traspaso en `PROJECT_LOG.md` (Registro): sesiones abiertas y su estado, lo que espera
     revisión, lo que quedó sin commitear y de quién es, y el próximo paso;
  3. le dice a Gerardo en una línea que abra una sesión nueva de coordinación, que arranca leyendo esa nota.
- Lo mismo vale para las sesiones de ejecución: al 65 % cierran su informe y lo dicen, en vez de seguir.
- **Las sesiones que inició el coordinador se compactan al llegar al 65 % (Gerardo, 2026-11-09; 65 % desde 2026-11-11).** El coordinador
  revisa su contexto con `get_usage` en cada vigilancia. Hay que esperar a que la sesión termine el ítem en curso
  y no tenga nada sin guardar. Entonces la sesión escribe su nota de traspaso en el Registro de `PROJECT_LOG.md`.
  Después el coordinador la vacía con `clear_session` y le manda con `SendMessage` un brief autocontenido que
  empieza leyendo esa nota. No se compacta una sesión en medio de un ítem.

## Regla estricta: elegir modelo y esfuerzo por tarea (ahorrar tokens sin perder calidad)
- **Cada tarea lleva su modelo y su esfuerzo elegidos a conciencia**, y se dicen en una línea ANTES de abrir la
  sesión (`start_session`, `model` y `effort`) o de mandar el trabajo. Nunca el valor por defecto ni «alto» por
  reflejo. El coordinador administra el gasto de tokens de Gerardo: es su responsabilidad.
- Tabla de decisión:

  | Tarea | Modelo | Esfuerzo |
  |---|---|---|
  | Mecánica, formato fijo, mucho volumen, leer/buscar | Haiku 4.5 (o OpenCode con Sol) | sin esfuerzo |
  | Arreglo chico, UI, validaciones, tests, docs | Sonnet 5 | bajo o medio |
  | Feature normal, refactor, revisar un diff | Sonnet 5 | medio |
  | Solver, geometría difícil, arquitectura, auditoría a fondo | Opus 5 | alto |
  | Lo más difícil o agéntico largo, última instancia | Opus 5 | alto |

- **Fable no se usa salvo que Gerardo lo pida por nombre (2026-11-01): consume mucho.** El tope es Opus alto.
- **La calidad del código manda**: si la tarea toca solver, geometría, núcleo o es delicada, no se baja el
  esfuerzo para ahorrar. Se ahorra en lo mecánico, no en lo que decide si el código anda.
- No se cambia el modelo de una sesión en marcha (corta y pierde contexto) salvo que se quede corta.
- Al integrar una sesión, anotar si el modelo elegido alcanzó; si falló por quedarse corto, subir un escalón la
  próxima vez, y si sobró, bajarlo.

## Límites de intentos: cómo se cuenta y qué se informa
- Iteración = un ciclo cambio → prueba → mirar el resultado. Intento de prueba = una hipótesis distinta sobre el mismo problema (otro valor, otra pieza, otro camino). Repetir el mismo comando sin cambiar nada no cuenta como intento nuevo: no se hace.
- Mensaje al coordinador al tocar el tope (SendMessage, 5 líneas como mucho): ID; «tope de iteraciones» o «tope de intentos»; qué se probó (comandos y resultado, archivo:línea); hipótesis que quedan; próximo paso propuesto (otro modelo, otro carril, Fusion abierto, preguntarle a Gerardo).
- El coordinador decide: reasignar, subir modelo un escalón (regla de modelos), partir el ítem o dejarlo Parcial en docs/seguimiento/.

## Avisos de recursos: formato
- Una línea al empezar el ítem: «Recurso: <Opus alto | ultracode | Fusion abierto | túnel 27182> — porque <qué de la tarea lo exige> — alternativa probada: <cuál y por qué no alcanzó>».
- Ultracode (workflows multi-agente) solo en auditorías y jueces, como ya dice la memoria del coordinador; los arreglos siguen en Opus alto.
- Fusion: primero `scripts/fusion_docs.py buscar/ver`. Fusion abierto solo para comparar comportamiento que la ayuda no aclara. Chequeo del túnel: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:27182/mcp` (000 = caído o Fusion cerrado). Abrir Fusion y el túnel se pide al chat de la PC o a Gerardo.

## E11 · Computer Use en la PC
- Dónde: sesión de Claude en la PC de Gerardo, checkout D:/PROGRAMA-noche (o D:/PROGRAMA al día con vps/main). Herramientas: mcp__computer-use (request_access a OmniCAD y Fusion 360), MCP fusion360 local, capturas y grabación.
- Cuándo: solo con la PC libre (Gerardo avisa) o con su OK explícito en el momento. Antes de arrancar, avisa al coordinador; al terminar, devuelve la PC (cierra Fusion si lo abrió, como pide la regla de Fusion).
- Cómo prueba: sigue los 10 puntos de «toda prueba como usuario humano» y la sección 4b de la skill omnicad-test, pero con mouse y teclado reales. Modela una pieza real de principio a fin, cambia una cota, guarda y reabre. Hace lo mismo en Fusion y compara resultado, opciones y mensajes.
- Evidencia por falla en evidencias/reportes_pc/AAAA-MM-DD_<tema>/: capturas (antes/después), video si la falla es de movimiento o tiempo, pasos numerados reproducibles, versión (git rev-parse --short HEAD), qué hace Fusion en el mismo caso. Respeta los límites de intentos (3 por problema).
- Informe al coordinador: un mensaje con la carpeta y una línea por falla. El coordinador asigna ID, carga la fila en docs/seguimiento/ y la ubica en ahora.md (lotes de 13:00 y 19:00; solo un bloqueante entra en el momento).
- No toca código, no commitea, no edita docs/seguimiento/.
## Consumo de tokens: informe de los viernes
- El coordinador junta get_usage de cada sesión E1–E11 y el suyo propio: contexto usado, modelo/esfuerzo, ítems cerrados en la semana.
- Mensaje al chat de la PC, 5 filas como mucho: sesión, modelo, ítems cerrados, gasto, si el modelo alcanzó o sobró (y el ajuste propuesto: subir o bajar un escalón).
- Señales de desperdicio a cortar: archivos leídos enteros sin necesidad, pruebas repetidas sin cambio, mensajes largos entre sesiones, Opus en tareas mecánicas.
