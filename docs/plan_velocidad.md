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
- Hecho (2026-11-06, P-63): Sol en OpenCode (se le acabaron los 25 min antes de medir; midió el coordinador). Medido de día con 22 archivos (1079 tests): serie 1167 s, 3 rojos por `MemoryError` del tope de 3000 MB de `turno.py`; `-n 2` 526 s, todo verde, pico de 3,5 GB en total. `-n 4` sin medir: de día había de 1 a 4 GB libres y la PC se colgó una vez (no durante esta prueba). Tope que aguanta esta PC: se mide la primera noche; si pasa 8 GB, `-n 3`. Cierre del 2026-11-07, de día y con `-n 2`: ~62 min compartiendo la fila de `turno.py` con otra sesión, 1 rojo por carga (B-238) y la memoria libre bajó a 291 MB: `-n 4` sigue sin medir, solo de noche con la PC libre.

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
- Hecho (2026-11-06, P-65): `todo.py --paralelo N`. Lo empezó GLM 5.3 (sin créditos) y lo terminó Sol. Medido de día con 4 piezas (auditoria_undo, paneles_inventario, booleana_unir, cinta_completa; 984 comprobaciones, 0 ✗ en los dos modos): serie 316 s, `--paralelo 2` 238 s (25 % menos), picos de 1,8 y 2,2 GB. Cierre del 2026-11-07: las 52 piezas con `--paralelo 2` en 34 min (serie: 94 min), meta cumplida.

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
