# Faltantes

Funciones que todavía no existen. La especificación de cada ID está en el `docs/brechas_*.md` que nombra cada sección. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-20 (secciones Boceto, Superficie y Sólido: 2026-10-24). Total 74: Abierto 47 · Parcial 24 · Bloqueado 2 · Sin verificar 1 (2026-11-13: el cambio 3 pasó las filas de prioridad 2 a despues.md; 2026-11-12: fusión de B-385; 2026-11-13: sumó BOC-84 Estrella; 2026-11-13: ASM-18 pasó a Parcial (componente vacío, nombre y «A partir de cuerpos» por API); 2026-11-13: se cerró CF-15 (Gerardo aprobó el ViewCube); 2026-11-12: fusión de GZ-26; 2026-11-12: fusión de CF-15; 2026-11-13: H-115 nuevo (Grosor de tangencia del Empalme, visto en P-141); 2026-11-12: sumó GZ-26 (flecha de radio de la Rosca, E1); 2026-11-12: sumó CF-15 de Gerardo (ViewCube como el de Fusion); 2026-11-10: entraron H-113 y H-114 de los videos de roscas; 2026-11-07: +H-110 de la fase 2 de CREAR y MODIFICAR; H-109 y H-111 ya cerrados).

## Pendientes generales

Abierto 13 · Parcial 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-22a | Modo seguro (contador de arranques fallidos) | Abierto | Media | Sin programar. | grep «modo seguro» y «arranques fallidos» en omnicad/: sin resultados | 2026-10-20 |
| P-22b | Diario del solver de bocetos (grabar y reproducir) | Abierto | Media | Sin programar; serviría de corpus para R4. | omnicad/restricciones/ sin diario | 2026-10-20 |
| P-23c3 | c) Grupos anidados (mover un grupo dentro de otro) | Abierto | Media | Opción grisada: sin grupos anidados. | omnicad/ui/acciones_navegador.py | 2026-10-20 |
| P-23e2 | e) Ocultar perfil, Mostrar cota, Ocultar proyectadas y construcción fuera del editor | Abierto | Media | El visor general no dibuja esas cuatro capas; grisadas fuera del editor. | omnicad/ui/acciones_navegador.py:281-288 | 2026-10-20 |
| P-25f | f) INSPECCIONAR: análisis de pila de fijadores (Fastener Stack Analysis) | Abierto | Media | No existe. No aparece en las capturas de INSPECCIONAR. | docs/brechas_inspeccionar.md | 2026-11-01 |
| P-25h | h) SELECCIONAR: arrastre de componentes (casilla) | Abierto | Media | No existe la casilla. | grep «Arrastre de componentes» en omnicad/ui: sin resultados | 2026-10-20 |
| P-11g | d) Nombres de los cuerpos del .f3d (panel, aro_izq, perno_1) | Abierto | Alta | Están en el flujo de diseño pero no se encontró cómo ligarlos a cada cuerpo del SAB. | PROJECT_LOG.md:32; notas en privado/reportes/upgrades3/notas_flujo_diseno.md | 2026-10-20 |
| P-23c2 | c) Copiar y Cortar en el navegador (hoy grisados) | Abierto | Alta | No hay portapapeles paramétrico de cuerpos/pasos. | omnicad/ui/acciones_navegador.py:92 | 2026-10-20 |
| P-25e | e) ENSAMBLAR: Restricción de componentes y Relación de tangente | Abierto | Alta | No existen en la cinta. | omnicad/ui/cinta.py (grep «Restricción de componentes» y «tangente» en ENSAMBLAR: sin resultados) | 2026-10-31 |
| P-25e2 | e) Conjuntos de contacto y «Activar todos los contactos» (grisados) | Abierto | Alta | Botones grisados; misma brecha que SC6. | omnicad/ui/cinta.py:65 | 2026-10-20 |
| P-11h | d) Historial de operaciones del .f3d (traducir el timeline de Fusion) | Parcial | Muy alta | Los cuerpos entran como operación base y los bocetos como pasos; la tabla de tipos del flujo (BINCHA: 44 extrusiones, 14 empalmes, 9 chaflanes…) se declara al abrir. Las operaciones no se descifran: qué perfil usa cada extrusión y qué aristas toca cada empalme son recetas de nombre persistente que solo Fusion resuelve, y el archivo guarda solo el B-rep final (`docs/f3d_formato.md`: dos caminos probados). | tests/test_f3d_historial.py::test_abrir_un_f3d_con_historial_avisa_lo_que_no_se_tradujo; omnicad/io_archivos/f3d_historial.py | 2026-10-26 |
| P-11l | Bocetos de un .f3d con varios componentes | Abierto | Alta | El bloque `.smb` de bocetos no dice de qué componente es y la caja de los cuerpos no alcanza (415 de 418 perfiles de CARTERA GOTICA caen en más de un componente): hoy no se importan y se avisa. Hay que ligar cada `BREP.*.smb` con su componente leyendo los registros del flujo de diseño. | omnicad/io_archivos/f3d_nativo.py (_bocetos_ubicados); tests/test_f3d_bocetos.py::test_con_varios_componentes_los_bocetos_no_se_importan_y_se_avisa | 2026-10-26 |
| P-11m | Trazos abiertos, construcción, cotas, restricciones y nombres de los bocetos de un .f3d | Abierto | Muy alta | El `.smb` solo guarda las regiones cerradas: los bocetos importados no traen los trazos que no cierran región, la geometría de construcción, las cotas («4 mm», «120 mm»…) ni las restricciones, y se llaman Boceto1… Todo eso está en el flujo de diseño propietario. | omnicad/io_archivos/f3d_bocetos.py | 2026-10-26 |
| P-11i | Referencias externas de un .f3z (diseños hijos referenciados) | Abierto | Muy alta | Se identifican las ocurrencias externas pero no se decodifica su disposición interna. | PROJECT_LOG.md:32 (upgrades3, SIN RESOLVER) | 2026-10-20 |
| P-12h | Hélice de boceto | Parcial | Media | Existe la espiral 2D; falta la hélice 3D (barrer/roscar a lo largo de ella). | omnicad/ui/modo_boceto.py:54; omnicad/ui/editor_boceto.py:1154; omnicad/ui/cinta_boceto.py:32 | 2026-10-20 |
| P-27-6 | Booleanas con holgura y formas listas para insertar (cono, pirámide, cuña, cápsula…) | Parcial | Media | Existen create_box/cylinder/sphere/torus; faltan holgura en booleanas y las demás formas. | omnicad/api/herramientas_solido.py:327 (create_box); herramientas create_cylinder/sphere/torus | 2026-10-20 |

## Hallazgos de pruebas de uso

Abierto 17 · Parcial 1 · Sin verificar 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| H-115 | Empalme sólido › falta «Grosor de tangencia» (Tangency Weight): Fusion lo trae en el diálogo del Fillet (ayuda «Fillet reference» › Tangency Weight), OmniCAD no tiene el parámetro | Abierto | Media | Sumar el peso de tangencia al empalme (núcleo, operación, campo a la vista y herramienta del MCP) | `clon/omnicad/ui/comandos/modificar.py:75` | 2026-11-13 |
| H-105 | Extruir superficie «Dos lados»: tipo de extensión propio del lado 2 (Al objeto, Todo) | Sin verificar | Media | Gemelo de H-81 (resuelto en el sólido el 2026-11-06). En superficie el lado 2 sigue siendo solo una distancia: `OpSupExtruir`, el panel y `create_surface_extrude` no tienen `extension2`/`hasta2`. La ayuda de Fusion para superficie dice «distances for each side independently» y no aclara si la extensión también va por lado: confirmarlo en Fusion antes de construir. | timeline/ops_superficie.py:100-151; ui/comandos/superficie.py:53-58; api/herramientas_superficie.py:75-125; docs/fusion_docs (Extrude a surface body) | 2026-11-06 |
| H-82 | Extruir › Al objeto sobre una cara: «Hasta caras adyacentes» (sólido) y «Extend Faces / Chain Faces» (superficie) | Abierto | Media | Sólido: Extender tiene cara, cuerpo y a través; falta To Adjacent Faces. Superficie: no tiene ninguna opción de Extender. | timeline/operaciones.py:1133 (`hasta_modo`); ui/comandos/superficie.py:55; ayuda `Extrude reference` y `Extrude a surface body` | 2026-11-05 |
| H-83 | Extruir, Revolución, Barrido y Solevación: operación «Componente nuevo» (sólido y superficie) | Abierto | Media | Fusion crea el cuerpo en un componente nuevo (diseño híbrido) en las cuatro herramientas (ayudas `Revolve reference`, `Sweep reference` y `Loft reference`, también en superficie). Hoy hay cuerpo nuevo, unir, cortar e intersecar; el componente se arma después con `create_component`. | timeline/operaciones.py:32 (`OPERACIONES_CUERPO`); api/herramientas_solido.py:183 | 2026-11-05 |
| H-84 | Extrusión delgada: Cadena tangente y conicidad con perfil abierto | Abierto | Baja | Falta la casilla Tangent Chain (elegir de una vez las curvas tangentes). La conicidad con perfil abierto da error; la ayuda no la restringe al tipo: confirmarlo en Fusion antes de hacerla. | ui/comandos/solido.py:33-35; nucleo/solidos_crear.py:487 | 2026-11-05 |
| H-88 | Revolución «A objeto» con «Dos lados» (sólido y superficie) | Abierto | Media | Fusion: con Tipo de extensión «To Object» la Dirección ofrece One Side y Two Sides. En OmniCAD la ventana esconde la Dirección y `revolve` / `create_surface_revolve` con `to_object` y `direction="two_sides"` dan INVALID_ARGUMENTS («to_object gira hacia un solo lado»). | timeline/operaciones.py:1294 (`OpRevolucion.ejecutar`); timeline/ops_superficie.py:195 | 2026-11-05 |
| H-90 | Solevación sólida: condición «Punto tangente» en un perfil punto | Abierto | Baja | Fusion ofrece Sharp y Point Tangent (cúpula). La ventana del sólido solo ofrece «Aguda» y `loft end_condition={"type": "point_tangent"}` da «type es free, direction, tangent o smooth». La superficie ya lo hace (157,12 mm² contra la media esfera de 157,08). | ui/comandos/crear.py:144 (`_condiciones_de`) | 2026-11-05 |
| H-91 | Solevación sólida: condiciones de borde junto con carriles, línea central, cerrada o reglada, y exactas | Abierto | Alta | En el sólido, Dirección, Tangente y Suave son aproximadas con una sección auxiliar y dan «no se combinan con carriles, línea central, solevado cerrado ni reglado». Fusion las combina, y la superficie ya lo hace con la derivada exacta (SUP-13). | nucleo/solidos_crear.py:1307 | 2026-11-05 |
| H-96 | Repujado sobre caras que no son planas ni cilíndricas (esfera, cono, forma libre) | Abierto | Alta | Fusion repuja sobre cualquier cara del cuerpo. OmniCAD da «El repujado admite caras planas o cilíndricas (envolviendo)»: cuadro 6×6 sobre el polo de una esfera r 20 (`sondas_nrr.py rep_esfera`). | nucleo/solidos_crear.py:1571 | 2026-11-05 |
| H-97 | Repujado: asas de alineación (desplazamiento horizontal, vertical y giro) en la vista | Abierto | Media | Fusion: «Use the distance manipulator… / angle manipulator in the canvas» para Horizontal Distance, Vertical Distance y Rotation Angle. OmniCAD tiene los tres campos (en Más opciones) pero solo el asa de Profundidad. Pieza `nervio_red_repujado` («asas de alineación»). | ui/comandos/asas_extra.py:308 (`_asas_repujado`) | 2026-11-05 |
| H-19 | Vínculo de movimiento solo lineal | Abierto | Alta | Vínculo no lineal para biela-manivela; depende de resolver los lazos cerrados (H-18). | api/herramientas_ensamble.py:642-659 (valor unión 2 = ratio × unión 1) | 2026-10-20 |
| H-4 | Insertar: derivación y Duplicar con uniones hechos; falta el catálogo de piezas | Parcial | Media | Falta un catálogo local de piezas estándar más allá de las fijaciones (rodamientos, perfiles, pasadores…; sin servicios en línea): hay que decidir qué piezas y sus medidas. Duplicar con uniones copia un componente por vez, las copias son independientes (sin instancias asociativas) y no tiene los modos de destino «Entre dos caras» e «Intersección de dos aristas» ni «Borrar último duplicado». | ui/cinta.py:59 (Duplicar con uniones); api/herramientas_ensamble.py (duplicate_with_joints); ui/comandos/derivacion.py:16; api/herramientas_documento.py:322 (insert_derive); tests/test_derivacion.py; tests/test_duplicar_con_uniones.py; nucleo/fijaciones.py (solo fijaciones) | 2026-10-31 |
| H-69 | Organización del boceto: la geometría suelta no tiene nombre, ocultar, bloquear ni «en perfiles» propios | Abierto | Media | Hoy cada curva suelta se lista en Geometrías y su menú ofrece Seleccionar, Convertir en objeto (queda rígido, fuera del solver) y Eliminar. Falta guardar esas propiedades por curva sin sacarla del solver ni duplicar el modelo de objetos (plan_boceto_organizar.md, secciones 4 y 8). | clon/omnicad/ui/navegador_boceto.py (menú de `curva_boceto`); clon/tests/test_boceto_organizar.py::test_categorias_salen_del_dato_y_un_grupo_no_cambia_la_de_sus_miembros | 2026-11-05 |
| H-70 | Organización del boceto: expandir el contenido interno de un SVG o DXF (capas y formas) en el navegador | Abierto | Media | El SVG/DXF se lista como una unidad y sus partes solo se cuentan. Falta listar capas y formas bajo demanda (sin crear miles de filas) y poder elegir una pieza interna sin romper el contorno ni el relleno (plan_boceto_organizar.md, secciones 2 y 7). | clon/omnicad/ui/navegador.py (`_ramas_boceto`); clon/omnicad/restricciones/objetos.py (`unidades`) | 2026-11-05 |
| H-76 | Exportar STEP y OBJ con los colores (cuerpos y caras pintadas) | Abierto | Media | El STEP se escribe sin colores (`escribir_step` usa STEPControl, no la versión con XCAF) y el OBJ sin .mtl; el glTF sí los lleva. Comprobar en Fusion qué colores guarda su STEP antes de construir. El 3MF multicolor es P-27-11. Ver docs/brechas_aspecto.md. | clon/omnicad/nucleo/intercambio.py (`escribir_step`); clon/omnicad/io_archivos/exportar.py (`exportar_obj`) | 2026-11-05 |
| H-113 | Rosca › flecha en el visor para cambiar el tamaño de la rosca (arrastrar cambia Tamaño, Designación y el cilindro) | Abierto | Media | Asa de arrastre sobre la cara, como Fusion (0:36–0:56). Gerardo (2:30): «DEBERÍA PODER VER LAS FLECHAS PARA ADAPTAR EL TAMAÑO» | Ayuda de Fusion «Thread reference» (`scripts/fusion_docs.py ver "Thread reference" -s fusion-model`); `evidencias/videos_roscas_2026-11-10/informe.md`; captura `Fusion_0m40_cara_elegida_flechas_y_vista_previa.png` | 2026-11-10 |
| H-114 | Rosca › vista previa de la rosca cosmética (anillos sobre la cara) | Abierto | Media | Fusion dibuja los surcos aunque «Modelado» esté sin tildar; OmniCAD muestra el cilindro liso | `clon/omnicad/ui/comandos/crear.py` (Rosca); `evidencias/videos_roscas_2026-11-10/informe.md`; capturas `Fusion_0m33_dialogo_vacio_aceptar_gris.png`, `OmniCAD_0m30_dialogo_rosca_cosmetica_aviso.png` | 2026-11-10 |

## Boceto (auditoría contra la ayuda de Fusion, 2026-10-23)

Abierto 1 (H-110 de la fase 2 de CREAR y MODIFICAR). Plan por fases: [plan_boceto.md](../plan_boceto.md). Cada ID incluye su herramienta MCP/CLI, su test y la doc regenerada.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| BOC-84 | Herramienta «Estrella» del boceto (pedido de Gerardo, propia de OmniCAD: Fusion no la tiene): puntas 3–64, redondeo de puntas y de valles, proporción interior, giro, modo {n/m}, restricciones y `draw_star` | Abierto | Media | Sin empezar; especificación en [plan_boceto.md](../plan_boceto.md), sección BOC-84. Conviene hacerla junto con P-154 (editar el número de lados después de dibujar) | omnicad/ui/modo_boceto.py; omnicad/ui/editor_boceto.py | 2026-11-13 |

## Superficie (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SUPERFICIE con los artículos de la ayuda de Fusion (sección Fusion-Patch de `docs/fusion_docs/`) y de probar las 14 herramientas por MCP/CLI. Los bugs se reprodujeron; los scripts de prueba (`sonda*.py`) están en `evidencias/superficie_2026-10-24/`, fuera de git.

Parcial 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SUP-13 | Solevación de superficie: condiciones de borde, guías y pesos | Parcial | Alta | Hecho: condición por sección, alineación de bordes, rieles (también hasta un perfil punto, y en lazo con solevación cerrada), línea central, «Fusionar» y cadena; las condiciones se combinan con rieles y con línea central; Dirección, Tangente y Suave de los extremos fijan la derivada de salida con el peso como velocidad (medido: desvío de la salida de Tangente 5e-4 contra 0,106; Suave se separa de la cara 2e-4 mm contra 1,2e-3; con peso 2, unos 0,4°), también con rieles. Los pasos guardados antes siguen con secciones auxiliares (`condicion_exacta` falso) y dan lo mismo. Queda aproximado, con secciones auxiliares: Dirección en un perfil de en medio, Punto tangente, las condiciones con línea central y las de perfiles que no se emparejan (distinta cantidad de esquinas, como rectángulo a círculo: repartir el contorno redondearía las esquinas). Queda sin combinar: solevación cerrada con línea central (`MakePipeShell` de OCC no lo hace) y tramos rectos con guías o condiciones. ⚠ Qué valor de peso equivale a cada peso de Fusion no se pudo comparar: el MCP de Fusion no conecta. Ayuda: Loft reference (Surface). | omnicad/nucleo/superficies.py (`solevar_superficie`, `_solevar_con_rieles`, `_derivadas`, `_exacta_posible`); tests/test_superficie_guias.py::test_tangente_exacta_sale_con_la_direccion_de_la_cara | 2026-11-01 |
| SUP-14 | Parche: peso de tangencia por arista | Parcial | Media | Hecho: continuidad por arista (Agrupar aristas), rieles y puntos interiores e Invertir normal (`create_patch`: group_edges, edge_continuity, interior, flip). Falta el peso de tangencia (Tangency Weight, G1 y G2) por arista. Intento acotado (2026-10-31): `MakeFilling.Add`, `GeomPlate_*Constraint` y `GeomFill_ConstrainedFilling` no tienen peso (los criterios G0/G1/G2 son tolerancias; Coons es de 3 o 4 lados y calcula solo el largo de la derivada). `Plate_Plate` sí acepta una derivada con valor explícito, pero la placa es una altura sobre un plano medio: con G1 la pendiente la fija la cara de soporte y el largo de la tangente no existe en esa parametrización. Un peso real pide un relleno parametrizado por el borde; el atajo (puntos o secciones auxiliares sobre la tangente, como en la solevación) es una aproximación y no se simuló. Ayuda: Patch open areas on a surface body. Evidencia local: `evidencias/sup14_peso_2026-10-31/` (fuera de git). | omnicad/nucleo/superficies.py (`parche`); tests/test_superficie_fusion.py::test_parche_continuidad_por_arista_y_guias_interiores | 2026-10-31 |
| SUP-17 | Extender: alineación libre en caras curvas y valor por defecto de Fusion | Parcial | Baja | Hecho: Alineación de bordes del tipo Natural (`edge_alignment`): «alinear» (G1, lo de siempre y el valor por defecto) y «libre» (G0: además extiende una cara no rectangular en UV; plana con una franja tangente, curva —esfera, cilindro, cono, toroide, B-spline— sobre su propia superficie; un parche de relleno plegado fuera de sus límites cae a la franja tangente plana). Falta solo que el valor por defecto sea el de Fusion (Free Edges): se dejó «alinear» a propósito, porque cambiarlo haría que las recetas viejas den otro resultado (decisión de la tanda 1). Ayuda: Extend a surface body. | omnicad/nucleo/superficies.py (`extender`, `_extension_libre`); tests/test_superficie_fusion.py::test_extender_alineacion_libre_en_una_cara_curva_no_rectangular | 2026-10-31 |

## Sólido (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SÓLIDO (y PLÁSTICO, CONSTRUIR, INSPECCIONAR, INSERTAR, SELECCIONAR) con los artículos de la ayuda de Fusion (carpeta `fusion-model`) y de probar unas 70 herramientas por API con valores normales, de borde e inválidos. Los bugs se reprodujeron; los scripts (`s*.py`) están en `evidencias/solido_2026-10-24/`, fuera de git. Lo que ya estaba cargado (SC12, SC3, P-25d, P-25f, P-25g2, P-25i, P-25j) no se repite.

Parcial 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SOL-8 | Barrido sólido: Ruta + Superficie guía, Barrido de cuerpo, orientación Alineada y cadena tangente | Parcial | Alta | El barrido de un cuerpo sólido es aproximado: une copias del cuerpo a lo largo de la ruta (error de escalonado ≈2 % en un arco). Probé dos caminos exactos y ninguno anda: (1) `BRepOffsetAPI_MakePipe` de cada cara del cuerpo más el cuerpo inicial devuelve un sólido nulo e inválido para las caras que contienen la tangente de la ruta (en un cuarto de arco da 535,6 contra 566,65 exactos); (2) `MakePipeShell` con la cara como perfil recoloca el perfil de forma impredecible según la orientación de la cara (se ve en las cajas envolventes de los barridos). Test que lo muestra: `test_barrido_de_cuerpo_en_arco_se_acerca_al_volumen_exacto_y_la_via_por_caras_se_queda_corta`. Ya están Ruta + Superficie guía, orientación Alineada, `sweep_bodies` (aproximado) y la selección encadenada de aristas de cuerpo. | omnicad/nucleo/solidos_crear.py › `barrer`; tests/test_sol08_barrido.py | 2026-10-25 |
| SOL-22 | Retícula volumétrica (giroide o cruz) dentro de un cuerpo | Parcial | Alta | Ya están Cruz, Celda X, X 2.5D y a medida (sólido; solidez hasta donde la geometría de la celda llega: la Celda X llega a 99 %, la Cruz a 90 % y no a 95 %), Gyroid, Schwarz P y Schwarz D (malla, también sobre una malla cerrada), solidez en gradiente por una ruta, zona de desfase con mezcla y mover/girar las celdas. Quedan aproximaciones con su salida: la malla achaflana las aristas vivas un paso de grilla (≈3 % de volumen en un cilindro a 2 mm; se afina con `resolution` a costa de tiempo y memoria); en 2.5D con solidez variable el espesor cambia por capa de celdas, no de forma continua; con solidez variable las barras no se unen punta a punta y se llega antes al tope de 800 barras (subir la celda). Comparado con las capturas de Fusion: faltan OctetoTruss y Panal, las pestañas Configuración, Solidez y Desfase, el manipulador para mover y girar, y Restablecer. | omnicad/nucleo/reticula.py; tests/test_sol22_reticula.py; docs/brechas_extensiones.md | 2026-11-01 |
| SOL-24 | Reconocer funciones (Find Features) en cuerpos importados | Parcial | Muy alta | Rehace como pasos del timeline (`rebuild_features`, verificado por volumen y caja) los agujeros, empalmes y chaflanes. La extrusión (un prisma, con sus agujeros pasantes en el perfil) también se rehace como boceto + extrusión (`rebuild_features types=[extrude]`). Revoluciones, simetrías y patrones se reconocen y se informan, pero no se rehacen: la revolución necesita cortar el perfil por el eje (un sólido que contiene al eje da un perfil que lo cruza y `revolve` lo rechaza) y los patrones exigirían quitar copias y rearmarlas con su patrón. Faltan simetría en planos que no sean X, Y o Z por el centro, patrones radiales y extrusiones escalonadas. | omnicad/nucleo/reconocer_funciones.py; tests/test_sol24_reconocer_funciones.py | 2026-10-25 |

## SUPERFICIE contra capturas de Fusion (2026-11-01)

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SUP-27 | Cinta de SUPERFICIE como Fusion: ítems y nombres | Abierto | Media | Faltan Derivar, Patrón, Simetría, Llenado, Origen de la unión, Chaflán, Quitar, Material físico, Administrar y Lista de materiales. | docs/brechas_superficie.md § SUP-27; ui/cinta.py:128 | 2026-11-01 |
| SUP-28 | Empalme y Chaflán de superficie completos | Abierto | Alta | Tipos, tipo de radio, cadena tangente y esquina; hoy son 3 campos. | docs/brechas_superficie.md § SUP-28; `fillet_surface` rechaza radius_type y tangent_chain, por API | 2026-11-01 |
| SUP-30 | Valores por defecto de superficie y paneles de material | Abierto | Media | Agrupar, Eje de proyecto, Anular recorte, Alargar y biblioteca de Material físico (el panel Aspecto ya está completo: `tests/test_aspecto_panel.py`). | docs/brechas_superficie.md § SUP-30 | 2026-11-01 |

## ENSAMBLAR contra capturas de Fusion (2026-11-01)

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| ASM-17 | Restricción de componentes: Alinear, Ángulo, Centro y Tangente | Parcial | Muy alta | Hechos Alinear, Ángulo, Centro y Tangente (2026-11-12): paso `restriccion` del timeline (`OpRestriccion`), herramienta `constrain_components` (`type` align, angle, center o tangent; `angle_reference`, `geometry1b`/`geometry2b`), comando y botón de ENSAMBLAR: caras coplanares, ejes concéntricos y puntos coincidentes con desfase y voltear; ángulo entre caras, aristas o ejes, con referencia de ángulo opcional; centro de una cara (o del plano medio de dos) entre las dos caras del otro componente, con voltear; tangente entre caras planas, cilíndricas, esféricas, cónicas y toroidales, aristas rectas y circulares, ejes y vértices, con «Todas las caras» (apagado exige que las caras se toquen); tabla de filas (`rows` en la API, «+ Agregar restricción» en el panel): se resuelven todas a la vez y el conflicto se avisa; cada fila lleva su nombre y su desfase (editables en la lista del panel y en `rows`), y un parámetro que solo cita el desfase de una fila extra recalcula el paso; límites de desfase por fila en Alinear y Ángulo (`offset_min`, `offset_max`, `offset_as_rest`; recorta y avisa, con apoyo es error); vista previa al pasar el cursor por la geometría del componente 2 (`PREVIA_SOBRE`, como «Preview On Hover»); y aviso con el nombre de cada unión que une un componente movido con otro que no se movió. Falta: Tangente con curvas libres (hoy error claro) y cono, toro o círculo con otra cosa que un plano, animar los límites («Preview Limits») y editarlos después desde el navegador, «Solve All Constraints» (resolver con las restricciones anteriores del timeline) y que el conflicto con una unión se compruebe en geometría y no solo se avise. | docs/brechas_ensamblar.md § ASM-17; `tests/test_asm17_alinear.py`; `clon/omnicad/timeline/ops_ensamblar.py` (`OpRestriccion`) | 2026-11-12 |
| ASM-18 | Nuevo componente vacío y con opciones de Fusion | Parcial | Alta | Hecho (2026-11-13): componente vacío (sin cuerpos, por API y por el comando), nombre del componente (campo del comando, `name`), Padre (ya estaba) y «A partir de cuerpos» por API (`from_bodies`: un componente por cuerpo, en un solo deshacer). Falta: «A partir de cuerpos» en el comando (un paso por cuerpo: el comando devuelve un solo paso), Tipo de componente (Estándar o Chapa: OmniCAD no tiene componentes de chapa, la chapa es de cada cuerpo), Externo con Tipo de diseño (crea otro archivo: decidir el alcance) y Activar (no hay componente activo; depende de ASM-9). | docs/brechas_ensamblar.md § ASM-18; `tests/test_asm18_nuevo_componente.py` | 2026-11-13 |
| ASM-19 | Menú ENSAMBLAR y paneles como Fusion | Abierto | Media | Orden, nombres, atajo Mayús+J, pestañas de Unión e Incluir hijos encendido. | docs/brechas_ensamblar.md § ASM-19; ui/cinta.py:57 | 2026-11-01 |

## Capturas de Fusion sin clasificar (2026-11-02)

Salen de las 674 capturas del escritorio, ya ordenadas en `analisis/capturas_fusion/` (índice: `INDICE.md`; las ya hechas se borraron, ver `borradas.tsv`). Abierto 10 · Bloqueado 2. Especificación: mirar las capturas de su sección y `scripts/fusion_docs.py buscar`.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CF-6 | Diálogo «¿Qué desea diseñar?» al crear un diseño | Abierto | Media | Tipo (piezas, ensamblaje, híbrido, dibujo), sistema de unidades y plantilla. Hoy `nuevo()` crea siempre un diseño vacío. Relacionada con H-5. | grep «Qué desea» en omnicad/: sin resultados; capturas `INTERFAZ/Nuevo_diseno*` | 2026-11-02 |

## Ensamblar (auditoría contra Fusion, 2026-10-25)

Cada fila salió de comparar ENSAMBLAR (uniones, componentes, grupo rígido, vínculos, estudio de movimiento) con los artículos de la ayuda de Fusion (carpeta `fusion-assemble`), de probar unas 60 llamadas por API (`evidencias/ensamble_2026-10-25/a*.py`) y de usar la ventana real como una persona (`scripts/prueba_ui/ensamblar.py`, 224 comprobaciones). Lo que ya estaba cargado (P-25e, P-25e2, SC6, SC7, SC8, SC15, H-4, H-5, H-19, F8, P-6d) no se repite.

Abierto 1 · Parcial 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| ASM-9 | Activar componente (lo que queda de los subensamblajes) | Parcial | Alta | Hecho el 2026-11-01: Nuevo componente con «Padre», navegador en árbol, mover o unir al padre arrastra a sus hijos (uniones, vínculos, posición inicial, Capturar y Revertir, estudio y arrastre del visor), «Incluir componentes secundarios» del grupo rígido, copiar y patronear subensamblajes enteros, `parent`/`children`/`path` en `get_assembly` y la lista de materiales. Falta Activar componente (Activate a component): el timeline muestra solo los pasos del componente activo (lo espera FU-14), padre y hermanos translúcidos, y lo que se crea entra al componente activo (uniones y estudios siguen en la raíz). | tests/test_ensamblar_asm9.py; scripts/prueba_ui/subensamblaje.py | 2026-11-01 |
| ASM-16 | Arrastrar componentes: lazos cerrados, rotar libre y varios a la vez | Abierto | Alta | El arrastre del visor (ASM-15, resuelto) sigue los grados de libertad de una unión y traslada los libres. Falta: resolver un lazo cerrado de uniones mientras se arrastra (hoy lo rechaza con un mensaje que manda a Accionar uniones), rotar un componente libre con el mouse (hoy, Editar posición inicial) y arrastrar varios componentes elegidos a la vez. Con algo sin capturar, elegir en el visor queda en pausa hasta Capturar o Revertir (en Fusion se sigue eligiendo). Ayuda: Capture or revert position of components. | omnicad/timeline/posicion.py (`que_arrastra`); tests/test_posicion_ventana.py::test_sin_capturar_ni_el_resaltado_ni_el_clic_eligen_la_posicion_vieja | 2026-11-01 |


## Asas de arrastre (gizmos) contra la ayuda de Fusion (auditoría 2026-10-26)

Se recorrieron los 148 comandos del catálogo y las cintas: 44 tienen asas (`Comando.manipuladores`) y 104 no. Acá solo están los que **la ayuda de Fusion dice que tienen manipulador** y OmniCAD no (o los tiene incompletos). Los comandos sin asa en Fusion (Alinear, Simetría, Combinar, Dividir, ejes, planos por puntos, análisis de color, etc.) quedan fuera a propósito. Las asas se arman con `ui/manipuladores.py` (Flecha, Angulo, AsaRadial, Posicion, Triada y las de calcomanía: giro, codo de escala y volteos). Cada gizmo lleva su prueba en `tests/` y en la pieza `asas` de `scripts/prueba_ui/`. Ya resueltos (están en el Registro): Lienzo, Calcomanía, las asas de Revolución de superficie y Reglada (SUP-25) y el tope de Extender (SUP-26). El que ya tiene fila propia: FU-4 (asas de Extruir).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Fusion 360

Abierto 1 · Parcial 1. Especificación: [brechas_fusion.md](../brechas_fusion.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| FU-14 | Engranaje del timeline: «Ocultar pasos inactivos» y «Cambiar a modelado directo» | Abierto | Alta | Hace falta un componente activo (que filtre el timeline) y un modo sin historial; el engranaje ya existe con «Muestra de color por componente» | ui/panel_timeline.py (engranaje con una sola opción); ui/acciones_navegador.py:164 («Cambiar al modelado directo» grisado) | 2026-10-21 |
| FU-8 | Historial de pasos al abrir un .f3d | Parcial | Muy alta | Los bocetos entran como pasos y el historial se declara al abrir (P-11h). Falta descifrar el flujo de diseño de Fusion o traducirlo con su API pública (el puente con Fusion abierto). | omnicad/io_archivos/f3d_historial.py; integraciones/fusion/OmniCADPuente (parámetros con Fusion) | 2026-10-26 |

## FreeCAD

Abierto 1 · Parcial 2 · Bloqueado 1. Especificación: [brechas_freecad.md](../brechas_freecad.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| F6 | Rebanar: N cortes paralelos como curvas, caras o láminas | Abierto | Media | Operación y comando de serie de cortes paralelos con salida a bocetos o cuerpos finos | sin código (grep rebanar/slice); existen dividir_cuerpo y cortar_plano de malla | 2026-10-20 |
| F2 | Revisar geometría con botón Reparar | Parcial | Media | Lista con clic por problema que resalta la pieza; mapa de color del espesor | 4fca4c7; nucleo/revision.py; ui/comandos/revision.py; api check_geometry, repair_body; tests/test_revision.py; tests/test_api_revision.py | 2026-10-20 |
| F8 | Uniones de transmisión (engranaje, cremallera-piñón, tornillo, correa) | Parcial | Media | Tipos de unión propios que calculen la relación solos (cremallera-piñón, tornillo, correa) | timeline/ops_ensamblar.py:461 OpVinculoMovimiento (factor manual); api/herramientas_ensamble.py:642 create_motion_link; create_gear_pair crea el vínculo con la relación de dientes | 2026-10-20 |
| F21 | Fragmentos booleanos, XOR, conectar e incrustar forma | Bloqueado | Media | Solo si el usuario lo pide: fragmentos, XOR y conectar/incrustar/recortar forma | sin código (grep xor/fragmento) | 2026-10-20 |

## Plasticity

Parcial 1. Especificación: [brechas_plasticity.md](../referencia/brechas_plasticity.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PL8 | Instancias que comparten geometría y Realizar instancias | Parcial | Media | Instancias de curvas de boceto y de operaciones del timeline | 4b50c6f; nucleo/solidos_crear.py:2793; api realize_copies; tests/test_pl8_instancias.py | 2026-10-20 |

## Blender

Abierto 2 · Parcial 2. Especificación: [brechas_blender.md](../referencia/brechas_blender.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B12 | Esparcir copias sobre una superficie | Abierto | Media | Tipo «Sobre superficie» del Patrón con densidad y semilla | timeline/ops_solido.py OpPatron: rectangular, circular, ruta, puntos; sin esparcir | 2026-10-20 |
| B10 | Ajustar a superficie (Shrinkwrap) | Abierto | Alta | Llevar curvas, mallas o puntos a una superficie (más cercano, eje o normal) | sin código (grep shrinkwrap/ajustar a superficie) | 2026-10-20 |
| B2 | Revisión de impresión 3D (espesor, voladizos, aristas filosas) | Parcial | Media | Lista con clic por problema y mapa de color sobre la pieza | 4fca4c7; nucleo/revision.py revisar_impresion; api check_printability; tests/test_revision.py; tests/test_api_revision.py | 2026-10-20 |
| B7 | Imán (snapping) completo en el visor | Parcial | Alta | Barra de imanes: vértice, arista, cara, centro de arista, perpendicular, varios a la vez | ui/manipuladores.py:51,297-347 (enganche a centro de cara, esquinas y puntos medios al ubicar) | 2026-10-20 |

## Rhino 8

Abierto 5 · Parcial 3. Especificación: [brechas_rhino.md](../referencia/brechas_rhino.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RH1 | Mezcla de superficies con continuidad G0 a G3 | Abierto | Alta | Mezclar bordes con continuidad por lado y radio o tensión variable | sin código (grep mezclar/blend en superficies); existen parche, reglada y sup_empalme | 2026-10-20 |
| RH2 | Igualar superficie o curva (Match) | Abierto | Alta | Mover un borde hasta coincidir en posición, tangencia o curvatura con otro | sin código (grep); solo reemplazar_cara sin continuidad | 2026-10-20 |
| RH4 | Desenrollar y solevación desarrollable | Abierto | Alta | Aplanar superficies desarrollables con mapa de distorsión y exportar a DXF | nucleo/chapa.py:609 patron_plano (solo chapa); sin Unroll ni Squish (grep) | 2026-10-20 |
| RH5 | Editar agujeros y caras de un cuerpo sin historial | Abierto | Alta | Mover, copiar y cambiar Ø o profundidad de un agujero existente; mover cara o arista | existen desfase_cara y borrar_caras; sin edición de agujeros existentes (grep) | 2026-10-20 |
| RH7 | Deformar: fluir, doblar, torcer, cónico, jaula, caída suave | Abierto | Muy alta | Operación Deformar con tipos, vista previa viva y manipulador | sin código (grep deformar/flow/bend/twist) | 2026-10-20 |
| RH6 | Seleccionar por criterio (duplicados, no manifold, planos, color) | Parcial | Media | Duplicados, objetos chicos, malos, no manifold, planos, por color o material | ui/ventana.py:420-421 (Seleccionar por nombre y por tamaño); ui/cinta.py:69-70; api find_edges, find_faces con selectores | 2026-10-20 |
| RH8 | Más superficies: red de curvas, entre curvas, cortina, por puntos | Parcial | Alta | Red de curvas, entre curvas, extrusión a un punto, cortina, superficie por puntos | timeline/ops_superficie.py:104 OpParche (cubre algo de EdgeSrf); ui/comandos/superficie.py:311; tests/test_comandos_superficie.py | 2026-10-20 |
| RH9 | Editar por puntos de control (curvas y caras) | Parcial | Alta | Mover CV de curvas 3D y caras, insertar nudo, cambiar grado, reconstruir, caída suave | restricciones/boceto.py:198 (spline de control en bocetos con pesos y nudos); ui/editor_boceto.py:2654 | 2026-10-20 |

## SolidCraft

Abierto 3 · Parcial 2. Especificación: [brechas_solidcraft.md](../brechas_solidcraft.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SC6 | Conjuntos de contacto en uniones y estudio de movimiento | Abierto | Alta | Implementar el contacto; el botón sigue grisado. | omnicad/ui/cinta.py:65 (grisado) | 2026-10-20 |
| SC8 | Uniones con relación: leva y tornillo | Abierto | Alta | Leva (cuchilla, rodillo, plano) y tornillo; hoy solo engranaje y cremallera. | omnicad/api/herramientas_ensamble.py:645 (create_motion_link solo ratio) | 2026-10-20 |
| SC3 | Nombres persistentes por historia del kernel | Abierto | Muy alta | Usar Modified/Generated de OpenCascade para nombrar caras y aristas. Ejemplo (2026-10-24): borrar un agujero rompe el empalme de las aristas paralelas a Z que viene después (REFERENCE_LOST). | omnicad/timeline/entidades.py (firma geométrica tolerante); sin BRepTools_History | 2026-10-20 |
| SC1 | Suite de piezas de referencia con valores analíticos | Parcial | Media | Faltan esperado.json con fórmulas cerradas (Pappus, Steiner) y la herramienta run_reference_tests. | tests/test_paridad_motor.py (paridad OpenCascade vs OmniKernel, ~55 casos); caso_paridad_motor.py | 2026-10-20 |
| SC5 | Configuraciones: tabla de filas con parámetros, supresiones y material | Parcial | Media | Falta material/aspecto por cuerpo en la fila y robustez al renombrar (la herramienta manage_configurations ya existe). | omnicad/timeline/documento.py:168-170,403; tests/test_administrar.py::test_configuraciones_aplican_parametros_y_supresion | 2026-10-20 |

## C++

Bloqueado 1. Especificación: [plan_cpp.md](../plan_cpp.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CPP-F2 | Fase 2 spike C++: módulo que recibe un TopoDS_Shape de OCP | Bloqueado | Media | Falta permiso para bajar cabeceras OCCT 8.0 y pybind11 >= 3. | docs/plan_cpp.md:75-82 | 2026-10-20 |
