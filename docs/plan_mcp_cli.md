# Plan: MCP + CLI para que cualquier agente IA diseñe y desarrolle con OmniCAD

Fecha: 2026-10-09. Estado: **aprobado, en ejecución**. El programa se llama **OmniCAD** (hasta el 2026-10-09 fue FusionClone).

## Objetivo

Que cualquier agente IA pueda:

- **Diseñar con el programa.** Crear y modificar piezas 3D, sin ventana o mirando el modelo en vivo.
- **Desarrollar el programa.** Agregar y mejorar funciones con documentación clara y una verificación de un solo comando.

Los agentes previstos son Claude Code, OpenCode, Codex, Cursor, Gemini CLI, Claude Desktop y scripts propios.

## Datos verificados que sostienen el plan

| Dato | Evidencia |
|---|---|
| El núcleo no usa Qt, así que se puede diseñar sin abrir la ventana. | `grep` de `PySide6` en `nucleo/`, `timeline/`, `io_archivos/` y `restricciones/` no encuentra nada. |
| Hay 85 tipos de operación registrados en un solo diccionario. | `timeline/operaciones.py:626` (`TIPOS_OPERACION`) más `registrar_operacion`. |
| Cada operación declara sus parámetros con valores por defecto, sus expresiones y un docstring que dice a qué comando de Fusion equivale. Con eso se puede generar el esquema de las 85 operaciones sin escribirlo a mano. | `operaciones.py:171` (`PARAMS`, `EXPRESIONES`). |
| La receta del diseño ya se guarda en JSON. | `Documento.a_dict` / `desde_dict` y `operacion_desde_dict`. |
| El formato `.omnicad` es un ZIP que se guarda de forma atómica. | `io_archivos/proyecto.py`. |
| Hay deshacer y rehacer, parámetros con expresiones y recálculo. | `Documento` (`deshacer`, `parametros`, `recalcular`). |
| Las referencias a caras y aristas son persistentes: sobreviven al recálculo porque usan una firma geométrica. | `nucleo/referencias.py`. |
| Se pueden sacar imágenes sin ventana con un render por software en numpy. | `nucleo/render_cpu.py` (`renderizar`, `guardar_png`). |
| Se pueden sacar imágenes en vivo desde la GPU. | `ui/visor3d.py:1594` (`captura_png`). |
| Exporta a STL, OBJ, STEP, IGES y BREP. | `io_archivos/exportar.py`. |
| La versión vigente del SDK oficial de MCP para Python es la 2.3.0. En la v2, `FastMCP` pasó a llamarse `MCPServer` y se importa con `from mcp.server import MCPServer`. | PyPI y la documentación v2, consultados el 2026-10-09. |
| El SDK de MCP no está instalado en el venv. | `pip list`. |
| La carpeta no tiene git. | `git status` devuelve "not a git repository". |
| En esta PC hay dos agentes instalados para las pruebas reales: `claude` y `opencode`. No están `codex`, `gemini` ni `cursor`. | `command -v`. |
| Hay un MCP de Fusion 360 de terceros (Faust Machines) que sirve de referencia de nombres. Tiene unas 90 herramientas en inglés (`create_sketch`, `draw_rectangle`, `extrude`, `fillet`, …) y errores con `error_kind` más pistas. | `%APPDATA%\Autodesk\…\AddIns\Fusion360MCP\server\command_handler.py`. Solo se leyó: no se copia código. |

## Decisiones (tomadas, con su motivo)

1. **Una sola API y tres caras.** Cada herramienta se define una vez en `omnicad/api/`. De esa definición salen solas:
   - las herramientas del MCP;
   - los comandos de la CLI;
   - la documentación.

   Así no hay dos fuentes de verdad que se contradigan. Un test verifica que la documentación esté al día.
2. **Nombres en inglés, compatibles con el MCP de Fusion 360.** Por ejemplo `create_sketch`, `extrude`, `fillet`, `get_viewport_image`. Un agente que ya sabe usar Fusion usa el clon sin aprender nada nuevo. Las descripciones, la documentación y los mensajes de error quedan en español. Los códigos de error son fijos y en inglés (`PROFILE_NOT_CLOSED`), igual que en ese MCP.
3. **Dos modos de trabajo con las mismas herramientas.**
   - Modo **sin ventana**: es el modo por defecto. Es rápido, sirve para tests y no necesita la app abierta.
   - Modo **en vivo**: la app abierta muestra en tiempo real lo que hace el agente. Hay que encenderlo a mano.
4. **Las 85 operaciones quedan disponibles sin crear 85 herramientas.**
   - Unas 25 herramientas cómodas cubren lo común: boceto, extruir, revolución, empalme, agujero, patrón, etc.
   - Para el resto están `describe_operation` y `run_operation`, que usan el formato de receta que ya existe.

   Demasiadas herramientas confunden a los agentes.
5. **Selectores de caras y aristas al estilo CadQuery**, que los modelos ya conocen. Ejemplos: `">Z"` es la cara de más arriba, `"|Z"` son las aristas verticales y `"%CIRCLE"` las curvas circulares. Por dentro se convierten en las referencias persistentes de `nucleo/referencias.py`.
6. **Los resultados se pueden ver.** Las herramientas que modifican el diseño aceptan `with_image=true` y devuelven una miniatura en la misma respuesta. El agente ve lo que hizo sin pedir otra llamada.
7. **Git local, sin remoto.** Es la red de seguridad para revisar o deshacer lo que cambie un agente en el código. Nunca se sube nada a internet sin el OK del usuario.
8. **El nombre es OmniCAD.** El paquete es `omnicad`, el archivo de proyecto es `.omnicad` y la CLI y el MCP se llaman `omnicad`. Los `.fclone` viejos se siguen abriendo.

## Arquitectura

```
 Agentes IA (Claude Code, OpenCode, Codex, Cursor, Gemini, Claude Desktop, scripts)
      │ MCP (stdio o HTTP 127.0.0.1)    │ CLI `omnicad` (JSON)          │ Python
      ▼                                  ▼                              ▼
 omnicad/servidor_mcp/         omnicad/cli/              from omnicad import api
      └─────────────────┬────────────────┘
                omnicad/api/  ← CATÁLOGO ÚNICO: nombre, parámetros, esquema, función,
                │                    errores con error_kind y pistas
       ┌────────┴─────────┐
  Sesión sin ventana   Sesión en vivo ──► puente local en la app (QTcpServer 127.0.0.1 + token)
  (Documento en          que ejecuta la MISMA función del catálogo sobre el documento abierto,
   memoria)              en el hilo de Qt, como un paso de deshacer
       └────────┬─────────┘
   timeline/Documento · restricciones/Boceto · nucleo (OCCT) · io_archivos · render_cpu
```

El puente en vivo usa `QTcpServer`, que corre dentro del bucle de eventos de Qt. Por eso no necesita hilos ni el "event bridge" del add-in de Fusion: es más simple y no tiene carreras.

## Catálogo de herramientas: primera versión

Las herramientas se agrupan en "toolsets". El agente activa solo los que necesita, por ejemplo con `--toolsets diseno,dev`.

| Grupo | Herramientas |
|---|---|
| documento | `get_scene_info`, `new_document`, `open_document`, `save_document`, `export`, `undo`, `redo`, `get_timeline`, `edit_feature`, `suppress_feature`, `delete_feature`, `rename` |
| parametros | `get_parameters`, `create_parameter`, `set_parameter`, `delete_parameter` |
| boceto | `create_sketch` (sobre un plano o una cara), `draw_line`, `draw_rectangle`, `draw_circle`, `draw_arc`, `create_polygon`, `draw_spline`, `create_construction_plane`, `add_constraint`, `add_dimension`, `get_sketch` (perfiles, grados de libertad y estado), `sketch_from_spec` (un boceto entero en un JSON) |
| solido | `extrude`, `revolve`, `sweep`, `loft`, `fillet`, `chamfer`, `shell`, `create_hole`, `rectangular_pattern`, `circular_pattern`, `mirror`, `boolean_operation`, `create_box`, `create_cylinder`, `create_sphere`, `create_torus`, `move_body` |
| inspeccion | `get_viewport_image` (vistas iso, front, top, …), `find_faces`, `find_edges`, `measure_distance`, `measure_angle`, `get_physical_properties`, `check_interference` |
| avanzado | `list_operation_types`, `describe_operation`, `run_operation`, `get_recipe`, `apply_recipe`, `execute_code` (Python con `api` ya cargado), `get_guide` |
| dev | Solo con `--dev`: `run_checks` (ruff + pytest + prueba de humo) y `app_screenshot` (captura de la ventana real) |

El formato de la respuesta es el mismo en todas las herramientas:

```
{"ok": true, "result": {...}, "avisos": [...]}
{"ok": false, "error_kind": "PROFILE_NOT_CLOSED", "mensaje": "…", "pistas": ["…"]}
```

Unidades: mm y grados. Los valores aceptan expresiones con parámetros, por ejemplo `"ancho / 2"`, porque las operaciones ya las entienden.

Extras del MCP:

- **Resources:** guía de diseño, esquema de cada operación, receta actual y ejemplos.
- **Prompts:** `disenar_pieza`, `preparar_impresion_3d` y `revisar_diseno`.
- **`instructions`:** el flujo básico (boceto → perfil → operación → mirar la imagen).

Algunos clientes no soportan resources ni prompts. Para ellos `get_guide` devuelve lo mismo como herramienta.

## Hitos y paquetes de trabajo

### Hito 0. Base segura (paquete A)

**Qué incluye:**
- ✅ Hecho el 2026-10-09: `git init` en `D:\PROGRAMA`, con `.gitignore`. Quedan afuera:
  - `analisis/`, `evidencias/` y `privado/`: material de referencia y pruebas locales, que nunca se publica;
  - `skills/`: es ajeno al proyecto;
  - `.venv` y las cachés.
- ✅ Commit base y cambio de nombre a OmniCAD.
- `pyproject.toml` con los comandos `omnicad` y `omnicad-mcp` (`pip install -e .`). Se pasa a los paquetes F y G: no se crean comandos que todavía no hacen nada.
- ✅ `mcp==2.3.0` agregado a `requirements.txt` e instalado.
- ✅ `AGENTS.md` en la raíz, que es el estándar que leen Codex, OpenCode, Cursor, Gemini y Copilot. Junta las reglas de `docs/brief_agentes.md`, que queda como enlace.
- `CLAUDE.md`, que importa `@AGENTS.md`.

**Listo cuando:**
- `git log` muestra el commit;
- `.venv/Scripts/omnicad --version` responde;
- `import mcp` da 2.3.x;
- `AGENTS.md` tiene: mapa de carpetas, cómo agregar una operación, cómo agregar una herramienta y los comandos de verificación.

**Ejecutor:** Sonnet 5, esfuerzo medio. Es mayormente configuración y documentación, pero toca las reglas del proyecto.

### Hito 1. La API única: el corazón

**Paquete B. Sesión, catálogo y errores.** ✅ Hecho el 2026-10-09: 16 herramientas, 52 tests. El catálogo vive en `api/registro.py`.
- **Qué incluye:**
  - `omnicad/api/` con `Sesion` (nuevo, abrir, guardar, deshacer y documento activo);
  - el decorador `@herramienta(nombre, grupo, descripcion)`, que genera el esquema JSON a partir de los tipos;
  - la tabla `error_kind` → pistas;
  - los grupos documento y parámetros.
- **Listo cuando:**
  - los tests pasan;
  - `api.catalogo()` devuelve cada herramienta con su esquema;
  - un test confirma que importar `omnicad.api` NO carga PySide6.
- **Ejecutor:** Opus 5, esfuerzo alto. Es la pieza de la que depende todo: un mal diseño acá se paga tres veces.

**Paquete C. Boceto y sólidos.** ✅ Hecho el 2026-10-09.
- **Qué incluye:** los grupos boceto y sólido, con nombres compatibles con Fusion, más `sketch_from_spec`.
- **Listo cuando:**
  - un test arma un soporte en L con dos agujeros usando solo la API;
  - el volumen da el esperado con un margen de ±0,1 %.
- **Ejecutor:** Sonnet 5, esfuerzo medio. Es código estándar sobre operaciones que ya existen.

**Paquete D. Selectores de caras y aristas.** ✅ Hecho el 2026-10-09.
- **Qué incluye:** `find_faces` y `find_edges`, y selectores dentro de `fillet`, `chamfer`, `shell` y `create_hole`.
- **Listo cuando:**
  - `fillet(edges="|Z")` sobre una caja toma 4 aristas;
  - el empalme sobrevive a un cambio de parámetro;
  - una referencia perdida da `REFERENCE_LOST` con pistas.
- **Ejecutor:** Sonnet 5, esfuerzo medio. Se apoya en `referencias.py`, que ya existe. Si falla dos veces, se escala a Opus.

**Paquete E. Inspección y modo avanzado.** ✅ Hecho el 2026-10-09.
- **Qué incluye:**
  - `get_viewport_image` sin ventana, usando `render_cpu`;
  - propiedades físicas, medición e interferencia;
  - `describe_operation` y `run_operation` para las 85 operaciones;
  - `apply_recipe` y `execute_code`.
- **Listo cuando:**
  - un test recorre las 85 operaciones y `describe_operation` responde en todas;
  - la imagen del ejemplo a 640×480 sale en menos de 2 s y es un PNG válido.
- **Ejecutor:** Sonnet 5, esfuerzo medio.

### Hito 2. Las tres caras

**Paquete F. CLI `omnicad`.** ✅ Hecho el 2026-10-09.
- **Qué incluye:**
  - `omnicad tools` y `omnicad call <herramienta> --doc pieza.omnicad --args '{…}'`: todo el catálogo, sin escribir cada comando a mano;
  - atajos: `new`, `info`, `export`, `render`, `run script.py`, `batch pasos.jsonl` y `describe <op>`;
  - `--json` para máquinas;
  - códigos de salida: 0 si salió bien, 1 si hay un error del diseño, 2 si hay un error de uso.
- **Listo cuando:** los tests con `subprocess` pasan, `call create_box` modifica el archivo y `batch` corre 10 pasos en un solo proceso.
- **Ejecutor:** Sonnet 5, esfuerzo medio.

**Paquete G. Servidor MCP.** ✅ Hecho el 2026-10-09.
- **Qué incluye:**
  - `python -m omnicad.servidor_mcp` (no se llama `omnicad/mcp` para no confundirse con el paquete `mcp` del SDK), con `MCPServer` v2;
  - registro automático del catálogo y toolsets;
  - imágenes como contenido de imagen;
  - resources, prompts e `instructions`;
  - transporte stdio, y HTTP solo en 127.0.0.1;
  - `.mcp.json` del proyecto.
- **Listo cuando:**
  - un test con un cliente en memoria lista las herramientas, llama a `create_box` y recibe la imagen;
  - `claude mcp list` muestra omnicad ✓ Connected;
  - OpenCode también conecta.
- **Ejecutor:** Sonnet 5, esfuerzo medio.

**Paquete H. Puente en vivo.** ✅ Hecho el 2026-10-09 (commit 0fb142d).
- **Qué incluye:**
  - Un servidor local dentro de la app. Viene apagado: se enciende en Preferencias, en la opción "Permitir agentes IA", o con `--puente`.
  - Un token aleatorio guardado en un archivo del usuario.
  - Un protocolo de líneas JSON.
  - Cada llamada es un paso de deshacer y muestra el aviso "Agente IA: Extrusión 3" en la barra de estado.
  - Si el usuario tiene un comando abierto, la respuesta es `APP_BUSY`.
  - El MCP detecta solo si la app está abierta.
- **Listo cuando**, en una fase nueva de la prueba de humo:
  - el cliente conecta;
  - `create_box` aparece en el navegador;
  - deshacer lo saca;
  - un token incorrecto se rechaza.
- **Ejecutor:** Opus 5, esfuerzo alto. Hay concurrencia con la interfaz y seguridad.

### Hito 3. Herramientas de desarrollo y documentación

**Paquete I. Herramientas de desarrollo.** ✅ Hecho el 2026-10-09 (commit 0fb142d).
- **Qué incluye:**
  - `omnicad dev check`: corre ruff, pytest y la prueba de humo, y devuelve un resumen JSON;
  - `omnicad dev screenshot`: captura de la ventana real, reutilizando `scripts/capturas_ui.py`;
  - el toolset `dev` del MCP.
- **Listo cuando:** `omnicad dev check --json` devuelve `{"ruff":"ok","pytest":"N passed","humo":"OK"}` y sale con 0.
- **Ejecutor:** Haiku 4.5. La especificación es cerrada: es cablear `subprocess`.

**Paquete J. Documentación organizada.** ✅ Hecho el 2026-10-09: `docs/agentes/` y `ejemplos/agentes/`.
- **Qué incluye:** la carpeta `docs/agentes/` con:
  - `README.md`: índice y "empezá acá";
  - `conectar.md`: configuraciones listas para Claude Code, Claude Desktop, OpenCode, Codex, Cursor, Gemini CLI y VS Code;
  - `guia_diseno.md`: flujo, selectores y unidades;
  - `cli.md`;
  - `puente.md`;
  - `herramientas.md`: se GENERA desde el catálogo.

  Además:
  - `ejemplos/agentes/`, con una receta, un script y un batch, todos ejecutables;
  - actualizar `arquitectura.md` y `PROJECT_LOG.md`.
- **Listo cuando:**
  - el test de sincronía de la documentación pasa;
  - cada ejemplo corre dentro de pytest;
  - las configuraciones de los clientes no probados dicen "no probado".
- **Ejecutor:** Sonnet 5, esfuerzo medio.

**Paquete L. Skill `omnicad`: una sola, que sirve para el MCP y para la CLI.** ✅ Hecho el 2026-10-09 (falta probar que se active sola: va en el paquete K).
- **Qué incluye:** un `SKILL.md` en el formato estándar de skills, guardado en `.claude/skills/omnicad/` del proyecto. Dice:
  - cuándo usarla: diseñar o modificar una pieza, o mejorar el programa;
  - el ciclo de trabajo: mirar → hacer → ver la imagen → medir → guardar;
  - qué usar: el MCP si está conectado; si no, la CLI `omnicad --json`;
  - una hoja corta con los selectores y los errores más comunes.

  No repite la guía: enlaza a `get_guide` y a `docs/agentes/guia_diseno.md`, así no hay dos versiones que se contradigan.

  El comando `omnicad setup` hace la instalación: registra el MCP y copia la skill en Claude Code y en OpenCode.
- **Listo cuando:**
  - en una sesión nueva de Claude Code, el pedido "diseñá un soporte en L" activa la skill sola;
  - OpenCode también la ve, o queda anotado que no la soporta.
- **Ejecutor:** Sonnet 5, esfuerzo medio, con la skill `skill-creator` si está disponible en esa sesión.

### Hito 4. Prueba real con agentes (paquete K): la que dice si es "cómodo"

- **Qué incluye:** agentes reales, sin leer el código, arman 3 piezas a partir de un texto:
  - un soporte en L con agujeros y empalmes;
  - una caja con tapa vaciada;
  - una brida con un patrón circular de agujeros.

  Se prueban tres vías: MCP sin ventana, solo la CLI y el modo en vivo, con Claude Code y con OpenCode.

  Se mide: si salió, cuántas llamadas hizo y cuántos errores tuvo. Cada fricción se corrige.
- **Listo cuando:**
  - las 3 piezas salen bien, con el volumen dentro de ±1 % y la imagen revisada contra el pedido;
  - las fricciones quedan anotadas y corregidas.
- **Ejecutor:** Sonnet 5, esfuerzo medio, como "usuario". La revisión la hace el orquestador.

### Hito 5 (opcional, más adelante). Complementos

Una carpeta `complementos/` donde un agente puede sumar herramientas u operaciones nuevas sin tocar el núcleo. Funcionaría como los Scripts y Add-ins de Fusion, con `registrar(api)`. Solo se hace si el usuario lo pide.

## Orden y dependencias

```
A ──► B ──► C ──► D
            │     │
            └──► E ──► F, G (en paralelo) ──► H ──► I, J, L (en paralelo) ──► K
```

## Riesgos

| Riesgo | Mitigación |
|---|---|
| El agente y el usuario tocan el mismo diseño en vivo. | Todo pasa por el hilo de Qt. Si hay un comando abierto, la respuesta es `APP_BUSY`, y cada llamada es un paso de deshacer. |
| El puente es una puerta local: `execute_code` puede correr Python. | Viene apagado, escucha solo en 127.0.0.1, usa un token aleatorio en un archivo del usuario y muestra un indicador visible de "agente conectado". |
| Demasiadas herramientas confunden a los agentes. | Unas 35 por defecto, en grupos. El resto pasa por `run_operation`. El hito 4 mide los errores reales. |
| Las caras o aristas referenciadas se pierden al recalcular. | Se usan las firmas persistentes que ya existen, más `REFERENCE_LOST` con pistas para volver a elegir. |
| Las imágenes sin ventana tardan, porque el render es por software. | 640×480 sin supermuestreo por defecto. En vivo se usa la captura de la GPU. |

## Las 3 acciones de mayor impacto

1. Hacer primero la API única (paquete B). Sin ella, el MCP y la CLI serían dos programas distintos que se contradicen.
2. Hacer git antes de dejar que un agente toque el código (paquete A). Todo cambio queda revisable y se puede deshacer.
3. Hacer la prueba con agentes reales (paquete K). Es la única que mide si de verdad es cómodo de usar.
