# Conectar un agente al MCP de OmniCAD

Bloques listos para copiar. Hay uno por cliente.

> **Ninguna de estas configuraciones se probó todavía con el cliente real.** Cada sección lo dice ("no probado").
> Lo que sí se verificó: el formato de cada cliente contra su documentación oficial (fuente al pie de cada sección)
> y que el comando del servidor arranca por stdio y lista las herramientas (1,3 s en esta PC).

## Atajo: `omnicad setup` (Claude Code y OpenCode)

Registra el MCP y copia la skill `omnicad` sin editar nada a mano.

```
omnicad setup --cliente todos            # solo MUESTRA qué haría (no escribe nada)
omnicad setup --cliente todos --aplicar  # lo hace: respalda cada archivo con .bak y no borra otros servidores
```

- `--cliente claude-code | opencode | fusion | todos`. Correrlo dos veces no duplica nada.
- Fusion 360: copia el complemento OmniCADPuente a la carpeta AddIns DEL USUARIO (`%APPDATA%/Autodesk/Autodesk Fusion 360/API/AddIns/`;
  nunca a la instalación de Fusion). Arranca solo con Fusion; la primera vez, reiniciá Fusion o ejecutalo en Utilidades ›
  Complementos (Mayús+S). Con eso, `open_document` y Archivo › Abrir abren `.f3d` y `.f3z` (forma + parámetros de usuario).
- Claude Code: usa `claude mcp add --scope user`; la skill va a `~/.claude/skills/omnicad/`.
- OpenCode: suma `mcp.omnicad` a `~/.config/opencode/opencode.jsonc` (o `.json`). Con `todos`, la skill queda solo en
  `~/.claude/skills/` porque OpenCode también lee esa carpeta (dos copias darían «duplicate skill name»).
- Los otros clientes se configuran a mano con los bloques de abajo.

## El comando del servidor

Dentro de cada configuración va uno de estos dos comandos. Los dos hacen lo mismo.

| Forma | Comando |
|---|---|
| Con el Python del venv (recomendada) | `D:/PROGRAMA/clon/.venv/Scripts/python.exe -m omnicad.servidor_mcp` |
| Con el comando instalado | `D:/PROGRAMA/clon/.venv/Scripts/omnicad-mcp.exe` |

- Usá **rutas absolutas**: los clientes lanzan el servidor desde otra carpeta.
- Escribí las rutas con barras `/`, incluso en Windows: evita tener que duplicar las barras invertidas en JSON y TOML.
- Todos los bloques de abajo usan la primera forma. Para la segunda: `"command": "D:/PROGRAMA/clon/.venv/Scripts/omnicad-mcp.exe"` y sin `args`.
- El nombre del servidor es `omnicad`. No le pongas guiones bajos ni espacios: algunos clientes arman con él el nombre de cada herramienta.
- El servidor habla por stdio. No imprime nada en stdout que no sea del protocolo; sus mensajes van a stderr.

## Opciones del servidor

Se agregan a `args` (o al comando). Todas son opcionales.

| Opción | Qué hace |
|---|---|
| `--doc RUTA` | abre ese proyecto `.omnicad` al arrancar (trabaja sin ventana) |
| `--toolsets LISTA` | solo estos grupos, separados por coma. Por defecto: `documento,parametros,boceto,solido,inspeccion,avanzado` |
| `--modo auto\|vivo\|sin_ventana` | de dónde salen las herramientas; por defecto `auto`. Ver [puente.md](puente.md) |
| `--dev` | suma el grupo `dev` (`run_checks`, `app_screenshot`, `run_bench`). Ver [puente.md](puente.md) y [cli.md](cli.md) |
| `--http` y `--port N` | sirve por HTTP en `127.0.0.1` (puerto por defecto 27190, ruta `/mcp`) en vez de stdio |
| `--log-level NIVEL` | `DEBUG`, `INFO`, `WARNING` (por defecto) o `ERROR`, siempre a stderr |

Ejemplo de `args` con opciones: `["-m", "omnicad.servidor_mcp", "--toolsets", "documento,boceto,solido,inspeccion"]`.

## Cómo saber que anda

1. El cliente lista el servidor `omnicad` como conectado.
2. Pedile al agente `get_scene_info`: tiene que devolver un documento vacío.
3. Pedile `get_guide` con `topic="flujo"`: tiene que devolver la guía ([guia_diseno.md](guia_diseno.md)).

Si el cliente no conecta, probá el comando solo en una terminal. Tiene que quedar esperando sin imprimir errores:

```
D:/PROGRAMA/clon/.venv/Scripts/python.exe -m omnicad.servidor_mcp --log-level INFO
```

Si no conecta o tarda: probá subir el tiempo de arranque del cliente (hay un campo `timeout` o similar en varios de abajo).

---

## Claude Code

**Estado: no probado.**

- Por comando (alcance `local`: solo este proyecto, queda en `~/.claude.json`):

```
claude mcp add omnicad -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m omnicad.servidor_mcp
```

- Para compartirlo con el equipo: agregá `--scope project` (escribe `.mcp.json` en la raíz del proyecto; Claude Code pide aprobación la primera vez). Para todos tus proyectos: `--scope user`.
- El separador `--` es obligatorio: todo lo que va después es el comando del servidor.
- Por archivo: `.mcp.json` en la raíz del proyecto.

```json
{
  "mcpServers": {
    "omnicad": {
      "command": "D:/PROGRAMA/clon/.venv/Scripts/python.exe",
      "args": ["-m", "omnicad.servidor_mcp"]
    }
  }
}
```

- Verificar: `claude mcp list` (tiene que decir Connected), `claude mcp get omnicad`, o `/mcp` dentro de Claude Code.
- Quitar: `claude mcp remove omnicad`.

Fuente: <https://code.claude.com/docs/en/mcp> (sintaxis de `claude mcp add`, alcances, aprobación del alcance project y `claude mcp list`). El bloque `.mcp.json` con `command` y `args` está en la documentación del Agent SDK (<https://code.claude.com/docs/en/agent-sdk/mcp>). No encontré una nota específica de Windows.

## Claude Desktop

**Estado: no probado.**

- Archivo: `%APPDATA%\Claude\claude_desktop_config.json`. Se abre desde Ajustes › Developer › Edit Config (lo crea si no existe).
- Si el archivo ya tiene contenido, sumá solo la clave `omnicad` dentro de `mcpServers`.

```json
{
  "mcpServers": {
    "omnicad": {
      "command": "D:/PROGRAMA/clon/.venv/Scripts/python.exe",
      "args": ["-m", "omnicad.servidor_mcp"]
    }
  }
}
```

- Después de guardar: cerrá Claude Desktop del todo y abrilo de nuevo.
- Logs del servidor: `%APPDATA%\Claude\logs\mcp-server-omnicad.log` (y `mcp.log` para la conexión).
- Ojo: el ejemplo oficial para Windows escribe las rutas con barras invertidas dobles (`C:\\Users\\...`). Acá usé `/`; es JSON válido y Windows lo acepta, pero **no está confirmado en Claude Desktop**. Si falla, probá con `D:\\PROGRAMA\\clon\\.venv\\Scripts\\python.exe`.

Fuente: <https://modelcontextprotocol.io/docs/develop/connect-local-servers> (ubicación del archivo, formato `mcpServers`, logs).

## OpenCode

**Estado: no probado.**

- Archivo del proyecto: `opencode.json` en la raíz (tiene prioridad). Global: `~/.config/opencode/opencode.json` o
  `opencode.jsonc` (en Windows, `C:\Users\<usuario>\.config\opencode\`, confirmado con `opencode debug paths`).
- Más simple: `omnicad setup --cliente opencode --aplicar` (ver arriba).
- Si ya existe, sumá solo la clave `omnicad` dentro de `mcp`.
- `command` es una lista (el comando y sus argumentos juntos), no un texto más una lista.
- `timeout` está en milisegundos y es lo que espera OpenCode para pedir las herramientas (por defecto 5000). El servidor tardó 1,3 s en arrancar en esta PC; 30000 deja margen para un arranque en frío.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "omnicad": {
      "type": "local",
      "command": ["D:/PROGRAMA/clon/.venv/Scripts/python.exe", "-m", "omnicad.servidor_mcp"],
      "enabled": true,
      "timeout": 30000
    }
  }
}
```

- Verificar: `opencode mcp ls`.
- Apagarlo sin borrarlo: `"enabled": false`.

Fuente: <https://opencode.ai/docs/mcp-servers> (opciones `type`, `command`, `enabled`, `environment`, `timeout`), <https://opencode.ai/docs/config> (ubicaciones) y <https://opencode.ai/docs/cli> (`opencode mcp ls`).

## Codex CLI

**Estado: no probado.**

- Archivo: `~/.codex/config.toml` (en Windows, `%USERPROFILE%\.codex\config.toml`). También sirve `.codex/config.toml` dentro del proyecto, pero solo si el proyecto es de confianza.
- Cada servidor es una tabla `[mcp_servers.<nombre>]`.
- `startup_timeout_sec` es el tiempo que tiene el servidor para arrancar (por defecto 10).

```toml
[mcp_servers.omnicad]
command = "D:/PROGRAMA/clon/.venv/Scripts/python.exe"
args = ["-m", "omnicad.servidor_mcp"]
startup_timeout_sec = 30
```

- Por comando (equivale a lo de arriba, sin el tiempo de arranque): `codex mcp add omnicad -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m omnicad.servidor_mcp`
- Verificar: `codex mcp list`.
- No encontré una nota específica de Windows en la documentación.

Fuente: <https://learn.chatgpt.com/docs/extend/mcp?surface=cli> (el enlace <https://developers.openai.com/codex/mcp> redirige ahí).

## Cursor

**Estado: no probado.**

- Archivo del proyecto: `.cursor/mcp.json`. Global: `~/.cursor/mcp.json`.
- La documentación es inconsistente: su tabla marca `type` como obligatorio (`"stdio"`) pero sus ejemplos no lo ponen. Lo incluí.

```json
{
  "mcpServers": {
    "omnicad": {
      "type": "stdio",
      "command": "D:/PROGRAMA/clon/.venv/Scripts/python.exe",
      "args": ["-m", "omnicad.servidor_mcp"]
    }
  }
}
```

- Si algo falla: panel Output (Ctrl+Shift+U) › "MCP Logs".

Fuente: <https://cursor.com/docs/mcp> (ubicaciones, formato `mcpServers`, tabla de campos stdio). No pude confirmar dónde se ve el estado del servidor en la configuración.

## Gemini CLI

**Estado: no probado.**

- Archivo del proyecto: `.gemini/settings.json`. Del usuario: `~/.gemini/settings.json`.
- Si el archivo ya existe, sumá solo la clave `omnicad` dentro de `mcpServers`.
- `timeout` está en milisegundos.
- Los servidores stdio solo conectan en carpetas de confianza: si `gemini mcp list` los muestra como Disconnected, corré `gemini trust` en la carpeta.

```json
{
  "mcpServers": {
    "omnicad": {
      "command": "D:/PROGRAMA/clon/.venv/Scripts/python.exe",
      "args": ["-m", "omnicad.servidor_mcp"],
      "timeout": 30000
    }
  }
}
```

- Por comando: `gemini mcp add [opciones] <nombre> <comando> [args...]` (alcance `project` por defecto; `-s user` para el usuario). Con argumentos que empiezan con `-` como `-m`, la documentación usa `--` antes de ellos. **No está confirmada la forma exacta para este servidor**; si falla, usá el JSON.
- Verificar: `gemini mcp list`, o `/mcp` dentro de una sesión.
- Evitá guiones bajos en el nombre del servidor (`omnicad` está bien): rompen las reglas de políticas.

Fuente: <https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md>.

## VS Code

**Estado: no probado.**

- Archivo del proyecto: `.vscode/mcp.json`. La clave de arriba es `servers` (no `mcpServers`). Las dos páginas de la documentación que leí no coinciden: una lo presenta como el formato de VS Code y la otra lo llama "deprecated".
- Alternativa portable que la documentación prefiere para servidores nuevos: `.mcp.json` en la raíz del proyecto, con `mcpServers` (el mismo bloque que Claude Code).
- Del usuario: comando **MCP: Open User Configuration**. También existe **MCP: Add Server** y **MCP: List Servers** (para ver el estado, arrancar o reiniciar).

```json
{
  "servers": {
    "omnicad": {
      "type": "stdio",
      "command": "D:/PROGRAMA/clon/.venv/Scripts/python.exe",
      "args": ["-m", "omnicad.servidor_mcp"]
    }
  }
}
```

- Un servidor del proyecto hereda la confianza del espacio de trabajo (Workspace Trust).

Fuente: <https://code.visualstudio.com/docs/copilot/customization/mcp-servers> y <https://code.visualstudio.com/docs/agents/reference/mcp-configuration>.

---

## Otros clientes y scripts

Cualquier cliente MCP que lance un comando por stdio sirve con el mismo comando. Si no habla MCP, está la CLI: [cli.md](cli.md).
