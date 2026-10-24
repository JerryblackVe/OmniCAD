# OmniCAD

## REGLA ESTRICTA (sin excepciones): MCP y CLI siempre completos
- TODAS las herramientas de la app están en el MCP y en la CLI, siempre. Vale para todo: operaciones,
  comandos de la cinta, menús contextuales, opciones de cada diálogo y espacios de trabajo (DIBUJO,
  RENDERIZAR, ANIMACIÓN…). Lo único que queda afuera es lo que no le sirve a un agente (tema, atajos,
  paneles), y eso se escribe con su razón en `docs/brechas_mcp.md`.
- Toda función nueva o cambiada lleva SIEMPRE su
  herramienta en `clon/omnicad/api/` (receta C de AGENTS.md), y con eso queda en el MCP y en la CLI.
- No se da por terminada una tarea si falta la herramienta, su test o la doc regenerada
  (`docs/agentes/herramientas.md`).
- Si encontrás algo de la app sin herramienta, se la agregás en el mismo turno.

## Regla estricta: bugs, faltantes y mejoras en un solo lugar
- Todo lo que falta resolver se recopila SOLO en `docs/seguimiento/`:
  - `bugs.md`: lo que falla.
  - `faltantes.md`: funciones que no existen.
  - `mejoras.md`: upgrades de lo que ya existe.
  Método y columnas: `docs/seguimiento/README.md`. Índice de toda la doc: `docs/README.md`.
- Lo que se encuentra se agrega ahí al momento, con el siguiente ID libre.
- **Al resolverse, la fila se BORRA** en el mismo commit que el arreglo, y se anota en el Registro de
  `PROJECT_LOG.md` con el ID y la prueba que lo cubre. Las listas tienen solo lo pendiente.
- Antes de informar qué está hecho o qué falta, se verifica contra el código y los tests. Nunca solo con el log.
- Cada tarea deja el proyecto limpio: sin archivos sueltos ni contradicciones entre documentos.

## Regla: rendimiento con Rust
- La app a veces se siente lenta: la meta es optimizar lo más posible.
- Todo cuello de botella que se pueda pasar a Rust (malla, solver de bocetos, teselado, visor,
  recálculo del timeline) se pasa, como módulo puntual vía PyO3 llamado desde Python.
- Medir primero (perfilar), después optimizar. No reescribir la app entera: la geometría ya es
  OpenCascade (C++).
- Instalar el toolchain de Rust/maturin requiere permiso del usuario.

## Regla obligatoria: ponytail
- **Se INVOCA con la herramienta Skill, no alcanza con leer la regla.** Toda sesión que vaya a tocar código
  (también las sub-sesiones y las que orquestan OpenCode) arranca con `ponytail`, termina con `ponytail-review`,
  y usa `ponytail-audit` / `ponytail-debt` cuando haga falta. Un hook de `.claude/settings.json` lo recuerda
  al abrir la sesión y antes de cada `git commit`. Los briefs a OpenCode llevan ponytail embebido.
- Usar SIEMPRE la skill `/ponytail` en todo proceso de código donde sea útil o necesario
  (escribir, arreglar, refactorizar, elegir dependencias): el cambio más chico que resuelve
  la tarea completa, sin sobre-ingeniería.
- Usar SIEMPRE la skill `/ponytail-review` antes de dar por terminado un cambio de código:
  revisión de lógica, seguridad, carga real, tests y que cada línea sea necesaria.

@AGENTS.md
