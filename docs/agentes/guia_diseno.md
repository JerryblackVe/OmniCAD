# Guía de diseño para agentes

La guía vive **en un solo lugar**: los archivos de `clon/omnicad/api/guia/`. Esta página no la repite: dice para qué
sirve cada tema y cómo pedirlo. Así no hay dos versiones que se contradigan.

## Los temas

| Tema | Para qué | Archivo |
|---|---|---|
| `indice` | el mapa: qué grupos de herramientas hay, qué temas existen y las reglas que valen siempre | [indice.md](../../clon/omnicad/api/guia/indice.md) |
| `flujo` | el ciclo de trabajo (mirar, hacer, ver la imagen, medir, guardar), unidades, cómo se nombran cuerpos y pasos, cómo leer los errores | [flujo.md](../../clon/omnicad/api/guia/flujo.md) |
| `selectores` | elegir caras y aristas (`>Z`, `\|Z`, `%CIRCLE`…) para empalmes, chaflanes, vaciados, agujeros y bocetos sobre una cara | [selectores.md](../../clon/omnicad/api/guia/selectores.md) |

Orden de lectura: `flujo` antes de tocar nada; `selectores` la primera vez que necesites una cara o una arista.

## Cómo pedirla

| Dónde | Cómo |
|---|---|
| Herramienta (sirve en cualquier cliente) | `get_guide` con `topic="flujo"`; sin tema devuelve el `indice` y la lista de temas |
| Recurso MCP | `omnicad://guia/flujo`, `omnicad://guia/selectores`… |
| Prompt MCP | `disenar_pieza` arma un pedido que ya sigue el ciclo de trabajo |
| CLI | `omnicad call get_guide topic=flujo --json` (sin `--json` el texto se recorta) |
| Archivos | los de la tabla de arriba |

Algunos clientes no soportan resources ni prompts: para ellos está `get_guide`, que devuelve lo mismo como herramienta.

## Unidades

- **Milímetros y grados.** Un número suelto se toma como mm o grados según el campo.
- Los campos de tipo expresión aceptan `"10 mm"`, `"45 deg"` o `"ancho / 2"`, con los nombres de los parámetros que existan.
- Las medidas importantes conviene dejarlas como parámetros (`create_parameter`): después se cambian con `set_parameter` y el modelo se recalcula.

## Errores

- Toda falla vuelve como `{"ok": false, "error_kind", "mensaje", "pistas"}`. Decidí con `error_kind`: no cambia entre versiones.
- Los errores de la API y de los selectores están explicados en `flujo` y en `selectores`.
- Los del modo en vivo (`APP_BUSY`, `UNSAVED_CHANGES`…) están en [puente.md](puente.md#errores-del-modo-en-vivo).

## Para quien mantiene la guía

- Agregar un tema es agregar un `.md` a `clon/omnicad/api/guia/`: `get_guide` y los recursos MCP lo listan solos.
- Las herramientas que nombra la guía existen en el catálogo ([herramientas.md](herramientas.md)).
- Un ejemplo completo de la guía aplicada: [ejemplos/agentes](../../ejemplos/agentes/README.md).
