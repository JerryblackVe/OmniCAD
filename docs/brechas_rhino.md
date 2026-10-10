# Brechas frente a Rhino 8

Fecha: 2026-10-09.
Fuentes (leídas ese día): [lista oficial de comandos de Rhino](https://wiki.mcneel.com/rhino/commandlist) (McNeel Wiki,
revisión del 2025-03-31: ~1000 nombres), [novedades de Rhino 8](https://www.rhino3d.com/8/new/),
[soporte de Rhino](https://www.rhino3d.com/support/). Grasshopper va en su propio archivo: `docs/brechas_grasshopper.md`.

**Regla:** Rhino es propietario. Se replican las FUNCIONES y opciones, nunca código, textos ni recursos.
Excepción a verificar: leer y escribir `.3dm` con `rhino3dm`/openNURBS de McNeel (licencia MIT).

**Qué es verificado y qué no:** los NOMBRES de comando salen de la lista oficial. La ayuda con descripciones
(`docs.mcneel.com`) devolvió 403, así que lo que hace cada comando está escrito de mi conocimiento de Rhino. Donde
una opción es dudosa lo marco ⚠.

Misma idea que en `brechas_freecad.md`, `brechas_blender.md` y `brechas_plasticity.md`: sacar funciones de acá, con
el manejo de Fusion 360 (botón en la cinta, panel con vista previa viva, manipuladores, un paso editable en el
timeline, API/MCP/CLI y prueba con resultado numérico).

## Ya está en OmniCAD (no repetir)

Boceto completo; extrusión, revolución, barrido, solevación, parche, reglada, desfase, recorte, destrimar, extender,
coser, engrosar y empalme de superficies; empalme, chaflán, vaciado, desmoldeo; booleanas; matriz rectangular,
circular y en ruta; simetría; escala; alinear; mover/copiar; dividir cara/cuerpo; silueta; mallas (reducir, remallar,
reparar, suavizar, booleanas, corte con plano); análisis cebra, peine de curvatura, mapa de curvatura, mapa de entorno (≈ `EMap`), isocurva, desmoldeo,
accesibilidad, radio mínimo, sección y centro de masa (`ui/cinta.py`); dibujo con vista base, proyectada, sección y detalle, cotas, ordenada, notas y globos; historial completo
(el timeline: es más fuerte que el `History` de Rhino, que vale solo para algunos comandos).

## Para hacer

### Prioridad 1

| # | Herramienta (comandos de Rhino) | Cómo debe sentirse (Fusion) | Estado / dónde engancha |
|---|---|---|---|
| RH1 | **Mezcla de superficies** con continuidad de posición, tangencia, curvatura y G3; radio o tensión variable por extremo. `BlendSrf`, `VariableBlendSrf`, `BlendEdge`. | SUPERFICIE › «Mezclar»: clic en un borde y en otro; menú de continuidad por lado; deslizadores y flechas en los extremos; vista previa viva. | No existe (hay `parche`, `reglada`, `sup_empalme`). En `nucleo/superficies.py`. |
| RH2 | **Igualar superficie o curva**: mover el borde elegido hasta coincidir en posición, tangencia o curvatura con otro. `MatchSrf`, `Match`, `MatchMeshEdge`. | SUPERFICIE › «Igualar»: borde a mover + borde destino + continuidad + «mantener estructura». | Hay `reemplazar_cara` (sin continuidad). |
| RH3 | **Abrir y guardar `.3dm`** con capas, colores y bloques. Biblioteca `rhino3dm`. | Archivo › Abrir/Exportar `.3dm`, igual que STEP y `.f3d`. | `io_archivos/abrir_externo.py`. ⚠ Paquete nuevo: pedir permiso antes de instalar. |
| RH4 | **Desenrollar y solevación desarrollable**: aplanar una superficie desarrollable o casi, con mapa de estiramiento; solevar entre curvas dejando la forma desarrollable. `UnrollSrf`, `Squish`/`SquishBack`/`SquishInfo`, `FlattenSrf`, `DevLoft`. | CREAR › «Desenrollar»: caras elegidas; sale un cuerpo plano + mapa de color de la distorsión; exporta a DXF. Para cuero, tela, vinilo, cartón. | `patron_plano` solo existe para chapa. |
| RH5 | **Editar agujeros y caras de un cuerpo SIN historial** (importado de STEP, `.f3d` o malla): mover, copiar, hacer matriz, espejar, rotar y cambiar diámetro/profundidad de un agujero que ya existe; mover una cara o una arista; insertar una cara hacia adentro. `MoveHole`, `CopyHole`, `ArrayHole`, `ArrayHolePolar`, `MirrorHole`, `RotateHole`, `RoundHole`, `RevolvedHole`, `PlaceHole`, `MakeHole`, `MoveFace`, `MoveEdge`, `Inset`. | MODIFICAR › «Editar agujero»: clic en el agujero → panel con Ø, profundidad y posición, flecha para moverlo; el cuerpo sigue siendo uno solo. | Hay `desfase_cara` y `borrar_caras`; no hay edición de un agujero existente. Importante porque `.f3d`/STEP entran sin historial (pendiente 11). |
| RH6 | **Seleccionar por criterio**: duplicados, objetos chicos, curvas cortas, malos, no manifold, cerrados/abiertos, planos, con historial, por color o material. ~130 comandos `Sel*`: `SelDup`, `SelSmall`, `SelShortCrv`, `SelBadObjects`, `SelNonManifold`, `SelClosedSrf`, `SelOpenPolysrf`, `SelPlanarSrf`, `SelObjectsWithHistory`, `SelColor`, `SelMaterialName`. | Menú «Seleccionar por…» en el navegador y en la caja de la tecla S; el resultado queda elegido y se cuenta abajo a la derecha. | Hay selección por clic, ventana y filtros. Nuevo, en `ui/ventana.py`. |

### Prioridad 2

| # | Herramienta (comandos de Rhino) | Cómo debe sentirse (Fusion) | Estado / dónde engancha |
|---|---|---|---|
| RH7 | **Deformar**: fluir un objeto a lo largo de una superficie o curva, doblar, torcer, cónico, cortar-estirar, vórtice, deformar con jaula y editar con caída suave. `Flow`, `FlowAlongSrf`, `Bend`, `Twist`, `Taper`, `Shear`, `Stretch`, `Maelstrom`, `Splop`, `Cage`/`CageEdit`, `SoftMove`, `SoftEditSrf`, `Smash`. | MODIFICAR › «Deformar»: tipo + objetos + superficie base o eje; vista previa viva; manipulador de ángulo o factor. | Nuevo. Pide malla de caras densa. |
| RH8 | **Más superficies**: red de curvas, bordes, entre curvas, extrusión cónica o a un punto, cortina sobre puntos, superficie por puntos. `NetworkSrf`, `EdgeSrf`, `TweenCurves`, `TweenSurfaces`, `ExtrudeCrvTapered`, `ExtrudeCrvToPoint`, `ExtrudeSrfAlongCrv`, `Drape`, `SrfPt`, `FitSrf`, `RailRevolve`. | SUPERFICIE › cada una con su panel; «Red de curvas» con curvas en U y en V y continuidad en los bordes. | Hay solevación, barrido, revolución, parche. |
| RH9 | **Editar por puntos de control**: mostrar y mover CVs de curvas y caras, insertar/quitar nudo o punto, cambiar grado, reconstruir con N puntos, hacer periódica, simplificar, alisar. `PointsOn`, `EditPtOn`, `InsertKnot`, `RemoveKnot`, `InsertControlPoint`, `ChangeDegree`, `Rebuild`, `RebuildUV`, `Fair`, `Smooth`, `SimplifyCrv`, `MakePeriodic`, `ConvertToBeziers`. | Modo «Puntos de control» sobre la selección; arrastrar con caída suave; «Reconstruir» con grado y cantidad. | Nuevo. Junto con F12 de `brechas_freecad.md`. |
| RH10 | **Relieve desde imagen** (mapa de altura → superficie). `Heightfield`. | CREAR › «Relieve desde imagen»: imagen, tamaño, altura máxima, resolución. | Hay `repujado` con perfiles y texto, sin imagen. |
| RH11 | **ShrinkWrap**: malla estanca alrededor de mallas, NURBS, SubD o nubes de puntos. `ShrinkWrap`. | MALLA › «Envolver»: objetos + tamaño de celda + cerrar huecos. Útil para imprimir modelos sucios. | Hay `reparar_malla`, `solido_envolvente`. ⚠ Puede pedir una dependencia: preguntar. |
| RH12 | **Gumball e imanes**: manipulador que aparece al elegir (flechas para mover/extruir/escalar, con alineación y reinicio); imanes a punto, medio, centro, cuadrante, tangente, perpendicular, intersección, con seguimiento inteligente. `Gumball`, `GumballAlignment`, `PushPull`, `Osnap`, `SmartTrack`, `SnapToMeshes`, `SnapToLocked`, `ProjectOsnap`. | Clic en una cara → flecha → arrastrar = Pulsar/tirar con vista previa. Barra de imanes en el visor. Es la misma tarea que B7 de `brechas_blender.md`: hacerla UNA vez. | Hay manipuladores dentro de cada comando y Pulsar/tirar. Buscado en el código: el visor 3D (`ui/visor3d.py`, `ui/manipuladores.py`) no tiene imanes; solo aparecen en Ensamblar y Dibujo. |
| RH13 | **Análisis ampliado**: espesor, continuidad por borde (G0/G1/G2), aristas abiertas y no manifold, desviación entre curvas o puntos, normales visibles. `ThicknessAnalysis`, `EdgeContinuity`/`GCon`, `ShowEdges`, `CrvDeviation`, `PointDeviation`, `Dir`/`ShowDir`. | ANALIZAR › cada una con mapa de color en la vista y lista de resultados. Las aristas abiertas y el espesor son el mismo informe que F2 de `brechas_freecad.md` y B2 de `brechas_blender.md`; la desviación va con F10 de FreeCAD. | Hay cebra, peine y mapa de curvatura, mapa de entorno, isocurva, desmoldeo, accesibilidad, radio mínimo y sección. |
| RH14 | **Dibujo**: cotas de longitud de curva, de área y de volumen; estilos de anotación importables; plantillas de hoja con varios detalles a distintas escalas; curvas de corte para fabricación. `DimCurveLength`, `DimArea`, `DimVolume`, `DimCreaseAngle`, `ImportAnnotationStyles`, `Layout`, `Detail`, `ClippingDrawings`, `ExtractClippingSections`. | Mismo flujo de dibujo actual; panel de estilo con vista previa. | `nucleo/dibujo.py` (ver también F9 de `brechas_freecad.md`). |
| RH15 | **Colocar y repartir sobre superficies**: orientar un objeto sobre una superficie o curva en un punto, matriz sobre superficie o sobre curva en una cara, distribuir con separación pareja. `OrientOnSrf`, `OrientOnCrv`, `Orient3Pt`, `ArraySrf`, `ArrayCrvOnSrf`, `Distribute`. | MODIFICAR › «Colocar sobre superficie»: objeto + superficie + punto (o U/V) + alinear a la normal. | Hay `alinear`, `mover`, `patron` en ruta. |
| RH16 | **Modos de pantalla por objeto y poses guardadas**: Pluma, Técnico, Arctic, Monocromo, Fantasma, aplicables a un objeto; posiciones y selecciones con nombre. `SetDisplayMode`, `SetObjectDisplayMode`, `NamedPosition`, `NamedSelections`, `NamedView`, `NamedCPlane`, `SaveWindowLayout`. | Estilo visual con vista previa; «Guardar posición» como en Animación; guardar la disposición de ventana. | Va con el pendiente 4 (render). El corte en el render es VR5 de `brechas_vray.md`. |
| RH17 | **Bloques vinculados**: una definición compartida por muchas copias, vinculada a un archivo que se recarga. `Block`, `BlockManager`, `ReplaceBlock`, `CreateUniqueBlock`, `ExportLinkedBlocks`. | «Insertar diseño» (ya existe) con «Actualizar si cambió el archivo» y «Hacer única». Es F17 de `brechas_freecad.md`: una sola tarea. | Ver `insertar_diseno` y F17. |
| RH18 | **Curvas desde superficies y cuerpos**: isocurvas, bordes, contorno por cortes paralelos, silueta, proyectar, tirar. `ExtractIsocurve`, `DupBorder`, `DupEdge`, `Contour`, `Silhouette`, `Project`, `Pull`, `Section`. | INSERTAR › «Curvas desde cara»; salen como boceto. `Contour` es lo mismo que F6 (Rebanar) de FreeCAD. | Hay proyectar/intersecar en boceto. El análisis de isocurva ya existe; lo nuevo es SACAR la curva. |

### Prioridad 3 — grandes, piden decisión

| # | Herramienta | Nota |
|---|---|---|
| RH19 | **Modelado por subdivisión (SubD)**: cajas, esferas, solevación, barrido, extrusión, desfase, pliegues, simetría viva, convertir a NURBS. `SubDBox`, `SubDLoft`, `SubDSweep1`, `ExtrudeSubD`, `SubDCrease`, `OffsetSubD`, `ToNURBS`, `ToSubD`, `MultiPipe`, `Symmetry`. | Pasó de «fuera de alcance» a prioridad 3 el 2026-10-09 (`brechas_fusion.md`). Va junto con PolySplines (`brechas_plasticity.md`) y la «Forma» de Fusion. Proyecto aparte. |
| RH20 | **Quad remesh y cuadrangulación.** `QuadRemesh`, `QuadrangulateMesh`. | Base de RH19 en sentido inverso. Algoritmo pesado. |
| RH21 | **Mapeo UV y texturas**: proyección caja/cilindro/esfera/superficie, editor de UV. `ApplyBoxMapping`, `ApplySphericalMapping`, `UVEditor`, `Unwrap`. | Va con el pendiente 4 (render). Es la misma tarea que B18 de `brechas_blender.md`. |
| RH22 | **Nube de puntos**: reducir, contornos y secciones. `PointCloud`, `PointCloudContour`, `ReducePointCloud`. | Va con F22 de `brechas_freecad.md`. |

## Lo que hace Rhino 8 de nuevo y a quién le toca

| Novedad (Rhino 8) | Dónde queda |
|---|---|
| ShrinkWrap, PushPull, Gumball, Inset, Auto CPlanes | RH11, RH12, RH5 y la idea de plano de trabajo con una tecla (`brechas_plasticity.md`) |
| Mallas: booleanas reescritas | Ya está |
| Estilos de sección, recorte selectivo, dibujos vectoriales dinámicos, secciones para fabricación | RH14 y RH18 |
| SubD con pliegues | RH19 |
| Editor de scripts con Python 3 y C# | Ver `brechas_grasshopper.md` (GH6) |
| Dark mode, Window Layouts, administrador de capas | Temas ya existen; RH16 |
| Cycles con GPU, texturas procedurales, UV | Pendiente 4 y RH21 |
| `.glb`, USD, E57, bloques dinámicos | B3 de `brechas_blender.md` y RH3 |

## Descartado a propósito

Digitalizadores (`Dig*`), `Hydrostatics` y `Catenary` (nicho naval y arquitectura), licencias y nube Zoo, plugins
de Mac, `Worksession`, líneas de comando con macros (la CLI de OmniCAD ya cubre eso).

## Sin verificar

- Las descripciones de cada comando (arriba): de mi conocimiento, no de la ayuda de McNeel.
- RH6: los nombres `Sel*` son los de la lista; las opciones de cada uno no se leyeron.
- Qué hace hoy OmniCAD en RH12, RH13 y RH16: buscado en el código, no probado en la app.
