# Referencia: CREAR y MODIFICAR del boceto contra Fusion 360 y SOLIDWORKS (fase 2, 2026-11-07)

Fase 2 de [auditoria_boceto_crear_modificar.md](../auditoria_boceto_crear_modificar.md). Sigue al
[inventario](boceto_crear_modificar_inventario.md) (fase 1). Acá van solo las **diferencias reales**: una opción, un
modo, un valor por defecto o un comportamiento que la ayuda oficial dice explícitamente y OmniCAD no tiene o hace
distinto (comprobado en el código). Si la ayuda no lo dice, figura «sin dato». **Fusion manda**; SOLIDWORKS se usa
para casos que Fusion no documenta.

Fuentes:
- Fusion: `docs/fusion_docs/contenido/fusion-sketch/` (`scripts/fusion_docs.py buscar|ver`), árbol en
  `docs/fusion_docs/indice/fusion-sketch.md`.
- SOLIDWORKS: ayuda oficial 2025, prefijo `https://help.solidworks.com/2025/english/SolidWorks/sldworks/` (abajo, «SW:»).
  Varias páginas se leyeron incompletas; lo no leído es «sin dato».

## 1. Diferencias con Fusion

| Comando | Fusion (ayuda) | OmniCAD (código) | Diferencia | Fila |
|---|---|---|---|---|
| Spline de puntos de control | «Degree 5 is the default option» (`spline-degree-control-reference-e322c291e98.md`). Con menos de 6 polos el grado baja a polos − 1 (foro de Autodesk, hilo 12126030: «2 control points … degree 1 … up to 6 control points, which is degree 5») | Arrancaba en grado 3 (`ui/editor_boceto.py:647`, `draw_spline degree=3`) y la API rechazaba 4 polos con grado 5 | Cerrada en esta fase | P-67 |
| Proyectar a superficie (Create › Project/Include) | «Creates a 3D sketch by projecting selected sketch objects to selected BRep faces» (`reference-project-to-surface-dialog-c5a9911bdda.md`) | Solo MCP: `project_to_surface` (`api/herramientas_boceto3d.py:512`). Sin clave, botón ni comando en `ui/` | Falta en la ventana | H-109 |
| Curva de intersección (Create › Project/Include) | «Creates a 3D sketch by intersecting the selected sketch geometry with the selected faces…» (`reference-intersection-curve-dialog-037f94c55e6.md`) | Solo MCP: `intersect_curves` (`api/herramientas_boceto3d.py:479`) | Falta en la ventana | H-109 |
| Recortar | «click and hold the mouse button, then drag the cursor to touch each segment you want to trim» (`trim-or-extend-sketch-geometry-9b1b49a62dd.md`) | `ui/editor_boceto.py:5495` solo actualiza la vista previa al mover; recorta de a un clic | Falta el recorte por barrido | H-110 |
| Arco tangente | «Click to place the second point of the arc, or specify a radius value» (`create-arcs-in-a-sketch-6534f047cef.md`) | La ventana acepta radio tecleado (`editor_boceto.py:3779`, `3929`); `draw_arc tangent_to` exige `end_x/end_y` (`api/herramientas_boceto.py:1278`) | La API no puede pedir el arco tangente por radio | P-72 |
| Curva de fusión | «…blend curve between the endpoints of two existing sketch curves or edges» (`create-a-blend-curve-8690a28053c.md`) | `draw_blend_curve` (`api/herramientas_boceto.py:2209`) recibe solo curvas del boceto | Una arista del modelo hay que proyectarla antes | P-73 |
| Círculo de 3 tangentes | «use window selection to select multiple lines at once» (`create-circles-in-a-sketch-e87fd277002.md`) | Las tangentes se eligen de a un clic (`editor_boceto.py:189`, `2191-2201`) | Sin confirmar: falta probar un arrastre en la ventana (fase 6) | — |
| Línea, Mover/Copiar | Ya comparados en el inventario § 3 (arco tangente dentro de la Línea: ya estaba, H-108; mover fuera del plano: `transform_sketch_3d`) | — | Sin diferencia nueva | — |

Sin diferencia encontrada (opciones y datos que pide cada comando): Línea, Línea de punto medio, los 3 rectángulos,
círculo de centro, de 2 y 3 puntos y de 2 tangentes, arco de 3 puntos y de centro, los 3 polígonos, elipse, las 5
ranuras, spline de ajuste (abrir/cerrar, insertar punto, manijas, peine), cónica (`rho`), punto, texto (en trayectoria,
`{param}`, fuente, alineación, desglosar), simetría, los dos patrones (extensión/separación, simétrico, suprimir
instancias, editar), Proyectar, Intersecar, Incluir 3D, Perfil giratorio, Isoparamétrica, Romper vínculo, Proyecciones
perdidas, cota (tipos, conducida, desfase), empalme, los 3 chaflanes, desfase (uno, dos lados, simétrico, cadena,
elipse/óvalo) y soltar desfase, recortar (sin cruce borra la curva, como Fusion), alargar (sin cruce falla, como
Fusion), partir, escala, mover/copiar y parámetros.

Sin dato en la ayuda de Fusion: radio de empalme imposible, chaflán más largo que el tramo, `rho` por defecto de la
cónica, tope de lados del polígono, qué hace con las cotas al recortar. Para eso se usa SOLIDWORKS (§ 2) o el
comportamiento más seguro (error claro y boceto sin cambios), que prueba la fase 3.

## 2. SOLIDWORKS: lo que agrega a la referencia

Solo se carga fila cuando el comportamiento también es de Fusion o protege la geometría. Lo que es propio de
SOLIDWORKS queda anotado como dato, sin fila (prioridad Fusion).

| Herramienta SW | Dato oficial | OmniCAD | Uso |
|---|---|---|---|
| Sketch Fillet | «Keep constrained corners»: conserva el punto de intersección virtual si el vértice tiene cotas; desmarcado, **pregunta** antes de borrarlas (SW: `HIDD_DVE_SKETCH_FILLET.htm`) | Línea-línea re-apunta las cotas a un vértice virtual; en paralelas y en el caso general las borra e informa (`constraints_deleted`, P-68) | Equivalente. Sin fila |
| Offset Entities | Relación viva con la original; **no** offsetea si da geometría autointersectada; Cap ends y bidireccional (SW: `c_Offset_Entities.htm`, `HIDD_OFFSET1.htm`) | Desfase asociado y de dos lados (`offset_sketch_curves direction`); sin tapas | Autointersección: la prueba la fase 3. Cap ends: solo SW, sin fila |
| Trim | Cinco modos (Power trim con arrastre, Corner, Inside, Outside, To closest) y «Keep trimmed entities as construction»; mantiene las cotas de lo recortado (SW: `HIDD_TRIM_CHOICES.htm`) | Un modo (como Fusion) | El arrastre coincide con Fusion → H-110. El resto es solo SW |
| Extend | La mitad de la curva bajo el cursor decide el sentido (SW: `t_Extend_Entities.htm`) | `extend_sketch_curve` usa el punto elegido | Equivalente |
| Split | Un punto parte una curva abierta; círculo, elipse o spline cerrada necesitan **dos** (SW: `c_split_entities.htm`) | `partir` | La fase 3 prueba partir un círculo |
| Move/Copy | «Keep relations»: desmarcado, solo se rompen las relaciones con lo no elegido (SW: `t_Moving_or_Copying_Sketch_Entities.htm`) | `transform_sketch` | La fase 3 prueba qué relaciones conserva |
| Scale | Punto base, factor, Copy y **Number of Copies** (SW: `t_Scaling_Sketch_Entities.htm`) | `transform_sketch scale` con `copy` | Cantidad de copias: solo SW, sin fila |
| Mirror | Relación Symmetric por cada par de puntos; eje = línea, centerline o arista del modelo (SW: `c_Mirror_Entities.htm`) | `mirror_sketch` | La fase 3 prueba la asociatividad |
| Linear/Circular Pattern | Instancias a saltar, Fix X-axis direction, cotas opcionales de separación (SW: `HIDD_DVE_SKETCH_PATTERN_LINEAR.htm`) | Suprimir instancias y editar (`edit_sketch_pattern`) | Equivalente en lo que Fusion también tiene |
| Polygon | De **3 a 40 lados** (SW: `t_Sketching_Polygons.htm`) | Tope propio (P-70 lo unificó en el núcleo) | Dato para los casos límite de la fase 3 |
| Chamfer | Ángulo-distancia, distancia-distancia y distancia igual (SW: `HIDD_DVE_SKETCH_CHAMFER.htm`) | Los tres | Equivalente |

Ni Fusion ni SOLIDWORKS documentan qué pasa con un radio de empalme imposible o un chaflán más largo que el tramo:
sin dato en las dos ayudas.
