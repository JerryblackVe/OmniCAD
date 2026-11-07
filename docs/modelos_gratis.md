# Modelos gratis para ejecutar tareas de OmniCAD

Pedido de Gerardo (2026-11-07): revisar Cline, OpenCode, Kiro, Qoder, Kilo y CodeBuddy, ver qué modelos gratis tienen
y cuáles sirven para el proyecto. Las promos gratis cambian cada semana: **antes de usar uno, repetir la prueba de
«¿responde?»** (abajo). Cuándo usar cada ejecutor lo deciden `CLAUDE.md` (tabla de modelos) y la memoria
`modelos-baratos-opencode`; acá queda solo lo medido.

## Veredicto (2026-11-07)

| Modelo | Dónde | ¿Responde hoy? | Calidad medida en OmniCAD | ¿Sirve? |
|---|---|---|---|---|
| GLM 5.3 Flash | OpenCode `opencode/glm-5.3-flash-free` | **Sí en la ventana interactiva de OpenCode** (Gerardo, 2026-11-07); en `opencode run` (modo automático) devuelve «Free usage limit reached… Free models work in OpenCode» y se cuelga reintentando | La mejor de los gratis: 1 corrección menor en 4 tareas difíciles (asas) | **Sí, para lógica y ventana**, cuando vuelva el cupo |
| DeepSeek V4.1 Flash | OpenCode `opencode/deepseek-v4.1-flash-free` | Igual que GLM: sí en la ventana, no en `opencode run` | 4 correcciones en 16 ítems; bien para lo mecánico y para confirmar reportes | **Sí, para lo mecánico**, cuando vuelva el cupo |
| Nemotron 3.5 Super VL | Cline `cline-free/nemotron-3.5-super-vl` · Kilo `kilo/nvidia/nemotron-3.5-super-vl:free` | Sí (9 s y 17 s) | Tareas chicas con tests verdes, pero no corre `ponytail-review` de verdad, deja scripts sueltos y entregó roto B-171 | **Solo tareas de pocas líneas**, revisadas por el coordinador |
| Dots3-Note Preview | Kilo `kilo/dots-studio/dots-3-note-preview:free` | Sí (15 s) | Sin tareas en el proyecto | Sin probar: preview, puede desaparecer |
| Kilo Auto (free) | Kilo `kilo/kilo-auto/free` | Sí (16 s) | Elige el modelo solo: no se sabe cuál corre | **No**: sin saber el modelo no se puede medir ni repetir |
| Nemotron 3.5 Lightning | Cline `nvidia/nemotron-3.5-lightning-free` · Kilo `kilo/nvidia/nemotron-3.5-lightning:free` | Sí (5 s y 16 s) | Sin tareas en el proyecto | Sin probar: candidato para lo mecánico (formato, docs, buscar) |
| North Mini Code (Cohere) | Kilo `kilo/cohere/north-mini-code:free` | Sí (13 s) | Sin tareas en el proyecto | Sin probar: candidato para lo mecánico |
| Nemotron 3 Ultra | Kilo `kilo/nvidia/nemotron-3-ultra-550b-a55b:free` | Sí (16 s) | Entregó un solver que no convergía (rechazado) y reportó 3 «bugs» que eran uso equivocado de la herramienta | **No** para código |
| Beam | Cline `reflection/beam-free` · Kilo `kilo/reflection/beam-free` · OpenCode | Cline y Kilo sí; OpenCode colgado | En Kilo convirtió cualquier excepción en xfail y no escribió tests; en Cline mandó una edición rota (error 400) | **No** |
| MiMo V2.6 Flash | OpenCode `opencode/mimo-v2.6-flash-free` | No (Cline: «terminó la promo»; OpenCode colgado) | La V2.5 falló dos veces el mismo día (rehízo su propia versión) | **No** |
| Step 5 Preview | Cline `cline-free/step-5-preview` | No: «terminó la promo» | — | No disponible |
| Big Pickle | OpenCode `opencode/big-pickle` | No: colgado | — | No disponible |
| GLM 5.3 | OpenCode `tokenrouter/z-ai/glm-5.3-free` | No: «Invalid token» (la clave de tokenrouter no vale) | — | No disponible; sacarlo de la configuración o renovar la clave |
| hy3, deepseek-v4.1-flash, glm-5.3, minimax-m3.1-flash y el resto | CodeBuddy | No: «credits exhausted» en todos | hy3 y deepseek: 11 tandas de UN ítem en ~10 min, todas commiteadas | **Sí cuando haya créditos**; no se compran add-ons sin pedido de Gerardo |
| Qwen3.8-Flash | Qoder `qodercli` | No: «no models available for your account» | Buen diagnóstico; dejó una regresión y un «Should fix» propio sin arreglar | **Sí, con el prompt de `arreglos_qwen.md`**, si la cuenta vuelve a tener modelos |
| qwen3-coder-next, deepseek-3.2, minimax-m2.5, glm-5 y otros | Kiro `kiro-cli` | No: «monthly usage limit has been reached» | Sin tareas en el proyecto | Sin probar; cobra créditos por modelo (de 0,05× a 1,3×) y el cupo del mes ya se usó |

### Proveedores con clave ya cargada en OpenCode

| Modelo | Dónde | ¿Responde hoy? | Calidad medida en OmniCAD | ¿Sirve? |
|---|---|---|---|---|
| MiniMax M3.1 Flash | OpenCode `nvidia/minimaxai/minimax-m3.1-flash` (NVIDIA NIM, gratis para desarrollo) | Sí (10 s) | B-185 bien hecho: test que fallaba antes y `ponytail-review` real con hallazgos (2026-11-03). P-69 (2026-11-07): arreglo, test, doc y seguimiento bien, pero se cortó a los 25 min sin correr `ponytail-review`; 2 correcciones menores del revisor (una descripción y un conteo) | **Sí: el mejor gratis disponible hoy** para bugs chicos y medianos, de a un ítem |
| GLM 5.3 Flash y DeepSeek V4.1 Flash | OpenCode `nvidia/z-ai/glm-5.3-flash`, `nvidia/deepseek-ai/deepseek-v4.1-flash` | No: colgados en la cabecera | Los mismos modelos de arriba | Volver a probar otro día: en NVIDIA suelen tener cola |
| GLM 5.3, DeepSeek, Kimi K2.7 Code, MiniMax M3 | OpenCode `ollama-cloud/*` | No: el plan gratis de Ollama Cloud solo incluye `gemma4:31b` | — | **No**: lo bueno es pago; Gemma 4 no tiene historial de código acá |

### Revisados de la lista de Gerardo (33 harnesses y 27 proveedores), 2026-11-07

| Opción | Qué se encontró | ¿Sirve? |
|---|---|---|
| Gemini CLI | Desde el 18-06-2026 no atiende cuentas gratis: pasó a Antigravity CLI ([aviso oficial](https://github.com/google-gemini/gemini-cli/discussions/27274)) | **No** (el informe pegado estaba desactualizado) |
| FreeInference (Harvard) | «New account onboarding is paused»: no se pueden crear cuentas | **No** por ahora |
| OrcaRouter | Cuenta creada por Gerardo (2026-11-07). Gratis: `z-ai/glm-5.3-flash-free`, `deepseek/deepseek-v4.1-flash-free`, `deepseek/deepseek-v4-flash-free`, `tencent/hy3-free`, `tencent/hy4-preview-free` y `orcarouter/free` (compatible con OpenAI, `https://api.orcarouter.ai/v1`; dice no entrenar con los prompts). Los gratis exigen vincular una cuenta de GitHub con antigüedad: Gerardo la vinculó y a los ~10 min GLM, DeepSeek V4.1 y hy3 respondieron (2–4 s). **Tope medido del plan gratis: entre 20 000 y 24 000 tokens de entrada por pedido.** Cargado en OpenCode como `orcarouter/<modelo>` (clave en la config global, fuera del repo), pero OpenCode falla: «This prompt is longer than the free tier allows» (su pedido base, con herramientas y skills, ya pasa el tope) | **No para agentes**: una sesión de código de OmniCAD pasa los 24 000 tokens en cuanto lee un archivo grande. **Sí para pedidos sueltos y cortos** por API (revisar un diff chico, resumir, clasificar) |
| OpenCode Go (`crouton-alpha-free`, `beam-free`, `iceman-contributor-free`) | Piden la suscripción Go o permitir que entrenen con los pedidos | **No** sin pedido de Gerardo |
| OpenRouter (de la lista de OpenCode) | `nemotron-3-nano-omni…:free` y `openrouter/free` responden; `xing4.0-29b-a4b` colgado; `deepseek-v4-flash-0731` ya no es gratis | **No**: 50 pedidos por día y modelos chicos |
| Z.ai GLM 5.3 Flash | Es pago (muy barato), no gratis | **No** sin pedido de Gerardo |
| OpenRouter `:free` | Ya hay clave; 50 pedidos por día sin créditos | **No** para agentes: una tarea usa decenas de pedidos |
| Modelos locales (Ollama, Qwen 3.6 35B, gpt-oss-20b) con OpenHands, Aider, Goose | Piden 32 GB o más y placa de video | **No** en esta PC (13 GB, gráficos integrados) |
| Frameworks (ADK, LangGraph, CrewAI, smolagents…) | No traen modelos: son para armar agentes propios | **No** aportan modelos gratis |

**Ojo con los gratis de OpenCode Zen:** en `opencode run` (lo que usan las sesiones para lanzar agentes) el cupo gratis aparece agotado aunque en la ventana interactiva anden. Sirven para que Gerardo trabaje a mano en la ventana, no para tandas automáticas. No se busca darle la vuelta: es una regla del proveedor.

**En resumen, hoy:** el mejor gratis que responde es **MiniMax M3.1 Flash por NVIDIA en OpenCode**
(`nvidia/minimaxai/minimax-m3.1-flash`). Después, **Nemotron 3.5 Super VL** (Cline o Kilo), solo para tareas chicas. Los buenos (GLM y DeepSeek en OpenCode, CodeBuddy, Qwen en
Qoder) están sin cupo. Para el trabajo de verdad siguen Sol (suscripción de ChatGPT) y, como última instancia, Claude.

## Cómo repetir la prueba

Desde una carpeta vacía (no el repo), con `</dev/null` y sin sandbox. Un modelo que solo imprime la cabecera
`> build · modelo` está sin cupo, no muerto (OpenCode reintenta en silencio por horas):

```bash
timeout 90 opencode run -m opencode/glm-5.3-flash-free "Respondé solo la palabra OK" </dev/null
timeout 90 opencode run -m nvidia/minimaxai/minimax-m3.1-flash "Respondé solo la palabra OK" </dev/null
timeout 90 kilo run -m kilo/nvidia/nemotron-3.5-super-vl:free "Respondé solo la palabra OK" </dev/null
timeout 120 cline -P cline -m cline-free/nemotron-3.5-super-vl "Respondé solo la palabra OK" </dev/null
timeout 90 codebuddy -p --model hy3 "Respondé solo la palabra OK" </dev/null
timeout 60 qodercli -p "Respondé solo OK" </dev/null
timeout 120 kiro-cli chat --no-interactive --trust-tools= --model qwen3-coder-next "Respondé solo OK" </dev/null
```

Listas de modelos: `opencode models`, `kilo models`, `qodercli --list-models`, `kiro-cli chat --list-models`,
`codebuddy --help` (línea `--model`). Cline no tiene listado por CLI: sus gratis rotan y se ven en el selector `/model`
(<https://docs.cline.bot/getting-started/free-models>; avisa que el uso gratis puede usarse para entrenar).

## Reglas para darle trabajo a un gratis

- Tandas de **un ítem**, con informe al cerrar cada uno (los cortes por tiempo no dejan informe).
- El prompt lleva `/fable-method`, `/ponytail` y `/ponytail-review`. El coordinador comprueba que pegó la salida real.
- Nada confidencial: el uso gratis de Cline (y de varias promos) puede usarse para entrenar.
- Revisión obligatoria del coordinador antes del commit: ninguno de estos commitea.
