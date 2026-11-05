# Vista previa en proceso aparte: error oculto y demora

Especificación de B-155 y del punto 1 de RS-X6. El estado vive solo en `docs/seguimiento/`.

## Qué pasa

Gerardo lo vio el 2026-11-01 en Empalme y Chaflán, sobre la arista de un agujero, con cuerpos de 64 caras o más:

- El panel dice «El proceso de la vista previa falló (código 0x1)».
- Con un valor bueno, queda «Calculando vista previa en un proceso aparte…» y tarda.

## Causa

- Con 64 caras o más, `ui/comando.py` (`_previa_pesada`) manda la previa a `CalculoPendiente`.
- Un valor imposible hace que el hijo termine con salida 1. El motivo queda en `errores.txt`.
- `CalculoPendiente.sondear` (`nucleo/aislado.py:419`) no lo lee, a diferencia de `_caida`.
- Cada previa arranca un Python nuevo, con prioridad baja, y rehace el documento (P-56 y RS-X6).

## Medido

Placa de 400 × 400 × 10 mm con 70 agujeros de Ø 20, dos pasos, con el cierre completo corriendo:

| Radio | Salida del hijo | Tiempo | Mensaje |
|---|---|---|---|
| 5 mm | 0 | 1,81 s | Previa correcta |
| 9,9 mm | 0 | 1,81 s | Previa correcta |
| 32,329 mm | 1 | 1,34 s | `errores.txt` tiene «El empalme falló: el radio es demasiado grande…»; el panel muestra `código 0x1` |

Script: `evidencias/empalme_previa_2026-11-01/repro.py`.
