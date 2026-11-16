# Auditoría de Patrón rectangular y Patrón circular (P-168)

E7, 2026-11-16, contra `docs/fusion_docs/` («Pattern reference», «Create a rectangular/circular pattern», «Create a rectangular/circular sketch pattern»). Pruebas con eventos simulados (nunca el cursor real) en la VPS (xvfb). Evidencia en `evidencias/patrones_2026-11-16/` (no está en git): `patrones_boceto.log`, `patrones_solidos.log`, `tortura_api.log`, `b599.py`, `ventana_chica.py`, capturas en `evidencias/ui_2026-11-16/capturas/`.

Leyenda: ✓ igual que Fusion y probado · ⚠ anda pero con una diferencia o sin probar con el mouse real · ✗ falta o falla · n/a no existe en Fusion.

## Dónde existe el patrón en Fusion y en OmniCAD

| Entorno | Fusion (ayuda local) | OmniCAD | Resultado |
|---|---|---|---|
| Boceto (rectangular y circular) | Sí | Sí: cinta BOCETO › Crear, panel con asas | ✓ |
| Sólido › Crear › Patrón | Sí (rectangular, circular, en ruta) | Sí: `cinta.py:105` | ✓ |
| Superficie | La ayuda lista `Surface > Create > Mirror`; el Patrón no aparece | Sin Patrón ni Simetría en la pestaña (`cinta.py:139`); se hace desde Sólido con cuerpos de superficie | ⚠ B-602 |
| Ensamblar | No tiene Patrón; el de componentes sale de Sólido (Tipo de objeto = Componentes) | Igual | ✓ |
| Chapa | La ayuda no lista Patrón en Sheet Metal › Create | Sin Patrón | ✓ n/a |
| Plástico | `Plastic > Create > Geometric Pattern` | El grupo CREAR lleva los patrones y el Patrón geométrico (`cinta.py:168`) | ✓ |

## Boceto

| Opción de Fusion | Rectangular | Circular | Herramienta MCP/CLI |
|---|---|---|---|
| Geometría a repetir (curvas, puntos) | ✓ | ✓ | `sketch_*_pattern(entities)` |
| Dirección 1 y 2 con líneas del boceto / Centro (punto, origen, X/Y) | ✓ | ✓ (centro = punto del boceto, extremo o centro de un círculo, probado) | `direction1_line/2`, `angle`, `angle2` / `center_x/y`, `center_point` |
| Tipo de distancia Extensión / Espaciado | ✓ | n/a | `spacing` |
| Espaciado angular Completa / Ángulo / Simétrica | n/a | ✓ (los tres, y el sentido ⇄) | `total_angle`, `symmetric` |
| Cantidad (campo y asa) | ✓ | ✓ | `count1/2`, `count` |
| Distancia / Ángulo total (campo y asa) | ✓ | ✓ | `distance1/2`, `total_angle` |
| Dirección Una / Simétrica | ✓ (por dirección: `symmetric2`) | ✓ | `symmetric`, `symmetric2` |
| Supresión de copias (casilla sobre cada copia) | ✓ | ✓ | `suppress`; ⚠ B-601 acepta un índice inexistente |
| Misma previa y mismas asas | ✓ | ⚠ B-599: no se reproduce en la VPS | — |
| Editar con doble clic en el glifo | ✓ | ✓ | `edit_sketch_pattern` |
| Cantidad 0, 1, negativa | ✓ rechaza con su mensaje | ✓ | — |
| Distancia 0, ángulo 0, ángulo > 360 | ✓ rechaza | ✓ rechaza | — |
| 1000 copias | ✓ (previa 0,04 s, repintado 0,4 s, API 0,3 s) | ✓ (API 2,5 s) | tope propio 1000 copias |
| Ctrl+Z / Ctrl+Y tras Aceptar | ✓ un solo paso | ✓ un solo paso | `undo` |
| Ventana 1024×700 | ✓ el panel entra y Aceptar se ve | ⚠ el panel cae en el centro y tapa el dibujo (se puede mover) | — |

Medido: `patrones_boceto.py` da 98 de 106 en verde; los 8 ✗ son textos esperados viejos de la propia prueba, no del programa (B-603).

## Sólido

| Opción de Fusion | Rectangular | Circular | Herramienta MCP/CLI |
|---|---|---|---|
| Tipo de objeto: Cuerpos | ✓ | ✓ | `bodies` |
| Tipo de objeto: Caras | ✓ (copias como cuerpos de superficie) | ✓ | `faces` |
| Tipo de objeto: Operaciones (features) | ✓ (clic en el timeline) | ✓ | `features` |
| Tipo de objeto: Componentes | ✓ clic en el navegador o en la vista (B-600, cerrado) | ✓ idem | `components` |
| Tipo de objeto: Geometría de construcción | ✓ | ✓ | `construction` |
| Eje / Ejes (origen, eje de construcción, arista, cara, plano) | ✓ | ✓ (también cara cilíndrica) | `axis1`, `axis2`, `plane2` / `axis` |
| Distribución Extensión / Espaciado | ✓ | ✓ (más Completa, Parcial, Simétrica) | `distribution` |
| Cantidad | ✓ | ✓ | `x_count`, `y_count` / `count` |
| Dirección Una / Simétrica | ✓ (`symmetric`, `symmetric2`) | ✓ | `symmetric` |
| Dirección 2 opcional / plano de referencia | ✓ | n/a | `axis2`, `plane2` |
| Supresión (casillas en la vista y campo de texto) | ✓ | ✓ | `suppress` (valida el rango) |
| Tipo de cálculo Optimizado / Idéntico / Ajustar (solo con Operaciones) | ✓ | ✓ | `compute` (las 6 combinaciones corren; resultado numérico en `tests/test_patrones_solidos_semantica.py`) |
| Extras de OmniCAD: unir al original, copias ligeras | ✓ | ✓ | `combine`, `lightweight` |
| Misma previa y asas | ✓ (33 de 33 en `patrones_solidos.py`) | ✓ | — |
| Valores raros | ✓ 0, 1 y negativas rechazadas; 10.001 rechazado; distancia 0 y ángulo 0 se rechazan al ejecutar, el paso se deshace; negativa invierte el sentido; `nan`, texto y 2,5 rechazados | ✓ | — |
| 1000 copias | ✓ 0,4 s | ✓ 0,4 s | tope 10.000 |
| Ctrl+Z | ✓ vuelve al estado anterior | ✓ | `undo` |
| Ventana 1024×700 | ✓ el panel entra y tiene scroll | ✓ | — |

## Superficie, Ensamblar, Chapa, Plástico

- **Superficie:** sin botón propio (B-602). Por Sólido › Patrón con cuerpos de superficie y con Caras anda.
- **Ensamblar:** por Sólido › Patrón con Componentes; por API anda (`components=[...]`); en la ventana, con clic en el navegador o en la vista (B-600, cerrado).
- **Chapa:** nada que comparar; sin diferencia con la ayuda de Fusion. Nada va a `despues.md`.
- **Plástico:** hereda los patrones del Sólido. Sin hallazgos.

## Hallazgos (filas en `docs/seguimiento/bugs.md`)

| ID | Qué | Dueño |
|---|---|---|
| B-599 | No se reproduce en la VPS con 3 variantes de centro; falta el archivo o la captura de Gerardo | E1 / E11 |
| B-600 | Patrón › Componentes se elige escribiendo nombres | E2 (cerrado el 2026-11-16) |
| B-601 | `suppress` fuera de rango se acepta en silencio en el patrón de boceto | E1 |
| B-602 | Superficie sin Patrón ni Simetría | E4 |
| B-603 | `patrones_boceto.py` espera textos viejos (8 ✗) | E7 |

## Lo que necesita el mouse real (lista de E11)

1. B-599: con el `.omnicad` de Gerardo, Patrón circular con 4 objetos y centro «Punto 576»: ¿se ven las copias en Windows? Capturas con y sin tema oscuro.
2. Arrastrar las asas de Cantidad, Distancia y Ángulo total del boceto con el mouse físico y comparar con Fusion.
3. Casillas de supresión sobre la vista (sólido y boceto) con clic real, en ventana de 1024×700.
4. Panel en 1024×700: moverlo con el mouse y ver si deja ver las copias.
5. Superficie: si Fusion trae Patrón o Simetría en Superficie › Crear (B-602).

## No cubierto

- Patrón en ruta y Patrón en puntos (no son de este ítem).
- Resultado numérico de `compute` sobre piezas reales: lo cubre el test de semántica, no lo repetí.
