# Auditoría de tiempos de toda la app (AG-8)

> Cubierta desde el 2026-11-13 por [plan_fluidez.md](plan_fluidez.md) (filas FL-*), que da el orden; esto queda como antecedente. El prompt se retiró (AG-8 salió de la agenda).

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
- Planes: [plan_rust.md](plan_rust.md), [plan_cpp.md](plan_cpp.md) y [plan_velocidad_tests.md](plan_velocidad_tests.md). El último
  es de la velocidad de los tests, no de la app.
- Medidores en `scripts/`: `medir_fluidez.py`, `medir_previa_comandos.py`, `medir_costos_previa.py`,
  `medir_ventana_arrastre.py`, `medir_ui_boceto.py`, `medir_solver_boceto.py`, `bench_rendimiento.py`,
  `bench_booleana.py`, `bench_perfiles_interior.py` y `bench_objetos_vectoriales.py`.
- Caza automática con juez de rendimiento: `scripts/caza/cazar.py tema <tema>`.
- Filas de rendimiento ya cargadas en `docs/seguimiento/mejoras.md`: P-99, P-35, P-78 y las secciones «Rust» y «C++».
  Se reusan; no se duplican.
