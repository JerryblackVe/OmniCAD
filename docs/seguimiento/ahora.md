# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora

**Cupo ROJO (90 %, 17/11 ~09:40 UTC): todo Claude en pausa hasta el 19/11 08 UTC; solo OpenCode.** (uno por sesión)


| Sesión | Ítem | Qué |
|---|---|---|
| E1 | — | En pausa (cupo semanal 89 %, contexto 37 %). B-619 integrado como Parcial (0b099ba7; quedan B-619b y B-619c). Cuando vuelva: B-617 (Concéntrica arco–arco), Opus alto |
| E2 | — | En pausa (tope de 3 sesiones por el cupo). B-600 integrado: 80b708f |
| E3 | — | En pausa (cupo amarillo, 82 % el 16/11 19 UTC). B-503 Parcial: 7cc89af (falta una cara sola de letra curva, velocidad y Arial en Windows) |
| E4 | — | En pausa por el cupo semanal (B-438 integrado: 9e70b64); cuando vuelva: B-602 (Superficie sin Patrón ni Simetría, sin verificar) |
| E5 | — | En pausa (cupo amarillo). ASM-9 integrado: 99fb1de. Sigue ASM-16 con Opus alto (pide el solver de uniones) cuando haya cupo |
| E6 | — | Desde el 19/11, SOLO velocidad de prioridad 1, comando por comando, contra plan_fluidez M1/M2 (congelamientos >250 ms, previa <0,3 s), empezando por lo que mida FLUIDEZ-P1 (OpenCode). B-620 Parcial: falta Windows (E11) |
| E7 | — | Libre. B-626 integrado (planos del tamaño de la pieza) |
| E8 | — | Libre (tope de sesiones por el cupo). P-169 completa: 243e3cb |
| E9 | — | En pausa (rojo). Las corridas de OpenCode las lanza el vigía; cola en `~/coordinador/opencode_cola/` («Protocolo de OpenCode» en `docs/coordinacion.md`). P-158 del núcleo integrado: 6c65875c; UI-1117 terminada, falta integrar |
| E10 | — | En pausa por el cupo semanal (B-535 integrado: 97226db) |
| E11 | — | En la PC, solo con el OK de Gerardo. Esperan Windows: B-48, B-172, B-620 |

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 1a | B-638 | Alargar del boceto no hace nada en la ventana (E1, Opus alto; si no sale rápido, en gris por la regla 16) |
| 1b | B-626 | Reabierto: los planos de origen aparecen solos al abrir una herramienta y tapan la pieza (E7, Sonnet; comparar con Fusion) |
| 1d | B-637 | Extruir: perfiles coplanares de varios bocetos (como Fusion), mensaje y flecha en su lugar (E2, Opus alto) |
| 1e | B-639 | La spline usada como ruta sale deformada (Plano a lo largo de la ruta; revisar Barrido); previa y campo 0–1 (E2, Opus alto) |
| 2 | B-633 | Solevación rectángulo→círculo: Engrosar (superficie) falla con mensajes falsos (E3, Opus alto; reporte de Gerardo del 17/11) |
| 3 | B-618 | Solevación entre dos círculos: falso «se autointerseca» y previa manchada (E2, Opus alto; bug de prioridad 1, va antes que SOL-8) |
| 4 | SOL-8 | Barrido exacto de un cuerpo sólido (E2, Opus alto) |
| 5 | SUP-13 / SUP-28 | Solevación de superficie con condiciones y guías; Empalme y Chaflán de superficie (E4, Opus alto) |

Esperan a E11 en Windows (sin código por ahora): B-48 (caída nativa con la previa en paralelo) y B-172 (sin la pieza original).

**Meta 30/11 (Gerardo, regla 13): app usable.** Fuera de la cola hasta esa fecha (siguen en sus listas): FL-14, P-159, B-405, B-389, P-134 y todo P2 (P-156 sí entra, Gerardo 15/11).

Sin ítem de prioridad 1 libre: caza automática (`scripts/caza/cazar.py tema` sobre bocetos, sólido, superficie y construir) y `scripts/prueba_ui` de las mismas áreas; lo rojo entra con su ID (chat maestro, 14/11). Los P2 del lote de las 19 h (B-471 a B-479, B-481) y los del lote de las 13 h del 15/11 (B-511 a B-515) quedan en bugs.md sin cola; B-516 Sin verificar.

Hechos y esperando integrar (no ocupan cola): ninguno. Lo integrado va al Registro de `PROJECT_LOG.md`, no acá.
