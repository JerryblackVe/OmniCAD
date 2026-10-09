# OmniCAD para agentes IA: empezá acá

OmniCAD es un CAD 3D paramétrico en Python (kernel OpenCascade). Un agente IA lo puede usar para **diseñar piezas**
y para **desarrollar el programa**, sin abrir la ventana o mirándola en vivo.

- Diseño: boceto, extruir, empalmar, agujeros, patrones, medir, ver una imagen, exportar a STL o STEP.
- Todo es una receta: parámetros y pasos que se recalculan enteros con cada cambio.
- Unidades: milímetros y grados.

## Tres vías, la misma API

| Vía | Para qué | Doc |
|---|---|---|
| Servidor MCP (`omnicad-mcp`) | agentes que hablan MCP: Claude Code, Claude Desktop, OpenCode, Codex, Cursor, Gemini CLI, VS Code | [conectar.md](conectar.md) |
| CLI (`omnicad`) | agentes sin MCP, scripts y pruebas a mano | [cli.md](cli.md) |
| Python (`from omnicad import api`) | scripts propios | [ejemplo](../../ejemplos/agentes/soporte_l.py) |

Las tres salen de un solo catálogo (`clon/omnicad/api/`): una herramienta se define una vez y aparece en las tres.

## Empezar en 3 pasos

1. **Conectá el agente.** Copiá el bloque de tu cliente de [conectar.md](conectar.md). Si no hay MCP, usá la CLI.
2. **Leé la guía.** Pedí `get_guide` con `topic="flujo"` (o leé [guia_diseno.md](guia_diseno.md)): el ciclo es mirar, hacer, ver la imagen, medir, guardar.
3. **Armá una pieza.** Seguí un ejemplo de [ejemplos/agentes](../../ejemplos/agentes/README.md): un soporte en L con agujeros y empalmes, en tres formas.

## Qué doc leer según lo que quieras

| Quiero… | Leé |
|---|---|
| conectar mi agente | [conectar.md](conectar.md) |
| saber cómo se diseña y qué hay que mirar | [guia_diseno.md](guia_diseno.md) |
| usar la terminal | [cli.md](cli.md) |
| ver la lista completa de herramientas y sus parámetros | [herramientas.md](herramientas.md) (generado) |
| que el agente trabaje sobre la ventana abierta | [puente.md](puente.md) |
| ver una pieza armada paso a paso | [ejemplos/agentes](../../ejemplos/agentes/README.md) |
| agregar una herramienta o una operación al programa | [AGENTS.md](../../AGENTS.md) (recetas A, B y C) |
| entender cómo está armado todo | [arquitectura.md](../arquitectura.md#7-capa-de-agentes) |
| el plan y el estado del trabajo | [plan_mcp_cli.md](../plan_mcp_cli.md) |

## Dos modos de trabajo

- **Sin ventana** (por defecto): el agente tiene su propio documento en memoria. Rápido; sirve para pruebas y no necesita la app.
- **En vivo**: la app está abierta y el agente controla ese documento; vos ves cada cambio. Hay que encenderlo a mano. Ver [puente.md](puente.md).

## Cómo responden las herramientas

```
{"ok": true, "result": {...}, "avisos": [...]}
{"ok": false, "error_kind": "OPERATION_FAILED", "mensaje": "...", "pistas": ["..."]}
```

- Decidí con `error_kind` (fijo, en inglés). El `mensaje` y las `pistas` están en español y dicen qué probar.
- Una herramienta que modifica es **un** paso de deshacer y es atómica: si falla, el documento queda igual.
- Las imágenes vuelven como imagen (MCP) o como archivo PNG (CLI): nunca como texto en base64.

## Estado de lo probado

- Probado: la CLI (tests con subproceso), el servidor MCP con un cliente en memoria, los ejemplos (corren dentro de pytest) y que el comando del servidor arranca por stdio.
- **No probado** con el cliente real: ninguna de las configuraciones de [conectar.md](conectar.md). Cada una lo dice.

## Para quien desarrolla el programa

- Las reglas y las recetas están en [AGENTS.md](../../AGENTS.md).
- Verificar un cambio: `omnicad dev check` ([cli.md](cli.md#dev)), o `run_checks` en el MCP con `--dev`.
- Este directorio se mantiene con el programa: `herramientas.md` se regenera con `omnicad tools --markdown --output docs/agentes/herramientas.md` y un test avisa si quedó viejo.
