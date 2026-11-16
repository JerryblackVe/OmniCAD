# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora (uno por sesión)


| Sesión | Ítem | Qué |
|---|---|---|
| E1 | B-585 | Solver: al restringir agranda mucho el círculo en vez de mover lo menos posible. Opus alto. B-582 integrado |
| E2 | — | En pausa (tope de 3 sesiones por el cupo). B-600 integrado: 80b708f |
| E3 | — | En pausa (cupo amarillo, 82 % el 16/11 19 UTC). B-503 Parcial: 7cc89af (falta una cara sola de letra curva, velocidad y Arial en Windows) |
| E4 | — | En pausa por el cupo semanal (B-438 integrado: 9e70b64); cuando vuelva: B-602 (Superficie sin Patrón ni Simetría, sin verificar) |
| E5 | — | En pausa (cupo amarillo). ASM-9 integrado: 99fb1de. Sigue ASM-16 con Opus alto (pide el solver de uniones) cuando haya cupo |
| E6 | — | Libre. B-611 integrado (no era regresión: el test esperaba el texto largo; Chaflán sin «⚠ ⚠»). Rojos viejos anotados: B-613, B-614 |
| E7 | — | En pausa (tope de sesiones). P-169 (2) y B-603 integrados. Sigue P-167 cuando haya lugar |
| E8 | — | Libre (tope de sesiones por el cupo). P-169 completa: 243e3cb |
| E9 | Caza + cola OpenCode | 1) caza superficie y construir (corriendo); 2) P-158, un archivo por corrida (GLM, revisa MiniMax), agregándolo a TOPES en 0: timeline/operaciones.py (38), nucleo/geometria.py (22), timeline/ops_modificar.py (19), nucleo/editar_cara.py (17), nucleo/construccion.py (16), nucleo/analisis.py (13), nucleo/vectores.py (9); 3) lo rojo de la caza, con su ID. En rojo (90 %) las lanza el coordinador |
| E10 | — | En pausa por el cupo semanal (B-535 integrado: 97226db) |

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 2 | B-619 | Proyectar un barril: silueta con cientos de puntos, borde ondulado y puntos sueltos; y revisar los 5 tipos de PROYECTAR contra Fusion (E1 tras B-585, Opus alto) |
| 2b | B-620 | Vaciado: la previa aparte tarda ~17 s y Aceptar 2–3 s (E6, Opus alto; arranca cuando el cupo lo permita) |
| 3 | B-618 | Solevación entre dos círculos: falso «se autointerseca» y previa manchada (E2, Opus alto; bug de prioridad 1, va antes que SOL-8) |
| 4 | SOL-8 | Barrido exacto de un cuerpo sólido (E2, Opus alto) |
| 5 | SUP-13 / SUP-28 | Solevación de superficie con condiciones y guías; Empalme y Chaflán de superficie (E4, Opus alto) |

Esperan a E11 en Windows (sin código por ahora): B-48 (caída nativa con la previa en paralelo) y B-172 (sin la pieza original).

**Meta 30/11 (Gerardo, regla 13): app usable.** Fuera de la cola hasta esa fecha (siguen en sus listas): FL-14, P-159, B-405, B-389, P-134 y todo P2 (P-156 sí entra, Gerardo 15/11).

Sin ítem de prioridad 1 libre: caza automática (`scripts/caza/cazar.py tema` sobre bocetos, sólido, superficie y construir) y `scripts/prueba_ui` de las mismas áreas; lo rojo entra con su ID (chat maestro, 14/11). Los P2 del lote de las 19 h (B-471 a B-479, B-481) y los del lote de las 13 h del 15/11 (B-511 a B-515) quedan en bugs.md sin cola; B-516 Sin verificar.

Hechos y esperando integrar (no ocupan cola): ninguno. Lo integrado va al Registro de `PROJECT_LOG.md`, no acá.
