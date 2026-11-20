# Ahora y Sigue

La única cola de trabajo (plan de reorganización del 2026-11-13). Lo que no está acá no se toma.
Una sesión toma el siguiente de «Sigue» recién cuando cerró el suyo (integrado o devuelto a su lista con una nota).
La columna «Prioridad» de las listas ya no ordena: ordena este archivo. Lo actualiza el coordinador al integrar.

## Ahora

**Cupo VERDE (20/11 ~10 UTC, semanal 32 %, ritmo ~11,5 %/día contra ~13 % del plan): hasta 5 sesiones de Claude a la vez, solo boceto.** (uno por sesión)

| Sesión | Ítem | Qué |
|---|---|---|
| E1 (Sonnet medio) | — libre | B-753/754/755 y B-738 integrados (B-738 cerrado con el ajuste empírico); sin ítem en Sigue (pasa B-766) |
| E4 (Sonnet medio) | B-734 y B-730 | Texto: clic en vista 3D y Desagrupar (B-697 cerrado; brief `~/coordinador/briefs/E4_B-734_B-730.md`) |
| E7 (Sonnet medio) | En espera (cupo 5) | Prueba como usuario de lo integrado el 20/11 y PRUEBA-OPC-2 (brief `~/coordinador/briefs/E7_siguiente.md`) |
| E8 (Sonnet medio) | B-782, después B-512 (resto) | B-772 integrado; Revolución sin boceto y casos de B-512 (brief `E8_proximo.md`) |
| E3 (Sonnet medio) | B-778 (B-764 integrado; arreglar test_b445 por B-762) | Navegador visible en el boceto (brief `E3_B-778.md`) |
| E6 (Sonnet medio) | B-781 y B-679 | Main verde: operación elegida a mano en Extruir y test intermitente del plástico (B-775 integrado; brief `E6_proximo.md`) |
| OpenCode | B-682, PREP-OPCIONES-BOCETO, B-684, B-686, P-178, B-670 corriendo; en cola B-687/688/689/691/692, B-671/672/681, PREP tests de cotas, PROYECTAR y comandos | Cola de boceto (vigía); GLM 5.3 primero hasta el 23/11 (AG-21) |
| E11 | — | Paró la noche del 20/11 (driver AMD de la PC en blanco; Gerardo reinicia a la mañana). Pendiente tras el reinicio: batería del punto 4, B-710; B-690 resuelto (Fusion no permite Perpendicular línea–spline). Tanda: `~/coordinador/casos/e11_noche_19-11.md`. Antes: Tanda esperando su OK: B-619c, B-667 2.º arrastre, B-690 (pasos en `~/coordinador/casos/b690/`), B-463 (puntos y curva de la spline de ajuste en Fusion: `~/coordinador/casos/b463/pasos_fusion.md`) |

**Foco del 19/11 (Gerardo: «que los agentes solo trabajen en boseto»): solo boceto en Ahora y Sigue; sin fecha de corte hasta cerrar el «Listo cuando» de `plan_boceto_perfecto.md`.** Plan: [plan_boceto_perfecto.md](../plan_boceto_perfecto.md).

## Sigue (en orden)

| # | Ítem | Qué |
|---|---|---|
| 00 | B-778 | Boceto: el Navegador se pliega y queda vacío al entrar a un boceto (video 18:07; prioridad 1; revierte parte de P-195) |
| 0 | PRUEBA-OPC-2 (E7) | Probar como usuario las 11 opciones que quedan sin prueba en `preparado/opciones_asas_boceto.md`: Insertar DXF, Vectorizar, Perfil giratorio (tolerancia, invertir, solo contorno), Desfase (cadena, topología), Kerning de un par, Boceto 3D |
| 1 | B-738 | Parcial con datos de Fusion de E11 (giros 0/30/60/90°, `~/coordinador/casos/b463/e11_b738_giros.md`): ajustar `escala_manija` a esa dependencia de período 90° (E6 o E1, Opus alto, tras su ítem actual) |
| 2 | PRUEBA-PROY (hecha por E7: B-684, B-685, B-686 a OpenCode) | Probar como usuario los 5 tipos de PROYECTAR del boceto (Proyectar, Intersecar, Incluir geometría 3D, Perfil giratorio, Curva isoparamétrica): mouse simulado y valores raros contra `docs/fusion_docs` (E7, Sonnet medio; cada falla = fila nueva de boceto; antes, OpenCode prepara los tests que falten) |
| 3 | PRUEBA-CMDS | Probar en la ventana los 61 comandos de la cinta del boceto sin prueba como usuario (lista en `docs/plan_boceto_perfecto.md` › Cobertura; script `scripts/cobertura_boceto.py`): E7 en Linux con `prueba_ui`, E11 con mouse real lo que E7 no pueda; cada falla, fila nueva de boceto |

Esperan a E11 en Windows (sin código por ahora): B-48 (caída nativa con la previa en paralelo) y B-172 (sin la pieza original).

**Meta 30/11 (Gerardo, regla 13): app usable.** Fuera de la cola hasta esa fecha (siguen en sus listas): FL-14, P-159, B-405, B-389, P-134 y todo P2 (P-156 sí entra, Gerardo 15/11).

Sin ítem de prioridad 1 libre: caza automática (`scripts/caza/cazar.py tema` sobre bocetos, sólido, superficie y construir) y `scripts/prueba_ui` de las mismas áreas; lo rojo entra con su ID (chat maestro, 14/11). Los P2 del lote de las 19 h (B-471 a B-479, B-481) y los del lote de las 13 h del 15/11 (B-511 a B-515) quedan en bugs.md sin cola; B-516 Sin verificar.

Hechos y esperando integrar (no ocupan cola): ninguno. Lo integrado va al Registro de `PROJECT_LOG.md`, no acá.
