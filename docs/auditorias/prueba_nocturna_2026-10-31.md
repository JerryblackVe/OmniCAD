# Pruebas pendientes para la sesión nocturna (2026-10-31)

Lista de TODO lo que hay que probar y todavía no se probó sobre el código final. Se arma durante el día,
sin correr nada pesado. La sesión nocturna la ejecuta en orden, de a una cosa a la vez (`scripts/turno.py`),
y al terminar borra de acá lo que quedó verde y anota lo que falló en `docs/seguimiento/`.

Estado del código: `main` en `40a5fcf` (sin subir a origin) más lo que sigue sin commitear: Rust, paneles, SÓLIDO,
SUPERFICIE y ENSAMBLAR. Con las tres últimas juntas corrieron ruff (limpio) y seis archivos cruzados (`test_seguimiento`,
`test_doc_agentes`, `test_claves_comandos`, `test_cobertura_ui_api`, `test_iconos_extra`, `test_iconos_gramatica`,
`test_formulario_paneles`, `test_b105_panel_chico`): 952 OK. Con la segunda tanda (sección 3d): ruff limpio y `test_sol15_bocetos`
más esos mismos archivos, 944 OK. Con BOC-52, 77 y 78: ruff limpio y esos mismos archivos, 946 OK. **La programación de la sección 0 terminó. Falta el push, que espera el «sí» de Gerardo, y refrescar la página de seguimiento después.**

## 0. Programación de la sesión nocturna (de menor a mayor complejidad)

Lanzada por Gerardo el 2026-10-31 a las 21:30. Extruir y Proyectar ya terminaron; prueba de humo con los dos, BOC-81 y el bloque 1: TODO OK (`evidencias/humo_2026-10-31/humo.txt`). Dos sesiones de ejecución, reusadas con `clear_session` + `SendMessage`: **A** `local_230279c4-0388-4bc1-b032-0782fcf6f3a7` y **B** `local_8d498caa-1987-4fbf-8d1c-464c5510c2a1`. Cada una toca archivos distintos; los comandos pesados van de a uno con `turno.py`.

| # | Bloque | Sesión | IDs | Modelo |
|---|---|---|---|---|
| 1 | Baja: API y tests (**terminado**, Sonnet medio alcanzó) | A | B-112, H-49, H-50, H-51, H-52, H-53 | Sonnet medio |
| 2 | Baja: paneles (**terminado**, Sonnet alto alcanzó) | B | UI-7, UI-4, UI-3 | Sonnet alto |
| 3 | Media: boceto (**terminado**, Opus alto alcanzó) | A | BOC-81, 3 tests rojos, B-120, BOC-83, B-110 | Opus alto |
| 4a | Media: timeline e Insertar (**terminado**; H-4 queda Parcial, falta el catálogo; Sonnet alto alcanzó) | A | H-6, H-4 | Sonnet alto |
| 4b | Media: ventana (**terminado**; UI-1 queda Parcial; UI-8 nueva; Sonnet alto alcanzó) | B | UI-5, UI-1, `test_temas`, foco del botón ⋯, mensaje viejo | Sonnet alto |
| 5 | **Control** (**terminado**: 7473 tests, humo OK, rojos corregidos, commits hechos) | coordinador | Cierre completo, rojos, commits separados | — |
| 6 | Alta: sólido y superficie (**terminado**; SUP-13 queda Parcial; Opus alto alcanzó) | A | CAP-13, SUP-13, B-124 | Opus alto |
| 7 | Alta: ensamble (**terminado**; ASM-16 y B-123 nuevos; Opus alto alcanzó) | B | ASM-15, B-108 | Opus alto |
| 8 | Muy alta (**terminado**; ASM-9 queda Parcial, falta Activar componente; lo que falte va con Opus alto) | B | ASM-9 | Opus alto |
| 9 | **Final** (**terminado** a las 07:10: cierre verde con 7567 tests, `test_motor` aparte OK, 41 piezas 0 ✗, humo y foco OK; tortura con 10 hallazgos, B-125 a B-129 y T-19 a T-23; commits hechos) | coordinador | Cierre completo, rojos, tortura, commits | — |

Reglas de la noche:
- El bloque 5 existe para proteger el trabajo: hoy hay más de 180 archivos sin commitear, y lo difícil (6 a 8) va encima de eso. Si ASM-9 sale mal, se descarta solo lo suyo.
- **Corte a las 05:00:** no arranca ningún bloque nuevo. Lo que esté a medio termina o se descarta, y corre el bloque 9.
- `git push` no corre de noche: espera el «sí» de Gerardo. La página de seguimiento se refresca después del push.
- Rojo que no se arregla: pasa a `docs/seguimiento/` y sigue el bloque siguiente.
- `tests/test_motor.py::test_prueba_humo_arranca_con_omnikernel_y_ocp_bloqueado` falló en la tanda 3 por `MemoryError` y pasa solo. Si vuelve a pasar en el bloque 9, se repite solo antes de contarlo como rojo.

Quedan afuera:
- Fusion real (no conecta): BOC-50, BOC-76, BOC-79, BOC-80, PAT-1, SUP-23, B-118, B-122.
- Rust y rendimiento (después de las herramientas): BOC-38, BOC-49 y las filas RS.
- Instalar o comprar algo: AUD-1, AUD-2, AUD-8, AUD-9, FU-12.
- Monitor real: UI-2.
- Límite de OpenCascade o de recetas: SUP-14, SUP-17.
- Alta sin turno esta noche: SOL-8, SOL-22, H-19. FU-14 necesita ASM-9.
- Baja sin turno esta noche: H-54.
- Espera decisión: B-121 (cambiaría lo que dan las recetas guardadas).

## 0b. Correcciones pedidas después de la tortura (2026-11-01, 07:20)

Gerardo pidió corregir la lista de la tortura. Corre en paralelo, sin commitear:
- **A** (Opus alto): B-125, B-126, B-128 y T-20. Suma tests de booleanas; repetir `scripts/bench_booleana.py todo`.
- **B** (Sonnet alto): B-127, B-129, T-19, T-21, T-22 y T-23.
- **Tortura** `local_ed211518-d842-489b-947c-66e3c52aabfc` (Opus alto): RS-X1, trabajador persistente. Toca recálculo, caché y cancelar.

Al terminar, en este orden:
1. **CONSTRUIR** (hecho, sin commitear): CON-1 a CON-8, B-130 y B-131 resueltos. Lo que deja sin probar está en la sección «3d. Tarea nueva: CONSTRUIR».
2. **INSPECCIONAR** (hecho, sin commitear): INS-1 a INS-8, B-147, B-148 y B-150 resueltos; las 15 herramientas andan (pieza `inspeccionar`: 256 comprobaciones, 0 ✗). Quedan B-149 Parcial, H-55, H-56 y P-25f solo con la pila de fijadores. Pedido literal en `evidencias/inspeccionar_2026-11-01/pedido.md`, especificación en `docs/brechas_inspeccionar.md`. INS-8 reusa `ui/panel_info.py`, el panel del SCU. Suma la pieza `inspeccionar` a `todo.py`. Lo que deja sin probar lo anota en la sección 3e.
3. **Comparación con Fusion real** (hecha por script el 2026-11-01): B-134, TXT-9, B-118, B-122, BOC-50, BOC-76, PAT-1, SUP-23 y Parámetros tienen su respuesta en `docs/seguimiento/` y en `docs/brechas_parametros.md`; BOC-79 coincide y se cerró. Scripts y salidas en `evidencias/fusion_2026-11-01/`. La API no llega a lo que necesita cursor: BOC-80, Apply y copiar en Parámetros, lo marcado abajo de INSPECCIONAR y «Decisiones tomadas por inferencia» de `docs/auditorias/construir_2026-11-01.md`. Interferencia entre componentes sí se midió: 2 cm³, igual a la cuenta.
4. **Texto en curva** (hecho, sin commitear): B-132, B-133, B-135, B-136, B-137 y TXT-8 resueltos; OmniKernel filtra las cintas sin área. B-134 y TXT-9 resueltos con la respuesta de Fusion real (sin commitear). Queda H-58. Después del arreglo de Extruir faltó repetir `paneles_boceto`, `boceto_herramientas` y `ventana_uso`: entran en el cierre completo. Una corrida de `texto_curva` se cayó con `access violation` con Fusion abierto y poca memoria; no se repitió. Pedido literal en `evidencias/texto_curva_2026-11-01/pedido.md`, con su video.
5. **Parámetros** (Opus alto, hecho, sin commitear): B-138 a B-143 y PAR-1 a PAR-11 cerradas. Falta en el cierre lo de la sección 3g.
6. **Reconstruir sólido, fases 0 a 3** (hecho, sin commitear): RI-1, F10, SC13 y F11 resueltos; RI-2 Parcial, con 30 de 30 en el banco y 6 de 51 en los STL reales. Pedido literal en `evidencias/reconstruir_2026-11-01/pedido.md`, plan en `docs/plan_reconstruir_solido.md`, STL de referencia de Gerardo en su carpeta del Escritorio. Suma `compare_to_mesh`, `analyze_mesh_features`, `reconstruct_from_mesh`, el mapa de color y el banco de 30 piezas. Va después de Parámetros porque el mapa de color entra en INSPECCIONAR y es la tarea más larga.
7. Repetir la tortura con 200 pasos y cadena de 200, más una pasada con la ventana real, que quedaron sin probar.
8. Cierre completo y commits hechos el 2026-11-01 (`evidencias/cierre_2026-11-01/`): 8230 tests en verde, 3 rojos y 3 piezas corregidos y repetidos (1190 tests cruzados con `-W error`), humo OK. Después de esos arreglos no se repitió la suite entera. El push espera el «sí» de Gerardo. La tortura de 200 pasos queda para la próxima tanda.

**Para próximas sesiones (Gerardo, 2026-11-01):** queda sin asignar, para Claude o para OpenCode con DeepSeek 4.1 Flash o OpenAI Sol. Lo mecánico y de un solo archivo sirve para OpenCode: H-55, H-56, H-58 y T-21. Lo que toca geometría o timeline va con Sol o Opus: B-144, B-123, H-54, ASM-16, ASM-9, H-4, SUP-13, RI-2 y H-57. Después, Rust: RS-X6, RS-X7 y RS-X8. B-149 espera su decisión.

**Para mirar con Fusion real (INSPECCIONAR):** Interferencia con componentes y Quitar volumen en modo directo; si Mostrar puntos de forzado sigue visible con el filtro de cuerpos o componentes; Aceptar gris sin selección en los análisis; Sustainability Insights con un cuerpo elegido.

B-129 espera a que A libere `nucleo/geometria.py`: `Eps=1e-8` en `geo._integral` baja el error de +0,539 a +0,004 mm³.

Cambio de orden (2026-11-01, 12:45): con 5,5 GB libres, Gerardo pidió sumar tareas. Corren en paralelo CONSTRUIR (A, en verificación final), Reconstruir sólido (B, Opus alto) y texto en curva (Tortura, Opus alto); B-134 queda para la pasada con Fusion. Al terminar CONSTRUIR entra INSPECCIONAR en A. Parámetros va después de la pasada con Fusion, que necesita un rato sin pruebas pesadas.

## 1. Lo último que estuvo verde (referencia, no vale como cierre)

Pasada sobre `3c7ad28`, 2026-10-31 (anterior a restricciones y patrones del boceto):

| Qué | Resultado |
|---|---|
| ruff | limpio |
| pytest `-W error`, 6 tandas | 1112 + 1148 + 1002 + 1188 + 1218 (1 salteado) + 719 = 6387 OK |
| piezas de ventana `todo.py` (minimizada) | sin ✗ reales (el «23 líneas con ✗» era el texto «0 con ✗»: el conteo del script estaba mal, ya corregido) |
| humo | TODO OK |
| `registro_uso` + `asistente` (ventana visible) | 24 y 124 comprobaciones, 0 ✗ |

## 2. Nunca corrió sobre el código integrado (prioridad 1)

| # | Prueba | Cómo | Estado |
|---|---|---|---|
| 1 | Cierre completo sobre `main` final (ruff, 6 tandas `-W error`, `todo.py`, humo, piezas con foco) | `bash scripts/cierre_completo.sh` (la PC sin uso al final: el humo mueve el cursor real) | **No corrió.** La pasada sobre `472777a` se cortó a pedido de Gerardo porque faltaban cambios |
| 2 | Prueba de humo con Restricciones + Patrones del boceto ya juntos | incluida en el #1 | La sesión de patrones avisó «falta la prueba de humo» |
| 3 | Piezas de ventana del boceto juntas: `inferencias`, `simetria_boceto`, `desfase_boceto`, `patrones_boceto`, `restricciones_boceto` | `todo.py` las toma de `PIEZAS` | Cada una pasó en su rama (restricciones 592/0 ✗, desfase 46/46); ninguna sobre el merge |
| 4 | Tests que tocan los dos archivos que chocaron al juntar (`editor_boceto.py`, `herramientas_boceto.py`) | incluidos en las tandas del #1 | Resolución sin conflicto de código, pero sin suite completa encima |
| 5 | `docs/agentes/herramientas.md` regenerado tras el merge | `tests/test_doc_agentes.py` en el #1 | El merge de la rama de patrones lo regeneró; falta confirmarlo con el test |
| 6 | Seguimiento al día | `tests/test_seguimiento.py`, `tests/test_claves_comandos.py` en el #1 | Idem |

## 3. Lo que van a dejar las dos sesiones abiertas (completar cuando terminen)

- **Desfase del boceto vs Fusion — INTEGRADO en `main` (`223eac2`).** Pieza de ventana `desfase_boceto`
  (51/51 en su rama), tests nuevos `test_desfase_equivalencia.py` (54) y `test_desfase_boceto.py`, matriz de 31
  filas en `docs/auditorias/desfase_boceto_2026-10-31.md`. En su rama: suite 6594 OK y humo OK. Sin verificar:
  suite y humo con todo integrado; en Fusion real, la convención de «Dos lados» (sale de un solo caso del video),
  el reemplazo de selección con otro clic y Match Topology (BOC-70, BOC-71 y BOC-72 ya se resolvieron: ver 3d);
  `auditoria_boceto.py` tenía 1 ✗ en «Patrón circular · barra con cantidad y ángulo»: era una prueba vieja del
  patrón de boceto (flujo de barra anterior a `9596b91`); ya se sacó, lo cubre `patrones_boceto`.
- **Patrones de sólidos — INTEGRADO en `main` (`40a5fcf`, 3 commits): rectangular, circular, trayectoria,
  puntos y multitransformación. Lo que no pudo probar (previa en vivo con muchas instancias, guardar y
  reabrir en cadena, deshacer/rehacer) está abajo.
  **Dejó:** pieza de ventana nueva `patrones_solidos`
  (en `PIEZAS`, 32/32 en minimizada); tests `test_patrones_solidos_semantica.py`, `test_patrones_solidos_ui.py`,
  `test_api_patrones_solidos.py`. Sin verificar: la suite completa y la humo **con todo integrado** (corrieron
  en la rama sola: 6608 pasadas, humo OK); las piezas `asas` (283/283 en la rama) y `auditoria_boceto` (78/78) sobre la rama integrada (se sacó de ellas
  el patrón de boceto viejo: lo cubre `patrones_boceto`); previa en vivo con
  cientos de instancias (el límite de 10.000 se prueba por API, no con la ventana); equivalencia con Fusion real de
  la cantidad en «Simétrico» (PAT-1) y del inicio en porcentaje (PAT-2), ver `docs/seguimiento/mejoras.md`.
- **Investigación Rust — TERMINADA** (solo documentación, sin commitear en `main`): informe
  `docs/auditorias/rust-pipeline-2026-10-31.md`, filas `RS-X1` a `RS-X5`. Midió con la PC compartida
  (porcentajes confiables, milisegundos ±20 %): repetir de noche con la PC libre las mediciones de
  `evidencias/rust_pipeline_2026-10-31/` (proyectos `motor_impreso` y `gatoRL`, BINCHA `.f3d`, BVH, `reducir`,
  `remallar`) y `scripts/bench_booleana.py todo`. Sin medir (lo dice el informe): visor 3D con ventana, memoria
  con modelos grandes, `reducir`/`remallar` en Rust (los 20–50× son del plan), RS-X4 y RS-X5.
- **Rust en producción (Zstandard del `.f3d` + BVH de rayos) — NO integrado todavía** (cambios sin commitear; el coordinador integra). Verificado acá solo con los tests de sus archivos y de `.f3d`/picking, de a uno, `-W error`. **Sin verificar de noche:** (1) suite completa y humo con el `.pyd` nuevo (recompilar: `cd clon/rust && ../.venv/Scripts/python.exe -m maturin develop --release`); (2) piezas de ventana que eligen cuerpos/caras con el mouse (`registro_uso`, `asas`, `auditoria_boceto`): el hover y el elegir usan ahora el BVH y el resultado debe ser el mismo; (3) hover con un modelo de más de 200 k triángulos en la ventana real (el primer clic construye el BVH, ≈ 45 ms, y el resto cuesta microsegundos); (4) memoria: un BVH por cuerpo en `Visor3D._pick` (≈ 110 B por triángulo) además de los triángulos que ya había; (5) `OMNICAD_SIN_RUST=1` con la suite de `.f3d` y picking (ya corrió `test_f3d_nativo` y `test_bvh_rust`, no el resto); (6) repetir con la PC libre `scripts/bench_nativo.py f3d <BINCHA.f3d>` y `rayos`, con y sin `OMNICAD_SIN_RUST=1` (mismas cifras de `PROJECT_LOG.md`); (7) empaquetado: el instalador/PyInstaller lleva el `.pyd` nuevo (no se probó). (8) arrastrar un cuerpo con la previa y elegirlo con el mouse justo después: el BVH viejo se tira en `Visor3D` (`m.pop("bvh")` y las claves `bvh`/`caja_tris` de `_pick`, cerca de la línea 665); no tiene test, solo se razonó. Pendiente de código: `analisis._rayos_chocan` (accesibilidad) sigue en numpy a propósito (otro convenio de bordes), ver RS-R3. El `.pyd` nuevo se instaló renombrando el viejo (otro proceso lo tenía cargado): reiniciar el MCP/la app abierta para que lo tome.
- **Paneles de herramienta (sistema común) — rama de trabajo sin commitear.** Dejó: `ui/formulario.py`, cambios en
  `ui/comando.py`, `ui/superposiciones.py`, `ui/temas.py`, `ui/aspectos_ui.py`, `ui/panel_patron.py` y los metadatos de
  campos de los 19 módulos de `ui/comandos/`; tests `test_formulario_paneles.py` (26) y 1 nueva en `test_b105_panel_chico.py`;
  piezas de ventana nuevas `paneles_inventario`, `dialogos_inventario` y `paneles_temas` (en `PIEZAS`); informe
  `docs/auditorias/ui_paneles_2026-10-31.md`. **Sin verificar de noche:**
  1. escalado real de Windows al 125 % y 150 % y mover la ventana entre monitores (solo se simuló con letra 125/150 % y
     ventanas de 1024×640 y 800×520): correr `paneles_inventario.py <fase> <ancho> <alto>` y `paneles_temas.py` con la
     pantalla escalada de verdad y mirar las capturas (UI-2);
  2. suite completa y humo con todo integrado (corrieron solo los 45 archivos que abren comandos, ver el informe);
  3. las piezas de ventana `cinta_completa`, `superficie`, `solido_crear`, `solido_modificar`, `asas`, `teclear`,
     `ventana_uso`, `ensamblar`, `patrones_solidos`, `patrones_boceto` y `seccion_color` con el sistema común (ver el
     Registro de `PROJECT_LOG.md` para las que ya corrieron);
  4. a mano en la ventana: abrir y aceptar sin tocar un paso viejo con algo avanzado (debe abrir «Más opciones»),
     arrastrar un asa con la sección plegada, y Tab/Enter dentro de las listas de Multitransformación;
  5. los diálogos de render (UI-1) siguen sin tratar.
  6. `ventana_uso` con `--ventana visible`: con el sistema común y la ventana minimizada, tras abrir un panel la
     activación pasó a la ventana de Dibujo y 30 atajos no disparaban (en `main`, 0); la pieza ahora reactiva la
     principal en cada vuelta y da 671/671, pero la causa no está aislada. Si con foco real de Windows vuelve a pasar,
     es un defecto de la aplicación (mirar `ui/comando.py`, el panel recién abierto).
- Cada una puede quedar con ⚠ de cosas «no verificadas en Fusion real»: copiarlos acá.

## 3b. Tarea nueva: herramientas de SÓLIDO contra capturas (CAP-1 a CAP-12)

Terminó (`local_3e7d1ed0-0dba-4526-8474-79dc23457556`, sin commitear en `main`). Corrió verde: ruff, `tests/test_herramientas_solido.py`, los tests tocados (1603 passed), los vecinos (440 passed, 1 skipped) y la pieza `herramientas_solido` (44, 0 ✗, solo minimizada). Lo que falta:
- La suite completa y la prueba de humo: los cambios en `ui/comando.py`, `ui/manipuladores.py`, `ui/visor3d.py` y `ui/analisis_vista.py` tocan todos los paneles y el visor.
- Las piezas `solido_crear`, `solido_modificar`, `superficie`, `asas`, `teclear`, `cinta_completa` y `ventana_uso` sobre el código final, y `herramientas_solido` con `--ventana visible` una vez.
- `tests/datos/qss_base.qss` se regeneró: si `test_temas` falla al integrar, volver a generarlo.
- Regenerar `docs/agentes/herramientas.md` y `api/claves_comandos.py` al integrar, si otra sesión sumó herramientas después.
- Ver con ojos: lo no comparable con las capturas, Rosca con clase en ACME, BSP y tuberías (CAP-14, ver 3d) y Editar cara sobre una cara no plana.
- No verificado en Fusion real (solo contra capturas y ayuda): movimiento de la grilla de Editar cara, tablas de rosca nuevas en una pieza impresa.

## 3c. Tareas nuevas en paralelo: SUPERFICIE y ENSAMBLAR

Terminaron sobre `main` sin commitear, en la misma carpeta que SÓLIDO y con archivos separados:
- SUPERFICIE (`local_1730ee23-48ed-4a9a-95b4-1a51e0363f38`, Sonnet alto): SUP-10, 11, 14 a 19, 21, 22, 23 y 26. Ver 3c-ter.
- ENSAMBLAR (`local_827e3a56-a73e-4d73-bb64-e268e6d30a4d`, Sonnet medio): ASM-6, 7, 8 y 10 a 15. Ver 3c-bis.

Cada una sumó sus tests y una pieza de ventana nueva a `scripts/prueba_ui/todo.py`. Quedan afuera: ASM-9 y, hasta la tanda 3d, SUP-9, SUP-12 y SUP-13. Lo generado (`docs/agentes/herramientas.md` y `api/claves_comandos.py`) quedó al día con las tres juntas; se regenera solo si se suma otra herramienta. Los cinco archivos que estaban en CRLF con LF en git ya se pasaron a LF.

### 3c-bis. ENSAMBLAR terminó (ASM-6, 7, 8, 10 a 15; sin commitear en `main`)

Dejó: `tests/test_ensamblar_asm.py` (31 tests numéricos), la pieza de ventana `ensamblar_asm` en `PIEZAS` de `todo.py`
(64/64 en modo minimizada) y `ensamblar` re-corrida (236/236, ahora con el menú del navegador nuevo). Lo que falta:
- Correr `ensamblar_asm` y `ensamblar` con `--ventana visible` una vez (hoy solo en minimizada).
- La suite completa y la prueba de humo no corrieron (cambios en `ui/cinta.py`, `ui/navegador.py`, `ui/ventana.py`,
  `ui/iconos_extra.py`, `ui/comandos/ensamblar.py`).
- Regenerar `scripts/claves_comandos.py` y `docs/agentes/herramientas.md` al integrar: otras sesiones agregan
  herramientas y comandos en paralelo y lo generado envejece.
- Ver con ojos: el panel del Estudio de movimiento (`capturas/ensamblar_asm_estudio_panel.png`) y los íconos nuevos
  (`capturas/iconos_ensamblar_asm.png`) en el tema claro; solo se miraron en el oscuro.

### 3c-ter. SUPERFICIE terminó (SUP-10, 11, 16, 18, 19, 22, 26; SUP-14, 15, 17, 23 quedan Parcial; SUP-21 se cerró en 3d; sin commitear en `main`)

Dejó: `tests/test_superficie_fusion.py` (24 tests numéricos: núcleo, pasos, diálogos, API y asas), la pieza de ventana
`superficie_fusion` en `PIEZAS` de `todo.py` (136, 0 ✗, en minimizada) y `superficie` re-corrida (234/234, cambió
`simetrica` por `lados`). Sobre este código: 1450 tests relacionados OK con `-W error` y ruff limpio. Lo que falta:
- La suite completa y la prueba de humo no corrieron (cambios en `ui/comandos/superficie.py`, `ui/comandos/asas_extra.py`,
  `ui/cinta.py` —botón Escala en SUPERFICIE › MODIFICAR—, `api/herramientas_documento.py` y `api/herramientas_solido_extra.py`).
- `cinta_completa` pasó en minimizada (612, 0 ✗); correrla junto con `superficie` y `superficie_fusion` en `--ventana visible` una vez.
- Regenerar `scripts/claves_comandos.py` y `docs/agentes/herramientas.md` al integrar (ya están al día con el `main` de hoy).
- Ver con ojos las capturas `evidencias/ui_2026-10-31/capturas/fusion_*.png` (paneles de Extruir, Revolución, Parche, Reglada,
  Destrimar, Coser y Extender) y los recortes `p_fusion_*.png`; en el panel de «A objeto» se ve «Más opciones» cortado: es B-113.
- Sin verificar en Fusion real (el MCP de Fusion no conectó): el lado positivo de la normal (SUP-23), la alineación libre
  como valor por defecto (SUP-17) y el ingletear con curvas (SUP-15).
- **B-113** (el panel no crecía al cambiar de modo) quedó arreglado en `ui/comando.py` (`superficie_fusion` 136, 0 ✗). Toca todos los paneles: repasar `paneles_inventario` en la noche y pasar el ratón sobre un panel de verdad. La segunda reubicación (`_t_reubicar`) solo la protege la sección 11 de `superficie_fusion`, no pytest: no borrarla sin correr esa pieza. Sin revisar: ventanas de menos de 800x520 y el `Navegador`, que tiene su propio `ajustar_alto`.

## 3d. Segunda tanda de herramientas

Terminó sobre `main` sin commitear, en la misma carpeta y con archivos separados. Cada sesión anotó acá lo que deja sin probar y sumó una pieza a `PIEZAS`:
- Superficie difícil (`local_1f6d8511-aaad-4460-b277-eddfec4ec376`, Opus alto): SUP-9, SUP-12 y SUP-21 resueltos; SUP-13 queda Parcial. Pieza nueva `superficie_guias` (112 comprobaciones, 0 ✗ en ventana transparente) y `tests/test_superficie_guias.py`; los tests del área dieron 1229 OK corridos juntos, no con la suite completa. Falta probar de noche:
  - `tests/test_superficie_guias.py`, `test_superficie_fusion`, `test_api_superficie`, `test_tuberia_cadena` y `test_cobertura_ui_api` dentro de la suite completa: la cadena de la tubería y la de superficie ahora son el mismo código (`ops_solido._en_cadena`).
  - La pieza `superficie_guias` con `--ventana visible` una vez, y `superficie`, `asas` y `cinta_completa` sobre el código final: SUPERFICIE › CREAR sumó seis botones (`sup_caja` a `sup_tuberia`) y cambiaron los diálogos de barrido, solevación y Coser.
  - Ver con ojos `evidencias/ui_<hoy>/capturas/guias_*.png`: verde y rojo de Coser, fila elegida en naranja y encuadre al borde.
  - Una pieza real de principio a fin con un barrido con riel y una solevación con Tangente, cambiando una cota y guardando y reabriendo el `.omnicad`.
  - Sin verificar en Fusion real: que Escalar, Estirar y Ninguna den la misma forma con un riel de largo distinto al de la ruta, y la forma de Tangente y Suave con peso (acá son secciones auxiliares, aproximadas).
- Boceto (`local_fdb6f4a8-a842-4b9d-a479-bba6e4861dfb`, Sonnet alto): resueltos BOC-33, 37, 40, 45, 46, 48, 53, 60, 62, 70, 71 y 72; BOC-36 y BOC-41 quedan Abiertos (pospuestos por tamaño), BOC-47 verificado (Abierto con evidencia) y BOC-50 Sin verificar. Pieza nueva `boceto_herramientas` (34 comprobaciones, 0 ✗ en ventana transparente). Falta probar de noche:
  - La pieza `boceto_herramientas` con `--ventana visible` una vez, y `inferencias`, `desfase_boceto`, `simetria_boceto`, `boceto_cotas`, `patrones_boceto` y `restricciones_boceto` sobre el código final: tocan `inferencia.py`, el desfase, la simetría, el dibujo de las cotas y las asas del patrón.
  - Ver con ojos `evidencias/ui_<hoy>/capturas/herr_*.png`: la línea de cota con flechas (`herr_cota_con_linea`), el contorno del perfil con su hueco (`herr_desfase_perfil`), la elipse desfasada (`herr_desfase_elipse`), la guía de la intersección aparente y la tangente de círculos.
- Patrones y ajustes (`local_7236269e-1bf4-4e9b-be82-e9e070a7722d`, Sonnet medio): PAT-2 a PAT-5, CAP-14, ASM-11 y ASM-13 resueltos; PAT-6 se resolvió después (3e). Pieza nueva `patrones_ensamble_rosca` (31 comprobaciones, 0 ✗ en ventana transparente). Falta probar de noche:
  - La pieza `patrones_ensamble_rosca` con `--ventana visible` una vez, y `asas`, `patrones_solidos`, `ensamblar`, `ensamblar_asm` y `herramientas_solido` sobre el código final: tocan `AsaRuta` (ahora con `factor`), los patrones, la unión y la rosca.
  - Ver con ojos `evidencias/ui_<hoy>/capturas/patron_ruta_inicio_porcentaje.png` (la silueta roja de la copia suprimida es chica) y `multitransformar_hasta_etapa.png` (siluetas azules de la etapa elegida sobre las copias de la vista previa).
  - Rosca con clase de Fusion (`auto`): los tipos ACME, BSP, tuberías, trapezoidal, autorroscantes y AFBMA pasan del perfil básico a la clase (corrimiento de decenas de micras). Decisión de Gerardo (2026-10-31): se acepta también en archivos viejos, para que coincida con Fusion. Imprimir un tornillo y una tuerca ACME 3G y comprobar el encastre.
  - Sin verificar en Fusion real: que el inicio en porcentaje, el cabeceo/guiñada de la bola (el orden de las tres rotaciones anidadas es el de OmniCAD, la ayuda no lo define) y la clase por defecto coincidan con Fusion; qué tan rápido es «Optimizado» en Fusion frente al de OmniCAD (PAT-6 resuelto, ver 3e).
  - Un vínculo de la misma unión con un `.omnicad` guardado y reabierto, y con límites de movimiento en el giro.

## 3e. Tercera tanda: de fácil a difícil

El orden que manda desde ahora es la sección 0; las tandas 3 y 4 quedaron dentro de ella. Las sesiones de la tanda 1 se reusan para las siguientes (`clear_session` + `SendMessage`):
- Tanda 1 (Sonnet alto, terminada): SUP-15, 17 y 14 en `local_230279c4-0388-4bc1-b032-0782fcf6f3a7`; BOC-41, 47 y 36 en `local_8d498caa-1987-4fbf-8d1c-464c5510c2a1`.
- Tanda 1 bis (Sonnet alto): terminada; `asas` volvió a 0 ✗ (291) antes del último cambio de `GestorAsas2D`.
- Tanda 2 (Opus alto): PAT-6 en `local_230279c4-0388-4bc1-b032-0782fcf6f3a7`. BOC-52 y BOC-78 terminaron junto con BOC-77 (ver abajo).
- Tanda 3 (Opus alto): SUP-13, CAP-13 y ASM-15, después de Proyectar y Extruir.
- Tanda 4 (Opus alto): ASM-9.
- Boceto, tanda 1 terminó (BOC-41, 47 y 36 resueltos; BOC-73, 74 y 75 nuevos; sin commitear en `main`). Pieza `boceto_herramientas` ampliada (secciones 8 a 10, 0 ✗ en ventana transparente). Falta probar de noche:
  - `boceto_herramientas` con `--ventana visible` una vez, y mirar `capturas/herr_escala_panel.png`, `herr_mover_chica_1024x640.png`, `herr_mover_chica_800x520.png`, `herr_boceto3d_punto_medio.png`, `herr_boceto3d_alineacion.png`, `herr_isoparametrica_unica.png` y `herr_isoparametrica_distribuidas.png` (el marcador y la etiqueta de la ayuda 3D, y las curvas sobre la cara).
  - Las piezas `patrones_boceto`, `desfase_boceto`, `inferencias` y `auditoria_boceto`: tocan `editor_boceto.py` (set_herramienta, Enter, Esc, dibujo) y `Lienzo._rotulo`.
  - Sin verificar en Fusion real: cómo reparte Fusion las curvas «Distributed» y que «U» sea la curva que sigue U (V constante) (BOC-76).
  - No cubierto: la curva isoparamétrica sobre una cara con agujeros solo se probó en el núcleo (`test_una_cara_con_agujero_recorta_la_curva_en_dos_tramos`), no con clic en la ventana.
- Boceto, tanda 1 bis terminó (BOC-73, 74 y 75 resueltos; BOC-76 a 78 nuevos; sin commitear en `main`). Pieza `boceto_herramientas` ampliada (asas de Mover, vista previa de la isoparamétrica y restricción 3D de las ayudas). Falta probar de noche:
  - `boceto_herramientas` con `--ventana visible` una vez, y mirar `capturas/herr_mover_asas.png` y `herr_isoparametrica_previa.png` (color y grosor de la vista previa sobre la cara).
  - La vista previa de la isoparamétrica con «Distribuidas» sobre una cara grande: las 80 ms de espera evitan recalcular en cada movimiento, pero no se midió el costo de una pasada (hasta 200 curvas) en la ventana.

Cada sesión anota acá lo que deja sin probar.

- **B-125, B-126, B-128 y T-20: lo que queda sin probar.** Corrió verde: ruff, `test_booleanas_tortura`, `test_b39_*`, `test_documento`, `test_api_solido*`, `test_api_documento`, `test_hallazgos_tortura`, `test_revision`, `test_motor`, `test_paridad_motor` y `test_consultas_motor`. Falta:
  - La suite completa y la prueba de humo: `geo.booleano` y `_problema_booleana` los usa casi todo el núcleo, y ahora un resultado desmentido por los puntos termina en error claro donde antes pasaba callado. Cualquier rojo nuevo con «los puntos dan cerca de» se mira primero como geometría que ya estaba mal.
  - `scripts/bench_booleana.py todo` con la PC libre, contra 2,50 / 2,48 / 1,95 s de placa3000.
  - `python scripts/fuzz_b39.py --casos 4000` completo: la comprobación nueva cambia cuáles resultados pasan.
  - Abrir recetas reales con Combinar › Cortar de varias herramientas y comparar cuerpos y referencias: el camino de una pasada solo se probó con cajas, cilindros, esferas y toros.
  - Sin verificar en Fusion real: qué hace con una herramienta de 1e-6 mm y con una arista pellizcada (B-126). No se pudo: Fusion no conectó.

- **Bloque 6, CAP-13 y SUP-13: lo que queda sin probar.** Corrió verde: ruff de lo tocado, `test_herramientas_solido`, `test_superficie_guias`, `test_sol09_solevacion`, `test_sol15_bocetos`, los tests de API, comandos y documentación, y las piezas `herramientas_solido` y `superficie_guias` en ventana transparente. Recetas viejas: comparadas contra `git HEAD`, 10 casos con diferencia 0. Falta de noche:
  - La suite completa y la prueba de humo: se tocó `nucleo/superficies.py` (`solevar_superficie`, `_solevar_con_rieles`), `nucleo/editar_cara.py`, `nucleo/solidos_modificar.py` (`desfasar_caras`) y `ui/comandos/editar_cara.py`.
  - `herramientas_solido` con `--ventana visible` una vez, y mirar `capturas/editar_cara_contorno.png`, `editar_cara_alt.png` y `panel_editar_cara_espaciado.png`. En la pieza Alt se simula solo la lectura de `keyboardModifiers` (el `sendEvent` no la actualiza): falta un Alt de teclado real al arrastrar la tríada, y ver que Windows no abra el menú de la ventana.
  - Sin verificar en Fusion real (el MCP no conecta): qué hace Espaciado de contorno (Contour Spacing: la ayuda solo lo nombra y las capturas no lo muestran; acá suma una fila de cuadros a esa distancia del borde), qué hace Fusion con una vecina tangente (acá la cara sube a plomo), qué peso de Fusion equivale a cada peso de la solevación.
  - No cubierto en la ventana: solevación cerrada con rieles y rieles hasta un punto (solo núcleo y API); Editar cara sobre una superficie cosida, sobre una cara ya editada y con la cara curva con vecinas tangentes (error claro) solo en el núcleo. Un Alt sobre un punto del contorno suma líneas adentro de la cara: la grilla sigue siendo un rectángulo, no agrega caras hacia afuera como T-Spline.
  - El desfase de caras con agujero ciego ahora devuelve un sólido: mirar `offset_faces` y Mover cara sobre piezas reales con agujeros.

- **ASM-15 y B-108: lo que queda sin probar.** Corrió verde: ruff, `test_posicion_asm`, `test_posicion_ventana` y los vecinos, y las piezas `posicion_asm` (nueva), `ensamblar` y `ensamblar_asm`, todas en ventana transparente. Falta de noche:
  - La prueba de humo y la suite completa: se tocaron `visor3d.py`, `ventana.py` y `superposiciones.py`.
  - `posicion_asm` con `--ventana visible` una vez, y mirar `capturas/posicion_asm_sin_capturar.png`, `posicion_asm_giro.png` y `posicion_asm_800x520.png`: la pregunta «Algunos componentes se movieron» solo se vio en ventana transparente.
  - Sin verificar en Fusion real (el MCP no conecta): qué hace al soltar con el botón fuera de la ventana y si elegir sigue andando con algo sin capturar (acá queda en pausa, ver ASM-16).
  - El archivo real `evidencias/grove_2026-10-28/interferencia_giro_10.omnicad` sigue dando lo mismo que antes (receta vieja, interferencia 10,3536 mm³): no se migra solo.

- **BOC-52, BOC-77 y BOC-78: lo que queda sin probar.** Corrió verde: ruff, los tests de solver, boceto y boceto 3D, y las piezas `boceto_herramientas` (100, 0 ✗) y `restricciones_boceto`, las dos solo en ventana transparente. Falta para el cierre: (1) suite completa y prueba de humo; tocan `restricciones/boceto3d.py`, `inferencia3d.py`, `ui/triada3d.py` y `aplicar_restriccion` de `ui/editor_boceto.py`; (2) `boceto_herramientas` y `restricciones_boceto` con `--ventana visible`, y mirar `capturas/herr_boceto3d_medio_en_el_espacio.png`, `herr_boceto3d_tangente.png` y `herr_tangente_fuera_del_arco.png`; (3) `inferencias`, `auditoria_boceto`, `patrones_boceto` y `desfase_boceto`, que comparten `editor_boceto.py`; (4) una pieza real con ruta 3D de línea + arco tangente + spline, barrida con `sweep` y cambiando una cota: la spline toma la dirección del arco, pero nadie barrió por esa ruta; (5) la vista en perspectiva: la tolerancia del enganche en el espacio es la del objetivo de la vista, así que varía con la profundidad (la pieza prueba una vista inclinada a distancia normal); (6) con muchas curvas: 120 curvas dan 10 ms por movimiento y 95 ms al rearmar, medido solo en el núcleo; el solver 3D con tangentes o splines largas se siente lento al arrastrar (BOC-82). ⚠ Fusion real no conectó: BOC-79 y BOC-80. ⚠ BOC-81: tangente 3D con un arco libre todavía puede cambiarle el radio.

- **Tanda 2, PAT-6 (patronear caras): lo que queda sin probar.** Corrió verde: ruff, tests de patrones y de seguimiento y la pieza `asas` (291, 0 ✗, solo minimizada; `GestorAsas2D` ya probado). `patrones_solidos` no se corrió: el panel solo cambió el texto de ayuda de «Tipo de cálculo». Falta para el cierre: (1) suite completa, prueba de humo y `patrones_solidos`; (2) `asas` en `--ventana visible` y otra vez si la sesión de Boceto vuelve a tocar `GestorAsas2D`; (3) una pieza real con «Optimizado» sobre un cuerpo con empalmes y varias caras, y seguir modelando encima; ⚠ solo se probó un chaflán, la malla y STEP sobre una placa simple, no un vaciado ni un empalme sobre las caras copiadas; (4) guardar en `.omnicad`, cerrar y reabrir en la ventana real; (5) el resaltado y la selección de caras copiadas en el visor no se miraron; (6) con OmniKernel no se patronean caras: corre por la herramienta, sin prueba propia.

- **Bloque 1 (B-112, H-49 a H-53): lo que queda sin probar.** Corrió verde: ruff y 894 tests con `-W error` (catálogo, sólido, avanzado, seguimiento, doc de agentes, íconos y boceto). Sin probar: `execute_code` con una imagen en una sesión MCP en vivo (solo se probó la conversión `a_resultado_mcp`); el orden completo de la suite con el `QT_QPA_FONTDIR` nuevo de `conftest.py` (lo corre el cierre); el aviso de H-52 con un boceto de muchos perfiles reales.

- **Tanda 1, SUPERFICIE (SUP-15, 17 y 14): lo que queda sin probar.** Corrió verde: ruff, 579 tests de superficie/API/doc/seguimiento con `-W error` y la pieza `superficie_fusion` (152, 0 ✗, solo minimizada). Falta para el cierre: (1) suite completa y prueba de humo, que nadie corrió con estos cambios; (2) `superficie_fusion` en `--ventana visible` (los atajos y el foco real no se probaron); (3) ventana chica 800x520 del panel de Reglada con «Esquinas ingleteadas» y de Extender con «Bordes libres» (la pieza solo cubre 1024x640 y 800x520 con otros valores); (4) la extensión libre sobre un parche de relleno (B-spline plegada) cae a la franja plana: solo la cubre el test de API, no hay captura que la compare con Fusion; (5) ingletear con curvas 3D no planas: la esquina queda sin cortar y el paso avisa (probado solo con dos rectas y con tres aristas, no con curvas 3D); (6) SUP-14 sigue Parcial: nada que probar. ⚠ Las capturas `fusion_reglada_luna_ingleteada` y `fusion_extender_libre_curva` se ven chicas (zoom de la escena): el número de la pieza manda, no se comparó contra una captura de Fusion.

- **BOC-81 y aviso de H-52: lo que queda sin probar.** Corrió verde: ruff y los tests de boceto 3D, sólido, documentación y seguimiento. Falta para el cierre: (1) suite completa y prueba de humo; tocan `restricciones/boceto3d.py` (`resolver` y `acomodar_tangente`) y `api/herramientas_boceto3d.py`; (2) ninguna pieza de ventana cubre esto: la tangente 3D con movimiento solo existe por MCP y CLI, y se probó por API; (3) ⚠ sin comparar con Fusion real qué curva se mueve (BOC-79: el MCP de Fusion no conecta). Se siguió la figura de su ayuda: el círculo queda igual y se mueve la línea; (4) una línea que pasa justo por el centro va a un lado u otro según la muestra más cercana y puede caer fuera del tramo (avisa); (5) el gemelo 2D quedó en BOC-83, sin arreglar; (6) `test_boceto_fase9_3d_ui.py::test_spline_termina_con_intro_y_esc_cancela` está rojo, sin relación con esto: B-120.

- **Bloque 2 (UI-7, UI-4 y UI-3): lo que queda sin probar.** Corrió verde: ruff, 883 tests de los consumidores de los paneles (formulario, B-105, cobertura UI/API, comandos, ensamblar, preajustes, tarjeta de Proyectar, boceto, preferencias) y la pieza nueva `panel_movible` (62, 0 ✗, solo minimizada; 1280×720, 1024×640 y 800×520). Falta para el cierre: (1) suite completa y prueba de humo: tocan `ui/comando.py`, `ui/superposiciones.py`, `ui/ventana.py`, `ui/modo_boceto.py` y `ui/preajustes_ui.py`; (2) `panel_movible` con `--ventana visible` una vez (el menú «⋯» se abrió con clic real en la ventana transparente, pero el foco real de Windows y el Tab con la ventana activa de verdad no); (3) re-correr `paneles_inventario` (los 148 comandos con la cabecera nueva, a 1280×720, 1024×640 y 800×520), `paneles_temas` (el botón «⋯» en los 5 temas y a 125/150 %), `teclear`, `ventana_uso` y `herramientas_solido`: no se corrieron; (4) a mano: arrastrar un panel de un monitor a otro y con la pantalla en 125/150 % (la posición se guarda en px lógicos; solo se simuló con ventanas chicas); (5) sin verificar en Fusion real (el MCP no conecta): la ayuda local no dice si los diálogos se arrastran; sí dice que el preajuste va arriba del diálogo, y de ahí sale el botón de la cabecera. No cubierto: el nombre del preajuste nuevo se tecleó en un cuadro simulado, no en el `QInputDialog` real. `tests/test_temas.py::test_el_qss_por_defecto_es_identico_al_de_antes_de_la_tipografia` falla hoy por el QSS sin commitear de `temas.py` (de otra sesión, no de este bloque).

- **Bloque 3, resto (B-120, BOC-83, B-110, íconos `sup_*`): lo que queda sin probar.** Corrió verde: ruff, tests de tangente, API de boceto, tríada, Proyectar, íconos, seguimiento y doc de agentes, y las piezas `perdidas_atenuar` (13), `boceto_herramientas` (100), `restricciones_boceto` (592) e `iconos` (22), 0 ✗, solo minimizadas. Falta: (1) suite completa y prueba de humo: tocan `restricciones/solver.py`, `ui/triada3d.py`, `ui/editor_boceto.py` y `api/herramientas_boceto.py`; (2) Fusion real no conecta: sin comparar qué hace con una cara que gana una arista ni qué curva mueve en una tangente arco-spline (⚠ BOC-79); (3) el `.omnicad` real del abanico (ver «Proyectos reales» en 3f). B-121 queda abierto: decidir antes de tocar el solver.

- **Bloque 4, primera parte (H-6, H-4 y Esc en la tríada): lo que queda sin probar.** Corrió verde: ruff, 1207 tests con `-W error` (ensamble, documento, navegador, selección, íconos, cinta, claves, doc de agentes, seguimiento y boceto 3D) y la pieza nueva `timeline_menu` (29, 0 ✗, solo ventana transparente; capturas `duplicar_con_uniones_panel.png`, `duplicar_con_uniones_resultado.png`, `duplicar_con_uniones_1024x640.png`, `duplicar_con_uniones_800x520.png` y `timeline_menu_buscar.png`). Falta para el cierre: (1) suite completa y prueba de humo: tocan `timeline/ops_ensamblar.py`, `ui/panel_timeline.py`, `ui/ventana.py`, `ui/cinta.py`, `ui/iconos_extra.py` y `ui/triada3d.py`; (2) `timeline_menu` con `--ventana visible` una vez, y mirar el ícono nuevo `duplicar_con_uniones` en la cinta y en el timeline (el paso «Copiar componente» lo reusa); (3) arrastrar un paso del timeline con VARIOS elegidos (Ctrl+clic) con el ratón de verdad: se probó que mueve el arrastrado, pero el soltar fue un `QDropEvent` armado (QDrag no se maneja con eventos simulados); (4) [resuelto en 4b: `PanelComando._limpiar_mensaje`] el aviso «Elegí al menos un destino» quedaba a la vista después de elegir los destinos; (5) «Desactivar operaciones» se resolvió como «Suprimir N pasos»: sin Fusion real no se pudo comprobar que Fusion no tenga un comando aparte; (6) Duplicar con uniones: solo con uniones rígidas y de revolución en prueba, no con deslizantes ni bola, ni con componentes de varios cuerpos.
- **Bloque 4b (UI-5, UI-1 parcial, «⋯», aviso viejo, `test_temas`): lo que queda sin probar.** Corrió verde: ruff, 1.861 tests con `-W error` (93 archivos que abren paneles de comando, boceto o render) y las piezas `paneles_boceto` (121, nueva), `panel_movible` (68), `dialogos_inventario` (23), `patrones_boceto` (105), `simetria_boceto` (45) y `paneles_temas` (91), todas solo con ventana transparente y a 1280×720, 1024×640 y 800×520 donde corresponde (capturas en `evidencias/ui_paneles_2026-10-31/boceto_paneles/`, `despues_dialogos/` y `movible/`). Falta para el cierre: (1) suite completa y prueba de humo (tocan `ui/comando.py`, `ui/formulario.py`, `ui/modo_boceto.py`, `ui/panel_patron.py`, `ui/panel_simetria.py`, `ui/panel_transformar.py`, `ui/render.py`, `ui/preajustes_ui.py` y `ui/ventana.py`); (2) `paneles_boceto` y `panel_movible` con `--ventana visible` una vez: Espacio sobre «⋯» se probó con el atajo Espacio puesto en la ventana, pero con la transparente; (3) la posición de los paneles del boceto y de render vale solo mientras dura la sesión (no va a la preferencia): no se probó cerrar y reabrir el boceto con el panel movido; (4) los diálogos de render con la letra al 125 y 150 % y con la pantalla real al 125/150 % (`paneles_temas` solo cubre Extruir, Patrón y Multitransformación); (5) `DialogoRenderizar` con una carpeta de red tipeada: `_revisar` mira el disco en cada tecla y no se probó con una ruta UNC lenta; (6) las filas que quedan abiertas: UI-1 (Escena y Aspecto sin barra en una ventana de render baja) y UI-8 (Carácter de ≈ 540 px se corta en ventanas bajas).

- **UI-1 y UI-8 (paneles con barra, Renderizar con letra grande): lo que queda sin probar.** Corrió verde: ruff, 617 tests con `-W error` (render, boceto, temas, seguimiento) y las piezas `paneles_boceto` (127), `dialogos_inventario` (23) y `paneles_temas` (121, ahora con Renderizar al 125 y 150 % en los 5 temas), 0 ✗, solo con ventana transparente y a 1280×720, 1024×640 y 800×520 donde corresponde. Falta de noche:
  - La suite completa y la prueba de humo: se tocaron `ui/render.py` (`PanelFlotante`, `DialogoRenderizar`), `ui/modo_boceto.py` (`PanelCaracter.ajustar`), `ui/superposiciones.py` (`AreaVisor.reubicar`) y `ui/temas.py`.
  - `paneles_boceto` y `paneles_temas` con `--ventana visible` una vez, y mirar `boceto_paneles/caracter_abierto_800x520.png`, `ventana_caracter_movido_800x520.png` y `temas/<tema>_150/renderizar.png`.
  - No cubierto: los paneles Escena y Aspecto dentro de una ventana de render real baja se probaron solo con tests (offscreen, sin fuentes: los textos salen como cuadros); ninguna pieza de ventana abre `VentanaRender` con la letra al 150 %. Con el escalado real de Windows sigue valiendo UI-2.
  - `DialogoLienzo` y `VisorImagen` quedan sin mensajes tipados (no tienen nada que avisar).
  - `test_doc_agentes` (3 pruebas) estaba rojo por `include_children` de la sesión de ASM-9, no por este cambio.

- **Bloque 8, ASM-9 (subensamblajes; queda Parcial por Activar componente): lo que queda sin probar.** Corrió verde: ruff, `tests/test_ensamblar_asm9.py` (9) y los vecinos de ensamble, patrones, duplicar, materiales y doc de agentes (147 + 86), y la pieza nueva `subensamblaje`, solo en ventana transparente. Falta para el cierre:
  - La suite completa y la prueba de humo: se tocaron `timeline/ops_ensamblar.py` (`grupo_rigido` ahora suma los subcomponentes; `poses_de_estudio`), `ops_solido.py` (`copiar_componentes`), `ui/ventana.py` (ojo y Aislar por familia) y `ui/navegador.py` (árbol).
  - `subensamblaje` con `--ventana visible` una vez, y mirar `capturas/subensamblaje_navegador.png` (CMano debajo de CBrazo), `subensamblaje_girado.png`, `subensamblaje_arrastre.png` y `subensamblaje_800x520.png`.
  - Sin verificar en Fusion real (el MCP no conecta): si al arrastrar un hijo sin unión dentro de un subensamblaje con unión Fusion lo mueve solo (acá, si el hijo existía cuando se creó la unión del padre, arrastra esa unión; `posicion.py`, shortcut) y si Capturar / Revertir de un padre alcanzan a los hijos.
  - No cubierto: un subensamblaje de tres niveles con uniones en cada nivel y un lazo cerrado; renderizar (`get_viewport_image`) con `component_colors` sigue pintando por componente directo, no por familia; `Insertar diseño` de un `.omnicad` con subensamblajes aplana en un componente (como antes).

- **Seis hallazgos menores de la tortura (B-127, T-19, T-22 y T-23 resueltos; T-21 Parcial; B-129 medido): lo que queda sin probar.** Corrió verde: ruff y 244 tests con `-W error` (`test_tortura_menores` 22, sólido, ensamble, tortura, revisión) más cuatro tandas de archivos vecinos. Falta:
  - La suite completa y la prueba de humo: se tocaron `api/registro.py` (todo parámetro numérico no finito se rechaza), `timeline/operaciones.py` (`aplicar_resultado`, `OpCombinar`), `nucleo/revision.py`, `api/herramientas_solido.py`, `herramientas_documento.py` y `herramientas_inspeccion.py`. Ninguna pieza de ventana se corrió.
  - ⚠ T-22 sin comprobar en Fusion real (la ayuda no lo dice y el MCP no conecta): Extruir y Crear caja con Intersecar sin nada en común ahora fallan igual que Combinar. Los paneles Extruir y Crear caja no se probaron con ese caso en la ventana: el error tiene que salir en el panel sin cerrarlo y sin borrar el cuerpo.
  - T-23: un `nan` escrito como texto en un campo de expresión sigue diciendo «Nombre desconocido: 'nan'»; los `nan` dentro de listas (puntos, desfases) los valida cada herramienta.
  - T-21: la primera revisión de cada rosca distinta sigue esperando 10 s (con 3 roscas se agota el presupuesto de 30 s); la memoria guarda 16 formas, vence a los 5 minutos y se pierde al cerrar la app. La revisión de la ventana (Inspeccionar › Revisar geometría) con un cuerpo roscado no se probó.
  - T-19, segunda tanda: `_r_chico` también en el campo `volume` de `check_geometry`, malla, lista de materiales, interferencias (`check_interference` y el paso de ensamble), `create_shaft` y `get_sheet_metal_info`. Tienen test `check_geometry`, la lista de materiales, `check_interference` y `get_mesh_info`; `create_shaft`, `get_sheet_metal_info` y el paso de ensamble no tienen uno propio. Siguen con `_r` los volúmenes de `herramientas_grafo.py:169` y de `herramientas_dev.py`.
  - B-129 (resuelto, segunda versión): `geo._propiedades` integra el volumen con `Eps` = 1e-8 solo si la forma tiene hasta 300 caras y todas sus caras libres son B-spline de hasta 170 polos (`_apta_para_integral_fina`), y en ese caso no corre la malla de control. La primera versión (hasta 64 caras) erraba en piezas reales: en EXTRUSOR XOX.f3z la adaptativa daba -10 % y -3,7 % en tornillos de 500 a 750 polos y movía una pieza de lugar (65 componentes movidos en vez de 64). Falta: la suite completa y la prueba de humo (corrieron `test_f3d_reales` y 1.394 tests vecinos). los volúmenes de piezas libres con 170 polos o menos cambian hasta 1e-4 respecto de antes (el agujero roscado ciego 2288,6556 → 2288,7455 y la tuerca de `test_b70_pasante` 3234,8859 → 3234,928, ambos igual a la cuenta a mano o a Eps 1e-12).

- **RS-X1, trabajador persistente (sin commitear en `main`): lo que queda sin probar.** Corrió verde: ruff, 377 tests de recálculo y las piezas `pasos_largos`, `auditoria_undo`, `timeline_menu`, `teclear`, `solido_modificar` y `ventana_uso` (1426 comprobaciones, 0 ✗, ventana transparente). Falta:
  - La suite completa y la prueba de humo: se tocaron `nucleo/aislado.py`, `nucleo/intercambio.py`, `timeline/calculo_aislado.py`, `timeline/documento.py`, `ui/ventana.py` y `tests/conftest.py` (el fixture autouse cierra el trabajador tras cada prueba).
  - Pieza nueva `pasos_largos` con `--ventana visible` una vez, y mirar `capturas/pasos_largos_caida.png`.
  - ⚠ La app instalada: el hijo es `OmniCAD.exe --tarea-aislada trabajador <carpeta>`. Se probó el canal por entrada estándar con `pythonw.exe` (ejecutable de ventana, igual que el .exe), no con el instalador.
  - ⚠ Una caída nativa real dentro del trabajador vivo (0xC0000005): se simuló con `_comando` falso y matando el proceso, que da «sin detalle» en lugar del mensaje de error nativo. Lo de B-48 sigue sin reproducirse a pedido.
  - ⚠ Linux y macOS: el código de `_memoria_mb` y `os.fdopen(0)` solo corrió en Windows.
  - Pasos 200 y cadena 200 de la saturación: ahora tienen sentido, antes tardaban demasiado.

## 3f. Tarea nueva: Proyectar y tarjeta de herramienta

Hecho en `local_8d498caa-1987-4fbf-8d1c-464c5510c2a1` (Opus alto), sin commitear en `main`. Pedido en `evidencias/proyectar_2026-10-31/pedido.md`. Tests nuevos: `tests/test_proyectar_tarjeta.py`; pieza nueva: `proyectar_boceto` (en `PIEZAS`). Falta probar:
- **Prueba de humo**, una sola vez y sin otra sesión: el código de la paleta y la tarjeta es nuevo y la humo no lo corrió.
- **Suite completa:** corrieron solo los archivos que tocan boceto, proyección o paleta (2 102 verdes; 3 rojos ajenos: `test_boceto_fase9_3d_ui.py::test_spline_termina_con_intro_y_esc_cancela` por la tríada, y dos de `test_iconos_unicos.py` por los íconos `sup_*`). Tocado de uso general: `restricciones/boceto.py` (`agregar_proyeccion`, `reproyectar`, `romper_vinculo`, `eliminar_proyeccion`), `nucleo/perfiles.py` (`_spline_de_arista`), `ui/superposiciones.py` (paleta y aviso flotante), `ui/temas.py` y `estado_referencias` (ahora el paso visible).
- **`cinta_completa` y el resto de las piezas:** ya corrieron en ventana transparente `proyectar_boceto` 43/43, `auditoria_boceto` 79/79, `boceto_herramientas` 100/100, `desfase_boceto` 51/51 y `perdidas_atenuar` 8/8.
- **`proyectar_boceto` con `--ventana visible`:** corrió solo en ventana transparente.
- **Proyectos reales:** abrir un `.omnicad` con proyecciones viejas (el abanico de B-110) y ver que no aparezcan «perdidas» nuevas: los registros anteriores a unir arcos pasan por el reintento de `reproyectar`, cubierto solo con un test sintético.
- ⚠ Fusion real no conectó: lo que pasa al cambiar de herramienta con Proyectar abierto no se pudo comparar; acá se descarta y se avisa en la barra de estado.

## 3g. Extruir, B-116 y B-117: lo que queda sin probar

Corrió verde: ruff, `tests/test_cuerpos_partidos.py`, 71 archivos de tests vinculados (cortes, recetas, patrones) y las piezas `herramientas_solido` y `solido_crear` en minimizada. Falta: (1) suite completa y prueba de humo, que nadie corrió con estos cambios; `todo.py` entero y los tests de boceto tampoco; (2) `herramientas_solido` en `--ventana visible`; (3) ventana chica 1024×640 y 800×520 del panel Extruir con Operación en Cortar (al pasar solo aparece el campo Objetos); (4) un cuerpo pesado de verdad: el proceso aparte se probó bajando `CARAS_PESADAS` a 1, no con 64 caras reales; (5) un corte que parte un cuerpo de chapa: la parte chica queda como sólido común, sin revisar contra Fusion.

## 3d. Tarea nueva: CONSTRUIR (CON-1 a CON-8, B-130, B-131)

Hecho el 2026-11-01, sin commitear. Corrió verde: `ruff`, la pieza `construir` en minimizada (635 comprobaciones, 0 ✗) y 88 archivos de tests de construcción, API, comandos, gizmos y ventana. Falta: (1) suite completa y prueba de humo: nadie las corrió con estos cambios, que tocan `ui/comando.py`, `ui/visor3d.py`, `ui/ventana.py`, `ui/superposiciones.py`, `timeline/operaciones.py` y `timeline/entidades.py`; (2) `todo.py` entero, porque `cinta_completa`, `asas` y `solido_crear` pasan por los paneles de construcción nuevos; (3) una pasada con `--ventana visible` de la pieza `construir`, porque Ctrl en el forzado se probó con el modificador simulado; (4) «Decisiones tomadas por inferencia» de `docs/auditorias/construir_2026-11-01.md` contra Fusion real, en la pasada de la sección 0b.

## 3e. Tarea nueva: INSPECCIONAR (INS-1 a INS-8, P-25f)

Hecho el 2026-11-01, sin commitear. Corrió verde: `ruff`, la pieza `inspeccionar` en minimizada (256 comprobaciones, 0 ✗) y los tests de análisis, API, comandos y manipuladores. Resultado en `docs/auditorias/inspeccionar_2026-11-01.md`. Falta: (1) suite completa y prueba de humo: tocó `ui/comando.py`, `ui/visor3d.py`, `ui/ventana.py`, `ui/navegador.py`, `ui/manipuladores.py` y `ui/panel_timeline.py`. (2) Regenerar `omnicad/api/claves_comandos.py` y `docs/agentes/herramientas.md` después de integrar todo. (3) B-149: decidir si el modo viejo de Radio mínimo también cambia.

## 3f. Tarea nueva: texto en curva y extrusión (B-132 a B-137, TXT-8, TXT-9)

Hecha el 2026-11-01, sin commitear. Pieza nueva `texto_curva` en `todo.py`. Queda sin probar:
- La suite completa y la prueba de humo: se tocaron `nucleo/perfiles.py`, `nucleo/fuentes.py`, `restricciones/boceto.py`, `timeline/operaciones.py`, `ui/comando.py`, `ui/formulario.py`, `ui/visor3d.py`, `ui/ventana.py`, `ui/editor_boceto.py`, `ui/modo_boceto.py` y `ui/panel_info.py`.
- Todas las piezas: Extruir rechaza ahora lo que `sin_volumen` da por chato, y un texto nuevo crea sus parámetros «Text» y «Text_height» (también `sketch_from_spec`). Borrar o desglosar un texto borra los suyos, salvo los que use otro.
- Con OmniKernel: `omnikernel/perfiles.py` filtra las cintas sin área; solo lo cubre `test_omnikernel_tampoco_lista_los_restos_sin_area`.
- Pieza `texto_curva` con `--ventana visible` una vez, mirando `b137_durante.png` y `letras_extruidas.png`.
- Todas las piezas que cuentan perfiles: el texto se calcula aparte de las curvas (`perfiles.detectar_boceto`), así que sus perfiles ahora se pisan con los de abajo.
- B-152: los textos nuevos son más grandes (la altura es el alto de la A). Abrir un documento viejo con texto y mirar que no cambie; todas las piezas que escriben texto.
- ⚠ Rendimiento de `_arreglo_coherente` con 200 W sobre un círculo: lo mide `tests/test_boc28_rust.py`, sin correr con carga.
- TXT-9 (2026-11-12, E1): el clic de un comando que pide perfil y cae en un trazo con el relleno debajo avisa con el aviso flotante (`ui/visor3d.py`, `ui/ventana.py`): falta la prueba de humo y la pieza `objetos_vectoriales`.
- B-367/B-251 (2026-11-12, E1): Rosca rellena o tornea toda la cara al Ø del tamaño (`nucleo/solidos_crear.py` › `rosca`): correr todos los tests de rosca, agujero y fijaciones, y la caza `tema rosca`.

## 3g. Tarea nueva: parámetros (PAR-1 a PAR-11, B-138 a B-143)

Hecha, sin commitear, sobre `main`. Falta en el cierre:
- Suite completa: el evaluador lo usan todos los pasos, y cada documento suma filas de pasos a `doc.parametros`. Los tests que se tocaron ya corrieron; el resto no.
- Pieza de ventana `parametros` (ya en `PIEZAS`).
- Prueba de humo: `ui/comando.py` usa ahora `CampoExpresion` en todos los campos de expresión.

## 3h. Tarea nueva: reconstruir sólido (RI-1 a RI-6, F10, F11)

Fases 0 a 3 construidas (F10, SC13, F11 y RI-1 cerradas; RI-2 Parcial). Sin commitear, sobre `main`. Falta en el cierre:
- Tests: `test_comparar_malla.py`, `test_formas_malla.py`, `test_reconstruir_malla.py` y, por lo tocado, `test_cobertura_ui_api.py`, `test_iconos_extra.py`, `test_api_malla.py`, `test_claves_comandos.py`, `test_doc_agentes.py`, `test_patrones_boceto.py`, `test_boceto_fase8_malla.py`.
- Pieza de ventana `mapa_desviacion` (ya en `PIEZAS`).
- Banco: desde `clon/`, `.venv/Scripts/python.exe ../scripts/turno.py --plazo 1700 -- .venv/Scripts/python.exe ../scripts/bench_reconstruir.py correr`, y `reales` con `--plazo 3400`. El banco se genera con `generar` en `evidencias/reconstruir_2026-11-01/banco/`.
- RI-3 a RI-6 y ESC siguen sin empezar.

## 3i. Tarea nueva: escanear con el celular (ESC-1 a ESC-7)

Upgrade a futuro: no entra en las pruebas hasta que Gerardo lo pida.

## 3j. Tareas nuevas: SUPERFICIE, ENSAMBLAR y ANIMACIÓN

Sin empezar: SUP-27 a SUP-31, ASM-17 a ASM-20, ANI-1 a ANI-5 y B-145. Cada una suma tests y prueba de ventana. ANIMACIÓN no tiene pieza propia en `todo.py`.

## 3k. Tarea nueva: plástico y extensiones (PLA-1 a PLA-14, SOL-22)

Sin empezar. Cada herramienta suma tests y la pieza nueva `plastico` en `todo.py`. PLA-7 y PLA-11 piden comprobar en Fusion real. PLA-12 y EXT-1 a EXT-4 quedan afuera: PLA-12 va aparte y las EXT esperan decisión.

## 3l. Errores que cierran la app y B-157 (B-157, B-158, B-159, B-160, B-170)

Pedido el 2026-11-02. Falta en el cierre: suite completa, humo y `solido_modificar`, `superficie` y `asas`, porque tocan empalme, chaflán, solevación y abrir archivos. Después, `scripts/caza/cazar.py rapida` y `noche`, que nunca corrió.

## 3m. Tareas chicas de OpenCode (tandas 1 a 4)

- Tandas 1 a 3 integradas (hasta `30b04d4`): sus tests se corrieron sueltos. Falta verlas en la suite completa y en la prueba de humo.
- Tanda 4 (`fa934e5`) y prueba en Cline (AUD-13, PLA-14) integradas con sus tests sueltos. Falta: suite completa, humo y una pieza de ventana para ANI-4.
- Tanda 5 (H-66, PLA-6, F3, F18) integrada con sus tests sueltos. Falta en la ventana: la pieza `cinta_completa` de `todo.py` (cinta PLÁSTICO) y la vista previa de patrón en puntos y en ruta.
- B-185 integrado con sus tests: falta mirar en la ventana real que la fila elegida se ve elegida y con el borde de origen.
- Tareas del 2026-11-03 (MAL-1, H-67, KS1, H-59 en `b7db046`; PLA-9 después): tests sueltos verdes. Falta: suite completa y humo; en la ventana real, el botón Combinar grupos de caras, elegir una curva de Boceto 3D en el visor, el selector «Preajuste» de Configuración de escena, deshacer con el diálogo Parámetros abierto y un comando de afuera, y SÓLIDO › MODIFICAR › Simplificar › Eliminar caras (clic, elegir, Aceptar, doble clic en el timeline).

- Tarde del 2026-11-03 (en `ca87869`): en la ventana real, SÓLIDO › Simplificar (Eliminar caras, Eliminar operaciones, Reemplazar con primitivas), PLÁSTICO › Apoyo, Vectorizar con Ángulo de esquina y el Preajuste de render; suite completa y humo.

## 3n. Perfiles sin triangulación y reproducción de REMOVEDOR (2026-11-04)

- Incluir `tests/test_perfiles_interior.py` y `scripts/bench_perfiles_interior.py` en el próximo cierre integrado.
- Sigue pendiente la suite completa con los cambios concurrentes. La tanda focalizada de 14 archivos dio 548 passed y 69 failed: un fallo de `test_motor` y los 68 de `test_paridad_motor` por el arranque de OmniKernel, B-189. Repetir ambos después de corregir `_trozos` en `solidos_crear.py`.
- Falta reproducir B-188 con el proyecto `.omnicad` o receta original, incluyendo el boceto/SVG y los movimientos op22/op23/op55. El STEP final disponible no lo reproduce.

## 3o. Auditoría de Extruir en todos los espacios (2026-11-05)

- Pieza nueva `scripts/prueba_ui/extruir_espacios.py` (en `PIEZAS` de `todo.py`): botón Extruir en SÓLIDO, SUPERFICIE y PLÁSTICO (y que CHAPA no lo tenga), clic en perfil y en cara plana con el filtro de Extruir superficie, «Dos lados» con el lado 2 tecleado en −5 mm, Enter, reabrir, deshacer, Inicio › Objeto inclinado y el panel más largo en 1024×640 y 800×520. Corrió en minimizada: 18 comprobaciones (una es el control de que los clics sirven), 4 ✗ esperadas (B-205, B-206 y H-85, dos veces): deben seguir en ✗ hasta que se arreglen.
- Cierre integrado del 2026-11-06 (`evidencias/cierre_2026-11-06/`): corrió en minimizada; sus 2 ✗ son H-85 (resuelto en la rama `codebuddy-nocturna`, sin fusionar). Falta: correrla en `--ventana visible`. Capturas `extruir_*.png` miradas por el coordinador: Aceptar entra en 1024×640 y 800×520; las cajas de valor se pisan (B-207).

## 3p. Tarea nueva: arreglos de Extruir en OpenCode con Sol (B-205, B-206, B-207, B-197)

Prompt en `docs/auditoria_extruir.md` (2026-11-05). Tocará `timeline/operaciones.py`, `timeline/ops_superficie.py`, `nucleo/solidos_crear.py` y las asas de `ui/comandos/solido.py`. Cuando termine: suite completa y prueba de humo, todas las piezas que extruyen (`solido_crear`, `teclear`, `asas`, `herramientas_solido`, `superficie`, `extruir_espacios`) y `extruir_espacios` con `--ventana visible`, mirando las capturas.

## 3q. Tarea nueva: auditoría de Revolución, Barrido y Solevación (2026-11-05)

Solo documenta, sin tocar la app. Si deja la pieza `revolucion_barrido_solevacion`, correrla en el cierre integrado y con `--ventana visible`.

- Pieza nueva `scripts/prueba_ui/revolucion_barrido_solevacion.py` (en `PIEZAS` de `todo.py`): los botones de Revolución, Barrido y Solevación en SÓLIDO, SUPERFICIE y PLÁSTICO (y ninguno en CHAPA), Revolución «Dos lados» con −45° tecleado, Enter, reabrir, deshacer y rehacer, «A objeto» con Dirección, «Proyectar eje», las opciones y el volumen del Barrido con carril, Distancia tecleada («0,5», «0», «1,5», vacío), Solevación de dos cuadros y la fila de una punta, y el Barrido con carril en 1024×640 y 800×520. Corrió en minimizada: 40 comprobaciones, 10 ✗ esperadas (B-208, B-209, B-210, B-211, H-88 dos veces, H-89, H-90 y H-92 dos veces): deben seguir en ✗ hasta que se arreglen.
- Cierre integrado del 2026-11-06: 5 ✗, todas con fila (H-88 ×2, H-89, B-208 resuelto en la rama de Sol, H-90). Falta: correrla en `--ventana visible`. Las sondas sin ventana (`evidencias/ui_2026-11-05/sondas_rbs.py`, 78 casos) se pueden repetir para comprobar los arreglos.

## 3r. Tarea nueva: auditoría de Nervio, Red y Repujado (2026-11-05)

Segunda tanda, va después de la 3q. Si deja la pieza `nervio_red_repujado`, correrla en el cierre integrado y con `--ventana visible`.

- Pieza nueva `scripts/prueba_ui/nervio_red_repujado.py` (en `PIEZAS` de `todo.py`): los botones de Nervio, Red y Repujado en SÓLIDO y PLÁSTICO (y ninguno en SUPERFICIE, CHAPA ni MALLA), el Nervio de una escuadra por el corredor (+1200 mm³, reabrir, deshacer), Grosor tecleado («2,5», «e * 2», vacío, «10 deg», «abc», pegar «3 mm»), Enter, Invertir, dos curvas sueltas, desmoldeo −1° y con extracción, los campos de Fusion del Nervio, la Red con Invertir en una caja hueca, el Repujado con y sin cadena tangente y la Profundidad tecleada, las asas de los tres (3 mm y más allá del cero), la Red con «Más opciones» en 1024×640 y 800×520, y guardar → reabrir. Corrió en minimizada: 82 comprobaciones, 9 ✗ de la app (B-213, B-214, B-215 dos veces, B-216, B-217, H-95, H-97 y H-99): deben seguir en ✗ hasta que se arreglen.
- Cierre integrado del 2026-11-06: 5 ✗, todas con fila (B-215 ×2, resuelto en la rama de Sol; H-95, H-99, H-97). Falta: correrla en `--ventana visible` (el chequeo de Tab necesita el foco real: en minimizada sale con ⚠). Las sondas sin ventana (`evidencias/ui_2026-11-05/sondas_nrr.py`, 61 casos) se pueden repetir para comprobar los arreglos.
- La corrieron con el código de Extruir de OpenCode sin commitear (`comando.py`, `manipuladores.py`, `solidos_crear.py`…): si algo cambia al integrarlo, puede venir de ahí.

## 3s. Tarea nueva: arreglos con Qwen3.8-Flash en cinco tandas (2026-11-05)

Prompt en `docs/arreglos_qwen.md` (B-210, B-211, B-214, B-216, B-217, B-209, H-92, H-86, H-99, H-94). Cada tanda la revisa el coordinador con todos los tests que usan lo tocado. Al terminar las cinco: suite completa y prueba de humo, y las piezas `revolucion_barrido_solevacion`, `nervio_red_repujado`, `solido_crear` y `superficie` con `--ventana visible`.

- Tandas 1 a 4 commiteadas en `main` (`799d6f6`, `7e95678`, `64a79f0`, `ba26cc0`). Cierre completo del 2026-11-06 sobre `ba26cc0`: ruff limpio, suite verde (`parte_04` rehecha en dos mitades por el tope de 900 s; un rojo por falta de memoria de OpenBLAS pasó solo), humo OK, piezas con foco OK. La pieza `solido_crear` daba ✗ en «extruir simétrico» por el defecto nuevo de H-86: la prueba ahora pide «mitad» explícito. Falta: la tanda 5 (H-99, H-94) y las cuatro piezas con `--ventana visible`.

## 3t. Velocidad de pruebas (2026-11-06): lo que queda

- **Cierre del 2026-11-07 (07:27–09:14, de día con la PC en uso, `-n 2`):** A listo (ranking de 9628 tests en `evidencias/tiempos.json`, ninguna tanda pasó los 900 s: la más larga 433 s); E listo (52 piezas con `--paralelo 2` en 34 min, contra 94 en serie; todas las ✗ tienen fila); humo minimizado y `test_motor` OK.
- **D (P-60):** falta el humo en modo `visible` (`OmniCAD.py --prueba-humo` sin la variable, con la PC quieta); el atajo S del humo solo se ejercita ahí.
- **B (P-63):** con `-n 2` la suite dio 1 rojo que pasa solo (B-238) y tardó ~62 min porque compartió la fila de `turno.py` con otra sesión; la memoria libre bajó a 291 MB con la PC en uso. Falta la primera noche con `-n 4` (solo con ≥6 GB libres y nada más corriendo) y medir el pico. Hasta dos noches seguidas en verde, la serie queda con `bash scripts/cierre_completo.sh --serie`.

## 3v. Auditoría de CREAR y MODIFICAR del boceto (2026-11-06, arrancó el 2026-11-07)

- Pedido: `docs/auditoria_boceto_crear_modificar.md`. El cierre del 2026-11-07 (HEAD 8cf46ca) cubrió la fase 1 y B-232 a B-236: suite verde y piezas `boceto_herramientas`, `auditoria_boceto`, `boceto_cotas`, `restricciones_boceto`, `simetria_boceto` e `inferencias` sin ✗.
- **Falta:** B-237 (f5a8e13, después del cierre) en la suite; ver en la ventana copiar un chaflán (Mover con Copiar) y que Alargar un extremo fijo muestre «El extremo es fijo: quitale «Fijo» antes de alargarlo.» sin tocar nada; y la fase 6 de la auditoría (una pieza de ventana por comando de CREAR y MODIFICAR).
- **P-71 (2026-11-07):** los tres casos de MODIFICAR se reprodujeron con Qt nativo y eventos al widget (`test_gizmo_boceto.py::test_p71_…`): aviso de empalme compartido con MCP, Soltar desfase sin conservar cota y Escala con base obligatoria. Ninguno necesitó foco real. Incluir estas regresiones y la doc regenerada en el próximo cierre integrado; no reemplazan las piezas de la fase 6.
- **Falta (2026-11-07, tarde):** suite completa y piezas de ventana del boceto (`boceto_herramientas`, `auditoria_boceto`, `boceto_cotas`) sobre P-69 (f356869), P-68 (1c826f8), P-70 (f088367), P-71 (c86ab4f), H-107 (fbae72b) y H-108 (064f8f0): cada uno cerró con `tests_afectados.py` verde, no con la suite. En la ventana real, con foco: Empalme y Chaflán por vértice (H-107: vista previa al pasar y clic en una punta libre que elige la curva) y la tecla S de Empalme.
- **Falta (P-67, 2026-11-07):** suite completa con P-67 (spline de control en grado 5; corrieron sus 20 grupos de `tests_afectados`); en la ventana, dibujar una spline de control con 4 clics y Enter: el selector «Grado» muestra 5 y la curva queda en grado 3; con 6 clics, grado 5. Pieza: `boceto_herramientas`.
- **Falta (fase 3, 2026-11-07):** `tests/test_boceto_combinaciones.py` (nuevo, por API) en la suite completa; sus combinaciones 1-8 siguen sin probarse desde la ventana (fase 6).

## 4. Cosas que ninguna prueba cubre todavía

| # | Qué falta | Dónde está anotado |
|---|---|---|
| 7 | Pieza completa de principio a fin cambiando una cota, con capturas (punto 9 de la regla «probar como usuario humano») | `CLAUDE.md`: «falta automatizar el 9» |
| 8 | Ventana chica (1024×640 y 800×520) para los paneles NUEVOS (Desfase, patrones de sólidos, multitransformación) | punto 8 de la misma regla; `todo.py` lo cubre solo para las piezas ya escritas |
| 11 | Relleno azul del perfil al dibujar | FU-5 (Sin verificar) |
| 12 | Normal de las superficies nuevas (tubo extruido: ¿mira adentro?) | SUP-23 (Parcial: falta comprobarla en Fusion real) |
| 15 | Sección del análisis: ¿`seccion()` ya evita recalcular el contorno? | CPP-P21 (Sin verificar) |

## 5. Tortura de operaciones y booleanas (hecha el 2026-11-01)

- Corrió completa por la API sin ventana, sobre `main` en 2d8212e (evidencias en `evidencias/tortura_2026-11-01/`, fuera de git): `bench_booleana.py todo`, AUD-6, valores extremos, matriz de booleanas 8×8×8, historial, saturación, patrones de 10.000 copias en Idéntico, Ajustado y Optimizado, y B-48. Los hallazgos están en `docs/seguimiento/` (B-125 a B-129, T-19 a T-23, AUD-6 y RS-X1 con números).
- Queda sin probar:
  - Pasos 200 y cadena 200: con 100 pasos ya tarda 237 s (RS-X1); no tiene sentido medirlos antes de arreglar eso.
  - Las booleanas con la ventana real (panel Extruir y Combinar tecleando valores extremos): todo se probó por la API.
  - La matriz de booleanas corrió con una sola vuelta por celda: sus tiempos no son la mediana de 3.
  - B-48 no se reprodujo (376 cambios a 146 pasos): sigue Parcial.
- No se usó ningún documento de Gerardo.

## 6. Necesitan permiso o a una persona (no los puede hacer la sesión sola)

| Qué | Por qué |
|---|---|
| AUD-9: `pip-audit` (escaneo de CVE) | instalar paquetes requiere permiso |
| AUD-10: instalar el `.exe` publicado en una máquina limpia sin Python | necesita una VM o PC limpia |
| P-11k: comparar EXTRUSOR XOX.f3z contra Fusion | importarlo en Fusion crea diseños en la nube del usuario |
| Escaneo de secretos del workflow de CI (`.github/workflows/instaladores.yml`, paso «Escaneo de secretos») | corre solo en CI; localmente hay que correr el mismo comando antes de cualquier `push` |
| `git push` de `main` | solo con el «sí» de Gerardo; un push a `main` no dispara CI |
| B-363 / B-337: el .f3d ya se comparó en Fusion (2026-11-12, ver B-363). Falta en la PC: abrir el .f3d por el puente (Fusion → STEP → OmniCAD) y medir cuánto tarda OmniCAD con esa STEP de 72,6 MB, y la STEP de SolidWorks en la ventana con el proceso aparte (en la VPS: congelada 91 s, abrir 698 s) | Fusion corre solo en la PC de Gerardo (puente y túnel prendidos) |

## 7. Orden de la noche


1. Verificar con `git status` y la lista de sesiones que no quede ninguna sesión de código trabajando; si no, esperar.
2. RAM libre ≥ 5 GB; cerrar todo lo demás.
3. `bash scripts/cierre_completo.sh` (≈ 1 h). Mirar `evidencias/cierre_<fecha>/resumen.txt`.
4. Cada rojo: reproducir y mirar el log antes de decidir si es bug de la app o de la prueba (omnicad-test, sección 5).
5. Mediciones (#14, #13), después la tortura (§5).
6. Anotar en `PROJECT_LOG.md` (Registro) y en `docs/seguimiento/`; borrar de esta lista lo que quedó verde.
7. Refrescar la página de seguimiento (pasos en `CLAUDE.md`) y avisar a Gerardo los números.
- **Tandas del 3 y 4/11 revisadas e integradas el 2026-11-05** (suite completa en verde salvo B-197, que ya fallaba en HEAD; ruff limpio). Falta probar en ventana real, como usuario: piezas `registro_uso` con foco real (botón «Reportar problema y sugerencia» y la sección Registro de uso de Configuración, en 800x520 y en los dos temas), Unión con el campo Tipo más abajo (ASM-20), línea de tiempo de ANIMACIÓN (ANI-4), Empalme con tabla de grupos (FU-6), barrido de parámetros en INSPECCIONAR (SC18), carpetas del timeline (SC9), cotas de línea base y longitud de arco en DIBUJO (CF-3), organización del boceto y texto en ruta con arrastre (B-187), y el pintado del mapa de entorno en perspectiva (H-56).
- **2026-11-05, Proyección (B-119, B-203, B-204):** verde por API y con clic real en tests/test_proyeccion_seccion.py y tests/test_proyectar_tarjeta.py. Falta en ventana real: Intersecar con Cuerpos, Proyectar en superficie y Curva de intersección; mirar la silueta de la bala en la ventana de Gerardo.
- **2026-11-05, Proyección (H-77, H-78, H-79):** verde por API en tests/test_proyeccion_seccion.py y con arrastre simulado en tests/test_boceto_fase9_3d_ui.py::test_arrastrar_lo_vinculado_al_modelo_lo_suelta_y_deshacer_lo_vuelve. Falta en ventana real: proyectar la bala, mover un empalme antes del boceto en el timeline y mirar que la silueta se rehace y el aviso; proyectar una rosca modelada y medir la espera; incluir un vértice con Incluir geometría 3D, mover el cuerpo y arrastrar el punto con la tríada.
- **2026-11-08 · Falta probar en la ventana (piezas `boceto_herramientas` y `auditoria_boceto`, minimizada) y en la humo:** H-110 (recortar arrastrando), P-75 (empalme sin línea guía, glifo), B-242 (empalme de esquina restringida). Rosca: B-247/B-248 sin el diálogo en la ventana.
- **2026-11-09 · Falta en la ventana y en la humo (fusionados de noche solo con `tests_afectados`):** B-265/B-266, B-268 y B-269 tocan `ui/comando.py` y `ui/ventana.py` (Extruir sólida elige el perfil con clic en el borde; la caja de selección elige perfiles; el navegador no muestra la vista previa): pieza `extruir_espacios` o `solido_crear` minimizada y la prueba de humo. P-94, B-257, B-259, B-260, B-262 y B-263 son de API y timeline: cubiertos por sus tests.
- **2026-11-10 · Fusionados de noche solo con `tests_afectados` (el cierre completo NO corrió: no entraba antes de las 08:00):** P-121 (caja envolvente con caché), B-273 (nombre vigente en navegador y API), P-122 y P-124 (un redibujo al Aceptar/Cancelar y al Terminar boceto, `ui/comando.py` y `ui/ventana.py`), P-123 (polilíneas del boceto en caché, `ui/visor3d.py`), P-125 (tareas aisladas con forma al trabajador vivo, `nucleo/aislado.py`), B-289 (la ✕ del panel de datos), P-130 y P-131 (tests_afectados y turno), B-280 y B-281 (desfase de media cara; aviso «sin solape»). Falta: suite completa, humo y piezas de ventana minimizada (`solido_crear`, `solido_modificar`, `boceto_herramientas`, `extruir_espacios`); en la humo se esperan las 3 fallas de B-291. ⚠ `registro_uso` y Ctrl+Mayús+A de `asistente` (foco real) solo con el OK de Gerardo.
- **2026-11-10 · Fusionados de día solo con `tests_afectados`:** B-290 (Empalme con radio igual al de un arco: error claro), B-282 (botón de selección «Cara +X · Cuerpo1», recorte al final; `ui/comando.py`, `ui/formulario.py`, `ui/modo_boceto.py`) y B-293 (previas del panel con booleanas en serie, `geo.en_serie`; `ui/comando.py`, `ui/comandos/solido.py`). Falta en la ventana y en la humo: mirar el botón de selección con caras de nombre largo; Extruir con 12 o más perfiles del llavero y **Aceptar** (y el recálculo), que siguen en paralelo y no se probaron (`side-session-notes/…/ag8_medicion/perfil_ventana.py extruir`); Revolver, Barrido y Combinar con muchos perfiles en la previa.
- **2026-11-10 · Fusionados de noche solo con `tests_afectados`:** B-271 (Parámetros cancela sus `_poblar` diferidos, `ui/dialogo_parametros.py`) y B-283 (la referencia de una arista recta guarda su `sentido` atado a la curva; `nucleo/referencias.py`, `timeline/entidades.py`). Falta: abrir y cerrar Parámetros en la ventana editando valores; con B-283, Revolver y los patrones con eje en una arista de un cuerpo que un parámetro gira (sin test propio), y abrir un `.omnicad` viejo con ejes en aristas.
- **2026-11-10 · B-298 (OpenCode Sol):** la holgura negativa en Rosca y Agujero roscado da «no puede ser negativa». Falta en la ventana: teclear -0,8 en «Holgura impresión 3D» del panel de Rosca y del Agujero roscado y ver el mensaje en rojo en el pie (antes la previa quedaba lisa y muda).
- **2026-11-12 · P-145 (E1):** la previa de Rosca modelada pinta de azul los tramos de afuera y las crestas. Falta: la humo y mirar en la ventana una rosca interna (agujero roscado) y una larga (M7×50), que el azul no tape nada ni tarde.
- **2026-11-12 · P-135 (E1):** flechas de Desfase y Longitud de Rosca sobre la pared (`FlechaCilindro`). Falta en la ventana: la prueba de humo, la pieza de Rosca de `prueba_ui` (arrastrar las dos flechas, pasar por 0, agujero roscado), y mirar que no se escondan detrás de la rosca modelada.

## Archivos de prueba de referencia (fuera de git)

- `evidencias/archivos_prueba/prusa_core_one.step` (95 MB, 547 cuerpos; pedido de Gerardo 2026-11-12): importación STEP pesada. Se usa para medir el tiempo de importar y la ventana congelada (B-335, B-337), las colgadas y los ensamblajes con muchos cuerpos y componentes (B-336). En la noche: abrirlo con `xvfb-run` y anotar tiempo de lectura, segundos de ventana sin responder y cantidad de componentes y cuerpos.
- `evidencias/archivos_prueba/prusa_core_one.f3d` (21 MB): el original de Fusion del mismo modelo. Sirve para comparar la importación `.f3d` contra la STEP (tiempo, cuerpos y componentes: B-335, B-336, B-337) y para medir el Zstandard del `.f3d` (RS-R1, `scripts/bench_nativo.py`).
