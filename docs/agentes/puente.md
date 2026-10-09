# El modo en vivo: el puente entre la app y el agente

Con el puente encendido, el agente controla la ventana de OmniCAD que está **abierta**. Vos ves cada cambio mientras
lo hace. Son las mismas herramientas que sin ventana ([herramientas.md](herramientas.md)).

| | Sin ventana | En vivo |
|---|---|---|
| Documento | uno propio del servidor MCP, en memoria | el que está abierto en la ventana |
| Hace falta la app abierta | no | sí, con el puente encendido |
| Se ve el cambio | no (se pide una imagen) | sí, en la ventana |
| Cuándo se usa | con `--modo sin_ventana`, o con `auto` si la app no está | con `--modo vivo`, o con `auto` si la app está escuchando |

## Encenderlo

Viene **apagado**. Dos formas:

- Al abrir la app: `clon/.venv/Scripts/python.exe clon/OmniCAD.py --puente`.
- Con la app abierta: Preferencias › General › «Permitir que agentes IA controlen OmniCAD (MCP en vivo)» (preferencia `general/puente_agentes`).

Si no se puede encender (por ejemplo, ningún puerto libre), la app lo avisa en el log y sigue funcionando sin puente.

Para apagarlo: destildá la preferencia o cerrá la app.

## Cómo se protege

- Escucha **solo en 127.0.0.1**, nunca en otra interfaz. Puerto 27191; si está ocupado, uno de los 10 siguientes.
- Un **token aleatorio por arranque**. Está en `%LOCALAPPDATA%/OmniCAD/puente.json`, el único lugar donde se consigue:

```
{"port": 27191, "token": "…", "pid": 1234, "version": "0.1.0", "protocol": 1}
```

- El archivo se borra al apagar el puente (y solo si sigue siendo el de esa app).
- Un token incorrecto da `UNAUTHORIZED` y se corta la conexión.
- La barra de estado muestra un indicador siempre que el puente está encendido:
  - «Puente IA activo» (gris): espera agentes.
  - «● Agente IA conectado» (verde, con el número si son varios): hay un agente controlando.
- Cada llamada que **modifica** es un paso de deshacer (Ctrl+Z lo saca) y deja en la barra el aviso «Agente IA: extrude → Extrusión3».

## El servidor MCP y sus modos

`--modo` se agrega a las opciones del servidor ([conectar.md](conectar.md)):

| `--modo` | Qué hace |
|---|---|
| `auto` (por defecto) | en cada llamada mira si la app está escuchando: si está, trabaja en vivo; si no, sobre un documento propio sin ventana. Cuando cambia de uno a otro lo dice en `avisos`, porque pasó a **otro documento** |
| `vivo` | siempre la app. Si no está abierta con el puente, falla con `APP_NOT_RUNNING` |
| `sin_ventana` | siempre un documento propio; nunca toca la ventana |

- `--doc RUTA` abre un proyecto y **fuerza** `sin_ventana`: es una sesión propia. Combinarlo con `--modo vivo` es un error.
- En `auto` conviene empezar con `get_mode`: dice en qué modo está trabajando antes de cambiar nada.

### `get_mode`

Existe **solo** en los modos `vivo` y `auto` (no está en el catálogo de [herramientas.md](herramientas.md)). Devuelve:

| Clave | Qué es |
|---|---|
| `configured` | el modo pedido con `--modo` |
| `active` | `vivo`, `sin_ventana` o `null` (en `vivo`, sin app) |
| `app` | el estado de la app (abajo), o `null` si no hay |
| `explanation` | una frase que dice qué documento está tocando el agente |

El estado de la app (`app`): `document`, `path`, `modified`, `bodies`, `timeline_steps`, `busy`, `busy_reason`,
`command_open`, `sketch_open`, `execute_code_allowed` y `agents_connected`, más `version`, `protocol`, `pid` y `port`.

## Qué cambia en vivo

- **`new_document` y `open_document`** cambian lo que muestra la ventana. Si el documento de la ventana tiene cambios sin guardar, fallan con `UNSAVED_CHANGES`: no se descarta nada.
- **`execute_code` está apagado** salvo que se active Preferencias › General › «Permitir también execute_code en vivo» (`general/puente_codigo`). Corre Python dentro de la ventana: un bucle infinito la congelaría, con tu trabajo adentro. Sin ventana no tiene ese riesgo.
- **`get_viewport_image`** en vivo usa el mismo render por software que sin ventana. Para ver la interfaz tal como la ves vos, `app_screenshot` (grupo `dev`).
- **El grupo `dev` nunca corre en vivo**: corre en el proceso del servidor MCP (pytest, capturas).
- Las herramientas que **solo leen** funcionan siempre. Las que **modifican** se rechazan con `APP_BUSY` si estás usando la app (abajo).

## Errores del modo en vivo

Se suman a los errores de la API ([guia_diseno.md](guia_diseno.md)). Siempre vuelven como `{"ok": false, "error_kind", "mensaje", "pistas"}`.

| `error_kind` | Cuándo | Qué hacer |
|---|---|---|
| `UNAUTHORIZED` | el token no coincide con el de `puente.json` | volver a leer `puente.json` (la app se reinició) |
| `APP_BUSY` | una herramienta que **modifica** llegó mientras tenés un comando abierto, editás un boceto, elegís un plano en la vista o hay un diálogo modal | esperar o pedirle al usuario que termine; las de lectura siguen andando |
| `APP_NOT_RUNNING` | no hay app escuchando según `puente.json` | abrir OmniCAD con `--puente`, o usar `--modo sin_ventana` |
| `APP_NOT_RESPONDING` | la app no contestó en 120 s (se corta esa conexión) | revisar si la app está colgada; reintentar |
| `UNSAVED_CHANGES` | `new_document` u `open_document` con cambios sin guardar en la ventana | guardar en la ventana, o pedirle al usuario que decida |
| `LIVE_NOT_ALLOWED` | `execute_code` sin la preferencia `general/puente_codigo`, o una herramienta del grupo `dev` | usar herramientas normales; para `dev`, correr sin pasar por el puente |
| `BRIDGE_ERROR` | se cortó la conexión a mitad de una llamada, o la respuesta vino mal | **no se sabe si se aplicó**: mirar `get_scene_info` o `get_timeline` antes de repetir |

## El grupo `dev` del MCP

Solo con `--dev` (no está en los grupos por defecto). Son del servidor, no de la ventana:

| Herramienta | Qué hace |
|---|---|
| `run_checks` | corre ruff, pytest y la prueba de humo y resume cada paso. Se niega si lo llama la propia verificación que lanzó (`NESTED_CHECKS`) |
| `app_screenshot` | abre la ventana real en otro proceso, la captura entera y la cierra |

Equivalentes en la terminal: `omnicad dev check` y `omnicad dev screenshot` ([cli.md](cli.md#dev)).

## Limitaciones

- Hay **un solo** `puente.json`: si abrís dos OmniCAD con el puente encendido, gana la última. Al cerrar una app no se borra el archivo de la otra.
- El agente toca un solo documento a la vez: el de la ventana.
- La CLI (`omnicad`) no tiene modo en vivo: siempre trabaja sobre el archivo.

## Hablarle al puente sin MCP

Es un protocolo de líneas JSON en UTF-8 por TCP local (un objeto por línea, terminado en `\n`). Está en `clon/omnicad/api/protocolo_puente.py`.

```
→ {"id": 1, "token": "…", "tool": "create_box", "args": {"length": 20, "width": 20, "height": 10}}
← {"id": 1, "ok": true, "result": {…}, "avisos": []}
```

- La respuesta es la de `api.llamar` más el `id`. Las imágenes viajan como `{"png_base64", "width", "height"}`.
- Pedidos especiales, que no son herramientas del catálogo: `ping` y `status`.
- Esta vía **no se probó** al escribir esta página. Lo normal es usar el servidor MCP, que ya sabe hacerlo.
