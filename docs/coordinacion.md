# Coordinación de OmniCAD: procedimientos

Procedimientos completos que antes vivían en `CLAUDE.md` (movidos el 2026-11-13 por el plan de reorganización que aprobó Gerardo). `CLAUDE.md` deja la regla corta y enlaza acá.

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
- Ver videos (skill `watch`, modo local; **no está instalada en la VPS**, solo el plugin `watch:watch` de la PC):  ffmpeg, yt-dlp (`~/.local/bin`, con pipx) y Deno (`~/.deno/bin`) instalados en la VPS (2026-11-11).
- Capacidad medida (2026-11-11): un pytest pesado ocupa 1,5 GB y ~3 núcleos; la humo, 1,1 GB. Con pytest pesados el
  rendimiento tope llega con 3-4 a la vez (8 a la vez no rinde más y rompe B-222); las corridas de OpenCode casi no usan
  CPU y tienen su tope en el «Protocolo de OpenCode». Cada sesión de Claude ocupa ~0,35 GB. La memoria
  no limita: el límite es el CPU.
- Tests con `scripts/turno.py` (cuántos a la vez: `CLAUDE.md` › «Dónde se trabaja»; en la PC, de a 1). Ese tope vale
  para las sesiones: la suite nocturna corre en 4 partes por su cuenta y la verificación de la cola (`scripts/verif_tarea.sh`)
  corre sin turno. El cupo lo maneja Gerardo. La tabla de sesiones vive solo en `CLAUDE.md`.
- El `push` a GitHub sigue siendo solo con su pedido (remoto `origin` de la VPS; acceso con `gh` de la cuenta JerryblackVe desde el 2026-11-11, token en `~/.config/gh/hosts.yml`, nunca en el repo).

## Dirección del chat maestro (Gerardo, 2026-11-16)
- `~/chat_maestro.txt` en la VPS: 1.ª línea, el **nombre exacto** de la sesión del chat maestro actual tal como sale en
  `ListAgents`; 2.ª, su id. Cada chat maestro nuevo lo reescribe al arrancar, con el título de la sesión idéntico a esa línea 1 (sin
  «nuevo» ni «(PC)» de más) y archivando o renombrando «(viejo)» la anterior: con dos sesiones de igual título el
  mensaje puede llegar a la equivocada.
- **El coordinador se reemplaza igual que el maestro** (`clear_session` falla con Remote Control): nota de traspaso,
  sesión nueva con el mismo título «Coordinador principal OmniCAD en VPS», **Remote Control prendido** (sin eso el
  maestro no la encuentra por nombre) y la vieja pasa a «(viejo)». Así el nombre no cambia y no necesita archivo.
- **Lista para abrir el reemplazo (maestro o coordinador), todo en el mismo turno** (Gerardo, 2026-11-17, tras dejar
  sesiones colgadas dos veces):
  1. Antes de irse, la vieja hace `detach_session` de TODAS las sesiones que abrió (E1–E11, etc.) y las fija: si no, quedan
     colgadas de «(viejo)» y se archivan con ella.
  2. Abre la nueva el chat maestro desde la PC (`start_session`; el coordinador con host «VPS OMNICAD»). Desde una sesión
     con Remote Control `start_session` no anda; y si el pedido no lo escribió Gerardo en ese turno, la app lo frena:
     pedirle en 1 línea «escribí: abrí el coordinador nuevo» (es la excepción de `CLAUDE.md` › «Loop por fases»).
  3. Recién abierta: `detach_session` de la nueva (no queda colgada de quien la abrió), `set_pinned` true a la nueva y
     false a la vieja, y `move_sessions` al grupo que corresponda.
  4. Remote Control prendido, vieja renombrada «(viejo)», `~/chat_maestro.txt` al día y toda vigilancia (cron) que nombre
     el id viejo, rehecha con el id nuevo.
  5. El brief de la nueva cierra con: «Listo cuando no queda nada pendiente; nunca terminar el turno con trabajo»
     (integración, cola vacía, ítems sin asignar). Gerardo, 2026-11-17.
  6. Antes de dar el reemplazo por cerrado, `list_sessions` y comprobar que haya UNA sola sesión fijada con ese título
     sin «(viejo)»; si hay dos, renombrar y desfijar la vieja en ese momento (Gerardo, 2026-11-18).
  7. Antes de irse, la vieja deja la cola y la reserva de OpenCode llenas según los números de «Cola sin sesiones»
     (Gerardo, 2026-11-18).
- Todo lo que es para Gerardo o el chat maestro (cierres, integraciones, bloqueos, pedidos de OK) va **siempre** por
  `SendMessage` a ese nombre, leído antes de cada envío. Escribirlo solo en el chat del coordinador no alcanza.
- Desde la VPS, el id de una sesión de la PC no llega («not found»): llega solo por el nombre (Remote Control prendido).
  Si el envío falla, avisarle a Gerardo en el chat del coordinador en 1 renglón.

## Página de seguimiento (Artifact de claude.ai)
- Gerardo ve los pendientes en una página: <https://claude.ai/artifact/4oDQpqbDYfnnsmBREjDRbp> («Seguimiento
  OmniCAD», tipo Dashboard, privada hasta que él la comparta). Muestra bugs, faltantes y mejoras con filtros,
  lo último resuelto y los prompts para agentes. **No es fuente de verdad**: la fuente sigue siendo
  `docs/seguimiento/` y los documentos de cada prompt.
- **Prompt nuevo:** se guarda en su documento (`## Prompt para el agente`) y se suma a la tabla «Prompts guardados»
  de `docs/seguimiento/README.md`, en el mismo turno. `tests/test_seguimiento.py` falla si queda afuera.
- **Prompt hecho:** cuando el coordinador revisa y cierra el trabajo de un prompt, borra su sección `## Prompt para el agente`
  (o el documento entero si era solo el prompt) y su fila de «Prompts guardados»; la página lo recoge en el refresco de las 19 h y muestra solo prompts por hacer o por revisar.
- **No se actualiza sola.** Se refresca una vez por día, a las 19 h y solo a esa hora (Protocolo de ahorro de `CLAUDE.md`):
  1. `python scripts/seguimiento_json.py <carpeta_temporal>` escribe `seguimiento.json`, `resueltos.json`,
     `prompts.json` y `agenda.json` (pendientes de `docs/seguimiento/`, las últimas 25 entradas del Registro de `PROJECT_LOG.md` y
     los prompts guardados).
  2. Subir cada archivo con la herramienta `Artifact` (`url` de la página, `asset: true`, `file_path`; uno por llamada).
  3. Con `ArtifactData` `update`, poner el `source` completo (`format`, `kind`, `name` y la `url` nueva `/_blob/...`) y `updated` = `{at, by}` en `datasets/seguimiento`,
     `datasets/resueltos`, `datasets/prompts` y `datasets/agenda`. Las tarjetas, las tablas y el gráfico se recalculan solos.
- **Agenda (`docs/seguimiento/agenda.md`):** tareas que Gerardo programa para una fecha («agendá X para el
  viernes»). Solo él las pide; el coordinador anota la fila (siguiente AG-n, fecha `AAAA-MM-DD` o «A definir»)
  y la página la recoge en el refresco de las 19 h. **Al empezar cada sesión, el coordinador lee la agenda y avisa en una línea
  lo que vence hoy o ya venció.** Hecha la tarea, la fila se borra y va al Registro de `PROJECT_LOG.md`.
- La página no se vuelve a escribir salvo que Gerardo pida un cambio de diseño (documento `files/index.html`).
- Si se pierde el acceso al Artifact, se vuelve a crear desde la herramienta `Artifact` con el tipo Dashboard:
  datasets `seguimiento`, `resueltos`, `prompts` y `agenda` como archivos JSON y las calcs `resumen`, `total` y `por_tema`.

## Regla estricta: toda prueba se hace como un usuario humano habitual
- La regla (mouse, teclado, teclear en los campos, valores raros) está en `CLAUDE.md`; acá, el detalle.
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
  (000 = túnel caído o Fusion cerrado). Fusion y el túnel los abre el chat maestro o E11 en la PC; la sesión de la VPS se lo pide al chat maestro (o a Gerardo); con la PC
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

## Referencia: MitCad (Gerardo, 2026-11-20)
- **Qué es:** CAD paramétrico de escritorio (C++17, Qt6, OpenCascade; Rust para el modelo, el solver y la importación), licencia MIT. Copia local, fuera del repo: `~/referencias/mitcad` (depth 1, commit 72c96ac).
- **Cuándo mirarlo:** solver de bocetos, velocidad e importación con historial (`.f3d`), además de `docs/fusion_docs` y `analisis auto/`. Para el comportamiento de un comando, la fuente sigue siendo Fusion.
- **Cuidado (Gerardo, 2026-11-20: «es un programa en desarrollo igual que el de nosotros, puede tener errores»):** Fusion manda siempre (`docs/fusion_docs`). MitCad sirve para ver cómo se hace algo, no qué hay que hacer. Todo lo que se tome de MitCad entra con su propio test en OmniCAD y se compara contra Fusion; si no coinciden, gana Fusion.
- **Uso:** solo se lee, nunca se ejecuta nada de ahí. Por ser MIT, su código se puede copiar a OmniCAD citando el origen (archivo y commit) en el docstring.

## Cómo correr un plan por fases en loop, sin que el usuario apruebe nada
Para encadenar fases (p. ej. `docs/plan_boceto.md`) sin que Gerardo esté presente:
- **El chat coordinador ya corre en `bypassPermissions`**: sus comandos no piden permiso. Lo que SÍ pide
  aprobación y corta el loop es **borrar sesiones** (tarjeta en todos los modos) y **abrir sesiones nuevas desde un
  aviso automático** (solo se puede proponer una tarjeta). Por eso **no se borran ni se abren sesiones entre fases**.
- **No pedir permiso para abrir sesiones** (regla en `CLAUDE.md` › «Loop por fases»). Si la app igual muestra su tarjeta, no hay ajuste que la apague desde acá: se le avisa en una línea.
- **Reusar UNA sesión de ejecución**: al cerrar una fase y commitearla, vaciarla con `clear_session` (en bypass no
  pide aprobación) y mandarle el brief de la fase siguiente con `SendMessage` (anda desde un aviso automático). El
  brief tiene que ser autocontenido (el clear borra el contexto). Se borra la sesión solo al terminar el plan o si
  Gerardo lo pide. La primera sesión la inicia Gerardo con un clic en la tarjeta.
- **Implementar en OpenCode:** la sesión orquesta con `/orquestador-opencode` siguiendo el «Protocolo de OpenCode»
  (más abajo): modelo, cupo, corridas y vigilancia.
- **Cierre de cada fase (lo hace el coordinador, no la sesión):** `ruff check .` limpio y `scripts/tests_afectados.py
  --correr` verde sobre lo integrado, más `git merge-tree` sin conflicto; la suite completa y la humo corren solas cada
  noche (`CLAUDE.md` › «pruebas pesadas de noche»). Fallos en tests lejanos son regresiones reales: devolverlos a la
  sesión. Recién con eso: `git add` explícito (sin `docs/fusion_docs/`, que está ignorada) y commit; el `push` solo si
  Gerardo lo pide. El brief siguiente nombra `docs/fusion_docs/` y exige `ponytail` y `ponytail-review`.
- El estado de cada fase vive en `docs/seguimiento/`.
- **Un ítem cerrado antes del siguiente** (regla en `CLAUDE.md`): cada ítem va en su worktree, `bash scripts/worktree_item.sh
  crear <ID>` crea la rama `item/<ID>` y la carpeta `<repo>-<ID>` (usa el `clon/.venv` del repo principal) y, ya fusionada
  la rama, `bash scripts/worktree_item.sh borrar <ID>` borra las dos. Los briefs siguen `docs/brief.md`.
- **Limpieza semanal de worktrees (OK de Gerardo, 2026-11-17)**: la crontab corre `scripts/limpiar_worktrees.sh` los domingos
  07:00 UTC. Borra solo worktrees sin cambios sin guardar, sin commits fuera de main, sin tarea en la cola de OpenCode
  y sin proceso adentro; registro en `~/coordinador/limpieza_worktrees.log`. Lo demás se borra a mano tras fusionar.

## Trabajo continuo para todas las EX (Gerardo, 2026-11-21: «para todos los trabajos»)
- Cada `EX_proximo.md` lleva **3 ítems o más, en orden** («después: X, Y, Z»), de cualquier carril; el foco del día primero.
- Se repone cuando le queda 1 ítem, no cuando la EX queda quieta. Nunca el mismo ID a una EX y a OpenCode a la vez (antes de escribir, `grep` del ID en `briefs/` y en `opencode_cola/`).
- La reserva de OpenCode tiene 8 tareas o más; al cerrar un ítem se repone en el mismo turno (`scripts/llenar_cola_opencode.py` desde la raíz del repo).

## Protocolo de OpenCode y CodeBuddy (Gerardo, 2026-11-16 y 17; regla 18 de CLAUDE.md)
Meta: OpenCode trabaja **siempre**. Sus modelos son gratis y ahorran el cupo de Claude. Esta sección es la única regla
de OpenCode; las demás la enlazan.
- **Modelos, en el orden en que los usa el vigía** (la lista que corre es `MODELOS` en `scripts/vigia_opencode.sh`;
  esta tabla la describe):

  | Orden | Modelo | Para qué |
  |---|---|---|
  | 0 (hasta el 23/11) | `opencode-go/glm-5.3`: promo de OpenCode Go (Gerardo, 19/11), primero hasta el domingo 23/11; después vuelve al puesto 6 | Todo, mientras dure; Extra Usage apagado, sin comprar créditos |
  | 1–2 | CodeBuddy gratis: `cb:hy3`, `cb:deepseek-v4.1-flash` (`~/.local/cb/codebuddy -p -y --model <m>`, Node 22 propio) | Lo mecánico; ~8 s, 4 a la vez; corta con 429 al quedarse sin cupo |
  | 3–4 | OpenCode Go gratis (Gerardo, 19/11): `opencode-go/beam-free`, `opencode-go/hy4-flash-free` | Lo mecánico con herramientas; 10–13 s. `iceman-contributor-free` y `longcat-2.5-free` no andan hasta que Gerardo cambie la consola |
  | 5–6 | OpenCode Go con cupo pago (suscripción de Gerardo; Extra Usage apagado, nunca prenderlo ni comprar créditos): `opencode-go/glm-5.3` (~44 s), `opencode-go/kimi-k3.1-pro` (~4 min) | Tareas de varios archivos; si el cupo se acaba, el vigía rota. Descartados en la prueba del 19/11: `gpt-6-luna` (tocó de más), `qwen4-max` (no terminó en 5 min), `deepseek-v4-pro` (falló)
  | 7 | MiniMax: `nvidia/minimaxai/minimax-m3.1-flash` (esa ruta, nunca el alias `nvidia/minimax-m3.1-flash`) | Lo mecánico y varios archivos con herramientas |
  | 8 | OpenAI (ChatGPT Plus de Gerardo, OK del 17/11): `openai/gpt-6.2-sol` | Lo difícil: arreglos de varios archivos y revisión (la tarea lo pide con `MODELO=`) |
  | 9–10 | OpenAI: `openai/gpt-6.2-astra`, `openai/gpt-6.1-terra` | Respaldo |
  | 11 | GLM: `opencode/glm-5.3-flash-free` | Respaldo (no contestó en la prueba de carga del 17/11) |
  | 12 | DeepSeek: `opencode/deepseek-v4.1-flash-free` | Respaldo (no contestó en la prueba de carga del 17/11) |
  | 13 | `opencode/big-pickle` | Último respaldo (anda, pero ~77 s) |

  **Prohibido: nemotron (Gerardo, 21/11).** Ninguna corrida lo usa; ni en `MODELOS` ni con `MODELO=`.

  **Cupo de OpenCode Go (Gerardo, 2026-11-19, vía el chat maestro; el 19/11 iba 26 % de la ventana de 5 h, 10 % del semanal y 5 % del mensual):**
  Actualización 19/11 (semanal al 29 %): Go sirve para TODA tarea de la cola (la suscripción ya está paga y Extra Usage está apagado: al tope corta solo).
  1) Tope por hora de corridas de Go en `VIGIA_GO_HORA` (el vigía no lee el uso de Go, así que las cuenta). 2) Con el semanal al 80 %, el coordinador
  apaga Go con `touch ~/coordinador/opencode_cola/go_apagado` y vuelven los gratis y CodeBuddy; se reanuda borrando ese archivo. 3) Un 429 o «limit» de
  un modelo de Go pausa Go 5 h (`opencode_cola/go_pausa`) y rotan los demás. En el script: `go_libre`, `omitir`.
  Promo de `glm-5.3` (USD 200 de API, hasta el 23/11): también lo frena `go_apagado` y tiene su propio tope por hora (`VIGIA_GLM_HORA`; el semanal de Go subió del 29 al 50 % en 1 h); además lo frena un 429. Después del 23/11 vuelve a las reglas de arriba.
  **Cupo de OpenAI (Gerardo, 2026-11-18):** compartido entre todos los modelos de Codex, con tope cada 5 h y otro semanal
  (el 18/11 se fue el 36 % del semanal en ~12 h). Se guarda para lo difícil; lo mecánico va a CodeBuddy y MiniMax. Un
  «usage limit» no lo da por muerto: el vigía lo vuelve a probar en cada tarea nueva y vuelve solo al reiniciarse las 5 h.
  Con la cuenta ChatGPT NO andan `gpt-5.x`, `gpt-5.4-mini` ni `codex-spark`. La suscripción tiene límite de uso: con
  429 el vigía rota al siguiente, como con CodeBuddy.
  La geometría difícil no va a OpenCode: va a Opus alto. Prohibidos:
  OpenCode Go (sin suscripción) y `mimo` (entrena con los datos).
- **Modelo según el cupo**: si un modelo corta por límite, saldo o error, el vigía pasa la pieza al siguiente de la
  tabla sin preguntar (esta rotación es la excepción a «solo los modelos del brief» de `docs/brief.md`). A mano, prueba:
  `timeout 90 opencode run -m <modelo> "Respondé solo la palabra OK"`.
- **Según el semanal de Claude**: en verde y amarillo, OpenCode hace lo mecánico y las piezas acotadas; en rojo (90 %)
  trabaja solo OpenCode («Cupo semanal de Claude al 90 %»).
- **Quién hace qué**: el vigía lanza las corridas; el coordinador llena la cola (con filas chicas de prioridad 1 de
  `docs/seguimiento/`), revisa el diff e integra. `ahora.md` tiene solo los ítems de las sesiones: su fila de OpenCode
  enlaza a la cola.
- **Vigía sin modelo** (Gerardo, 2026-11-17): `scripts/vigia_opencode.sh` en la crontab de la VPS, cada 20 min: mata una corrida que no escribe hace 20 min (`MIN`) y lanza las `NN_nombre.tarea` de `~/coordinador/opencode_cola/` en orden alfabético hasta el tope de corridas (`WT=`, `BRIEF=`, `MODELO=` y `VARIANTE=` opcionales; cada corrida con `timeout 2700`; log en `vigia.log`). Una tarea trabada o en rojo se relanza con el modelo siguiente y un brief que sigue desde `git diff` + el log; si no queda modelo libre (cupo, 429, sin respuesta) vuelve a la cola para la vuelta siguiente (3 veces como mucho; a la 4.ª, `trabadas/` con aviso), y va a `trabadas/` solo si falló de verdad (error o rojo, sin cupo) con 2 modelos distintos (Gerardo, 2026-11-18). Al terminar bien la verifica `scripts/verif_tarea.sh` (ruff y los tests de los archivos tocados, sin turno, ignora los rojos de main de `~/coordinador/suite_noche/rojos.txt`): verde → `hechos/`.
- **Cola sin sesiones (Gerardo, 2026-11-17: todo verde, sin depender de una sesión)**: el coordinador deja 20 tareas o
  más en `~/coordinador/opencode_cola/reserva/`; el vigía de la crontab las pasa a la cola hasta tener 8 y anota «AVISO
  reserva con menos de 8» cuando hay que reponer. Las de prioridad 2 llevan el prefijo `z_` (corren al final) y las que
  esperan un archivo ocupado, `zz_`. Tareas que tocan una lista compartida (p. ej. los TOPES de un test):
  el brief dice «no toques esa lista»; el coordinador la actualiza una sola vez al integrar, así no hay choques.
- **Reserva que se llena sola (Gerardo, 2026-11-19: «OpenCode nunca más quieto»)**: con la reserva baja, el vigía corre
  `scripts/llenar_cola_opencode.py` (sin modelo): 1) comandos del boceto sin test (`cobertura_boceto.py`) → `PREP-TEST-<clave>`;
  2) filas abiertas de boceto de `bugs.md` que no están en `ahora.md` → `FIX-<ID>` (fila corta) o `PREP-<ID>` (larga); 3) una
  caza de boceto por día; 4) valores raros por comando (`RARO-<clave>`), bancos de velocidad (`BANCO-*`) y revisión de los
  `test_prep_*` (`REV-*`; maestro, 20/11). No repite lo que ya está en la cola, `corriendo`, `hechos`, `descartadas` o `trabadas`; el modelo y
  el cupo de Go los decide el vigía como siempre. Test: `clon/tests/test_llenar_cola_opencode.py`.
- **Tareas chicas (Gerardo, 2026-11-17: los gratis fallaron 24 de 53 corridas, 10 por tiempo)**: una tarea = un archivo y un
  solo cambio (un bug, o hasta 10 mensajes o 5 tests); lo más grande se parte antes de cargarlo. Lo que es solo leer y
  proponer (preparar un bug, medir, revisar listas) deja un `.md` en `docs/seguimiento/preparado/` y no toca la app.
- **Scripts de la cola** (todos sin modelo): `scripts/vigia_opencode.sh` (lanza y rota), `scripts/verif_tarea.sh`
  (verifica), `scripts/limpiar_worktrees.sh` (limpieza semanal), `scripts/suite_noche.sh` (cierre nocturno). Los de
  `~/coordinador/` (`vigilar.sh`, `tanda.sh`, `integrar.sh`, `fusionar.sh`) son ayudas del coordinador, fuera del repo.
- **Cada corrida**: una tarea, en su worktree, con respaldo antes (tgz del vigía). **Tope: hasta 6 corridas a la vez**
  en la VPS (2 por modelo de CodeBuddy y 1 por modelo de OpenCode; Gerardo, 2026-11-17: exprimirlos; `MAX` del vigía);
  en la PC, nunca. La verificación de la cola es `scripts/verif_tarea.sh` (rápida); `tests_afectados.py --correr` es
  la de las sesiones y la corre el coordinador al integrar. La revisión del diff (y `ponytail-review`) es solo del
  coordinador: a main entra solo lo que él revisó.
- **Vigilancia**: el coordinador y el chat maestro, cada 2 h, comprueban que haya corridas activas
  (`ls ~/coordinador/opencode_cola/corriendo`, que ve OpenCode y CodeBuddy) y que la reserva no baje de 8; si baja, la
  rellenan. El aviso «reserva con menos de 8» de `avisos.txt` se atiende en esa misma vuelta, llenando la reserva
  (Gerardo, 2026-11-18). Leen también `avisos.txt` de la cola (trabadas, cola o reserva vacías, ningún modelo responde, pytest
  huérfano cortado) y la hora de `latido`: si tiene más de 1 vuelta, el vigía no corre (crontab o máquina) y se avisa a
  Gerardo. Lo que llega a `trabadas/` lo decide el coordinador (partirlo o pasarlo a una sesión de Claude).
- **Próximo brief escrito de antemano (Gerardo, 2026-11-20)**: al entregar un brief a una sesión EX, el coordinador deja también `~/coordinador/briefs/EX_proximo.md` con su ítem siguiente de «Sigue» (sin ítem, no hay archivo). El chat maestro vigila cada 1 h: si EX está quieta y existe `EX_proximo.md`, la vacía, se lo entrega y lo renombra a `EX_<IDs>.md`. El coordinador integra aparte, sin frenar el reparto.
- **Topes del vigía (nada queda quieto sin corte)**: corrida o verificación sin escribir ni usar CPU en `MIN` min → se
  corta y se relanza con el modelo siguiente; sin modelo libre → vuelve a la cola; falla real con 2 modelos → `trabadas/` con aviso. Corrida: `timeout 2700`;
  verificación: pytest con `timeout 1500`. Sin worktree o sin brief → `trabadas/` sin rotar. Una vuelta a la vez
  (`flock`, se suelta solo si el vigía muere). Pytest huérfano (sin padre) de más de 45 min → se corta con aviso.
  Prueba en seco: `scripts/prueba_vigia_opencode.sh`.

## Protocolo de tests rápidos (Gerardo, 2026-11-18: tests rápidos = feedback rápido para los agentes)
<a id="protocolo-de-tests-rapidos"></a>
- **Tope de un test:** el de AGENTS.md › «Cómo verificar» (pruebas rápidas); no se repite acá.
- **Cada noche** `scripts/suite_noche.sh` corre la suite con `--durations=20` y guarda los 20 tests más lentos de sus 4 partes
  en `~/coordinador/suite_noche/lentos.txt`.
- **Al mirar la suite a la mañana**, el coordinador carga a la reserva de OpenCode una tarea por cada test de `lentos.txt`
  arriba del tope: acelerarlo sin perder lo que prueba (fixture compartida, menos geometría o malla más gruesa) y, si no
  hay otra, marcarlo `@pytest.mark.lento`. Un archivo por tarea; el brief prohíbe tocar las aserciones.
- **`scripts/tests_afectados.py --correr`** corre primero los tests del ítem (los que el cambio toca) con `-x`: si uno falla,
  corta ahí y no espera al resto (falla rápido). Después, el resto de lo elegido.

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

### Caza con el Fusion 360 Gallery Dataset (AG-20, 2026-11-19)
- `scripts/caza/galeria.py` rehace boceto + extruir de diseños reales de Fusion con la API y compara volumen, área y caja
  envolvente con los `properties` del JSON (cm → mm). Sin modelos ni red: los datos ya están en el disco.
- **Datos fuera del repo y nunca a git** (licencia solo investigación): `~/datos/fusion_gallery/r1.0.1/reconstruction/`
  (2,1 GB comprimido; `OMNICAD_GALERIA` cambia la carpeta). Se bajan de
  `fusion-360-gallery-dataset.s3.us-west-2.amazonaws.com/reconstruction/r1.0.1/r1.0.1.zip`.
- Comandos, desde `clon/` con el Python del venv (sin `scripts/turno.py`, que corta a los 900 s: un diseño a la vez, cada uno en su proceso, poca memoria):
  - `../scripts/caza/galeria.py correr --n 500`: ~25 min; informe en `evidencias/galeria_<fecha>/informe.md` y `resultados.json`.
  - `../scripts/caza/galeria.py uno <id>`: un diseño, para reproducir un caso.
- Alcance: curvas línea, arco y círculo, y bocetos paralelos a un plano de origen (la API no arma planos sueltos sin un
  vértice). Lo demás cuenta como «fuera de alcance», no como falla de OmniCAD.
- Quien coordina carga las diferencias y errores en `docs/seguimiento/` **una fila por causa**, con los ids de diseño.

## Memoria de la PC (Gerardo, 2026-11-08)
- La PC tiene 13 GB: ahí corren solo E11 y el chat maestro, **nada de pytest pesado ni de OpenCode** (una sola corrida
  pesada a la vez, con `scripts/turno.py`). El 2026-11-07 la app se cayó por memoria con 4 sesiones, OpenCode y varios pytest.
- Las sesiones terminadas o en pausa se archivan: cada proceso ocupa memoria aunque esté quieto. El trabajo pesado
  corre en la VPS (`free -g`); cuántas sesiones a la vez: Protocolo de ahorro de `CLAUDE.md`.

## Contexto: traspaso (Gerardo, 2026-11-05; reglas y tope en `CLAUDE.md` › Protocolo de ahorro, punto 1)
- El tope se mide sobre el contexto total (hook `.claude/hooks/ctx25.py`, que avisa en el turno siguiente); el número vive solo en `CLAUDE.md`. El coordinador mira el suyo y el de las sesiones con `get_usage`
  al cerrar cada tarea o tanda y antes de lanzar otra.
- Al llegar al tope no se arranca nada nuevo. Se cierra el ítem en curso y se escribe una nota de traspaso de 5 líneas
  en el Registro de `PROJECT_LOG.md` (sesiones abiertas y su estado, lo que espera revisión, lo que quedó sin
  commitear y de quién es, próximo paso). Después, según quién sea:
  - **E1–E11**: el coordinador espera que no tenga nada sin guardar, la vacía con `clear_session` y le manda con
    `SendMessage` un brief autocontenido que empieza leyendo la nota (se vacía al cerrar CADA ítem, Gerardo 2026-11-09).
  - **Coordinador y chat maestro**: sesión nueva con el mismo título, la vieja pasa a «(viejo)»; el maestro además
    reescribe `~/chat_maestro.txt` (ver «Dirección del chat maestro»). Sin `clear_session`.
- No se compacta una sesión en medio de un ítem.

## Regla estricta: elegir modelo y esfuerzo por tarea (ahorrar tokens sin perder calidad)
- **Cada tarea lleva su modelo y su esfuerzo elegidos a conciencia**, y se dicen en una línea ANTES de abrir la
  sesión (`start_session`, `model` y `effort`) o de mandar el trabajo. Nunca el valor por defecto ni «alto» por
  reflejo. El coordinador administra el gasto de tokens de Gerardo: es su responsabilidad.
- Tabla de decisión:

  | Tarea | Modelo | Esfuerzo |
  |---|---|---|
  | Mecánica, formato fijo, mucho volumen, leer/buscar | Haiku 5.5 (o OpenCode con GLM) | sin esfuerzo |
  | Arreglo chico, UI, validaciones, tests, docs | Sonnet 5.5 | bajo o medio |
  | Feature normal, refactor, revisar un diff | Sonnet 5.5 | medio |
  | Solver, geometría OCC, núcleo y velocidad (`CLAUDE.md` › Protocolo de ahorro, punto 3); auditoría a fondo | Opus 5.5 | alto |
  | Solo si Gerardo lo pide por nombre | Fable 5.2 | — |

- **Fable no se usa salvo que Gerardo lo pida por nombre (2026-11-01): consume mucho.** El tope es Opus alto.
- **La calidad del código manda**: si la tarea toca solver, geometría, núcleo o es delicada, no se baja el
  esfuerzo para ahorrar. Se ahorra en lo mecánico, no en lo que decide si el código anda.
- No se cambia el modelo en medio de un ítem salvo que se quede corto. Entre ítems sí: al vaciar la sesión, el
  coordinador le pone el modelo del ítem nuevo con `set_session_model` (Protocolo de ahorro de CLAUDE.md, 2026-11-16).
- Al integrar una sesión, anotar si el modelo elegido alcanzó; si falló por quedarse corto, subir un escalón la
  próxima vez, y si sobró, bajarlo.

## Límites de intentos: cómo se cuenta y qué se informa
- Iteración = un ciclo cambio → prueba → mirar el resultado. Intento de prueba = una hipótesis distinta sobre el mismo problema (otro valor, otra pieza, otro camino). Repetir el mismo comando sin cambiar nada no cuenta como intento nuevo: no se hace.
- Mensaje al coordinador al tocar el tope (SendMessage, 5 líneas como mucho): ID; «tope de iteraciones» o «tope de intentos»; qué se probó (comandos y resultado, archivo:línea); hipótesis que quedan; próximo paso propuesto (otro modelo, otro carril, Fusion abierto, preguntarle a Gerardo).
- El coordinador decide: reasignar, subir modelo un escalón (regla de modelos), partir el ítem o dejarlo Parcial en docs/seguimiento/.

## Avisos de recursos: formato
- Una línea al empezar el ítem: «Recurso: <Opus alto | ultracode | Fusion abierto | túnel 27182> — porque <qué de la tarea lo exige> — alternativa probada: <cuál y por qué no alcanzó>».
- Ultracode (workflows multi-agente) solo en auditorías y jueces, como ya dice la memoria del coordinador; los arreglos siguen en Opus alto.
- Fusion: primero `scripts/fusion_docs.py buscar/ver`. Fusion abierto solo para comparar comportamiento que la ayuda no aclara. Chequeo del túnel: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:27182/mcp` (000 = caído o Fusion cerrado). Fusion y el túnel los abre el chat maestro o E11 en la PC; las sesiones de la VPS se lo piden al chat maestro.

## E11 · Computer Use en la PC
- Dónde: sesión de Claude en la PC de Gerardo, checkout D:/PROGRAMA-noche (o D:/PROGRAMA al día con vps/main). Herramientas: mcp__computer-use (request_access a OmniCAD y Fusion 360), MCP fusion360 local, capturas y grabación.
- Cuándo: solo con el OK explícito de Gerardo en el momento (nunca porque la PC parezca quieta). Antes de arrancar, avisa al coordinador; al terminar, devuelve la PC (cierra Fusion si lo abrió, como pide la regla de Fusion).
- Cómo prueba: sigue los 10 puntos de «toda prueba como usuario humano» y la sección 4b de la skill omnicad-test, pero con mouse y teclado reales. Modela una pieza real de principio a fin, cambia una cota, guarda y reabre. Hace lo mismo en Fusion y compara resultado, opciones y mensajes.
- Evidencia por falla en evidencias/reportes_pc/AAAA-MM-DD_<tema>/: capturas (antes/después), video si la falla es de movimiento o tiempo, pasos numerados reproducibles, versión (git rev-parse --short HEAD), qué hace Fusion en el mismo caso. Respeta los límites de intentos (`CLAUDE.md` › «Límites de intentos»).
- Informe al coordinador (no al chat maestro; este lo ve en el lote): un mensaje con la carpeta y una línea por falla. El coordinador asigna ID, carga la fila en docs/seguimiento/ y la ubica en ahora.md (lotes de 13:00 y 19:00; solo un bloqueante entra en el momento).
- No toca código, no commitea, no edita docs/seguimiento/.
## Informes al chat maestro (única tabla de cadencias)
| Cuándo | Qué |
|---|---|
| Lote de las 19 h | 1 línea: semanal %, ritmo, color e ítems cerrados del día; refresco de la página de seguimiento |
| Viernes | Consumo de tokens por sesión (abajo) |
| Al llegar al 90 % del semanal | Aviso inmediato («Cupo semanal al 90 %») |

## Consumo de tokens: informe de los viernes
- El coordinador junta get_usage de cada sesión E1–E11 y el suyo propio: contexto usado, modelo/esfuerzo, ítems cerrados en la semana.
- Mensaje al chat de la PC, 5 filas como mucho: sesión, modelo, ítems cerrados, gasto, si el modelo alcanzó o sobró (y el ajuste propuesto: subir o bajar un escalón).
- Señales de desperdicio a cortar: archivos leídos enteros sin necesidad, pruebas repetidas sin cambio, mensajes largos entre sesiones, Opus en tareas mecánicas.

## Cupo semanal de Claude al 90 % (Gerardo, 2026-11-16)
- El coordinador mide el semanal con `get_usage` al cerrar cada ítem y avisa al chat maestro en cuanto llega al 90 %.
- Al 90 %: se pausan todas las sesiones de Claude (E1–E11) (el coordinador sigue activo). Hasta el reinicio semanal trabaja solo OpenCode, según el
  «Protocolo de OpenCode». Lo que deja en verde no se integra a main hasta la integración diaria.
- El coordinador se guarda ~5 % del semanal: una integración por día de lo que OpenCode dejó en verde (revisando el diff), y los bloqueantes. Nada más.
