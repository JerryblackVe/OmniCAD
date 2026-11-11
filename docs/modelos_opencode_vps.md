# Modelos de OpenCode en la VPS (prueba del 2026-11-11)

Prueba de 38 modelos con las 3 pruebas chicas, desde una carpeta temporal vacía, `timeout 180`, sin gastar saldo
pago (solo gratis y suscripciones ya conectadas). Cuentas conectadas: OpenCode, OpenCode Go, Nvidia, OpenRouter,
TokenRouter, Ollama Cloud y OpenAI (ChatGPT, oauth).

- **A)** responder solo «OK». **B)** `area_triangulo(a, b, c)` (Herón, `ValueError`, 3 asserts), guardada y corrida con
  `python3`: ✓ = corre sin fallar. **C)** explicar el chaflán en 3 líneas: ✓ = español claro y correcto (leído a mano).
- Una sola medición por modelo: los gratis se caen y vuelven en horas (ver `docs/modelos_gratis.md`). Un ✗ no es definitivo.
- Los que fallaron la prueba A no hicieron B ni C.

## Respondieron (A, B y C)

| Modelo | Cuenta | A) «OK» | B) Código Herón | C) Español | Para qué sirve |
|---|---|---|---|---|---|
| `opencode/beam-free` | OpenCode (gratis) | 5 s ✓ | 5 s ✓ | 6 s ✓ | lógica y código estándar; el más rápido de los gratis |
| `openrouter/free` | OpenRouter (gratis) | 5 s ✓ | 5 s ✓ | 14 s ✓ | mecánico; el modelo real lo elige OpenRouter, no repetible |
| `opencode/glm-5.3-flash-free` | OpenCode (gratis) | 5 s ✓ | 7 s ✓ | 7 s ✓ | mecánico / código estándar (cero retención) |
| `nvidia/mistral-large-4-1t-a52b` | NVIDIA (API) | 8 s ✓ | 7 s ✓ | 13 s ✓ | lógica / revisión de otra familia |
| `crowllm/crow-code-limitless:free` | CrowLLM (gratis) | 9 s ✓ | 7 s ✓ | 13 s ✓ | código estándar (sin cuenta propia: confirmar estabilidad) |
| `openai/gpt-6-luna` | OpenAI (ChatGPT, oauth) | 5 s ✓ | 8 s ✓ | 5 s ✓ | mecánico rápido (cupo ChatGPT) |
| `opencode/mimo-v2.6-flash-free` | OpenCode (gratis) | 8 s ✓ | 9 s ✓ | 10 s ✓ | mecánico (usa los datos para entrenar: nada privado) |
| `nvidia/nemotron-3-ultra-550b` | NVIDIA (API) | 6 s ✓ | 11 s ✓ | 4 s ✓ | lógica difícil (grande y rápido) |
| `opencode/big-pickle` | OpenCode (gratis) | 4 s ✓ | 12 s ✓ | 7 s ✓ | lógica y código estándar |
| `openai/gpt-6.1-sol` | OpenAI (ChatGPT, oauth) | 6 s ✓ | 12 s ✓ | 7 s ✓ | lógica y código difícil (cupo ChatGPT) |
| `opencode/deepseek-v4.1-flash-free` | OpenCode (gratis) | 8 s ✓ | 14 s ✓ | 6 s ✓ | mecánico / código estándar (cero retención) |
| `opencode/nemotron-3.5-super-vl-free` | OpenCode (gratis) | 14 s ✓ | 20 s ✓ | 21 s ✓ | imágenes / contexto grande; lento |
| `opencode/nemotron-3.5-lightning-free` | OpenCode (gratis) | 5 s ✓ | 29 s ✓ | 6 s ✓ | mecánico; lento en código (28 s) |
| `nvidia/deepseek-ai/deepseek-v4.1-flash` | NVIDIA (API) | 78 s ✓ | 64 s ✓ | 132 s ✓ | no usar: 64-132 s por prueba |

## No anduvieron

| Modelo | Cuenta | A) «OK» | B) | C) | Motivo |
|---|---|---|---|---|---|
| `opencode/nemotron-3-ultra-free` | OpenCode (gratis) | 2 s ✗ | — | — | Error del servidor («Unexpected server error») en 2 intentos |
| `opencode-go/deepseek-v4-pro` | OpenCode Go | 3 s ✗ | — | — | Región: hay que elegir «Global» en la consola de OpenCode |
| `opencode-go/glm-5.3` | OpenCode Go | 3 s ✗ | — | — | Falta suscripción Go activa |
| `opencode-go/kimi-k3` | OpenCode Go | 3 s ✗ | — | — | Falta suscripción Go activa |
| `opencode-go/kimi-k2.7-code` | OpenCode Go | 4 s ✗ | — | — | Falta suscripción Go activa |
| `opencode-go/minimax-m3` | OpenCode Go | 3 s ✗ | — | — | Falta suscripción Go activa |
| `opencode-go/qwen3.8-max` | OpenCode Go | 3 s ✗ | — | — | Falta suscripción Go activa |
| `opencode-go/qwen3.8-flash` | OpenCode Go | 3 s ✗ | — | — | Falta suscripción Go activa |
| `opencode-go/mimo-v2.6-pro` | OpenCode Go | 3 s ✗ | — | — | Falta suscripción Go activa |
| `opencode-go/gpt-6-luna` | OpenCode Go | 3 s ✗ | — | — | Falta suscripción Go activa |
| `opencode-go/claude-haiku-5-5` | OpenCode Go | 3 s ✗ | — | — | Falta suscripción Go activa |
| `opencode-go/grok-4.7` | OpenCode Go | 3 s ✗ | — | — | Falta suscripción Go activa |
| `opencode-go/gemini-4-argon` | OpenCode Go | 3 s ✗ | — | — | Falta suscripción Go activa |
| `ollama-cloud/kimi-k3` | Ollama Cloud | 3 s ✗ | — | — | Sin créditos / sin plan en Ollama Cloud |
| `ollama-cloud/glm-5.3` | Ollama Cloud | 3 s ✗ | — | — | Sin créditos / sin plan en Ollama Cloud |
| `ollama-cloud/deepseek-v4.1-flash` | Ollama Cloud | 3 s ✗ | — | — | Sin créditos / sin plan en Ollama Cloud |
| `ollama-cloud/gpt-oss:120b` | Ollama Cloud | 3 s ✗ | — | — | Sin créditos / sin plan en Ollama Cloud |
| `ollama-cloud/nemotron-3-ultra` | Ollama Cloud | 3 s ✗ | — | — | Sin créditos / sin plan en Ollama Cloud |
| `ollama-cloud/minimax-m3` | Ollama Cloud | 5 s ✗ | — | — | Sin créditos / sin plan en Ollama Cloud |
| `nvidia/z-ai/glm-5.3` | NVIDIA (API) | 2 s ✗ | — | — | Error del servidor («Unexpected server error») en 2 intentos |
| `openai/gpt-5.4-mini` | OpenAI (ChatGPT, oauth) | 3 s ✗ | — | — | No soportado con cuenta ChatGPT |
| `nvidia/gpt-oss-20b` | NVIDIA (API) | 180 s ✗ | — | — | Se colgó: 180 s sin respuesta |
| `tokenrouter/z-ai/glm-5.3-free` | TokenRouter | 3 s ✗ | — | — | Token inválido (hay que renovarlo) |
| `crowllm/agnes-2.5-flash:free` | CrowLLM (gratis) | 180 s ✗ | — | — | Se colgó: 180 s sin respuesta |

## Conclusiones

- Mejores: `nvidia/nemotron-3-ultra-550b` y `openai/gpt-6.1-sol` (lógica), `opencode/beam-free` (el más rápido de los gratis).
- Gratis para código estándar y mecánico: `big-pickle`, `deepseek-v4.1-flash-free`, `glm-5.3-flash-free`, `mimo-v2.6-flash-free`.
- OpenCode Go entero falla: falta la suscripción Go activa (y `deepseek-v4-pro` pide región Global).
- Ollama Cloud entero falla: hace falta plan o créditos. Ninguna de las dos se probó con plata.
- Para repetir: `~/.opencode/bin/opencode run -m <proveedor/modelo> "<prompt>"` desde una carpeta vacía.
