# Registro de uso local

Apagado de fábrica. Preferencias › General › Registro de uso local, `OmniCAD.py --registro`
o `set_usage_logging(enabled=true)` lo activan. La barra de estado muestra **● REG**.
El flag y la herramienta actúan sobre la sesión; la preferencia persiste entre arranques.

Los JSONL se escriben en `carpeta_datos()/registro/` (`%LOCALAPPDATA%/OmniCAD/registro`
en Windows). No hay envío, sockets ni servicios externos. El primer evento contiene la
versión y los datos del entorno. Cada evento tiene `t`, `ts`, `tipo`, `datos` y `seq`.

Los campos guardan números o longitudes: nunca texto libre, chat, contenido de archivos,
ni rutas de documentos. Del proyecto inicial se guarda solo el nombre. Los errores guardan
categoría y ubicación sin copiar su mensaje (puede contener rutas, expresiones o secretos).
Las claves internas de comando y operación se conservan. Un marcador guarda la longitud de
su nota, no su texto. Las capturas, cuando se solicitan expresamente, contienen el visor.

Un solo hilo escribe cada línea completa y hace flush. El productor no hace E/S y usa
una cola acotada: ante saturación se descartan eventos y el estado informa `dropped`.
Ante fallo de disco se detiene la escritura y el estado informa `error`.
Rotación en segmentos de hasta 5 MB, límite total de 50 MB y retención de 14 días;
la poda se hace al escribir. Solo se podan archivos propios del registro.

## Eventos de la aplicación

Los paneles comunes registran apertura, cambios, aceptación y cancelación con valores
numéricos evaluados, duración y cantidad de cambios. El timeline registra cada paso,
incluidos los reutilizados (duración real de la consulta, no la duración histórica),
el recálculo y sus cinco pasos más lentos, deshacer y rehacer. Los volúmenes se miden
por integración exacta en el escritor, fuera del recálculo. No se agrega teselado.

Los puntos comunes de archivos registran formato, tamaño, duración y éxito. La UI
registra atajos de acciones, botones, menús y selección con costo de picking. El
vigilante de 50 ms informa demoras superiores a 250 ms e inactividad del panel.
Cada cinco segundos informa RSS, formas únicas retenidas por el historial (no todos
los objetos internos del kernel), tiempos de dibujo promedio/p95 y FPS mínimo de los
cuadros dibujados. No se toma la inactividad de una vista quieta como FPS bajo.

Ctrl+Mayús+M o **Marcar problema** abre el marcador con nota opcional (se guarda
su longitud) y captura del visor únicamente con la casilla explícita. Los ganchos
de excepciones y mensajes Qt encadenan los anteriores y se retiran al apagar.

## Detector y resumen

`registro_uso/detector.py` no importa Qt. `analizar(eventos, umbrales=None)` devuelve
hallazgos con regla, severidad (alta/media/baja), momento (`t` y `ts`), qué pasaba y un
borrador de fila para `docs/seguimiento/` con ID `B-?` o `P-?`; nunca escribe el archivo.
`resumir(eventos)` devuelve tiempo y cambios por comando, top 10 de operaciones lentas,
cantidad de errores, recálculos, picking promedio y hallazgos por severidad.

Reglas y umbrales (`UMBRALES`, todos ajustables): operación > 2 s; apertura > 10 s;
bloqueo de interfaz > 250 ms; visor con p95 < 15 FPS; mismo comando con 2 fallas
seguidas; 3 cancelaciones seguidas del mismo comando; Deshacer a menos de 3 s de una
operación; diálogo sin actividad > 20 s; más de 4 clics al mismo control en 2 s;
memoria +30 % en 5 minutos sin abrir un proyecto; excepciones de Qt, de la API y errores
de operación (los avisos se informan como severidad baja). Los hallazgos repetidos se
agrupan con una ventana corta para que el informe no se llene de copias.

## Herramientas y modo en vivo

Grupo `avanzado` del catálogo (MCP y CLI): `set_usage_logging(enabled)`,
`get_usage_log(since, kinds, limit, session)`, `get_usage_summary(session, thresholds)`,
`mark_usage_event(label)` y `build_usage_report(session)`. `get_usage_log` devuelve
`last_seq` para seguir en vivo con `since`; `mark_usage_event` guarda la etiqueta como slug
seguro y, en la ventana abierta, entra por el puente a la sesión viva.

`omnicad registro` resume la última sesión; `omnicad registro --seguir --json` imprime un
evento JSON por línea (encabezados y cambios de sesión por stderr) y con `--since N`
reproduce primero lo anterior. El lector (`registro_uso/almacen.py`) recuerda el byte de
cada parte: no relee el archivo entero y espera las líneas a medio escribir.

`build_usage_report` escribe `informe_sesion_<id>.md` en la carpeta del registro con el
resumen, los hallazgos, la línea de tiempo y las filas sugeridas en un bloque de borrador.
**Nunca** escribe en `docs/seguimiento/`: la carga de una fila la decide una persona.
