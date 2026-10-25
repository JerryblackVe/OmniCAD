# Plan: Asistente IA dentro de OmniCAD (chat que diseña con el usuario)

> Este archivo es la especificación. Lo que falta de cada ID (`IA-1…IA-8`) está en
> [docs/seguimiento/faltantes.md](seguimiento/faltantes.md) › «Asistente IA». Si algo de acá no coincide con el
> seguimiento, vale el seguimiento.

Fecha: 2026-10-25. Estado: **fases 1 a 9 ejecutadas el 2026-10-25** (commits `f60d51b` a `4e981c0`). Lo que queda vive en `docs/seguimiento/faltantes.md` › «Asistente IA» (IA-2 Parcial: streaming y prueba real por API).

## Objetivo

Un panel de chat dentro de la ventana, como el **Autodesk Assistant** de Fusion, donde el usuario escribe en español
y la IA:

- **explica** («¿por qué mi boceto está sobre-restringido?», «¿dónde está el vaciado?»);
- **muestra** («¿cuánto pesa esto?», «seleccioná los cuerpos de la tapa»), sin cambiar nada;
- **guía** paso a paso, preguntando antes de cada cambio;
- **hace** («empalme de 2 mm en todas las aristas de la Caja»): muestra el plan, el usuario aprueba y se ejecuta.

La IA se conecta de dos formas: **con clave de API** (paga por uso) o **con la suscripción** que el usuario ya tiene
(Claude Code o Codex instalados en su PC).

## Cómo lo hace Fusion (referencia)

Fuente: `docs/fusion_docs/contenido/fusion-autodesk-assistant/` y `fusion-visor/navigate-the-assistant-panel-*.md`
(buscar con `scripts/fusion_docs.py buscar assistant`).

| Fusion | OmniCAD |
|---|---|
| Botón **Autodesk Assistant** a la derecha de la barra de la aplicación, y en el menú Ayuda | Botón **Asistente** en el mismo lugar y en Ayuda |
| Panel acoplado a la derecha del lienzo, queda abierto mientras trabajás | `QDockWidget` a la derecha |
| Saludo, campo «Ask Autodesk Assistant», flecha de enviar o Enter | Igual: «Preguntale al Asistente» |
| Menú **Chat**: biblioteca de prompts e historial | Igual, el historial queda en la PC (no hay nube) |
| **+** para un chat nuevo | Igual |
| Estrella con el aviso «es IA, puede equivocarse» | Igual |
| Tres niveles: *Show me* (mirar), *With me* (guiar), *For me* (hacer tras aprobar) | Modos **Mostrar · Guiar · Hacer** (más *Explicar*) |
| **Cancel** mientras trabaja | Botón Cancelar: corta y deshace lo que quedó a medias |
| Tokens Flex por mes | Tokens y costo en USD por pedido, con tope configurable |

## Datos verificados que sostienen el plan

| Dato | Evidencia |
|---|---|
| Hay 324 herramientas en un catálogo único, cada una con su JSON Schema (`esquema`) y si modifica (246 modifican). Sirven tal cual como definición de herramientas para el modelo. | `api.catalogo()` → claves `nombre, grupo, descripcion, esquema, modifica` (2026-10-25) |
| `api.llamar(sesion, nombre, args)` nunca lanza y devuelve `ok/result/avisos` o `error_kind/mensaje/pistas`: es el formato ideal para devolverle al modelo. | `clon/omnicad/api/registro.py:285` |
| El puente en vivo ya ejecuta herramientas sobre la ventana abierta con todas las reglas: rechaza las que modifican si el usuario está en un comando (`APP_BUSY`), bloquea el grupo `dev` y `execute_code`, y refresca título, recientes y autoguardado. | `clon/omnicad/ui/puente.py:264` (`PuenteAgentes.ejecutar`) |
| Ya hay guía para agentes (ciclo de trabajo, selectores, unidades): es la base del prompt de sistema. | `clon/omnicad/api/guia/*.md` (215 líneas) y `get_guide` |
| Captura del visor para mandarle imágenes al modelo. | `ui/ventana.py:1531` (`capturar_visor`) |
| No hay dependencias de HTTP ni de llavero: `httpx`, `keyring`, `anthropic` y `openai` NO están en el venv. | `import` falla (2026-10-25); `clon/requirements.txt` |
| En esta PC están `claude` (Claude Code; su login de terminal estaba cerrado: `claude auth status` → `loggedIn: false`), `opencode` y Codex: la app de la Microsoft Store (`OpenAI.Codex`) trae la CLI en `<InstallLocation>/app/resources/codex.exe` (`codex-cli 0.164.0`, «Logged in using ChatGPT»), fuera del PATH; la ruta sale de `Get-AppxPackage OpenAI.Codex`. No están `gemini` ni Ollama (el PATH nombra `AppData/Local/Programs/Ollama`, pero la carpeta no existe). | `which`, `Get-AppxPackage`, `codex login status` (2026-10-25) |
| Claude Code corre sin ventana con `-p --output-format stream-json`, y acepta `--mcp-config`, `--strict-mcp-config`, `--allowedTools`, `--append-system-prompt`, `--resume`. | `claude --help` (2026-10-25) |
| OpenCode corre sin ventana con `opencode run --format json`, `-m proveedor/modelo`, `--variant`, `-s sesión`. | `opencode run --help` (2026-10-25) |
| Codex corre sin ventana con `codex exec --json` y se loguea con «Sign in with ChatGPT» (suscripción). | learn.chatgpt.com/docs/non-interactive-mode (2026-10-25) |
| ⚠ Anthropic no permite que una app de terceros ofrezca el login de claude.ai ni rutee pedidos por planes Free/Pro/Max en nombre del usuario, ni que guarde sus credenciales. | code.claude.com/docs/en/legal-and-compliance (2026-10-25) |

## Decisiones (tomadas, con su motivo)

1. **El asistente usa las MISMAS herramientas del catálogo**, ejecutadas por `PuenteAgentes.ejecutar`. Cero
   herramientas nuevas para diseñar: lo que puede un agente por MCP lo puede el asistente, con las mismas reglas
   (`APP_BUSY`, sin `dev`, sin `execute_code` salvo la preferencia `general/puente_codigo`).
2. **Núcleo sin Qt en `clon/omnicad/asistente/`**: proveedores, bucle, prompt e historial se prueban sin ventana.
   La UI (`ui/asistente.py`) solo muestra y manda eventos. Mismo criterio que `api/`.
3. **Sin dependencias nuevas para hablar con la API**: `urllib.request` de la biblioteca estándar, con lectura de
   eventos SSE, en un hilo aparte (`QThread` del lado de la UI). Los SDK oficiales no hacen falta para dos
   formatos de mensaje.
4. **Dos formatos de API cubren casi todo**:
   - **Anthropic Messages** (Claude por clave de API).
   - **OpenAI compatible** (OpenAI, OpenRouter, Ollama y LM Studio locales: la misma forma de `tools`).
5. **La suscripción se usa lanzando el agente que el usuario ya instaló y logueó**, nunca con un login propio:
   - **Claude Code**: `claude -p --output-format stream-json --mcp-config <omnicad en vivo> --strict-mcp-config
     --allowedTools "mcp__omnicad__*"`.
   - **Codex**: `codex exec --json` con OmniCAD como servidor MCP.
   - **OpenCode**: `opencode run --format json`.

   El agente externo se conecta al puente en vivo (`omnicad-mcp --modo en_vivo`) y el panel solo dibuja los
   eventos que el proceso imprime. OmniCAD nunca ve, pide ni guarda credenciales de la suscripción.
6. **No se mandan las 324 herramientas juntas** (demasiadas confunden al modelo y gastan tokens): va un núcleo fijo
   de unas 25 (las del ciclo de `api/guia/flujo.md`: mirar, bocetar, extruir, empalme, medir, imagen, deshacer,
   `describe_operation`, `run_operation`) más una herramienta `buscar_herramientas(tema)` que suma las de un
   grupo cuando hacen falta.
7. **Cada pedido es un grupo de deshacer**: un marcador antes de empezar; «Deshacer este pedido» vuelve ahí.
   Cancelar también vuelve ahí.
8. **Claves de API**: en el llavero del sistema (`keyring`, **requiere permiso para instalar**). Mientras tanto:
   variables de entorno (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`). Nunca en QSettings en texto
   plano, ni en el `.omnicad`, ni en el historial, ni en logs.
9. **Historial local**: un JSON por chat en `carpeta_datos()/asistente/`. Nada sale de la PC salvo lo que se manda
   al proveedor elegido.
10. **Gasto visible**: cada respuesta muestra tokens y costo en USD que reporta la API; tope por pedido configurable
    (por defecto 0,50 USD) que corta el bucle. Los modelos locales (Ollama) muestran solo tokens.

## Arquitectura

```
ui/asistente.py (QDockWidget)              ui/preferencias.py › pestaña «Asistente IA»
   │  eventos: texto, herramienta, imagen, plan, uso, error
   ▼
asistente/sesion_chat.py ── historial.py (JSON local)
   │
   ├─ modo API:     bucle.py ──► proveedores/anthropic.py | proveedores/openai_compat.py
   │                   │   (urllib + SSE)
   │                   └─► ejecutar(herramienta, args) = PuenteAgentes.ejecutar  ──► api.llamar
   │
   └─ modo suscripción: proveedores/agente_local.py (subprocess: claude | codex | opencode)
                           └─► omnicad-mcp --modo en_vivo ──► puente (127.0.0.1 + token) ──► api.llamar

asistente/prompt.py: prompt de sistema = guía de api/guia + estado del documento + modo + reglas
asistente/herramientas.py: núcleo fijo + buscar_herramientas, desde api.catalogo()
```

## Interfaz

- **Ícono**: destello + globo de diálogo, en `ui/iconos_extra.py` (`_asistente`), con versión clara y oscura.
- **Dónde**: botón a la derecha de la barra de la aplicación (como Fusion), ítem en **Ayuda › Asistente**, comando
  en la búsqueda de comandos y un atajo libre (el test de atajos no tiene que encontrar choques).
- **Panel**: cabecera con proveedor y modelo, **+** (chat nuevo), menú **Chat** (biblioteca de prompts, historial),
  estrella con el aviso de IA. Abajo: selector de modo (Explicar · Mostrar · Guiar · Hacer), campo de texto
  multilínea (Enter envía, Mayús+Enter salta de línea), Enviar / Cancelar.
- **Mensajes**: texto con markdown simple; cada herramienta usada como una línea plegable («✓ extrude → op5»,
  «✗ fillet: OPERATION_FAILED»); miniaturas del visor; tarjeta de **plan** con Aplicar / Cancelar en modo Hacer;
  pie con tokens y costo.
- **Ventana chica**: tiene que entrar en 1024×640 y 800×520 (regla de prueba 8).
- **Adjuntos** (pedido de Gerardo, 2026-10-25): botón con ícono de clip al lado del campo para subir **PDF, imágenes (PNG, JPG), vectores (SVG) y DXF**; **hasta 10 adjuntos** por mensaje; **Ctrl+V pega una imagen del portapapeles** en el campo; también arrastrar y soltar. Cada adjunto se ve como una ficha chica (miniatura o ícono, nombre, ✕ para quitarlo) arriba del campo. Detalle en la fase 9.
- **Preferencias › Asistente IA**: proveedor, modelo, esfuerzo, clave (campo oculto + «Probar conexión»), modo por
  defecto, tope de gasto, «mandar imágenes del visor» (sí/no), ruta del ejecutable para Claude Code / Codex /
  OpenCode (autodetectada).

## Prompt de sistema (el «promter»)

Se arma en cada pedido, corto, en `asistente/prompt.py`:

1. **Rol y reglas fijas**: asistente de OmniCAD, responde en español, mm y grados, un cambio por vez, mira la imagen
   después de cada cambio, pregunta antes de borrar, guardar encima o exportar fuera de la carpeta del proyecto.
2. **Guía**: `api/guia/flujo.md` y `selectores.md` (lo mismo que lee un agente por MCP).
3. **Estado actual**: nombre del documento, unidades, cuerpos, parámetros, último paso del timeline, selección del
   usuario (`leer_seleccion`) y si hay un comando abierto.
4. **Modo**: Explicar (sin herramientas que modifican), Mostrar (solo lectura + seleccionar), Guiar (propone y espera
   el OK de cada paso), Hacer (plan → OK → ejecuta).
5. **Biblioteca de prompts**: archivo editable `asistente/prompts.json` con pedidos de ejemplo por espacio de trabajo.

Lo que viene del documento (nombres de cuerpos, notas, texto de un SVG importado) se marca como **dato**, no como
instrucción: defensa contra inyección de prompt.

## Seguridad

- Las herramientas que modifican pasan por `PuenteAgentes.ejecutar`: mismas reglas que un agente externo.
- `execute_code` y el grupo `dev` quedan afuera del asistente por defecto.
- Tope de vueltas por pedido (por defecto 25) y tope de gasto.
- Claves solo en llavero o entorno; un test verifica que no aparecen en el historial ni en el `.omnicad`.
- Modo suscripción: el proceso hijo hereda el token del puente por el `mcp-config` temporal (borrado al terminar),
  nunca por la línea de comandos visible.
- Modo suscripción con Claude Code: **decidido por Gerardo el 2026-10-25, se programa** (OmniCAD lanza el `claude`
  que el usuario ya instaló y logueó; nunca ve sus credenciales). Ver el ⚠ de «Datos verificados».

## MCP y CLI (regla estricta)

- El chat es un panel: se anota en `docs/brechas_mcp.md` con su razón (un agente externo ya ES el asistente; no
  necesita hablar con otro).
- Lo que sí va al catálogo (`api/herramientas_asistente.py`, grupo `asistente`, fuera de los grupos por defecto del
  MCP porque gasta plata):
  - `get_assistant_config` / `set_assistant_config` (proveedor, modelo, modo, tope; **nunca la clave**);
  - `assistant_ask(prompt, mode)`: corre un pedido sin ventana con el proveedor configurado. Da la CLI
    `omnicad assistant_ask "hacé una caja de 40 mm con empalme de 3"`.
- Grupo nuevo → también en `GRUPOS_CONOCIDOS` de `servidor_mcp/servidor.py` y en `docs/agentes/cli.md` y
  `conectar.md` (lección del 2026-10-20).

## Fases

| # | ID | Fase | Archivos principales | Modelo y esfuerzo | Listo cuando |
|---|---|---|---|---|---|
| 1 | IA-1 | Núcleo sin Qt: interfaz `Proveedor`, `bucle.py`, `herramientas.py` (núcleo + `buscar_herramientas`), proveedor falso para tests | `omnicad/asistente/` | Opus, alto | Con el proveedor falso: un pedido crea una caja, mira la imagen y se detiene; error de herramienta vuelve al modelo; tope de vueltas corta; tests < 3 s, sin red |
| 2 | IA-2 | Proveedores por API: Anthropic Messages y OpenAI compatible (OpenAI, OpenRouter, Ollama) con SSE, herramientas, imágenes y uso | `asistente/proveedores/` | Sonnet, medio | Tests con respuestas grabadas (sin red ni gasto); prueba real con Ollama local; prueba paga **solo con OK de Gerardo** |
| 3 | IA-3 | Prompt de sistema, contexto del documento, modos y biblioteca de prompts | `asistente/prompt.py`, `asistente/prompts.json` | Opus, alto | Modo Explicar y Mostrar nunca llaman herramientas que modifican (test); el contexto entra en < 2000 tokens con un documento de 50 pasos |
| 4 | IA-4 | Panel, ícono, botón, menú Ayuda, atajo y pestaña de Preferencias; claves por entorno (llavero si se aprueba `keyring`) | `ui/asistente.py`, `ui/iconos_extra.py`, `ui/ventana.py`, `ui/preferencias.py` | Sonnet, medio | Humo OK; pieza nueva `asistente` en `scripts/prueba_ui/` (teclear, Enter, Esc, Cancelar, ventana chica) |
| 5 | IA-5 | Permisos y deshacer: tarjeta de plan, «Deshacer este pedido», Cancelar con vuelta atrás, tope de gasto, `APP_BUSY` visible en el chat | `asistente/sesion_chat.py`, `ui/asistente.py` | Opus, alto | Cancelar a mitad deja el documento como antes (test); en modo Hacer nada se ejecuta sin Aplicar. Se apoya en CL1 si ya existe |
| 6 | IA-6 | Suscripción vía agente local: Claude Code, Codex y OpenCode por el puente en vivo, eventos JSON al panel | `asistente/proveedores/agente_local.py` | Opus, alto | Con `claude` y `opencode` de esta PC: un pedido modifica la ventana y el panel muestra cada herramienta; sin el ejecutable, mensaje claro |
| 7 | IA-7 | Historial de chats, herramientas `get/set_assistant_config` y `assistant_ask`, doc regenerada | `asistente/historial.py`, `api/herramientas_asistente.py`, `servidor_mcp/servidor.py`, `docs/agentes/` | Sonnet, medio | Reabrir un chat viejo; `omnicad assistant_ask` anda sin ventana; `test_doc_agentes` y test de que la clave no aparece en ningún archivo |
| 8 | IA-8 | Respuestas de ayuda («¿cómo se hace…?») con la documentación local de OmniCAD, citando la fuente | `asistente/ayuda.py` | Sonnet, medio | Busca en `docs/guia_comandos.md`, `api/guia/` y `docs/agentes/herramientas.md`; cada respuesta cita archivo |
| 9 | IA-9 | Adjuntos en el chat: ícono de clip, PDF, imágenes, SVG y DXF, hasta 10 por mensaje, pegar imagen del portapapeles (Ctrl+V) y arrastrar y soltar | `ui/asistente.py`, `asistente/adjuntos.py`, `asistente/proveedores/` | Opus, alto | La IA recibe cada adjunto: imágenes como imagen; PDF como documento nativo (Anthropic `document`, OpenAI `file`) o aviso claro si el proveedor no lo acepta; SVG y DXF con una vista previa en imagen más su ruta, para que pueda usar `insert_svg` / `insert_dxf`; el 11.º adjunto se rechaza con mensaje; tope de tamaño por archivo y solo extensiones permitidas (archivos de otros: validar, nunca ejecutar); en modo suscripción, la ruta en el pedido; prueba de usuario con clic en el clip, Ctrl+V de una imagen y arrastre |

## Orden y dependencias

- **1 → 2 → 3** en orden: el bucle define la interfaz que implementan los proveedores, y el prompt se prueba con un
  proveedor real.
- **4** puede empezar junto con 2 (archivos distintos), contra el proveedor falso.
- **5** después de 4 (usa el panel). **6** después de 4 (dibuja en el panel) y de la decisión de Gerardo.
- **7 y 8** al final, en cualquier orden.
- **9** (adjuntos) después de 7: usa el panel y los proveedores ya cerrados.

## Pendiente de decidir (Gerardo)

1. Instalar `keyring` para guardar claves en el llavero del sistema (o quedarse con variables de entorno).
2. ~~Modo suscripción con Claude Code~~: decidido el 2026-10-25, se programa como está en el plan.
3. Cualquier prueba que gaste plata en una API.

## Fuera de alcance

- Login propio con cuentas de Anthropic u OpenAI (prohibido o innecesario: ver decisión 5).
- Generar imágenes o renders con IA (Fusion lo tiene como «AI visualizations»): plan aparte si se pide.
- Historial en la nube.
