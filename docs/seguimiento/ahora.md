# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1 | B-466 | Restricción Curvatura arco–spline destruye la geometría (arco a r=5107) (B-48 parte integrado: c8f9e66; falta Windows) |
| E2 | B-462 | Barrido y Solevación que se autointersecan crean un cuerpo inválido; guarda común con check_geometry (B-454 integrado: 44055c7) |
| E3 | B-460 | Empalme más estricto que Fusion: falla desde r41 donde Fusion acepta r55 y r59 (B-440 parte integrado: 3ac43ed) |
| E4 | B-459 | Vaciado sin caras falla en cualquier caja ya unida o cortada (también en main) (B-455 y B-419 integrados: 3d82975, 8347d0a) |
| E5 | B-443 | «Propiedades» no abre desde el cuerpo ni el componente, y falta en la cinta (ASM-17 integrado: 81f0885) |
| E6 | B-461 | Rosca modelada lenta: M10×30 6 s, M2 34 s (Fusion 0,2 s) (FL-3b integrado: ab9ae53; falta Windows) |
| E7 | B-468 | Caja de valor junto al asa como en Fusion, en todas las asas (B-456 integrado: 45f39ca) |
| E8 | B-469 | Texto de boceto: el clic en «Contenido» cierra el boceto (B-465 tests integrados: 7f78ac5; falta E11) |
| E9 | Sol | Sol siempre corriendo (Gerardo 14/11): H-115, B-442, B-435, B-436, B-428, B-423, B-451, B-447, B-401, H-82, B-457, B-444, P-134, P-98, B-450 |
| E10 | B-337 | Abrir e importar un STEP pesado sin congelar (B-335 + B-337; B-363 parte integrado: 8cf5219) |

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 1 | B-470 | Vaciado da «ok» con una cáscara abierta en un cuerpo modificado (va con la guarda de B-462) |
| 2 | B-467 | Empalme sobre aristas tangentes: Fusion toma la cadena tangente y entra (resto de B-454) |
| 3 | B-464 | Solevación con punto tangente da error con peso 1 (Fusion 15708,3) |
| 4 | H-118 | Desfase de caras de una rosca modelada, como Fusion (holgura para imprimir) |
| 5 | B-480 | Girar el boceto 90° pierde restricciones y cotas sin aviso |
| 6 | B-444 (resto) | Cambiar de pestaña en el panel no mueve la barra con el anclaje por el pie de B-421; test intermitente 1 de 4 (E6, dueña del anclaje) |
| 7 | FL-8 (sección) | Análisis de sección con muchos agujeros, 1,1 s en `malla._orejas` (E6) |
| 8 | B-405 | Plano de desfase con distancia cero: falta comparar otros desfases en Fusion (E11) |
| 9 | B-411 | Entrar a un boceto bloquea la ventana 409 ms en Windows |
| 10 | H-91 | Solevación sólida: condiciones de borde exactas y combinables |

Sin ítem de prioridad 1 libre: caza automática (`scripts/caza/cazar.py tema` sobre bocetos, sólido, superficie y construir) y `scripts/prueba_ui` de las mismas áreas; lo rojo entra con su ID (chat maestro, 14/11). Los P2 del lote de las 19 h (B-471 a B-479, B-481) quedan en bugs.md sin cola.

Hechos y esperando integrar (no ocupan cola): ninguno. Integrados 13-14/11: B-456, B-465 (tests), B-445, ASM-17, B-455, B-419, B-454, FL-3b, B-440 (parte), B-48 (parte), B-453 (parte), B-458, B-432, B-448, H-97, B-421, B-425 (parte), B-457, DIETA-1114, REV-1114, H-69, B-431 y B-441 (Sol), B-434, P-78 (parte), B-417, B-433, PRUEBA-1114, B-426 revertido (no era bug), B-363 (parte), B-420, B-429, B-424, B-423 (parte), B-428, B-426, B-427, B-422 (parte), H-84 (parte), FL-3 Abrir, B-397, H-113, B-48 y FL-2 (partes), B-409, B-410, B-418f, B-418g, B-408 cerrado, B-384, P-153, B-416, PRUEBA9c, B-418b, B-418c, B-418d, B-418e, FL-0, FL-9 + B-418 (d8d4b9f), B-344e, B-412 (cerrado: Fusion hace lo mismo), B-400, B-392, ASM-19, B-172 (Parcial, no se reproduce; entró B-416).
