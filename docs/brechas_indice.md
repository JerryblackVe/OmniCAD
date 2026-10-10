# Índice de brechas — por dónde seguir

Fecha: 2026-10-09. Punto de partida para la próxima sesión: acá están TODAS las listas de funciones a
incorporar, en qué orden y qué hay que decidir antes. El detalle de cada ítem está en su archivo.

## Las listas

| Programa | Archivo | IDs | Pendiente (`PROJECT_LOG.md`) | Licencia |
|---|---|---|---|---|
| Fusion 360 | `brechas_fusion.md` | — | varios | propietario: solo funciones |
| FreeCAD | `brechas_freecad.md` | F1–F23 | 13 | LGPL-2.1: se puede reescribir citando |
| Plasticity | `brechas_plasticity.md` | PL1–PL13 | 14 | propietario |
| Blender | `brechas_blender.md` | B1–B19 | 15 | GPL: se puede tomar código citando |
| Rhino 8 | `brechas_rhino.md` | RH1–RH22 | 16 | propietario (`.3dm` con `rhino3dm`, MIT) |
| Grasshopper | `brechas_grasshopper.md` | GH1–GH12 | 17 | propietario |
| KeyShot | `brechas_keyshot.md` | KS1–KS15 | 18 | propietario |
| V-Ray | `brechas_vray.md` | VR1–VR13 | 19 | propietario |

Toda herramienta lleva la «receta de experiencia Fusion» (ver `brechas_freecad.md`): botón en la cinta y en la
tecla S, panel con vista previa viva, manipuladores, un paso editable del timeline, equivalente en API/MCP/CLI y
prueba con resultado numérico. Recetas de código: A, B y C de `AGENTS.md`.

## Decisiones del usuario que faltan (preguntar ANTES de programar eso)

1. ~~Motor de render~~ DECIDIDO (2026-10-09): los tres, en orden — escena común + OpenGL mejorado → Cycles de
   Blender (B1) → trazador propio. El usuario elige en el combo «Motor».
2. **Dependencias nuevas**: `rhino3dm` (RH3), ffmpeg (B6), vectorizador tipo potrace (B4), lector `.exr` (KS2),
   motor de física (B17), CalculiX + Gmsh (F19). No instalar sin permiso.
3. **IA** (KS15): solo con pedido explícito (regla de no gastar en APIs).

## Tareas que son UNA sola aunque aparezcan en varias listas

| Tarea | IDs |
|---|---|
| Informe de geometría / impresión 3D | F2 + B2 + RH13 |
| Imanes y manipulador contextual | RH12 + B7 |
| Instancias / copias ligeras | F17 + RH17 + PL8 |
| Puntos de control y B-spline | F12 + RH9 |
| Deformar / ajustar a superficie | RH7 + B10 |
| Relieve desde imagen o textura | RH10 + B13 |
| Patrón en puntos / esparcir | F3 + B12 + VR9 |
| Rebanar / curvas de corte | F6 + RH18 |
| Mapeo UV | RH21 + B18 |
| Pases de render | KS11 + VR3 |
| Complementos de usuario | B5 + GH12 |
| Cotas y símbolos de dibujo | F9 + RH14 |

## Orden sugerido (lo que no pide decisiones)

1. F2+B2+RH13 informe de geometría (útil ya, para STEP y mallas importadas).
2. F1 engranajes · F3 patrón en puntos · RH6 seleccionar por criterio · PL1 comandos según lo elegido.
3. RH1 mezcla de superficies · RH2 igualar · RH4 desenrollar · RH5 editar agujeros sin historial.
4. VR10 render en la API/MCP · VR1 mezcla de luces · VR2 postproceso · KS10 variantes en lote.
5. GH1 → GH2 → GH3 → GH5 → GH8 (grafo sin ventana, ya útil para agentes).
6. Prioridad 3 (Simulación, Fabricación, SubD): después de decidir dependencias.

## Cómo arrancar la próxima sesión

Leer `PROJECT_LOG.md` (pendientes 13–19 y Registro del 2026-10-09) y este índice; elegir un ítem; abrir su
archivo de brechas; aplicar la receta A/B/C de `AGENTS.md`; cerrar con ruff, pytest, humo y entrada en el Registro.
Cada archivo tiene una sección «Sin verificar»: confirmar esos puntos en la app antes de programar.
