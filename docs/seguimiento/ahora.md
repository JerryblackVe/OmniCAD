# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1 | B-413 | Boceto › la cota de un rectángulo sin restringir debe dejar fija la primera esquina, como Fusion (FL-2 parte integrado) |
| E2 | B-425 | Patrón de 5000 copias: modelo 5,4 → 0,5 s; reuso de malla en `set_modelo` (sin tope, como Fusion) |
| E3 | P-78 | Rosca modelada rápida (F6) |
| E4 | B-419 | Solevación de superficie con autointersección que da `ok` (gemelo de B-416) |
| E5 | ASM-17 | Restricción de componentes |
| E6 | FL-3b | Aceptar, editar y deshacer fuera de la ventana, y la Rosca sin mallar en la ventana (FL-3 Abrir integrado: 572e69c) |
| E7 | B-433 | Poner al día `prueba_ui/teclear.py` con B-422 (después B-432; PRUEBA-1114 integrada: 0327816) |
| E8 | B-417 | Timeline › doble clic en un paso solo lo selecciona la primera vez |
| E9 | Sol | B-431 y H-115 listos (faltan sus tests), B-421 y H-97 en tests; Sol sin cupo desde las 10:36 UTC; después B-428 y B-423 (resto) |
| E10 | B-337 | Abrir e importar un STEP pesado sin congelar (B-335 + B-337; B-363 parte integrado: 8cf5219) |

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 1 | B-439 | Boceto › no se puede acotar un círculo (E1 al cerrar B-413) |
| 2 | B-440 | Salir del boceto traba la ventana 3 s; cota o desfase ~0,5 s |
| 3 | B-443 | «Propiedades» no abre desde el cuerpo ni el componente, y falta en la cinta |
| 4 | B-434 | Pulsar/tirar con un empalme vecino agranda la caja en Y (Fusion solo mueve la cara) — E3 al cerrar P-78 |
| 5 | B-437 | Un error de GL repetido abre un cuadro por cada repintado |
| 6 | FL-8 (sección) | Análisis de sección con muchos agujeros, 1,1 s en `malla._orejas` (E6) |
| 7 | B-405 | Plano de desfase con distancia cero: falta comparar otros desfases en Fusion (E11) |
| 8 | B-369 | Rosca modelada M2 completa falla sobre un cilindro Ø2 × 30 |
| 9 | B-411 | Entrar a un boceto bloquea la ventana 409 ms en Windows |
| 10 | H-91 | Solevación sólida: condiciones de borde exactas y combinables |

Hechos y esperando integrar (no ocupan cola): ninguno. Integrados 13-14/11: PRUEBA-1114, B-426 revertido (no era bug), B-363 (parte), B-420, B-429, B-424, B-423 (parte), B-428, B-426, B-427, B-422 (parte), H-84 (parte), FL-3 Abrir, B-397, H-113, B-48 y FL-2 (partes), B-409, B-410, B-418f, B-418g, B-408 cerrado, B-384, P-153, B-416, PRUEBA9c, B-418b, B-418c, B-418d, B-418e, FL-0, FL-9 + B-418 (d8d4b9f), B-344e, B-412 (cerrado: Fusion hace lo mismo), B-400, B-392, ASM-19, B-172 (Parcial, no se reproduce; entró B-416).
