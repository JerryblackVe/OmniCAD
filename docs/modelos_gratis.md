# Modelos gratis para ejecutar tareas de OmniCAD

Pedido de Gerardo (2026-11-07): revisar Cline, OpenCode, Kiro, Qoder, Kilo y CodeBuddy, ver qué modelos gratis tienen
y cuáles sirven para el proyecto. Las promos gratis cambian cada semana: **antes de usar uno, repetir la prueba de
«¿responde?»** (abajo). Cuándo usar cada ejecutor lo deciden `CLAUDE.md` (tabla de modelos) y la memoria
`modelos-baratos-opencode`; acá queda solo lo medido.

## Veredicto (2026-11-07)

| Modelo | Dónde | ¿Responde hoy? | Calidad medida en OmniCAD | ¿Sirve? |
|---|---|---|---|---|
| GLM 5.3 Flash | OpenCode `opencode/glm-5.3-flash-free` | No: se cuelga en la cabecera (cupo gratis agotado) | La mejor de los gratis: 1 corrección menor en 4 tareas difíciles (asas) | **Sí, para lógica y ventana**, cuando vuelva el cupo |
| DeepSeek V4.1 Flash | OpenCode `opencode/deepseek-v4.1-flash-free` | No: se cuelga en la cabecera | 4 correcciones en 16 ítems; bien para lo mecánico y para confirmar reportes | **Sí, para lo mecánico**, cuando vuelva el cupo |
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

**En resumen, hoy:** de los gratis, solo responden los de **Cline y Kilo**, y entre ellos el único con historial
aceptable es **Nemotron 3.5 Super VL, para tareas chicas**. Los buenos (GLM y DeepSeek en OpenCode, CodeBuddy, Qwen en
Qoder) están sin cupo. Para el trabajo de verdad siguen Sol (suscripción de ChatGPT) y, como última instancia, Claude.

## Cómo repetir la prueba

Desde una carpeta vacía (no el repo), con `</dev/null` y sin sandbox. Un modelo que solo imprime la cabecera
`> build · modelo` está sin cupo, no muerto (OpenCode reintenta en silencio por horas):

```bash
timeout 90 opencode run -m opencode/glm-5.3-flash-free "Respondé solo la palabra OK" </dev/null
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
