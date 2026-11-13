# Lista nocturna: pruebas ya verdes (archivado de prueba_nocturna_2026-10-31.md)

## 1. Lo último que estuvo verde (referencia, no vale como cierre)

Pasada sobre `3c7ad28`, 2026-10-31 (anterior a restricciones y patrones del boceto):

| Qué | Resultado |
|---|---|
| ruff | limpio |
| pytest `-W error`, 6 tandas | 1112 + 1148 + 1002 + 1188 + 1218 (1 salteado) + 719 = 6387 OK |
| piezas de ventana `todo.py` (minimizada) | sin ✗ reales (el «23 líneas con ✗» era el texto «0 con ✗»: el conteo del script estaba mal, ya corregido) |
| humo | TODO OK |
| `registro_uso` + `asistente` (ventana visible) | 24 y 124 comprobaciones, 0 ✗ |

