# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora

**Cupo AMARILLO (19/11 11 UTC, semanal 8 %): 3 sesiones de Claude a la vez, solo boceto.** (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1, E3, E4, E8 | — | Vaciadas y quietas; reciben lo que salga de OpenCode que no cierre (por el chat maestro) |
| OpenCode | B-682, PREP-OPCIONES-BOCETO, B-684, B-686, P-178, B-670 corriendo; en cola B-687/688/689/691/692, B-671/672/681, PREP tests de cotas, PROYECTAR y comandos | Cola de boceto (vigía); GLM 5.3 primero hasta el 23/11 (AG-21) |
| E11 | — | En pausa (Gerardo en la PC). Tanda esperando su OK: B-619c, B-667 2.º arrastre, B-690 |

**Foco del 19/11 (Gerardo: «que los agentes solo trabajen en boseto»): solo boceto en Ahora y Sigue; sin fecha de corte hasta cerrar el «Listo cuando» de `plan_boceto_perfecto.md`.** Plan: [plan_boceto_perfecto.md](../plan_boceto_perfecto.md).

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 0 | B-695 y B-696 (prioridad alta, Gerardo en vivo; E4 o E8, mismo panel Carácter/Texto) | B-695: aviso falso «el cuerpo 'op58.c5' no existe» al editar el texto de un boceto anterior. B-696: el panel Carácter dice «Juli J» y el dibujo muestra «Ceci» |
| 0 | B-699 (E1, Opus alto) | La extrusión da un cuerpo inválido en los casos 138071 y 24822 de la galería (el perfil ya se encuentra; pasa igual sin Rust) |
| 0 | PRUEBA-TEXTO-SIM (E7) | Probar como usuario Texto/Panel Carácter (parámetro, familia, pivote de 6) y Panel Simetría (eje); y revisar las filas «no» viejas de `preparado/opciones_asas_boceto.md` contra los scripts de `prueba_ui` |
| 1 | B-667 | Parcial: el 2.º arrastre deforma la spline; E3 desde las 13:13 UTC en ~/OmniCAD-B-667b (Opus alto) |
| 2 | PRUEBA-PROY (hecha por E7: B-684, B-685, B-686 a OpenCode) | Probar como usuario los 5 tipos de PROYECTAR del boceto (Proyectar, Intersecar, Incluir geometría 3D, Perfil giratorio, Curva isoparamétrica): mouse simulado y valores raros contra `docs/fusion_docs` (E7, Sonnet medio; cada falla = fila nueva de boceto; antes, OpenCode prepara los tests que falten) |
| 3 | PRUEBA-CMDS | Probar en la ventana los 61 comandos de la cinta del boceto sin prueba como usuario (lista en `docs/plan_boceto_perfecto.md` › Cobertura; script `scripts/cobertura_boceto.py`): E7 en Linux con `prueba_ui`, E11 con mouse real lo que E7 no pueda; cada falla, fila nueva de boceto |

Esperan a E11 en Windows (sin código por ahora): B-48 (caída nativa con la previa en paralelo) y B-172 (sin la pieza original).

**Meta 30/11 (Gerardo, regla 13): app usable.** Fuera de la cola hasta esa fecha (siguen en sus listas): FL-14, P-159, B-405, B-389, P-134 y todo P2 (P-156 sí entra, Gerardo 15/11).

Sin ítem de prioridad 1 libre: caza automática (`scripts/caza/cazar.py tema` sobre bocetos, sólido, superficie y construir) y `scripts/prueba_ui` de las mismas áreas; lo rojo entra con su ID (chat maestro, 14/11). Los P2 del lote de las 19 h (B-471 a B-479, B-481) y los del lote de las 13 h del 15/11 (B-511 a B-515) quedan en bugs.md sin cola; B-516 Sin verificar.

Hechos y esperando integrar (no ocupan cola): ninguno. Lo integrado va al Registro de `PROJECT_LOG.md`, no acá.
