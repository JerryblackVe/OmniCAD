# Apariencia y materiales: rediseño del sistema (AG-9)

Pedido de Gerardo (2026-11-09): mejorar el sistema de color, apariencia, materiales y texturas. Antes de programar se
diseña la interfaz: «me gustaría saber cómo podemos hacer para diseñar primero la UI antes de implementar». No es
prioritario: va después de la auditoría de tiempos (AG-8), pero queda programado.

## Qué se busca

- Un panel único, «Apariencia y materiales», que reemplaza al diálogo actual de Aspecto: destino (qué se pinta),
  biblioteca (Biblioteca, Mis recursos, Favoritos, En uso) y propiedades editadas en el mismo panel.
- Colores con paletas, recientes, favoritos y dos goteros: uno de pantalla y otro que copia la apariencia del modelo.
- Un registro «En uso» que se deriva de las asignaciones del documento, sin una lista paralela.
- Material físico (masa, cálculos) separado de la apariencia (color, acabado, texturas).
- Texturas PBR con efecto real en el visor y el render, importación de mapas y colocación (proyecciones, escala en mm).
- El mismo sistema en Sólido, Plástico, Superficie, Malla, Chapa y Forma, y consumido por Renderizar, Animación y Dibujo.

## Referencias visuales

Siete imágenes de la propuesta, una por subcarpeta, en
`evidencias/propuesta_ui_apariencia_materiales_2026-11-09/` (fuera de git; galería en `GALERIA.html`):
`01_vista_general`, `02_colores_goteros_paletas`, `03_registro_en_uso`, `04_material_fisico`, `05_texturas_pbr`,
`06_mapeo_y_calcomanias` y `07_todas_las_areas`. Muestran la intención: los nombres, cantidades y valores son de
ejemplo.

## Fase 0: maqueta de la interfaz, antes de programar

1. Una maqueta navegable en PySide6, con los widgets, el tema y los tamaños reales de OmniCAD. Lleva datos de ejemplo y
   no se conecta al documento. Vive en `scripts/maquetas/apariencia_materiales.py` y se abre con
   `clon/.venv/Scripts/python.exe scripts/maquetas/apariencia_materiales.py`.
2. Cubre las siete pantallas de las imágenes. Pestañas, botones y desplegables cambian de vista al hacer clic.
3. Capturas en 1280x800, 1024x640 y 800x520, en `evidencias/maqueta_apariencia_<fecha>/`. Cada una se compara con su
   imagen: una línea por pantalla diciendo qué se parece y qué no.
4. Gerardo la usa y pide cambios. Se itera hasta que la apruebe.
5. La maqueta aprobada es la referencia obligatoria de las fases 1 a 6. No se programa ninguna pantalla que no
   esté en la maqueta aprobada.

## Reparto con otras auditorías

AG-9 es la dueña de Aspecto: biblioteca, asignación, edición y material físico. RENDERIZAR (AG-3) solo verifica que el
render consuma bien las asignaciones. MODIFICAR (AG-4) sigue salteando su sección 27 (Aspecto).

## Prompt para el agente

Guardado el 2026-11-09. Modelo sugerido: Claude Opus 5 con esfuerzo alto para la fase 0 y para la arquitectura. Las
partes mecánicas (formatos de importación, tests de persistencia) se pueden repartir con GPT-6.1 Sol en OpenCode.

```text
ARRIBA DE TODO, invocá con la herramienta Skill: `fable-method` y `ponytail` al empezar; seguí `plan-then-do`,
`tool-calling-guard`, `verify-before-commit` y `omnicad-test`; e invocá `ponytail-review` antes de cerrar cada fase,
pegando su salida REAL en el informe. Para la maqueta usá también `impeccable`.

Especificación: `docs/apariencia_materiales.md` (leelo entero). Repo `D:/PROGRAMA`, rama main; reglas en `CLAUDE.md`
y `AGENTS.md`. Un ítem por worktree (`bash scripts/worktree_item.sh crear <ID>`); no commitees en `D:/PROGRAMA`:
avisale al coordinador de fusiones.

FASE 0 (primero, obligatoria): la maqueta navegable de la interfaz, como dice la sección «Fase 0» del documento.
Entregá las capturas en los tres tamaños, la comparación con cada imagen de referencia y el comando para abrirla.
Pará y esperá la aprobación de Gerardo. Sin aprobación no se pasa a la fase 1.

Después de la aprobación, el pedido completo de Gerardo:

Quiero que implementes una actualización integral de la herramienta de color, apariencia, materiales y texturas de
OmniCAD.

OBJETIVO
Convertir la herramienta actual en un sistema intuitivo y unificado, llamado “Apariencia y materiales”, que permita:
- Seleccionar fácilmente qué cuerpos, caras o regiones se van a modificar.
- Elegir, editar y aplicar colores, acabados y texturas.
- Consultar dónde está aplicada cada apariencia.
- Guardar y reutilizar colores, materiales, paletas y favoritos.
- Trabajar de manera coherente en las distintas áreas del programa.

REFERENCIAS VISUALES
Las siete imágenes de la propuesta están en
D:\PROGRAMA\evidencias\propuesta_ui_apariencia_materiales_2026-11-09
(subcarpetas 01_vista_general, 02_colores_goteros_paletas, 03_registro_en_uso, 04_material_fisico, 05_texturas_pbr,
06_mapeo_y_calcomanias, 07_todas_las_areas). Muestran la intención de diseño y los flujos de trabajo. Adaptá su
composición a los componentes, temas y tamaños de ventana reales de OmniCAD (y a la maqueta aprobada). Los nombres de
ejemplo, cantidades de caras, valores físicos y geometrías son ilustrativos.

FORMA DE TRABAJO
1. Leé AGENTS.md, CLAUDE.md y las instrucciones aplicables del proyecto.
2. Revisá el código real y las dependencias antes de modificarlo.
3. Identificá qué funciones ya existen, cuáles están incompletas y cuáles faltan. Reutilizá la infraestructura existente.
4. Prepará un plan por fases pequeñas y ejecutalo, verificando cada fase.
5. Respetá las reglas de arquitectura, documentación, pruebas, permisos y trabajo simultáneo del proyecto.
Puntos de partida: clon/omnicad/ui/aspectos_ui.py, clon/omnicad/ui/comandos/aspecto.py,
clon/omnicad/timeline/aspectos_doc.py, clon/omnicad/nucleo/aspectos.py, clon/omnicad/api/herramientas_aspecto.py,
clon/omnicad/api/herramientas_material.py y los consumidores del visor, render, guardado e intercambio. Hay una base
existente de aspectos, favoritos, bibliotecas personales y asignaciones por cuerpo y cara: comprobala antes de diseñar.

1. PANEL ÚNICO E INTUITIVO
Panel lateral acoplable, redimensionable y flotante, con tres zonas:
A. Destino: qué se modifica exactamente («Cuerpo completo · Base», «12 caras · Alas»), cambio entre cuerpos, caras y
   regiones de malla, cantidad y nombres de lo elegido.
B. Biblioteca: pestañas Biblioteca, Mis recursos, Favoritos y En uso; buscador; categorías y filtros; tarjetas con
   nombre, miniatura y estrella; crear, duplicar, renombrar y guardar recursos propios.
C. Propiedades: edición integrada sin encadenar ventanas; lo básico visible; lo avanzado agrupado y desplegable;
   controles accesibles en ventanas chicas.
Flujo principal: Seleccionar → elegir color o acabado → vista previa → Aplicar.

2. SELECCIÓN Y APLICACIÓN
- Respetar la selección previa; elegir desde el visor y el árbol; selección múltiple, sumar/quitar y por ventana.
- Arrastrar y soltar una muestra sobre su destino; modo explícito para pintar varios destinos seguidos.
- Mostrar el destino antes de aplicar y resaltarlo con contorno, sin tapar el color real.
- Aplicar a «Cuerpo completo» pinta TODO el cuerpo, también las caras con apariencia propia; opción explícita para
  conservarlas.
- La vista previa se puede descartar; cada aplicación confirmada es un paso de deshacer; deslizar un control no llena
  el historial. Aplicar, Cerrar y Esc definidos y coherentes, conservando lo ya confirmado.

3. COLORES, PALETAS Y GOTEROS
- Selector visual; campos HEX, RGB y HSV; muestras anterior/nueva; recientes; paletas con nombre; guardar y marcar
  favorito; persistencia entre sesiones; campos numéricos con punto y coma decimal.
- Gotero de pantalla: escritorio y otras aplicaciones, varios monitores y escalado, lupa y muestra, clic para capturar
  y Esc para cancelar.
- Copiar apariencia del modelo: la apariencia asignada a un objeto o cara (acabado completo y su textura), leída del
  documento y no del píxel iluminado del visor.

4. REGISTRO «EN USO»
- Vista persistente: objeto, destino (cuerpo, cara o región), apariencia, cantidad de usos, propia o heredada.
- Acciones: localizar y resaltar, seleccionar todos los usos, reemplazar en todos o solo en la selección, quitar una
  asignación, crear variante, consultar por objeto o por apariencia.
- Al editar una apariencia compartida: «Actualizar todos sus usos» o «Crear una variante para la selección».
- Derivado de las asignaciones reales del documento, sin una segunda lista. Conservar las referencias al cambiar
  parámetros; un destino perdido conserva su información y ofrece reasignarlo, nunca se pega callado a otra cara.

5. MATERIAL FÍSICO Y APARIENCIA
Mismo sistema, separación clara: material físico = propiedades del cuerpo para masa y cálculos; apariencia = color,
acabado y texturas (un PLA puede verse cromado sin la densidad del acero). La apariencia va a caras; el material
físico al cuerpo o componente. Solo las propiedades físicas que OmniCAD soporta, con unidades claras.

6. TEXTURAS Y MATERIALES PBR
- Editor de canales con miniatura, archivo, activación y ajustes: color base, rugosidad, metálico, normal, relieve
  visual (bump), opacidad y recorte, emisión, oclusión ambiental.
- Revisar barniz, anisotropía, transmisión/translucidez y su conexión con los motores de visualización.
- Todo control funcional tiene efecto real: guardar un parámetro sin usarlo en la visualización no cuenta.
- Separar relieve visual de relieve real por textura (cambia la geometría: tratamiento y validación propios).
- Respetar el espacio de color: imágenes de color y mapas de datos no se procesan igual.

7. IMPORTACIÓN Y RECURSOS
- PNG, JPG/JPEG, TIFF, TGA, WebP y BMP; planificar y verificar EXR/HDR donde corresponda.
- Importar imágenes, carpetas o ZIP de mapas PBR; detectar canales por nombre; revisar y corregir antes de confirmar.
- Incluir las texturas en el proyecto, reutilizar una imagen sin duplicarla, detectar ausentes y revincular.
- Respetar las validaciones y topes de archivos del proyecto. La compatibilidad con otras aplicaciones se describe por
  formatos y capacidades verificadas: leer una imagen no es interpretar un material nativo de Blender o Substance.

8. COLOCACIÓN DE TEXTURAS Y CALCOMANÍAS
Proyección automática, plana, caja, cilíndrica, esférica y triplanar; UV cuando haya; escala real en mm; giro;
desplazamiento; repetición; espejo; dirección de veta o cepillado; manipulador en el visor; restablecer; calcomanías
con transparencia. La colocación puede variar por asignación (mismo material, distinta escala u orientación).

9. INTEGRACIÓN EN LAS ÁREAS DEL PROGRAMA
Un sistema común de recursos y asignaciones en Sólido, Plástico, Superficie, Malla, Chapa y Forma, cada uno con su
selección adecuada (regiones cómodas en malla, ambos lados en superficie, relación plegado/desarrollo verificada en
chapa). Renderizar, Animación y las vistas sombreadas de Dibujo consumen las mismas asignaciones. Guardado e
intercambio coherentes en los formatos soportados.

10. ARQUITECTURA Y COMPATIBILIDAD
Reutilizar aspectos y propiedades del documento; abrir proyectos viejos con sus apariencias; Qt fuera del núcleo;
no recalcular geometría por cambios visuales; interfaz fluida al cargar imágenes o vistas previas (ver
`docs/auditoria_tiempos.md`); lo automatizable en la API común (MCP y CLI) con su doc regenerada.

11. FASES Y VERIFICACIÓN
Orden: 0) maqueta aprobada; 1) panel y selección; 2) colores, goteros, paletas y favoritos; 3) registro En uso y
edición compartida; 4) texturas, importación y representación; 5) colocación e integración entre áreas;
6) verificación integral y cierre.
Comprobar con pruebas y uso real (como usuario, regla de CLAUDE.md): aplicación a cuerpos y caras, selección múltiple
y repetida, copiar apariencia, persistencia de paletas y favoritos, apariencias compartidas y variantes, cambios
paramétricos y destinos perdidos, deshacer y rehacer, guardar/cerrar/reabrir, texturas incluidas, efecto visible de
cada canal, coherencia visor/render, ventanas chicas y escalados, proyectos anteriores.
Tests con `scripts/tests_afectados.py --correr` y lo pesado de a uno con `scripts/turno.py`. PROJECT_LOG.md,
`docs/seguimiento/` y la doc al día; una fase parcial queda marcada como parcial.

ENTREGA FINAL: qué quedó y dónde se usa, cómo se accede, qué queda pendiente, archivos principales y resultados reales
de las verificaciones. Gerardo es disléxico: informe corto, resultado primero.

Listo cuando: la maqueta está aprobada por Gerardo, las fases 1 a 6 están hechas o cargadas en `docs/seguimiento/` con
su motivo, y cada control del panel tiene efecto real verificado.
```
