# Plan de velocidad: pruebas y procesos más rápidos

Pedido de Gerardo (2026-11-06): «todo tarda mucho: buscar alternativas más eficientes, de mejor calidad y que tarden
mucho menos». Este documento es la especificación; el estado de cada paquete vive en `docs/seguimiento/mejoras.md`
cuando se lance.

## Metas

| Qué | Hoy | Meta |
|---|---|---|
| Cierre completo (suite + piezas + humo) | 2 h 45 min | menos de 45 min |
| Probar un arreglo durante el día | a ojo, 5–15 min | menos de 5 min, con los tests que de verdad tocan lo cambiado |
| PC quieta para el humo | sí, con espera | no: corre minimizado, sin mover el cursor real |
| Ítems de agentes a la vez | 1 por carpeta, ~25 min cada uno | 2 en paralelo, cada uno en su worktree |

## Lo medido (no supuesto)

Fuente: `evidencias/cierre_2026-11-06/resumen.txt` y la hora de cada archivo de esa carpeta.

- **Suite: 69 min** (09:43 → 10:52), en 6 tandas **una detrás de otra y en un solo proceso**. La tanda 4 pasó los 900 s
  de `turno.py`, se cortó y hubo que repetirla en dos mitades (`p04a`, `p04b`). Las tandas se arman por cantidad de
  archivos (`split -n l/6` en `scripts/cierre_completo.sh`), no por tiempo: salen de 3 a 15 min.
- **Piezas de ventana: 94 min** (10:52 → 12:26), las 51 de `PIEZAS` en `scripts/prueba_ui/todo.py`, de a una.
- **Humo y piezas con foco: 2 min**, pero esperan que la PC lleve 2 min sin uso (`espera_ocio` en el cierre).
- **La PC tiene 12 núcleos y 13 GB**: la suite usa uno. Cada pytest reserva ~1 GB (`scripts/turno.py`, línea 3).
- **Importar la app no es el problema**: núcleo + timeline 0,9 s y la ventana otros 0,9 s.
- **No hay plugins de pytest** fuera de pytest 9.1.1 (`pip list`): ni ejecución en paralelo ni selección por impacto.
- 381 archivos de test, ~5400 funciones; 195 archivos abren la ventana o una `QApplication`.
- La prueba de humo mueve el cursor real en 7 lugares (`clon/omnicad/prueba_humo.py`, `QTest.mouseMove`/`QCursor.setPos`).
- **No medido todavía**: qué tests son los lentos. Ese es el paquete A.

## Paquetes (en orden)

### A. Medir los tests lentos
- Qué: el cierre agrega `--durations=0 --junitxml` a cada tanda; `scripts/tiempos.py` junta todo en
  `evidencias/tiempos.json` (segundos por test y por archivo) y lista los 30 más lentos.
- Listo cuando: existe el ranking real de una suite entera y el tiempo por archivo queda guardado para el paquete B.
- Ejecutor: CodeBuddy deepseek (mecánico), revisa el coordinador.
- Hecho (2026-11-06, P-59): CodeBuddy deepseek-v4.1-flash; falta el ranking de una suite entera (lista nocturna §3t).

### B. La suite en paralelo
- Qué: `pytest-xdist` (pide permiso para instalar) con 4 procesos (`-n 4 --dist loadfile`, un archivo entero por
  proceso); el tope de `turno.py` sube para esa corrida (4 × ~1 GB). Las tandas se arman por **tiempo medido** (A), no
  por cantidad, para que ninguna se acerque a los 900 s.
- Listo cuando: la suite entera pasa igual de verde que en serie, en menos de 25 min, sin cortes por plazo, y el pico
  de memoria medido queda por debajo de 8 GB.
- Ejecutor: CodeBuddy hy3; Opus revisa los tests que fallen solo en paralelo (son bugs de test: archivos o ajustes
  compartidos; se arreglan con `tmp_path`, nunca salteando el test).
- Hecho (2026-11-06, P-63): Sol en OpenCode (se le acabaron los 25 min antes de medir; midió el coordinador). Medido de día con 22 archivos (1079 tests): serie 1167 s, 3 rojos por `MemoryError` del tope de 3000 MB de `turno.py`; `-n 2` 526 s, todo verde, pico de 3,5 GB en total. `-n 4` sin medir: de día había de 1 a 4 GB libres y la PC se colgó una vez (no durante esta prueba). Tope que aguanta esta PC: se mide la primera noche; si pasa 8 GB, `-n 3`.

### C. Correr solo lo afectado durante el día
- Qué: `scripts/tests_afectados.py`: de `git diff` saca los módulos tocados, y por el grafo de imports (sin instalar
  nada) los tests que los usan, más las piezas de ventana que tocan esa área (mapa pieza → módulos en `todo.py`).
  Agentes y coordinador corren eso en vez de elegir tests a ojo. La suite entera queda para el cierre.
- Listo cuando: para los últimos 10 commits, la lista que da incluye todos los tests que esos commits cambiaron o
  que fallaron en su momento, y tarda menos de 5 s en armarse.
- Ejecutor: CodeBuddy hy3.
- Hecho (2026-11-06, P-62): Sol en OpenCode; el coordinador afinó las referencias a docs. Límite: lo que se usa sin import (el humo por `OmniCAD.py`, `importlib`) no se ve; el cierre completo sigue siendo la red.

### D. Humo sin cursor real
- Qué: los 7 movimientos del cursor real de `prueba_humo.py` pasan a eventos simulados (`_mover`, como pide AGENTS.md
  para pasos nuevos). El humo corre minimizado y sin esperar PC quieta. `registro_uso` y `asistente` (foco real de
  Windows) se revisan igual; si no se pueden simular, siguen de noche.
- Listo cuando: el humo da «TODO OK» con `--ventana minimizada` mientras se usa la PC, y el cierre ya no espera ocio
  para el humo.
- Ejecutor: CodeBuddy hy3.
- Hecho (2026-11-06, P-60): lo empezó CodeBuddy hy3 (se quedó sin cupo) y lo terminó Sol en OpenCode (`openai/gpt-6.1-sol --variant high`); el coordinador sacó `setActiveWindow` en minimizada (robaba el foco).

### E. Piezas de ventana en paralelo
- Qué: `todo.py --paralelo 3`: tres piezas a la vez, cada una en su ventana minimizada, las más largas primero.
  Empieza con 2 y sube a 3 si el pico de memoria y la placa de video integrada aguantan.
- Listo cuando: las 51 piezas dan las mismas ✗ que en serie, en menos de 40 min.
- Ejecutor: CodeBuddy hy3.

### F. Acelerar los tests más lentos
- Qué: con el ranking de A, los 30 más lentos: la ventana y las piezas base se crean una vez por archivo
  (`scope="module"`) en vez de una por test; lo que tarda más de 10 s y no aporta en el día lleva la marca `lento`.
  **No se cambia qué comprueba ningún test.**
- Listo cuando: esos 30 suman al menos un 40 % menos de tiempo, con los mismos tests y las mismas aserciones.
- Ejecutor: CodeBuddy hy3; Opus alto revisa cada cambio de fixture (un fixture compartido mal hecho esconde bugs).

### G. Dos agentes a la vez
- Qué: `scripts/worktree_item.sh <ID>` crea un worktree y una rama por ítem y los borra al fusionar. Con B y C cada
  agente verifica en minutos sin pisar la fila de `turno.py`.
- Listo cuando: dos ítems corren a la vez en dos worktrees, cada uno cierra con su commit y se fusionan sin choques.
- Ejecutor: CodeBuddy deepseek (script chico); el coordinador cambia la regla del loop en `CLAUDE.md`.
- Hecho (2026-11-06, P-64): `bash scripts/worktree_item.sh crear|borrar <ID>` (rama `item/<ID>`, carpeta `<repo>-<ID>`; borra solo lo suyo, limpio y ya fusionado). Lo escribió Sol (sin cupo antes de probarlo); GLM 5.3 no llegó a cambiar nada en 25 min; el coordinador arregló el test y lo probó en el repo real.

## Orden

1. **A** (sin instalar nada) y **D** (lo que más molesta: la PC quieta) en paralelo, cada uno en su worktree.
2. **C** (gana tiempo todos los días).
3. **B** cuando Gerardo apruebe instalar `pytest-xdist`.
4. **E**, **F**, **G**.

## Riesgos

- **Tests que dependen del orden o comparten archivos** fallan solo en paralelo. Se arreglan como bugs de test; la
  suite en serie sigue disponible hasta que la paralela esté verde dos noches seguidas.
- **Memoria (13 GB)**: 4 procesos + piezas pueden colgar la PC. Se mide el pico en cada paso y `turno.py` mantiene un
  tope.
- **La selección por impacto se puede saltear un test.** La suite entera sigue corriendo en cada cierre: es la red.
- **Placa de video integrada** con varias ventanas OpenGL a la vez: se empieza con 2 piezas en paralelo.
- **Acelerar un test sin cambiar qué prueba**: todo cambio de fixture lo revisa Opus contra el diff de aserciones.

## Prompt para el agente

Entregado el 2026-11-06 (paquete E). Modelo sugerido: GLM en CodeBuddy, esfuerzo por defecto (`codebuddy -p --permission-mode bypassPermissions --model glm-5.3`), en el worktree `D:/PROGRAMA-velE` con `timeout 1500`; revisa, commitea y fusiona el coordinador.

```text
ANTES DE NADA: cargá y seguí las skills `fable-method` y `ponytail` (y `plan-then-do`, `tool-calling-guard`, `verify-before-commit`, `omnicad-test`). Al terminar, corré `ponytail-review` sobre el cambio y pegá su salida real. Si no tenés las skills, seguí estas reglas igual: el cambio más chico que resuelve TODO lo pedido, sin opciones ni abstracciones que nadie pidió; leé cada archivo antes de editarlo; nunca digas "listo" sin pegar la salida real de los comandos de verificación.

Paquete E de `docs/plan_velocidad.md` (OmniCAD): las piezas de ventana de `scripts/prueba_ui` en paralelo. Leé esa sección del plan, `scripts/prueba_ui/todo.py` (81 líneas), `scripts/turno.py` (sobre todo `OMNICAD_TURNOS`, que da varios lugares a la vez) y cómo `scripts/prueba_ui/arnes.py` arma los nombres de las capturas y los registros.

DÓNDE: SOLO en `D:/PROGRAMA-velE` (rama `velocidad-E`). Python: `/d/PROGRAMA/clon/.venv/Scripts/python.exe`; desde `D:/PROGRAMA-velE/clon` importa el código del worktree. No instales nada. No hagas commit ni push. Todo en español. Archivos: `scripts/prueba_ui/todo.py`, lo mínimo de `scripts/prueba_ui/arnes.py` si dos piezas a la vez pisan el mismo archivo, y un test nuevo `clon/tests/test_todo_paralelo.py`. NO toques `docs/`, `AGENTS.md` ni `CLAUDE.md`. Otra sesión corre tests con `turno.py` en esta PC: no cortes procesos que no lanzaste vos.

QUÉ HACER:
1. `todo.py --paralelo N` (por defecto 1, como hoy): corre hasta N piezas a la vez, cada una en su ventana minimizada (transparente y sin foco, el modo por defecto), con `turno.py` dándole N lugares (`OMNICAD_TURNOS=N` para los hijos). Sin `--paralelo`, todo queda exactamente como hoy.
2. Las más largas primero: al terminar, `todo.py` guarda los segundos de cada pieza en `SALIDA/tiempos_piezas.json` y, si existe el de una corrida anterior (el más nuevo de `evidencias/ui_*/tiempos_piezas.json`), ordena las piezas de mayor a menor. Una pieza sin dato va al final.
3. El resumen sale en el orden de `PIEZAS` (o el de los nombres pedidos), con las mismas líneas de hoy, aunque terminen desordenadas. Las piezas de `PIEZAS_CON_FOCO_REAL` siguen salteándose en minimizada con su ⚠.
4. Que dos piezas a la vez no pisen el mismo archivo de `SALIDA` (logs, `*.json`, capturas). Si hoy pueden chocar, arreglalo con el nombre de la pieza en el archivo.
5. `clon/tests/test_todo_paralelo.py`: sin abrir ventanas, con piezas falsas (scripts chicos en `tmp_path` que imprimen `=== N comprobaciones, M con` y duermen un poco), comprobá: con `--paralelo 2` corren dos a la vez, el resumen sale en orden, se escribe `tiempos_piezas.json` y la corrida siguiente arranca por la más larga. Si para eso hace falta pasarle a `todo.py` otra carpeta de piezas o de salida, usá variables de entorno que ya existan (`OMNICAD_PRUEBA_SALIDA`) o la mínima nueva. Tiene que pasar con `-W error`.

VERIFICACIÓN (pegá la salida real):
- Desde `D:/PROGRAMA-velE/clon`: `/d/PROGRAMA/clon/.venv/Scripts/python.exe -m ruff check . ../scripts/prueba_ui/todo.py` y `/d/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/tests_afectados.py --correr`.
- ANTES de las piezas reales, mirá la memoria libre (`powershell -NoProfile -Command "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)"`). Con menos de 5000 MB, esperá hasta 10 min mirando cada minuto; si no sube, corré igual con `--paralelo 2` y decilo.
- Elegí 4 piezas CORTAS de `PIEZAS` (mirá el tamaño de sus scripts) y corrélas desde `D:/PROGRAMA-velE/clon`: primero en serie (`../scripts/prueba_ui/todo.py a b c d`) y después con `--paralelo 2`, de a una corrida. Pegá el tiempo de pared de cada una, los dos resúmenes (tienen que dar las mismas ✗) y el pico de memoria de todos los python, muestreando cada 2 s (por ejemplo `(Get-Process python* | Measure-Object WorkingSet64 -Sum).Sum` en un bucle).
- NO corras las 51 piezas: van a la corrida nocturna.

INFORME FINAL (corto): qué cambiaste, las 4 piezas, los dos tiempos, los dos resúmenes, el pico de memoria, la salida de `ponytail-review` y lo que no pudiste verificar (con ⚠).
```
