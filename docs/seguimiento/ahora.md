# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora

**Cupo VERDE (20/11 ~10 UTC, semanal 32 %, ritmo ~11,5 %/día contra ~13 % del plan): hasta 5 sesiones de Claude a la vez, solo boceto.** (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1 (Opus alto) | B-735 | Escalar una spline con manija (brief `~/coordinador/briefs/E1_B-735.md`); B-463 espera la prueba de E11 en Windows |
| E4 (Sonnet medio) | P-186 | Mosaico de Restricciones automáticas como Fusion (brief `~/coordinador/briefs/E4_P-186.md`) |
| E7 (Sonnet medio) | REPRO-E11 + auditoría UX | Reproducir con eventos simulados B-729, B-730, B-731 (brief `~/coordinador/briefs/E7_repro.md`); incluir Restricciones automáticas (mosaico, P-186) en su prueba; B-734; después recorrer los comandos del boceto buscando tarjetas repetidas (una fila por caso) |
| E8 (Sonnet medio) | P-187 | Cinta de BOCETO como Fusion y personalizable (brief `~/coordinador/briefs/E8_P-187.md`) |
| E3 (Sonnet medio) | P-188 | Texto: UNA tarjeta por tarea (brief `~/coordinador/briefs/E3_P-188.md`) |
| OpenCode | B-682, PREP-OPCIONES-BOCETO, B-684, B-686, P-178, B-670 corriendo; en cola B-687/688/689/691/692, B-671/672/681, PREP tests de cotas, PROYECTAR y comandos | Cola de boceto (vigía); GLM 5.3 primero hasta el 23/11 (AG-21) |
| E11 | — | Paró la noche del 20/11 (driver AMD de la PC en blanco; Gerardo reinicia a la mañana). Pendiente tras el reinicio: B-667, batería del punto 4, B-710; B-690 resuelto (Fusion no permite Perpendicular línea–spline). Tanda: `~/coordinador/casos/e11_noche_19-11.md`. Antes: Tanda esperando su OK: B-619c, B-667 2.º arrastre, B-690 (pasos en `~/coordinador/casos/b690/`), B-463 (puntos y curva de la spline de ajuste en Fusion: `~/coordinador/casos/b463/pasos_fusion.md`) |

**Foco del 19/11 (Gerardo: «que los agentes solo trabajen en boseto»): solo boceto en Ahora y Sigue; sin fecha de corte hasta cerrar el «Listo cuando» de `plan_boceto_perfecto.md`.** Plan: [plan_boceto_perfecto.md](../plan_boceto_perfecto.md).

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 0 | PRUEBA-OPC-2 (E7) | Probar como usuario las 11 opciones que quedan sin prueba en `preparado/opciones_asas_boceto.md`: Insertar DXF, Vectorizar, Perfil giratorio (tolerancia, invertir, solo contorno), Desfase (cadena, topología), Kerning de un par, Boceto 3D |
| 1 | B-667 | Parcial: el 2.º arrastre deforma la spline; E3 desde las 13:13 UTC en ~/OmniCAD-B-667b (Opus alto) |
| 2 | PRUEBA-PROY (hecha por E7: B-684, B-685, B-686 a OpenCode) | Probar como usuario los 5 tipos de PROYECTAR del boceto (Proyectar, Intersecar, Incluir geometría 3D, Perfil giratorio, Curva isoparamétrica): mouse simulado y valores raros contra `docs/fusion_docs` (E7, Sonnet medio; cada falla = fila nueva de boceto; antes, OpenCode prepara los tests que falten) |
| 3 | PRUEBA-CMDS | Probar en la ventana los 61 comandos de la cinta del boceto sin prueba como usuario (lista en `docs/plan_boceto_perfecto.md` › Cobertura; script `scripts/cobertura_boceto.py`): E7 en Linux con `prueba_ui`, E11 con mouse real lo que E7 no pueda; cada falla, fila nueva de boceto |

Esperan a E11 en Windows (sin código por ahora): B-48 (caída nativa con la previa en paralelo) y B-172 (sin la pieza original).

**Meta 30/11 (Gerardo, regla 13): app usable.** Fuera de la cola hasta esa fecha (siguen en sus listas): FL-14, P-159, B-405, B-389, P-134 y todo P2 (P-156 sí entra, Gerardo 15/11).

Sin ítem de prioridad 1 libre: caza automática (`scripts/caza/cazar.py tema` sobre bocetos, sólido, superficie y construir) y `scripts/prueba_ui` de las mismas áreas; lo rojo entra con su ID (chat maestro, 14/11). Los P2 del lote de las 19 h (B-471 a B-479, B-481) y los del lote de las 13 h del 15/11 (B-511 a B-515) quedan en bugs.md sin cola; B-516 Sin verificar.

Hechos y esperando integrar (no ocupan cola): ninguno. Lo integrado va al Registro de `PROJECT_LOG.md`, no acá.
