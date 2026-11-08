# Auditoría de tiempos de toda la app (AG-8)

Pedido de Gerardo (2026-11-08): «al extruir se trababa el programa, no es fluido como Fusion. Revisá los tiempos de todas
las herramientas, no solamente las de extrusión. Hay que optimizar los tiempos de toda la app».

## Qué se busca

- Que **ninguna herramienta trabe la ventana**. Fusion responde al clic al instante y la vista previa acompaña. En
  OmniCAD, Extruir con 41 perfiles tarda 3 s por API y en la ventana recalcula la vista previa con cada clic
  ([P-99](seguimiento/mejoras.md)).
- Un **número medido** por herramienta: tiempo de la operación, de la vista previa y del redibujo, en un modelo chico,
  uno mediano y uno grande. Después, un ranking de las lentas.
- Arreglar de la más lenta a la más rápida, midiendo antes y después. **Primero el algoritmo** (recalcular de más,
  hacer el trabajo en el hilo de la interfaz, teselar dos veces). Recién después Rust o C++, según la regla de
  rendimiento de `CLAUDE.md`. Agregar crates o tocar el toolchain pide permiso de Gerardo.
- Que no vuelva: pruebas de rendimiento con tope, y el juez «rendimiento» de `scripts/caza/` con la base al día.

## Metas (objetivo, a confirmar contra lo medido)

| Qué | Meta |
|---|---|
| Respuesta al clic en el visor (elegir, resaltar) | menos de 50 ms |
| Vista previa de un comando en un modelo mediano | menos de 200 ms, sin congelar la ventana |
| Ventana congelada (hilo de la interfaz bloqueado) | nunca más de 100 ms seguidos mientras se usa un comando |
| Aceptar una operación en un modelo mediano | menos de 1 s |

## Lo que ya existe (no rehacer)

- Mediciones y arquitectura de la fluidez: [fluidez-2026-10-28.md](auditorias/fluidez-2026-10-28.md),
  [previa-asincrona-2026-10-29.md](auditorias/previa-asincrona-2026-10-29.md) (vista previa en proceso aparte para los
  comandos pesados) y [rust-pipeline-2026-10-31.md](auditorias/rust-pipeline-2026-10-31.md).
- Planes: [plan_rust.md](plan_rust.md), [plan_cpp.md](plan_cpp.md) y [plan_velocidad.md](plan_velocidad.md). El último
  es de la velocidad de los tests, no de la app.
- Medidores en `scripts/`: `medir_fluidez.py`, `medir_previa_comandos.py`, `medir_costos_previa.py`,
  `medir_ventana_arrastre.py`, `medir_ui_boceto.py`, `medir_solver_boceto.py`, `bench_rendimiento.py`,
  `bench_booleana.py`, `bench_perfiles_interior.py` y `bench_objetos_vectoriales.py`.
- Caza automática con juez de rendimiento: `scripts/caza/cazar.py tema <tema>`.
- Filas de rendimiento ya cargadas en `docs/seguimiento/mejoras.md`: P-99, P-35, P-78 y las secciones «Rust» y «C++».
  Se reusan; no se duplican.

## Prompt para el agente

Guardado el 2026-11-08. Modelo sugerido: una sesión Claude Opus 5 con esfuerzo alto (mide, perfila y arregla; la geometría y el hilo de la interfaz no se le dan a un modelo barato).

```text
ARRIBA DE TODO, invocá con la herramienta Skill: `fable-method` y `ponytail` al empezar; seguí `plan-then-do`,
`tool-calling-guard`, `verify-before-commit` y `omnicad-test`; e invocá `ponytail-review` antes de cerrar cada ítem,
pegando su salida REAL en el informe.

Tarea: auditoría de tiempos de TODA la app OmniCAD (repo `D:/PROGRAMA`, rama main; reglas en `CLAUDE.md` y `AGENTS.md`).
La especificación es este documento (`docs/auditoria_tiempos.md`): leelo entero, con «Lo que ya existe». Modelo: Opus,
esfuerzo alto.

Fases (cada una se cierra con su commit en su rama antes de la siguiente):

1. **Banco de tiempos.** Un script `scripts/bench_herramientas.py` que recorre el catálogo de `clon/omnicad/api/`. Por
   cada herramienta que modifica el documento, mide el tiempo de la llamada en tres modelos:
   - chico: una caja;
   - mediano: el boceto del SVG «LAS VALIENTES», `evidencias/svg_valientes_2026-11-08/valientes.svg`, con 41 perfiles;
   - grande: una placa de 200 agujeros o un proyecto real de `evidencias/`.

   Para cada medición mide también el recálculo del timeline y el teselado. Escribe un JSON y una tabla ordenada de la
   más lenta a la más rápida. Lo pesado va con `scripts/turno.py`.
2. **Ventana.** Mide, como usuario y con la ventana minimizada, la latencia de clic, de vista previa y de aceptar en
   los comandos de la cinta. También cuánto se bloquea el hilo de la interfaz: un temporizador de Qt que anota los
   saltos de más de 100 ms. Reusá `medir_previa_comandos.py` y `medir_fluidez.py`. Cubrí primero Extruir con muchos
   perfiles (P-99 y el video de Gerardo de las 20:07: cada clic recalcula la vista previa).
3. **Ranking y causas.** Informe `docs/auditorias/tiempos_<fecha>.md` con:
   - las 20 más lentas contra las metas de este documento;
   - la causa medida de cada una, con un perfilador (`cProfile` o `py-spy` si ya está instalado): qué parte es
     OpenCascade, cuál Python, cuál teselado o redibujo, y si se recalcula de más.

   Si una herramienta está en Fusion, mirá su comportamiento en `docs/fusion_docs/`; Fusion se puede abrir para medir
   (permiso de Gerardo; ver `CLAUDE.md`).
4. **Arreglos**, de la más lenta a la más rápida. Un ítem por worktree: `bash scripts/worktree_item.sh crear <ID>`. Cada
   arreglo lleva:
   - la medición antes y después en el Registro;
   - un test de rendimiento con tope generoso (que no sea frágil bajo carga);
   - la fila de `docs/seguimiento/` borrada.

   Algoritmo primero. Lo que necesite Rust o C++ va a su fila de `mejoras.md` (secciones Rust y C++) con la medición:
   agregar crates pide permiso.
5. **Que no vuelva.** Actualizá la base del juez «rendimiento» de la caza y corré `cazar.py tema` de lo tocado.
6. **Portón:** `docs/auditorias/porton_auditoria.md`.

Reglas:
- Cada hallazgo va a `docs/seguimiento/` con el siguiente ID libre, buscado con grep: en paralelo hay otras sesiones
  cargando IDs.
- En `D:/PROGRAMA` no edites, no commitees ni cambies de rama: commitea en `item/<ID>`; fusiona el coordinador.
- Como mucho 2 sesiones trabajando en la PC y una corrida pesada a la vez (`scripts/turno.py`). Nada de OpenCode sin
  permiso del coordinador.
- Si cambia una herramienta, va con su herramienta en `clon/omnicad/api/` y la doc regenerada.
- Al 60 % de contexto, cerrá el ítem en curso, dejá la nota de traspaso y avisá al coordinador.
- Gerardo es disléxico: informes cortos.

Listo cuando: las 6 fases están hechas, o cargadas con su motivo en `docs/seguimiento/`; ninguna herramienta del ranking
traba la ventana más de 100 ms en el modelo mediano, o tiene su fila con la causa medida y el plan.
```
