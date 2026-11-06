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

### B. La suite en paralelo
- Qué: `pytest-xdist` (pide permiso para instalar) con 4 procesos (`-n 4 --dist loadfile`, un archivo entero por
  proceso); el tope de `turno.py` sube para esa corrida (4 × ~1 GB). Las tandas se arman por **tiempo medido** (A), no
  por cantidad, para que ninguna se acerque a los 900 s.
- Listo cuando: la suite entera pasa igual de verde que en serie, en menos de 25 min, sin cortes por plazo, y el pico
  de memoria medido queda por debajo de 8 GB.
- Ejecutor: CodeBuddy hy3; Opus revisa los tests que fallen solo en paralelo (son bugs de test: archivos o ajustes
  compartidos; se arreglan con `tmp_path`, nunca salteando el test).

### C. Correr solo lo afectado durante el día
- Qué: `scripts/tests_afectados.py`: de `git diff` saca los módulos tocados, y por el grafo de imports (sin instalar
  nada) los tests que los usan, más las piezas de ventana que tocan esa área (mapa pieza → módulos en `todo.py`).
  Agentes y coordinador corren eso en vez de elegir tests a ojo. La suite entera queda para el cierre.
- Listo cuando: para los últimos 10 commits, la lista que da incluye todos los tests que esos commits cambiaron o
  que fallaron en su momento, y tarda menos de 5 s en armarse.
- Ejecutor: CodeBuddy hy3.

### D. Humo sin cursor real
- Qué: los 7 movimientos del cursor real de `prueba_humo.py` pasan a eventos simulados (`_mover`, como pide AGENTS.md
  para pasos nuevos). El humo corre minimizado y sin esperar PC quieta. `registro_uso` y `asistente` (foco real de
  Windows) se revisan igual; si no se pueden simular, siguen de noche.
- Listo cuando: el humo da «TODO OK» con `--ventana minimizada` mientras se usa la PC, y el cierre ya no espera ocio
  para el humo.
- Ejecutor: CodeBuddy hy3.

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

Entregado el 2026-11-06. Modelo sugerido: CodeBuddy hy3, esfuerzo por defecto (el paquete A ya está en main; queda D, a medias en la rama `velocidad-D`). Corre con `codebuddy -p --permission-mode bypassPermissions`, en su worktree y con `timeout 1500`; revisa, commitea y fusiona el coordinador.

```text
=== PAQUETE D ===

ANTES DE NADA: si tenés las skills `fable-method`, `ponytail`, `plan-then-do`, `tool-calling-guard`, `verify-before-commit` y `omnicad-test`, cargalas y seguilas; al terminar, `ponytail-review` sobre tu cambio y pegá su salida. Si no las tenés, seguí estas reglas igual: el cambio más chico que resuelve TODO lo pedido, sin opciones ni abstracciones que nadie pidió; leé cada archivo antes de editarlo; no digas "listo" sin pegar la salida real de los comandos de verificación.

Paquete D de `docs/plan_velocidad.md` (OmniCAD, CAD en Python con PySide6): la prueba de humo sin mover el cursor real y con la ventana invisible, para que Gerardo pueda usar la PC mientras corre.

DÓNDE: trabajás SOLO en el worktree `D:/PROGRAMA-velD` (rama `velocidad-D`). No toques `D:/PROGRAMA` ni otro worktree. Python: `/d/PROGRAMA/clon/.venv/Scripts/python.exe` (desde `D:/PROGRAMA-velD/clon` importa el código del worktree). No instales nada. No hagas commit ni push: commitea el coordinador. Todo en español.

ARCHIVOS QUE PODÉS TOCAR: `clon/omnicad/prueba_humo.py` y, solo si hace falta para lo de abajo, lo mínimo de `clon/OmniCAD.py` y `clon/omnicad/ui/`. NO toques `scripts/` (el cierre lo cambia el coordinador) ni los tests de otros.

QUÉ HACER:
1. Cursor: `prueba_humo.py` mueve el cursor REAL de Windows con `QTest.mouseMove` (líneas ~116, 451, 452, 549 dentro de un bucle, 569, 781; buscá también `QCursor.setPos` y cualquier otro). Pasalos todos a `_mover(w, pos)` (ya existe en el mismo archivo, línea ~288: evento simulado al widget). Si un paso depende de que el código bajo prueba lea `QCursor.pos()` o reciba `enterEvent`/hover, hacé que el widget reciba el evento simulado que necesita; NUNCA borres un paso ni debilites una aserción (mismo chequeo, mismo umbral). Al final no tiene que quedar ninguna llamada que mueva el cursor real.
2. Ventana: con la variable de entorno `OMNICAD_PRUEBA_VENTANA=minimizada`, la ventana del humo se abre como lo hace `scripts/prueba_ui/arnes.py` (`mostrar` y `activar`, líneas ~95-125: `WA_ShowWithoutActivating`, flags `Tool | WindowTransparentForInput | WindowDoesNotAcceptFocus`, opacidad 0, y `QApplication.setActiveWindow` en lugar de `activateWindow`). Leé esas funciones y replicá lo mínimo en el humo (sin la variable, el humo queda exactamente como hoy). Todo `activateWindow`/`raise_`/foco real dentro del humo pasa por la misma regla. Si un paso necesita sí o sí el foco real de Windows, NO lo saltees en silencio: dejalo andar en visible y en minimizada imprimí un aviso `⚠` con el nombre del paso, y decilo en el informe.

VERIFICACIÓN (pegá la salida real):
- Desde `D:/PROGRAMA-velD/clon`: `/d/PROGRAMA/clon/.venv/Scripts/python.exe -m ruff check .`
- `grep -n "mouseMove\|setPos" omnicad/prueba_humo.py` → nada que mueva el cursor real.
- Humo minimizado, con la posición del cursor antes y después: escribí un script AFUERA del repo (en `%TEMP%`) que con `ctypes.windll.user32.GetCursorPos` imprima la posición, corra con `subprocess` (env `PYTHONIOENCODING=utf-8`, `OMNICAD_PRUEBA_VENTANA=minimizada`) `/d/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py --plazo 900 -- /d/PROGRAMA/clon/.venv/Scripts/python.exe OmniCAD.py --prueba-humo`, guarde su salida en `%TEMP%`, y vuelva a imprimir la posición (y cuántas veces cambió, mirando cada 100 ms en un hilo). Pegá las dos posiciones y las últimas líneas del humo: tiene que decir «Resultado: TODO OK». No muevas el ratón ni uses el teclado mientras corre.
- Comparación paso por paso: `git diff` de `prueba_humo.py` y una tabla corta "paso original → cambio → misma aserción sí/no".
- NO corras la suite completa ni las piezas de `scripts/prueba_ui`.

INFORME FINAL (corto): archivos tocados, la tabla de pasos, las salidas de arriba y lo que no pudiste verificar (con ⚠).
```
