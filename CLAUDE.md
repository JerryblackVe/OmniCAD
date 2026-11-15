# OmniCAD

Procedimientos largos (VPS, página de seguimiento, prueba como usuario, ayuda de Fusion, loop por fases, caza,
contexto, modelos, memoria de la PC): [docs/coordinacion.md](docs/coordinacion.md). Acá queda la regla corta.

## REGLAS DE NIVEL 1 (mandatorias, Gerardo 2026-11-14 y 15)
Se aplican antes que cualquier otra regla, en el coordinador, E1–E11, OpenCode y el chat maestro.
1. **Orden de trabajo**: bocetos → sólido → superficie → construir/inspeccionar/ensamblar; la velocidad es prioridad 1; lo demás después.
2. **Cola única**: solo `ahora.md`; reportes en lotes de 13 y 19 h; solo un bloqueante entra en el momento.
3. **Sin desvíos**: un ítem por sesión, cerrado antes del siguiente; tope de 6 iteraciones por tarea y 3 intentos por problema.
4. **Eficiencia**: modelo y esfuerzo justos; solo `tests_afectados.py --correr`, de a 5 (`OMNICAD_TURNOS=5`), sin repetir; mensajes cortos; leer solo la sección necesaria. **Si `tests_afectados.py` elige más de 15 grupos** (cambios en el núcleo), la sesión corre solo los tests de su ítem y los de los archivos que importan directo lo que tocó, y la suite completa queda para el cierre nocturno (Gerardo, 2026-11-15, por la cola de tests).
5. **Nada es «listo» sin verificar**: ruff, tests y humo en verde con la salida real, y `ponytail-review`.
6. **Copiar Fusion**: leer `docs/fusion_docs` antes de arreglar; comparar contra Fusion.
7. **Probar como una persona**: mouse, teclado, valores raros; E11 con mouse real solo con la PC libre o el OK de Gerardo.
8. **Seguridad**: sin push, gasto, borrado ni archivos privados sin el OK de Gerardo; credenciales nunca a la vista; MCP solo en 127.0.0.1.
9. **Solo OpenCascade**: OmniKernel suspendido.
10. **Todo en MCP y CLI**: cada herramienta nueva con su versión para agentes, test y doc.
11. **Avisos**: contexto al 65 %, cupo de Claude al 95 %, OpenCode (glm-5.3-flash-free; Sol dado de baja por Gerardo el 2026-11-15) siempre con trabajo.
12. **Hablarle corto a Gerardo**: 3–5 líneas, resultado primero, ⚠ para riesgos, una sola pregunta.
13. **Cuidar los tokens, sin perder calidad (Gerardo, 2026-11-15: prioridad máxima)**: meta, una app usable para el 30/11. Modelo y esfuerzo justos (Opus solo en solver, geometría y núcleo; lo demás en Sonnet; lo mecánico en OpenCode gratis o en scripts); leer solo lo necesario; nada de pruebas ni análisis repetidos; mensajes cortos; nada de prioridad 2 hasta terminar la 1. Sin capacidad ociosa en lo que suma a la meta, pero gastar menos vale más que gastar todo el cupo.
14. **App para todos (Gerardo, 2026-11-15)**: OmniCAD tiene que ser intuitiva y gráfica, y entenderse desde un chico de 10 años hasta una persona de 100. Todo se trabaja bajo esta premisa: mensajes de 1 renglón con ícono y sin jerga, límites y errores mostrados en el dibujo (asa, campo o previa en rojo), muestras visuales en vez de textos largos, y el detalle en un «?» o en la ayuda. Lo que ya existe y no cumple se adapta (P-157, P-158).
15. **Nunca ser complaciente (Gerardo, 2026-11-15)**: si un pedido, un plan o una idea (de Gerardo, del coordinador o de otra sesión) es mala idea, no conviene o no es lo adecuado, decirlo antes de hacerlo, en una línea, con la razón y la alternativa. Como expertos, no se ejecuta algo malo por darle el gusto a nadie; si es buena idea, se hace sin vueltas.

## REGLA ESTRICTA: qué se trabaja primero (Gerardo, 2026-11-10)
«Esto es lo que va a hacer funcional la app, aunque esté incompleta.» La meta es que estas herramientas anden al
100 %, rápido y sin bugs, antes que cualquier otra cosa:
- **Prioridad 1**, en este orden:
  1. **Bocetos**: crear, modificar, restricciones y cotas. Es lo que más importa: sin fallas y rápido.
  2. **Sólido**:
     - Crear: extruir, revolución, barrido, solevación, nervio, red, repujado, agujero, rosca, primitivas, patrón,
       simetría, engrosar.
     - Modificar: pulsar/tirar, empalme, chaflán, vaciado, combinar (booleanas), dividir, mover/copiar.
  3. **Superficie**: crear y modificar.
  4. **Construir** (planos, ejes, puntos, SCU), **Inspeccionar** y **Ensamblar**.
- **La velocidad es parte de la prioridad 1.** Un cuello de botella de esas herramientas entra acá, con Rust si hace
  falta. El orden de la velocidad lo da [docs/plan_fluidez.md](docs/plan_fluidez.md).
- **Prioridad 2**, después: render, animación, simulación, malla, plástico, chapa, dibujo y el resto.
- **Criterio para armar `ahora.md`** (lo que se ejecuta es `ahora.md`): 1) los bugs de la prioridad 1; 2) su
  velocidad; 3) lo que les falte. Un ítem de prioridad 2 entra solo si no queda nada de la 1, o si Gerardo lo pide.
- **OmniKernel suspendido (Gerardo, 2026-11-14):** hasta nuevo aviso no se trabaja nada del kernel propio (rama
  `motor-omnikernel`, OmniKernel). Solo el kernel principal (OpenCascade). Los ítems de OmniKernel no entran en
  `ahora.md` ni en Sigue.

## Cola única y bandeja de entrada (reorganización, Gerardo 2026-11-13)
- **La cola es [docs/seguimiento/ahora.md](docs/seguimiento/ahora.md)**: «Ahora» (un ítem por sesión) y «Sigue» (los
  próximos 10). Lo que no está ahí no se toma. Una sesión tiene un ítem a la vez (cada ítem en su worktree) y toma el
  siguiente recién cuando cerró el suyo. La columna «Prioridad» de las listas no ordena: ordena `ahora.md`.
- **Los reportes de Gerardo llegan del chat de la PC en dos lotes por día (13:00 y 19:00, hora de Argentina)**, un
  mensaje cada uno. Con cada lote el coordinador da todos los ID en un commit, los ubica en la cola y **no saca a
  ninguna sesión de lo que está haciendo**. Solo un **bloqueante** (no puede trabajar, pierde trabajo o la app se
  cierra) entra en el momento.

## Dónde se trabaja: main vive en la VPS de Google (Gerardo, 2026-11-11)
- `main` vive en `omnicad-vps` (`/home/mosos/OmniCAD`; app de Claude › SSH `mosos@34.66.139.76`). La PC de Gerardo
  sigue `vps/main` (remoto `vps`) y sirve para abrir la app y probar a mano la ventana de Windows.
- En Linux: `.venv/bin/python`; lo que abre ventanas va con `xvfb-run -a`. Un worktree por ítem (`~/OmniCAD-<ID>`,
  `scripts/worktree_item.sh`).
- Gasto: tope USD 290/mes. Cambiar la máquina o sumar algo que suba el costo pide su OK.
- Tests de a 5 con `scripts/turno.py` (`OMNICAD_TURNOS=5` en `~/.claude/settings.json` de la VPS; Gerardo, 2026-11-14).
- **Sesiones de ejecución fijas**, una por carril. El coordinador les manda ítems con `SendMessage` (vaciado al 65 %: ver
  la regla de contexto):

  | Sesión | Carril | Modelo |
  |---|---|---|
  | E1 | Bocetos (crear, modificar, restricciones, cotas, solver) | Opus alto |
  | E2 | Sólido › Crear | Opus alto |
  | E3 | Sólido › Modificar | Opus alto |
  | E4 | Superficie | Opus alto |
  | E5 | Construir, Inspeccionar, Ensamblar | Sonnet medio |
  | E6 | Velocidad y Rust | Opus alto |
  | E7 | Pruebas como usuario (prueba_ui, caza, banco de fluidez) | Sonnet medio |
  | E8 | Linux, arreglos chicos, UI, docs | Sonnet medio |
  | E9 | Arreglos de prioridad 1, orquestando OpenCode (glm-5.3-flash-free) para las piezas acotadas | Sonnet medio |
  | E10 | Arreglos de prioridad 1 (archivos `.f3d`, sólidos, GitHub) | según la tarea |
  | E11 | Pruebas con Computer Use en la PC (OmniCAD y Fusion); reporta al chat maestro | Sonnet medio |

- El `push` a GitHub es solo con el pedido de Gerardo (remoto `origin`, `gh` de JerryblackVe; el token nunca en el repo).
- Detalle (OpenCode, herramientas de video, capacidad medida): [docs/coordinacion.md](docs/coordinacion.md).

## REGLA ESTRICTA (sin excepciones): MCP y CLI siempre completos
- TODAS las herramientas de la app están en el MCP y en la CLI, siempre: operaciones, comandos de la cinta, menús
  contextuales, opciones de cada diálogo y espacios de trabajo. Lo único que queda afuera es lo que no le sirve a un
  agente (tema, atajos, paneles), con su razón en `docs/brechas_mcp.md`.
- Toda función nueva o cambiada lleva SIEMPRE su herramienta en `clon/omnicad/api/` (receta C de AGENTS.md).
- No se da por terminada una tarea si falta la herramienta, su test o la doc regenerada (`docs/agentes/herramientas.md`).
- Si encontrás algo de la app sin herramienta, se la agregás en el mismo turno.

## Regla estricta: PROJECT_CONTEXT.md siempre al día (local, nunca a GitHub)
- `PROJECT_CONTEXT.md`, en la raíz, es el documento maestro para que cualquier IA entienda y continúe OmniCAD.
- **No se sube a git** (`.gitignore`). Nunca `git add -f`.
- **Se actualiza en el mismo turno** que cualquier cambio que lo deje viejo. Al pie: `Actualizado: AAAA-MM-DD — qué cambió`.
- **No duplica fuentes de verdad**: da conteos y enlaces a `docs/seguimiento/`; las reglas resumen y enlazan.
- Antes de afirmar algo en él, se verifica en el código. El coordinador lo revisa al cerrar cada tanda.

## Regla: commit automático del coordinador (Gerardo, 2026-11-05)
- **El coordinador hace commit solo, sin preguntar, cada vez que una tarea o tanda queda verificada**: tests verdes
  (los rojos que ya fallaban, con su fila), `ruff check .` limpio y humo OK si se tocó la UI, más seguimiento,
  `PROJECT_LOG.md` y lista nocturna al día. Un commit por tarea o tanda.
- `git add` explícito, archivo por archivo (nunca `privado/`, `analisis/`, `evidencias/`, `docs/fusion_docs/`,
  `PROJECT_CONTEXT.md` ni `.agents/`). Mensaje con qué se hizo y los IDs.
- **El `push` sigue siendo solo con el pedido de Gerardo.** Las sesiones de ejecución no commitean.

## Regla estricta: bugs, faltantes y mejoras en un solo lugar
- Método completo en AGENTS.md › «Registrar el trabajo» (`docs/seguimiento/`, la fila se borra al resolverse).
- El siguiente ID libre se busca mirando **todos los worktrees**, no solo `main`.
- Cada tarea deja el proyecto limpio: sin archivos sueltos ni contradicciones entre documentos.

## Página de seguimiento (Artifact de claude.ai)
- <https://claude.ai/artifact/4oDQpqbDYfnnsmBREjDRbp> («Seguimiento OmniCAD»): bugs, faltantes, mejoras, resueltos,
  prompts y agenda. **No es fuente de verdad** (lo es `docs/seguimiento/`) y **no se actualiza sola**: la refresca el
  coordinador al cerrar una tanda. Pasos, prompts guardados y agenda: [docs/coordinacion.md](docs/coordinacion.md).
- **Al empezar cada sesión, el coordinador lee la agenda (`docs/seguimiento/agenda.md`) y avisa en una línea lo que
  vence hoy o ya venció.**

## Regla estricta: toda prueba se hace como un usuario humano habitual
- Al probar la app se simula a una persona que la usa todos los días: mouse (elegir en el visor, arrastrar asas,
  hover, doble clic), botones, Enter, Esc, Tab y **teclear en los campos** (unidades, expresiones, vacío, 0, negativo,
  enormes), mirando dónde aparece lo escrito y qué mensaje sale. Llamar a la API no reemplaza esto.
- Eventos simulados al widget, nunca el cursor real (skill `omnicad-test`, sección 4b); la única excepción es E11 (ver «Agente de Computer Use»).
- Una prueba de la app está completa solo si cubre los 10 puntos de la lista (cinta, comandos, campos, asas,
  timeline y visor, atajos, guardar/deshacer, ventana chica, pieza real con capturas, sin excepciones en slots de Qt).
  Lo que no se pudo se dice con ⚠. Lista completa y `scripts/prueba_ui/`: [docs/coordinacion.md](docs/coordinacion.md).

## Regla: rendimiento con Rust
- Todo cuello de botella que se pueda pasar a Rust (malla, solver de bocetos, teselado, visor, recálculo) se pasa,
  como módulo puntual vía PyO3. Medir primero, después optimizar. La geometría ya es OpenCascade (C++).
- Instalar el toolchain de Rust/maturin requiere permiso del usuario.
- **Toda vía rápida o caché (Gerardo, 2026-11-14, por B-453):** si falla, cae sola al camino normal sin mostrarle
  su error al usuario, y lleva un test sobre un cuerpo YA modificado por un paso anterior. Sin eso no se integra.

## Recurso indispensable: documentación oficial de Fusion 360
- Está completa en **`docs/fusion_docs/`** (no se sube a git) y es la fuente de verdad de **cómo funciona Fusion**.
- **Se consulta SIEMPRE antes de corregir un bug o agregar un faltante** que replique un comando de Fusion. No se
  programa de memoria.
- Buscar con `clon/.venv/bin/python scripts/fusion_docs.py buscar <palabras> [-s carpeta]` y `ver "<título>"`.
  Carpeta de cada pestaña, trampas y Fusion en vivo por el túnel de la PC: [docs/coordinacion.md](docs/coordinacion.md).
- Los briefs a sub-sesiones y a OpenCode nombran `docs/fusion_docs/` y el comando `scripts/fusion_docs.py buscar`.

## Loop por fases sin que Gerardo apruebe nada
- **OBLIGATORIO (Gerardo, 2026-10-31): no pedirle permiso para abrir sesiones.** El coordinador reusa las que existen
  (`clear_session` + `SendMessage`, sin tarjeta) y llama a `start_session` solo si no queda ninguna.
- **Un ítem cerrado antes del siguiente (Gerardo, 2026-11-06)**: arreglo → tests → commit; nunca dos ítems sin
  commitear juntos. Cada ítem en su worktree.
- Cierre de fase, OpenCode y vigilancia: [docs/coordinacion.md](docs/coordinacion.md).

## Regla obligatoria: ponytail
- **Se INVOCA con la herramienta Skill, no alcanza con leer la regla.** Toda sesión que vaya a tocar código
  (también las sub-sesiones y las que orquestan OpenCode) arranca con `ponytail`, termina con `ponytail-review`, y
  usa `ponytail-audit` / `ponytail-debt` cuando haga falta. Un hook de `.claude/settings.json` lo recuerda.
- **OBLIGATORIO para TODAS las sesiones de código**: el brief lleva ARRIBA DE TODO, en el `prompt` (nunca solo en
  `background`): «invocá con la herramienta Skill `fable-method` y `ponytail` al empezar, `plan-then-do`,
  `tool-calling-guard`, `verify-before-commit` (y `omnicad-test` si prueba la ventana), y `ponytail-review` antes de
  cerrar». El coordinador comprueba en el informe que la sesión pegó la salida real de `ponytail-review`.

## Regla: pruebas pesadas de noche y lista viva
- **Quién verifica qué:** la sesión termina su ítem con `tests_afectados.py --correr` verde (y la humo si tocó la UI,
  cuando la fila lo permite); el coordinador integra y corre la suite completa y la humo en el cierre.
- Mientras haya sesiones o pedidos abiertos **no se lanza el cierre completo** (suite, piezas de ventana, humo). Solo se
  integra y se verifica lo mínimo (git, `merge-tree`, `scripts/tests_afectados.py --correr`).
- Todo lo que falta probar vive en **`docs/auditorias/prueba_nocturna_2026-10-31.md`**. Cada tarea nueva de Gerardo
  la actualiza en el mismo turno.
- El cierre completo corre con `scripts/cierre_completo.sh` solo cuando Gerardo diga «corré todo». Lo verde se borra
  de la lista; lo rojo va a `docs/seguimiento/`.

## Caza automática de errores
- `scripts/caza/` busca errores solo, sin modelos ni red (`docs/plan_caza_errores.md`). Comandos (`rapida`, `noche`,
  `tema`, `repetir`) y qué hacer con el informe: [docs/coordinacion.md](docs/coordinacion.md).

## Regla estricta: aviso de contexto al 65 % (Gerardo, 2026-11-05; 65 % desde 2026-11-11)
- El coordinador mira su contexto (`get_usage`) al cerrar cada tarea o tanda. **Al 60 % avisa; al 65 % no arranca
  nada nuevo:** commit de lo verificado, seguimiento y página al día, nota de traspaso en el Registro de
  `PROJECT_LOG.md`, y le dice a Gerardo en una línea que abra una sesión nueva de coordinación.
- Las sesiones de ejecución hacen lo mismo al 65 %; el coordinador las vacía con `clear_session` entre ítems (nunca
  en medio de uno) y les manda un brief que empieza leyendo su nota. Detalle: [docs/coordinacion.md](docs/coordinacion.md).

## Regla estricta: elegir modelo y esfuerzo por tarea (ahorrar tokens sin perder calidad)
- **Cada tarea lleva su modelo y su esfuerzo elegidos a conciencia**, dichos en una línea ANTES de abrir la sesión o
  mandar el trabajo. Nunca el valor por defecto ni «alto» por reflejo.
- Mecánico o de volumen: Haiku (o OpenCode con GLM). Arreglo chico, UI, tests, docs: Sonnet bajo o medio. Feature o
  refactor: Sonnet medio. Solver, geometría difícil, arquitectura, auditoría: Opus alto.
- **Fable no se usa salvo que Gerardo lo pida por nombre (2026-11-01).** El tope es Opus alto.
- **La calidad del código manda**: si la tarea toca solver, geometría o núcleo, no se baja el esfuerzo para ahorrar.
- No se cambia el modelo de una sesión en marcha salvo que se quede corta. Tabla completa: [docs/coordinacion.md](docs/coordinacion.md).

## Límites de intentos (Gerardo, 2026-11-13)
- Por tarea, como mucho **6 iteraciones** (cambio → prueba → mirar). Por problema, **3 intentos de prueba**, cada uno
  distinto: no se repite una prueba que no aporta nada nuevo.
- Al llegar al tope: parar, anotar en el Registro de `PROJECT_LOG.md` qué se probó y qué salió, y avisar al
  coordinador (bloqueo, evidencia, próximo paso propuesto).
- El tope corta el trabajo, no lo cierra: sin ruff, tests y `ponytail-review` la fila sigue abierta como Parcial.

## Avisos de recursos (Gerardo, 2026-11-13)
- Antes de empezar, la sesión avisa al coordinador en una línea si necesita Opus alto o ultracode (y qué de la tarea
  lo justifica), Fusion abierto o el túnel VPS↔PC (`127.0.0.1:27182`).
- Primero lo barato: la ayuda local (`scripts/fusion_docs.py buscar`) antes que Fusion abierto; el modelo de la
  tabla de «elegir modelo y esfuerzo» antes que uno más caro.
- Sin el recurso, sigue con lo que puede y anota el caso para después.

## Agente de Computer Use: E11 en la PC (Gerardo, 2026-11-13)
- **E11** corre en la PC (Fusion, la ventana de Windows y `mcp__computer-use`). Sonnet medio por defecto.
- Usa OmniCAD y Fusion como un usuario real: mouse, teclado, menús, diálogos y asas. Modela de verdad, captura
  imágenes, graba video si hace falta y compara contra Fusion.
- Cada falla va a `evidencias/reportes_pc/<fecha>_<tema>/` con capturas y pasos reproducibles. Avisa al coordinador,
  que asigna, recibe y decide. Si se bloquea, pide ayuda en vez de insistir.
- Complementa `scripts/prueba_ui` y la skill `omnicad-test`, no los reemplaza. Mueve el cursor real (única excepción a
  «eventos simulados»): corre solo con la PC libre o con el OK de Gerardo. No toca código.
- Detalle: [docs/coordinacion.md](docs/coordinacion.md).

## Consumo de tokens (Gerardo, 2026-11-13)
- Modelo y esfuerzo: los de «elegir modelo y esfuerzo»; lo caro solo donde la complejidad lo justifica.
- Leer la sección que hace falta, no el archivo entero. No releer lo que no cambió. Reusar la evidencia válida; no
  repetir análisis ni pruebas sin motivo.
- Cada sesión carga solo el contexto de su ítem. Lo mecánico va a un script o a un modelo barato; las operaciones
  se agrupan.
- Mensajes entre sesiones: cortos y verificables (ID, archivo:línea, comando y resultado).
- El coordinador mide el gasto con `get_usage` y lo informa al chat de la PC los viernes.

@AGENTS.md
