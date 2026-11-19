# Plan: boceto y restricciones perfectos (Gerardo, 2026-11-19)

«Es importante que sketch quede perfecto porque es la parte más básica en CAD. Debes hacer un plan integral.»
Desde el 19/11 todo el foco está en Boceto y Restricciones. La cola sigue siendo [seguimiento/ahora.md](seguimiento/ahora.md);
este archivo dice quién hace qué y cuándo está listo. Los bugs viven en [seguimiento/bugs.md](seguimiento/bugs.md).

## Punto de partida
Video de Gerardo del 19/11 (`~/coordinador/casos/video_boceto_1119/`, fuera del repo): B-649, B-650 y B-651.

## Quién hace qué
| Quién | Qué |
|---|---|
| E1 (Opus alto) | Solver y arrastre: B-649, B-650, B-651 y todo bug nuevo del solver. Lee `docs/fusion_docs` antes (regla 6) |
| E3, E8 | Boceto fuera del solver: herramientas, Recortar, Alargar, Desfase, selección |
| E6 | Termina B-644 y pasa a velocidad del solver (arrastre fluido, sin saltos) |
| E7 | Caza `tema` boceto en Linux (`scripts/caza/`) y `scripts/prueba_ui` de boceto, con arrastres y valores raros |
| OpenCode | Un test de restricciones por bug (casos chicos) y la doc |
| E11 (PC) | Batería con mouse real; cada falla en `evidencias/reportes_pc/<fecha>_<tema>/`, informa al coordinador |
| Coordinador | Da el ID, ordena `ahora.md`, integra |

Lo que no es boceto se frena al cerrar su ítem actual (E4 con SUP-28, E7 con AG-20).

## Ciclo
E11 o E7 encuentran → el coordinador da ID → E1, E3 o E8 arreglan con su test → E11 vuelve a probar.

## Listo cuando
La batería entera de E11 pasa sin fallas y no queda ningún bug de boceto abierto en `bugs.md`.
