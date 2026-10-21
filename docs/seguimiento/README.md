# Seguimiento: bugs, faltantes y mejoras

Única fuente de verdad de lo que **falta resolver**. Si otro archivo dice otra cosa, vale lo de acá y el otro se
corrige. Lo que se resuelve **se borra** de la lista: la historia queda en el Registro de `PROJECT_LOG.md` y en git.

| Archivo | Qué tiene |
|---|---|
| [bugs.md](bugs.md) | Algo que falla, da un resultado malo o un mensaje engañoso |
| [faltantes.md](faltantes.md) | Una función que todavía no existe |
| [mejoras.md](mejoras.md) | Algo que existe y se puede hacer mejor: rendimiento, interfaz, mensajes, instalador |

La especificación de cada faltante (qué hace en el programa de referencia y cómo tiene que sentirse) está en
los `docs/brechas_*.md`. Esos archivos describen; **el estado vive solo acá**.

## Columnas

`| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |`

- **ID**: el de origen (B-71, T-04, H-12, P-26, RH3, MCP-26…). Nunca se reutiliza ni se renumera.
- **Estado**: `Abierto` · `Parcial` (resuelto en parte: «Queda» dice qué falta) · `Bloqueado` (espera algo del
  usuario) · `Sin verificar` (nadie lo comprobó contra el código; es preferible a adivinar). No hay estados de
  cerrado: lo resuelto se borra.
- **Dificultad** de lo que queda:
  - `Baja`: horas, un archivo.
  - `Media`: medio día, varios archivos o interfaz.
  - `Alta`: días, arquitectura o geometría difícil.
  - `Muy alta`: semanas, el kernel, investigación o una dependencia nueva.
- **Evidencia**: dónde está hoy en el código (un test `tests/archivo.py::nombre`, un `archivo:línea` o un commit).
  `tests/test_seguimiento.py` falla si nombra un test que no existe.
- **Verificado**: fecha (AAAA-MM-DD) de la última vez que alguien lo comprobó contra el código.

## Cómo se trabaja

1. **Antes de informar un estado**, se mira el código y los tests. El log y la memoria pueden estar viejos.
2. **Bug nuevo**: una fila en `bugs.md` con el siguiente número B-n libre, cómo reproducirlo y dónde está.
3. **Al resolver algo**: en el mismo commit que el arreglo se **borra su fila** (y su ficha de «Detalle», si
   tiene) y se anota en el Registro de `PROJECT_LOG.md` el ID, qué se hizo y la prueba que lo cubre.
   Si se resolvió solo en parte: queda `Parcial`, con «Queda» y la fecha al día.
4. **Lo que no se va a hacer** (no era un bug, no se reproduce, se descarta): también se borra, con una línea en
   el Registro que diga por qué. Si un bug vuelve a aparecer, se carga de nuevo con un B-n nuevo.
5. **Detalle largo** (pasos para reproducir, mediciones): en la sección «Detalle» del mismo archivo.

## Decisiones que esperan al usuario (estado `Bloqueado`)

No se empiezan sin su OK, porque instalan algo, gastan plata o cambian el alcance.

| Tipo | Qué hay que decidir | IDs |
|---|---|---|
| Paquete nuevo | `rhino3dm` · `mutmut` · `hidapi` · motor de física · CalculiX + Gmsh · OpenSCAD · cabeceras de OCCT 8.0 + `pybind11` · `ffmpeg` · lector `.exr` | RH3 · SC16 · PL12 · B17 · F19 · F22 · CPP-F2 · B6 · KS2 |
| Gasto | Cuenta Apple Developer (USD 99 al año) · certificado de firma para el `.exe` | P-26d · AUD-8 |
| Máquina o hardware | PC con Linux nativo · PC limpia para el instalador · SpaceMouse | P-1b · P-1c · P-8b · PL12 |
| Alcance | CAM · SubD y espacio FORMA · quad remesh · edición de malla · fragmentos booleanos · piezas de McMaster/TraceParts · «AI Shots» · menú del boceto distinto de Fusion | F20 · RH19 · P-25j · RH20 · B16 · F21 · P-25g2 · KS15 · MCP-HAL3 |

## Tareas que aparecen en varias listas

Son UNA sola tarea: al hacerla se borran todas sus filas juntas (y su ID de estas dos tablas).

| Tarea | IDs |
|---|---|
| Informe de geometría e impresión 3D | F2 · B2 · RH13 |
| Imanes y manipulador contextual | RH12 · B7 |
| Instancias o copias ligeras | RH17 · PL8 |
| Puntos de control y B-spline | F12 · RH9 |
| Deformar y ajustar a superficie | RH7 · B10 · P-27-8 |
| Relieve desde imagen o textura | RH10 · B13 · P-27-9 |
| Patrón en puntos y esparcir | F3 · B12 · VR9 |
| Rebanar y curvas de corte | F6 · RH18 |
| Mapeo UV | RH21 · B18 |
| Pases de render | KS11 · VR3 |
| Complementos de usuario | B5 · GH12 · PAQ-H5 |
| Cotas y símbolos de dibujo | F9 · RH14 |
| Video MP4 y cámara en ruta | B6 · P-27-15 |
| Puente con Blender | P-3a · PL10 · B1 |

## Otras listas que se siguen aparte

- **FK-n**: faltantes del kernel OmniKernel. Viven en su propio repo
  (`$OMNIKERNEL_DIR/docs/faltantes_omnicad.md`); acá solo se anota el impacto en OmniCAD.
- **IM-n**: inventario generado de imports del motor (`docs/inventario_motor.md`, `scripts/inventario_motor.py`). No
  son tareas.
