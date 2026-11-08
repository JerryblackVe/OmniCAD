# OmniCAD

## REGLA ESTRICTA (sin excepciones): MCP y CLI siempre completos
- TODAS las herramientas de la app están en el MCP y en la CLI, siempre. Vale para todo: operaciones,
  comandos de la cinta, menús contextuales, opciones de cada diálogo y espacios de trabajo (DIBUJO,
  RENDERIZAR, ANIMACIÓN…). Lo único que queda afuera es lo que no le sirve a un agente (tema, atajos,
  paneles), y eso se escribe con su razón en `docs/brechas_mcp.md`.
- Toda función nueva o cambiada lleva SIEMPRE su
  herramienta en `clon/omnicad/api/` (receta C de AGENTS.md), y con eso queda en el MCP y en la CLI.
- No se da por terminada una tarea si falta la herramienta, su test o la doc regenerada
  (`docs/agentes/herramientas.md`).
- Si encontrás algo de la app sin herramienta, se la agregás en el mismo turno.

## Regla estricta: PROJECT_CONTEXT.md siempre al día (local, nunca a GitHub)
- `PROJECT_CONTEXT.md`, en la raíz, es el documento maestro para que cualquier IA entienda y continúe OmniCAD:
  qué es, funciones, tecnologías, arquitectura, carpetas, datos, APIs, integraciones, estado, decisiones y cómo seguir.
- **No se sube a git**: está en `.gitignore`. Nunca `git add -f`.
- **Se actualiza en el mismo turno** que cualquier cambio que lo deje viejo: una función, módulo, carpeta,
  dependencia, herramienta del MCP o regla nueva o borrada, o una decisión técnica. Al pie lleva
  `Actualizado: AAAA-MM-DD — qué cambió`.
- **No duplica fuentes de verdad.** La sección de estado da conteos y enlaces a `docs/seguimiento/`, sin copiar filas.
  Las reglas resumen y enlazan a `AGENTS.md` y a este archivo.
- Antes de afirmar algo en él, se verifica en el código. El coordinador lo revisa al cerrar cada tanda.

## Regla: commit automático del coordinador (Gerardo, 2026-11-05)
- **El coordinador hace commit solo, sin preguntar, cada vez que una tarea o tanda queda verificada**: suite completa
  verde (los rojos que ya fallaban en HEAD, con su fila en `docs/seguimiento/`), `ruff check .` limpio y prueba de humo
  OK si se tocó la UI, más seguimiento, `PROJECT_LOG.md` y lista nocturna al día. Un commit por tarea o tanda cerrada,
  antes de lanzar otra tanda de agentes.
- `git add` explícito, archivo por archivo (nunca `privado/`, `analisis/`, `evidencias/`, `docs/fusion_docs/`,
  `PROJECT_CONTEXT.md` ni `.agents/`). Mensaje con qué se hizo y los IDs.
- **El `push` sigue siendo solo con el pedido de Gerardo.** Los agentes y las sesiones de ejecución no commitean
  (`AGENTS.md`): commitea el coordinador después de revisar.

## Regla estricta: bugs, faltantes y mejoras en un solo lugar
- Todo lo que falta resolver se recopila SOLO en `docs/seguimiento/`:
  - `bugs.md`: lo que falla.
  - `faltantes.md`: funciones que no existen.
  - `mejoras.md`: upgrades de lo que ya existe.
  Método y columnas: `docs/seguimiento/README.md`. Índice de toda la doc: `docs/README.md`.
- Lo que se encuentra se agrega ahí al momento, con el siguiente ID libre.
- **Al resolverse, la fila se BORRA** en el mismo commit que el arreglo, y se anota en el Registro de
  `PROJECT_LOG.md` con el ID y la prueba que lo cubre. Las listas tienen solo lo pendiente.
- Antes de informar qué está hecho o qué falta, se verifica contra el código y los tests. Nunca solo con el log.
- Cada tarea deja el proyecto limpio: sin archivos sueltos ni contradicciones entre documentos.

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
  registros y capturas en `evidencias/ui_<hoy>/`. Cubre 1 a 8 y 10; falta automatizar el 9 (pieza completa).
  Piezas: la lista vive solo en `PIEZAS` de `scripts/prueba_ui/todo.py`.
  `todo.py` corre por defecto con la ventana **transparente y sin foco** (`--ventana minimizada`, variable
  `OMNICAD_PRUEBA_VENTANA`): no aparece nada ni se roba el foco, así que Gerardo puede usar la PC. Con
  `--ventana visible` la ventana se ve y toma el foco: ahí no se usa el mouse ni el teclado. Sin la variable, el arnés
  sigue en `visible`. Lo que necesita el foco real de Windows (la pieza `registro_uso` y el chequeo de Ctrl+Mayús+A
  de `asistente`) se saltea con ⚠ en minimizada y exige `--ventana visible`: con la PC en uso se corre al final.
  La lista de esas piezas vive solo en `PIEZAS_CON_FOCO_REAL` de `scripts/prueba_ui/todo.py`.

## Regla: rendimiento con Rust
- La app a veces se siente lenta: la meta es optimizar lo más posible.
- Todo cuello de botella que se pueda pasar a Rust (malla, solver de bocetos, teselado, visor,
  recálculo del timeline) se pasa, como módulo puntual vía PyO3 llamado desde Python.
- Medir primero (perfilar), después optimizar. No reescribir la app entera: la geometría ya es
  OpenCascade (C++).
- Instalar el toolchain de Rust/maturin requiere permiso del usuario.

## Recurso indispensable: documentación oficial de Fusion 360 (con imágenes)
- Está descargada completa en **`docs/fusion_docs/`** (3473 artículos distintos, 8659 imágenes; 4,4 GB; **no se sube
  a git**, está en `.gitignore`). Es la fuente de verdad de **cómo funciona Fusion**.
- **Se consulta SIEMPRE antes de corregir un bug o agregar un faltante** que replique un comando de Fusion: qué
  opciones tiene, cómo se comporta, qué muestra. No se programa de memoria ni se adivina.
- **Cómo encontrar un artículo (no recorrer carpetas a ojo)**, con `clon/.venv/Scripts/python.exe scripts/fusion_docs.py`:
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

## Regla obligatoria: ponytail
- **Se INVOCA con la herramienta Skill, no alcanza con leer la regla.** Toda sesión que vaya a tocar código
  (también las sub-sesiones y las que orquestan OpenCode) arranca con `ponytail`, termina con `ponytail-review`,
  y usa `ponytail-audit` / `ponytail-debt` cuando haga falta. Un hook de `.claude/settings.json` lo recuerda
  al abrir la sesión y antes de cada `git commit`. Los briefs a OpenCode llevan ponytail embebido.
- Usar SIEMPRE la skill `/ponytail` en todo proceso de código donde sea útil o necesario
  (escribir, arreglar, refactorizar, elegir dependencias): el cambio más chico que resuelve
  la tarea completa, sin sobre-ingeniería.
- Usar SIEMPRE la skill `/ponytail-review` antes de dar por terminado un cambio de código:
  revisión de lógica, seguridad, carga real, tests y que cada línea sea necesaria.
- **OBLIGATORIO para TODAS las sesiones de código** («todo prompt a un agente lleva `/fable-method` y `/ponytail`
  al inicio y `/ponytail-review` al final, con la herramienta Skill»; también está en el CLAUDE.md global).
  Cada tarea nueva que Gerardo manda abre una sesión (`start_session`), y su brief lleva ARRIBA DE TODO, en el
  `prompt` (nunca solo en `background`), el bloque: «invocá con la herramienta Skill `fable-method` y `ponytail`
  al empezar, `plan-then-do`, `tool-calling-guard`, `verify-before-commit` (y `omnicad-test` si prueba la ventana),
  y `ponytail-review` antes de cerrar». El coordinador comprueba en el informe que la sesión pegó la salida real
  de `ponytail-review`; si no, se la pide antes de integrar.

## Regla: pruebas pesadas de noche y lista viva
- Mientras haya sesiones o pedidos abiertos **no se lanza el cierre completo** (suite, piezas de ventana, humo):
  queda vieja con el próximo cambio. Solo se integra y se verifica lo mínimo (git, `merge-tree`, `scripts/tests_afectados.py --correr`).
- Todo lo que falta probar vive en **`docs/auditorias/prueba_nocturna_2026-10-31.md`** (la fecha del nombre es la
  del documento vivo; si se renombra, actualizar `docs/README.md`). **Cada vez que Gerardo pasa una tarea nueva,
  el coordinador actualiza esa lista en el mismo turno**: qué piezas y tests nuevos trae, qué quedó sin verificar.
- El cierre completo corre con `scripts/cierre_completo.sh` solo cuando Gerardo diga «corré todo» o lance la
  sesión nocturna. Lo verde se borra de la lista; lo rojo va a `docs/seguimiento/`.

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

## Regla estricta: aviso de contexto al 60 % (Gerardo, 2026-11-05)
- El coordinador mira cuánto lleva lleno su contexto (`get_usage` con `session_id: "self"`) cada vez que cierra una
  tarea o una tanda, y antes de lanzar otra.
- **Al llegar al 55 %, avisa en una línea que se acerca al límite.** **Al llegar al 60 %, no arranca nada nuevo:**
  1. guarda todo: commit de lo verificado; `docs/seguimiento/`, `PROJECT_LOG.md`, la lista nocturna y la página de
     seguimiento al día;
  2. escribe una nota de traspaso en `PROJECT_LOG.md` (Registro): sesiones abiertas y su estado, lo que espera
     revisión, lo que quedó sin commitear y de quién es, y el próximo paso;
  3. le dice a Gerardo en una línea que abra una sesión nueva de coordinación, que arranca leyendo esa nota.
- Lo mismo vale para las sesiones de ejecución: al 60 % cierran su informe y lo dicen, en vez de seguir.

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

@AGENTS.md
