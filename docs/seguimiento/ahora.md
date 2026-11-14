# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1 | B-48 | Investigación: caída nativa OCCT en Windows, hilos y formas compartidas (brief en su ficha; H-69 integrado: 9c6edd7) |
| E2 | B-425 | Patrón de 5000 copias: modelo 5,4 → 0,5 s; reuso de malla en `set_modelo` (sin tope, como Fusion) |
| E3 | B-440 | Salir del boceto traba la ventana 3 s; cota o desfase ~0,5 s (B-434 integrado: 830b0a8) |
| E4 | B-448 | Extender «Natural» −1,5 % contra Fusion (B-447 pasa a Sol) (B-419 en tests) |
| E5 | ASM-17 | Restricción de componentes |
| E6 | FL-3b | Aceptar, editar y deshacer fuera de la ventana, y la Rosca sin mallar en la ventana (FL-3 Abrir integrado: 572e69c) |
| E7 | B-453 + B-458 | Regresión de la previa de Extruir tras unir: caer a la previa normal sin el mensaje rojo, asa sobre la cara y test FL-2 sobre cuerpo modificado (REV-1114 integrada: 33d1716; B-432 espera sus tests) |
| E8 | B-445 | La cara gana al plano de origen al elegir (B-437 integrado: ad02acb) |
| E9 | Sol | Sol siempre corriendo (Gerardo 14/11): H-115, B-442, B-435, B-436, B-428, B-423, dieta, B-451, B-447; E9 con B-421 y H-97 |
| E10 | B-337 | Abrir e importar un STEP pesado sin congelar (B-335 + B-337; B-363 parte integrado: 8cf5219) |

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 1 | B-454 | Empalme frena en 1 mm y 0,01 mm, y el chaflán da un tope que contradice al asa, sobre el cuerpo unido de B-453 (puede ser la misma causa: lo toma la misma sesión) |
| 2 | B-455 | Previa aparte: un error del hijo que no es del kernel sale en rojo y Aceptar no reintenta (REV-1114) |
| 3 | B-456 | Abrir fuera de la ventana: con el trabajador caído un proyecto chico no abre; test sobre proyecto real (REV-1114) |
| 4 | B-457 | Rosca P-78: test sobre un cuerpo ya modificado (REV-1114) |
| 5 | B-443 | «Propiedades» no abre desde el cuerpo ni el componente, y falta en la cinta |
| 6 | FL-8 (sección) | Análisis de sección con muchos agujeros, 1,1 s en `malla._orejas` (E6) |
| 7 | B-405 | Plano de desfase con distancia cero: falta comparar otros desfases en Fusion (E11) |
| 8 | B-369 | Rosca modelada M2 completa falla sobre un cilindro Ø2 × 30 |
| 9 | B-411 | Entrar a un boceto bloquea la ventana 409 ms en Windows |
| 10 | H-91 | Solevación sólida: condiciones de borde exactas y combinables |

Hechos y esperando integrar (no ocupan cola): ninguno. Integrados 13-14/11: REV-1114, H-69, B-431 y B-441 (Sol), B-434, P-78 (parte), B-417, B-433, PRUEBA-1114, B-426 revertido (no era bug), B-363 (parte), B-420, B-429, B-424, B-423 (parte), B-428, B-426, B-427, B-422 (parte), H-84 (parte), FL-3 Abrir, B-397, H-113, B-48 y FL-2 (partes), B-409, B-410, B-418f, B-418g, B-408 cerrado, B-384, P-153, B-416, PRUEBA9c, B-418b, B-418c, B-418d, B-418e, FL-0, FL-9 + B-418 (d8d4b9f), B-344e, B-412 (cerrado: Fusion hace lo mismo), B-400, B-392, ASM-19, B-172 (Parcial, no se reproduce; entró B-416).
