# Brechas frente a Plasticity

Fecha: 2026-10-09.
Fuentes (leídas ese día): [manual de Plasticity](https://doc.plasticity.xyz/) — comandos de sólidos y hojas, de bocetos y
primitivas, comunes, esenciales de la interfaz y notas de la versión 2026.1.

**Regla:** Plasticity es propietario. Se replican las FUNCIONES y opciones, nunca código, textos ni recursos.

Plasticity es un modelador de NURBS «directo» (sin historial), con pocos comandos que cambian según lo elegido y
mucha atención al detalle de uso. Por eso esta lista tiene MÁS ideas de uso que funciones nuevas: lo geométrico
que comparte con Rhino está en `docs/brechas_rhino.md` y acá solo se apunta.

## Ideas de uso que vale copiar

| # | Idea | Cómo se vería en OmniCAD |
|---|---|---|
| PL1 | **Un comando, según lo elegido.** «Fillet», «Offset», «Join», «Extend», «Reverse», «Unjoin», «Rebuild», «Align» y «Imprint» son un solo botón que actúa distinto sobre curvas, vértices, aristas, caras o cuerpos. | Menos botones en la cinta: un «Desfase» que, con curvas elegidas, desfasa curvas; con aristas, aristas; con una cara, la cara. El panel cambia solo y la ayuda dice qué hace en cada caso. |
| PL2 | **Teclas de opción a la vista.** Cada comando muestra qué hace Mayús/Ctrl/Alt mientras está activo, y Shift+R repite el último. | Pie del panel de comando: «Mayús: simétrico · Ctrl: copiar». «Repetir» YA existe en el menú radial (`ui/ventana.py`, `_ultimo_comando`): falta solo el atajo de teclado. |
| PL3 | **Plano de trabajo con una tecla.** Con una cara elegida, Espacio la vuelve el plano de construcción; Mayús+Espacio, desde la cámara. 2026.1 suma imán 2D sobre ese plano. | Ya hay planos y «Boceto sobre cara»; falta el atajo directo y que primitivas y Mover arranquen en ese plano. |
| PL4 | **Orden de empalme.** Su tutorial «Fillet Order of Operations» enseña a empalmar de lo grande a lo chico. ⚠ Si el comando de Plasticity avisa solo al fallar: no leído. | Si `empalme` falla, el aviso dice «probá primero el radio mayor» y ofrece reordenar por radio. |
| PL5 | **Sugerencias según la selección** («Suggested Commands» junto a la barra). | Al elegir una cara, una tira corta con los 4–5 comandos que aplican (como el menú radial, pero siempre visible). |

## Funciones propias (o con un giro propio)

| # | Herramienta (en Plasticity) | Cómo debe sentirse (Fusion) | Estado / dónde engancha |
|---|---|---|---|
| PL6 | **Quitar empalmes de un cuerpo** y **borrar topología redundante** (aristas y vértices que sobran). `Remove Fillets from Shell`, `Delete Redundant Topology`. | MODIFICAR › «Quitar empalmes»: elegís el cuerpo; se resaltan las caras de empalme detectadas; filtro por radio máximo. | Hay `borrar_caras` (una por una). La detección de caras de empalme es lo nuevo. |
| PL7 | **Desfasar aristas o un lazo de caras**: crea aristas nuevas a una distancia, sin cortar el cuerpo; opción simétrica. `Offset Edge`, `Offset Face Loop`. | Parte de PL1: «Desfase» con aristas o caras elegidas. | Hay `dividir_cara`. |
| PL8 | **Instancias**: copias que comparten la geometría, de sólidos y de curvas; «Realizar instancias» las vuelve reales. `Create Instance`, `Realize Instances`. | Es F17 de `brechas_freecad.md` y RH17 de `brechas_rhino.md`: una sola tarea. | Ver esas dos. |
| PL9 | **Exportar líneas ocultas a SVG** (vista con las aristas tapadas en línea punteada). `Export Hidden Line`, `Export SVG`. | Archivo › Exportar › SVG desde una vista del dibujo. | Hay vistas de dibujo; falta la salida a SVG. |
| PL10 | **Puente en vivo con Blender**: un add-on que transmite mallas por un puerto local y las refresca. `Blender Bridge`. | Botón «Enviar a Blender» y refresco al cambiar un parámetro. Modelo de diseño para el pendiente 3 (ver también B1 de `brechas_blender.md`). | Hay `ui/puente.py` (127.0.0.1 + token). |

## Lo que comparte con Rhino (ya listado ahí)

| Plasticity | Dónde queda |
|---|---|
| `Bridge Surface`, `Bridge Edge` (G0–G3 con tensión) | RH1 |
| `Match Face`, `Align Surface` | RH2 |
| `Unwrap Face` | RH4 |
| `Deform` (envolver sobre superficie) | RH7 |
| `XNurbs`, `Square`, `Constrained Surface` | RH8 |
| `Insert Knot`, `Raise Degree`, `Slide CV`, `Rebuild` | RH9 |
| `Isoparam`, `Create Outline`, `Project Outline` | RH18 |
| `PolySplines` (malla a NURBS) | RH19 |
| Gizmo de mover con edición proporcional | RH12 |
| `Measure Continuity`, curvatura | RH13 |

## Detalles chicos

| # | Detalle (2026.1 y manual) | Nota |
|---|---|---|
| PL11 | **Buscador en el Outliner** y agrupar objetos. | El navegador ya agrupa; falta buscar por nombre. |
| PL12 | **Soporte de SpaceMouse** (3Dconnexion) con refinamientos en 2026.1. | Buscado en el código: no hay nada de SpaceMouse/3Dconnexion. Fusion sí lo soporta. |
| PL13 | **Modo Render** dentro del visor con HDRI integrados. | Va con el pendiente 4 (render). |

## Descartado a propósito

Plasticity Share (publicar en su nube), tipos de licencia, `Fork Material` (OmniCAD ya tiene materiales).

## Sin verificar

- Qué hace hoy OmniCAD en PL5, PL11 y PL12: buscado en el código, no probado en la app.
- Los nombres vienen del manual; las opciones de cada comando no se leyeron una por una.
