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
