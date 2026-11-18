# Propuesta: reglas cortas de OmniCAD

Base del worktree al 18/11/2026: `CLAUDE.md` 23.857 bytes, `AGENTS.md` 16.772 y `docs/coordinacion.md` 28.007; total 68.636. Mantener las reglas de arranque y el manual corto para agentes; consultar el detalle por enlace, según el rol y el ítem. El bloque copiable de la parte 3 se evalúa desde la raíz del repo. No aplicar el recorte sin hacer antes los traslados de la parte 4.

## 1. Regla repetida

Referencias obtenidas con `grep -n`. `CLAUDE.md`, `AGENTS.md` y `docs/coordinacion.md` son las fuentes; los rangos delimitan cada copia. Se agrupa el mandato común aunque las copias tengan distinto alcance o agreguen detalles. Una remisión sin contenido normativo no cuenta como copia.

| Regla repetida | Copias (`archivo:línea`) |
|---|---|
| P1: bocetos → sólido → superficie → construir/inspeccionar/ensamblar; la velocidad es P1. | `CLAUDE.md:10`, `CLAUDE.md:30-45` |
| No tomar P2 mientras quede P1; el detalle de la cola explicita el pedido de Gerardo. | `CLAUDE.md:10`, `CLAUDE.md:22`, `CLAUDE.md:43-45` |
| Solo OpenCascade; OmniKernel suspendido. | `CLAUDE.md:18`, `CLAUDE.md:46-48` |
| Solo `ahora.md` ordena la ejecución. | `CLAUDE.md:11`, `CLAUDE.md:44-45`, `CLAUDE.md:51-53`; aplicación para E9 y E11: `docs/coordinacion.md:180-182`, `docs/coordinacion.md:263` |
| Lotes a las 13 y 19 h; solo el bloqueante entra al momento. | `CLAUDE.md:11`, `CLAUDE.md:54-57`, `docs/coordinacion.md:263` |
| Un ítem por sesión, cerrado antes de tomar el siguiente. | `CLAUDE.md:12`, `CLAUDE.md:51-53`, `CLAUDE.md:148-149`, `AGENTS.md:26-27`, `docs/coordinacion.md:145-148`, `docs/coordinacion.md:157-159`, `docs/coordinacion.md:188-190` |
| Un worktree por ítem. | `CLAUDE.md:51-53`, `CLAUDE.md:62-63`, `CLAUDE.md:148-149`, `docs/coordinacion.md:9-10`, `docs/coordinacion.md:157-159`, `docs/coordinacion.md:188-190` |
| No arreglar lo ajeno al ítem/asignación; dejar constancia. La fila de seguimiento y el informe de archivos ajenos no se reemplazan. | `CLAUDE.md:12`, `AGENTS.md:19-20`, `AGENTS.md:26-27` |
| Máximo 6 iteraciones por tarea, 3 intentos por problema; no repetir la misma prueba. | `CLAUDE.md:12-13`, `CLAUDE.md:22`, `CLAUDE.md:209-214`, `docs/coordinacion.md:248-251` (cómputo y escalado), `docs/coordinacion.md:262` (3 para E11), `docs/coordinacion.md:268` (no repetir) |
| Llegado el tope: parar, avisar con evidencia y siguiente paso; no cerrar sin verificar. | `CLAUDE.md:212-214`, `docs/coordinacion.md:250-251` |
| `main` y el trabajo pesado en la VPS; Windows queda para usar la app y probar a mano, sigue `vps/main`. Python Linux y `xvfb-run -a` para ventanas. | `CLAUDE.md:59-63`, `AGENTS.md:79-81`, `AGENTS.md:87`, `docs/coordinacion.md:5-10`, `docs/coordinacion.md:209-213`, `docs/coordinacion.md:258-261` |
| Hace falta OK para gasto; la VPS tiene tope mensual de USD 290. No instalar paquetes o toolchain sin permiso. | `CLAUDE.md:17`, `CLAUDE.md:26`, `CLAUDE.md:64`, `CLAUDE.md:133`, `AGENTS.md:15`, `docs/coordinacion.md:11-12` |
| `push` solo a pedido; CI verde es un requisito adicional. | `CLAUDE.md:17`, `CLAUDE.md:26`, `CLAUDE.md:83`, `CLAUDE.md:107`, `AGENTS.md:16-17`, `AGENTS.md:55-56` (CI), `docs/coordinacion.md:21`, `docs/coordinacion.md:154-155` |
| No subir privados ni forzar ignorados; conservar las listas y casos concretos. | `CLAUDE.md:17`, `CLAUDE.md:96`, `CLAUDE.md:105-106`, `CLAUDE.md:138`, `AGENTS.md:12-13`, `AGENTS.md:16-17`, `docs/coordinacion.md:106-107`, `docs/coordinacion.md:154` |
| Credenciales fuera de vista y de Git. | `CLAUDE.md:17`, `CLAUDE.md:83`, `AGENTS.md:42-44`, `AGENTS.md:51-52` (no loguear), `docs/coordinacion.md:21` |
| MCP solo en loopback; token y no exposición del puente se detallan en AGENTS. | `CLAUDE.md:17`, `AGENTS.md:51-54` |
| Archivar sesiones terminadas, no borrarlas sin permiso. | `CLAUDE.md:17`, `CLAUDE.md:26`, `docs/coordinacion.md:142-148`, `docs/coordinacion.md:212-213` |
| La sesión corre afectados con turno; si el selector da más de 15 grupos, ítem + importadores directos. | `CLAUDE.md:13-14`, `CLAUDE.md:103`, `CLAUDE.md:164-167`, `CLAUDE.md:199-200`, `AGENTS.md:27-29`, `AGENTS.md:95-101`, `AGENTS.md:106-107`, `AGENTS.md:137`, `docs/coordinacion.md:151-155`, `docs/coordinacion.md:188-190` |
| Comandos pesados con `turno.py`: VPS 5, PC 1. | `CLAUDE.md:13`, `CLAUDE.md:65`, `AGENTS.md:73`, `AGENTS.md:95-101`, `docs/coordinacion.md:19-20`, `docs/coordinacion.md:88-90` (arnés por piezas), `docs/coordinacion.md:204`, `docs/coordinacion.md:209-213` |
| Ruff y tests verdes, evidencia real y `ponytail-review` antes de cerrar. | `CLAUDE.md:14`, `CLAUDE.md:102-104`, `CLAUDE.md:152-161`, `CLAUDE.md:203-204`, `CLAUDE.md:214`, `AGENTS.md:21-29`, `AGENTS.md:106-109`, `AGENTS.md:175-176`, `AGENTS.md:181-182`, `docs/coordinacion.md:151-155`, `docs/coordinacion.md:188-190` |
| Suite completa y humo a cargo del coordinador en el cierre; no son la verificación de cada sesión. | `CLAUDE.md:13-14`, `CLAUDE.md:103`, `CLAUDE.md:164-171`, `CLAUDE.md:199-200`, `AGENTS.md:95-99`, `AGENTS.md:106-107`, `AGENTS.md:137`, `docs/coordinacion.md:151-155` |
| La prueba automática de humo se ejecuta con `OmniCAD.py --prueba-humo`. | `AGENTS.md:84`, `AGENTS.md:91` |
| Pasar integración por `merge-tree` y afectados; solo el coordinador hace commit tras verificar, con `git add` explícito. | `CLAUDE.md:101-107`, `CLAUDE.md:148-149`, `CLAUDE.md:164-167`, `AGENTS.md:16-17`, `docs/coordinacion.md:145-146`, `docs/coordinacion.md:151-155`, `docs/coordinacion.md:264` (E11 no commitea) |
| Invocar `ponytail` al arrancar código y `ponytail-review` antes de cerrarlo; pedirlos en el brief. | `CLAUDE.md:14`, `CLAUDE.md:153-161`, `CLAUDE.md:214`, `AGENTS.md:22-25`, `AGENTS.md:181-182`, `docs/coordinacion.md:155` |
| Consultar `docs/fusion_docs/` antes del arreglo o faltante y comparar el comportamiento, sin adivinar. | `CLAUDE.md:15`, `CLAUDE.md:137-142`, `CLAUDE.md:219-220`, `AGENTS.md:29`, `AGENTS.md:36-39`, `docs/coordinacion.md:105-118`, `docs/coordinacion.md:256`, `docs/coordinacion.md:261` |
| Briefs a sub-sesiones y OpenCode nombran la ayuda de Fusion y cómo buscar. | `CLAUDE.md:143`, `docs/coordinacion.md:136-137`, `docs/coordinacion.md:155` (carpeta) |
| Avisar recursos de entrada en una línea; primero lo barato. Fusion abierto/túnel solo si la ayuda no alcanza; PC apagada o recurso ausente: anotar y seguir. | `CLAUDE.md:216-221`, `docs/coordinacion.md:100-105`, `docs/coordinacion.md:253-256` |
| El maestro o E11 abre Fusion y el túnel; se pide al maestro desde la VPS. El chequeo devuelve `000` si no llega. | `docs/coordinacion.md:100-105`, `docs/coordinacion.md:256` |
| Probar la app como usuario con mouse/teclado, tecleo y valores raros; diez puntos, capturas miradas y ⚠ para huecos. | `CLAUDE.md:16`, `CLAUDE.md:121-128`, `CLAUDE.md:225-230`, `docs/coordinacion.md:71-97`, `docs/coordinacion.md:261` |
| Eventos simulados al widget, cursor real solo para E11 en PC libre o con OK. Humo minimizada no roba foco. | `CLAUDE.md:16`, `CLAUDE.md:125`, `CLAUDE.md:229-230`, `AGENTS.md:102`, `docs/coordinacion.md:73`, `docs/coordinacion.md:92-97` (arnés y excepción de foco), `docs/coordinacion.md:258-261` |
| E11 prueba OmniCAD y Fusion en la PC, no toca código; guarda evidencia reproducible y reporta al coordinador. | `CLAUDE.md:60-61`, `CLAUDE.md:81`, `CLAUDE.md:223-231`, `docs/coordinacion.md:8`, `docs/coordinacion.md:209-211`, `docs/coordinacion.md:258-264` |
| MCP/CLI: cada función nueva o cambiada lleva herramienta, test y doc regenerada; API como catálogo. | `CLAUDE.md:19`, `CLAUDE.md:86-92`, `AGENTS.md:29-30`, `AGENTS.md:139-156` |
| No dejar activo un control que no funciona; gris en el alcance mínimo. | `CLAUDE.md:25`, `AGENTS.md:134-135` (botón sin clave) |
| `docs/seguimiento/` es fuente de pendientes; el Artifact, `PROJECT_CONTEXT.md` y los planes no la reemplazan. | `CLAUDE.md:98-99`, `CLAUDE.md:109-112`, `CLAUDE.md:115-117`, `AGENTS.md:159-167`, `docs/coordinacion.md:47-51`, `docs/coordinacion.md:156` (fases) |
| Antes de declarar estado, comprobar en el código (y tests para seguimiento), no de memoria. | `CLAUDE.md:98-99`, `AGENTS.md:161` |
| Bug, faltante o mejora nueva → fila e ID libre; al resolver, borrar fila y registrar cierre. | `CLAUDE.md:12`, `CLAUDE.md:110-112`, `CLAUDE.md:170-171` (rojos de noche), `AGENTS.md:27`, `AGENTS.md:106-109`, `AGENTS.md:162-166`, `docs/coordinacion.md:205-207` (caza), `docs/coordinacion.md:251` (Parcial), `docs/coordinacion.md:263` (E11) |
| Cierre con seguimiento y Registro al día, sin archivos sueltos ni contradicciones. | `CLAUDE.md:102-104`, `CLAUDE.md:109-112`, `AGENTS.md:106-109`, `AGENTS.md:163-167`, `AGENTS.md:174-184` |
| Artifact manual a las 19 h, una vez por día; al arrancar el coordinador lee agenda y avisa vencidos. | `CLAUDE.md:114-119`, `CLAUDE.md:205-207` (refresco), `docs/coordinacion.md:54-66` |
| Caza sin red ni modelo; consultar comandos y tramitar sus hallazgos. | `CLAUDE.md:173-175`, `AGENTS.md:73` (comandos), `docs/coordinacion.md:195-207` |
| No pedir permiso para pasos ya decididos; reusar sesiones y mandar briefs nuevos con `clear_session` y `SendMessage` cuando corresponda. | `CLAUDE.md:26`, `CLAUDE.md:66-67`, `CLAUDE.md:145-147`, `CLAUDE.md:181-186`, `docs/coordinacion.md:141-148`, `docs/coordinacion.md:218-225` |
| Al cerrar cada ítem de ejecución, nota de traspaso y vaciado por el coordinador; no vaciar/compactar en medio. | `CLAUDE.md:66-67`, `CLAUDE.md:181-186`, `docs/coordinacion.md:145-147` (fases), `docs/coordinacion.md:216-225`, `docs/coordinacion.md:243-244` |
| Al tope de contexto avisar y hacer traspaso; maestro y coordinador se reemplazan, mismo título y Remote Control, sin colgar sesiones. | `CLAUDE.md:20`, `CLAUDE.md:26`, `CLAUDE.md:181-186`, `docs/coordinacion.md:23-41`, `docs/coordinacion.md:215-225` |
| Elegir modelo y esfuerzo por ítem, mínimo suficiente; cambiar entre ítems; Opus alto para lo delicado, scripts/alternativas baratas para lo mecánico; Fable solo a pedido por nombre. | `CLAUDE.md:13`, `CLAUDE.md:22`, `CLAUDE.md:66-81` (arranque por carril), `CLAUDE.md:159-160`, `CLAUDE.md:193-197`, `CLAUDE.md:217-220`, `AGENTS.md:27-28`, `docs/coordinacion.md:164-179`, `docs/coordinacion.md:227-246`, `docs/coordinacion.md:254-255`, `docs/coordinacion.md:265-268` |
| Fable solo a pedido expreso por nombre, distinto de invocar la skill `fable-method`. | `CLAUDE.md:196`, `docs/coordinacion.md:240` |
| Leer solo la sección necesaria; no repetir análisis/pruebas ni extender mensajes. | `CLAUDE.md:13`, `CLAUDE.md:21-22`, `CLAUDE.md:198-204`, `CLAUDE.md:210-211`, `AGENTS.md:28`, `AGENTS.md:181-182`, `docs/coordinacion.md:249-250`, `docs/coordinacion.md:268` |
| Informe de sesión: 10 líneas y hallazgos de la revisión, salidas reales. | `CLAUDE.md:14`, `CLAUDE.md:161`, `CLAUDE.md:203-204`, `AGENTS.md:21`, `AGENTS.md:181-182` |
| Medir el semanal al cerrar; avisar desvío/90 %. En rojo, E1–E11 en pausa, OpenCode sigue, coordinador reserva ~5 % para integración diaria y bloqueantes. | `CLAUDE.md:20`, `CLAUDE.md:187-192`, `docs/coordinacion.md:178-182`, `docs/coordinacion.md:270-274` |
| OpenCode/CodeBuddy continuos, gratis y en P1; mantener cola/reserva, rotar y revisar antes de integrar. | `CLAUDE.md:20`, `CLAUDE.md:28`, `CLAUDE.md:79` (E9), `CLAUDE.md:192` (rojo), `docs/coordinacion.md:149-150`, `docs/coordinacion.md:161-193`, `docs/coordinacion.md:272-274` |
| Vigía cada 20 min; retoma el mismo trabajo y rota si falla. Vigilancia humana cada 2 h, distinta del cron. | `CLAUDE.md:28`, `CLAUDE.md:205-207`, `AGENTS.md:73` (función del vigía), `docs/coordinacion.md:175-177`, `docs/coordinacion.md:183-193` |
| Español en código y mensajes; el contrato de API deja en inglés sus identificadores externos. | `AGENTS.md:14`, `AGENTS.md:31-32`, `AGENTS.md:118`, `AGENTS.md:148-150` |
| Núcleo puro, sin Qt; solo `ui/` conoce Qt. API sin Qt ni `mcp`. | `AGENTS.md:33-34`, `AGENTS.md:76-77`, `AGENTS.md:142` |

## 2. Vencida o contradictoria

No se deduce vigencia de un número por el nombre de un archivo ni por una medición pasada. En los choques normativos se conserva la precedencia escrita; el funcionamiento observado en scripts se anota aparte, sin darlo por autorizado ni verificar una crontab en vivo.

| Estado y tema | Parte A (`archivo:línea`) | Parte B (`archivo:línea`) | Lectura para la propuesta |
|---|---|---|---|
| Contradicción: corridas de OpenCode/CodeBuddy. | `CLAUDE.md:3`, `CLAUDE.md:28`: 4 (2+2, modelos distintos). | `docs/coordinacion.md:164-171`, `docs/coordinacion.md:188-190`: 6; cuotas por modelo distintas. `scripts/vigia_opencode.sh:22-26`, `scripts/vigia_opencode.sh:34-37`: 6 por defecto y permite dos del mismo modelo CodeBuddy. | Mantener 4 (2+2 distintos) en la regla corta. Los máximos por modelo del detalle permiten 7 si se leen sin el tope global de 6; no son el mismo reparto. El script queda para reconciliar aparte. |
| Procedimiento desplazado o solapado: quién alimenta y lanza la cola. | `CLAUDE.md:11`, `CLAUDE.md:28`, `CLAUDE.md:79`: `ahora.md` ordena trabajo; el coordinador carga la cola del vigía; E9 orquesta. | `docs/coordinacion.md:180-187`: la fila E9 se llama «la cola» y E9 lanza al cerrar; la reserva y crontab no dependen de E9. | Separar orden de ítems de la cola de ejecución. No retirar a E9 su revisión ni la capacidad de orquestar; el vigía puede encadenar sin sesión. |
| Alcance desactualizado: modelos citados en avisos. | `CLAUDE.md:20`: solo nombra GLM, MiniMax y DeepSeek. | `CLAUDE.md:28`, `docs/coordinacion.md:164-177`: también CodeBuddy, primero según la prueba del 17/11. | En #11 enlazar el protocolo sin fijar otra lista. El detalle distingue selección por tipo de tarea, primer intento y respaldo. |
| Choque entre protocolo y script de cola: plazos, reintentos y verificación. | `docs/coordinacion.md:175-177`, `docs/coordinacion.md:183`, `docs/coordinacion.md:188-193`: sondeo 90 s, a `trabadas/` a la segunda trabada, corrida 1.500 s y afectados + ruff; vigilancia manual ~25 min y deriva a Claude. | `scripts/vigia_opencode.sh:39-51`, `scripts/vigia_opencode.sh:59-68`, `scripts/vigia_opencode.sh:81-92`, `scripts/verif_tarea.sh:3-18`: sondeo 150 s, corrida 2.700 s, rotación hasta agotar opciones y verificación rápida con ruff + importadores directos. | No sustituir los plazos documentados por los del código sin decisión. Distinguir la vigilancia de 2 h del cron de 20 min y la verificación del lanzador de la previa a integrar. |
| Referencia histórica: frecuencia anterior del vigía. | `PROJECT_LOG.md:12`: traspaso de 10 min y tareas `*.sh`. | `CLAUDE.md:28`, `docs/coordinacion.md:183`, `scripts/vigia_opencode.sh:15`: 20 min y cola `*.tarea`. | Conservar 20 min; la nota es histórica, no una instrucción para volver al cron anterior. |
| Alcance ambiguo: «de a 5» y «de a UNA». | `CLAUDE.md:13`: cinco sin nombrar máquina; `AGENTS.md:73`, `AGENTS.md:95-101`: «de a uno/UNA» y luego PC 1/VPS 5. | `CLAUDE.md:59-65`, `docs/coordinacion.md:19-20`, `docs/coordinacion.md:209-213`, `scripts/suite_noche.sh:4-8`: cinco turnos en VPS, uno en PC; el cron de suite divide en cuatro partes en la VPS. | Nombrar ambas máquinas y separar concurrencia de comandos, partición de una suite y prohibición de lanzar suites completas desde cada sesión. |
| Procedimiento desplazado: «solo de noche» frente a cron y cierre bajo pedido. | `CLAUDE.md:14`, `CLAUDE.md:164-167`, `CLAUDE.md:199-200`, `AGENTS.md:86-109`, `docs/coordinacion.md:151-153`: suite y humo del cierre, aunque AGENTS muestra los comandos juntos. | `CLAUDE.md:168-171`: cierre completo solo con «corré todo» y sin sesiones ni pedidos abiertos; suite sola cada noche a las 03:15. | No interpretar «corré todo» como requisito del cron, ni los comandos de AGENTS como rutina de cada sesión. |
| Alcance ambiguo: «afectados verdes» con más de 15 grupos. | `CLAUDE.md:14`, `CLAUDE.md:102-104`, `CLAUDE.md:164-167`, `AGENTS.md:106-107`, `docs/coordinacion.md:151-153`: se exige afectados verde. | `CLAUDE.md:13`, `AGENTS.md:95-101`: para la sesión, con más de 15 pide solo ítem + importadores directos. | Hacer visible la excepción en las reglas 4–5; no extenderla al coordinador por analogía. |
| Procedimiento que no cabe aplicar literalmente: no pedir permiso para abrir. | `CLAUDE.md:26`, `CLAUDE.md:145-147`, `docs/coordinacion.md:141-148`: reusar, no pedir permiso ni abrir entre fases. | `docs/coordinacion.md:28-41`: en reemplazos con Remote Control no se puede iniciar desde esa sesión; la app puede requerir que Gerardo escriba el pedido. | Mantener la regla de no pedir OK redundante y su excepción de plataforma; el reemplazo del coordinador/maestro no es el loop de ejecución. |
| Choque de permisos: borrar sesiones al terminar el plan. | `CLAUDE.md:17`, `CLAUDE.md:26`, `docs/coordinacion.md:212`: archivar, no borrar sin OK. | `docs/coordinacion.md:142-148`: prevé borrar al terminar el plan o si Gerardo lo pide. | Terminar un plan no autoriza borrado. Borrar un worktree fusionado es otro procedimiento (`docs/coordinacion.md:157-159`); no mezclarlo con archivar sesiones. |
| Choque de alcance: agregar en el turno un MCP/CLI faltante ajeno al ítem. | `CLAUDE.md:12`, `AGENTS.md:19-20`, `AGENTS.md:26-27`: fuera del ítem se registra, no se arregla de paso. | `CLAUDE.md:86-92`: si falta una herramienta, agregarla en el mismo turno. | Dentro del ítem sí; para un hallazgo ajeno prima la regla 3. No omitir del alcance normal la API, el test ni la doc. |
| Tensión de prioridad: P2 a pedido versus nada de P2 mientras haya P1. | `CLAUDE.md:22`: nada de P2 hasta terminar P1. | `CLAUDE.md:43-45`: P2 si no queda P1 o si Gerardo lo pide. | No introducir una excepción automática: el detalle documenta el pedido explícito de Gerardo y no autoriza tomar P2 por cuenta propia. |
| Choque de ruteo: modelo por tarea versus usar el carril o ampliar el uso de Opus. | `CLAUDE.md:22`, `CLAUDE.md:193-197`: Opus en solver/OCC/núcleo/velocidad, Sonnet para el resto no mecánico. | `CLAUDE.md:66-81` (modelos de partida), `docs/coordinacion.md:227-246` (incluye auditorías, arquitectura y Haiku). | No tratar el carril como modelo fijo; preservar la tabla como partida y la precedencia de CLAUDE, sin borrar el criterio técnico del detalle. |
| Duplicación contra fuente única; nombre de hook histórico. | `CLAUDE.md:3`, `CLAUDE.md:181-192`: aviso 30 %, topes 35/40 %, rojo 90 %; números en el Protocolo. | `CLAUDE.md:20`, `docs/coordinacion.md:178-179`, `docs/coordinacion.md:215-216`, `docs/coordinacion.md:270-274`; `.claude/hooks/ctx25.py:15` confirma `30, 35, 40`. | Dejar los números en el Protocolo, usar «rojo» en las remisiones; `ctx25.py` no indica 25 %. No renombrar el hook ni convertir los cortes vigentes en otros. |
| Medición tomada como regla vigente. | `CLAUDE.md:177-180`: 77 %, 2,7 días y 200–575 mil tokens, medidos el 16/11. | `CLAUDE.md:187-189`, `docs/coordinacion.md:271`: semanal real por `get_usage`; plan fechado hasta fin de noviembre. | Conservar la muestra como historia y el plan fechado como tal; la meta 30/11 y los tramos 19–30/11 no están vencidos al 18/11. No extrapolarlos a diciembre. |
| «Completa» y no garantizada: cobertura de la ayuda local. | `CLAUDE.md:138`, `AGENTS.md:37-39`, `docs/coordinacion.md:106-107`: descargada «completa». | `docs/coordinacion.md:134-137`: cobertura no garantizada, 335 errores y fuentes alternativas. | Llamarla copia local de la ayuda oficial; conservar prioridad, imágenes y qué hacer si falta un artículo. |
| Regla general de idioma frente a excepción de la API. | `AGENTS.md:14`: español también para nombres. | `AGENTS.md:148-150`: herramientas, parámetros y claves en inglés; textos en español. | Dejar explícita la excepción ya escrita, sin traducir contratos. |
| Alcance ambiguo: cuánto pegar de la revisión. | `CLAUDE.md:161`: el coordinador comprueba que se pegó la salida real de la revisión. | `CLAUDE.md:203-204`, `AGENTS.md:181-182`: hallazgos, no toda la salida. | Pegar los hallazgos reales, sin volcar toda la revisión; ruff y tests conservan sus salidas reales. |

## 3. Texto propuesto de CLAUDE.md

Las anclas ASCII nuevas están declaradas en la parte 4. Se crean al trasladar el detalle, antes de instalar este texto; las demás ya corresponden a secciones existentes. Las reglas de arranque de OpenCode siguen copiadas en `AGENTS.md`.

```markdown
# OmniCAD

**Precedencia:** CLAUDE.md > AGENTS.md > docs/coordinacion.md > `~/.claude/CLAUDE.md` global > memoria. La memoria solo enlaza; no fija reglas ni números. Los topes de contexto, el semáforo y sus cupos viven en «Protocolo de ahorro». Consultá el [detalle](docs/coordinacion.md) por sección.

## Reglas de nivel 1

Mandatorias, antes que cualquier otra regla. Valen para el coordinador, E1–E11, OpenCode y el chat maestro.

1. **Orden:** bocetos → sólido → superficie → construir/inspeccionar/ensamblar. Velocidad es P1; el resto, después. [Detalle](docs/coordinacion.md#prioridades-y-kernel).
2. **Cola única:** solo `ahora.md`. Lotes a las 13 y 19 h de Argentina. Solo un bloqueante entra al momento. [Detalle](docs/coordinacion.md#cola-y-bandeja).
3. **Sin desvíos:** cerrá un ítem antes del siguiente, en su worktree. Lo ajeno va como fila nueva, no se arregla de paso. Máximo 6 iteraciones por tarea y 3 intentos por problema. [Detalle](docs/coordinacion.md#límites-de-intentos-cómo-se-cuenta-y-qué-se-informa).
4. **Eficiencia:** modelo y esfuerzo mínimos que alcancen; lectura puntual, mensajes cortos, sin repetir. Solo afectados con turno: VPS 5, PC 1. Si el selector da más de 15 grupos, la sesión corre ítem + importadores directos. [Detalle](docs/coordinacion.md#verificacion-y-noche).
5. **Verificá:** ruff y `tests_afectados.py --correr` verdes (salvo la excepción de #4), con salida real, y `ponytail-review`. Suite y humo son del cierre nocturno. [Detalle](docs/coordinacion.md#verificacion-y-noche).
6. **Copiá Fusion:** si el arreglo o faltante replica un comando de Fusion, leé antes `docs/fusion_docs/` y compará el comportamiento. [Detalle](docs/coordinacion.md#recurso-indispensable-documentación-oficial-de-fusion-360-con-imágenes).
7. **Probá como persona:** mouse, teclado, tecleo y valores raros, con eventos simulados; la API no reemplaza la prueba. Solo E11 usa mouse real, con PC libre u OK. [Detalle](docs/coordinacion.md#regla-estricta-toda-prueba-se-hace-como-un-usuario-humano-habitual).
8. **Seguridad:** sin push, gasto, borrado ni archivos privados sin OK de Gerardo. Archivá sesiones terminadas. Credenciales fuera de vista; MCP solo en `127.0.0.1`. [Detalle](docs/coordinacion.md#seguridad-git-y-contexto-del-proyecto).
9. **Kernel:** solo OpenCascade. OmniKernel suspendido y fuera de «Ahora» y «Sigue». [Detalle](docs/coordinacion.md#prioridades-y-kernel).
10. **MCP y CLI:** función nueva o cambiada lleva herramienta, test y doc regenerada. Completá lo que falte dentro del ítem. [Detalle](docs/coordinacion.md#mcp-y-cli-completos).
11. **Avisos:** avisá al tope de contexto, si el semanal se sale del ritmo o entra en rojo. Mantené OpenCode con trabajo. [Contexto](docs/coordinacion.md#contexto-traspaso-gerardo-2026-11-05-reglas-y-tope-en-claudemd--protocolo-de-ahorro-punto-1) · [Cupo](docs/coordinacion.md#cupo-semanal-de-claude-al-90--gerardo-2026-11-16).
12. **A Gerardo:** 3–5 líneas, resultado primero, ⚠ para riesgos y una sola pregunta. [Detalle](docs/coordinacion.md#mensajes-y-decisiones).
13. **Ahorro sin perder calidad:** prioridad máxima, app usable al 30/11. No tomar P2 mientras quede P1. No dejar capacidad ociosa en lo que suma; gastar menos vale más que agotar cupo. [Detalle](docs/coordinacion.md#regla-estricta-elegir-modelo-y-esfuerzo-por-tarea-ahorrar-tokens-sin-perder-calidad).
14. **App para todos:** interfaz intuitiva y gráfica, de 10 a 100 años. Mensaje de un renglón con ícono, sin jerga. Límites y errores en rojo en asa, campo o previa; muestras visuales, detalle en «?» o ayuda. Adaptá lo existente (P-157/P-158). [Detalle](docs/coordinacion.md#producto-app-para-todos).
15. **No seas complaciente:** ante una mala idea de cualquiera, avisá antes en una línea con razón y alternativa. No la ejecutes para complacer. Si conviene, hacela sin vueltas. [Detalle](docs/coordinacion.md#mensajes-y-decisiones).
16. **En gris lo roto:** desactivá lo mínimo que falla en uso común, no lo lento ni raro. «No disponible: <motivo>», un renglón. Lista central para cinta, menús, paneles y API. Rehabilitá en el commit del arreglo probado. [Detalle](docs/coordinacion.md#producto-app-para-todos).
17. **Actuá sin preguntar** si una regla ya decide; avisá en una línea. Preguntá solo por push/publicación, gasto, borrado, salida externa o dos caminos de producto válidos. Una pregunta, recomendación primero. [Detalle](docs/coordinacion.md#mensajes-y-decisiones).
18. **OpenCode y CodeBuddy:** siempre gratis y en P1; hasta 4 a la vez (2+2, modelos distintos). Coordinador: cola de 8 tareas chicas o más y revisión del diff antes de integrar. Vigía cada 20 min: retoma, rota por falla/cupo y pasa el esfuerzo. [Detalle](docs/coordinacion.md#protocolo-de-opencode-y-codebuddy-gerardo-2026-11-16-y-17-regla-18-de-claudemd).

## Protocolo de ahorro

- **Contexto:** maestro/coordinador 40 %, E1–E11 35 %, aviso 30 % (`ctx25.py`); autocompactado al 70 % solo de respaldo. Al tope no arranques otro ítem. Cerrá el actual y dejá nota de 5 líneas en Registro. El coordinador vacía a E1–E11 con `clear_session` por ítem y manda brief autocontenido. Maestro/coordinador se reemplazan al tope, sin vaciar. Nunca en medio del ítem. [Reemplazo y entrega](docs/coordinacion.md#dirección-del-chat-maestro-gerardo-2026-11-16).
- **Semanal:** `get_usage` al cerrar cada ítem. Ritmo = restante ÷ días al reinicio (jueves 05:00 AR). Plan de noviembre: ~8 % al día hasta 19/11, ~13 % del 19 al 26, ~19 % del 26 al 30 (queda ~10 % para 1–3/12). Verde: 5 sesiones; amarillo (+3 puntos o más): 3, solo P1; rojo (90 %): E1–E11 en pausa, sigue OpenCode. Coordinador activo con ~5 % para lanzar, revisar, rellenar, integrar una vez al día y atender bloqueantes.
- **Modelo por ítem:** el brief fija modelo y esfuerzo; `set_session_model` al vaciar. Opus alto para solver, geometría OCC, núcleo y velocidad; Sonnet medio para lo demás no mecánico; OpenCode gratis o scripts para lo mecánico. Fable solo a pedido por nombre. Empezá con el esfuerzo más bajo que alcance (maestro en bajo), subilo si hace falta y bajalo al cerrar.
- **Lectura y pruebas:** `grep -n`, offset/limit y `tail` o `ctx_execute` para salidas largas. Al abrir, leé solo la última nota «Traspaso <título de la sesión>» y lecciones del tema; ni `PROJECT_LOG.md` ni `APRENDIZAJES.md` enteros. Prima sobre `project-memory`, `aprender` y el global. Afectados al fin del intento, no tras cada edición.
- **Mensajes:** brief de hasta 5 líneas: ID, archivo y [docs/brief.md](docs/brief.md), sin pegar contenido. Informe de hasta 10 líneas más hallazgos de `ponytail-review`, no su salida entera. Entre sesiones: ID, archivo:línea, comando y resultado.
- **Coordinador:** vigila cada 2 h y al cerrar sesiones, integra por tandas. Lee agenda al arrancar y avisa en una línea lo vencido o de hoy. [Artifact](docs/coordinacion.md#página-de-seguimiento-artifact-de-claudeai): refresco a las 19 h; en el lote manda al maestro semanal %, ritmo, color e ítems cerrados.

## Antes de programar o cerrar

- Invocá las skills con la herramienta Skill. Brief obligatorio de código, incluidas sub-sesiones y orquestadores: instrucciones arriba del `prompt`, no solo en `background`. Seguí [docs/brief.md](docs/brief.md) para las skills y la evidencia del informe. E1–E11 y coordinador siguen su brief, no el ruteo global. `ponytail-audit` y `ponytail-debt` si hacen falta.
- Coordinador: commit automático solo al verificar tarea/tanda. Las sesiones no commitean. Al tope de intentos, frená, dejá evidencia y avisá; sin verificar queda Parcial. [Cierre y Git](docs/coordinacion.md#seguridad-git-y-contexto-del-proyecto).
- [Seguimiento](AGENTS.md#registrar-el-trabajo): única fuente de pendientes. Buscá el ID libre en todos los worktrees. Dejá el árbol limpio y los docs coherentes. `PROJECT_CONTEXT.md` se actualiza en el turno, queda local y nunca se fuerza a Git.
- [Rust](docs/coordinacion.md#rendimiento-con-rust): medí primero. Vía rápida o caché: si falla, volvé al camino normal sin exponer el error; probá con un cuerpo ya modificado. Sin eso no se integra.
- [Loop por fases](docs/coordinacion.md#cómo-correr-un-plan-por-fases-en-loop-sin-que-el-usuario-apruebe-nada): reusá con `clear_session` y `SendMessage`; `start_session` solo si no queda ninguna. Cerrá y commiteá antes del próximo ítem. Si la app exige tarjeta, avisá en una línea.
- [E11](docs/coordinacion.md#e11--computer-use-en-la-pc), [caza](docs/coordinacion.md#caza-automática-de-errores) y [avisos de recursos](docs/coordinacion.md#avisos-de-recursos-formato): consultá según la tarea. Sin el recurso, seguí con lo posible y anotá el caso.

@AGENTS.md
```

## 4. Tabla de control

`#1`–`#18` son los números de nivel 1 del bloque, no anclas. `D` = `docs/coordinacion.md`; `D nueva` indica un encabezado a crear con el ancla indicada, copiando el detalle citado antes de recortar. Las fusiones eliminan solo copias, nunca el mandato ni sus condiciones particulares. Las discrepancias de la parte 2 quedan visibles hasta aplicar la precedencia o confirmar el procedimiento operativo.

| Origen en CLAUDE.md | Destino en el texto corto y detalle a conservar |
|---|---|
| `CLAUDE.md:1-7` Título, precedencia y remisiones | Encabezado y precedencia, con enlace a D. |
| `CLAUDE.md:8-9` Alcance nivel 1 | «Reglas de nivel 1», frase inicial. |
| `CLAUDE.md:10` Nivel 1.1: orden | #1; D nueva «Prioridades y kernel» (`#prioridades-y-kernel`), lista y orden completos de 30–48. |
| `CLAUDE.md:11` Nivel 1.2: cola | #2; D nueva «Cola y bandeja» (`#cola-y-bandeja`), trasladar 50–57. |
| `CLAUDE.md:12` Nivel 1.3: sin desvíos | #3 y «Antes de programar o cerrar»; D «Límites de intentos» y «Cola y bandeja»; conservar que prima sobre «arreglá todo» global. |
| `CLAUDE.md:13` Nivel 1.4: eficiencia | #4, Protocolo «Modelo por ítem» y «Lectura y pruebas»; D nueva «Verificación y noche» (`#verificacion-y-noche`) para el procedimiento. |
| `CLAUDE.md:14` Nivel 1.5: verificar | #5; D «Verificación y noche» y cierre de fases. No confundir cierre completo con suite sola. |
| `CLAUDE.md:15` Nivel 1.6: Fusion | #6; D «Recurso indispensable…», 99–137. |
| `CLAUDE.md:16` Nivel 1.7: humano/E11 | #7; D «Toda prueba…» y «E11», 71–97 y 258–264. |
| `CLAUDE.md:17` Nivel 1.8: seguridad | #8; D nueva «Seguridad, Git y contexto del proyecto» (`#seguridad-git-y-contexto-del-proyecto`): incluir autorización, archivo de sesiones, remisión a «Seguridad» de AGENTS y los detalles de 94–107. |
| `CLAUDE.md:18` Nivel 1.9: kernel | #9; D «Prioridades y kernel», rama `motor-omnikernel`, duración «hasta nuevo aviso» y exclusión en 46–48. |
| `CLAUDE.md:19` Nivel 1.10: MCP/CLI | #10; D nueva «MCP y CLI completos» (`#mcp-y-cli-completos`), 86–92 más enlace a Receta C. |
| `CLAUDE.md:20` Nivel 1.11: avisos | #11, #18 y Protocolo de ahorro; D «Contexto», «Cupo semanal» y «Protocolo de OpenCode y CodeBuddy». Quitar solo la lista duplicada de modelos. |
| `CLAUDE.md:21` Nivel 1.12: hablar a Gerardo | #12; D nueva «Mensajes y decisiones» (`#mensajes-y-decisiones`): 21, 24 y 26, en particular el alcance de cada permiso y la diferencia entre mensaje, brief e informe. |
| `CLAUDE.md:22` Nivel 1.13: ahorro | #13 y Protocolo; D «Elegir modelo y esfuerzo» y «Prioridades y kernel», conserva la meta fechada y el orden. |
| `CLAUDE.md:23` Nivel 1.14: app para todos | #14; D nueva «Producto: app para todos» (`#producto-app-para-todos`): trasladar 23 y 25, incluidos ejemplos, P-157, P-158 y P-169. |
| `CLAUDE.md:24` Nivel 1.15: no complacencia | #15 y D «Mensajes y decisiones»: también aplica a ideas del coordinador y de otras sesiones. |
| `CLAUDE.md:25` Nivel 1.16: gris | #16; D «Producto: app para todos»: conservar «rompe, pierde trabajo o no hace nada», alcance mínimo y reactivación en el mismo commit. |
| `CLAUDE.md:26` Nivel 1.17: actuar sin preguntar | #17 y D «Mensajes y decisiones»: mover los ejemplos de pasos ya decididos y hacer explícito que la memoria solo remite a reglas, según la precedencia. |
| `CLAUDE.md:28` Nivel 1.18: OpenCode/CodeBuddy | #18 y D «Protocolo de OpenCode y CodeBuddy»; mantener cola, rotación, esfuerzo y revisión, con el tope de nivel 1 (ver parte 2). |
| `CLAUDE.md:30-48` Qué se trabaja primero, lista 1–4 | #1, #9 y #13; trasladar toda la lista de comandos, orden 1–4, P2, criterio de `ahora.md`, pedido explícito y enlace a `docs/plan_fluidez.md` a D «Prioridades y kernel». |
| `CLAUDE.md:50-57` Cola y bandeja | #2–3 y D «Cola y bandeja»: Ahora/Sigue sin cupo fijo, un ítem, la columna Prioridad no ordena, un mensaje y un commit de IDs por lote, no interrumpir salvo bloqueante con su definición. |
| `CLAUDE.md:59-84` VPS, carriles E1–E11 | #4, #8 y Protocolo; D «Dónde se trabaja» ya cubre VPS, Python, pantalla virtual, gasto, turnos y push. Mover íntegra la tabla E1–E11 de 69–81 y 66–67 a esa sección; corregir su remisión de que la tabla vive solo en CLAUDE. Modelos de partida, no fijos. |
| `CLAUDE.md:86-92` MCP y CLI | #10 y D «MCP y CLI completos»: cinta, menús, opciones y espacios; excepciones justificadas en `docs/brechas_mcp.md`, Receta C, tests y `docs/agentes/herramientas.md` generada. |
| `CLAUDE.md:94-99` PROJECT_CONTEXT.md | «Antes de programar o cerrar» y D «Seguridad, Git y contexto del proyecto»: raíz, maestro local, nunca `git add -f`, fecha y cambio al pie, conteos/enlaces sin duplicar, comprobación en código y revisión por tanda. |
| `CLAUDE.md:101-107` Commit automático | #8 y «Antes de programar o cerrar»; D «Seguridad, Git y contexto del proyecto»: condiciones verdes o rojos preexistentes con fila, seguimiento/Registro/lista nocturna al día, uno por tarea/tanda, archivos explícitos, lista íntegra de exclusiones, IDs en mensaje y restricción de push. |
| `CLAUDE.md:109-112` Bugs, faltantes, mejoras | «Antes de programar o cerrar» y AGENTS «Registrar el trabajo»: fila sale al resolver, ID libre en todos los worktrees, limpieza y coherencia. |
| `CLAUDE.md:114-119` Artifact y agenda | Protocolo «Coordinador» y D 47–69: URL, contenido, autoridad de seguimiento, refresco, prompts, agenda y aviso al arrancar. |
| `CLAUDE.md:121-128` Prueba humana | #7 y D 71–97: diez puntos, skill, arnés, ⚠ para lo no hecho y variantes de la prueba; la API no reemplaza la UI. |
| `CLAUDE.md:130-135` Rust | «Antes de programar o cerrar» y D nueva «Rendimiento con Rust» (`#rendimiento-con-rust`): mover 130–135 íntegro (cuellos, PyO3, medir, permiso toolchain/maturin y prueba/fallback). |
| `CLAUDE.md:137-143` Ayuda Fusion | #6 y D 99–137: fuente, `buscar`/`ver`, carpetas, túnel, no versionar y briefs; calificar cobertura como hace 134–137. |
| `CLAUDE.md:145-150` Loop | «Antes de programar o cerrar» y D 139–159: reuso sin OK redundante, solo abrir si no queda sesión, tarjeta si la app la exige, arreglo → tests → commit sin mezclar ítems y worktree propio. |
| `CLAUDE.md:152-161` Ponytail y brief | «Antes de programar o cerrar», AGENTS reglas absolutas y `docs/brief.md:9-15`: hook, invocación, `fable-method`, `ponytail`, `verify-before-commit`, `omnicad-test` para ventana, `ponytail-review`, y `plan-then-do`/`tool-calling-guard` solo briefs a OpenCode. Conservar en D «Verificación y noche» la obligación del coordinador de comprobar evidencia de la revisión sin exigir todo su volcado, y que OpenCode recibe #3–6 y #10 vía AGENTS. |
| `CLAUDE.md:163-171` Pruebas nocturnas y lista viva | #4–5 y D «Verificación y noche»: trasladar íntegro quién verifica, mínimo de integración, lista `docs/auditorias/prueba_nocturna_2026-10-31.md` al día en el turno, script bajo pedido, cron de 03:15, ruta del resultado, borrar verdes y cargar rojos. |
| `CLAUDE.md:173-175` Caza | «Antes de programar o cerrar» y D 195–207: red/modelos no, plan, comandos y trámite del informe. |
| `CLAUDE.md:177-180` Protocolo: alcance y medición inicial | «Protocolo de ahorro», #13; conservar la muestra de 16/11 y el motivo del contexto chico como antecedente en D «Contexto: traspaso», no como estado actual. |
| `CLAUDE.md:181-186` Protocolo 1: contexto | «Contexto» y D 23–45, 215–225: topes, red al 70 %, traspaso de 5 líneas y reemplazos; pasar junto al detalle de D los casos Remote Control, mismo título, «(viejo)», detach/pin y archivo del maestro. |
| `CLAUDE.md:187-192` Protocolo 2: ritmo | «Semanal», #11 y D «Cupo semanal…»: fórmula, jueves, plan fechado, semáforo, reserva del coordinador y bloqueantes. |
| `CLAUDE.md:193-197` Protocolo 3: modelo | «Modelo por ítem» y D 227–246: cambio al vaciar, especialidades, mecánica, Fable y vuelta al esfuerzo bajo. |
| `CLAUDE.md:198-202` Protocolo 4: lectura y pruebas | «Lectura y pruebas» y #4–5: herramientas de lectura, momento de probar, traspaso propio, precedencia sobre skills globales y pruebas pesadas por script. |
| `CLAUDE.md:203-204` Protocolo 5: mensajes | «Mensajes», D «Mensajes y decisiones», AGENTS «Registrar el trabajo» y `docs/brief.md:5-15`: formato y topes, resultados e informe. |
| `CLAUDE.md:205-207` Protocolo 6: coordinador | «Coordinador» y D «Página de seguimiento», «Dirección del chat maestro» y «Protocolo de OpenCode y CodeBuddy»: tanda, vigilancia, refresco, contenido del lote. |
| `CLAUDE.md:209-214` Límites de intentos | #3 y «Antes de programar o cerrar»; D 248–251: trasladar además dejar constancia en Registro, avisar bloqueo/evidencia/próximo paso y condición de Parcial. |
| `CLAUDE.md:216-221` Recursos | «Antes de programar o cerrar» y D 253–256: línea de aviso, Opus/ultracode/Fusion/túnel, alternativas baratas y qué hacer sin el recurso. |
| `CLAUDE.md:223-231` Computer Use E11 | #7 y enlace E11; D 258–264: mantener modelo base en tabla de carriles, registro de falla, pedir ayuda si bloquea y «complementa, no reemplaza» a arnés/skill. |
| `CLAUDE.md:233` Inclusión | `@AGENTS.md`, sin cambiar qué manual recibe Claude. OpenCode tiene sus reglas operativas directamente en AGENTS. |

**Presupuesto de AGENTS.md.** Tope **11.215 bytes** para que ambos sumen como máximo 20.000. Conservar como base las líneas 1–2, 9–57, 76–78, 86–110 y 139–184: **10.765 bytes** medidos; quedan **450 bytes** para enlaces y ajustes. La base incluye seguridad, separación de Qt, verificación, reglas 3–6 y 10 para OpenCode, receta C y Registro. Trasladar íntegros la presentación (3–8), el mapa (58–75) y cómo arrancar la app (79–85) a `docs/README.md`; recetas A y B (111–138) a D «Recetas de desarrollo». Dejar enlaces a los destinos en AGENTS y corregir remisiones a títulos movidos en los tres documentos. Es un presupuesto de recorte, no una medición de un AGENTS ya reescrito.

**Tamaño del bloque propuesto (`wc -c`, UTF-8, con salto final y sin las cercas Markdown): 8.785 bytes.**
