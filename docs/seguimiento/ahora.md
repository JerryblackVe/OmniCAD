# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1 | B-452 | Fuera del boceto, la vista 3D sigue mostrando las curvas y objetos de boceto ocultos (B-480 integrado: e909112) |
| E2 | B-531 | Regresión de B-461 (cresta a derechas), primero; después P-156 fase 2: Holgura de impresión: botón de la placa, molde, Impresa/… (B-520 integrado: c325d0c; B-530 Sin verificar para E11) |
| E3 | B-528 | Limpiar el desfase 2D de texto (`vectores.desfase_caras`: contornos que se cruzan, aristas de 7e-5 mm) para que el desfase por contorno sirva con «@tienda» (B-525 integrado: 2d91b7d) |
| E4 | B-438 | Superficie › Desfase: teclear «1e3 mm» traba la ventana 2 s (worktree `~/OmniCAD-B-438` con un arreglo previo: revisarlo). B-514 (P2) en pausa hasta después del 30/11 |
| E5 | B-534 | Asa de cantidad del Patrón en trayectoria no baja (posible regresión de B-435) (B-471 integrado: bacda54) |
| E6 | FL-15 | Editar el perfil de un Barrido con Empalme y Vaciado: ~20 s (FL-13 integrado: a1f3430) |
| E7 | Caza | Repro de B-519 entregado (Deshacer del menú vuelve todo; Ctrl+Z real queda para E11); vuelve a la caza automática y `scripts/prueba_ui`; lo rojo entra con su ID |
| E8 | B-518 | Traza «CajaValor already deleted» al cerrar (manipuladores.py:1896) (B-444 integrado: 036c59f) |
| E8b | P-158c | Entrega 2 de P-158: Mensajes cortos de Superficie y el resto (368 pendientes); P-158b integrado: 126305f |
| E9 | B-401 | El cálculo aislado pierde atributos de boceto; OpenCode siempre corriendo (B-450 integrado: 9044a97) |
| E10 | B-533 | Cinta en ventana chica: nombres de grupo partidos al medio («C…▾») (B-423 integrado: verificado en la VPS, falta Windows) |

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 1 | B-425 | Patrón con muchas copias congela la ventana (E6) |
| 2 | B-331 | La API en vivo congela la ventana (E6) |

Esperan a E11 en Windows (sin código por ahora): B-48 (caída nativa con la previa en paralelo) y B-172 (sin la pieza original).

**Meta 30/11 (Gerardo, regla 13): app usable.** Fuera de la cola hasta esa fecha (siguen en sus listas): FL-14, P-159, B-405, B-389, P-157, P-134 y todo P2 (P-156 sí entra, Gerardo 15/11).

Sin ítem de prioridad 1 libre: caza automática (`scripts/caza/cazar.py tema` sobre bocetos, sólido, superficie y construir) y `scripts/prueba_ui` de las mismas áreas; lo rojo entra con su ID (chat maestro, 14/11). Los P2 del lote de las 19 h (B-471 a B-479, B-481) y los del lote de las 13 h del 15/11 (B-511 a B-515) quedan en bugs.md sin cola; B-516 Sin verificar.

Hechos y esperando integrar (no ocupan cola): ninguno. Integrados 13-15/11: B-496, B-502, B-489, H-119, B-503 (parte 1), FL-8 (sección), H-91 (parte), B-464b, B-403, FL-3d, B-493, PRUEBA-1115, B-490, H-96, B-442, B-451, B-428, H-82 (parte), P-98, B-491, B-494, B-468, B-362 (parte), B-337 y B-335 (parte), FL-3c (parte), B-464, B-411 (parte), B-466, B-469, B-443, B-423 (parte), B-447 (parte), B-484, H-118 (Parcial), B-470, B-460, B-459, B-485, B-462, B-461 (parte), B-456, B-465 (tests), B-445, ASM-17, B-455, B-419, B-454, FL-3b, B-440 (parte), B-48 (parte), B-453 (parte), B-458, B-432, B-448, H-97, B-421, B-425 (parte), B-457, DIETA-1114, REV-1114, H-69, B-431 y B-441 (Sol), B-434, P-78 (parte), B-417, B-433, PRUEBA-1114, B-426 revertido (no era bug), B-363 (parte), B-420, B-429, B-424, B-423 (parte), B-428, B-426, B-427, B-422 (parte), H-84 (parte), FL-3 Abrir, B-397, H-113, B-48 y FL-2 (partes), B-409, B-410, B-418f, B-418g, B-408 cerrado, B-384, P-153, B-416, PRUEBA9c, B-418b, B-418c, B-418d, B-418e, FL-0, FL-9 + B-418 (d8d4b9f), B-344e, B-412 (cerrado: Fusion hace lo mismo), B-400, B-392, ASM-19, B-172 (Parcial, no se reproduce; entró B-416).
