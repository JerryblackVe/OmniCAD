# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1 | B-48 | Investigación: caída nativa OCCT en Windows, hilos y formas compartidas (brief en su ficha; H-69 integrado: 9c6edd7) |
| E2 | B-454 | Empalme frena en 1 mm y 0,01 mm, y el chaflán da un tope que contradice al asa, sobre el cuerpo unido (B-425 integrado: f3cc951) |
| E3 | B-440 | Salir del boceto traba la ventana 3 s; cota o desfase ~0,5 s (B-434 integrado: 830b0a8) |
| E4 | B-455 | Previa aparte: un error del hijo que no es del kernel sale en rojo y Aceptar no reintenta (B-448 integrado: 1b37b9d; B-419 en tests) |
| E5 | ASM-17 | Restricción de componentes |
| E6 | FL-3b | Aceptar, editar y deshacer fuera de la ventana, y la Rosca sin mallar en la ventana (FL-3 Abrir integrado: 572e69c) |
| E7 | B-456 | Abrir fuera de la ventana: con el trabajador caído un proyecto chico no abre; test sobre proyecto real (B-453 parte y B-458 integrados: 0ffd6e9; B-432: 1e5ef0a) |
| E8 | B-445 | La cara gana al plano de origen al elegir (B-437 integrado: ad02acb) |
| E9 | Sol | Sol siempre corriendo (Gerardo 14/11): H-115, B-442, B-435, B-436, B-428, B-423, B-451, B-447, B-401, H-82, B-457, B-444, P-134, P-98, B-450 |
| E10 | B-337 | Abrir e importar un STEP pesado sin congelar (B-335 + B-337; B-363 parte integrado: 8cf5219) |

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 1 | B-460 | Empalme más estricto que Fusion: falla desde r41 donde Fusion acepta r55 y r59 (Sólido › Modificar, E3 al liberarse) |
| 2 | B-462 | Barrido y Solevación que se autointersecan crea un cuerpo inválido (volumen negativo) en vez de fallar; guarda común con check_geometry |
| 3 | B-464 | Solevación con punto tangente da error con peso 1 (Fusion 15708,3) |
| 4 | B-461 | Rosca modelada lenta: M10×30 6 s, M2 34 s (Fusion 0,2 s); velocidad, E6 |
| 5 | B-444 (resto) | Cambiar de pestaña en el panel no mueve la barra con el anclaje por el pie de B-421; test intermitente 1 de 4 (E6, dueña del anclaje) |
| 6 | B-443 | «Propiedades» no abre desde el cuerpo ni el componente, y falta en la cinta |
| 7 | FL-8 (sección) | Análisis de sección con muchos agujeros, 1,1 s en `malla._orejas` (E6) |
| 8 | B-405 | Plano de desfase con distancia cero: falta comparar otros desfases en Fusion (E11) |
| 9 | B-411 | Entrar a un boceto bloquea la ventana 409 ms en Windows |
| 10 | H-91 | Solevación sólida: condiciones de borde exactas y combinables |

Hechos y esperando integrar (no ocupan cola): ninguno. Integrados 13-14/11: B-453 (parte), B-458, B-432, B-448, H-97, B-421, B-425 (parte), B-457, DIETA-1114, REV-1114, H-69, B-431 y B-441 (Sol), B-434, P-78 (parte), B-417, B-433, PRUEBA-1114, B-426 revertido (no era bug), B-363 (parte), B-420, B-429, B-424, B-423 (parte), B-428, B-426, B-427, B-422 (parte), H-84 (parte), FL-3 Abrir, B-397, H-113, B-48 y FL-2 (partes), B-409, B-410, B-418f, B-418g, B-408 cerrado, B-384, P-153, B-416, PRUEBA9c, B-418b, B-418c, B-418d, B-418e, FL-0, FL-9 + B-418 (d8d4b9f), B-344e, B-412 (cerrado: Fusion hace lo mismo), B-400, B-392, ASM-19, B-172 (Parcial, no se reproduce; entró B-416).
