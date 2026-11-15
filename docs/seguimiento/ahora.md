# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1 | B-489 | **BLOQUEANTE** Patrón de boceto ×1000 cuelga o cierra la app: tope con error claro antes de detectar perfiles (B-466 integrado: 5924490) |
| E2 | B-497 | Rosca: tamaño automático como Fusion y 2 asas (hecho, en tests reducidos); después B-508 (B-461 sin booleana: al tope, queda en ~/OmniCAD-B-461 y vuelve a Sigue) |
| E3 | B-507 | `offset_faces` sobre esfera con −radio: «ok» con un sólido inválido (B-503 parte 1 integrada: 8dfc8ca; la parte de UI espera el estudio de E11, parche en `evidencias/parches/b503_ui.patch`) |
| E4 | B-496 | Estrella de boceto: 22 puntas dibuja ~9 lóbulos, glifos encimados, puntos sueltos (Gerardo) (B-493 integrado: 6fe740b) |
| E5 | H-119 | Ensamblar › «Nuevo conjunto de contactos», «Desactivar todos» y los «Activar» grisados, como Fusion (B-443 integrado: c9af24a) |
| E6 | FL-5 | Prevuelo desde 60 pasos: 300 cajas 23,5 s → 2,6 s sin él; después FL-12 y FL-14 (FL-8 sección integrado: 06882d8) |
| E7 | Caza | Sin ítem P1 libre para E7: caza automática (`scripts/caza/cazar.py tema` bocetos, sólido, superficie, construir) y `scripts/prueba_ui`; lo rojo entra con su ID (B-468 integrado: e0273ac) |
| E8 | B-444 (resto) | Cambiar de pestaña en el panel no mueve la barra con el anclaje por el pie de B-421; test intermitente 1 de 4 (B-491 integrado: 28ae484) |
| E8b | B-502 | Prueba del advisor (Opus) por 1 día, Gerardo 15/11; sesión «E8 con advisor», cwd `~/OmniCAD-E8`: barra de posición pisada a 800×520 |
| E9 | Sol | **B-495 primero (regresión de su B-423)**; después: Sol siempre corriendo (Gerardo 14/11): H-115, B-435, B-436, B-401, B-457, P-134, B-450, B-438, B-474 |
| E10 | B-509 | Las sesiones por API, MCP y CLI no autoguardan (H-91 parte integrado: 6d956c9) |

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 1 | B-487 | Curvatura línea–spline mueve la línea ~6 mm (Fusion la deja quieta) (E1, después de B-489) |
| 2 | P-158 | Mensajes de los paneles cortos y gráficos (1 renglón con ícono, tope en el asa, rojo); auditoría y test de largo (P1, Gerardo) |
| 3 | B-500 | MCP `manage_analysis` falla con un Mapa de desviación (falta el tipo en TIPOS) (E5, después de H-119) |
| 4 | B-501 | Ensamblar › Conjunto: el nombre y el desfase tecleados en la fila no se aplican (E5) |
| 5 | B-506 | Agujeros tangentes dan «ok» con un cuerpo inválido (también por set_parameter) (E2 o E3) |
| 6 | B-504 | `stitch_surfaces` con tolerancia 1e6: «ok» con forma vacía que rompe get_scene_info (E4) |
| 7 | B-505 | `drag_component` da «ok» sin mover (E5, después de H-119) |
| 8 | B-510 | `sketch_fillet` casi colineal crea un arco de largo 0 (E1) |
| 9 | FL-12 | Huella de find_faces/find_edges en caché (11×) (E6) |
| 10 | FL-13 | draw_line con detección incremental de perfiles (E6 o E1) |
| 11 | FL-14 | Miniatura al guardar y prevuelo al abrir (E6) |
| 12 | FL-15 | Editar el perfil de un Barrido con Empalme y Vaciado: ~20 s (E6) |
| 13 | P-159 | 179 + 19 parámetros a `Expr` por tandas (E8 o Sol) |
| 14 | P-156 | Holgura de impresión 3D única (diseño de Gerardo, ficha en mejoras.md): reemplaza `print_clearance` (E2, después de B-497) |
| 15 | B-405 | Plano de desfase con distancia cero: falta comparar otros desfases en Fusion (E11) |
| 16 | B-389 | Windows agota memoria en una tanda larga: `~/OmniCAD-B-389` tiene un arreglo sin integrar de hace 2 días (`turno.py` con BLAS de un hilo bajo el tope, más su test); verificar, revisar y cerrar |
| 17 | P-157 | Reorganizar Preferencias como Fusion, visual y con poco texto (P2, pedido de Gerardo; junta P-152, CF-7, CF-8, NOV-tip-2/3/4 y P-2d) |
| 18 | B-461 (sin booleana, 2.ª vuelta) | La directa (0,4 s) rompe 7 grupos de la rosca: `_es_filete` (un flanco cada 4–5 vueltas o reconocer por la varilla), sección por el eje degenerada, previa, rechazos de B-299, tolerancia de B-250; worktree `~/OmniCAD-B-461` |

Sin ítem de prioridad 1 libre: caza automática (`scripts/caza/cazar.py tema` sobre bocetos, sólido, superficie y construir) y `scripts/prueba_ui` de las mismas áreas; lo rojo entra con su ID (chat maestro, 14/11). Los P2 del lote de las 19 h (B-471 a B-479, B-481) y los del lote de las 13 h del 15/11 (B-511 a B-515) quedan en bugs.md sin cola; B-516 Sin verificar.

Hechos y esperando integrar (no ocupan cola): ninguno. Integrados 13-15/11: B-503 (parte 1), FL-8 (sección), H-91 (parte), B-464b, B-403, FL-3d, B-493, PRUEBA-1115, B-490, H-96, B-442, B-451, B-428, H-82 (parte), P-98, B-491, B-494, B-468, B-362 (parte), B-337 y B-335 (parte), FL-3c (parte), B-464, B-411 (parte), B-466, B-469, B-443, B-423 (parte), B-447 (parte), B-484, H-118 (Parcial), B-470, B-460, B-459, B-485, B-462, B-461 (parte), B-456, B-465 (tests), B-445, ASM-17, B-455, B-419, B-454, FL-3b, B-440 (parte), B-48 (parte), B-453 (parte), B-458, B-432, B-448, H-97, B-421, B-425 (parte), B-457, DIETA-1114, REV-1114, H-69, B-431 y B-441 (Sol), B-434, P-78 (parte), B-417, B-433, PRUEBA-1114, B-426 revertido (no era bug), B-363 (parte), B-420, B-429, B-424, B-423 (parte), B-428, B-426, B-427, B-422 (parte), H-84 (parte), FL-3 Abrir, B-397, H-113, B-48 y FL-2 (partes), B-409, B-410, B-418f, B-418g, B-408 cerrado, B-384, P-153, B-416, PRUEBA9c, B-418b, B-418c, B-418d, B-418e, FL-0, FL-9 + B-418 (d8d4b9f), B-344e, B-412 (cerrado: Fusion hace lo mismo), B-400, B-392, ASM-19, B-172 (Parcial, no se reproduce; entró B-416).
