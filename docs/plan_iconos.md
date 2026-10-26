# Plan de íconos (2026-10-26)

Origen: el usuario armó un dron con el Asistente IA (73 pasos, 31 cuerpos) y en el timeline casi todos los pasos
se veían iguales. Este plan lleva los íconos de toda la interfaz a: **se distinguen de un vistazo, se ven bien,
combinan con el tema y no mienten**. El estado de cada fase vive en `docs/seguimiento/mejoras.md` (filas ICO-n).

## Qué se midió (2026-10-26, con un script sobre el código real)

| Hallazgo | Número | Dónde |
|---|---|---|
| Tipos de paso registrados | 101 | `timeline/operaciones.py` › `TIPOS_OPERACION` |
| Pasos que caen al ícono genérico «caja» en el timeline | **90 de 101** | `ui/panel_timeline.py:27-34` (`ICONO_TIPO` tiene solo 10 entradas; `icono_operacion` cae a `"caja"`) |
| De esos 90, ya tienen ícono propio en su comando de la cinta | 83 | `ui/comandos/*.py` (`ICONO`): arreglo barato, solo falta conectarlos |
| Tipos de paso sin comando que los cree (sin ícono propio asegurado) | 7 | `operacion_base`, `calibracion_holguras`, `insertar_diseno`, `grafo`, `importar_iges`, `insertar_malla`, `borrar_caras` |
| Pares de comandos que comparten ícono | 8 | plegar/replegar, patron_plano/exportar_dxf_chapa, cortar_plano/seccion_malla, invertir_normal(2), desfase_cara/desfase, empalme_3d/sup_empalme, alinear/apoyar, extruir/extruir_cara |
| Extrusión nuevo / unir / cortar / intersecar | 1 solo ícono | `op.p["operacion"]` no se refleja |
| Dibujos que ningún comando ni el mapa del timeline usa | 124 de 266 | 112 los usa la interfaz por nombre; 12 no tenían ninguna referencia (6 eran ítems grisados de la cinta sin `ico=`): F3 los conectó, quedan 0 (`scripts/hoja_iconos.py --sin-uso`) |
| Tamaños en pantalla | cinta 28-30 px · timeline 24 px · navegador 16 px | los dibujos son vectoriales en grilla 32×32 (`ui/iconos.py`, `ui/iconos_extra.py`, 3 386 líneas) |

Conclusión: **la biblioteca de íconos no es el problema** (a 40 px casi todos se distinguen). El problema es que
el timeline no la usa, que no muestra qué hizo el paso (nuevo/unir/cortar) y que a 24 px las siluetas azules
isométricas se parecen. Primero se conecta lo que ya existe; después se mejora el sistema.

## Decisiones tomadas

- **Sin imágenes de IA (ni FP navegador) para los íconos.** A 16-24 px un raster generado sale borroso, distinto
  entre sí, sin transparencia limpia y no se recolorea con el tema. Los íconos siguen siendo vectores dibujados
  con QPainter (ya hay 266, sin dependencias nuevas). Lo que sí se genera por script es una **hoja de contacto**
  antes/después (`evidencias/capturas/`) para mirar los cambios de verdad.
- **Una sola fuente de verdad**: el ícono de un paso sale del comando que lo crea (`CLASE_OP.TIPO → Comando.ICONO`);
  `ICONO_TIPO` queda solo para excepciones.
- La distinción de estado no puede depender solo del color (daltonismo): lleva forma (insignia).
- Los íconos no tienen herramienta MCP/CLI: no le sirven a un agente. Se anota en `docs/brechas_mcp.md` con esa razón.

## Fases

| Fase | Qué | Listo cuando | Modelo |
|---|---|---|---|
| **F0 · Red de seguridad** | Script `scripts/hoja_iconos.py` (contacto a 16/24/32 px, tema claro y oscuro) y `tests/test_iconos_unicos.py`: (1) todo tipo de paso resuelve a un dibujo que existe y no es «caja» salvo las primitivas; (2) dos tipos no comparten ícono sin estar en una lista de excepciones con su motivo; (3) a 24 px ningún par de íconos queda por debajo de una distancia mínima (hash perceptual). | El test **falla hoy** (90 genéricos) y la hoja «antes» queda guardada. | Sonnet 5 medio |
| **F1 · Timeline completo** | Derivar el mapa tipo→ícono de los comandos. Para los 7 sin comando, dibujar o asignar ícono. **Insignia de operación** abajo a la derecha (12 px): nuevo `+` verde · unir `∪` azul · cortar `−` rojo · intersecar `∩` naranja, leída de `op.p["operacion"]`. **Insignia de estado**: `!` en aviso y error (hoy solo fondo de color), suprimido ya sale gris. | Los 101 tipos con ícono propio; el dron de la captura se lee paso por paso sin tooltip; F0 en verde. | Sonnet 5 medio |
| **F2 · Gramática visual** | Escribir las reglas (abajo) y un test que las compruebe: grilla 32, margen de 2, trazo de 0,9 a 1,3, paleta por familia, insignias en una sola esquina. Corregir los dibujos que no las cumplan. | `tests/test_iconos_gramatica.py` verde; hoja «después» revisada a ojo contra «antes». | Opus 5 alto (decisiones de diseño) |
| **F3 · Repetidos y huérfanos** | Los 8 pares: dar un dibujo propio o una variante con insignia (p. ej. `desfase_cara` vs `desfase`, `sup_empalme` con insignia de superficie). Clasificar los 124 sin uso: interfaz (se quedan), variantes futuras o muertos (se borran). | Ningún par compartido sin motivo; 0 dibujos muertos. | Sonnet 5 medio |
| **F4 · Resto de la interfaz** | Navegador: íconos de 16 px re-dibujados a mano (hoy es el de 32 reducido) + insignia de estado. Menús contextuales del navegador con íconos (P-23e3). Título de cada diálogo de comando con su ícono. Asistente IA: ícono por herramienta en el chat. Barra del visor y pestañas de la cinta. **Íconos que cambian con el tema sin reiniciar** (P-9g): hoy `iconos_tema.py` recolorea píxeles una sola vez al arrancar; pasar a una paleta por tema y vaciar la caché al cambiar. | Cambiar de tema con la app abierta repinta todos los íconos; cada superficie revisada con captura a 100 % y 150 %. | Sonnet 5 medio |
| **F5 · Prueba como usuario** | Con `scripts/prueba_ui/`: capturas de la cinta, el timeline y el navegador en 1920×1080, 1024×640 y 800×520, tema claro y oscuro, con el dron como documento. Prueba de identificación: 20 pasos del dron sin tooltip, comparar contra la lista real. Comparar con el timeline de Fusion (`docs/fusion_docs/`, carpeta `fusion-designs`). Opcional: modo «ícono grande» (24 → 32 px) para la tira del timeline. | ≥ 18 de 20 pasos identificados; se mira cada captura y se dice qué se parece y qué no. | Sonnet 5 medio |

## Gramática (fijada en F2; lo medible lo comprueba `tests/test_iconos_gramatica.py`)

- **Un verbo = una silueta.** Extruir = caja + flecha; revolución = banda curva; empalme = esquina redondeada; chaflán = corte plano
  con marcas de distancia; agujero = cilindro hueco. Medido: dos íconos de comandos o pasos no pueden quedar a menos de **0,04** de
  distancia de color a 24 px (`test_iconos_unicos.UMBRAL`; hoy el par más cercano está en 0,046) ni compartir dibujo sin motivo escrito.
- **Color por familia** (lo que ya usaba la cinta; se midió el tono dominante de cada ícono): sólido, modificar, chapa y plástico en
  **azul** · superficie **naranja/ámbar** · malla **verde azulado** con triangulación · forma (T-Splines) violeta · planos de construcción
  naranja translúcido, ejes naranja oscuro, puntos amarillos · boceto gris con `+` verde · inspección y ensamblar multicolor.
  El color dice la familia; la forma dice el comando. Las excepciones están en `EXCEPCIONES_COLOR` con su motivo.
- **Margen de 2 unidades** en la grilla 32×32: `iconos.pixmap` achica solo cualquier dibujo que se pegue al borde (`_escala_de_margen`,
  se mide una vez por nombre); un dibujo nuevo no necesita cuidarlo, y el test confirma que ninguno queda fuera (salvo `marcador`).
- **Insignias** (`ui/insignias.py`): un disco en la esquina inferior derecha, siempre la misma, con un símbolo que no depende del color:
  operación `+` verde / `∪` azul / `−` rojo / `∩` naranja, estado `!` en triángulo ámbar (aviso) o disco rojo (error). El estado manda
  sobre la operación. Los íconos viejos pueden ocupar esa zona (los sólidos la llenan): la insignia se dibuja encima con borde blanco. Los dibujos nuevos
  para pasos (sin comando y variantes) la dejan libre (`test_iconos_extra.py::test_pasos_reservan_margen_y_esquina`).
- **Legibilidad a 24 px**: lo que no se lee a 24 px se quita (detalles de 1 px, degradados finos); trazos de contorno de 0,9 a 1,3.
- **Tema**: F4 (íconos con paleta por tema, sin reiniciar).

## Verificación

- `ruff check .` limpio; `pytest tests/test_iconos_unicos.py tests/test_iconos_gramatica.py tests/test_iconos_extra.py`
  con `scripts/turno.py`; prueba de humo (se toca la UI).
- Hoja de contacto antes/después y capturas de F5 en `evidencias/` (fuera de git).
- Cada fase cierra con la fila ICO-n borrada de `docs/seguimiento/mejoras.md` y su entrada en `PROJECT_LOG.md`.

## Orden recomendado

F0 → F1 (resuelve la queja del dron en una sesión) → F3 → F2 → F4 → F5. F2 va después de F1 para que las reglas
se escriban mirando los íconos ya conectados, no a ciegas.

## Estado (2026-10-26)

- **F0 a F5 hechas** (ICO-1 a ICO-6 cerradas; ya no quedan filas en `docs/seguimiento/mejoras.md`): hoja de contacto y tests (`scripts/hoja_iconos.py`, `test_iconos_unicos.py`, `test_iconos_gramatica.py`,
  `test_insignias.py`), timeline con el ícono del comando que crea cada paso, insignias de operación y de estado, 5 dibujos nuevos para pasos
  sin comando, 8 variantes para los pares que compartían dibujo, 4 pares casi idénticos rehechos y los 12 dibujos sin uso conectados.
- Orden real: F0 → F1 → F3 → F2 (la gramática se midió sobre los íconos ya conectados). Decisión: el color de CONSTRUCCIÓN es el que ya tenía la cinta
  (planos naranja translúcido), no el «gris con eje» del primer borrador.
- F4: los íconos son `iconos.IconoVivo` (un `QIconEngine`): se dibujan al tamaño exacto que pide cada widget (también a 150 %) y con el tema de ese
  momento; `iconos_tema` vacía la caché cuando cambia el tema y la ventana repinta (el timeline reconstruye sus pasos apagados), así que cambiar de
  tema con la app abierta recolorea todo sin reiniciar (P-9g; ya no hay aviso de reinicio en Preferencias). El navegador dibuja sus filas a 16 px
  reales con insignia de estado (aviso/error del paso que creó el cuerpo o boceto); los menús contextuales del navegador (P-23e3), las líneas de
  herramienta del chat del Asistente y las ventanas de diálogo llevan ícono. Decisiones: la cinta no lleva íconos en sus pestañas ni en los títulos
  de grupo (como Fusion: solo texto); el panel de comando ya tenía el ícono en su cabecera.
- F5 (2026-10-26, `scripts/prueba_ui/iconos.py`, ventana real con el dron de 73 pasos): capturas de la ventana, el timeline, el navegador y la cinta en 1920×1080,
  1024×640 y 800×520 (la ventana mide 821 px de ancho como mínimo) con tema oscuro y claro, y el cambio de tema en vivo: 22 comprobaciones, 0 con ✗, ninguna excepción.
  Prueba de identificación sin tooltip, 20 pasos al azar (semilla 7): **20 de 20** (tipo y operación). Límites honestos: quien miró fue Claude, no una persona nueva;
  conocía los 13 tipos de paso del documento; la muestra tocó 7 de los 13. Contra Fusion (`fusion-designs › Use the Timeline`): igual en lo central (cada paso lleva el ícono
  de su comando, lo suprimido se ve atenuado, los avisos y errores se marcan); OmniCAD agrega la insignia de operación. Fusion tiene grupos plegables y OmniCAD no (no es de este plan).
