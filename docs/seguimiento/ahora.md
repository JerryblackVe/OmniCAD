# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1 | B-440 | Velocidad de boceto: lo que queda de salir del boceto y poner cotas (primer texto de la sesión ~700 ms y el resto de la fila); B-519 queda Parcial solo por el Ctrl+Z de E11 |
| E2 | B-461 (2.ª vuelta) | Rosca sin booleana (0,4 s) sin romper los 7 grupos de la rosca; worktree `~/OmniCAD-B-461`; después P-156 (entra al 30/11, Gerardo: retomar su worktree) y B-520 |
| E3 | B-524 | Vaciado agranda el volumen al quitar una cara de un cuerpo ya vaciado; después B-525 (B-503 texto integrado: 24870c5; lo que queda es B-528) |
| E4 | B-438 | Superficie › Desfase: teclear «1e3 mm» traba la ventana 2 s (worktree `~/OmniCAD-B-438` con un arreglo previo: revisarlo). B-514 (P2) en pausa hasta después del 30/11 |
| E5 | B-523 | Junta `ball` de la caza (patrones_ensamble_rosca): faltan Pitch/Yaw y get_assembly no la devuelve; reproducir y abrir la fila (B-501 integrado: 6c75a69; E7 lo confirma en la PC) |
| E6 | FL-12 | Huella de find_faces/find_edges en caché (11×) (FL-5 integrado: db970f7) |
| E7 | Caza | Repro de B-519 entregado (Deshacer del menú vuelve todo; Ctrl+Z real queda para E11); vuelve a la caza automática y `scripts/prueba_ui`; lo rojo entra con su ID |
| E8 | B-444 (resto) | Cambiar de pestaña en el panel no mueve la barra con el anclaje por el pie de B-421; test intermitente 1 de 4 (B-491 integrado: 28ae484) |
| E8b | P-158 | Prueba del advisor (1 día). Mensajes de los paneles cortos y gráficos: auditoría (bocetos → sólido) y test de largo (B-502 integrado: d0e9043); sumar el mensaje de `nucleo/vectores.py:105` («⚠ −0,5 mm se come el trazo: probá con menos») |
| E9 | B-436 | Mensajes que confunden (pieza de GLM lista: cerrar tests y review) (B-435 integrado: 5b2e965); OpenCode siempre corriendo; después B-401, B-450, B-457 |
| E10 | B-474 | MCP `new_document` con cambios sin guardar: la herramienta siguiente corre sobre el documento viejo (worktree con arreglo previo); Sonnet medio desde 19:20 UTC (B-521 integrado: a182d81) |

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 1 | FL-13 | draw_line con detección incremental de perfiles (E6 o E1) |
| 2 | FL-15 | Editar el perfil de un Barrido con Empalme y Vaciado: ~20 s (E6) |
| 3 | B-525 | `offset_faces` deja autointersecciones con «ok» (E3) |
| 4 | B-527 | `create_patch` de un anillo ignora el hueco (E4, después de B-438) |
| 5 | B-522 | `insert_svg` con unidades em/ex da INTERNAL_ERROR (E9 con OpenCode GLM: pieza corta) |
| 6 | B-528 | Desfase 2D de texto que se cruza (lo que queda de B-503; Opus, E3) |

**Meta 30/11 (Gerardo, regla 13): app usable.** Fuera de la cola hasta esa fecha (siguen en sus listas): FL-14, P-159, B-405, B-389, P-157, P-134 y todo P2 (P-156 sí entra, Gerardo 15/11).

Sin ítem de prioridad 1 libre: caza automática (`scripts/caza/cazar.py tema` sobre bocetos, sólido, superficie y construir) y `scripts/prueba_ui` de las mismas áreas; lo rojo entra con su ID (chat maestro, 14/11). Los P2 del lote de las 19 h (B-471 a B-479, B-481) y los del lote de las 13 h del 15/11 (B-511 a B-515) quedan en bugs.md sin cola; B-516 Sin verificar.

Hechos y esperando integrar (no ocupan cola): ninguno. Integrados 13-15/11: B-496, B-502, B-489, H-119, B-503 (parte 1), FL-8 (sección), H-91 (parte), B-464b, B-403, FL-3d, B-493, PRUEBA-1115, B-490, H-96, B-442, B-451, B-428, H-82 (parte), P-98, B-491, B-494, B-468, B-362 (parte), B-337 y B-335 (parte), FL-3c (parte), B-464, B-411 (parte), B-466, B-469, B-443, B-423 (parte), B-447 (parte), B-484, H-118 (Parcial), B-470, B-460, B-459, B-485, B-462, B-461 (parte), B-456, B-465 (tests), B-445, ASM-17, B-455, B-419, B-454, FL-3b, B-440 (parte), B-48 (parte), B-453 (parte), B-458, B-432, B-448, H-97, B-421, B-425 (parte), B-457, DIETA-1114, REV-1114, H-69, B-431 y B-441 (Sol), B-434, P-78 (parte), B-417, B-433, PRUEBA-1114, B-426 revertido (no era bug), B-363 (parte), B-420, B-429, B-424, B-423 (parte), B-428, B-426, B-427, B-422 (parte), H-84 (parte), FL-3 Abrir, B-397, H-113, B-48 y FL-2 (partes), B-409, B-410, B-418f, B-418g, B-408 cerrado, B-384, P-153, B-416, PRUEBA9c, B-418b, B-418c, B-418d, B-418e, FL-0, FL-9 + B-418 (d8d4b9f), B-344e, B-412 (cerrado: Fusion hace lo mismo), B-400, B-392, ASM-19, B-172 (Parcial, no se reproduce; entró B-416).
