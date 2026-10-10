# Plan: texto y vectores en OmniCAD (2026-10-10)

Objetivo: superar a Fusion en texto y SVG (Fusion: SVG no editable después de insertar, lento, pocas fuentes,
texto en curva limitado).

## Estado actual (leído del código)
- Texto: `restricciones/boceto.py:221` (`Texto`: fuente, altura, ángulo, negrita, cursiva) y
  `nucleo/perfiles.py:311` (`contornos_texto` con OCC `Font_FontMgr`). Sin texto en curva, sin espaciado,
  sin alineación, sin cuadro. OCC solo ve las fuentes de `C:\Windows\Fonts`: **las instaladas "solo para el
  usuario" (`%LOCALAPPDATA%\Microsoft\Windows\Fonts`) no aparecen** → causa probable de "no toma todas mis fuentes".
- SVG: `io_archivos/svg.py` (parser propio, ya lee Bézier) + `ui/comandos/insertar.py:74`. Crea un **boceto
  nuevo**; no se inserta en el boceto activo, no hay caja de control, no se mueve/escala después.

## Fases (en orden)
| # | Fase | Qué incluye | Librería |
|---|---|---|---|
| 1 | Fuentes completas | Leer `C:\Windows\Fonts` + fuentes de usuario + carpeta extra; TTF/OTF/TTC/variables; vista previa de la fuente en el combo; favoritas y recientes; fuente faltante → aviso y reemplazo | `fontTools` |
| 2 | Texto completo | Cuadro de texto multilínea, alineación H/V, espaciado entre letras, interlineado, ancho/alto ajustado al cuadro, voltear H/V, expresiones (`fx`) y parámetros dentro del texto | `fontTools` |
| 3 | Texto en curva | Sobre línea, arco, círculo, spline o arista; lado adentro/afuera, desplazamiento, inicio/centro/fin, ajustar al largo, letras perpendiculares o derechas | propio |
| 4 | SVG en boceto activo | Insertar en el boceto abierto (no solo uno nuevo); elegir capas/grupos; colores→capas; texto del SVG; unidades y viewBox bien | `svg.py` actual (+ `svgelements` si falla con archivos reales) |
| 5 | Caja de transformación | Para cualquier grupo (SVG, texto, selección): mover, escalar (con/sin proporción), rotar, espejar, alinear y distribuir, con manejadores en pantalla y valores exactos; editable después desde el timeline | propio |
| 6 | Herramientas vectoriales | Unir/restar/intersecar perfiles, offset con esquinas redondas/vivas, texto→curvas, editar nodos Bézier, simplificar, cerrar huecos, quitar duplicados | `shapely` u OCC |
| 7 | Velocidad | Guardar curvas como Bézier, no cientos de puntos; caché de glifos; el grupo importado no entra al solver salvo que se "desglose"; meta: SVG de 5000 nodos en < 1 s | propio |
| 8 | Imagen → vector | PNG/JPG a contornos, con umbral y suavizado | `vtracer` |
| 9 | Exportar | Boceto → SVG/DXF (corte láser, vinilo) | propio |

Cada fase: herramienta MCP/CLI equivalente (`api/`), prueba numérica en `tests/` y paso de humo si toca la UI.

## Pendiente de decidir
- Librerías: `fontTools` y `contourpy` ya estaban instaladas y alcanzaron. Para la fase 6 se usa OpenCascade; `shapely` solo si hace falta (pedir OK).

## Estado (2026-10-10)
| Fase | Estado | Con qué modelo |
|---|---|---|
| 1 Fuentes completas | HECHA (`nucleo/fuentes.py`, `list_fonts`, `add_font_folder`) | Sonnet |
| 2 Texto completo | HECHA (incluye `{parámetro}` dentro del texto y vista previa de fuentes en el combo) | Sonnet |
| 3 Texto en curva | HECHA (núcleo, MCP/CLI y clic sobre una curva en la UI) | Opus |
| 4 SVG en boceto activo | HECHA por MCP/CLI (`insert_svg`, `inspect_svg`, capas y colores); en la UI falta insertar dentro del boceto abierto | Sonnet |
| 5 Caja de transformación | HECHA (marco de control en el boceto + `transform_sketch`) | Opus |
| 6 Herramientas vectoriales | HECHA: unir/restar/intersecar, offset, limpiar (repetidas, huecos, alineadas) y nodos (arrastre en la UI, `move_sketch_point`) | Opus |
| 7 Velocidad | HECHA: SVG de 5000 nodos fallaba → 2,5 s (solver por grupos, perfiles 2,4×, caché) | Opus |
| 8 Imagen a vector | HECHA (`trace_image`, comando «Vectorizar imagen») con librerías ya instaladas | Sonnet |
| 9 Exportar boceto a SVG/DXF | HECHA (`export_sketch` y «Guardar como SVG…» en el menú del boceto) | Sonnet |
