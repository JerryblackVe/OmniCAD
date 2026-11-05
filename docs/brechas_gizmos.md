# Asas de la ventana: que se vean y se entiendan

Especificación de H-60 (cerrado el 2026-11-02; auditoría en `docs/auditorias/asas_2026-11-01.md`). El estado vive solo en `docs/seguimiento/`.

## Qué pasa

Gerardo lo vio el 2026-11-01 en Análisis de sección, con Plano XZ:

- La flecha queda como una mancha azul chica, porque apunta casi hacia la cámara.
- Las cajas de valor `0 mm` y `0 deg` caen encima del asa.
- No se entiende qué se arrastra ni para qué.

**Referencia pedida:** la tríada de Mover, con ejes de colores, arcos de giro, cuadrados de plano y punto central, bien definida
y sin nada encima.

Sospecha sin medir: puede pasar igual en otros comandos que usan `Flecha`, `Angulo` o `Posicion`.

## Dónde está

- `clon/omnicad/ui/manipuladores.py`: `Flecha`, `Angulo`, `Posicion`, `AsaRadial`, `Triada`, `CajaValor`, `GestorManipuladores`.
- `clon/omnicad/ui/comandos/asas_extra.py` y `comandos/modificar.py`: los que ya usan `Triada`.
- `clon/omnicad/ui/comandos/`: unos 25 comandos definen `manipuladores`.
