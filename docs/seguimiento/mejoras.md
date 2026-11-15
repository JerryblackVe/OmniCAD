# Mejoras

Lo que ya existe y se puede hacer mejor: rendimiento, interfaz, calidad del código, instalador, documentación. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-20 (sección Boceto: 2026-10-23; Hallazgos de pruebas de uso, Superficie y Sólido: 2026-10-24; teselado y previas: 2026-10-28; Texto y vectores: 2026-11-04). Total 96: Abierto 41 · Parcial 45 · Bloqueado 2 · Sin verificar 8 (2026-11-12: fusión de FL-3d; 2026-11-12: fusión de P-98; 2026-11-12: fusión de FL-3c; 2026-11-12: fusión de P-78; 2026-11-14: FL-3 pasó a Parcial; 2026-11-12: fusión de FL-2; 2026-11-13: FL-9 pasó a Parcial; 2026-11-12: fusión de FL-1b; 2026-11-12: fusión de FL-1; 2026-11-12: fusión de BOC-84; 2026-11-12: fusión de RS-X4; 2026-11-13: el cambio 3 pasó las filas de prioridad 2 a despues.md; 2026-11-12: fusión de P-144b; 2026-11-13: cerró P-151, aprobado por Gerardo; 2026-11-13: plan de fluidez, FL-0 a FL-11; 2026-11-12: fusión de P-152; 2026-11-12: fusión de P-150; 2026-11-13: cerró P-149, aprobado por Gerardo; 2026-11-12: fusión de P-138; 2026-11-12: fusión de P-149b; 2026-11-13: sumó P-152 de Gerardo (temas con vista previa); 2026-11-12: fusión de P-78; 2026-11-12: fusión de P-139p; 2026-11-12: fusión de FU-2; 2026-11-13: RS-X3 pasó a Parcial (hover del boceto en lote: 2000 curvas de 153 a 3,9 ms, sin el tope de 400; falta el repintado); la sección Rust decía Abierto 15 y eran 14 (recontado por fila); 2026-11-12: fusión de RS-S1; 2026-11-12: fusión de P-139m; 2026-11-12: fusión de FU-3; 2026-11-12: fusión de P-147c; 2026-11-12: fusión de P-143b; 2026-11-12: fusión de BOC-38; 2026-11-13: se cerró FU-5 (el relleno azul del perfil ya existe, igual que Fusion); 2026-11-13: se cerró P-146 (detalle de rosca en una línea); 2026-11-12: fusión de P-141; 2026-11-12: fusión de P-149; 2026-11-12: fusión de P-144; 2026-11-12: se cerró P-145 (Gerardo aprobó la previa de la Rosca); fusión de P-135; 2026-11-12: fusión de P-145; 2026-11-12: fusión de P-147; 2026-11-12: fusión de P-143; 2026-11-12: fusión de P-148; 2026-11-12: sumó P-149 de Gerardo (colores, tamaño y opacidad de asas y superposiciones en Preferencias); se cerró TXT-9 (el clic en un trazo con relleno debajo avisa); sumaron P-147 y P-148 de la PC (asas de Dirección de la Solevación, escala de los peines); se cerró P-140 (ángulo de conicidad a la vista); se cerró BOC-61 (patrón de boceto: 1000 copias en 16 ms); se cerró P-142 (asas de los desfases y el giro de Repujado); se cerró BOC-82 (tangentes del boceto 3D en 11,5 ms); recontado por fila (P-95 y P-136 se habían borrado sin bajar el total; revisión previa a la versión); sumaron P-141 y P-142 de la auditoría de asas y paneles; 2026-11-11: sumó P-136 (distancias en 0 mm) y P-137 (flechas que se ven); 2026-11-10: P-78 al día con la medición contra Fusion de los videos de roscas; entraron P-133 a P-135 de los videos de roscas; entró P-132 de B-282 (cara plana inclinada sin rasgo); 2026-11-09: entraron P-98 del review de B-257 y P-130 de las fusiones; se cerró P-130; se cerró P-93; se cerró P-94; 2026-11-08: entraron P-94 y P-99; entró P-95 de la fase 6 de CREAR y MODIFICAR; P-92 entró y se cerró, igual que Fusion; 2026-11-07: se cerraron P-67 y P-72; entró P-73 de la fase 2 de CREAR y MODIFICAR).

## Pendientes generales

Abierto 10 · Parcial 9 · Sin verificar 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-99 | Extruir recalcula todos los perfiles en cada clic | Parcial | Alta | Reusar perfiles ya calculados o aislar la previa y medir en la PC. | tests/test_previa_prisma.py; evidencias/video_extrusion_2026-11-08/medir_extruir.py | 2026-11-12 |
| P-78 | Rosca modelada lenta | Parcial | Alta | El corte en sí (~0,35 s por corte en M40x3×30; Fusion ~0,05 s por rosca) y el corte que se tira cuando 0° falla: 229° primero lo ahorraría, pero rompe B-308. El costo ya no crece con el documento. | tests/test_p78_rosca_un_corte.py; PROJECT_LOG.md (2026-11-13 · P-78); nucleo/solidos_crear.py › `_cortar_helicoidal` | 2026-11-13 |
| P-61 | Las ventanas minimizadas de prueba pueden verse o tomar el foco | Abierto | Media | Medir foco y cursor en prueba_ui y evitar destellos sin romper atajos. | scripts/prueba_ui/arnes.py; clon/omnicad/prueba_humo.py | 2026-11-06 |
| P-40 | Extruir empieza en 10 mm y Fusion en 0 mm | Abierto | Baja | Gerardo debe decidir la distancia inicial. | omnicad/ui/comandos/solido.py (`Extruir`, valor inicial de la distancia) | 2026-10-28 |
| P-35 | El volumen exacto de cuerpos B-spline cuesta 0,5 s por llamada | Abierto | Baja | Guardar el volumen por forma o evitar mediciones sin aviso posible. | omnicad/timeline/operaciones.py; omnicad/nucleo/geometria.py | 2026-10-26 |
| P-36 | BRepCheck omite caras con más de 200 contornos | Parcial | Baja | Distinguir y revisar solo los contornos nuevos tras una booleana. | omnicad/nucleo/geometria.py (_es_valida_tras_booleana) | 2026-10-26 |
| P-33 | CI de main con ruff y pytest rápido en cada push | Abierto | Media | Crear el workflow y adaptar tests OpenGL; pendiente de Gerardo. | .github/workflows/ (solo instaladores.yml); AGENTS.md:50 | 2026-10-25 |
| P-10b-d | Fase 1: Rust y Zstandard con instalador | Abierto | Media | Migrar zstd_puro a Rust y probar .pyd, PyInstaller e instalador. | omnicad/io_archivos/zstd_puro.py; clon/rust/src/lib.rs | 2026-10-20 |
| P-10b-j | Bajar el dibujo Qt del boceto (11 ms con 10 000 puntos al mover la cámara) | Abierto | Media | Bajar de 5 ms el repintado completo del boceto. | PROJECT_LOG.md:341 | 2026-10-20 |
| P-22c | Casos límite y tolerancias explícitas en solver e intersecciones | Abierto | Media | Esferas anidadas y banda de tangencia sin tratar. | omnicad/restricciones/solver.py sin tratamiento de tangencia | 2026-10-20 |
| P-32 | Probar omnikernel ante uniones casi tangentes | Bloqueado | Media | Suspendido: OmniKernel en pausa (Gerardo, 2026-11-14). Comparar b39-1414 y el fuzzer; integrar solo si resuelve sin perder material. | scripts/fuzz_b39.py; tests/test_b39_revision.py | 2026-10-27 |
| P-10b-e | Fase 2: malla en Rust (R7, R2, R8, R10) con BVH R3 | Abierto | Alta | Reducir malla, half-edge, soldado y E/S de texto siguen en Python. | clon/rust/src/lib.rs solo tiene 3 funciones de render | 2026-10-20 |
| P-10b-g | Fase 4: remallado R6 en Rust y subir los topes | Abierto | Alta | Remallar sigue en Python con topes de 100 000 triángulos. | omnicad/nucleo/malla.py (TRIANGULOS_MAXIMOS_REMALLADO) | 2026-10-20 |
| P-10b-f | Fase 3: boceto en Rust (R5, solver R4, R9) | Abierto | Muy alta | Medir el solver antes de migrarlo a Rust. | omnicad/restricciones/solver.py; clon/rust/ | 2026-10-20 |
| P-9j | Auditar pantallas: estados vacíos, errores e identidad visual | Parcial | Media | Completar la revisión de estados e identidad visual tras 13 pantallas. | scripts/capturas_ui.py; evidencias/capturas/p9b_despues | 2026-10-20 |
| P-22d | Verificar tablas ISO 965/273 y reglas de chapa contra la norma | Parcial | Media | Verificar ISO 273 y K-factor de chapa. | omnicad/nucleo/tolerancias.py:10,163-200; commit 992b93c | 2026-10-20 |
| P-10b-c | Fase 5: previa asíncrona, memo por paso y firmas | Parcial | Alta | Completar P6 y deshacer serializado en un hilo. | omnicad/timeline/documento.py; omnicad/io_archivos/proyecto.py | 2026-10-20 |
| P-10b-h | Trabajador Python para teselado y HLR cancelables en paralelo | Parcial | Alta | Crear el pool para teselado y vistas. | omnicad/nucleo/aislado.py; tests/test_b48_crash.py | 2026-10-20 |
| P-10f | Paso 6: Rust con PyO3 solo si los números lo justifican | Parcial | Muy alta | Implementar el resto de R1-R13 según las filas RS-. | clon/rust/src/lib.rs (rasterizar, visibilidad, oclusion); omnicad/nativo.py | 2026-10-20 |
| P-11k | Comparar EXTRUSOR XOX.f3z contra Fusion y probar mallas convertidas | Sin verificar | Baja | Importarlo en Fusion puede crear diseños en la nube del usuario; sin ejemplo BINCHA a mano. | PROJECT_LOG.md:32 | 2026-10-20 |
| P-31-lic | Respetar licencias AGPL-3.0 (PartMode, QymCAD, Chili3D): solo ideas, nunca código | Sin verificar | Media | Regla de proceso, no tarea; no se puede comprobar contra el código. | PROJECT_LOG.md:117 | 2026-10-20 |
| P-156 | Holgura de impresión 3D única (Gerardo, 2026-11-15): un valor general calibrado con la placa, aplicado a la rosca modelada (agujero agranda, tornillo achica), al molde (Cortar con «Dejar holgura») y a «La otra pieza es: Impresa / Metálica»; UI de una línea | Abierto | Alta | Diseño aprobado y qué reemplaza: ver la ficha «P-156» en Detalle | Gerardo, `evidencias/reportes_pc/2026-11-15_gerardo_rosca/holgura_impresion_negativa.png` | 2026-11-15 |
| P-157 | Reorganizar Preferencias como Fusion: cada opción en su página, visual, poco texto, nada cortado a 1024×700, grisados con su motivo (Gerardo, 2026-11-15) | Abierto | Alta | Ver la ficha «P-157» en Detalle; junta P-152, CF-7, CF-8, NOV-tip-2/3/4 y P-2d | Gerardo, `evidencias/reportes_pc/2026-11-15_gerardo_preferencias/` | 2026-11-15 |
| P-158 | Mensajes de los paneles cortos y gráficos en toda la app (Gerardo, 2026-11-15): 1 renglón con ícono, el tope a la vista en el asa y el campo y la previa en rojo, sin consejos largos; auditoría de todos los mensajes y test de largo | Abierto | Alta | Ver la ficha «P-158» en Detalle | Gerardo, `evidencias/reportes_pc/2026-11-15_gerardo_textos_largos/empalme_mensaje_gigante.png` | 2026-11-15 |

## Hallazgos de pruebas de uso

Abierto 5 · Parcial 7.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| H-98 | Repujado cilíndrico exige marcar «Envolver en la cara» | Abierto | Baja | Envolver automáticamente sobre caras curvas, como Fusion. | nucleo/solidos_crear.py:1573 | 2026-11-05 |
| H-68 | Parámetros automáticos de cotas y operaciones, con preferencia | Abierto | Media | Estudiar los nombres de Fusion y crear los parámetros automáticamente. | timeline/parametros.py | 2026-11-03 |
| H-5 | Insertar componente no distingue pieza de ensamble | Abierto | Media | Decidir si hace falta el modo «diseño de pieza» y deshabilitar Insertar componente ahí. | grep sin resultados: solo ui/navegador.py:220 pone la etiqueta «Diseño de piezas» (informativa) | 2026-10-20 |
| H-37 | Cobertura de operaciones, interfaz, .fclone y .f3d | Parcial | Media | Cubrir los 59 tipos restantes y explicitar la razón pendiente por tipo. | tests/test_barrido_tipos.py; tests/test_f3d_nativo.py | 2026-11-03 |
| P-133 | Biblioteca de roscas en ventana completa con árbol y filtros | Abierto | Alta | Rehacer la biblioteca con favoritos, filtros y ficha con dibujo. | clon/omnicad/ui/comandos/crear.py:535; evidencias/videos_roscas_2026-11-10/informe.md | 2026-11-10 |
| P-134 | Rosca: aceptar y campos según cara; lista de Tamaño en el panel | Abierto | Baja | Deshabilitar sin cara y contener la lista Tamaño en el panel. | clon/omnicad/ui/comandos/crear.py:893; evidencias/videos_roscas_2026-11-10/informe.md | 2026-11-10 |
| P-135 | Rosca parcial: asas de Longitud y Desfase en el visor | Parcial | Media | Obtener la aprobación de Gerardo de la captura comparada con Fusion. | clon/omnicad/ui/comandos/crear.py; evidencias/videos_roscas_2026-11-10/informe.md | 2026-11-10 |
| P-139 | Anillos de ángulo como Fusion en las herramientas | Parcial | Media | Obtener el OK de Gerardo para Mover/copiar e Inclinación; «⋮» va en P-144. | tests/test_manipuladores.py; evidencias/reportes_pc/2026-11-12_gizmo_angulo_fusion/ | 2026-11-12 |
| P-143 | Empalme: flecha del radio y marcador «◁▷» como Fusion | Parcial | Media | Obtener el OK de la captura y estudiar el marcador «◁▷» en Fusion. | evidencias/reportes_pc/2026-11-12_empalme_4_aristas/ | 2026-11-12 |
| P-147 | Solevación: asas de Ángulo y Peso de despegue | Parcial | Media | Obtener el OK de Gerardo para la captura de convención angular. | Reporte de la PC: `evidencias/reportes_pc/2026-11-12_solevacion/` (`fusion_asas_direccion.jpg`, `omnicad_direccion_sin_asas.jpg`, video 4:20) | 2026-11-12 |
| P-154 | Cambiar Lados de un polígono ya dibujado | Parcial | Media | Reconocer polígonos terminados por sus restricciones y rehacerlos al editar. | clon/tests/test_boc84_estrella.py; pieza boceto_herramientas | 2026-11-13 |
| P-150 | Empalme y chaflán: aristas elegidas sin previa gruesas y sin profundidad | Parcial | Media | Decidir si afinar y dar profundidad a las aristas sin previa en todos los comandos. | tests/test_manipuladores.py; evidencias/p150_2026-11-13/p150_empalme_fusion_vs_omnicad.png | 2026-11-13 |

## Fusion 360

Abierto 2 · Parcial 1. Especificación: [brechas_fusion.md](../brechas_fusion.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| FU-3 | Cota de ángulo contra el eje X y barrido del arco | Parcial | Media | Ver en Fusion qué cota deja el barrido del arco central y replicarla. | ui/editor_boceto.py (`_cotas_de_lo_escrito`, rama `arco_centro`) | 2026-10-20 |
| FU-10 | .f3z con referencias externas | Parcial | Media | Resolver los diseños referenciados; hoy se abre solo el diseño principal | io_archivos/f3d_nativo.py:24,70; io_archivos/abrir_externo.py:39 | 2026-10-20 |

## FreeCAD

Parcial 3. Especificación: [brechas_freecad.md](../brechas_freecad.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| F4 | Referencias perdidas: reparar al editar un paso temprano | Parcial | Media | Reelegir en el acto la referencia perdida desde el panel del paso | tests/test_comandos.py; tests/test_hallazgos_tortura.py | 2026-10-20 |
| F5 | Diagnóstico del boceto: restricciones en conflicto y redundantes | Parcial | Media | Avisar conflictos y redundancias sin F5, cuidando el costo y el tope. | restricciones/solver.py; tests/test_restricciones_ui.py | 2026-10-31 |
| F12 | Herramientas de B-spline | Parcial | Media | Insertar nudo, subir/bajar grado, unir curvas y convertir a B-spline como herramientas | restricciones/boceto.py; ui/editor_boceto.py | 2026-10-20 |

## Plasticity

Parcial 2. Especificación: [brechas_plasticity.md](../referencia/brechas_plasticity.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PL3 | Plano de trabajo con una tecla (Espacio) | Parcial | Baja | Mayús+Espacio desde la cámara y que primitivas y Mover arranquen en ese plano | fdc9366; ui/ventana.py:395,2088; tests/test_plasticidad.py::test_espacio_arranca_el_boceto_sobre_la_cara_ya_elegida | 2026-10-20 |
| PL1 | Un comando contextual según lo elegido (Desfase, Unir, Extender…) | Parcial | Media | Integrar Unir, Invertir, Extender, Reconstruir, Alinear e Imprimir. | ui/comandos/modificar.py:757; tests/test_pl1_desfase.py | 2026-10-20 |

## Blender

Parcial 1. Especificación: [brechas_blender.md](../referencia/brechas_blender.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B8 | Orientaciones y pivotes (global, local, normal, vista, cursor 3D) | Parcial | Media | Selector de orientación y pivote (mediana, caja, activo) y cursor 3D | ui/comandos/modificar.py:462-500 (Mover/copiar con pivote elegible y tríada); ui/manipuladores.py Triada | 2026-10-20 |

## Rhino 8

Parcial 3. Especificación: [brechas_rhino.md](../referencia/brechas_rhino.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RH13 | Análisis ampliado: continuidad, desviación, normales visibles | Parcial | Media | Continuidad por borde G0/G1/G2, desviación entre curvas o puntos y normales visibles | nucleo/revision.py; tests/test_revision.py | 2026-10-20 |
| RH18 | Curvas desde superficies y cuerpos (isocurvas, contorno, silueta) | Parcial | Media | Agregar Contour por cortes paralelos y Pull como curvas de boceto. | api/herramientas_boceto.py:1581 | 2026-10-20 |
| RH12 | Gumball al elegir e imanes en el visor | Parcial | Alta | Agregar manipulador contextual y barra de imanes con seguimiento (B7). | ui/manipuladores.py; ui/sugerencias.py:30 | 2026-10-20 |

## Boceto (auditoría contra la ayuda de Fusion, 2026-10-23)

Abierto 4 · Parcial 2 · Sin verificar 1. Plan por fases: [plan_boceto.md](../plan_boceto.md). P-73: fase 2 de [auditoria_boceto_crear_modificar.md](../auditoria_boceto_crear_modificar.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-76 | Boceto y texto extruible sobre caras curvas | Abierto | Alta | Diseñar la función tras auditar CREAR/MODIFICAR; base H-109 y H-98. | video PhyCAD 04:06 | 2026-11-08 |
| BOC-80 | Verificar las ayudas del boceto 3D contra Fusion real | Sin verificar | Media | Mirar en Fusion cruces solo en pantalla y tangentes fuera del plano. | omnicad/restricciones/inferencia3d.py; tests/test_inferencia3d.py | 2026-11-01 |
| BOC-49 | Acelerar el rearmado del índice de ayudas con miles de entidades | Parcial | Media | Medir el costo restante y vectorizarlo o pasarlo a Rust si pesa en uso real. | clon/tests/test_boc49_indice_incremental.py; clon/omnicad/restricciones/inferencia.py | 2026-11-13 |

## Superficie (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SUPERFICIE con los artículos de la ayuda de Fusion (sección Fusion-Patch de `docs/fusion_docs/`) y de probar las 14 herramientas por MCP/CLI. Los bugs se reprodujeron; los scripts de prueba (`sonda*.py`) están en `evidencias/superficie_2026-10-24/`, fuera de git.

Sin pendientes.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Sólido (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SÓLIDO (y PLÁSTICO, CONSTRUIR, INSPECCIONAR, INSERTAR, SELECCIONAR) con los artículos de la ayuda de Fusion (carpeta `fusion-model`) y de probar unas 70 herramientas por API con valores normales, de borde e inválidos. Los bugs se reprodujeron; los scripts (`s*.py`) están en `evidencias/solido_2026-10-24/`, fuera de git. Lo que ya estaba cargado (SC12, SC3, P-25d, P-25f, P-25g2, P-25i, P-25j) no se repite.

Abierto 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Patrones de sólido (auditoría 2026-10-31)

Cada fila salió de la auditoría de Patrón rectangular, circular, en trayectoria, en puntos y Multitransformación contra
la ayuda de Fusion y el video de uso. Parcial 1. Informe y matriz por herramienta:
[patrones-solidos-2026-10-31.md](../auditorias/patrones-solidos-2026-10-31.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PAT-1 | Extensión simétrica con cantidad par sin medir en Fusion real | Parcial | Baja | Medir en Fusion Extensión simétrica con n par y el patrón en ruta. | tests/test_patrones_solidos_semantica.py | 2026-11-01 |

## Paneles de herramienta (auditoría 2026-10-31)

Salió de los dos videos de uso comparados con SolidCraft y de abrir los 148 comandos y 16 diálogos en la ventana real.
Sistema común, matriz por herramienta y capturas antes/después: [ui_paneles_2026-10-31.md](../auditorias/ui_paneles_2026-10-31.md).
Sin verificar 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| UI-2 | El escalado real de Windows (125 % y 150 %) y los monitores nuevos no se probaron | Sin verificar | Baja | Probar paneles al 125/150 % real de Windows y al cambiar de monitor. | scripts/prueba_ui/paneles_temas.py | 2026-10-31 |
| UI-6 | Comparar las agrupaciones de opciones con la ayuda de Fusion | Sin verificar | Media | Crear una matriz por comando de opciones agrupadas y avanzadas en Fusion. | docs/auditorias/ui_paneles_2026-10-31.md | 2026-10-31 |
| P-132 | Distinguir caras planas inclinadas al elegirlas | Abierto | Baja | Añadir ángulo o área en describir_ref sin desbordar el botón. | Informe Construir 2026-11-10 (B-282) | 2026-11-10 |

## Menú del boceto (decisión del usuario)

Bloqueado 1. Las herramientas export_sketch y clean_sketch ya existen: lo que falta es solo el menú.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| MCP-HAL3 | Menú del boceto sin «Guardar como SVG» ni «Limpiar geometría» | Bloqueado | Baja | Espera decisión del usuario: agregarlos rompe la lista exacta de Fusion. | omnicad/ui/ventana.py:1258 (manejador SVG sigue); export_sketch y clean_sketch existen | 2026-10-20 |

## SolidCraft

Abierto 1. Especificación: [brechas_solidcraft.md](../brechas_solidcraft.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SC20 | Mostrar mallas provisionales al abrir mientras se recalcula | Abierto | Media | Guardar mallas con control de tamaño y versión sin reemplazar el diseño. | omnicad/io_archivos/proyecto.py:85 | 2026-10-26 |

## Otros CAD libres

Abierto 1 · Parcial 1. Especificación: [brechas_cad_libres.md](../referencia/brechas_cad_libres.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-11n | .f3d: lector SAB y escena en Rust (Zstandard ya está) | Parcial | Alta | Migrar lector SAB y escena a datos PyO3; meta BINCHA ≤ 6 s. | omnicad/io_archivos/sab.py; omnicad/io_archivos/f3d_escena.py | 2026-10-31 |
| P-11o | .f3d: mallas convertidas grandes entran sin reparar | Abierto | Media | Reparar por partes o en Rust solo si el usuario muestra el caso. | omnicad/nucleo/acis_occ.py; tests/test_f3d_nativo.py | 2026-10-26 |

## Texto y vectores

Abierto 1. Especificación: [plan_texto_vectores.md](../plan_texto_vectores.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-96 | SVG: rellenos casi transparentes de Affinity dejan pestañas | Abierto | Baja | Comparar Fusion y filtrar por opacidad con aviso y opción de importación. | `evidencias/svg_valientes_2026-11-08/` (`valientes.svg`, `repro.py`) | 2026-11-08 |

## Fluidez (plan 2026-11-13)

Pedido de Gerardo: «tomá como prioridad mejorar el rendimiento, debe ir todo fluido». Especificación y mediciones: [plan_fluidez.md](../plan_fluidez.md). Orden: FL-0 (y a la vez FL-8 y B-396) → FL-1 → FL-2 → FL-4 y FL-3 → FL-5, P-78 (F6) y RS-X4 (F7) → FL-10.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| FL-0 | F0 banco de fluidez: `scripts/bench_fluidez.py` (15 escenarios como usuario, 4 con las piezas reales) + `tests/test_fluidez.py`; prueba_ui falla con un `bloqueo_ui` de más de 1 s; filtro de falsos y de acciones viejas | Parcial | Media | Hecho: banco, presupuestos y tabla hoy/meta. Falta commit e integración (coordinador); los presupuestos bajan con cada paquete FL. | docs/plan_fluidez.md | 2026-11-13 |
| FL-2 | F2 previa barata inmediata al teclear y arrastrar | Parcial | Alta | Extruir (Nuevo, Unir, Cortar en rojo) y Revolución hechos. Queda la previa cosmética inmediata de la rosca (escenario b) y medir a y b con el banco de FL-0 en la PC. | tests/test_fl2_previa_barata.py | 2026-11-13 |
| FL-3 | F3 aceptar, editar, deshacer y abrir fuera de la ventana | Parcial | Alta | Abrir, Aceptar, editar, deshacer y rehacer van en otro hilo con barra y Cancelar (`motor_impreso` 4389 → 117 ms; Rosca 2028 → 210 ms); falta verlo en Windows (E11) y Abrir de `ABANICO EMILIA` y `gatoRL` por encima de 250 ms (ver ficha). | tests/test_fl3b_aceptar_aparte.py | 2026-11-14 |
| FL-3c | Resto de FL-3b en el llavero (por API, `bloqueo_ui`): editar un paso viejo traba 1900 ms en un solo bloque; Unir 17 perfiles 5917 ms; Cortar 3190 ms; deshacer y rehacer 588 y 716 ms (en motor_impreso sí quedó en trozos de ~115 ms) | Parcial | Alta | Hecho 2026-11-15 (E6): con el puente en vivo un paso nuevo va al proceso aparte (`Documento.nuevos_aparte`; un documento chico nunca iba: no hay previa que mida su costo) y las mallas se hacen en otro hilo antes de avisarle a la ventana (`PuenteAgentes._mallar_en_hilo`, `Documento.diferir_avisos`); si el proceso aparte falla, el paso se calcula como siempre (`execute_code` queda afuera: ya tiene la ventana tomada). La barra de un cálculo aparte (abrir, Aceptar, editar) muestra los pasos que lleva el trabajador (`aislado.avanzar`/`avance`; motor_impreso: 53/292 a los 7 s, 286/292 a los 54 s); antes quedaba vacía. Bloqueo máximo en la VPS, mismo llavero, antes → ahora: editar op15 2,2 s → 0,43 s; Unir 17 perfiles 5,2 → 0,31 s; Cortar 3,7 → 0,29 s; deshacer y rehacer 0,75 → 0,45 s; una caja chica 0,09 s. **Queda:** los 0,3-0,45 s que siguen en la ventana (leer el cálculo y `_conservar_formas`); verlo en Windows con E11; el camino del mouse (Aceptar del panel) no se midió acá; la 1.ª edición después de abrir es 2-3× más lenta (E11, ronda 10: motor_impreso editar inicio 18 s, medio 7,5 s; deshacer y rehacer no usan caché). | E11, `evidencias/reportes_pc/2026-11-14_e11_fl3b_b48_b440/`; tests/test_fl3c_puente_aparte.py (barra: test_fl3c_la_barra_muestra_los_pasos_y_no_se_cierra_sola) | 2026-11-15 |
| FL-3d | Extruir join por API en el llavero (op58 → LLAVERO 2, la misma forma ya existe) tarda ~67 s en la PC y ~82 s en la VPS (mismo archivo y md5): 63,6 s de 64,6 s se van en `BRepClass3d_SolidClassifier.State()` dentro de `_queda_enterrada` (`geometria.py:908/913`, atajo de B-39): 4008 llamadas de 14 ms en la PC y 2004 de 33 ms en la VPS. Join a LLAVERO 1 o desde op1: 1,7 s; new_body: 0,12 s. No es regresión ni propio de Windows | Sin verificar | Media | Hecho 2026-11-15 (E6): `_queda_enterrada` arma un clasificador por sólido (`_clasificador`) y lo reusa con `Perform` para cada vértice y muestra; antes armaba uno por punto (14-33 ms cada uno). Mismo veredicto y mismo volumen. VPS, mismo llavero (op58, perfiles 0..16, -3, join): 86,7 s → 3,3-8,1 s (máquina con carga 11,7); a LLAVERO 1, 3,7 → 3,0-3,2 s. No es vía rápida nueva: el atajo de B-39 sigue igual. **Queda:** que E11 lo mida en Windows | E11, `evidencias/reportes_pc/2026-11-15_fl3d_windows/resumen.md`; tests/test_b39_enterrada.py (test_fl3d_el_atajo_arma_un_clasificador_por_solido_y_no_uno_por_punto) | 2026-11-15 |
| FL-4 | F4 Unir y Cortar solo contra los cuerpos que tocan (filtro por caja envolvente) | Abierto | Media | Filtrar por caja: mismo resultado y tiempo con 1 u 11 cuerpos (±20 %). | docs/plan_fluidez.md | 2026-11-13 |
| FL-5 | F5 el costo de una operación local crece con el largo del documento | Abierto | Alta | Medir 10/40/80 pasos y limitar el aumento de costo al 20 %. | docs/plan_fluidez.md | 2026-11-13 |
| FL-8 | F8 congelamientos ajenos a la geometría | Parcial | Media | Acelerar sección; medir repintado de preferencias y registro (meta i < 100 ms). | docs/plan_fluidez.md | 2026-11-13 |
| FL-9 | F9 trabajador precalentado; segundo solo con 8 GB libres | Parcial | Media | Falta evitar los 0,2-0,4 s de importar el trabajador al abrir un comando en el primer segundo y crear el segundo trabajador con 8 GB libres (CPP-C3; ver ficha). | tests/test_fl9_precalentar.py; docs/plan_fluidez.md | 2026-11-13 |
| FL-10 | F10 reusar mallas y extraerlas en bloque (RS-X6, CPP-P20, CPP-C1) | Abierto | Alta | Reusar y extraer mallas en bloque; CPP-C1 requiere permiso para dependencias. | docs/plan_fluidez.md | 2026-11-13 |
| FL-11 | F11 regla de fluidez y reporte diario de los diez peores bloqueos | Abierto | Baja | Tras FL-0, exigir test_fluidez verde y bloqueos ≤ 250 ms en AGENTS.md. | docs/plan_fluidez.md | 2026-11-13 |

## Rust

Abierto 7 · Parcial 5 · Sin verificar 2. Especificación: [plan_rust.md](../plan_rust.md). Orden de ejecución y mediciones: [rust-pipeline-2026-10-31.md](../auditorias/rust-pipeline-2026-10-31.md) (filas RS-X*).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RS-R13 | R13 menores (RDP, DXF/SVG, recortes, generar_grupos) | Abierto | Baja | Ganancia absoluta chica. | omnicad/io_archivos/vectorizar.py; dxf.py | 2026-10-20 |
| RS-R9 | R9 hit-testing del boceto | Abierto | Media | Medir el lote sin carga y usar Rust solo si supera 2 ms con miles de curvas. | omnicad/ui/editor_boceto.py | 2026-10-31 |
| RS-R3 | R3 BVH: accesibilidad, vaciado, proyección y punto más cercano | Parcial | Media | Integrar usos restantes y completar SAH y multihilo si hacen falta. | clon/rust/src/bvh.rs; tests/test_bvh_rust.py | 2026-10-31 |
| RS-R5 | R5 geometría de boceto (de Boor, intersecciones) en Rust | Parcial | Alta | Añadir splines cerradas/con manijas, mas_cercano, intersecciones y cajas. | clon/rust/src/spline.rs; omnicad/restricciones/solver.py | 2026-10-29 |
| RS-R4 | R4 kernel del solver (jacobiano analítico) en Rust | Abierto | Muy alta | Evaluar migrar el kernel y jacobiano del solver a Rust tras RS-S1. | omnicad/restricciones/solver.py | 2026-10-20 |
| RS-P3 | P3 repintado del boceto proyectando en bloque | Parcial | Media | Bajar de 5 ms el repintado completo, incluido Qt. | omnicad/ui/editor_boceto.py _poli_px; PROJECT_LOG.md:341 | 2026-10-20 |
| RS-X2 | Abrir un proyecto con caché tarda lo mismo que recalcularlo | Abierto | Baja | Guardar volumen y usar cajas baratas; abrir ≤ 1,5 s sin cambiar volúmenes ni avisos. | omnicad/io_archivos/proyecto.py; omnicad/nucleo/geometria.py | 2026-10-31 |
| RS-X3 | Selección bajo el cursor y repintado del boceto | Parcial | Media | Medir sin carga: meta 8 ms con 400 curvas; si no llega, sacar el bucle de la clave. | omnicad/ui/editor_boceto.py (`paintEvent`, bucle de curvas) | 2026-11-13 |
| RS-X5 | Verificar la caché de mallas por cara con modelos grandes | Sin verificar | Baja | Probar float32 y 256 MB; set_modelo repetido de 500 mil triángulos ≤ 50 ms. | omnicad/nucleo/render_cpu.py (_TOPE_BYTES_CARAS, _guardar_malla_cara) | 2026-10-31 |
| RS-X7 | Editar `motor_impreso` en el paso 73 y `gatoRL` no llegó a la meta de RS-X1 | Abierto | Alta | Acelerar cortes OCC: motor_impreso paso 73 ≤ 1 s y gatoRL ≤ 3 s. | omnicad/nucleo/aislado.py | 2026-11-01 |
| RS-X6 | Una previa rechazada hace volver a mallar lo recalculado | Abierto | Media | Conservar la identidad de las formas tras Esc para evitar remallarlas. | omnicad/timeline/calculo_aislado.py; tests/test_trabajador_persistente.py | 2026-11-02 |
| RS-X8 | El arreglo planar en Rust une caras cuando un cruce es casi tangente | Abierto | Media | Corregir el orden angular y certificar en Rust los cruces casi tangentes. | omnicad/nucleo/perfiles.py; tests/test_texto_curva.py | 2026-11-01 |

## C++

Abierto 5 · Parcial 5 · Sin verificar 1. Especificación: [plan_cpp.md](../plan_cpp.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CPP-P17 | P17 reusar BRepClass3d_SolidClassifier | Parcial | Baja | Reusar clasificadores en _queda_enterrada y al revisar vértices. | omnicad/nucleo/fijaciones.py:634-653; omnicad/nucleo/geometria.py:565-575 y 1042 | 2026-10-31 |
| CPP-C5 | C5 clasificación masiva de puntos contra sólidos | Abierto | Media | Ver CPP-P17. | omnicad/nucleo/fijaciones.py:636 | 2026-10-20 |
| CPP-P18 | P18 encadenado de aristas O(n²) con cKDTree | Abierto | Media | Sin cambios. | omnicad/nucleo/superficies.py y solidos_crear.py sin cKDTree | 2026-10-20 |
| CPP-P20 | P20 un solo BRepMesh por lote y caché de teselado entre visores | Abierto | Media | Sin empezar. | omnicad/ui/visor3d.py; omnicad/nucleo/geometria.py:499,642 | 2026-10-20 |
| CPP-C1 | C1 malla en bloque con id de cara (BRepMesh + extracción) | Abierto | Muy alta | No hay código C++; depende del spike de ABI. | grep C++ en el repo: sin carpeta cxx; teselar_por_cara en omnicad/nucleo/geometria.py | 2026-10-20 |
| CPP-C2 | C2 evaluación de superficies por lote (normales, curvatura, isocurvas) | Abierto | Muy alta | Sin empezar. | omnicad/nucleo/analisis.py _props_nodos | 2026-10-20 |
| CPP-P23 | P23 HLR exacto o rápido según tipo de superficie | Parcial | Media | Elegir HLR rápido para superficies que no son libres. | omnicad/nucleo/dibujo.py:242,345-373 (PLAZO_HLR, es_forma_libre) | 2026-10-20 |
| CPP-C3 | C3 ejecutor sin GIL de hojas OCC independientes | Parcial | Alta | Crear un pool por cuerpos o vistas. | omnicad/nucleo/aislado.py | 2026-10-20 |
| CPP-C4 | C4 hojas cancelables (booleana, sección, revisión) | Parcial | Alta | Agregar cancelación de booleanas y sección. | omnicad/nucleo/aislado.py; tests/test_b16_cancelar.py | 2026-10-20 |
| CPP-F1 | Fase 1 proceso trabajador en Python (teselado por cuerpo, HLR por vista, botón Cancelar) | Parcial | Alta | Completar el pool paralelo y el botón Cancelar en la interfaz. | omnicad/nucleo/aislado.py | 2026-10-20 |
| CPP-P21 | P21 sección del análisis usando el contorno que ya calcula | Sin verificar | Media | Comprobar si seccion() evita el cálculo repetido y corregirlo si hace falta. | omnicad/nucleo/analisis.py:1088 seccion; omnicad/ui/analisis_vista.py:60-70 (caché) | 2026-10-20 |

## Auditoría del 2026-10-14

Abierto 1. Especificación: [auditorias/](../auditorias/).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| AUD-6 | Evitar cuellos O(n²) en concavidad y empalmes masivos | Abierto | Media | Indexar orientación por cara y mapa por empalme; máscara de 2000 agujeros < 1 s. | nucleo/analisis.py:873; nucleo/solidos_modificar.py:266 | 2026-11-01 |

## Prueba de tortura

Parcial 1. Especificación: [informe_tortura_2026-10-17.md](../auditorias/informe_tortura_2026-10-17.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| T-21 | check_geometry agota 10 s por cada rosca modelada distinta | Parcial | Media | Evitar el tope inicial por rosca: evaluar hélices o pares de caras vecinas. | clon/omnicad/nucleo/revision.py; tests/test_tortura_menores.py | 2026-11-01 |

## Tipografía de la interfaz (2026-10-28)

Abierto 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| NOV-tip-1 | Letra grande: títulos de cinta elididos y ventana mínima de 1038 px | Abierto | Media | Compactar títulos de grupo y botón de espacio de trabajo al 120–150 %. | omnicad/ui/cinta.py; evidencias/tipografia_ui/f3_ventana_150.py | 2026-10-28 |

## Detalle de lo abierto

### P-158 · Mensajes de los paneles: cortos, con ícono y gráficos (Gerardo, 2026-11-15)
Gerardo: «estos textos gigantes no los quiero. Son feos y el usuario no los va a entender. Hay que hacer la app más intuitiva, menos texto, más gráfica, más entendible hasta para un niño de 10 años». Caso: el aviso del Empalme de 6 renglones («el asa frena en 36.26 mm… reordená los empalmes del timeline…»).
Especificación (prioridad 1: toca los paneles de bocetos y sólido):
1. **Mensaje del panel: máximo 1 renglón corto**, con ícono (⚠ o ✖) y una palabra clave, p. ej. «⚠ Radio máx. 36,2 mm». El detalle va en un «?» con tooltip, o no va.
2. **Mostrar en vez de explicar:** el tope en el asa misma (marca o tope rojo donde frena), el campo en rojo cuando el valor no entra, la previa en rojo.
3. **Sin consejos largos** en el panel; si hace falta, a la ayuda.
4. **Auditoría de TODOS los mensajes de los paneles** (bocetos → sólido → superficie → resto): lista de los que pasan de 1 renglón y su versión corta.
5. **Test** que falle si un mensaje de un panel pasa de N caracteres. La guía de estilo es la regla de nivel 1 n.º 14 de CLAUDE.md (15641c8); AGENTS.md solo la nombra.
Casos ya vistos: `nucleo/superficies.py:1380` (solevación de superficie cerrada, mensaje largo; E10, 15/11).
Relación con otras filas: B-436 (mensajes que dicen otra cosa; lo tiene E9) sigue aparte porque corrige el CONTENIDO, pero sus mensajes nuevos ya siguen este estilo. P-2b (traducción) va aparte: se traducen las versiones cortas.

### P-157 · Reorganizar Preferencias: ordenado, visual, poco texto (Gerardo, 2026-11-15)
Gerardo: «todo tiene que estar bien ordenado en su lugar, bien explicado pero intuitivo, más visual, sin mucho texto, fácil de entender, que hasta un nene de 10 años entienda». Capturas: `evidencias/reportes_pc/2026-11-15_gerardo_preferencias/`.
Señalado: los temas de la interfaz están en «General» y van en «Apariencia»; el rótulo «Mi tema (Azu…al) (propio)» sale cortado; «Se aplica al instante, sin reiniciar» queda cortado abajo; Idioma y Orientación grisados sin explicar por qué.
Especificación:
1. Árbol de páginas igual al de Fusion (`docs/fusion_docs`, Preferencias); cada opción en su página.
2. Muestras visuales en vez de textos largos, con una frase corta por opción.
3. Nada cortado a 1024×700.
4. Las opciones grisadas, con su motivo en el tooltip.
Reemplaza y junta (filas borradas el 2026-11-15; su detalle queda acá):
- **P-152:**  **Qué:** Preferencias › General › «Tema de la interfaz» es un combo de texto y no se ve cómo queda ningún tema antes de aceptar (Gerardo: «no hay forma visual para ver los temas antes de aceptar») · **Queda:** Hecho (2026-11-13, `ui/selector_temas.py`: tarjetas con miniatura, vista previa al pasar el mouse y al elegir, Cancelar vuelve, temas propios). Queda: que Gerardo apruebe la captura (`evidencias/p152_2026-11-13/`) · **Evidencia:** `evidencias/p152_2026-11-13/` (capturas); `clon/omnicad/ui/selector_temas.py`; `clon/tests/test_p152_selector_temas.py`
- **CF-7:**  **Qué:** Preferencias: páginas que no existen **Queda:** Páginas Dibujo, Configuraciones, Renderizar (valores por defecto), Material, Diseños híbridos y de ensamblaje, Unidades por defecto (Diseño) y Visualización de unidad y valor (faltan 10 de 13 ajustes). **Evidencia:** omnicad/ui/preferencias.py; capturas `INTERFAZ/Preferencias_*`
- **CF-8:**  **Qué:** Preferencias: opciones sueltas de General y Gráficos **Queda:** Hechas: el tamaño del ViewCube (cinco tamaños como Fusion, en Preferencias › General y en el clic derecho del ViewCube, API incluida) y la barra espaciadora que repite el último comando (`general/espacio_repite`) — tanda C11, 2026-11-06; el tema del sistema (`general/tema` = `sistema`: sigue al claro/oscuro de Windows, como «Match Device Theme» de Fusion; el tema queda fuera del MCP, como manda CLAUDE.md) y los presets de ratón Alias, Inventor, PowerMill y SOLIDWORKS (`general/raton`, también en la API; con Inventor, F2/F3/F4 navegan en el visor en vez de Renombrar) — tanda C13, 2026-11-06. Faltan: (a) orientación Y o Z hacia arriba: el combo «Orientación de modelado por defecto» solo ofrece «Z hacia arriba», y darlo vuelta toca el marco de la cámara en 15 lugares de 6 archivos (`ui/visor3d.py`: `ojo`, `desplazar`,
- **NOV-tip-2:**  **Qué:** Fuente de la interfaz: la lista no tiene buscador ni grupo de recomendadas, y el combo cerrado no muestra la forma de la letra elegida **Queda:** Hecho el 2026-10-29: cada familia de la lista se escribe con su propia letra y la lista abre acotada (14 filas con barra). Falta: caja de búsqueda dentro de la lista, grupo «Recomendadas» arriba (hoy solo van primero las de lectura fácil) y la fuente elegida mostrada con su letra en el combo cerrado. Pedido de Gerardo del 2026-10-29 (captura de Preferencias a 109 % y video 09-38-04), para una sesión nocturna. **Evidencia:** omnicad/ui/preferencias.py (`_combo_fuentes`, `_agregar_familia`)
- **NOV-tip-3:**  **Qué:** Colores de texto: el selector es el de Qt, sin el tema de la app, y un color rechazado solo avisa «probá uno más claro» **Queda:** Hecho el 2026-10-29: cada fila muestra el color real (nunca el código), marca en rojo el rechazado y el aviso va en criollo. Falta: selector de color con el tema de la app, proponer con un clic un color parecido que sí se lea, y mostrar «elegido» frente a «aplicado» cuando se rechaza. **Evidencia:** omnicad/ui/preferencias.py (`CampoColor`, `_Muestra`, `_mostrar_aviso_apariencia`)
- **NOV-tip-4:**  **Qué:** Preferencias › Apariencia no tiene vista previa propia, y los espacios y tamaños de la interfaz no están en un solo lugar **Queda:** Un panel de muestras (botón, campo, texto normal y secundario, acento y una cota del boceto) que cambie al instante con fuente, tamaño y colores; y valores comunes (espacios, radios, alturas) en un solo lugar para que todo escale parejo con letra grande. Validar a 100, 125 y 150 % y en 1024×640 y 800×520, con capturas antes y después. Pedido de Gerardo del 2026-10-29, para una sesión nocturna. **Evidencia:** omnicad/ui/preferencias.py, omnicad/ui/temas.py, omnicad/ui/cinta.py
- **P-2d:** | P-2d | Selector de idioma en Preferencias y test de cadenas sin traducir | Abierto | Media | Sin selector ni test que falle por cadena sin traducción; AGENTS.md aún exige TODO en español. | omnicad/ui/preferencias.py sin clave de idioma | 2026-10-20 |

### P-156 · Holgura de impresión 3D única (diseño aprobado por Gerardo, 2026-11-15)
Gerardo: «sí hazlo, pero hazlo con una UI intuitiva y simplificada» y «esto es una mejora de holgura. No dejes piezas sueltas: si una pisa la otra, borra». Especificación:
1. **Un valor general** en Preferencias, «Holgura de impresión 3D», por lado. Se calibra con la placa de `create_clearance_test`: se elige el agujero que mejor encaja y ese valor queda guardado (botón «Usar este valor»). Toda rosca nueva lo trae por defecto.
2. **Rosca modelada sobre una cara de Ø nominal:** decide sola si es agujero o tornillo. En el agujero agranda y en el tornillo achica todo el perfil (cresta, raíz y flancos) con el valor general.
3. **Molde:** en Combinar › Cortar con «Conservar herramienta», una casilla «Dejar holgura» que agranda la herramienta por ese valor antes de cortar (reemplaza el desfase a mano).
4. **«La otra pieza es: Impresa / Metálica».** Impresa: cada pieza se lleva la mitad. Metálica: la holgura entera va a la pieza impresa.
5. **UI simple:** en el panel de Rosca, una sola línea, «Holgura de impresión: 0,2 mm por lado», con el valor general cargado y una casilla para activarla. Sin campos sueltos ni términos técnicos. La previa cambia mientras se escribe. Tooltip: «Agranda el agujero o achica el tornillo para que rosque al imprimir».
6. Negativos: siguen rechazados; si hace falta un ajuste apretado, se propone en una línea.
**Qué REEMPLAZA y qué se borra (un solo valor, un solo camino):** la holgura vieja `print_clearance` de `create_hole` y `create_thread` (`api/herramientas_modificar.py`), `api/herramientas_calibracion.py`, `nucleo/calibracion.py`, `timeline/ops_calibracion.py` y `api/guia/flujo.md`. El parámetro viejo pasa a leer el mismo valor general (los archivos viejos lo traen y se respeta) o se borra; docs, MCP, CLI y `docs/agentes/herramientas.md` se actualizan en el mismo commit. También absorbe la holgura de P-27-6 (booleanas) y de P-29-1 (perfil de impresora). H-118 (desfase de caras de una rosca, paridad con Fusion) sigue aparte y NO es esta solución.
Además: MCP y CLI para cada opción nueva; tests numéricos de los Ø en agujero, tornillo y molde; comparar la UI con los paneles de Fusion.

### P-99 · Extruir recalcula todos los perfiles en cada clic

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Extruir se traba en la ventana: cada clic de perfil recalcula y el programa no responde como Fusion · **Queda:** Queda: cada clic sigue extruyendo y teselando TODOS los perfiles elegidos (con 28 perfiles en la VPS, 1,6 s: la malla del visor de los 28 cuerpos ~0,7 s, la extrusión ~0,3 s, validar y medir cada cuerpo ~0,4 s), así que crece con cada perfil. Falta reusar lo ya calculado de los perfiles anteriores (malla por contenido o extrusión incremental) o mover la previa a segundo plano; y medir otra vez en la PC de Gerardo. Hecho 2026-11-12 (E6): la plantilla del asa se arma al primer arrastre y la herramienta de «Nuevo» sale de la previa: 1 extrusión por clic en vez de 3 · **Evidencia:** Video `2026-11-08 20-07-53.mp4`; `evidencias/video_extrusion_2026-11-08/` (`medir_extruir.py`); registro de Gerardo 2026-11-11 (`evidencias/reportes_pc/2026-11-11_extrusion_rota/sesion_2026-11-11_211058_8968190f11d2_0001.jsonl`, 00:25:50-00:26:21 UTC): cada clic que suma un perfil congela más que el anterior, 0,53 → 0,92 → 1,05 → 1,05 → 1,37 → 1,69 → 2,04 s hasta 29 perfiles (y 3,5 s a las 00:34): recalcula la previa entera por clic; repro en la VPS con su autoguardado (`evidencias/reportes_pc/2026-11-11_extrusion_rota/`, 31 perfiles, `xvfb-run`): 30 clics 34,7 → 22,6 s, clic 28 2,42 → 1,62 s; `tests/test_previa_prisma.py::test_cada_cambio_sin_arrastre_extruye_una_sola_vez`

### P-78 · Rosca modelada lenta y más costosa al crecer el documento

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Rosca modelada lenta: entre 9 y 175 veces más que Fusion (0,04–0,10 s por rosca) y crece con el documento · **Queda:** Medido el 2026-11-10 por API, mediana de 3 (Fusion contra OmniCAD): M8 completa 54 contra 966 ms; M8 parcial 10 mm 36 contra 315 ms; M20 de 60 mm 48 contra 8390 ms; agujero roscado M6 50 contra 540 ms; recalcular 4 modeladas + 1 cosmética 163 contra 8730 ms (la cosmética es pareja). Crece con el documento: la M20 sola tarda 1,1 s y después de tres M8 en el mismo documento, 8,2 s. Medir con relojes por función adónde van esos ~7 s (`ag8_medicion/relojes_todo.py`; cProfile ve solo ~1 s). Candidato sin confirmar: `_cortar_helicoidal`, con hasta 12 cortes de reintento (4 giros × 3 tolerancias). Hecho antes: corte difuso primero (M3×20: 17,0 → 2,1 s; ANSI y GB M20: 2,1 → 0,5 s) y la hélice larga de un barrido (B-249). Del 2026-11-08 sigue: con clase, con giro 0 los 3 difusos dan corte vacío o inválido; idea probada y no integrada: recorrer todos los giros con 1e-4 antes del exacto y girar el CUERPO en vez del surco, que además conserva la fase (B-79) Reporte de Gerardo (2026-11-12, cilindro Ø20 × 100, Automático, Longitud completa: M20x2.5 6g): la previa congelaba la ventana 25,3 s; Fusion la muestra al instante (`evidencias/reportes_pc/2026-11-12_rosca_modelada/`). Ya no congela (2026-11-12, E6): la previa de la Rosca modelada va al proceso aparte (`ui/comando.py` › `_previa_pesada`) y Aceptar ya iba aparte; ventana real en la VPS (`xvfb-run`, reloj de 50 ms): congelada 31-45 s → 0,4-0,8 s (recibir la malla), Aceptar sin cortes. La causa de los 25 s: dentro de la ventana la previa corre en serie (B-293) y la rosca tarda 26 s; en paralelo, 7,8 s. Queda: la rosca misma (M20 6g: 0,5 s con 10 mm, 0,8 s con 30 mm, 7,9 s con 100 mm; Fusion ~0,05 s) y los reintentos de `_cortar_helicoidal` que fallan (ver B-369; B-371 se cerró el 2026-11-13). Ideas (Gerardo, 2026-11-12, «Fusion es mil veces más rápido»): mientras se arrastra o se cambia el tamaño, previa liviana (rosca cosmética o malla de la hélice) y el sólido real recién al soltar o Aceptar; y calcular el sólido fuera del hilo de la ventana (como B-337). · **Evidencia:** `evidencias/fusion_2026-11-10/rosca_fusion_vs_omnicad_2026-11-10.md`, `rosca_omnicad.txt` y `rosca_fusion.txt`; `evidencias/fusion_2026-11-08/` (medir_roscas, omni_casos); `nucleo/solidos_crear.py:2919` › `_cortar_helicoidal`

### P-61 · Las ventanas minimizadas de prueba pueden verse o tomar el foco

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Las ventanas «minimizadas» de prueba todavía pueden tomar el foco o verse un instante · **Queda:** Medir con el monitor de cursor y foco (`GetForegroundWindow` cada 100 ms) las piezas de `scripts/prueba_ui` en minimizada: `arnes.activar` llama `QApplication.setActiveWindow`, que en el humo tomaba el foco de Windows (2 veces por corrida, a los 27 y 29 s; sin esa llamada, 0 en 5 corridas). Cuidar las piezas que prueban atajos. Además, en 1 de 7 corridas del humo una ventana «OmniCAD» se vio opaca menos de 100 ms cerca de `_editar_boceto` (sin foco). · **Evidencia:** scripts/prueba_ui/arnes.py (`activar`); clon/omnicad/prueba_humo.py (`_editar_boceto`)

### P-40 · Extruir empieza en 10 mm y Fusion en 0 mm

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Extruir arranca en 10 mm; Fusion arranca en 0 mm y se arrastra la flecha · **Queda:** Video 2026-10-28 11-28-09: en Fusion la distancia empieza en 0,00 mm y el cuerpo aparece al arrastrar; en OmniCAD entra con 10 mm y ya se ve un cuerpo. Es una decisión de producto de Gerardo: replicar Fusion o dejar el cuerpo de entrada. · **Evidencia:** omnicad/ui/comandos/solido.py (`Extruir`, valor inicial de la distancia)

### P-35 · El volumen exacto de cuerpos B-spline cuesta 0,5 s por llamada

- **Historia (movida de la fila, 2026-11-13):** **Qué:** `volumen_exacto` de un cuerpo con 500 caras B-spline cuesta 0,5 s por llamada · **Queda:** `aplicar_resultado` lo llama tres veces en una unión (resultado, cuerpo y herramienta): 1,4 s de los 3 s de Unir en `bspline500`. Guardar el volumen por forma en el cuerpo (se invalida al cambiar `forma`) o no medirlo cuando no hay aviso posible. · **Evidencia:** omnicad/timeline/operaciones.py (`aplicar_resultado`), omnicad/nucleo/geometria.py (`_integral`); scripts/bench_booleana.py bspline500

### P-36 · BRepCheck omite caras con más de 200 contornos

- **Historia (movida de la fila, 2026-11-13):** **Qué:** B-39 no revisa con BRepCheck las caras cambiadas con más de 200 contornos · **Queda:** `_es_valida_tras_booleana` las salta porque BRepCheck clasifica los contornos de a pares (3000 agujeros: 11 s); el volumen y las aristas libres siguen vigentes. Revisar solo los contornos nuevos de esa cara (hoy la booleana rearma todos los contornos y no se distinguen por forma). · **Evidencia:** omnicad/nucleo/geometria.py (`_es_valida_tras_booleana`, `_MAX_CONTORNOS_REVISADOS`)

### P-33 · CI de main con ruff y pytest rápido en cada push

- **Historia (movida de la fila, 2026-11-13):** **Qué:** CI en GitHub para main: ruff y pytest rápido en cada push (sin la prueba de humo, que pide ventana) · **Queda:** Todo. AGENTS.md (Seguridad) ya exige «subir solo con la CI verde» pero no hay workflow: solo `instaladores.yml`, por tag. Puede pedir ajustar tests que necesitan OpenGL en la máquina de GitHub. Pendiente por decisión de Gerardo (2026-10-25). · **Evidencia:** .github/workflows/ (solo instaladores.yml); AGENTS.md:50

### P-10b-d · Fase 1: Rust y Zstandard con instalador

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Fase 1: andamiaje Rust + R1 (Zstandard) de punta a punta con el instalador · **Queda:** Mover el descompresor zstd_puro a Rust y probar empaquetado .pyd en PyInstaller e instalador. · **Evidencia:** omnicad/io_archivos/zstd_puro.py sigue en Python puro; clon/rust/src/lib.rs sin zstd

### P-10b-j · Bajar el dibujo Qt del boceto (11 ms con 10 000 puntos al mover la cámara)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Bajar el dibujo Qt del boceto (11 ms con 10 000 puntos al mover la cámara) · **Queda:** La meta < 5 ms del repintado completo no se cumple. · **Evidencia:** PROJECT_LOG.md:341 (proyectar 64,6 a 13,9 ms; Qt suma 11,5 ms)

### P-32 · Probar omnikernel ante uniones casi tangentes

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Probar el motor omnikernel (Rust) como segunda opinión en uniones casi tangentes · **Queda:** Tras reparar la revisión de B-39, una nueva corrida de 4 000 casos con controles geométricos completos deja 1 caso señalado (0,025 %): b39-1414, con una arista no manifold nueva, cuerpo estanco y válido. La cifra previa de 0,05 % usaba un validador que omitía controles geométricos y no sirve como comparación de validez. Plan: (1) comparar el caso 1414 y el fuzzer con omnikernel, sin cambiar los chequeos ni las semillas; (2) si resuelve el resto sin perder material, usarlo solo como último reintento de `geo.booleano`, convirtiendo la salida a B-rep OpenCascade; (3) si no lo resuelve, anotarlo en `docs/comparacion_motores.md` y mantener el error claro. Un contacto tangente exacto puede no tener cura en ningún kernel. · **Evidencia:** nucleo/geometria.py (`booleano`, `_REINTENTOS_BOOLEANA`); scripts/fuzz_b39.py; tests/test_b39_revision.py; nucleo/omnikernel/; docs/comparacion_motores.md

### P-10b-f · Fase 3: boceto en Rust (R5, solver R4, R9)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Fase 3: boceto en Rust (R5, solver R4, R9) · **Queda:** El solver sigue en scipy; con la colocación constructiva (SC4) 400 líneas arrastran en 258 ms, medir antes de pasar a Rust. · **Evidencia:** omnicad/restricciones/solver.py (least_squares method=lm); clon/rust sin módulo de boceto

### P-9j · Auditar pantallas: estados vacíos, errores e identidad visual

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Revisión crítica de cada pantalla (estados vacíos y de error, textos) con capturas · **Queda:** Solo 13 pantallas auditadas; faltan estados vacíos/errores y el objetivo de identidad visual propia. · **Evidencia:** scripts/capturas_ui.py; evidencias/capturas/p9b_antes y p9b_despues (13 pantallas cada una)

### P-22d · Verificar tablas ISO 965/273 y reglas de chapa contra la norma

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Verificar tablas ISO 965/273 y reglas de chapa contra la norma · **Queda:** ISO 965-1 solo verificada para M3-M39; falta ISO 273 y K-factor de chapa. · **Evidencia:** omnicad/nucleo/tolerancias.py:10,163-200; commit 992b93c

### P-10b-c · Fase 5: previa asíncrona, memo por paso y firmas

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Fase 5: P6, P7, P8, P9, P13 (previa asíncrona, memo por paso, firmas) · **Queda:** P6 completo (vista previa en un proceso aparte) y deshacer serializado en un hilo siguen abiertos. · **Evidencia:** omnicad/timeline/documento.py (_de_memo, _aplicar_memo); omnicad/nucleo/referencias.py:198 _firmas; omnicad/io_archivos/proyecto.py autoguardar_en_hilo

### P-10b-h · Trabajador Python para teselado y HLR cancelables en paralelo

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Proceso trabajador en Python: teselado y HLR en paralelo, cancelables · **Queda:** Solo autointersecciones y HLR exacto corren aisladas con tope; falta el pool para teselado y vistas. · **Evidencia:** omnicad/nucleo/aislado.py (subproceso con tope de tiempo); tests/test_b48_crash.py

### P-10f · Paso 6: Rust con PyO3 solo si los números lo justifican

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Paso 6: Rust con PyO3 solo si los números lo justifican · **Queda:** Hecho R11; el resto de R1-R13 sin empezar (ver filas RS-). · **Evidencia:** clon/rust/src/lib.rs (rasterizar, visibilidad, oclusion); omnicad/nativo.py

### H-98 · Repujado cilíndrico exige marcar «Envolver en la cara»

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Repujado sobre un cilindro exige marcar «Envolver en la cara» · **Queda:** Fusion no tiene esa casilla: envuelve solo sobre una cara curva. OmniCAD da «Sobre una cara cilíndrica el repujado se hace envolviendo (envolver=True)» si no se marca; marcado anda (cuadro 6×6 en un cilindro r 10: +37,80 mm³, la cuenta). · **Evidencia:** nucleo/solidos_crear.py:1573

### H-68 · Parámetros automáticos de cotas y operaciones, con preferencia

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Parámetros automáticos (a futuro): al dibujar un boceto y al aplicar una operación, crear solos los parámetros de sus cotas y valores, con una preferencia para activarlo o desactivarlo · **Queda:** Pedido de Gerardo con «Reportar problema» (registro de uso, sesión 2026-11-03_210154, seq 112). Hoy los parámetros se crean a mano. Copiar cómo nombra Fusion los parámetros de modelo (d1, d2…) antes de construir. · **Evidencia:** timeline/parametros.py

### H-37 · Cobertura de operaciones, interfaz, .fclone y .f3d

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Barrido sin cubrir: interfaz, 51 tipos de operación, .fclone y .f3d · **Queda:** 57 de 116 tipos con caso en tests/test_barrido_tipos.py (2026-11-05). Faltan casos para los otros 59 y cambiar la razón adivinada por nombre (`_razon_pendiente`) por una lista explícita por tipo. · **Evidencia:** tests/test_barrido_tipos.py; tests/test_io.py:93 (.fclone); tests/test_f3d_nativo.py

### P-133 · Biblioteca de roscas en ventana completa con árbol y filtros

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Rosca › biblioteca de roscas como ventana completa (árbol, favoritos, filtros por tamaño, designación, Ø, género y clase, ficha con dibujo) · **Queda:** Hoy es un diálogo chico con tabla. Gerardo (2:40–3:06): «¿POR QUÉ ESTÁ ESTE MENÚ?» · **Evidencia:** `clon/omnicad/ui/comandos/crear.py:535` (BibliotecaRoscas); `evidencias/videos_roscas_2026-11-10/informe.md`; capturas `OmniCAD_3m00_biblioteca_de_roscas_modal.png`, `Fusion_1m44_biblioteca_de_roscas_ventana_completa.png`, `Fusion_6m40_detalle_de_rosca_con_dibujo.png`

### P-134 · Rosca: aceptar y campos según cara; lista de Tamaño en el panel

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Rosca › Aceptar gris y campos en «Automático» hasta elegir la cara; la lista de Tamaño dentro del panel · **Queda:** Fusion (0:33) no deja aceptar sin cara; la lista Tamaño de OmniCAD sale a pantalla completa (3:12) · **Evidencia:** `clon/omnicad/ui/comandos/crear.py:893`; `evidencias/videos_roscas_2026-11-10/informe.md`; captura `Fusion_0m33_dialogo_vacio_aceptar_gris.png`

### P-135 · Rosca parcial: asas de Longitud y Desfase en el visor

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Rosca parcial › tramo y cotas en el visor para arrastrar el largo y el desfase · **Queda:** HECHO 2026-11-12 (E1): sin «Longitud completa» salen las dos flechas sobre la pared que se ve (`FlechaCilindro`, `ui/manipuladores.py`; `_asas_rosca`, `ui/comandos/asas_extra.py`): Desfase en el borde de arriba del tramo y Longitud en el de abajo, corrida 25° a la derecha como en Fusion; las dos se arrastran y la Longitud sigue al Desfase. Las de antes iban por el eje (se dibujaban encima del cuerpo, en el centro), no sobre la pared como Fusion. «Desfase» salió de «Más opciones» y quedó arriba de Longitud, como en Fusion. Test: `tests/test_p135_asas_rosca.py`. FALTA: que Gerardo apruebe la captura `evidencias/p135_2026-11-12/p135_fusion_vs_omnicad.png` (diferencia: flechas amarillas largas con caja de valor, el estilo de todas las asas de OmniCAD; en Fusion son grises y cortas). Antes: Fusion (0:56–1:30) muestra el tramo azul con flechas y cota; en OmniCAD «Desfase de inicio» está dentro de «Más opciones» PRIORIDAD 1 (Gerardo, 2026-11-12): al destildar «Longitud completa» Fusion muestra dos flechas sobre el cuerpo, en el borde de arriba de la rosca (Desfase 29.573 mm) y en el de abajo (Longitud 41.50 mm); se arrastran y la rosca se ve solo en ese tramo. OmniCAD no tiene ninguna asa en Rosca. `evidencias/reportes_pc/2026-11-12_rosca_modelada/` (Fusion 0:20-0:40, `fusion_rosca_parcial_M45.jpg`). Cambiar/agregar el dibujo, no reusar uno viejo; terminado = captura al lado de la de Fusion aprobada por Gerardo. · **Evidencia:** `clon/omnicad/ui/comandos/crear.py` (Rosca); `evidencias/videos_roscas_2026-11-10/informe.md`; captura `Fusion_0m56_longitud_parcial_desfase_y_longitud.png`

### P-139 · Anillos de ángulo como Fusion en las herramientas

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Extruir › el ángulo de conicidad es un asa suelta en la esquina del perfil; en Fusion es un anillo punteado centrado en la flecha de distancia, con el asa sobre el anillo y la caja «−37.0 deg» al lado · **Queda:** Aprobado por Gerardo con captura (2026-11-12) en Extruir, la torsión del Barrido y Revolución: `AnilloAngulo` en `ui/manipuladores.py` (`evidencias/p139_2026-11-12/p139_extruir_barrido_revolucion.png`). Mover/copiar pasado el 2026-11-13 (P-139m, E3: un anillo por eje en el centro de la tríada; `evidencias/p139_2026-11-12/p139m_mover_copiar_fusion_vs_omnicad.png`, falta que Gerardo la apruebe). Plano en ángulo pasado el 2026-11-13 (P-139p, E5; `evidencias/fusion_capturas_2026-11-12/4c` y `4d`). Inclinación (Modificar › Desmoldeo) pasado el 2026-11-13 (P-139i, E5; `evidencias/p139i_2026-11-13/p139i_ayuda_fusion_vs_omnicad.png`). Queda: que Gerardo apruebe las capturas de Mover/copiar e Inclinación (con eso la fila se borra); el «⋮» de la caja va con P-144 · **Evidencia:** `tests/test_manipuladores.py::test_p139_la_conicidad_de_extruir_es_un_anillo_en_el_pie_de_la_flecha`; `tests/test_manipuladores.py::test_p139_la_inclinacion_es_un_anillo_sobre_la_linea_neutra`; `evidencias/reportes_pc/2026-11-12_gizmo_angulo_fusion/` (PC de Gerardo)

### P-143 · Empalme: flecha del radio y marcador «◁▷» como Fusion

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Empalme › el asa del radio está en el MEDIO de la arista con flecha amarilla hacia abajo; en Fusion es una flecha azul en la punta de la arista, sobre la cara del extremo, con el marcador «◁▷» sobre el cuerpo · **Queda:** Queda: que Gerardo apruebe la captura `evidencias/p143_2026-11-12/p143_fusion_vs_omnicad.png` (Fusion a la izquierda, OmniCAD a la derecha), el marcador «◁▷» de Fusion, que se queda en el medio de la PRIMERA arista elegida (no se sabe qué hace: mirarlo en Fusion antes de copiarlo); la caja del valor aparte va con P-144. Hecho 2026-11-12 (E3): flecha-puntero azul nueva (`FlechaPuntero`, `ui/manipuladores.py`) que señala el punto del empalme y apunta hacia donde crece; la usan empalme, chaflán y pulsar/tirar sobre una arista. P-143b: va en la ÚLTIMA arista elegida (salta a cada una nueva, video de Fusion 2,9-6,5 s), en el punto donde se hizo clic, y sin clic (al editar, la API) en el medio, como las capturas de Fusion 1a y 1b; comparación en `evidencias/p143_2026-11-12/p143b_clic_fusion_vs_omnicad.png` · **Evidencia:** `evidencias/reportes_pc/2026-11-12_empalme_4_aristas/` (video 47 s: Fusion 0-22 s, OmniCAD 24-45 s; capturas y registro de uso), PC de Gerardo

### P-147 · Solevación: asas de Ángulo y Peso de despegue

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Solevación › con un perfil en «Dirección» faltan las asas: Fusion muestra sobre el perfil un anillo punteado con su punto (Ángulo de despegue) y una flecha (Peso de despegue) que se arrastran; OmniCAD solo tiene los campos · **Queda:** Queda: que Gerardo apruebe la captura `evidencias/p147_2026-11-12/p147d_convencion_fusion_vs_omnicad.png`. P-147d (2026-11-13): el Ángulo de despegue se mide como en Fusion, desde la normal (0° = perpendicular, por defecto), en el núcleo, la API, el panel y el anillo; una receta vieja (sin `version_angulo`) se pasa a 90 − ángulo al abrirla. Hecho 2026-11-12 (E3): el anillo del Ángulo de despegue (`AnilloAngulo` de P-139) centrado en el perfil y de canto a él, sin tope (da vueltas: el núcleo y la API lo toman módulo 360, −330° = 30°), y la flecha del Peso nace en el centro con peso 1, así el asa del ángulo queda en su punta, como Fusion `3a`/`3b` (P-147c); y la flecha del Peso de despegue sobre cada perfil en «Dirección» (`_asas_solevacion`, `ui/comandos/asas_extra.py`): sale del centro del perfil en el sentido de la solevación y se corre como la sección auxiliar del núcleo; solo la del perfil elegido, como Fusion. Peso 3,6 con 15°: OmniCAD también avisa («el sólido se autointersecta; la dirección del flujo de la solevación no es válida…»). Captura: `evidencias/p147_2026-11-12/p147_fusion_vs_omnicad.png` · **Evidencia:** Reporte de la PC: `evidencias/reportes_pc/2026-11-12_solevacion/` (`fusion_asas_direccion.jpg`, `omnicad_direccion_sin_asas.jpg`, video 4:20)

### P-154 · Cambiar Lados de un polígono ya dibujado

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Polígono: cambiar Lados después de dibujarlo no hace nada (Gerardo lo esperaba). Pedido: con el polígono recién dibujado, y mejor también al editarlo después, Lados en la tarjeta o en el campo vivo lo rehace con el mismo centro, radio, giro y tipo, conservando las cotas y restricciones que se puedan · **Queda:** Hecho para lo recién dibujado (E1, 2026-11-13): `Lienzo.cambiar_lados` / `rehacer_figura` rehacen el polígono (y la estrella, BOC-84) con el mismo círculo guía, así su cota sigue; un paso de deshacer; otra herramienta lo corta. Fusion no lo hace (su ayuda «Create polygons»: los lados se escriben antes del clic que lo ubica). Queda: rehacer un polígono ya terminado (elegirlo y cambiar Lados), que pide reconocerlo por sus restricciones · **Evidencia:** `clon/tests/test_boc84_estrella.py`; pieza `boceto_herramientas` (sección «Estrella y Lados»)


### P-150 · Empalme y chaflán: aristas elegidas sin previa gruesas y sin profundidad

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Empalme y chaflán › las aristas elegidas se dibujan como líneas azules gruesas por encima de todo (también las ocultas, que cruzan el cuerpo) y siguen donde estaba la arista viva cuando la previa ya redondeó, así que quedan flotando fuera del sólido; en Fusion son finas, van pegadas a la arista y el cuerpo las tapa · **Queda:** Hecho: mientras hay previa, Empalme (modo Empalme) y Chaflán ya no dibujan las aristas elegidas (`oculta_seleccion`, como Fusion: la previa se las come). Falta: sin previa (radio 0) siguen gruesas (3,5 px, `elegir_entidad` en `ui/visor3d.py`, igual para todos los comandos) y sin profundidad; decidir si se afinan para todos; la captura con previa la aprobó Gerardo el 2026-11-13 · **Evidencia:** `evidencias/p150_2026-11-13/p150_empalme_fusion_vs_omnicad.png` y `p150_chaflan_omnicad.png`; test `test_p150_la_previa_se_come_las_aristas_elegidas` (`tests/test_manipuladores.py`)

### FU-3 · Cota de ángulo contra el eje X y barrido del arco

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Cota de ángulo contra el eje X y barrido del arco · **Queda:** HECHO 2026-11-13 (E1): la primera línea con ángulo escrito (que no es 0° ni 90°) queda con cota de ángulo contra el eje X (`_cotas_de_lo_escrito`, `ui/editor_boceto.py`; test `tests/test_boceto_interaccion.py::test_fu3_primera_linea_con_angulo_escrito_se_acota_contra_el_eje_x`; captura `evidencias/fu3_2026-11-13/fu3_linea_30.png`). FALTA: el barrido escrito del arco de punto central no deja cota. La ayuda de Fusion solo dice que las cotas agregadas quedan en el lienzo, y su API no tiene cota de ángulo de arco: hay que ver en Fusion en vivo qué cota deja antes de hacerla. · **Evidencia:** ui/editor_boceto.py (`_cotas_de_lo_escrito`, rama `arco_centro`)

### F4 · Referencias perdidas: reparar al editar un paso temprano

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Referencias perdidas: reparar al editar un paso temprano · **Queda:** Reelegir en el acto la referencia perdida desde el panel del paso · **Evidencia:** nucleo/referencias.py (firmas geométricas); timeline/entidades.py:196; api/errores.py:208 REFERENCE_LOST; tests/test_comandos.py::test_referencias_de_aristas_sobreviven_a_un_cambio_de_cota; tests/test_hallazgos_tortura.py::test_t03_el_chaflan_del_borde_tras_un_vaciado_sobrevive_a_un_cambio_de_cota_del_29_por_ciento

### F5 · Diagnóstico del boceto: restricciones en conflicto y redundantes

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Diagnóstico del boceto: restricciones en conflicto y redundantes · **Queda:** Hecho (2026-10-31): `aplicar_restriccion` rechaza la que no quita ningún grado de libertad, F5 «Qué choca» dice cuáles sobran y las deja elegidas (Supr las borra) y `find_redundant_constraints` las lista. Queda: mostrarlas sin pedir F5 (borde naranja en el símbolo y aviso en la paleta); cuesta un cálculo de rango por vínculo (4,7 ms con 8 restricciones, 240 ms con 83: no se corre en cada cambio) y tiene tope de 150 vínculos (`TOPE_REDUNDANTES`). · **Evidencia:** restricciones/solver.py (`restricciones_redundantes`); ui/editor_boceto.py (`texto_redundantes`); tests/test_restricciones_ui.py::test_f5_dice_que_sobra_y_lo_deja_elegido

### F12 · Herramientas de B-spline

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Herramientas de B-spline · **Queda:** Insertar nudo, subir/bajar grado, unir curvas y convertir a B-spline como herramientas · **Evidencia:** restricciones/boceto.py:198-207 (spline por control, grado 3 o 5, pesos y nudos), :486 _insertar_nudo interno; ui/editor_boceto.py:2654 (marco de control); ui/modo_boceto.py:90

### PL1 · Un comando contextual según lo elegido (Desfase, Unir, Extender…)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Un comando contextual según lo elegido (Desfase, Unir, Extender…) · **Queda:** Unir, Invertir, Extender, Reconstruir, Alinear e Imprimir siguen como botones propios · **Evidencia:** 22c252d; ui/comandos/modificar.py:757 (Desfase); api offset_faces, offset_edges; tests/test_pl1_desfase.py

### RH13 · Análisis ampliado: continuidad, desviación, normales visibles

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Análisis ampliado: continuidad, desviación, normales visibles · **Queda:** Continuidad por borde G0/G1/G2, desviación entre curvas o puntos y normales visibles · **Evidencia:** 4fca4c7 (aristas abiertas, no manifold y espesor); nucleo/revision.py; api check_geometry, check_printability; tests/test_revision.py

### RH18 · Curvas desde superficies y cuerpos (isocurvas, contorno, silueta)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Curvas desde superficies y cuerpos (isocurvas, contorno, silueta) · **Queda:** Hechas la curva isoparamétrica (`isoparametric_curve`) y la silueta (Proyectar un cuerpo, B-119, 2026-11-05). Queda el contorno por cortes paralelos (`Contour`) y tirar (`Pull`) como curvas de boceto · **Evidencia:** api/herramientas_boceto.py:1581 project_to_sketch (proyectar e intersecar aristas, caras y cuerpos; un cuerpo da su silueta); sin Contour

### RH12 · Gumball al elegir e imanes en el visor

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Gumball al elegir e imanes en el visor · **Queda:** Manipulador contextual al elegir (flechas de mover/extruir/escalar) y barra de imanes con seguimiento · **Evidencia:** ui/manipuladores.py (manipuladores dentro de cada comando); ui/comandos/modificar.py PulsarTirar; ui/sugerencias.py:30 (tira de comandos); mismo trabajo que B7

### P-76 · Boceto y texto extruible sobre caras curvas

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Boceto directo sobre una cara curva (cilindro, cono) y texto envuelto que se extruye desde ahí · **Queda:** Idea del video de PhyCAD (YouTube YKVOVaaIY48, 04:06) que pidió Gerardo el 2026-11-08: elegir una cara curva como plano del boceto y dibujar o escribir texto sobre ella. Fusion no lo hace (obliga a un plano tangente más Proyectar o Repujado). Va aparte de las auditorías: es una función nueva del boceto, después de la auditoría de CREAR/MODIFICAR. Base: Proyectar a superficie (H-109) y Repujado envuelto (H-98). · **Evidencia:** video PhyCAD 04:06

### BOC-80 · Verificar las ayudas del boceto 3D contra Fusion real

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Boceto 3D: las ayudas enganchan en el espacio sin comparar con Fusion real · **Queda:** La API de Fusion no expone el forzado del cursor: el script no llega y falta mirarlo a mano. La ayuda solo dice que la tríada es un plano temporal. Se siguió la fila de auditoría («Fusion engancha en el espacio»): medio, cruce real, pie, contacto tangente y sobre la curva son puntos 3D; alineaciones y horizontal/vertical siguen en el plano activo. Falta ver qué hace con dos líneas que solo se cruzan en pantalla y con la tangente desde un punto fuera del plano del círculo. · **Evidencia:** `omnicad/restricciones/inferencia3d.py` (`_en_espacio`); `tests/test_inferencia3d.py::test_desde_fuera_del_plano_del_circulo_no_hay_tangente_real_y_no_queda_restriccion`

### BOC-49 · Acelerar el rearmado del índice de ayudas con miles de entidades

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Con miles de entidades, rearmar el índice de ayudas tras un cambio cuesta decenas de milisegundos · **Queda:** Hecho 2026-11-13 (E10): `Indice(b, previo)` reusa la caja y el punto medio de las curvas que no cambiaron. Medido con 2000 líneas y 1 cambio: 18-44 ms → 11-24 ms por rearmado (−40 %, medido en una VPS con otras corridas). Queda: el resto (dueños de puntos, lista de referencias y arrays, ~11 ms) sigue siendo Python; pasarlo a Rust o vectorizarlo solo si pesa en la práctica. Ojo: el índice es perezoso, se arma una vez en el primer movimiento del ratón tras cada cambio, no en cada paso de un arrastre · **Evidencia:** `clon/tests/test_boc49_indice_incremental.py`; `clon/omnicad/restricciones/inferencia.py` (`Indice.__init__`)

### PAT-1 · Extensión simétrica con cantidad par sin medir en Fusion real

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Extensión simétrica con cantidad par sin medir en Fusion real · **Queda:** Hecho: receta nueva con la tabla medida (`version_simetria`, los documentos viejos abren igual). Queda medir en Fusion n par en Extensión: OmniCAD deja la última copia en +medida, paso = medida / (n // 2); Fusion solo se midió con 3 en 100. El patrón en ruta sigue con n a cada lado: tampoco se midió. · **Evidencia:** tests/test_patrones_solidos_semantica.py::test_rectangular_simetrico_en_extension_mide_por_lado; ::test_circular_simetrico_el_angulo_es_el_total_y_la_de_mas_va_al_lado_negativo

### UI-2 · El escalado real de Windows (125 % y 150 %) y los monitores nuevos no se probaron

- **Historia (movida de la fila, 2026-11-13):** **Qué:** El escalado real de Windows (125 % y 150 %) y los monitores nuevos no se probaron · **Queda:** Se simuló con letra al 125/150 % y ventanas de 1024×640 y 800×520. Falta correr `paneles_inventario.py` y `paneles_temas.py` con la pantalla en 125 % y 150 % y moviendo la ventana de un monitor a otro · **Evidencia:** scripts/prueba_ui/paneles_temas.py

### UI-6 · Comparar las agrupaciones de opciones con la ayuda de Fusion

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Las agrupaciones de opciones de cada comando no se compararon una por una con la ayuda de Fusion · **Queda:** Los agentes miraron la ayuda de Fusion cuando dudaron (p. ej. Bobina); no hay una matriz comando por comando de qué opciones agrupa Fusion y cuáles son «avanzadas» allá · **Evidencia:** docs/auditorias/ui_paneles_2026-10-31.md

### P-132 · Distinguir caras planas inclinadas al elegirlas

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Selección › una cara plana inclinada (normal fuera de los ejes) se nombra «Cara plana · Cuerpo1», sin rasgo que la distinga de otra cara plana del mismo cuerpo · **Queda:** Darle un rasgo corto en `ui/formulario.py` › `describir_ref` (p. ej. el ángulo o el área) que entre en el botón · **Evidencia:** Pendiente que dejó B-282 (la cara en eje ya dice «Cara +X · Cuerpo1»): informe de la sesión Construir, 2026-11-10

### SC20 · Mostrar mallas provisionales al abrir mientras se recalcula

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Abrir un proyecto mostrando enseguida una imagen provisional desde una caché de mallas, mientras se recalcula · **Queda:** SolidCraft guarda mallas ya teseladas en una caché del archivo y las muestra al abrir mientras reconstruye; la caché nunca reemplaza el diseño. Acá solo se guarda `cache/pasos.json` (`io_archivos/proyecto.py:85`): al abrir hay que esperar el recálculo (BINCHA.f3d tarda 23 s). Atar al tamaño del archivo y a la versión del núcleo para que no muestre algo viejo. · **Evidencia:** omnicad/io_archivos/proyecto.py:85 (la caché no guarda mallas)

### P-11n · .f3d: lector SAB y escena en Rust (Zstandard ya está)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** .f3d: lector SAB y escena en Rust (Zstandard ya está) · **Queda:** Hecho 2026-10-31: Zstandard en Rust (`rust/src/zstd.rs`, crate `ruzstd`; RS-R1, `tests/test_zstd_rust.py`): el bloque de BINCHA baja de 6,9 s a 0,09 s y el archivo de 21,7 s a 9,6 s (PC compartida). Falta: el lector SAB (3,0 s) y la escena (≈ 3 s) como datos puros en un módulo PyO3 (obliga a adaptar `acis_occ.convertir` a columnas). Objetivo: BINCHA ≤ 6 s. · **Evidencia:** omnicad/io_archivos/sab.py; omnicad/io_archivos/f3d_escena.py; docs/f3d_formato.md; docs/auditorias/rust-pipeline-2026-10-31.md

### P-11o · .f3d: mallas convertidas grandes entran sin reparar

- **Historia (movida de la fila, 2026-11-13):** **Qué:** .f3d: mallas convertidas grandes entran sin reparar · **Queda:** Un cuerpo abierto de más de 2000 caras no pasa por ShapeFix (con 18 716 caras tardaba 247 s): entra como superficie y una parte queda con caras inválidas (338 de 3 516 en BINCHA). Habría que repararlo por partes o en Rust, solo si el usuario lo muestra. · **Evidencia:** omnicad/nucleo/acis_occ.py (CARAS_SIN_ARREGLO); tests/test_f3d_nativo.py::test_una_malla_abierta_enorme_no_pasa_por_shapefix

### P-96 · SVG: rellenos casi transparentes de Affinity dejan pestañas

- **Historia (movida de la fila, 2026-11-13):** **Qué:** SVG › los rellenos casi transparentes que deja Affinity (opacidad 4–13 %) entran como geometría y dejan pestañas sobre el borde · **Queda:** «LAS VALIENTES 1.svg» trae 24 recortes de `fill-opacity` 0,04–0,13 pegados al contorno exterior: en Affinity no se ven, en OmniCAD salen como pestañas y ondas. Ignorar al importar los rellenos con opacidad menor a un umbral (p. ej. 0,15), con aviso que diga cuántos se saltearon y una opción para traerlos. Mirar qué hace Fusion con `fill-opacity` en Insertar SVG · **Evidencia:** `evidencias/svg_valientes_2026-11-08/` (`valientes.svg`, `repro.py`)

### FL-0 · F0 banco de fluidez y detección de bloqueos UI mayores de 1 s

- **Historia (movida de la fila, 2026-11-13):** **Qué:** F0 banco de fluidez: `scripts/bench_fluidez.py` (11 escenarios como usuario) + `tests/test_fluidez.py`; prueba_ui falla con un `bloqueo_ui` de más de 1 s; filtrar los falsos de «abrir» y «preferencias» · **Queda:** Sin empezar. Listo cuando la tabla hoy/meta de los 11 escenarios está commiteada y el test corre con turno (E7; revisa E6). · **Evidencia:** docs/plan_fluidez.md

### FL-2 · F2 previa barata inmediata al teclear y arrastrar

- **Historia (movida de la fila, 2026-11-13):** **Qué:** F2 previa barata inmediata también al teclear y con las flechas (prisma, Cortar en rojo, revolución, rosca cosmética) · **Queda:** Sin empezar; va después de FL-1. Listo cuando en a y b la primera previa sale en menos de 50 ms y Aceptar usa la forma exacta (E2 crear, E3 Cortar). · **Evidencia:** docs/plan_fluidez.md

### FL-3 · F3 aceptar, editar, deshacer y abrir fuera de la ventana

- **Historia (movida de la fila, 2026-11-13):** **Qué:** F3 Aceptar, eliminar/editar paso, deshacer/rehacer y abrir fuera de la ventana, con barra y Cancelar · **Hecho 2026-11-14 (E6):** Abrir (menú, Recientes y arranque) arma el proyecto en otro hilo con una barra modal y Cancelar/Esc, que deja el documento de antes; un proyecto chico sin caché válida (guardado con otra versión) también se recalcula en el proceso aparte (`motor_cohete`, 41 pasos, recalculaba 5,5 s en la ventana); las mallas se hacen en el hilo y entran a la caché del visor (`datos_cuerpo`/`precargar`). Banco FL-0, bloqueo máximo antes → ahora: g 165 → 135 ms, h 3660 → 188 ms, l `motor_impreso` 57 534 → 212 ms, m `motor_cohete` 12 492 → 163 ms, n `gatoRL` 66 583 → 470 ms, o `ABANICO EMILIA` 3735 → 1441 ms. **Hecho 2026-11-14 (E6, FL-3b):** Aceptar, editar, deshacer y rehacer: si el cálculo va al proceso aparte, `Documento` lanza `CalculoDiferido` antes de tocar nada, la ventana lo calcula en otro hilo (`_cambio_aparte`) con la barra «Calculando en un proceso aparte…» y Cancelar/Esc (el documento queda como estaba), reconoce los cuerpos que no cambiaron y malla los demás en ese hilo, y repite el cambio, que adopta lo calculado (`_precalculo`). Al Aceptar un paso nuevo al final se reusa la malla de su previa (el filete de una M20 × 60 tardaba 2,15 s en una sola llamada que retiene el GIL). Cerrar la barra emitía `canceled` y cerraba el trabajador vivo: cada cálculo siguiente rehacía `motor_impreso` (Deshacer 59 s); también en Abrir. Banco FL-0 (bloqueo máximo, mediana de 3, VPS cargada) antes → ahora: s (Aceptar, deshacer y rehacer, 20 pasos) 508 → 195 ms; t (lo mismo en `motor_impreso`) 4389 → 117 ms, con Aceptar 4504 → 371 ms, Deshacer 2331 → 374 ms y Rehacer 1861 → 440 ms en total; b Rosca 2028 → 210 ms; e 1646 → 102 ms; h 290 → 246 ms. La previa de la Rosca (16 ms) y el autoguardado (85 ms, no guarda la caché B-Rep) no traban en Linux. **Queda:** verlo en Windows con E11 (fila en la lista nocturna: la traba de 350-670 ms de la previa de la Rosca y la de 1430 ms del autoguardado no se reproducen acá); o y n por encima de 250 ms (la barra cierra y el documento se aplica en la ventana). Listo cuando g y h bloquean menos de 250 ms y Cancelar deja el documento igual (E6). Cubre CPP-F1, CPP-C4 y RS-X2. Suma los ~4 s de los `bloqueo_ui panel_datos` del registro: son abrir el documento (mallar y dibujar los 11 cuerpos del STEP), no el panel (FL-8). · **Evidencia:** docs/plan_fluidez.md

### FL-4 · F4 Unir y Cortar solo contra los cuerpos que tocan (filtro por caja envolvente)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** F4 Unir y Cortar solo contra los cuerpos que tocan (filtro por caja envolvente) · **Queda:** Sin empezar. Listo cuando el escenario a por API tarda lo mismo con 1 que con 11 cuerpos (±20 %) y da el mismo resultado. · **Evidencia:** docs/plan_fluidez.md

### FL-5 · F5 el costo de una operación local crece con el largo del documento

- **Historia (movida de la fila, 2026-11-13):** **Qué:** F5 el costo de una operación local crece con el largo del documento · **Queda:** Sin empezar. Medir primero con documentos de 10, 40 y 80 pasos; listo cuando no sube más de 20 % (E6). · **Evidencia:** docs/plan_fluidez.md

### FL-8 · F8 congelamientos ajenos a la geometría

- **Historia (movida de la fila, 2026-11-13):** **Qué:** F8 congelamientos que no son geometría: preferencias, asistente, sección, `panel_datos` y arranque de las herramientas de boceto · **Queda:** Herramientas de boceto hechas (E1, FL-8b): el 2,6 y 3,3 s era cargar scipy en el primer boceto que se cierra; ahora se carga en un hilo al abrir (`tests/test_fl8b_precarga_scipy.py`). El 4,7 s de `sk_terminar` es el recálculo del timeline (F3). Preferencias hecho (E8, FL-8a): la vista previa de Tema, Apariencia, Gráficos y Asas se repinta una vez por tanda (150 ms) y cada control responde en menos de 9 ms (antes 0,6-1 s los de tema, fuente y tamaño; `tests/test_fl8_previa_preferencias.py`); lo que queda es el repintado único de la aplicación, 0,25-0,8 s por `app.setStyleSheet` (560 widgets). Asistente: son los mismos 83 `bloqueo_ui` de B-331. Queda: sección (E6: el 80 % del 1,1 s es `malla._orejas`, el recorte de orejas en Python con 40 agujeros; hace falta triangular más rápido, p. ej. incremental o en Rust) y `panel_datos` (no se reproduce: medido en la PC con los datos reales de Gerardo, `recargar()` tarda 18-19 ms; los `bloqueo_ui panel_datos` son abrir el documento —mallar y dibujar los 11 cuerpos del STEP— atribuidos a la última acción; esos ~4 s pasan a FL-3) (`recargar` tarda 17 ms con 10 recientes en la VPS: no se reproduce; sospecha: E/S lenta de la PC de Gerardo, sin evidencia). Listo cuando ninguno está entre los diez peores del registro y el escenario i queda bajo 100 ms. · **Evidencia:** docs/plan_fluidez.md

### FL-9 · F9 trabajador precalentado; segundo solo con 8 GB libres

- **Historia (movida de la fila, 2026-11-13):** **Qué:** F9 trabajador precalentado durante la portada; segundo trabajador solo con 8 GB libres (CPP-C3) · **Queda:** Sin empezar; los huérfanos son B-396. Listo cuando la primera previa tarda lo mismo que la segunda (±20 %) (E6). · **Evidencia:** docs/plan_fluidez.md
- **Historia (movida de la fila, 2026-11-14):** Hecho 2026-11-13 (E6): el trabajador se abre en la portada (`OmniCAD.py`) y arma el documento al ponerlo en la ventana (`aislado.precalentar`, tarea `calentar`); `set_documento` ya no lo cierra con un documento chico; el hijo malla con el detalle «Automático» del visor (`render_cpu.deflexion_automatica`). Primera previa de la sesión, main → FL-9 (documento liviano, comando abierto 0,5 s después de la ventana): Extruir 2,0 → 0,44 s (segunda 0,06), Barrido sin guía 2,2 → 0,45 s (segunda 0,21), Barrido con guía 5,2-7,1 → 1,44-1,57 s (segunda 1,40). Esperando 3 s, o con el documento pesado, la primera tarda lo mismo que la segunda. Queda: abrir un comando en el primer segundo paga 0,2-0,4 s de importar el trabajador; el segundo trabajador con 8 GB libres (CPP-C3) no se hizo.

### FL-10 · F10 reusar mallas y extraerlas en bloque (RS-X6, CPP-P20, CPP-C1)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** F10 no volver a mallar lo que no cambió y extraer la malla en bloque (RS-X6, CPP-P20, CPP-C1) · **Queda:** Sin empezar. CPP-C1 pide el OK de Gerardo para bajar cabeceras de OCCT y pybind11 (CPP-F2). · **Evidencia:** docs/plan_fluidez.md

### FL-11 · F11 regla de fluidez y reporte diario de los diez peores bloqueos

- **Historia (movida de la fila, 2026-11-13):** **Qué:** F11 regla permanente en «Definición de terminado» de `AGENTS.md`: ningún comando deja la ventana sin responder más de 250 ms y `test_fluidez` verde; informe diario de la PC con los diez peores · **Queda:** Va cuando exista `test_fluidez` (FL-0). Coordinador. · **Evidencia:** docs/plan_fluidez.md

### RS-R9 · R9 hit-testing del boceto

- **Historia (movida de la fila, 2026-11-13):** **Qué:** R9 hit-testing del boceto · **Queda:** Primero en numpy (RS-X3, hecho el hover el 2026-11-13: 2000 curvas en 3,9 ms con la VPS cargada); Rust solo si con miles de curvas el lote pasa de 2 ms en una máquina sin carga. · **Evidencia:** omnicad/ui/editor_boceto.py

### RS-R3 · R3 BVH: accesibilidad, vaciado, proyección y punto más cercano

- **Historia (movida de la fila, 2026-11-13):** **Qué:** R3 BVH de triángulos (resto: accesibilidad, vaciar, proyección de reducir/remallar, punto más cercano) · **Queda:** Hecho 2026-10-31: `rust/src/bvh.rs` (clase `Bvh`, primer choque por lote, hojas de 4 y partición por la mediana) detrás de `revision.primer_choque` (`espesores`), del hover/elegir del visor (`Visor3D._primer_rayo_cuerpo`) y de `elegir_entidad` de `ui/render.py` (BVH cacheado por cuerpo), con respaldo numpy. Medido (esfera, `scripts/bench_nativo.py rayos`): 2000 rayos a 50 k triángulos 352 → 11,5 ms y a 251 k 2 874 → 51 ms (incluye construir: ≈ 45 ms), un rayo de hover a 251 k 43 → 0,008 ms. Falta: `analisis._rayos_chocan` (accesibilidad; usa otro convenio de bordes, u ≥ 0 sin tolerancia, y cambiaría la salida), `malla.vaciar`, la proyección de `reducir`/`remallar`, punto más cercano, SAH y multihilo con `rayon` (no se agregó: 1 hilo ya está bajo el criterio, 2000 rayos en < 5 ms). · **Evidencia:** omnicad/nucleo/revision.py primer_choque; omnicad/ui/visor3d.py primer_rayo_triangulos; clon/rust/src/bvh.rs; tests/test_bvh_rust.py; docs/auditorias/rust-pipeline-2026-10-31.md

### RS-R5 · R5 geometría de boceto (de Boor, intersecciones) en Rust

- **Historia (movida de la fila, 2026-11-13):** **Qué:** R5 geometría de boceto (de Boor, intersecciones) en Rust · **Queda:** Hecho (B-111): `spline_extremos` (tangente y curvatura en los extremos de una spline de ajuste abierta; el solver la usa con respaldo Python). Falta: splines cerradas o con manijas, `mas_cercano`, intersecciones y cajas. · **Evidencia:** clon/rust/src/spline.rs; omnicad/restricciones/solver.py (`_extremo_spline`)

### RS-R4 · R4 kernel del solver (jacobiano analítico) en Rust

- **Historia (movida de la fila, 2026-11-13):** **Qué:** R4 kernel del solver (jacobiano analítico) en Rust · **Queda:** Solver sigue en scipy. Rebajado 2026-10-31: el polígono de 24 lados resuelve en 75 ms (el plan decía 5 s) y arrastrar cuesta 8–13 ms; solo pesaba con ≥ 200 piezas (400 piezas 2,1 s); RS-S1 (hecho 2026-11-13, «trf» disperso) lo bajó a 0,35 s. · **Evidencia:** omnicad/restricciones/solver.py

### RS-P3 · P3 repintado del boceto proyectando en bloque

- **Historia (movida de la fila, 2026-11-13):** **Qué:** P3 repintado del boceto proyectando en bloque · **Queda:** Proyección 64,6 a 13,9 ms con 10 000 puntos; la meta < 5 ms del repintado completo no se cumple (Qt suma 11,5 ms). · **Evidencia:** omnicad/ui/editor_boceto.py _poli_px; PROJECT_LOG.md:341

### RS-X2 · Abrir un proyecto con caché tarda lo mismo que recalcularlo

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Abrir un proyecto con caché tarda lo mismo que recalcularlo · **Queda:** `motor_cohete` (41 pasos) abre en 2,7 s y recalcula en 2,76 s: la caché guarda solo los pasos lentos y el resto paga `volumen_exacto` y cajas exactas (80 integrales de volumen 0,18 s y 139 `AddOptimal` 0,28 s). Guardar el volumen por forma y usar la caja barata donde solo se descarta (ver P-35). Aceptación: abrir en 1,5 s o menos con los mismos volúmenes y avisos. · **Evidencia:** omnicad/io_archivos/proyecto.py (`_escribir_cache`); omnicad/nucleo/geometria.py (`volumen_exacto`, `caja_envolvente`)

### RS-X3 · Selección bajo el cursor y repintado del boceto

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Selección bajo el cursor y repintado del boceto cuestan 36 µs por curva y el resaltado se apaga con más de 400 · **Queda:** HECHO 2026-11-13 (E1): la selección bajo el cursor mide todos los segmentos de una vez con numpy (`_segmentos_uv` con caché por geometría, `_uv_px`; los textos siguen con su cuenta propia) y el resaltado ya no tiene tope de curvas. Medido main → rama, misma máquina: `_curva_cercana` 400 curvas 31,2 → 0,82 ms, 1500 curvas 114,9 → 3,0 ms, 2000 curvas 153 → 3,9 ms. También: `_poli_px` reusa lo proyectado en el boceto 2D (antes solo en 3D), las splines de ajuste no se reinterpolan en cada cuadro y la unión de `determinadas` y `en_origen` salió del bucle por curva. Repintado (2026-11-13, segunda vuelta): las curvas y los puntos se pegan desde una imagen guardada (`_dibujar_capa_curvas`) cuya clave es exactamente lo que se dibuja (cada curva con color, grosor, estilo, polilíneas y guías; cada punto con lugar y colores; cámara y tamaño); `paintEvent` medido main → rama con la VPS cargada (load ~7): 400 curvas 27,2 → 11,3 ms y 2000 curvas 120 → 42 ms sin cambios en pantalla; rearmar la imagen (cambió el hover, la selección…) cuesta lo mismo que antes. FALTA: medir sin carga (la meta es 8 ms con 400; en la VPS no se puede) con `scripts/medir_paint_boceto.py` (desde `clon/`: `.venv/Scripts/python.exe ../scripts/medir_paint_boceto.py 100,400,2000`; en la VPS cargada da 400 curvas: hover 0,84 ms y repintado sin cambios 11,4 ms) y, si no llega, sacar el bucle de Python que arma la clave. Test de invalidación: `tests/test_rsx3_capa_curvas.py` (10 cambios: geometría, selección, hover, determinadas, tema, capas, cámara, resaltado parcial; con la clave rota fallan). Tests: `tests/test_rsx3_hover_boceto.py` y `tests/test_rsx3_capa_curvas.py`. · **Evidencia:** omnicad/ui/editor_boceto.py (`paintEvent`, bucle de curvas)

### RS-X5 · Verificar la caché de mallas por cara con modelos grandes

- **Historia (movida de la fila, 2026-11-13):** **Qué:** La caché de mallas por cara (32 MB) puede quedar chica para modelos de más de 230 mil triángulos · **Queda:** A 144 B por triángulo (vértices y normales en float64) caben unos 233 mil triángulos; un modelo mayor volvería a extraer todo en cada `set_modelo`. No se midió. Probar float32 y 256 MB; aceptación: `set_modelo` repetido de un modelo de 500 mil triángulos en 50 ms o menos. · **Evidencia:** omnicad/nucleo/render_cpu.py (`_TOPE_BYTES_CARAS`, `_guardar_malla_cara`)

### RS-X7 · Editar `motor_impreso` en el paso 73 y `gatoRL` no llegó a la meta de RS-X1

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Editar `motor_impreso` en el paso 73 y `gatoRL` no llegó a la meta de RS-X1 · **Queda:** Con el trabajador persistente, `motor_impreso` paso 73 da 1,11 s (meta 1 s) y `gatoRL` 3,1 s (meta 3 s). Lo que queda es OpenCascade rehaciendo los pasos siguientes: en `gatoRL`, un corte de 2,8 a 3,2 s (paso 77). Bajarlo pide acelerar ese corte, no el recálculo. · **Evidencia:** omnicad/nucleo/aislado.py

### RS-X6 · Una previa rechazada hace volver a mallar lo recalculado

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Una previa rechazada hace volver a mallar lo recalculado · **Queda:** Lo que dejó RS-X1. Tras Esc, lo que la previa reemplazó ya salió de las tablas del transporte: la edición siguiente lo vuelve a mandar como BREP y el padre recibe objetos nuevos, así que el visor los malla otra vez. No da mal; cuesta una vez. · **Evidencia:** omnicad/timeline/calculo_aislado.py (`_codificar`, `retiradas`); tests/test_trabajador_persistente.py::test_previa_rechazada_no_deja_al_trabajador_adelantado

### RS-X8 · El arreglo planar en Rust une caras cuando un cruce es casi tangente

- **Historia (movida de la fila, 2026-11-13):** **Qué:** El arreglo planar en Rust une caras cuando un cruce es casi tangente · **Queda:** Lo que dejó B-137. `_arreglo_coherente` lo detecta (regiones contra aristas − vértices + componentes) y rige OpenCascade, así que da bien pero tarda 15 ms contra 3 ms. Falta encontrar qué orden angular sale mal en `rust/src/perfiles.rs` y certificar en Rust. Con la base de una letra apoyada en un círculo pasa en 1 de cada 4 posiciones. · **Evidencia:** omnicad/nucleo/perfiles.py (`_arreglo_coherente`); tests/test_texto_curva.py::test_el_disco_no_se_pierde_cuando_una_letra_apoya_sobre_el_circulo

### CPP-P17 · P17 reusar BRepClass3d_SolidClassifier

- **Historia (movida de la fila, 2026-11-13):** **Qué:** P17 reusar BRepClass3d_SolidClassifier · **Queda:** `fijaciones.py` ya reusa un clasificador por cuerpo (`_dentro`, `_material`); quedan los de `geometria.py` (`_queda_enterrada`, vértices dentro de un sólido) que arman uno por punto. · **Evidencia:** omnicad/nucleo/fijaciones.py:634-653; omnicad/nucleo/geometria.py:565-575 y 1042

### CPP-P23 · P23 HLR exacto o rápido según tipo de superficie

- **Historia (movida de la fila, 2026-11-13):** **Qué:** P23 HLR exacto o rápido según tipo de superficie · **Queda:** Para formas libres corre exacto en subproceso con tope y cae a rápido; falta elegir el rápido para el resto por tipo. · **Evidencia:** omnicad/nucleo/dibujo.py:242,345-373 (PLAZO_HLR, es_forma_libre)

### CPP-C3 · C3 ejecutor sin GIL de hojas OCC independientes

- **Historia (movida de la fila, 2026-11-13):** **Qué:** C3 ejecutor sin GIL de hojas OCC independientes · **Queda:** Solo existe el subproceso para autointersecciones y HLR exacto; no hay pool por cuerpos o vistas. · **Evidencia:** omnicad/nucleo/aislado.py

### CPP-C4 · C4 hojas cancelables (booleana, sección, revisión)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** C4 hojas cancelables (booleana, sección, revisión) · **Queda:** Se cancela matando el subproceso solo en autointersecciones y HLR; no en booleanas ni sección. · **Evidencia:** omnicad/nucleo/aislado.py; tests/test_b16_cancelar.py

### CPP-F1 · Fase 1 proceso trabajador en Python (teselado por cuerpo, HLR por vista, botón Cancelar)

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Fase 1 proceso trabajador en Python (teselado por cuerpo, HLR por vista, botón Cancelar) · **Queda:** Existe el subproceso para tareas que pueden no terminar; falta el pool paralelo y el botón en la interfaz. · **Evidencia:** omnicad/nucleo/aislado.py

### CPP-P21 · P21 sección del análisis usando el contorno que ya calcula

- **Historia (movida de la fila, 2026-11-13):** **Qué:** P21 sección del análisis usando el contorno que ya calcula · **Queda:** El log la deja pendiente; no pude confirmar en el código si seccion() ya evita el cálculo repetido. · **Evidencia:** omnicad/nucleo/analisis.py:1088 seccion; omnicad/ui/analisis_vista.py:60-70 (caché)

### AUD-6 · Evitar cuellos O(n²) en concavidad y empalmes masivos

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Cuellos O(n²) en la máscara de aristas cóncavas y en el empalme de muchas aristas · **Queda:** Medido 2026-11-01 en una placa 400×200×20 con N agujeros pasantes (`evidencias/tortura_2026-11-01/aud6*.py`). (1) Máscara del radio mínimo: 0,30 / 2,74 / 11,6 s con N = 300 / 1000 / 2000 (×9 al triplicar, ×4 al duplicar); casi todo (6,17 de 6,26 s con 1500) está en `_es_concava`; el candidato es el bucle que recorre con `TopExp_Explorer` TODAS las aristas de la cara para ubicar la orientación de cada arista (las caras de arriba y abajo tienen N aristas): leído, sin confirmar con un perfil. (2) Empalme de los N bordes superiores: 0,69 / 3,47 / 13,7 / 82,3 s en `_ampliar_tangentes` con N = 500 / 1000 / 2000 / 4000 (un tercio del total, 254,7 s con 4000), porque `aristas_cadena_tangente` rearma el mapa vértice→aristas en cada arista; el resto es el kernel (`Add` 27,7 s y `Build` 148 s con 4000, también ~N²), que no se arregla acá. (3) El radio mínimo con 1,4 millones de vértices (1000 agujeros) llega a 2,1 GB de RAM y con 2 millones a 2,7 GB. Aceptación: ubicar la orientación una vez por cara y armar el mapa una vez por empalme; la máscara de 2000 agujeros en menos de 1 s. · **Evidencia:** nucleo/analisis.py:873 (`_es_concava`, bucle del explorador); nucleo/solidos_modificar.py:266 (`aristas_cadena_tangente`)

### T-21 · check_geometry agota 10 s por cada rosca modelada distinta

- **Historia (movida de la fila, 2026-11-13):** **Qué:** `check_geometry` espera el tope entero (10 s) por cada cilindro con rosca modelada distinto · **Queda:** Medido 2026-11-01: el análisis de autointersecciones de un cilindro M10 modelado tarda 303 s (resultado 0) y todo el resto de la revisión 0,32 s, así que los 10,3 s son `PLAZO_AUTOINTERSECCION` y no trabajo útil. Hecho: la misma forma que ya pasó el tope no se vuelve a esperar (0,3 s la segunda vez, también tras crear otro cuerpo; se vuelve a intentar a los 5 minutos). Queda: cada rosca distinta paga 10 s la primera vez (con 3 se agota el presupuesto de 30 s). Ideas sin probar: detectar la hélice antes de lanzar el proceso o revisar por pares de caras vecinas. · **Evidencia:** clon/omnicad/nucleo/revision.py (`_autointersecciones_seguras`); tests/test_tortura_menores.py::test_t21_la_misma_forma_no_se_vuelve_a_esperar_con_el_mismo_tope

### NOV-tip-1 · Letra grande: títulos de cinta elididos y ventana mínima de 1038 px

- **Historia (movida de la fila, 2026-11-13):** **Qué:** Con letra grande (120–150 %) los títulos de grupo de la cinta se eliden y la ventana no baja de ~1038 px · **Queda:** `ajustar_textos` compacta los botones pero no los títulos `#titulo_grupo` ni el botón de espacio de trabajo (108 px fijo); con 150 % el mínimo de la ventana es 1038 px. Medido en 1024×640 y 800×520. · **Evidencia:** omnicad/ui/cinta.py (`_fila_grupos`, `_estilo_boton`, `espacio.setFixedSize(108, 62)`); evidencias/tipografia_ui/f3_ventana_150.py
