# Corrida nocturna del 2026-11-05

Pedido de Gerardo (2026-11-05, noche): que trabajen solos Qwen3.8-Flash (Qoder CLI, gratis) y GPT-6.1 Sol (OpenCode;
tiene un tope de 5 horas y puede no terminar). Una sesión de Claude (Opus 5, esfuerzo alto) hace de coordinador
nocturno: lanza, revisa, commitea lo verde y deja el informe para la mañana.

## Informe de la mañana

Sin rechazos. Se cumplieron las tres líneas. La PC se reinició a las 04:29: se cortaron la tanda 4 de Qwen y la revisión de C11, y las dos se retomaron.

| Tanda o bug | Estado | Commit | Tests |
|---|---|---|---|
| Qwen 1: B-211, B-210 | Resueltos | `799d6f6` (main) | 632 + 303 |
| Qwen 2: B-216, B-214 | Resueltos; nuevo B-219 | `7e95678` (main) | 1105 + 444 |
| Qwen 3: B-217, B-209 | Resueltos; nuevo B-220 | `64a79f0` (main) | 1628 + 1095 |
| Qwen 4: H-92, H-86 | Resueltos | `ba26cc0` (main) | 894 + 866 + 833 |
| Qwen 5 | No se lanzó: pasa a hoy | — | — |
| Sol: B-212, B-215, B-208 | Resueltos | `32a9c4c`, `9eeb89f`, `a8816d5` (rama Sol) | 938 + 601 · 685 + 522 · 605 + 331 |
| Sol: B-213 | Parcial de noche; lo terminó otra sesión a las 07:49 | `95d19f2`, `4e89932` (rama Sol) | 1356 |
| Sol: B-206 | Parcial: el círculo inclinado con conicidad sigue en xfail | `bd7e3e5` (rama Sol) | 2073 |
| CodeBuddy: H-87, H-100, H-102, H-93, H-74, H-103, CF-11, H-71, H-85, H-104 | Resueltos | `64eb920` … `2518829` (rama CodeBuddy) | 270 a 2500 por tanda |
| CodeBuddy C11: CF-8 | Parcial (dos opciones hechas) | `7687fab` (rama CodeBuddy) | 1595 |

**Ramas sin fusionar.** `sol-geometria-nocturna` (6 commits) y `codebuddy-nocturna` (22 commits). Para fusionarlas:
- resolver los conflictos de `nucleo/solidos_crear.py` (Sol B-213/B-215 contra Qwen B-216/B-214) y `timeline/ops_solido.py` (CodeBuddy contra `main`), más los docs de seguimiento;
- correr la suite completa sobre lo fusionado;
- tener el «sí» de Gerardo.

**Cambian proyectos viejos:**
- una «Distancia» del barrido mayor que 1 ahora da error (B-211);
- la Red invertida puede cambiar de lado (B-216);
- «Estirar» y «Cadena tangente» cambian la forma (B-209, B-217);
- la cadena del barrido ahora encadena curvas de boceto (H-93).

**Cierre completo:** Hecho a las 12:28 sobre `ba26cc0` (`evidencias/cierre_2026-11-06/`):
- ruff limpio y suite verde (unos 9100 tests). `parte_04` pasó el tope de 900 s y se rehízo en dos mitades. Un test de la previa aislada falló por falta de memoria de OpenBLAS y pasó solo (20/20).
- Humo OK. Piezas con foco real (`registro_uso`, `asistente`) sin ✗.
- Piezas de ventana: 14 ✗ en 5 piezas. Una venía del defecto nuevo de H-86 (`solido_crear` suponía «media longitud»): se arregló la prueba. Las demás ya tienen fila (H-85, H-88, H-89, H-90, H-95, H-97, H-99; B-208 y B-215 resueltos en la rama de Sol). Nueva: B-221 (silueta roja de la copia suprimida en PAT-3).

**Modelos de CodeBuddy:**
- deepseek-v4.1-flash: la 1.ª tanda se cortó dos veces sin informe; después anduvo rápido y bien (C3, C5, C7, C9, C11; de 8 a 20 min).
- hy3: muy bueno y rápido (de 8 a 28 min). Dos fallas, las dos arregladas en la revisión: normalizó finales de línea (C8) y regeneró la doc desde `main` (C2).

**Uso y ahorro:**
- Tokens: Sol usó 1,31 M de entrada (+40,0 M de caché) y 106 k de salida. A precios de Claude Opus 5 serían unos US$ 29 (entrada $5/M, salida $25/M, caché $0,50/M). Qwen y CodeBuddy no dejan registro de tokens.
- Plan de Claude para coordinar: semanal del 20 % al 22 %.

⚠ A las 22:36 el coordinador lanzó GLM-5.3-Flash por error, sin autorización. Se cortó sin tocar archivos.
⚠ En el worktree de Sol hay cambios sin commitear de otra sesión (H-101, B-195). No se tocaron.
⚠ Qwen terminó 3 de sus 4 tandas sin escribir el informe; el coordinador cerró la revisión.

## Plan

| Línea | Quién | Dónde | Qué | Cómo se lanza |
|---|---|---|---|---|
| A | Qwen3.8-Flash en Qoder CLI | `main`, en `D:\PROGRAMA` | las 5 tandas de [arreglos_qwen.md](arreglos_qwen.md), en orden | `qodercli -p --dangerously-skip-permissions -w D:/PROGRAMA "<texto>"` (sin `-m`: el modelo es `qfmodel` en la config de Qoder) |
| B | GPT-6.1 Sol en OpenCode | rama `sol-geometria-nocturna`, worktree `D:\PROGRAMA-sol` | bugs de geometría difícil, uno por corrida: B-212, B-215, B-213, B-208 | `opencode run -m openai/gpt-6.1-sol --variant high "<texto>"` con la carpeta del worktree |

Las dos líneas corren en paralelo porque no comparten árbol de trabajo. Los comandos pesados de las dos pasan por
`scripts/turno.py`, que los pone en fila en toda la PC. La rama de Sol **no se fusiona de noche**: la revisa y la
fusiona el coordinador de día, con el «sí» de Gerardo.

### Texto para Qwen (línea A), una vez por tanda

```
TANDA = <N>
Leé docs/arreglos_qwen.md y seguí al pie de la letra la sección «## Prompt para el agente» (el bloque de texto completo) para esa tanda.
```

### Texto para Sol (línea B), una vez por bug

```
BUG = <ID>
ANTES DE TODO: invocá las skills /fable-method y /ponytail (y /plan-then-do, /tool-calling-guard, /verify-before-commit); al final /ponytail-review. Si no existen, seguí igual: el cambio más chico que arregla el bug entero, sin dependencias nuevas, leé antes de editar, nunca "listo" sin la salida real.
PROYECTO: OmniCAD, CAD 3D paramétrico en Python + OpenCascade que copia Fusion 360. Estás en un worktree de git (rama sol-geometria-nocturna); el código está en clon/. Leé AGENTS.md. Todo en español; mm y grados.
QUÉ: arreglá BUG. Detalle en docs/seguimiento/bugs.md (fila y sección «Detalle»: causa probable con archivo:línea, cómo reproducir y prueba propuesta) y en el informe de la auditoría que lo encontró (docs/auditoria_revolucion_barrido_solevacion.md o docs/auditoria_nervio_red_repujado.md). Antes de decidir el comportamiento, leé la ayuda de Fusion: D:/PROGRAMA/clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar <palabras> -s fusion-model (o -s fusion-patch), y ver "<título>" -s <carpeta>.
REGLAS: (1) test de la «Prueba propuesta» primero, con su salida en rojo; después el arreglo y la salida en verde. (2) Buscá los gemelos antes de editar: la previa (ui/comando.py, nucleo/previa*), la versión de superficie (nucleo/superficies.py, timeline/ops_superficie.py), OmniKernel (nucleo/omnikernel/) y la API (clon/omnicad/api/); listalos en el informe. (3) Tests: los del área MÁS todos los que salen de grep -l "<función que tocaste>" clon/tests/test_*.py; desde clon/: D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest <archivos> -q -p no:cacheprovider, en grupos de menos de 900 s. (4) Arreglá lo que marque tu /ponytail-review. (5) Si OpenCascade no sale en dos intentos, pará y dejá la fila en «Parcial» con lo que falta. (6) No commitees, no hagas git stash, checkout ni reset; no corras la suite completa ni la prueba de humo.
AL RESOLVER: borrá la fila de bugs.md, su «Detalle» y su ID en docs/seguimiento/README.md; viñeta en «## Registro» de PROJECT_LOG.md: «2026-11-05 · BUG (OpenCode con GPT-6.1 Sol, noche)».
INFORME: en docs/corrida_nocturna_2026-11-05.md, sección «## Informe Sol · BUG» arriba de «## Prompt para el agente»: estado, ayuda de Fusion, cambios (archivo:línea), gemelos, test rojo y verde, salida de ruff y de los grupos de tests, salida completa de /ponytail-review, ⚠ lo no verificado.
```

## Uso y ahorro

Plan de Claude (coordinador nocturno, `get_usage`):

| Hora | 5 horas | Semanal |
|---|---|---|
| 22:46 (inicio) | 58 % (se renueva 23:20) | 20 % |
| 00:50 | 3 % (ventana nueva, se renueva 04:20) | 20 % |
| 03:23 | 7 % | 21 % |
| 09:45 (cierre) | 9 % (ventana nueva tras el reinicio) | 22 % |

Corridas (tokens de `opencode stats` / sesiones de Qoder; «sin dato» si no se pudo sacar):

| Hora | Modelo | Tarea | Duración | Tokens entrada / salida | Resultado |
|---|---|---|---|---|---|
| 22:34 | Qwen en Qoder con `-m Qwen3.8-Flash` | tanda 1 | 6 s | 0 | no corrió: «not available, using auto» (el modelo se llama `qfmodel` en la config; se corre sin `-m`) |
| 22:35 | Qwen en OpenCode Go | tanda 1 | 8 s | 0 | no corrió: sin suscripción a OpenCode Go |
| 22:36 | GLM-5.3-Flash free (OpenCode) | tanda 1 | 2 min | 0 | ⚠ lanzado por error del coordinador (cambio de modelo no autorizado); límite gratis alcanzado, cortado sin tocar archivos |
| 22:34 | GPT-6.1 Sol (OpenCode) | B-212 | 17 min | 315 k (+12,9 M caché) / 17 k (+6 k razonamiento) | commit `32a9c4c` en `sol-geometria-nocturna` (938 + 601 tests verdes) |
| 23:02 | GPT-6.1 Sol (OpenCode) | B-215 (2 corridas: la 1.ª cortada a los 25 min esperando turno) | 50 min | 288 k (+9,1 M caché) / 14 k (+8 k razonamiento) | commit `9eeb89f` en `sol-geometria-nocturna` (685 + 522 tests verdes; la 2.ª corrida también se cortó esperando turno y los tests finales los corrió el coordinador) |
| 22:41 | Qwen3.8-Flash (Qoder, `qfmodel`) | tanda 1 (B-211, B-210) | 71 min | sin dato (las sesiones de Qoder no guardan tokens) | terminó sin informe: dejó los tests en cola y salió; se retomó la sesión |
| 22:50 | deepseek-v4.1-flash (CodeBuddy) | C1 (B-189, H-87) | 45 min (tope) | sin dato (salida json vacía al cortar) | cortado con H-87 hecho y B-189 a medias; se retomó la sesión |
| 23:35 | deepseek-v4.1-flash (CodeBuddy) | C1, continuación | 45 min (tope) | sin dato | otra vez cortado, sin informe; el coordinador revisó (550 + 728 verdes) y commiteó `64eb920` en `codebuddy-nocturna` (H-87; B-189 ya estaba resuelto en HEAD, queda su test; nuevos B-218 y H-102) |
| 00:00 | GPT-6.1 Sol (OpenCode) | B-213 | 19 min | 265 k (+5,5 M caché) / 18 k (+5 k razonamiento) | Parcial: Nervio arreglado, Red pendiente (2 tests en xfail estricto); commit `95d19f2` (689 + 2 xfail y 522 verdes) |
| 23:53 | Qwen3.8-Flash (Qoder) | tanda 1, sesión retomada | 55 min | sin dato | informe escrito; commit `799d6f6` en `main` (632 + 303 verdes, más 2505 de Qwen) |
| 00:39 | hy3 (CodeBuddy) | C2 (H-100) | 28 min | sin dato (salida de texto, sin tokens) | commit `2329d0f` en `codebuddy-nocturna` (538 + 842 verdes; el coordinador regeneró `herramientas.md` desde el worktree) |
| 01:10 | deepseek-v4.1-flash (CodeBuddy) | C3 (H-102) | 17 min | sin dato | commit `04bfa86` en `codebuddy-nocturna` (1505 + 787 verdes) |
| 01:41 | hy3 (CodeBuddy) | C4 (H-93) | 11 min | sin dato | commit `dade722` en `codebuddy-nocturna` (1519 + 1007 verdes) |
| 00:59 | Qwen3.8-Flash (Qoder) | tanda 2 (B-216, B-214) | 68 min | sin dato | commit `7e95678` en `main` (1105 + 444 verdes); nuevo B-219 |
| 02:09 | Qwen3.8-Flash (Qoder) | tanda 3 (B-217, B-209) | 73 min | sin dato | commit `64a79f0` en `main` (1628 + 1095 verdes); nuevo B-220 |
| 01:59 | deepseek-v4.1-flash (CodeBuddy) | C5 (H-74) | 8 min | sin dato | commit `75f541d` en `codebuddy-nocturna` (1280 + 268 verdes); la revisión halló una duplicación: fila H-103 |
| 02:11 | hy3 (CodeBuddy) | C6 (H-103) | 8 min | sin dato | commit `2d4b769` en `codebuddy-nocturna` (1498 verdes) |
| 02:22 | deepseek-v4.1-flash (CodeBuddy) | C7 (CF-11) | 14 min | sin dato | commit `23dd4c5` en `codebuddy-nocturna` (1402 + 763 verdes) |
| 02:46 | hy3 (CodeBuddy) | C8 (H-71) | 15 min | sin dato | commit `7db9d93` en `codebuddy-nocturna` (867 + 524 verdes); el coordinador deshizo el cambio de finales de línea de 2 archivos |
| 03:14 | deepseek-v4.1-flash (CodeBuddy) | C9 (H-85) | 20 min | sin dato | commit `af61543` en `codebuddy-nocturna` (1133 verdes); nuevo H-104 |
| 03:37 | hy3 (CodeBuddy) | C10 (H-104) | 10 min | sin dato | commit `2518829` en `codebuddy-nocturna` (1069 verdes) |
| 03:50 | deepseek-v4.1-flash (CodeBuddy) | C11 (CF-8, dos opciones) | 10 min | sin dato | revisión cortada por el reinicio de las 04:29; repetida a las 07:05: commit `7687fab` (283 + 362 + 347 + 603 verdes). CF-8 sigue Parcial |
| 03:35 | Qwen3.8-Flash (Qoder) | tanda 4 (H-92, H-86) | 54 min hasta el reinicio | sin dato | cortada por el reinicio de la PC (04:29); retomada a las 07:03 con su sesión |
| 07:03 | Qwen3.8-Flash (Qoder) | tanda 4 (retomada) | 60 min (tope) | sin dato | terminó el código y los tests sin escribir el informe; el coordinador revisó (2593 verdes), borró un bloque duplicado y commiteó |
| 00:41 | GPT-6.1 Sol (OpenCode) | B-208 | 14 min | 204 k (+6,2 M caché) / 15 k (+5 k razonamiento) | commit `a8816d5` (605 + 331 verdes) |
| 01:01 | GPT-6.1 Sol (OpenCode) | B-206 (resto) | 10 min | 242 k (+6,3 M caché) / 13 k (+5 k razonamiento) | Parcial: rectángulo inclinado con conicidad anda, círculo no (xfail estricto); commit `bd7e3e5` (2073 verdes). Fin de la línea B: 6 corridas de 6 |

