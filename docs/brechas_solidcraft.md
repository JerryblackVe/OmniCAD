# Brechas frente a SolidCraft

Fecha: 2026-10-19. Fuente: [tangency-labs/solidcraft](https://github.com/tangency-labs/solidcraft) (README, `ROADMAP.md`,
`docs/features.md`, `docs/oracle.md`, `docs/robustness.md`, `docs/mutation-testing.md`, `docs/perf.md`), leídos ese día.
No se corrió la app: lo de abajo es lo que ellos documentan.

**Qué es:** CAD paramétrico en Rust puro (egui + wgpu), con escritorio, web (wasm), CLI y MCP. Su kernel está armado
sobre las crates `truck` y lo van a cambiar por `solidcore` (#1597, `docs/mutation-testing.md`).
**Licencia:** MIT o Apache-2.0: se puede tomar código citando el origen y conservando el `NOTICE`. Como está en Rust
sobre otro kernel, lo útil son los MÉTODOS, no el código.
**Decisión (2026-10-19):** no se hace fork. Se toman las ideas de abajo.

Cada ítem lleva su herramienta MCP/CLI (receta C de `AGENTS.md`), test y doc regenerada.

## Prioridad 1 — calidad y robustez

| # | Qué | Por qué conviene | Estado en OmniCAD |
|---|---|---|---|
| SC1 | **Suite de piezas de referencia.** Cada caso es una receta JSON y un `esperado.json` (cantidad de cuerpos, volumen, área, centro de masa, caja, cantidad de caras), con tolerancia relativa 1e-3. Los valores salen de fórmulas cerradas (Pappus, Steiner, frustos) o de un kernel independiente corrido aparte. Cada pieza también se exporta a STEP, se valida y se vuelve a leer. Ellos tienen 83 casos: 62 analíticos y 21 de FreeCAD. | Mide los DOS motores (OpenCascade y OmniKernel) con la misma vara, y detecta regresiones en cualquier cambio de núcleo o el paso a Rust. | No existe. Los tests comprueban valores sueltos por archivo. Herramienta: `run_reference_tests` (o ampliar `run_checks`). Decidir: FreeCAD como oráculo externo es una dependencia, pedir permiso. Primero los casos analíticos. |
| SC2 | **Robustez con semilla.** Un generador arma diseños aleatorios pero realistas: caja, perfil o revolución, más hasta 8 pasos (uniones, cortes, empalmes, vaciados, agujeros, patrones). Las posiciones caen en una rejilla de 2,5 mm, así salen caras coincidentes y tangencias. Después de cada paso se chequea que el sólido es válido y que el volumen se mueve hacia el lado correcto (un corte nunca suma). Identidad booleana: V(A∪B)+V(A∩B)=V(A)+V(B). Un minimizador reduce el caso que falla a los pasos que importan. | Encuentra lo que la tortura a mano no ve, y deja cada falla como un caso chico que se puede reproducir. | Hay tortura a mano (`docs/informe_tortura_2026-10-17.md`, `tests/test_hallazgos_tortura.py`), no un generador. CLI: `omnicad fuzz --desde N --cantidad M`, más `fuzz-uno <semilla> --minimizar`. |
| SC3 | **Nombres persistentes por historia.** Las caras y aristas se nombran a partir de la historia que reporta el kernel (qué lado del boceto, tapa, pared interior del vaciado, copia del patrón), no por su geometría. Si una entidad se partió o desapareció, se avisa. | Es el problema de la «denominación topológica». Hoy un empalme o un boceto sobre una cara se pueden ir a otra cara cuando cambia una cota de antes. | Hoy se referencian por firma geométrica tolerante (centro, área, normal: `timeline/entidades.py:7` y `:117`). OpenCascade da la historia con `Modified`/`Generated` de cada operación (`BRepTools_History`). La firma queda como respaldo. Es la tarea más grande de esta lista. |
| SC4 | **Solver de bocetos constructivo antes del numérico.** Los puntos que fijan las restricciones se colocan exactos por construcción (intersección de lugares geométricos y descomposición en grupos rígidos, según Owen 1991 y Fudos–Hoffmann 1997). El numérico (Levenberg–Marquardt) resuelve solo el resto. Mantiene la rama de solución que tenía el boceto y rechaza la edición que lo daría vuelta. | El boceto no «salta» al cambiar una cota o al arrastrar, y resolver es más rápido. | Hoy todo va por `scipy.optimize.least_squares` (`restricciones/solver.py:14`). Encaja con `docs/plan_rust.md`: primero medir. |

## Prioridad 2 — funciones de Fusion que ellos ya tienen y nosotros no

| # | Qué | Estado en OmniCAD |
|---|---|---|
| SC5 | **Configuraciones:** una tabla de filas, cada una con valores de parámetros, pasos suprimidos y material/aspecto por cuerpo. Se activa una fila (se puede deshacer, es todo o nada) y sobrevive a renombrar parámetros y borrar pasos. | No existe. «Configurar» está en los menús de Fusion que faltan (pendiente 25 a y b). |
| SC6 | **Conjuntos de contacto:** al mover uniones o en un estudio de movimiento, las piezas del conjunto no se atraviesan. | El botón existe pero está grisado (`ui/cinta.py:62`). |
| SC7 | **Análisis del estudio de movimiento:** gráfico de valor, velocidad y aceleración de una unión; rastro de un punto; qué piezas chocan y en qué paso. | `motion_study` mueve las piezas. No hay gráfico, rastro ni choques a lo largo del estudio (no encontrado en `api/`). |
| SC8 | **Uniones con relación:** leva (seguidor de cuchilla, rodillo o plano sobre un perfil cerrado) y tornillo (giro↔avance). | Engranaje y cremallera ya van por `create_motion_link` (`api/herramientas_ensamble.py:643`). Faltan leva y tornillo. |
| SC9 | **Timeline:** carpetas de pasos, y copiar y pegar pasos (con sus dependencias). | No encontrado en `ui/panel_timeline.py`. |
| SC10 | **Vistas guardadas** (Named Views): guardar, renombrar, restaurar y borrar. | No existe. |
| SC11 | **Ratón 3D** (3Dconnexion SpaceMouse): desplazar, zoom y giro; en boceto, solo desplazar y zoom. Preferencias por eje (invertir, velocidad). | No existe. Hace falta leer HID: `hidapi` es un paquete nuevo (pedir permiso) o se lee con `ctypes`. |
| SC12 | **Plástico:** Ajuste a presión (Snap Fit) y Reposo (Rest). **Chapa:** Perforar. | No están entre las 95 operaciones (`list_operation_types`). Ya están Labio, Saliente, Nervio y Red. |
| SC13 | **Comparar cuerpos:** desviación entre dos cuerpos con mapa de color. Sirve para malla contra sólido, o versión vieja contra nueva. | No existe. |
| SC14 | **Importar `.FCStd` de FreeCAD:** es un ZIP con archivos `.brp` de OpenCascade, que se leen con `BRepTools.Read`. Rhino `.3dm` ya está como RH3. | No existe. Barato: sin dependencias nuevas. Validar como dice `AGENTS.md › Seguridad` (tope por miembro del ZIP, sin `extractall`). |

## Prioridad 3

| # | Qué | Estado en OmniCAD |
|---|---|---|
| SC15 | **Exportar URDF:** ensamble con uniones → eslabones con malla, masa e inercia, y juntas con límites, para simuladores de robots. | No existe. Barato: las uniones y las propiedades físicas ya están. |
| SC16 | **Pruebas de mutación** (`mutmut`) juzgadas solo por SC1 y SC2: muestran qué cambios de comportamiento nadie notaría. | No existe. `mutmut` es un paquete nuevo: pedir permiso. Va después de SC1 y SC2. |
| SC17 | **Mallado estanco y rápido:** un plan por cara que comparte los nodos de arista con las vecinas, grillas estructuradas en caras de 4 lados, y evaluación en GPU con respaldo en CPU. Ellos miden 78 cuerpos en ~65 ms, de 50 a 65 veces más rápido que antes. | Hoy `BRepMesh` de OpenCascade. Primero medir (regla de rendimiento). Si es cuello de botella, va a `docs/plan_rust.md`. |

## Descartado y ya hecho

- **Versión web (wasm):** descartada. Python + PySide6 + OpenCascade en el navegador cuesta demasiado frente a lo que da.
- **Su kernel:** descartado. Es `truck`, más inmaduro que OpenCascade en empalmes generales (su M3, ~30 h pendientes), y lo van a reemplazar.
- **Ya los tenemos:** autoguardado y recuperación; guardado atómico (`io_archivos/proyecto.py:207`); explosión automática
  (`ui/animacion.py`); copias ligeras (PL8); líneas ocultas a SVG y DXF (PL9); STEP e IGES; informes de error.
