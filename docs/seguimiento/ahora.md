# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora

**Cupo AMARILLO (19/11 11 UTC, semanal 8 %): 3 sesiones de Claude a la vez, solo boceto.** (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1 | B-669 | Gemelo de B-650: tangente línea–elipse y línea–curva 3D con el contacto en el tramo (Opus alto). B-650/B-651 integrados |
| E3 | — | B-660 y B-667 integrados (7f03f6f2, 220601c3); se vacía y queda quieta |
| E4 | B-619 (desde 13:10 UTC) | Proyectar un cuerpo de revolución: B-619b (curva 3D exacta) y B-619c (Opus alto; trabada en OpenCode con 2 modelos). B-665 y B-666 integrados |
| E8 | — | B-658 integrado (855b50ab); se vacía (contexto 30 %) |
| OpenCode | B-584, H-117, B-656, B-653, B-479, B-512, P-178, B-670, B-671, B-672; PREP: B-667b, B-619b, tests de restricciones y de cotas | Cola de boceto (vigía); lo demás en `manana/` |
| E2, E5, E6, E7, E9, E10 | — | En pausa por el amarillo (E6: B-659 y velocidad del solver cuando haya lugar) |
| E11 | — | En la PC, solo con el OK de Gerardo. Esperan Windows: B-48, B-172, B-620 |

**Foco del 19/11 (Gerardo: «que los agentes solo trabajen en boseto»): solo boceto en Ahora y Sigue; sin fecha de corte hasta cerrar el «Listo cuando» de `plan_boceto_perfecto.md`.** Plan: [plan_boceto_perfecto.md](../plan_boceto_perfecto.md).

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 1 | B-667 | Parcial: el 2.º arrastre deforma la spline; E3 desde las 13:13 UTC en ~/OmniCAD-B-667b (Opus alto) |
| 2 | PRUEBA-PROY (hecha por E7: B-684, B-685, B-686 a OpenCode) | Probar como usuario los 5 tipos de PROYECTAR del boceto (Proyectar, Intersecar, Incluir geometría 3D, Perfil giratorio, Curva isoparamétrica): mouse simulado y valores raros contra `docs/fusion_docs` (E7, Sonnet medio; cada falla = fila nueva de boceto; antes, OpenCode prepara los tests que falten) |
| 3 | PRUEBA-CMDS | Probar en la ventana los 61 comandos de la cinta del boceto sin prueba como usuario (lista en `docs/plan_boceto_perfecto.md` › Cobertura; script `scripts/cobertura_boceto.py`): E7 en Linux con `prueba_ui`, E11 con mouse real lo que E7 no pueda; cada falla, fila nueva de boceto |

Esperan a E11 en Windows (sin código por ahora): B-48 (caída nativa con la previa en paralelo) y B-172 (sin la pieza original).

**Meta 30/11 (Gerardo, regla 13): app usable.** Fuera de la cola hasta esa fecha (siguen en sus listas): FL-14, P-159, B-405, B-389, P-134 y todo P2 (P-156 sí entra, Gerardo 15/11).

Sin ítem de prioridad 1 libre: caza automática (`scripts/caza/cazar.py tema` sobre bocetos, sólido, superficie y construir) y `scripts/prueba_ui` de las mismas áreas; lo rojo entra con su ID (chat maestro, 14/11). Los P2 del lote de las 19 h (B-471 a B-479, B-481) y los del lote de las 13 h del 15/11 (B-511 a B-515) quedan en bugs.md sin cola; B-516 Sin verificar.

Hechos y esperando integrar (no ocupan cola): ninguno. Lo integrado va al Registro de `PROJECT_LOG.md`, no acá.
