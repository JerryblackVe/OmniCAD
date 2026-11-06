# Corrida nocturna del 2026-11-05

Pedido de Gerardo (2026-11-05, noche): que trabajen solos Qwen3.8-Flash (Qoder CLI, gratis) y GPT-6.1 Sol (OpenCode;
tiene un tope de 5 horas y puede no terminar). Una sesión de Claude (Opus 5, esfuerzo alto) hace de coordinador
nocturno: lanza, revisa, commitea lo verde y deja el informe para la mañana.

## Plan

| Línea | Quién | Dónde | Qué | Cómo se lanza |
|---|---|---|---|---|
| A | Qwen3.8-Flash en Qoder CLI | `main`, en `D:\PROGRAMA` | las 5 tandas de [arreglos_qwen.md](arreglos_qwen.md), en orden | `qodercli -p --dangerously-skip-permissions -m Qwen3.8-Flash -w D:/PROGRAMA "<texto>"` |
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
| 00:41 | GPT-6.1 Sol (OpenCode) | B-208 | 14 min | 204 k (+6,2 M caché) / 15 k (+5 k razonamiento) | commit `a8816d5` (605 + 331 verdes) |
| 01:01 | GPT-6.1 Sol (OpenCode) | B-206 (resto) | 10 min | 242 k (+6,3 M caché) / 13 k (+5 k razonamiento) | Parcial: rectángulo inclinado con conicidad anda, círculo no (xfail estricto); commit `bd7e3e5` (2073 verdes). Fin de la línea B: 6 corridas de 6 |

## Prompt para el agente

Entregado el 2026-11-05. Modelo sugerido: Opus 5, esfuerzo alto (coordinador nocturno; la geometría de Sol se revisa a fondo).

```text
ARRIBA DE TODO: invocá con la herramienta Skill fable-method y ponytail; usá plan-then-do, tool-calling-guard y verify-before-commit; ponytail-review sobre cada tanda o bug antes de commitear. Sos el COORDINADOR NOCTURNO de OmniCAD (repo D:\PROGRAMA). Gerardo duerme: no le preguntes nada; decidí con estas reglas y dejá todo escrito. Leé CLAUDE.md y AGENTS.md (las reglas del coordinador valen para vos esta noche).

TU TRABAJO: correr las dos líneas de docs/corrida_nocturna_2026-11-05.md (sección «Plan»), revisar cada entrega como coordinador, commitear lo verde y dejar el informe de la mañana. Gerardo te autoriza a commitear esta noche lo que verifiques (git add explícito, archivo por archivo; nunca privado/, analisis/, evidencias/, docs/fusion_docs/, PROJECT_CONTEXT.md ni .agents/). Nunca push.

PREPARAR
1. git status limpio en main (si no, anotalo y seguí con lo tuyo). Creá el worktree de Sol: git worktree add D:/PROGRAMA-sol -b sol-geometria-nocturna main. Comprobá que los tests del worktree importan su propio código: desde D:/PROGRAMA-sol/clon, D:/PROGRAMA/clon/.venv/Scripts/python.exe -c "import omnicad; print(omnicad.__file__)" tiene que mostrar D:\PROGRAMA-sol. Si no, anotalo y corré la línea B igual, pero con PYTHONPATH apuntando al worktree.
2. Carpeta de registros: evidencias/nocturna_2026-11-05/ (un .log por corrida).

LÍNEA A (Qwen, main): para N = 1 a 5, en orden:
- Lanzá en segundo plano (run_in_background), con tope de 90 minutos: timeout 5400 qodercli -p --dangerously-skip-permissions -m Qwen3.8-Flash -w D:/PROGRAMA "<Texto para Qwen con TANDA = N>" > evidencias/nocturna_2026-11-05/qwen_tanda_N.log 2>&1. Si acepta --reasoning-effort, usá el nivel más alto que liste --help.
- Cuando termine, revisá como coordinador: git diff; el «## Informe tanda N» de docs/arreglos_qwen.md (gemelos listados, test rojo y verde, salida de /ponytail-review con sus arreglos); ruff check .; los «Tests obligatorios» de la tanda MÁS todos los archivos de clon/tests que usan lo tocado (grep -l con cada función cambiada), con ../scripts/turno.py en grupos que terminen en menos de 900 s (si uno se corta, partilo: un corte no es verde); si tocó la ventana, la pieza en --ventana minimizada y mirá la captura con Read.
- Verde: commit con mensaje «Qwen tanda N: <IDs> (...)» y los IDs. Rojo: una sola vuelta de arreglo: timeout 3600 qodercli -p --dangerously-skip-permissions -c -m Qwen3.8-Flash -w D:/PROGRAMA "<qué falló, con la salida real>". Si sigue rojo: guardá git diff > evidencias/nocturna_2026-11-05/qwen_tanda_N_rechazada.patch, restaurá SOLO los archivos de esa tanda con git checkout -- <archivo> (nunca stash ni reset), anotá en el informe y seguí con la tanda siguiente.
- Si Qoder no responde (log en 0 bytes, sin CPU ni archivos tocados durante 25 minutos), cortá ese proceso y seguí.

LÍNEA B (Sol, worktree D:/PROGRAMA-sol), en paralelo con la A:
- Para BUG = B-212, B-215, B-213, B-208, en ese orden, uno por corrida: en segundo plano, con la carpeta del worktree como directorio de trabajo, timeout 1500 opencode run -m openai/gpt-6.1-sol --variant high "<Texto para Sol con BUG = ...>" > D:/PROGRAMA/evidencias/nocturna_2026-11-05/sol_<BUG>.log 2>&1. Antes de cada corrida, copiá los archivos que va a tocar (cp a evidencias/nocturna_2026-11-05/respaldo_<BUG>/).
- Si se corta por tiempo con avance real, una segunda corrida «seguí con BUG desde donde quedaste». Si el log dice que se acabó el cupo o el límite de uso, la línea B termina: anotalo.
- Revisión igual que en la A, pero dentro del worktree (los tests desde D:/PROGRAMA-sol/clon con el Python de D:/PROGRAMA/clon/.venv). Verde: commit en la rama sol-geometria-nocturna. Rojo: una vuelta de arreglo con el mismo texto más lo que falló; si sigue rojo, guardá el parche, restaurá esos archivos y anotalo.
- NO fusiones la rama en main.

CIERRE (cuando terminen las dos líneas, o a las 07:00 si siguen corriendo)
1. En main: el cierre completo con scripts/cierre_completo.sh (suite completa, prueba de humo y piezas; una sola corrida pesada a la vez). Lo rojo va a docs/seguimiento/ con su ID; lo verde se borra de docs/auditorias/prueba_nocturna_2026-10-31.md.
2. PROJECT_LOG.md (Registro): una viñeta por tanda y bug con su commit, y si el modelo alcanzó.
3. Refrescá la página de seguimiento (CLAUDE.md › «Página de seguimiento», pasos 1 a 3). Cuando cierres este prompt, borrá esta sección «## Prompt para el agente» y su fila de «Prompts guardados» en docs/seguimiento/README.md, y refrescá datasets/prompts.
4. Informe de la mañana en este documento, sección «## Informe de la mañana» arriba de las demás: tabla corta (tanda o bug · estado · commit · tests), lo rechazado y por qué, cómo quedó la rama de Sol (commits, qué falta para fusionar), resultado del cierre completo, y ⚠ lo que no se pudo. Máximo una pantalla.
5. Commit final de docs. Contexto: si llegás al 60 %, cerrá con el informe y pará (regla de CLAUDE.md).

PROHIBIDO: push, git stash, git reset --hard, borrar ramas o worktrees ajenos, gastar en APIs pagas, tocar archivos fuera de D:\PROGRAMA y D:\PROGRAMA-sol.
```
