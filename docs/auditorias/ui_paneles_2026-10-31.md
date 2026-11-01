# Paneles de herramienta: sistema común y matriz de cobertura (2026-10-31)

Pedido de Gerardo (dos videos del 2026-10-31, comparados con la versión mostrada de SolidCraft): controles mal distribuidos,
encabezado que no cambia al cambiar de modo (Patrón rectangular → circular), selecciones que solo dicen «1 seleccionado»,
paneles extensos, texto cortado a la derecha cuando aparece la barra, ayuda larga siempre visible. Esta página es la
**matriz de cobertura**: qué se revisó, qué se encontró, qué se hizo y cómo se comprobó. El estado de lo que sigue pendiente
vive solo en `docs/seguimiento/` (filas `UI-1` a `UI-n` de `mejoras.md`).

## 1. Qué se vio en los videos y qué hay en el código

| Observación (video) | Causa en el código | Tratamiento |
|---|---|---|
| El panel recorta lo de la derecha (combos, casillas, el borde de los campos) cuando aparece la barra | `PanelComando`: `ScrollBarAlwaysOff` en horizontal y una columna de campos de 170 px mínimos; el ancho lo decidía el contenido | Ancho fijo por tipo de formulario (`ANCHOS`), columna de etiquetas fija, combos con `AdjustToMinimumContentsLength`, barra horizontal solo si un widget propio no entra (y el inventario lo cuenta como falla) |
| El título sigue «PATRÓN RECTANGULAR» al elegir Circular | `titulo` era una etiqueta armada una vez con `comando.TITULO` | `Comando.TITULOS_MODO` + `PanelComando._actualizar_titulo`: título e ícono siguen al modo; «EDITAR …» al reabrir un paso |
| «1 seleccionado», sin saber qué | `_FilaSeleccion` solo contaba | `formulario.describir_ref` / `describir_seleccion`: «Cara plana +Z · Caja1», «3 aristas · Caja1», tooltip con el detalle, menú ▾ para quitar de a uno, marca «preelegida», fila vacía dice «Elegir perfil o cara plana» |
| 14–40 filas del mismo peso, todas visibles | no había jerarquía | `Campo.avanzado` (sección plegable «Más opciones» con resumen de lo activo), `Campo.grupo` (subtítulos), `Campo.etiqueta_si` (etiqueta por modo: «Extensión total» / «Separación entre instancias») |
| Texto de ayuda y teclas siempre visibles | pie «Enter: aceptar · Esc: cancelar» en todos; ayudas largas dentro del panel | el pie solo aparece si el comando tiene teclas de opción; Enter/Esc van en el tooltip de los botones; `?` en la cabecera muestra `AYUDA` |
| Mensajes que saltan y todos del mismo color | un solo estilo, panel que crece al aparecer | línea de estado reservada, 5 tipos con símbolo + color: instrucción ➜, inválido ✖, advertencia ⚠, calculando ⏳, error ✖ |
| Enter acepta aunque el foco esté en un desplegable, una tabla o «Cancelar» | `keyPressEvent` aceptaba siempre | `PanelComando._enter_es_del_control` |
| El campo de selección activo y el visor siguen apuntando a un campo que ya no se ve (cambio de modo) | `_actualizar_visibles` no revisaba la selección | `_revisar_selecciones_visibles`: la selección activa pasa al siguiente campo visible que falta y el resalte solo muestra lo visible |

**SolidCraft, lo que se tomó y lo que no.** De los videos: encabezado = nombre de la operación que cambia con «Type»; «Type»
siempre primero; una fila por parámetro con etiqueta a la izquierda; Cancel/OK abajo siempre a la vista; ancho constante.
No se copió su apariencia (OmniCAD conserva sus temas y su identidad) ni su código: SolidCraft es una aplicación en Rust
(`github.com/tangency-labs/solidcraft`, con cambios varias veces por día) y lo que se tomó es el comportamiento que muestran los
videos, que es una versión concreta y no necesariamente la actual del repositorio. No se leyó su código de interfaz.

## 2. Sistema común (dónde vive)

| Pieza | Archivo | Qué hace |
|---|---|---|
| `Campo(grupo, avanzado, etiqueta_si)` | `ui/comando.py` | jerarquía de campos |
| `Comando.TITULOS_MODO`, `ANCHO_PANEL`, `AYUDA`, `titulo_icono()` | `ui/comando.py` | cabecera por modo, ancho, ayuda del botón `?` |
| `PanelComando` | `ui/comando.py` | cabecera dinámica, ancho fijo, sección plegable, rótulos de grupo, línea de estado tipada, Enter seguro, Tab empieza en los campos |
| `formulario.Seccion`, `describir_*`, `texto_filtros`, `ANCHOS`, `TIPOS_MENSAJE` | `ui/formulario.py` | piezas sin Qt-lógica compartidas |
| `#grupo_cmd`, `#seccion_cmd`, `#resumen_seccion` | `ui/temas.py` | estilo (usa los tokens del tema, no colores propios) |
| `tests/test_formulario_paneles.py` | tests | 24 pruebas del sistema común |
| `scripts/prueba_ui/paneles_inventario.py`, `dialogos_inventario.py` | pieza de ventana | abre TODOS los comandos y los diálogos sueltos en la ventana real, mide y captura |

Reglas de jerarquía que se aplicaron a cada comando (las mismas se dieron a todos los que tocaron archivos):
1. **Orden**: modo/tipo → objetos → parámetros principales → opciones.
2. **Avanzado** solo lo opcional, poco frecuente y con valor por defecto sensato; nunca una selección que define la operación, ni lo necesario para completarla; panel de ≤ 6 campos sin avanzados; como máximo ~40 % de los campos.
3. **Grupos** solo en paneles de ≥ 8 campos visibles con unidades claras (Dirección 1 / Dirección 2…).
4. **Etiquetas** semánticas y sin repetidas confundibles; lo que depende del modo, con `etiqueta_si`.
5. Un valor inválido dentro de «Más opciones» cerrada **abre la sección** (no queda escondido); plegar/desplegar, ver la ayuda o mover el panel **no recalculan** la vista previa (prueba: `test_la_seccion_mas_opciones_resume_lo_activo_y_plegar_no_recalcula`).
6. No se cambió ninguna clave, valor por defecto, `construir` ni `desde_op`: abrir y aceptar un paso sin tocarlo da la misma operación (cubierto por las 414 pruebas de consumidores del panel).

## 3. Matriz de cobertura: los 148 comandos del catálogo (`CATALOGO`)

Todos usan el componente `PanelComando`. «Antes» y «Después» son el tamaño del panel recién abierto en la ventana real a 1280×720 («barra» = el cuerpo necesita desplazarse; «recorta» = el contenido no entraba a lo ancho y se cortaba). Capturas: `evidencias/ui_paneles_2026-10-31/{antes,despues}/<clave>.png` y, lado a lado con el mismo tamaño de ventana, `comparativas/<clave>.png` (extruir, patrón rectangular, agujero, engranaje, multitransformación, SCU, barrido, reglas de chapa, unión, retícula volumétrica). «Tratamiento» es lo que anotó cada sesión que tocó el archivo (`sistema común` = solo lo que da el panel; ese comando no necesitó metadatos propios).

| Herramienta | Módulo | Antes (ancho×alto @720p) | Después | Problemas encontrados | Tratamiento | Verificación |
|---|---|---|---|---|---|---|
| `aspecto` | aspecto | 331×377 · barra · recorta | 462×377 · barra | panel simple | ancho = «ancho» (biblioteca con buscador y miniaturas) | abre y cabe en 1280×720 |
| `convertir_chapa` | chapa | 306×233 | 322×213 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `desgarro` | chapa | 252×212 | 322×207 | chocaba con las filas de selección | «Selección» → «Desgarro por» | abre y cabe en 1280×720 |
| `desplegar` | chapa | 360×209 | 322×205 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `dobladillo` | chapa | 250×291 | 362×281 | orden | tipo (modo) primero | abre y cabe en 1280×720 |
| `exportar_dxf_chapa` | chapa | 373×225 | 322×265 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `patron_plano` | chapa | 292×233 | 322×213 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `pestana` | chapa | 308×377 · barra · recorta | 362×377 · barra | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `pestana_contorno` | chapa | 282×349 | 362×377 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `plegar` | chapa | 303×312 | 362×297 | etiqueta de 32 caracteres | radio: «Radio de plegado» + ayuda | abre y cabe en 1280×720 |
| `reglas_chapa` | chapa | 358×377 · barra · recorta | 362×377 | 13 campos planos, etiquetas largas con «(vacío = sin cambio)» | avanzados: alivio_forma/ancho/profundidad, esquina_forma/tam (5/13); grupos «Nuevos valores», «Alivio de plegado», «Alivio de esquina»; etiquetas cortas (Espesor, Separación de desgarro, Volver a la regla) con ayuda «Vacío = sin cambio» | abre y cabe en 1280×720 |
| `replegar` | chapa | 292×182 | 322×162 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `unir_plegando` | chapa | 271×225 | 322×201 | etiqueta de 32 caracteres | radio: «Radio de plegado» + ayuda | abre y cabe en 1280×720 |
| `eje_arista` | construir | 232×179 | 322×159 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `eje_cilindro` | construir | 327×179 | 322×159 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `eje_dos_planos` | construir | 246×182 | 322×162 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `eje_dos_puntos` | construir | 247×182 | 322×162 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `eje_perpendicular` | construir | 253×182 | 322×162 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `plano_angulo` | construir | 241×212 | 322×192 | paneles de 1 a 3 campos, un comando por modo, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `plano_desfase` | construir | 250×212 | 322×192 | paneles de 1 a 3 campos, un comando por modo, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `plano_dos_aristas` | construir | 271×182 | 322×162 | paneles de 1 a 3 campos, un comando por modo, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `plano_medio` | construir | 241×182 | 322×162 | paneles de 1 a 3 campos, un comando por modo, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `plano_perpendicular` | construir | 267×241 | 322×221 | paneles de 1 a 3 campos, un comando por modo, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `plano_ruta` | construir | 285×212 | 322×192 | paneles de 1 a 3 campos, un comando por modo, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `plano_tangente` | construir | 303×241 | 322×221 | paneles de 1 a 3 campos, un comando por modo, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `plano_tres_puntos` | construir | 273×211 | 322×191 | paneles de 1 a 3 campos, un comando por modo, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `punto_arista_plano` | construir | 232×182 | 322×162 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `punto_centro` | construir | 378×179 | 322×159 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `punto_dos_aristas` | construir | 272×182 | 322×162 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `punto_ruta` | construir | 285×212 | 322×192 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `punto_tres_planos` | construir | 273×211 | 322×191 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `punto_vertice` | construir | 237×179 | 322×159 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `scu` | construir | 347×377 · barra | 362×377 · barra | 9 campos planos; «Eje X» (selección) y «Ángulo X» (giro) se confundían | grupos «Origen y ejes» / «Desfase» / «Giro»; avanzados rx, ry, rz (3 de 9); etiquetas «Desfase en X/Y/Z», «Giro en X/Y/Z» | abre y cabe en 1280×720 |
| `agujero` | crear | 303×377 · barra · recorta | 362×377 · barra | 90 campos con «Tipo» repetido (3 confundibles), diámetro y profundidad lejos de su modo, afinado a la vista | reordenado en 3 grupos (Ubicación / Forma / Profundidad) + Cuerpos; avanzados: desfase del límite, punta y su ángulo, holgura 3D, dirección de la rosca; «Tipo de rosca» → «Rosca», familia «Tipo» → «Norma de rosca», «Desfase» → «Desfase del límite», Info «Rosca» → «Detalle de rosca» | abre y cabe en 1280×720 |
| `barrido` | crear | 312×377 · barra · recorta | 362×377 | 2 campos opcionales a la vista; etiqueta larga; «Distancia» sin explicar | avanzados: conicidad, torsión; «Tipo» → «Tipo de barrido»; «Eje de la orientación alineada» → «Eje de alineación»; ayuda en «Distancia» (0 a 1) | abre y cabe en 1280×720 |
| `bobina` | crear | 318×377 · barra · recorta | 362×377 · barra | 4 opciones de afinado a la vista; «Ángulo» sin significado | «Tipo de bobina» primero; grupos Ubicación / Hélice / Sección / Resultado; avanzados: ángulo (ahora «Ángulo de conicidad», es el taper de Fusion), posición de la sección, sentido horario, giro | abre y cabe en 1280×720 |
| `cuerpo_envolvente` | crear | 339×320 | 362×340 | 3 opciones de ensamblaje a la vista | avanzados: componente nuevo, grupo rígido, origen (→ «Origen del componente»); «Paso del SCU (id)» → «SCU (id del paso)» | abre y cabe en 1280×720 |
| `labio` | crear | 302×320 | 362×307 | cabecera fija para dos operaciones | «Tipo» primero; `TITULOS_MODO` (Labio / Ranura); avanzado: dirección de tirado; «Invertir» antes | abre y cabe en 1280×720 |
| `nervio` | crear | 325×377 · barra · recorta | 362×336 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `patron_circular_3d` | crear | 413×377 · barra · recorta | 362×377 · barra | el título seguía «PATRÓN RECTANGULAR» al elegir otro tipo; «Cantidad 1», «Distancia 1»… sin decir qué miden; 39 campos del mismo peso | diálogo único: «Tipo de patrón» primero; cabecera e ícono siguen al modo (Rectangular / Circular / En trayectoria / En puntos); grupos «Dirección 1» y «Dirección 2»; etiquetas por modo («Extensión total» / «Separación entre instancias», «Ángulo total» / «Ángulo entre instancias»); avanzados: copias suprimidas, elegir copias en la vista, copias ligeras, posición inicial y giro de la ruta | abre y cabe en 1280×720 |
| `patron_rectangular_3d` | crear | 413×377 · barra · recorta | 362×377 · barra | el título seguía «PATRÓN RECTANGULAR» al elegir otro tipo; «Cantidad 1», «Distancia 1»… sin decir qué miden; 39 campos del mismo peso | diálogo único: «Tipo de patrón» primero; cabecera e ícono siguen al modo (Rectangular / Circular / En trayectoria / En puntos); grupos «Dirección 1» y «Dirección 2»; etiquetas por modo («Extensión total» / «Separación entre instancias», «Ángulo total» / «Ángulo entre instancias»); avanzados: copias suprimidas, elegir copias en la vista, copias ligeras, posición inicial y giro de la ruta | abre y cabe en 1280×720 |
| `patron_ruta` | crear | 413×377 · barra · recorta | 362×377 · barra | el título seguía «PATRÓN RECTANGULAR» al elegir otro tipo; «Cantidad 1», «Distancia 1»… sin decir qué miden; 39 campos del mismo peso | diálogo único: «Tipo de patrón» primero; cabecera e ícono siguen al modo (Rectangular / Circular / En trayectoria / En puntos); grupos «Dirección 1» y «Dirección 2»; etiquetas por modo («Extensión total» / «Separación entre instancias», «Ángulo total» / «Ángulo entre instancias»); avanzados: copias suprimidas, elegir copias en la vista, copias ligeras, posición inicial y giro de la ruta | abre y cabe en 1280×720 |
| `red` | crear | 319×377 · barra · recorta | 362×336 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `relleno_contorno` | crear | 314×262 | 322×247 | etiqueta con texto de formato; 5 campos: sin avanzados | «Celdas a rellenar (n.º)» → «Celdas a rellenar» + ayuda; Info «Celdas» → «Celdas disponibles» | abre y cabe en 1280×720 |
| `repujado` | crear | 306×377 · barra · recorta | 362×323 | tipo detrás de las selecciones; 4 opciones de afinado a la vista; «Distancia» para un desfase | «Tipo de repujado» primero; avanzados: cadena tangente, desfases H/V, giro; «Distancia horizontal/vertical» → «Desfase horizontal/vertical» | abre y cabe en 1280×720 |
| `rosca` | crear | 348×377 · barra · recorta | 362×377 · barra | opciones de afinado mezcladas con lo principal; «Tipo» ambiguo | grupos Rosca / Longitud; Info junto a la norma; avanzados: desfase de inicio, holgura 3D, dirección, recordar tamaño; «Desfase» → «Desfase de inicio»; familia «Tipo» → «Norma de rosca» | abre y cabe en 1280×720 |
| `saliente` | crear | 367×320 | 322×300 | etiqueta larga; 6 campos: sin avanzados | «Altura (vacío = hasta el cuerpo)» → «Altura (vacío = auto)» + ayuda | abre y cabe en 1280×720 |
| `simetria_3d` | crear | 296×262 | 362×267 | 3 campos propios + `campos_objeto` (tratado por el coordinador) | sin cambios | abre y cabe en 1280×720 |
| `solevacion` | crear | 567×377 · barra · recorta | 362×377 · barra | 18 campos sin estructura, etiquetas de 30+ caracteres, texto de formato en la etiqueta | grupos Guía / Forma / Primer perfil / Último perfil / Resultado; avanzados: perfiles intermedios, fusionar tangentes; etiquetas «Condición/Ángulo/Cara tangente/Peso inicial/final»; «Perfiles intermedios (n.º:ángulo:peso;…)» | abre y cabe en 1280×720 |
| `tuberia` | crear | 316×370 | 362×377 | dos campos con la misma etiqueta «Distancia»; fracciones 0–1 por defecto a la vista | grupos Sección / Resultado; avanzados: distancia inicial y final (antes dos «Distancia» iguales); sección y tamaño antes que las distancias | abre y cabe en 1280×720 |
| `volumen_fluido` | crear | 384×262 | 322×252 | modo al medio; etiqueta larga; 6 campos: sin avanzados | «Tipo de volumen» primero; «Superficies que tapan las aberturas» → «Tapas de aberturas» (+ ayuda) | abre y cabe en 1280×720 |
| `insertar_derivacion` | derivacion | 388×377 · barra · recorta | 462×377 · barra | panel simple con listas apretadas | ancho = «ancho» (tres listas) | abre y cabe en 1280×720 |
| `eje_escalonado` | engranaje | 335×377 · barra · recorta | 362×377 · barra | hasta 53 campos con el prefijo «Tramo N:» repetido en cada etiqueta | grupo Ubicación, un grupo «Tramo N» por tramo (etiquetas sin prefijo: Diámetro, Largo, Remate inicial/final, Medida inicial/final), grupo Resultado (operación y objetos). Sin avanzados (superaría el 40 %) | abre y cabe en 1280×720 |
| `engranaje` | engranaje | 370×377 · barra · recorta | 362×377 · barra | 24 campos sin jerarquía, etiquetas de 30 caracteres con unidades dentro | 7 avanzados (ángulo de presión, desplazamiento x, holgura, juego, giro, desplazamiento 2.º, dirección 2.º); grupos Ubicación / Dimensiones / Par; etiquetas acortadas (Desplazamiento (x), Holgura de fondo, Agujero central, Alto hasta primitivo, «del 2.º», Crear unión y vínculo); cabecera por modo (engranaje / cremallera / rueda de cadena); ayudas con las unidades | abre y cabe en 1280×720 |
| `accionar_uniones` | ensamblar | 250×191 | 322×191 | ≤ 6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `fijar_componente` | ensamblar | 365×159 | 322×159 | etiqueta larga | etiqueta «Componente» + ayuda | abre y cabe en 1280×720 |
| `grupo_rigido` | ensamblar | 438×179 | 322×171 | etiqueta de 40 caracteres | etiqueta «Componentes» + ayuda | abre y cabe en 1280×720 |
| `nuevo_componente` | ensamblar | 246×209 | 322×189 | ≤ 6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `origen_union` | ensamblar | 284×328 | 322×308 | ≤ 6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `union` | ensamblar | 318×377 · barra · recorta | 362×374 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `union_construida` | ensamblar | 374×270 | 362×285 | ancho variable, recorte lateral con barra, cabecera fija, selección «1 seleccionado» | sistema común | abre y cabe en 1280×720 |
| `vinculo_movimiento` | ensamblar | 349×242 | 322×242 | etiqueta de 28 caracteres | «Relación 2 / 1» + ayuda | abre y cabe en 1280×720 |
| `fijacion` | fijacion | 474×361 · barra · recorta | 362×377 · barra | 10-11 campos con opciones raras mezcladas | avanzados: rosca, voltear, material; grupos Ubicación / Fijación; Propiedades antes de «Más opciones» | abre y cabe en 1280×720 |
| `calcomania` | insertar | 358×377 · barra · recorta | 362×377 · barra | 13 campos sin orden | igual que lienzo (grupos Imagen / Tamaño / Posición; avanzados: escala, volteos) | abre y cabe en 1280×720 |
| `insertar_dxf` | insertar | 296×370 | 362×339 | 8 campos planos | volteos avanzados; «Plano o cara» | abre y cabe en 1280×720 |
| `insertar_svg` | insertar | 329×377 · barra · recorta | 362×339 | etiquetas largas con instrucciones | volteos, Capas y Colores avanzados (las dos últimas con ayuda; etiquetas sin «(coma)» ni formato) | abre y cabe en 1280×720 |
| `lienzo` | insertar | 358×377 · barra · recorta | 362×377 · barra | 12 campos, «Mantener relación de aspecto» largo | avanzados: factor de escala, volteos; grupos Imagen / Tamaño / Posición; «Mantener proporción» | abre y cabe en 1280×720 |
| `vectorizar_imagen` | insertar | 323×377 · barra · recorta | 362×377 · barra | 12 campos sin orden | avanzados: umbral, suavizado, volteos; grupos Imagen / Trazado / Posición; «Tinta clara», «Curvas suaves» con ayuda | abre y cabe en 1280×720 |
| `accesibilidad` | inspeccionar | 291×183 | 322×183 | 0 a 5 campos, sin opciones raras | sin cambios | abre y cabe en 1280×720 |
| `angulo_desmoldeo` | inspeccionar | 294×241 | 322×241 | 0 a 5 campos, sin opciones raras | sin cambios | abre y cabe en 1280×720 |
| `buscar_similares` | inspeccionar | 365×159 · barra · recorta | 322×162 · barra | 2 a 4 campos, resultados calculados | sin cambios | abre y cabe en 1280×720 |
| `cebra` | inspeccionar | 323×169 | 322×169 | 0 a 5 campos, sin opciones raras | sin cambios | abre y cabe en 1280×720 |
| `centro_masa` | inspeccionar | 285×159 · barra · recorta | 322×159 · barra | 2 a 4 campos, resultados calculados | sin cambios | abre y cabe en 1280×720 |
| `curvatura_peine` | inspeccionar | 273×198 | 322×198 | 0 a 5 campos, sin opciones raras | sin cambios | abre y cabe en 1280×720 |
| `interferencia` | inspeccionar | 335×175 | 322×191 | 2 a 4 campos, resultados calculados | sin cambios | abre y cabe en 1280×720 |
| `isocurva` | inspeccionar | 251×169 | 322×169 | 0 a 5 campos, sin opciones raras | sin cambios | abre y cabe en 1280×720 |
| `mapa_curvatura` | inspeccionar | 312×162 | 322×162 | 0 a 5 campos, sin opciones raras | sin cambios | abre y cabe en 1280×720 |
| `mapa_entorno` | inspeccionar | 270×159 | 322×159 | 0 a 5 campos, sin opciones raras | sin cambios | abre y cabe en 1280×720 |
| `medir` | inspeccionar | 284×204 | 322×204 | 2 a 4 campos, resultados calculados | sin cambios | abre y cabe en 1280×720 |
| `radio_minimo` | inspeccionar | 327×162 | 322×170 | 0 a 5 campos, sin opciones raras | sin cambios | abre y cabe en 1280×720 |
| `reconocer_funciones` | inspeccionar | 324×343 | 362×377 · barra | 12 campos en fila sin separar detección de acción | grupos «Qué reconocer» / «Rehacer» / «Resultado» | abre y cabe en 1280×720 |
| `seccion` | inspeccionar | 302×320 | 362×272 | color y rayado (cosmético) ocupaban la vista; dos «Color…» confundibles | «Caras/plano» -> «Plano de corte»; «Color» -> «Color propio»; cuerpos sube tras el plano; avanzados color_modo, color, rayado (3 de 8) | abre y cabe en 1280×720 |
| `combinar_mallas` | malla | 329×262 | 322×250 | orden y cabecera | operación primero; cabecera por modo (Unir/Cortar/Intersecar/Fusionar mallas) | abre y cabe en 1280×720 |
| `convertir_malla` | malla | 342×233 | 322×229 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `cortar_plano` | malla | 294×341 | 362×323 | orden, etiquetas vagas | tipo primero; angulo avanzado; «Distancia al plano», «Ángulo del plano»; ayuda en Rellenar | abre y cabe en 1280×720 |
| `escalar_malla` | malla | 294×270 | 322×250 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `grupos_caras` | malla | 294×212 | 322×192 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `invertir_normal_malla` | malla | 294×179 | 322×159 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `limpiar_malla` | malla | 383×346 | 362×299 | etiquetas largas | avanzados: distancia, area_minima, lados (3/9); etiquetas más cortas | abre y cabe en 1280×720 |
| `malla_teselar` | malla | 350×233 | 322×229 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `reducir_malla` | malla | 298×241 | 322×231 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `remallar` | malla | 320×254 | 322×234 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `reparar_malla` | malla | 301×212 | 322×192 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `separar_malla` | malla | 294×212 | 322×192 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `suavizar_malla` | malla | 294×248 | 322×228 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `vaciado_malla` | malla | 294×212 | 322×192 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `seccion_malla` | malla_seccion | 294×299 | 322×284 | etiquetas vagas | «Distancia al plano», «Ángulo del plano» | abre y cabe en 1280×720 |
| `alinear` | modificar | 262×312 | 322×292 | 6 campos claros | sin cambios | abre y cabe en 1280×720 |
| `apoyar` | modificar | 342×189 | 322×208 | 2 campos | sin cambios | abre y cabe en 1280×720 |
| `chaflan_3d` | modificar | 292×291 | 362×267 | opciones de afinado a la vista | avanzados: Cadena tangente, Esquina («Tipo de esquina»→«Esquina») | abre y cabe en 1280×720 |
| `combinar` | modificar | 329×262 | 322×250 | 4 campos | sin cambios | abre y cabe en 1280×720 |
| `desfase` | modificar | 317×233 · barra · recorta | 362×233 | 7 campos, ≤6 visibles; el Info «Qué hace» calcula según lo elegido | sin cambios | abre y cabe en 1280×720 |
| `desfase_cara` | modificar | 292×233 | 322×213 | 3 campos claros | sin cambios | abre y cabe en 1280×720 |
| `desmoldeo` | modificar | 387×349 | 362×374 | tres «Tipo…», «Dirección» ambigua, caras después de opciones de partición | «Tipo»→«Método», «Dirección»→«Sentido del ángulo», «Tipo de desmoldeo»→«Lados»; grupos «Línea de partición» y «Ángulo»; avanzados: Modo de ángulo, Invertir dirección (2/12); orden: método, referencias, partición, ángulos | abre y cabe en 1280×720 |
| `dividir_cara` | modificar | 374×262 | 322×255 | etiqueta larga | «Extender herramienta de división»→«Extender herramienta» (+ayuda) | abre y cabe en 1280×720 |
| `dividir_cuerpo` | modificar | 374×233 | 322×221 | plural con selección única, etiqueta larga | «Herramientas de división»→«Herramienta de división»; «Extender herramienta» (+ayuda) | abre y cabe en 1280×720 |
| `division_silueta` | modificar | 299×241 | 322×221 | 3 campos claros | sin cambios | abre y cabe en 1280×720 |
| `empalme_3d` | modificar | 316×377 · barra · recorta | 362×377 | 23 campos sueltos, radio detrás de continuidad, opciones raras mezcladas con lo principal, dos «Tipo…» | cabecera por modo (TITULOS_MODO: Empalme / Empalme de reglas / Redondeo completo); «Tipo»→«Modo», «Tipo de esquina»→«Esquina», «Radio sobre la segunda cara»→«Radio en la 2.ª cara», «Aristas del conjunto 2»→«Aristas 2»; grupo «Conjunto 2»; avanzados: Puntos intermedios, Continuidad, Cadena tangente, Esquina, Distancia de setback (5/23); orden: modo, referencias (reglas), tipo de radio, radio y derivados, conjunto 2, avanzados | abre y cabe en 1280×720 |
| `escala_3d` | modificar | 387×283 · barra · recorta | 362×294 | etiqueta larga/imprecisa | «Entidades»→«Cuerpos», «Bocetos (una curva elige el boceto)»→«Bocetos» (frase a ayuda) | abre y cabe en 1280×720 |
| `material_fisico` | modificar | 279×162 | 322×162 | 2 campos | sin cambios | abre y cabe en 1280×720 |
| `mover_copiar` | modificar | 310×377 · barra · recorta | 362×377 · barra | X/Y/Z sueltas, etiquetas largas | grupos Traslación / Rotación / Posición; avanzado: Copia ligera (1/23); «X/Y/Z»→«Posición X/Y/Z», «Bocetos (…)»→«Bocetos», «Copia ligera (comparte la geometría)»→«Copia ligera» (frase ya en ayuda) | abre y cabe en 1280×720 |
| `pulsar_tirar` | modificar | 288×212 | 322×192 | etiqueta doble | etiqueta_si: «Distancia» (caras) / «Radio» (aristas) / «Distancia / radio» (sin elegir) | abre y cabe en 1280×720 |
| `quitar` | modificar | 243×179 | 322×159 | 1 campo | sin cambios | abre y cabe en 1280×720 |
| `quitar_empalmes` | modificar | 278×212 | 322×192 | 2 campos | sin cambios | abre y cabe en 1280×720 |
| `reemplazar_cara` | modificar | 289×182 | 322×170 | plural con selección única | «Caras de destino»→«Cara o plano de destino» | abre y cabe en 1280×720 |
| `reticula_volumetrica` | modificar | 360×377 · barra · recorta | 362×377 · barra | 24 campos sin estructura, etiquetas largas con instrucciones | grupos Celda / Solidez / Desfase; avanzados: Mover-girar celdas (+6 campos) y Muestras por celda (8/24); «Cuerpo sólido o malla cerrada»→«Cuerpo a rellenar», «Barras (…)»→«Barras» (formato a ayuda), «Zona (…)»→«Zona» (ayuda), «Tamaño de celda»/«Tamaño en X» según no uniforme (etiqueta_si); orden por unidades | abre y cabe en 1280×720 |
| `suprimir` | modificar | 243×159 | 322×159 | 1 campo | sin cambios | abre y cabe en 1280×720 |
| `vaciado` | modificar | 292×291 | 322×276 | casilla entre selección y parámetros | orden: «Cadena tangente» al final | abre y cabe en 1280×720 |
| `multitransformar` | patrones | 413×377 · barra · recorta | 462×377 · barra | lista y editor en 41 campos sin jerarquía | `ANCHO_PANEL="ancho"` (lista + editor); «Tipo de la elegida»→«Tipo de transformación»; avanzados (los de cada patrón + copias ligeras); info de etapa más corta | abre y cabe en 1280×720 |
| `patron_puntos` | patrones | 413×377 · barra · recorta | 362×377 · barra | el título seguía «PATRÓN RECTANGULAR» al elegir otro tipo; «Cantidad 1», «Distancia 1»… sin decir qué miden; 39 campos del mismo peso | diálogo único: «Tipo de patrón» primero; cabecera e ícono siguen al modo (Rectangular / Circular / En trayectoria / En puntos); grupos «Dirección 1» y «Dirección 2»; etiquetas por modo («Extensión total» / «Separación entre instancias», «Ángulo total» / «Ángulo entre instancias»); avanzados: copias suprimidas, elegir copias en la vista, copias ligeras, posición inicial y giro de la ruta | abre y cabe en 1280×720 |
| `asignar_regla_plastico` | plastico | 291×192 | 322×192 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `consejos_diseno` | plastico | 325×225 | 322×225 | ≤6 campos, etiquetas claras | sin cambios | abre y cabe en 1280×720 |
| `patron_geometrico` | plastico | 356×377 · barra · recorta | 362×377 · barra | 22 campos planos, etiquetas largas | avanzados: orientación, alineaciones, desfases, perímetro (7/18 visibles); grupos Tamaño, Distribución, Dirección U/V, Perímetro; operación y objetivos antes de los avanzados; etiquetas «Tamaño en el centro/esquina», «Distancia entre objetos» | abre y cabe en 1280×720 |
| `reglas_plastico` | plastico | 333×249 | 322×257 | etiqueta fija | cabecera por modo (Crear/Borrar regla); «Nombre» → «Regla a borrar» al borrar | abre y cabe en 1280×720 |
| `caja` | primitivas | 275×377 · barra · recorta | 362×377 · barra | 9 campos visibles sin rótulos; «Posición» repetía «Posición X/Y/Z» | grupos «Medidas» y «Ubicación»; Info «Posición» -> «Centro» | abre y cabe en 1280×720 |
| `cilindro` | primitivas | 275×358 · barra · recorta | 362×377 · barra | idem (8 visibles) | igual que caja | abre y cabe en 1280×720 |
| `esfera` | primitivas | 275×329 | 362×334 | etiqueta confundible | solo Info «Posición» -> «Centro» (sin grupos: 7 visibles) | abre y cabe en 1280×720 |
| `toroide` | primitivas | 298×358 | 362×377 · barra | idem (9 visibles) | igual que caja | abre y cabe en 1280×720 |
| `reparar_cuerpo` | revision | 374×296 | 322×308 | 6 campos, Info calculado | sin cambios | abre y cabe en 1280×720 |
| `revisar_geometria` | revision | 388×217 · barra · recorta | 362×348 · barra | 9 campos, 3 numéricos de afinado siempre a la vista | grupos «Revisar» / «Informe» / «Reparar»; avanzados espesor, voladizo, filo (3 de 9; solo aparecen con la casilla de impresión) | abre y cabe en 1280×720 |
| `extruir` | solido | 312×377 · barra · recorta | 362×377 | 20 campos con dos «Desfase» y dos «Objeto» iguales; opciones raras mezcladas con lo principal | cabecera por tipo (Extruir / Extrusión delgada); avanzados: inicio, desfase e inicio por objeto, conicidad (lado 1 y 2); «Tipo de extensión»→«Extensión», «Desfase»→«Desfase de inicio» / «Desfase del límite», «Objeto»→«Objeto de inicio» / «Objeto límite» | abre y cabe en 1280×720 |
| `extruir_cara` | solido | 258×241 | 322×221 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `revolucion` | solido | 291×370 | 362×375 | «Tipo» suelto; «Ángulo 2» ambiguo; casilla rara en vista principal | «Tipo» -> «Extensión», «Objeto» -> «Objeto límite», «Ángulo»/«Ángulo 2» -> «Ángulo del lado 1/2» (etiqueta_si), «Proyectar eje» avanzado + ayuda | abre y cabe en 1280×720 |
| `coser` | superficie | 259×212 | 322×192 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `descoser` | superficie | 246×179 | 322×159 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `destrimar` | superficie | 305×212 | 322×192 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `engrosar` | superficie | 301×299 | 322×284 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `extender_sup` | superficie | 295×241 | 322×221 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `invertir_normal` | superficie | 259×179 | 322×159 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `parche` | superficie | 305×212 | 322×192 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `recortar_sup` | superficie | 324×182 | 322×162 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `reglada` | superficie | 250×270 | 322×255 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `sup_barrido` | superficie | 297×299 | 322×279 | «Distancia» era una fracción 0-1 | «Distancia» -> «Largo de la ruta» | abre y cabe en 1280×720 |
| `sup_desfase` | superficie | 308×241 | 322×221 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `sup_empalme` | superficie | 290×241 | 322×221 | etiqueta doble; cabecera fija | TITULOS_MODO (Empalme / Chaflán de superficie); «Radio / distancia» -> etiqueta_si «Radio» / «Distancia» | abre y cabe en 1280×720 |
| `sup_extruir` | superficie | 312×291 | 322×271 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `sup_revolucion` | superficie | 241×241 | 322×221 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |
| `sup_solevacion` | superficie | 326×225 | 322×205 | ≤ 6 campos, etiquetas claras, orden correcto | sin cambios | abre y cabe en 1280×720 |


## 4. Diálogos y paneles de herramienta que no salen del catálogo de comandos

Inventario con `scripts/prueba_ui/dialogos_inventario.py` (abre cada uno sobre la ventana real y mide contra una pantalla de 1280×720; capturas en `evidencias/ui_paneles_2026-10-31/{antes,despues}_dialogos/`).

| Diálogo / panel | Componente | Tamaño antes → después | Problema encontrado | Tratamiento | Verificación |
|---|---|---|---|---|---|
| Boceto · Patrón rectangular/circular · Escala / Mover | `panel_patron.PanelPatron` · `panel_transformar.PanelTransformar` | 340×428 → 360×428 | «Distancia 1/2» no decía qué mide; cabecera, ancho y mensajes armados a mano (UI-5) | etiqueta por modo; cabecera movible, ancho `ANCHOS["normal"]` e instrucción ➜ / error ✖ de `formulario.py` | `patrones_boceto`, `paneles_boceto` |
| Boceto · Simetría | `panel_simetria.PanelSimetria` | 258×159 → 320×159 | cabecera, ancho y mensajes armados a mano (UI-5) | cabecera movible, ancho `ANCHOS["simple"]` e instrucción ➜ / error ✖ de `formulario.py` | `simetria_boceto`, `paneles_boceto` |
| Boceto · Carácter (texto) | `modo_boceto.PanelCaracter` | 320×533 → 320×539 (345 ya mostrado) | cabecera propia sin mover; la primera medida salía 25 px angosta | misma cabecera movible (con el botón de plegar y sin ✕); `showEvent` lo reajusta; el cuerpo va en un `QScrollArea` (UI-8) y `AreaVisor.reubicar` le pasa el alto que deja el lienzo (`ajustar_alto`): en una ventana baja se achica y baja con la barra | `paneles_boceto` |
| Boceto · Autorrestringir | `dialogo_autorestringir` | 520×569 | alto con lista de resultados; entra y los botones se ven | sin cambios | inventario |
| Malla · Guardar | `guardar_malla` | 440×531 | entra | sin cambios | inventario |
| Dibujo · Vista base | `dibujo.DialogoVista` | 374×309 | entra | sin cambios | inventario |
| Animación · Acción / Publicar | `animacion.DialogoAccion` / `DialogoPublicar` | 247×316 · 376×287 | entran | sin cambios | inventario |
| Administrar · Roscas, Configuraciones, Lista de materiales, Scripts | `administrar.*` | 703×480 · 900×420 · 820×420 · 720×460 | tablas anchas con desplazamiento propio; entran | sin cambios | inventario |
| Diseño · Parámetros, Rejilla | `dialogos.*` | 760×420 · 307×162 | entran | sin cambios | inventario |
| Aspecto · **Editor de materiales** | `aspectos_ui.EditorMateriales` | **287×959 → 340×438** | **no entraba en una pantalla de 720 y no tenía barra: Aceptar/Cancelar quedaban fuera** | cuerpo en un `QScrollArea` y botones fijos; los grupos apagados (Translucidez, Emisividad, Relieve, Corte) se pliegan; alto máximo 85 % de la pantalla | `test_el_editor_de_materiales_cabe_en_pantalla_con_los_botones_siempre_a_la_vista` |
| Ajustes · Atajo | `mas_comando.DialogoAtajo` | 266×150 | entra | sin cambios | inventario |

Render (UI-1): `DialogoRenderizar` (y Capturar imagen) pasó a 460 px fijos, con las secciones Tamaño / Calidad / Salida y un aviso ⚠ si la carpeta de destino no existe o la imagen pasa de 16 megapíxeles; `DialogoLienzo` a 400 px con la nota en tenue; `PanelEscena` (360×561) y `PanelAspecto` (360×567) (`PanelFlotante`) usan la cabecera movible y 360 px, con el cuerpo en un `QScrollArea` (`PanelFlotante.ajustar_alto`): en una ventana de render baja se achican y bajan con la barra. La ruta del diálogo Renderizar mira el disco una vez por pausa de 300 ms al teclear, no en cada tecla. `DialogoLienzo` y `VisorImagen` no llevan mensajes tipados porque no tienen nada que avisar.

No inventariados (con motivo): `DialogoRecuperados` (sale solo al arrancar con archivos de recuperación); `DialogoPerdidas` (necesita un boceto con proyecciones perdidas); cinta, navegador, línea de tiempo, Asistente y Preferencias (navegación y ajustes, fuera de «herramientas y operaciones» según el pedido).

## 5. Verificación

| Qué | Cómo | Resultado |
|---|---|---|
| Los 148 comandos abren, no recortan a la derecha y entran en el lienzo | `paneles_inventario.py` en 1280×720, 1920×1080, 1024×640 y 800×520 (ventana real, minimizada) | 148/148 abren; desborde horizontal 37 → 0; ancho: 81 valores distintos → 3 (322, 362 y 462 px); entran en el lienzo en los 4 tamaños |
| Vertical: paneles que necesitan barra | mismo inventario | 1280×720: 38 → 29 · 1920×1080: 13 · 1024×640: 23 (51 antes de subir el panel) · 800×520: 45 (121 antes de subirlo); en las ventanas bajas el panel sube sobre el ViewCube y el cuerpo conserva ≥ 110 px: `test_en_ventana_baja_el_cuerpo_del_panel_conserva_varias_filas` |
| Todos los temas y la letra al 100/125/150 % | `paneles_temas.py` (5 temas × 3 tamaños: Extruir con valor inválido y «Más opciones» abierta, Patrón al cambiar de modo, Multitransformación; contraste de instrucción/inválido/advertencia ≥ 4,5 contra el panel) | 91 comprobaciones, 0 ✗ |
| Piezas de ventana (`todo.py --ventana minimizada`) | `cinta_completa`, `superficie`, `solido_crear`, `solido_modificar`, `asas`, `teclear`, `ventana_uso`, `ensamblar`, `patrones_solidos`, `patrones_boceto`, `seccion_color` + las 3 nuevas | 590 · 234 · 290 · 321 · 283 · 345 · 671 · 232 · 32 · 105 · 14 comprobaciones, 0 ✗ al final. Dos ajustes de las propias piezas (ver §7) |
| Prueba de humo (una vez, al final) | `OmniCAD.py --prueba-humo` | TODO OK (salida 0) |
| Sistema común | `tests/test_formulario_paneles.py` | 24 pruebas (títulos por modo, etiquetas por modo, resumen y plegado sin recalcular, selección legible, quitar de a uno, ancho fijo, mensajes tipados, Enter, grupos, campo activo, editor de materiales) |
| Nada se rompió en los consumidores del panel | 45 archivos de tests que abren comandos o tocan sus campos (`test_comandos*`, `test_manipuladores`, `test_previa_*`, `test_b48`, `test_b105`, `test_sol27_preajustes`, `test_formulario_paneles`, `test_seguimiento`, `test_claves_comandos`, `test_doc_agentes`…) con `-W error`, en una sola corrida | **1334 OK** (726 s) |

**Límites de esta verificación** (también en `prueba_nocturna_2026-10-31.md` §3): el escalado real de Windows (125 %/150 %) y los monitores no se probaron: se simuló con el tamaño de letra de la interfaz (125/150 %) y con ventanas de 1024×640 y 800×520 (= 1280×720 y 1024×640 al 125/150 %); el contraste se midió con los tokens del tema, no con capturas de pantalla reales de Windows; los paneles flotantes que se pueden mover (los de boceto) no se tocaron.

## 6. Excepciones justificadas

- **Paneles anclados** (resuelto en UI-3, 2026-10-31): los de comando se mueven por la cabecera (`CabeceraMovible`, la misma de la tarjeta del boceto), recuerdan dónde quedaron (`vista/posicion_panel_comando`, respecto del borde derecho y del de arriba) y nunca se salen de la vista ni quedan bajo la barra de navegación; doble clic en la cabecera los devuelve a su lugar. También los del boceto (Patrón, Escala/Mover, Simetría y Carácter) y los paneles flotantes de render (Escena, Aspecto), con la misma cabecera (`formulario.armar_cabecera`); su lugar vale mientras dura la sesión (no va a la preferencia). Los preajustes no les corresponden: Fusion solo los tiene en herramientas de sólido.
- **Presets** (resuelto en UI-4, 2026-10-31): ya no hay fila propia de 36 px; un botón «⋯» en la cabecera abre un menú con Valores de fábrica y los preajustes (tildado el elegido), Guardar los valores actuales como nuevo, Guardar, Renombrar, Eliminar y Establecer como predeterminado (`BotonPreajustes`).
- **Sin avanzados**: Eje escalonado y Unión (agentes lo dejaron anotado): sus campos por tramo / límites superan el 40 % y perderían su contexto fuera del grupo.
- **Selecciones opcionales en «Más opciones»** (resuelto en UI-7, 2026-10-31): `nervio.direccion_desmoldeo`, `labio.direccion` y otras siete (`parche.interior`, `sup_extruir.direccion`, las cuatro «propias» de Unión y `alinear.cuerpos`) salieron de la sección; `test_ninguna_seleccion_vive_en_mas_opciones` lo exige.
- **Combinar mallas**: la cabecera dice «Unir mallas» y la cinta «Combinar mallas» (el título viene del modo del diálogo; igualar la cinta es cosmético).

## 7. Regresiones y defectos detectados durante el trabajo (y resueltos)

| Qué | Dónde se vio | Resolución |
|---|---|---|
| El texto de ayuda de la dirección 2 derivada y la explicación de «puntos sueltos» los comprobaba una prueba por su texto | `test_patrones_solidos_ui` | se conservó «derivada» y la frase de los puntos sueltos (son información necesaria, no decoración) |
| Un rótulo de grupo se asociaba al último rótulo creado de cualquier sección: un campo avanzado con `grupo` colgaba del rótulo equivocado | revisión del agente de Insertar/Ensamblar | rótulo vigente por grilla; prueba `test_un_campo_avanzado_con_grupo_cuelga_de_su_propio_rotulo` |
| Un valor inválido dentro de «Más opciones» cerrada quedaba escondido | prueba propia | `_actualizar_visibles` abre la sección; la vista solo salta al campo si no se está tecleando en otro |
| La selección automática saltaba a un campo plegado que la persona no ve | revisión propia | `_a_la_vista`; `test_la_seleccion_no_salta_a_un_campo_escondido_en_mas_opciones` |
| Un título largo (SCU, Eje a través de cilindro, Punto en el centro) ensanchaba el panel a 351/371/402 px | inventario a 1280×720 | título elidido con el completo en el tooltip → solo 3 anchos |
| El Editor de materiales medía 959 px de alto, sin barra: los botones quedaban fuera de una pantalla de 720 | inventario de diálogos | `QScrollArea` + grupos plegables (ver §4) |
| En una ventana baja (800×520) el cuerpo del panel quedaba en ~40 px (121 de 148 con barra) | inventario a 800×520 | el panel sube sobre el ViewCube si debajo no hay 330 px: 121 → 45 con barra; `test_en_ventana_baja_el_cuerpo_del_panel_conserva_varias_filas` |
| `solido_modificar` tenía 3 ✗ que ya estaban en `main` (`40a5fcf`): usaba las claves viejas del patrón (`d1`, `n1` en la trayectoria; `angulo` sin elegir «Parcial») | piezas de ventana | la pieza usa `rn`/`rd` y `modo = parcial` (321/321) |
| `ventana_uso`: 30 ✗ de atajos con el código nuevo (con `main` daba 0). Tras abrir el primer panel la ventana activa pasaba a la de Dibujo (abierta antes) y los atajos iban a ella; no se pudo reproducir en una prueba corta ni aislar el cambio que lo dispara (se descartaron `NoFocus` de la cabecera, el menú ▾ y un `QLabel` temporal) | pieza `ventana_uso` | la pieza reactiva la ventana principal antes de cada atajo (671/671). **Sin explicar la causa**: queda en la lista de la noche correrla con `--ventana visible` |
| Enter sobre el botón «Cancelar» aceptaba el comando | revisión propia | `_enter_es_del_control` |
| «Largo de la ruta» en el barrido de superficie sugería mm y es una fracción de 0 a 1 | `ponytail-review` del agente | «Fracción de la ruta» |
