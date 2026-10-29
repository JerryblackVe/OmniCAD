# Mejoras

Lo que ya existe y se puede hacer mejor: rendimiento, interfaz, calidad del código, instalador, documentación. Método y columnas: [README](README.md).

Solo lo que falta resolver: al resolverse, la fila se borra. Verificado contra el código el 2026-10-20 (sección Boceto: 2026-10-23; Hallazgos de pruebas de uso, Superficie y Sólido: 2026-10-24; teselado y previas: 2026-10-28). Total 132: Abierto 74 · Parcial 46 · Bloqueado 4 · Sin verificar 8.

## Pendientes generales

Abierto 24 · Parcial 12 · Bloqueado 3 · Sin verificar 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| P-50 | Previa de Intersecar supera 33 ms aunque el resultado es pequeño | Abierto | Media | Caja/Intersecar sobre placa200: p50/p95/máximo 108/175/220 ms. Kernel 53,3 % y resto de previa 44,0 %; teselado solo 2,4 %. Separar el armado de escena/bocetos y el costo restante del kernel antes de elegir una optimización: esa causa interna todavía es hipótesis. | scripts/medir_previa_comandos.py; docs/auditorias/previa-comandos-2026-10-28.md; omnicad/ui/visor3d.py:541-589; omnicad/timeline/documento.py:823-875 | 2026-10-28 |
| P-51 | Vaciado cerrado bloquea varios segundos la previa de la placa200 | Abierto | Alta | Perfilado 2026-10-28, 3 repeticiones: total de kernel 3225–3516 ms; PerformByJoin 2752–3025 ms, booleana 335–356 ms y validación 69–74 ms. El desfase ya está separado y confirmado. Tres ensayos con proceso aparte y malla preparada se retiraron: con gestos de 9 s los cuadros >100 ms bajaron 27→16→5, pero los máximos finales fueron 115–116 ms. Manipuladores p95 34–37→1,4–1,5 ms; set_modelo 53→8,4 ms; entrega 69→38–39 ms; resultado completo ~6 s. No alcanza el criterio estricto: falta separar los 5 picos restantes y una vía de entrega sin bloquear el cuadro. El kernel aceptado quedó intacto. | scripts/medir_previa_comandos.py; omnicad/nucleo/solidos_modificar.py:1039-1076; evidencias/vaciado_antes.json; evidencias/ensayo_F1.patch; evidencias/noche_F1_9seg_c/ | 2026-10-28 |
| P-40 | Extruir arranca en 10 mm; Fusion arranca en 0 mm y se arrastra la flecha | Abierto | Baja | Video 2026-10-28 11-28-09: en Fusion la distancia empieza en 0,00 mm y el cuerpo aparece al arrastrar; en OmniCAD entra con 10 mm y ya se ve un cuerpo. Es una decisión de producto de Gerardo: replicar Fusion o dejar el cuerpo de entrada. | omnicad/ui/comandos/solido.py (`Extruir`, valor inicial de la distancia) | 2026-10-28 |
| P-43 | El visor vuelve a teselar todos los cuerpos cuando el estado vuelve de otro proceso | Abierto | Media | La caché de `set_modelo` usa `id(c.forma)`; los cuerpos que vuelven del hijo son objetos nuevos aunque no cambiaron (213–284 teselados en 3–4 previas de 71 cuerpos, ≈ 200 ms por previa). Clave por id de cuerpo y revisión, o que el trabajador diga cuáles no cambiaron. Va junto con P-34. Medido tras P-42: un cuadro de ≈ 170 ms una vez por panel (la primera previa aislada deja formas ajenas al visor y la siguiente, en vivo, las retesela). | omnicad/ui/visor3d.py:548-553; docs/auditorias/fluidez-2026-10-28.md | 2026-10-28 |
| P-44 | La vista previa de Extruir tesela el sólido de cero en cada movimiento: 0,73 s con 200 agujeros y 2,95 s con 500 | Abierto | Alta | Previa por transformación (tapas y paredes desde el perfil teselado una vez; cambiar la distancia es mover una matriz) y el sólido exacto al soltar. La parte en Python del teselado (48 %: copia a numpy y normales) pasa a Rust/C++ (P-34); deflexión gruesa mientras se arrastra. | omnicad/nucleo/geometria.py:1048-1068; omnicad/nucleo/render_cpu.py:394-409; omnicad/nucleo/analisis.py:533; scripts/medir_costos_previa.py | 2026-10-28 |
| P-45 | La cámara cambia de golpe al entrar y salir del boceto, con el ViewCube y al Ajustar; Fusion anima esas transiciones | Abierto | Baja | La ayuda de Fusion: «Animate view transitions: animates named view and sketch view transitions» (se apaga en Preferencias). Interpolar la cámara 200–300 ms, interrumpible, con `suavizado` e `interpolar_camara` de `nucleo/animacion.py` y una preferencia para apagarlo. No sirve para tapar bloqueos. | omnicad/ui/visor3d.py:773-796; omnicad/ui/modo_boceto.py:875; omnicad/ui/ventana.py:734; docs/fusion_docs/contenido/fusion-getstarted/fusion-preferences-reference-073442e64a1.md | 2026-10-28 |
| P-54 | Previa de Cortar y Unir sobre una placa de 200 agujeros sigue en ≈ 420–470 ms (ángulo 1,0 durante el arrastre) | Parcial | Media | Medianas placa200 (3 corridas, antes → ahora): Cortar previa 652 → 421 ms y teselado 415 → 229 ms (−45 %); Unir 680 → 468 ms y 414 → 226 ms. No alcanzan el −50 % de teselado que se pedía. Queda además el kernel (106–156 ms) y ≈ 230 ms de teselado: una booleana devuelve todas las caras como nuevas (la caché por cara no acierta; 212 de 212 conversiones), así que haría falta reusar la malla de las caras que no cambiaron por geometría y no por identidad, o llevar la copia a numpy y las normales a Rust/C++ (P-34). Con el ángulo 0,6 el teselado sube a ≈ 360 ms. | clon/omnicad/nucleo/render_cpu.py (`_malla_arrastre`, `ANGULAR_ARRASTRE`, `_mallas_por_cara`); scripts/medir_previa_comandos.py --modelo placa200 | 2026-10-28 |
| P-34 | Reutilizar también la malla fina cuando la topología se duplica al modificar o copiar cuerpos | Parcial | Media | La caché LRU ya reusa arrays de caras intactas y copias con Location (2048 caras, hasta 32 MiB de arrays); los seis casos de previa redujeron T 60–80 % y su costo total 36–72 % con detalle temporal, recuperando el fino al soltar. Queda evitar la conversión completa de copias reales: `solidos_crear.aplicar` usa copy=True y las reparaciones booleanas también reemplazan TShape/triangulaciones. La placa200 todavía cuesta 354–451 ms por previa; no se afirma que llegue a 33 ms. MapNodeArray/MapTriangleArray del binding instalado no exponen buffer NumPy: se conservaron los bucles finos. Separar esas conversiones antes de decidir otro cambio; Rust/C++ sigue necesitando permiso. | omnicad/nucleo/render_cpu.py (_clave_malla_cara, _mallas_por_cara, _malla_arrastre); omnicad/ui/visor3d.py (set_modelo, _refinar_previa); tests/test_teselado_cache.py::test_cache_igual_al_recorrido_original; tests/test_teselado_cache.py::test_tres_copias_con_location_reusan_arrays_locales; tests/test_teselado_cache.py::test_visor_recupera_malla_fina_al_soltar; evidencias/teselado_cache_2026-10-28/ | 2026-10-28 |
| P-35 | `volumen_exacto` de un cuerpo con 500 caras B-spline cuesta 0,5 s por llamada | Abierto | Baja | `aplicar_resultado` lo llama tres veces en una unión (resultado, cuerpo y herramienta): 1,4 s de los 3 s de Unir en `bspline500`. Guardar el volumen por forma en el cuerpo (se invalida al cambiar `forma`) o no medirlo cuando no hay aviso posible. | omnicad/timeline/operaciones.py (`aplicar_resultado`), omnicad/nucleo/geometria.py (`_integral`); scripts/bench_booleana.py bspline500 | 2026-10-26 |
| P-36 | B-39 no revisa con BRepCheck las caras cambiadas con más de 200 contornos | Parcial | Baja | `_es_valida_tras_booleana` las salta porque BRepCheck clasifica los contornos de a pares (3000 agujeros: 11 s); el volumen y las aristas libres siguen vigentes. Revisar solo los contornos nuevos de esa cara (hoy la booleana rearma todos los contornos y no se distinguen por forma). | omnicad/nucleo/geometria.py (`_es_valida_tras_booleana`, `_MAX_CONTORNOS_REVISADOS`) | 2026-10-26 |
| P-33 | CI en GitHub para main: ruff y pytest rápido en cada push (sin la prueba de humo, que pide ventana) | Abierto | Media | Todo. AGENTS.md (Seguridad) ya exige «subir solo con la CI verde» pero no hay workflow: solo `instaladores.yml`, por tag. Puede pedir ajustar tests que necesitan OpenGL en la máquina de GitHub. Pendiente por decisión de Gerardo (2026-10-25). | .github/workflows/ (solo instaladores.yml); AGENTS.md:50 | 2026-10-25 |
| NOV-b80-1 | Dos `_referencia` casi iguales con dialectos distintos | Abierto | Baja | Unificar: borrar la de solido_extra y aceptar `{"body", "vertex"}` en la de construcción (≈55 líneas menos; hoy un agente aprende dos formatos). | omnicad/api/herramientas_solido_extra.py:49 y omnicad/api/herramientas_construccion.py:31 | 2026-10-20 |
| NOV-b80-3 | create_hole(positions) usa un solo cuerpo objetivo | Abierto | Baja | Si el vértice es de otro cuerpo, el agujero se hace en el principal y solo avisa que no cambió el volumen: resolver el cuerpo desde la referencia. | omnicad/api/herramientas_modificar.py:492 | 2026-10-20 |
| NOV-b80-4 | export_parameters no neutraliza celdas que empiezan con = + - @ | Abierto | Baja | Un comentario `=HYPERLINK(...)` sale tal cual y Excel lo ejecuta; decidir si se antepone `'` sin romper la ida y vuelta con la tabla de la ventana. | omnicad/api/herramientas_parametros_csv.py:23 | 2026-10-20 |
| P-12b | Registrar la tarea programada de Windows para el informe mensual | Abierto | Baja | La tarea no se registra sola; el comando está en el docstring del script. | scripts/novedades.py | 2026-10-20 |
| P-26a | CI en macOS (ruff + pytest + humo) para ver qué falla | Abierto | Baja | El workflow solo tiene jobs de Windows y Ubuntu. | .github/workflows/instaladores.yml | 2026-10-20 |
| P-8d | Paquetes .deb o Flatpak para Linux (dicho como «quizás») | Abierto | Media | Sin empezar; hoy solo AppImage. | instalador/linux/ solo tiene armar_appimage.sh | 2026-10-20 |
| P-10b-d | Fase 1: andamiaje Rust + R1 (Zstandard) de punta a punta con el instalador | Abierto | Media | Mover el descompresor zstd_puro a Rust y probar empaquetado .pyd en PyInstaller e instalador. | omnicad/io_archivos/zstd_puro.py sigue en Python puro; clon/rust/src/lib.rs sin zstd | 2026-10-20 |
| P-10b-j | Bajar el dibujo Qt del boceto (11 ms con 10 000 puntos al mover la cámara) | Abierto | Media | La meta < 5 ms del repintado completo no se cumple. | PROJECT_LOG.md:341 (proyectar 64,6 a 13,9 ms; Qt suma 11,5 ms) | 2026-10-20 |
| P-12d | Cada mes elegir 3 funciones útiles, programarlas y sacar versión nueva | Abierto | Media | Proceso recurrente sin ejecutar; anotar y subir cada versión a GitHub. | docs/novedades/ solo tiene 2026-10.md | 2026-10-20 |
| P-22c | Casos límite y tolerancias explícitas en solver e intersecciones | Abierto | Media | Esferas anidadas y banda de tangencia sin tratar. | omnicad/restricciones/solver.py sin tratamiento de tangencia | 2026-10-20 |
| P-32 | Probar el motor omnikernel (Rust) como segunda opinión en uniones casi tangentes | Abierto | Media | Tras reparar la revisión de B-39, una nueva corrida de 4 000 casos con controles geométricos completos deja 1 caso señalado (0,025 %): b39-1414, con una arista no manifold nueva, cuerpo estanco y válido. La cifra previa de 0,05 % usaba un validador que omitía controles geométricos y no sirve como comparación de validez. Plan: (1) comparar el caso 1414 y el fuzzer con omnikernel, sin cambiar los chequeos ni las semillas; (2) si resuelve el resto sin perder material, usarlo solo como último reintento de `geo.booleano`, convirtiendo la salida a B-rep OpenCascade; (3) si no lo resuelve, anotarlo en `docs/comparacion_motores.md` y mantener el error claro. Un contacto tangente exacto puede no tener cura en ningún kernel. | nucleo/geometria.py (`booleano`, `_REINTENTOS_BOOLEANA`); scripts/fuzz_b39.py; tests/test_b39_revision.py; nucleo/omnikernel/; docs/comparacion_motores.md | 2026-10-27 |
| P-26b | OpenGL 4.1 core en macOS (shaders GLSL 410, contexto core) | Abierto | Media | Los shaders usan #version 120. | omnicad/ui/render.py:124,133,221 | 2026-10-20 |
| P-26c | Compilar el módulo Rust para arm64 y x86_64 | Abierto | Media | Solo hay .pyd de Windows. | omnicad/_rs.cp312-win_amd64.pyd | 2026-10-20 |
| P-10b-e | Fase 2: malla en Rust (R7, R2, R8, R10) con BVH R3 | Abierto | Alta | Reducir malla, half-edge, soldado y E/S de texto siguen en Python. | clon/rust/src/lib.rs solo tiene 3 funciones de render | 2026-10-20 |
| P-10b-g | Fase 4: remallado R6 en Rust y subir los topes | Abierto | Alta | Remallar sigue en Python con topes de 100 000 triángulos. | omnicad/nucleo/malla.py (TRIANGULOS_MAXIMOS_REMALLADO) | 2026-10-20 |
| P-10b-f | Fase 3: boceto en Rust (R5, solver R4, R9) | Abierto | Muy alta | El solver sigue en scipy; con la colocación constructiva (SC4) 400 líneas arrastran en 258 ms, medir antes de pasar a Rust. | omnicad/restricciones/solver.py (least_squares method=lm); clon/rust sin módulo de boceto | 2026-10-20 |
| P-2c | Documentación y README en inglés | Parcial | Media | Traducir docs/ y docs/agentes; solo el README tiene versión inglesa. | README.en.md existe; docs/*.md solo en español | 2026-10-20 |
| P-9j | Revisión crítica de cada pantalla (estados vacíos y de error, textos) con capturas | Parcial | Media | Solo 13 pantallas auditadas; faltan estados vacíos/errores y el objetivo de identidad visual propia. | scripts/capturas_ui.py; evidencias/capturas/p9b_antes y p9b_despues (13 pantallas cada una) | 2026-10-20 |
| P-22d | Verificar tablas ISO 965/273 y reglas de chapa contra la norma | Parcial | Media | ISO 965-1 solo verificada para M3-M39; falta ISO 273 y K-factor de chapa. | omnicad/nucleo/tolerancias.py:10,163-200; commit 992b93c | 2026-10-20 |
| P-5b | Resto de mejoras de vectores, SVG, edición y texto según el manual de Blender | Parcial | Alta | Sigue la lista priorizada de docs/brechas_blender.md (vista previa de trazos, esquinas, texto avanzado). | tests/test_texto_vectores.py (64 pruebas); B4 queda con vista previa y esquinas pendientes | 2026-10-20 |
| P-6d | Revisar ensamblaje, animación, mallado, historial y movimiento de piezas | Parcial | Alta | Revisión general sin cerrar: faltan conjuntos de contacto, uniones leva/tornillo y gráficos del estudio de movimiento. | omnicad/api/herramientas_animacion.py (15 herramientas); herramientas_ensamble.py:621,703 (create_rigid_group, motion_study); tests/test_api_animacion.py; tests/test_ensamblar.py | 2026-10-20 |
| P-10b-c | Fase 5: P6, P7, P8, P9, P13 (previa asíncrona, memo por paso, firmas) | Parcial | Alta | P6 completo (vista previa en un proceso aparte) y deshacer serializado en un hilo siguen abiertos. | omnicad/timeline/documento.py (_de_memo, _aplicar_memo); omnicad/nucleo/referencias.py:198 _firmas; omnicad/io_archivos/proyecto.py autoguardar_en_hilo | 2026-10-20 |
| P-10b-h | Proceso trabajador en Python: teselado y HLR en paralelo, cancelables | Parcial | Alta | Solo autointersecciones y HLR exacto corren aisladas con tope; falta el pool para teselado y vistas. | omnicad/nucleo/aislado.py (subproceso con tope de tiempo); tests/test_b48_crash.py | 2026-10-20 |
| P-4a | Revisar entero el motor de render, materiales, colores e iluminación | Parcial | Muy alta | Hoy solo hay motor local OpenGL (GLSL 120) y CPU (con Rust); falta revisión completa y las listas KeyShot/V-Ray. | omnicad/ui/render.py:1589-1590 (combo Motor: GL y CPU); omnicad/nucleo/render_cpu.py; tests/test_render.py; tests/test_render_aspecto.py | 2026-10-20 |
| P-10f | Paso 6: Rust con PyO3 solo si los números lo justifican | Parcial | Muy alta | Hecho R11; el resto de R1-R13 sin empezar (ver filas RS-). | clon/rust/src/lib.rs (rasterizar, visibilidad, oclusion); omnicad/nativo.py | 2026-10-20 |
| P-8b | Validar el .exe armado por GitHub en una PC limpia | Bloqueado | Baja | Hace falta una máquina limpia (el armado local sí se probó). | README.md:74 avisa de SmartScreen; sin registro de prueba en PC limpia | 2026-10-20 |
| P-30-dec | Decidir FreeCAD como oráculo externo de SC1 y los paquetes hidapi y mutmut | Bloqueado | Baja | Decisiones del usuario; no instalar sin permiso. | PROJECT_LOG.md:112 | 2026-10-20 |
| P-1b | Probar en Linux nativo (GNOME/KDE, GPU real, atajos, diálogos de archivo) | Bloqueado | Media | Falta una PC con Linux nativo para probar a mano atajos y diálogos de archivo. | Solo hay corridas en WSL2 (Registro); el CI de Linux arma AppImage pero no prueba la interfaz | 2026-10-20 |
| P-11k | Comparar EXTRUSOR XOX.f3z contra Fusion y probar mallas convertidas | Sin verificar | Baja | Importarlo en Fusion puede crear diseños en la nube del usuario; sin ejemplo BINCHA a mano. | PROJECT_LOG.md:32 | 2026-10-20 |
| P-31-lic | Respetar licencias AGPL-3.0 (PartMode, QymCAD, Chili3D): solo ideas, nunca código | Sin verificar | Media | Regla de proceso, no tarea; no se puede comprobar contra el código. | PROJECT_LOG.md:117 | 2026-10-20 |

## Hallazgos de pruebas de uso

Abierto 5 · Parcial 2.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| H-53 | `execute_code` no devuelve imágenes: un `get_viewport_image` hecho adentro sale como texto | Abierto | Baja | Dentro de `execute_code`, `result = llamar("get_viewport_image", ...)["result"]["image"]` devuelve el objeto `Imagen` en su repr (aviso «result no es JSON: se devuelve su texto (repr)»), con los bytes enmascarados: el agente no ve la imagen y tiene que escribir el PNG a un archivo temporal y leerlo con su herramienta de archivos. Que `execute_code` detecte `Imagen` (o un dict con `image`/`png`) y lo entregue como contenido de imagen (PNG base64), como hace la herramienta directa. | repro 2026-10-24 en sesión en vivo: execute_code con `result` = imagen de `get_viewport_image` → aviso «result no es JSON: se devuelve su texto (repr)» | 2026-10-24 |
| H-52 | `extrude` con `profile="all"` ignora en silencio las curvas del boceto que no cierran región | Abierto | Baja | Si hay AL MENOS una región cerrada, el corte sale `ok` y solo se hacen esas: la respuesta trae `profiles_used` pero no dice cuántas curvas quedaron afuera ni cuáles. En un boceto con 7 perfiles, 3 de ellos abiertos por un error propio, el corte salió `ok` y la pieza quedó con 4 huecos de 7, sin aviso. Avisar el número de curvas ignoradas (y sus ids) cuando el boceto tenga curvas que no forman perfil. | omnicad/api/herramientas_solido.py:253 (devuelve `profiles_used`, sin aviso de lo que quedó afuera); omnicad/api/herramientas_boceto.py:190-199 (solo avisa cuando NO hay ninguna región) | 2026-10-21 |
| H-51 | El test de seguimiento saltea sin avisar una fila con una barra vertical en una celda | Abierto | Baja | `_filas` parte la línea por la barra vertical, aunque esté escapada en un selector: la fila da 8 celdas y se descarta, así que su ID, estado y evidencia quedan sin validar. Partir respetando la barra escapada, o fallar si una fila de tabla no da 7 celdas. | tests/test_seguimiento.py::_filas | 2026-10-21 |
| H-50 | La pista del chaflán propone como máximo la misma distancia que falló | Abierto | Baja | Caja 20×20×10, `chamfer` de las 4 aristas verticales con `distance=10`: falla (OPERATION_FAILED, bien) y la pista dice «Distancia máxima aproximada: 10 mm». Ese máximo no se alcanza: decir «menor que 10 mm». Con 9,99 da 2003,998 mm³, la cuenta exacta. | omnicad/nucleo/solidos_modificar.py:483 | 2026-10-21 |
| H-5 | Insertar componente no distingue pieza de ensamble | Abierto | Media | Decidir si hace falta el modo «diseño de pieza» y deshabilitar Insertar componente ahí. | grep sin resultados: solo ui/navegador.py:220 pone la etiqueta «Diseño de piezas» (informativa) | 2026-10-20 |
| H-49 | Parámetro body frente a bodies entre herramientas | Parcial | Baja | Aceptar `body` como alias de `bodies` o sugerir «¿quisiste decir bodies?» en el error. | api/registro.py:243-252 (el error lista argumentos válidos y firma); api/herramientas_inspeccion.py:207 (solo bodies); sin alias | 2026-10-20 |
| H-37 | Barrido sin cubrir: interfaz, 51 tipos de operación, .fclone y .f3d | Parcial | Media | Falta barrido automático de tipos sin caso válido; solo hay tests sueltos por tipo. | tests/test_io.py:93 (.fclone); tests/test_f3d_nativo.py; tests/test_chapa.py (unir plegando); tests/test_fijaciones.py; humo 168 pasos según el log (no corrido acá) | 2026-10-20 |

## Fusion 360

Abierto 4 · Parcial 1 · Sin verificar 1. Especificación: [brechas_fusion.md](../brechas_fusion.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| FU-4 | Asas de conicidad del lado 2 y desfase de inicio en Extruir | Abierto | Baja | Asas para conicidad2 (ya existe en la API) y para el desfase de inicio | ui/comandos/solido.py:74-100 (solo asas distancia, distancia2 y conicidad del lado 1); api/herramientas_solido.py:174 | 2026-10-20 |
| FU-2 | Imagen del agujero con cotas editables en el diálogo | Abierto | Media | Esquema del agujero con cotas editables dentro del diálogo de Agujero | ui/comandos/crear.py:314 (Agujero solo con campos de texto; sin imagen en ui/comando.py) | 2026-10-20 |
| FU-3 | Cota de ángulo contra el eje X y barrido del arco | Abierto | Media | Cota de ángulo línea contra eje X y barrido del arco de centro escrito | restricciones/boceto.py:1606 (la cota de ángulo solo admite linea-linea) | 2026-10-20 |
| FU-6 | Tabla de grupos de aristas en Empalme (radios distintos) | Abierto | Media | Varios grupos de aristas con radio propio por operación (el núcleo ya admite grupos) | timeline/ops_modificar.py:197-226 (OpEmpalme con un solo grupo y un solo radio) | 2026-10-20 |
| FU-10 | .f3z con referencias externas | Parcial | Media | Resolver los diseños referenciados; hoy se abre solo el diseño principal | io_archivos/f3d_nativo.py:24,70; io_archivos/abrir_externo.py:39 | 2026-10-20 |
| FU-5 | Relleno azul del perfil en la vista previa al dibujar | Sin verificar | Media | Comprobar en la app si el perfil se rellena mientras se dibuja | ui/editor_boceto.py: sin código de relleno de perfil encontrado, pero no se probó en la app | 2026-10-20 |

## FreeCAD

Parcial 4. Especificación: [brechas_freecad.md](../brechas_freecad.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| F4 | Referencias perdidas: reparar al editar un paso temprano | Parcial | Media | Reelegir en el acto la referencia perdida desde el panel del paso | nucleo/referencias.py (firmas geométricas); timeline/entidades.py:196; api/errores.py:208 REFERENCE_LOST; tests/test_comandos.py::test_referencias_de_aristas_sobreviven_a_un_cambio_de_cota; tests/test_hallazgos_tortura.py::test_t03_el_chaflan_del_borde_tras_un_vaciado_sobrevive_a_un_cambio_de_cota_del_29_por_ciento | 2026-10-20 |
| F5 | Diagnóstico del boceto: restricciones en conflicto y redundantes | Parcial | Media | Decir cuáles restricciones chocan o sobran y elegirlas desde la lista de avisos | restricciones/solver.py:36-57; ui/editor_boceto.py:616-645 (deshace la que sobre-restringe); ui/modo_boceto.py:754 | 2026-10-20 |
| F12 | Herramientas de B-spline | Parcial | Media | Insertar nudo, subir/bajar grado, unir curvas y convertir a B-spline como herramientas | restricciones/boceto.py:198-207 (spline por control, grado 3 o 5, pesos y nudos), :486 _insertar_nudo interno; ui/editor_boceto.py:2654 (marco de control); ui/modo_boceto.py:90 | 2026-10-20 |
| F14 | Piezas estándar ampliadas (rodamientos, pasadores, insertos) | Parcial | Media | Rodamientos, pasadores e insertos roscados (hay tornillos, tuercas, arandelas, varilla y espárragos) | nucleo/fijaciones.py:52 FAMILIAS; tests/test_fijaciones.py | 2026-10-20 |

## Plasticity

Parcial 3. Especificación: [brechas_plasticity.md](../brechas_plasticity.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PL3 | Plano de trabajo con una tecla (Espacio) | Parcial | Baja | Mayús+Espacio desde la cámara y que primitivas y Mover arranquen en ese plano | fdc9366; ui/ventana.py:395,2088; tests/test_plasticidad.py::test_espacio_arranca_el_boceto_sobre_la_cara_ya_elegida | 2026-10-20 |
| PL1 | Un comando contextual según lo elegido (Desfase, Unir, Extender…) | Parcial | Media | Unir, Invertir, Extender, Reconstruir, Alinear e Imprimir siguen como botones propios | 22c252d; ui/comandos/modificar.py:757 (Desfase); api offset_faces, offset_edges; tests/test_pl1_desfase.py | 2026-10-20 |
| PL13 | Modo Render en el visor con HDRI integrados | Parcial | Media | HDRI integrados (hoy los entornos son degradés de cielo) | ui/render.py:399 (visor con aspectos, entorno y sombras); nucleo/render_cpu.py ENTORNOS; sin HDRI (grep) | 2026-10-20 |

## Blender

Parcial 3. Especificación: [brechas_blender.md](../brechas_blender.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| B19 | Normales y sombreado al exportar mallas | Parcial | Baja | Elegir suavizado por ángulo y normales ponderadas al exportar mallas | io_archivos/gltf.py:10,46 (normales por vértice con ángulo de pliegue) | 2026-10-20 |
| B8 | Orientaciones y pivotes (global, local, normal, vista, cursor 3D) | Parcial | Media | Selector de orientación y pivote (mediana, caja, activo) y cursor 3D | ui/comandos/modificar.py:462-500 (Mover/copiar con pivote elegible y tríada); ui/manipuladores.py Triada | 2026-10-20 |
| B9 | Limpieza de malla ampliada | Parcial | Media | Disolver por ángulo, hacer plano y simetrizar (triángulos a cuadriláteros no cabe) | c1c40f2; nucleo/malla.py:2403-2420; api clean_mesh; timeline OpLimpiarMalla; tests/test_api_malla.py::test_limpiar_deja_una_malla_cerrada_y_es_editable | 2026-10-20 |

## Rhino 8

Abierto 1 · Parcial 5. Especificación: [brechas_rhino.md](../brechas_rhino.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RH14 | Dibujo: cotas de curva, área y volumen; estilos; plantillas de hoja | Abierto | Media | Cotas de longitud de curva, área y volumen; estilos importables; plantillas de hoja | nucleo/dibujo.py: sin esas cotas, estilos ni plantillas (grep) | 2026-10-20 |
| RH13 | Análisis ampliado: continuidad, desviación, normales visibles | Parcial | Media | Continuidad por borde G0/G1/G2, desviación entre curvas o puntos y normales visibles | 4fca4c7 (aristas abiertas, no manifold y espesor); nucleo/revision.py; api check_geometry, check_printability; tests/test_revision.py | 2026-10-20 |
| RH16 | Modos de pantalla por objeto y poses guardadas | Parcial | Media | Modos de pantalla por objeto (Pluma, Técnico, Fantasma), selecciones con nombre y disposición de ventana | ui/visor3d.py:70 ESTILOS (global); ui/navegador.py:221 y ui/ventana.py:2031 (vistas guardadas); api set_body_opacity | 2026-10-20 |
| RH17 | Bloques vinculados a un archivo que se recarga | Parcial | Media | Vínculo a un archivo externo que se recarga si cambió («Actualizar si cambió el archivo») | 4b50c6f; api realize_copies («Hacer única»); timeline/ops_ensamblar.py:499 OpInsertarDiseno; tests/test_pl8_instancias.py | 2026-10-20 |
| RH18 | Curvas desde superficies y cuerpos (isocurvas, contorno, silueta) | Parcial | Media | Sacar isocurvas, contorno por cortes paralelos, silueta y tirar como curvas de boceto | api/herramientas_boceto.py:1581 project_to_sketch (proyectar e intersecar aristas, caras y cuerpos); sin Contour ni ExtractIsocurve | 2026-10-20 |
| RH12 | Gumball al elegir e imanes en el visor | Parcial | Alta | Manipulador contextual al elegir (flechas de mover/extruir/escalar) y barra de imanes con seguimiento | ui/manipuladores.py (manipuladores dentro de cada comando); ui/comandos/modificar.py PulsarTirar; ui/sugerencias.py:30 (tira de comandos); mismo trabajo que B7 | 2026-10-20 |

## KeyShot

Parcial 2. Especificación: [brechas_keyshot.md](../brechas_keyshot.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| KS3 | Material completo: refracción, subsuperficie, anisotropía, emisivo, mapas | Parcial | Alta | El render ignora translucidez, emisividad, relieve y resalte; faltan IOR, subsuperficie y mapas. | omnicad/nucleo/aspectos.py:5-11,35-43 (el modelo los guarda, el render usa solo color, metálico, aspereza, transparencia, barniz, patrón) | 2026-10-20 |
| KS11 | Salida con alfa y por pases (EXR, TIFF, PSD) | Parcial | Alta | Faltan EXR/TIFF/PSD y pases (difuso, reflejo, sombra, ID); el PNG con alfa ya existe. | omnicad/ui/render.py:1595 (Fondo transparente), :1647 (solo PNG); nucleo/render_cpu.py:993 (fondo_transparente) | 2026-10-20 |

## V-Ray

Parcial 1. Especificación: [brechas_vray.md](../brechas_vray.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| VR13 | Render por mosaicos en varios procesos, cancelable y pausable | Parcial | Alta | Faltan varios procesos, pausa y no bloquear la ventana. | render_cpu.py:736,992-1030 (mosaicos, RenderCancelado); ui/render.py:2131 (QProgressDialog con Cancelar) | 2026-10-20 |

## Boceto (auditoría contra la ayuda de Fusion, 2026-10-23)

Abierto 1. Plan por fases: [plan_boceto.md](../plan_boceto.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| BOC-33 | Tangencia círculo-círculo inferida al dibujar con el ratón | Abierto | Baja | `inferir()` solo propone tangente respecto de una línea (contactos desde un punto base); con otro círculo, arco o elipse no propone nada. Al dibujar un círculo o arco con centro, buscar las curvas circulares cercanas y proponer el radio que lo deja tangente (por fuera: distancia entre centros = r1 + r2; por dentro: |r1 − r2|), engancharlo si el cursor está dentro de la tolerancia y agregar la restricción `tangente` entre las dos curvas, como ya se hace con la línea. La API ya tiene `tangente` entre curvas: no falta herramienta MCP/CLI. Test numérico: radio enganchado y grados de libertad que quedan. | omnicad/restricciones/inferencia.py (`inferir`, `_tangencias`); omnicad/ui/editor_boceto.py (herramienta círculo y arco); tests/test_boceto_fase9_inferencia_curvas.py | 2026-10-25 |

## Superficie (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SUPERFICIE con los artículos de la ayuda de Fusion (sección Fusion-Patch de `docs/fusion_docs/`) y de probar las 14 herramientas por MCP/CLI. Los bugs se reprodujeron; los scripts de prueba (`sonda*.py`) están en `evidencias/superficie_2026-10-24/`, fuera de git.

Abierto 4 · Sin verificar 1.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SUP-20 | Pestaña «Análisis» (Cebra, Mapa de curvatura, Isocurvas) en los diálogos de superficie | Abierto | Media | Fusion la trae en Barrido, Solevación, Parche, Reglada y Extender para juzgar la vista previa. Acá el análisis existe solo como comandos aparte (`analyze_geometry`, INSPECCIONAR). | omnicad/ui/comandos/superficie.py (campos sin análisis); omnicad/api/herramientas_analisis.py | 2026-10-24 |
| SUP-21 | Coser: informar cuántos bordes quedaron libres y cuáles | Abierto | Media | El núcleo ya devuelve `aristas_libres`, pero el aviso dice solo «Quedaron bordes abiertos». Fusion muestra el número de bordes libres y a coser, una tabla navegable y marca en verde los que están dentro de la tolerancia. | omnicad/nucleo/superficies.py:849-868; omnicad/timeline/ops_superficie.py:222-223 | 2026-10-24 |
| SUP-22 | Errores de superficie sin una causa que se pueda corregir | Abierto | Baja | «La revolución falló en el kernel» (perfil que cruza el eje), «El solevado falló en el kernel» y, en el parche G1/G2, «necesita el cuerpo vecino (`soporte`)», un parámetro interno que ni la API ni el diálogo tienen. Decir qué corregir. En la ventana también salen textos del kernel tal cual: «PipeShell : uncompatible wires» (Barrido de superficie con torsión 720 deg) y «BRepFill : The continuity is not G0 G1 or G2» (Parche G2); y el empalme de superficie sobre una arista que no comparte dos caras dice «¿radio demasiado grande?» aunque el radio sea de 1 mm: tendría que decir que la arista es libre. | omnicad/nucleo/superficies.py:326,466,482 | 2026-10-24 |
| SUP-23 | Sentido de la normal de las superficies nuevas | Sin verificar | Baja | Un tubo extruido desde un círculo: el desfase +5 lo achica (la normal mira hacia adentro) y +3 sobre una caja abierta lo agranda. Comprobar con Fusion qué lado debe ser el positivo y mostrar la normal (flecha o dato en `get_scene_info`). | omnicad/nucleo/superficies.py:617 (`desfasar_superficie`) | 2026-10-24 |
| SUP-26 | Extender: el asa de distancia se arrastra hasta valores negativos que dan error | Abierto | Baja | En la ventana, arrastrar la flecha de «Extender» más allá del cero deja la distancia en -6 mm y la vista previa en rojo («La distancia de extensión debe ser positiva»); Empalme, Chaflán, Vaciado y Agujero frenan el asa en 0. Ponerle el mismo tope. | omnicad/ui/comandos/asas_extra.py:272 | 2026-10-24 |

## Sólido (auditoría contra Fusion, 2026-10-24)

Cada fila salió de comparar la pestaña SÓLIDO (y PLÁSTICO, CONSTRUIR, INSPECCIONAR, INSERTAR, SELECCIONAR) con los artículos de la ayuda de Fusion (carpeta `fusion-model`) y de probar unas 70 herramientas por API con valores normales, de borde e inválidos. Los bugs se reprodujeron; los scripts (`s*.py`) están en `evidencias/solido_2026-10-24/`, fuera de git. Lo que ya estaba cargado (SC12, SC3, P-25d, P-25f, P-25g2, P-25i, P-25j) no se repite.

Abierto 4.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|

## Ensamblar (auditoría contra Fusion, 2026-10-25)

Cada fila salió de comparar ENSAMBLAR (uniones, componentes, grupo rígido, vínculos, estudio de movimiento) con los artículos de la ayuda de Fusion (carpeta `fusion-assemble`), de probar unas 60 llamadas por API (`evidencias/ensamble_2026-10-25/a*.py`) y de usar la ventana real como una persona (`scripts/prueba_ui/ensamblar.py`, 224 comprobaciones). Lo que ya estaba cargado (P-25e, P-25e2, SC6, SC7, SC8, SC15, H-4, H-5, H-19, F8, P-6d) no se repite.

Abierto 3.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| ASM-6 | nan e inf dan «Nombre desconocido» | Abierto | Baja | En Accionar uniones, el vínculo y `drive_joint`, escribir `nan` o `inf` responde «Nombre desconocido: 'nan'.», como si fuera un parámetro. Mejor: «No es un número». | omnicad/ui/comandos/ensamblar.py:202-215; api/herramientas_ensamble.py (drive_joint) | 2026-10-25 |
| ASM-7 | Mover el único cuerpo de un componente a otro deja el viejo vacío, fijo y con uniones | Abierto | Baja | `create_component` con un cuerpo que ya tiene componente solo avisa «pasa del componente X al nuevo»: la Base fija queda sin cuerpos, el componente nuevo no es fijo y las uniones del viejo siguen «ok» sin mover nada. Avisar que el componente queda vacío (o heredar lo fijo). | omnicad/timeline/ops_ensamblar.py:252-265 (`OpComponente.ejecutar`) | 2026-10-25 |
| ASM-8 | Suprimir una unión usada por un vínculo culpa al vínculo | Abierto | Baja | `suppress_feature` de la Unión1 que usa un vínculo responde OPERATION_FAILED «El paso Vínculo de movimiento1 falló… Las dos uniones tienen que existir» (borrar da FEATURE_IN_USE claro). Decir qué unión suprimida lo rompe. | omnicad/timeline/ops_ensamblar.py:670-674 | 2026-10-25 |


## Menú del boceto (decisión del usuario)

Bloqueado 1. Las herramientas export_sketch y clean_sketch ya existen: lo que falta es solo el menú.

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| MCP-HAL3 | Menú del boceto sin «Guardar como SVG» ni «Limpiar geometría» | Bloqueado | Baja | Espera decisión del usuario: agregarlos rompe la lista exacta de Fusion. | omnicad/ui/ventana.py:1258 (manejador SVG sigue); export_sketch y clean_sketch existen | 2026-10-20 |

## Capa para agentes (paquetes del plan)

Parcial 1. Especificación: [plan_mcp_cli.md](../plan_mcp_cli.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| PAQ-K | Paquete K: prueba real con agentes (Claude Code, OpenCode, solo CLI, modo en vivo) | Parcial | Media | Según el log solo Claude Code pasó; faltan OpenCode, solo CLI y modo en vivo (no verificable desde el código). | PROJECT_LOG.md:11; tests/test_setup.py | 2026-10-20 |

## SolidCraft

Abierto 2. Especificación: [brechas_solidcraft.md](../brechas_solidcraft.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| SC19 | Un error de operación abre un borrador de reporte (issue de GitHub) con el contexto y una captura | Abierto | Baja | SolidCraft arma, desde un error o la Ayuda, un borrador editable con versión, paso que falló, parámetros y una captura opcional que la persona revisa; abrir GitHub no lo envía. Acá hay informes de error (herramienta de revisión) pero ningún borrador listo para publicar. Nunca se envía solo (regla de salida hacia afuera). | grep issue/borrador en clon/omnicad/ui sin resultados | 2026-10-26 |
| SC20 | Abrir un proyecto mostrando enseguida una imagen provisional desde una caché de mallas, mientras se recalcula | Abierto | Media | SolidCraft guarda mallas ya teseladas en una caché del archivo y las muestra al abrir mientras reconstruye; la caché nunca reemplaza el diseño. Acá solo se guarda `cache/pasos.json` (`io_archivos/proyecto.py:85`): al abrir hay que esperar el recálculo (BINCHA.f3d tarda 23 s). Atar al tamaño del archivo y a la versión del núcleo para que no muestre algo viejo. | omnicad/io_archivos/proyecto.py:85 (la caché no guarda mallas) | 2026-10-26 |

## Otros CAD libres

Abierto 1 · Parcial 4. Especificación: [brechas_cad_libres.md](../brechas_cad_libres.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CL2 | Resultado con efecto observado en cada herramienta | Abierto | Media | Campo applied/moved/revisión final en la respuesta de llamar(). | omnicad/api/registro.py:310 (devuelve solo ok, result, avisos) | 2026-10-20 |
| CL7 | Ayuda del MCP según la versión que corre | Parcial | Baja | Sellar la guía con la versión; hoy viaja en el paquete sin indicarla. | omnicad/api/herramientas_avanzado.py:865-875 (get_guide); api/guia/*.md | 2026-10-20 |
| CL4 | Elegir caras por descripción con candidatos y motivo | Parcial | Media | Faltan selectores por intención, propiedades devueltas y aviso de ambigüedad. | omnicad/api/herramientas_inspeccion.py:367-382 (find_faces, find_edges con selectores) | 2026-10-20 |
| CL5 | Diagnóstico para el agente: registro de operaciones y fallos | Parcial | Media | Registro de operaciones y contexto de restricciones y kernel. | omnicad/api/herramientas_dev.py:201-209 (list_error_reports, read_error_report) | 2026-10-20 |
| CL8 | Importar declarando qué se reconstruyó y qué quedó fijo | Parcial | Alta | El .f3d ya declara al abrir su historial sin traducir y los bocetos que reconstruyó; falta el mismo informe en STEP, IGES, mallas y DXF. | omnicad/io_archivos/f3d_historial.py; tests/test_f3d_historial.py::test_abrir_un_f3d_con_historial_avisa_lo_que_no_se_tradujo | 2026-10-26 |
| P-11n | .f3d: Zstandard y lector SAB en Rust | Abierto | Alta | De los 23 s de BINCHA, 8,6 s son el descompresor Zstandard en Python puro (30 MB) y 3,6 s el lector SAB: datos puros para un módulo PyO3 (el toolchain ya está en `clon/rust`). Pide una dependencia nueva (`ruzstd`) o escribir el decodificador: necesita permiso. | omnicad/io_archivos/zstd_puro.py; omnicad/io_archivos/sab.py; docs/f3d_formato.md | 2026-10-26 |
| P-11o | .f3d: mallas convertidas grandes entran sin reparar | Abierto | Media | Un cuerpo abierto de más de 2000 caras no pasa por ShapeFix (con 18 716 caras tardaba 247 s): entra como superficie y una parte queda con caras inválidas (338 de 3 516 en BINCHA). Habría que repararlo por partes o en Rust, solo si el usuario lo muestra. | omnicad/nucleo/acis_occ.py (CARAS_SIN_ARREGLO); tests/test_f3d_nativo.py::test_una_malla_abierta_enorme_no_pasa_por_shapefix | 2026-10-26 |

## Texto y vectores

Parcial 1. Especificación: [plan_texto_vectores.md](../plan_texto_vectores.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| TXT-7 | Fase 7 velocidad (SVG de 5000 nodos en menos de 1 s) | Parcial | Media | Bajar de 2,5 s a menos de 1 s el SVG de 5000 nodos. | El log midió 2,5 s; la meta < 1 s no se cumple. tests/test_texto_vectores.py | 2026-10-20 |

## Rust

Abierto 12 · Parcial 2. Especificación: [plan_rust.md](../plan_rust.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| RS-R13 | R13 menores (RDP, DXF/SVG, recortes, generar_grupos) | Abierto | Baja | Ganancia absoluta chica. | omnicad/io_archivos/vectorizar.py; dxf.py | 2026-10-20 |
| RS-R1 | R1 descompresor Zstandard en Rust | Abierto | Media | Sigue en Python puro (zstd_puro.py); sin zstd en el crate. | omnicad/io_archivos/zstd_puro.py; clon/rust/src/lib.rs sin zstd | 2026-10-20 |
| RS-R8 | R8 dedupe de filas, soldado y normales suaves | Abierto | Media | Sin empezar. | omnicad/nucleo/malla.py | 2026-10-20 |
| RS-R9 | R9 hit-testing del boceto | Abierto | Media | Sin empezar. | omnicad/ui/editor_boceto.py | 2026-10-20 |
| RS-R10 | R10 lectura y escritura de mallas en texto | Abierto | Media | Sin empezar. | omnicad/nucleo/malla.py | 2026-10-20 |
| RS-R12 | R12 quitar aristas ocultas superpuestas (dibujo) | Abierto | Media | Sin empezar. | omnicad/nucleo/dibujo.py:269 | 2026-10-20 |
| RS-R2 | R2 reducir malla (QEM) en Rust | Abierto | Alta | Depende de R7. | omnicad/nucleo/malla.py _Editor; clon/rust/src/lib.rs sin malla | 2026-10-20 |
| RS-R3 | R3 BVH de triángulos (choque, más cercano, espesores) | Abierto | Alta | Sin BVH; rayos con numpy y descarte por caja. | omnicad/nucleo/revision.py; omnicad/ui/visor3d.py:165 rayo_caja | 2026-10-20 |
| RS-R5 | R5 geometría de boceto (de Boor, intersecciones) en Rust | Abierto | Alta | Sin módulo Rust de boceto. | omnicad/restricciones/boceto.py | 2026-10-20 |
| RS-R6 | R6 remallar isótropo en Rust | Abierto | Alta | Sin empezar. | omnicad/nucleo/malla.py | 2026-10-20 |
| RS-R7 | R7 núcleo half-edge / topología de malla | Abierto | Alta | Base de R2 y R6. | omnicad/nucleo/malla.py _Topo | 2026-10-20 |
| RS-R4 | R4 kernel del solver (jacobiano analítico) en Rust | Abierto | Muy alta | Solver sigue en scipy. | omnicad/restricciones/solver.py | 2026-10-20 |
| RS-P3 | P3 repintado del boceto proyectando en bloque | Parcial | Media | Proyección 64,6 a 13,9 ms con 10 000 puntos; la meta < 5 ms del repintado completo no se cumple (Qt suma 11,5 ms). | omnicad/ui/editor_boceto.py _poli_px; PROJECT_LOG.md:341 | 2026-10-20 |
| RS-P6 | P6 vista previa de comandos fuera del hilo de la interfaz | Parcial | Alta | La previa se reusa al aceptar; sigue en el hilo de la ventana (haría falta un proceso). | tests/test_rendimiento_arreglos.py:147; omnicad/ui/comando.py | 2026-10-20 |

## C++

Abierto 6 · Parcial 4 · Sin verificar 1. Especificación: [plan_cpp.md](../plan_cpp.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| CPP-P17 | P17 reusar BRepClass3d_SolidClassifier | Abierto | Baja | Se crea un clasificador por punto. | omnicad/nucleo/fijaciones.py:636; omnicad/nucleo/geometria.py:630 | 2026-10-20 |
| CPP-C5 | C5 clasificación masiva de puntos contra sólidos | Abierto | Media | Ver CPP-P17. | omnicad/nucleo/fijaciones.py:636 | 2026-10-20 |
| CPP-P18 | P18 encadenado de aristas O(n²) con cKDTree | Abierto | Media | Sin cambios. | omnicad/nucleo/superficies.py y solidos_crear.py sin cKDTree | 2026-10-20 |
| CPP-P20 | P20 un solo BRepMesh por lote y caché de teselado entre visores | Abierto | Media | Sin empezar. | omnicad/ui/visor3d.py; omnicad/nucleo/geometria.py:499,642 | 2026-10-20 |
| CPP-C1 | C1 malla en bloque con id de cara (BRepMesh + extracción) | Abierto | Muy alta | No hay código C++; depende del spike de ABI. | grep C++ en el repo: sin carpeta cxx; teselar_por_cara en omnicad/nucleo/geometria.py | 2026-10-20 |
| CPP-C2 | C2 evaluación de superficies por lote (normales, curvatura, isocurvas) | Abierto | Muy alta | Sin empezar. | omnicad/nucleo/analisis.py _props_nodos | 2026-10-20 |
| CPP-P23 | P23 HLR exacto o rápido según tipo de superficie | Parcial | Media | Para formas libres corre exacto en subproceso con tope y cae a rápido; falta elegir el rápido para el resto por tipo. | omnicad/nucleo/dibujo.py:242,345-373 (PLAZO_HLR, es_forma_libre) | 2026-10-20 |
| CPP-C3 | C3 ejecutor sin GIL de hojas OCC independientes | Parcial | Alta | Solo existe el subproceso para autointersecciones y HLR exacto; no hay pool por cuerpos o vistas. | omnicad/nucleo/aislado.py | 2026-10-20 |
| CPP-C4 | C4 hojas cancelables (booleana, sección, revisión) | Parcial | Alta | Se cancela matando el subproceso solo en autointersecciones y HLR; no en booleanas ni sección. | omnicad/nucleo/aislado.py; tests/test_b16_cancelar.py | 2026-10-20 |
| CPP-F1 | Fase 1 proceso trabajador en Python (teselado por cuerpo, HLR por vista, botón Cancelar) | Parcial | Alta | Existe el subproceso para tareas que pueden no terminar; falta el pool paralelo y el botón en la interfaz. | omnicad/nucleo/aislado.py | 2026-10-20 |
| CPP-P21 | P21 sección del análisis usando el contorno que ya calcula | Sin verificar | Media | El log la deja pendiente; no pude confirmar en el código si seccion() ya evita el cálculo repetido. | omnicad/nucleo/analisis.py:1088 seccion; omnicad/ui/analisis_vista.py:60-70 (caché) | 2026-10-20 |

## Auditoría del 2026-10-14

Abierto 9 · Sin verificar 3. Especificación: [auditorias/](../auditorias/).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| AUD-1 | Sin medición de cobertura de tests (pytest-cov) | Abierto | Baja | Agregar pytest-cov como dependencia de desarrollo y medir sin umbral. | grep de pytest-cov/--cov en clon/requirements*.txt, pyproject.toml y .github: sin resultados | 2026-10-20 |
| AUD-2 | Sin lockfile (requirements pineado con == pero sin lock) | Abierto | Baja | Generar un lock (uv pip compile) y usarlo en CI e instaladores. | clon/ no tiene lockfile; clon/requirements.txt pineado con == | 2026-10-20 |
| AUD-13 | Variables OMNICAD_PUENTE_DIR y OMNICAD_PUENTE_FUSION_DIR redundantes | Abierto | Baja | Unificar en un solo override de carpeta_datos() con migración documentada. | io_archivos/puente_fusion.py:28 y integraciones/fusion/OmniCADPuente/OmniCADPuente.py:40 siguen usando OMNICAD_PUENTE_FUSION_DIR | 2026-10-20 |
| AUD-3 | Sin verificador de tipos (mypy o pyright) | Abierto | Media | Empezar mypy no estricto sobre nucleo/. | Sin mypy/pyright en clon/pyproject.toml, requirements*.txt ni .github; sin mypy.ini | 2026-10-20 |
| AUD-5 | Seis funciones con complejidad mayor a 20 | Abierto | Media | Reemplazar los if/elif por tablas tipo→función en las funciones señaladas. | Conteo propio por ast (aprox.): registro._convertir 40, svg._recorrer 46, solver.auto_restringir 39, entidades.resolver 29, boceto_desde_primitivas 33, fuentes._tabla_kern 24 | 2026-10-20 |
| AUD-7 | add_text/edit_text con 33 y 34 parámetros | Abierto | Media | Agrupar las opciones de texto en un dict de opciones documentado. | api/herramientas_vectores.py:185 (conteo por ast: add_text 33, edit_text 34) | 2026-10-20 |
| AUD-8 | Instalador de Windows sin firma de código | Abierto | Media | Comprar certificado y firmar el .exe; hoy solo se documenta el aviso de SmartScreen. | README.md:74 (aviso «Windows protegió su PC») | 2026-10-20 |
| AUD-11 | La CI corre ruff y pytest pero no la prueba de humo | Abierto | Media | Agregar paso de humo offscreen al job test, si corre estable en windows-latest. | .github/workflows/instaladores.yml: job test con escaneo de secretos, ruff y pytest; sin --prueba-humo | 2026-10-20 |
| AUD-4 | Archivos gigantes: 20 módulos pasan las 1000 líneas | Abierto | Alta | Partir de a poco al tocar cada uno (editor_boceto, solidos_crear, boceto, malla, ventana). | wc -l sobre clon/omnicad: 20 archivos >1000 líneas; editor_boceto.py 3800 líneas | 2026-10-20 |
| AUD-9 | Dependencias sin escaneo de CVE (pip-audit nunca corrido) | Sin verificar | Baja | Correr pip-audit una vez cuando el usuario autorice instalarlo. | Sin rastro de pip-audit en .github ni en PROJECT_LOG | 2026-10-20 |
| AUD-6 | Cuellos O(n²) posibles en máscara de aristas cóncavas y empalme | Sin verificar | Media | Medir con un modelo grande antes de tocar; la máscara ya usa caché por arista. | nucleo/analisis.py:860-883 leído; no se midió | 2026-10-20 |
| AUD-10 | El .exe publicado sin probar en una máquina limpia sin Python | Sin verificar | Media | Instalar la Release en una VM limpia y abrir un proyecto. | uar-loop-2026-10-14.md:28 lo deja «pendiente de usuario» | 2026-10-20 |

## Prueba de tortura

Parcial 1. Especificación: [informe_tortura_2026-10-17.md](../informe_tortura_2026-10-17.md).

| ID | Qué | Estado | Dificultad | Queda | Evidencia | Verificado |
|---|---|---|---|---|---|---|
| T-18 | Render y respuestas grandes lentas en la API | Parcial | Media | HLR en un proceso persistente: medido y diferido | tests/test_hallazgos_tortura.py::test_t18_get_scene_info_y_open_document_tienen_modo_resumido | 2026-10-20 |
