# INSPECCIONAR en la ventana: auditoría del 2026-11-01

Las 15 herramientas probadas como persona con `scripts/prueba_ui/inspeccionar.py` (clic en el menú de la cinta, elegir con el
visor, teclear, vista previa, Enter, medir, reabrir, deshacer, Esc, Tab, ventana chica y una pieza real cambiando una cota).
Fuente del comportamiento: las 38 capturas de `analisis/capturas_fusion` (solo quedan las pendientes) y la sección «Analysis tools» de
`docs/fusion_docs`. Especificación: [brechas_inspeccionar.md](../brechas_inspeccionar.md).

## Antes y después

Antes: 135 comprobaciones, 34 con ✗ (`evidencias/inspeccionar_2026-11-01/antes/inspeccionar.log`). Después: 256 comprobaciones,
0 con ✗ (`evidencias/inspeccionar_2026-11-01/despues/inspeccionar.log`, capturas en `despues/capturas/`), sin excepciones en
un slot de Qt. «A medias» = lo que había andaba y faltaba lo de la columna.

| Herramienta | Antes | Después | Evidencia medida | Faltaba |
|---|---|---|---|---|
| Medir | A medias | Anda | Cara de 200 mm²; ΔX 30 en Global; Precisión 0.1 da «30.0 mm»; 80.0 mm (8.0 cm) | Filtro, Precisión, Unidades secundarias, Borrar selección, forzado, XYZ Delta, resaltar y copiar |
| Interferencia | A medias | Anda | Dos grupos, 4,000 mm³ y 0 mm³; Quitar volumen deja 8000 mm³ | Calcular, tabla ordenable, Mostrar todas, Quitar volumen |
| Curvatura en peine | A medias | Anda | Densidad 50, Escala 10.000; 99 segmentos | Valores por defecto y deslizadores |
| Cebra | A medias | Anda | Repetición 12 tecleada; pinta franjas | Reabrir para editar |
| Mapas de entorno | No anda | Anda | 13 entornos; cambia 0,16 % de los píxeles de la vista; Rotar 90° y sin reflejo cambian la imagen | Panel vacío |
| Ángulo de desmoldeo | A medias | Anda | −2 y 2 deg, Tolerancia ±0,5; un tope no cruza al otro; ±90; Calidad alta 19944 → 179496 vértices | Dos topes, Zona de tolerancia, Opacidad, Calidad alta |
| Mapa de curvatura | A medias | Anda | Límite máximo y mínimo según el tipo | Reabrir para editar |
| Isocurva | A medias | Anda | Una cara o el cuerpo: 940 segmentos; con peines 1900 | Elegir caras |
| Accesibilidad | A medias | Anda | Dirección 1: 90,7 %, Dirección 2: 35,7 %, Ambas: 97,8 % | Opacidad, Cambiar dirección |
| Radio mínimo | A medias | Anda | Sin y con Bordes afilados: 0 y 750 vértices rojos; el mínimo no pasa del máximo | Radio máximo y mínimo, Opacidad, Bordes afilados |
| Sección | A medias | Anda | Corta en z = 10; Desde el componente y rayado por defecto; Información con Consejos | Valores por defecto, panel de información |
| Centro de masa | A medias | Anda | Glifo en (−100, 0, 10); Medir desde él a la tapa: 10.000 mm | Carpeta Análisis, asociativo, medible |
| Sustainability Insights | No existe | Anda | 0.445 kg CO₂e; con stock el doble; País gris hasta la región | Todo |
| Colores de componente | A medias | Anda | Pinta y cicla; muestra en navegador y timeline; deshacer repone | Color de ciclo, muestras |
| Grupos de caras de malla | Grisado | Anda | Mayús+F; 3 colores por grupo; apagar devuelve el aspecto | Todo |

Pieza real: dos cuerpos con Centro de masa y Sección en la carpeta Análisis. Cambiar `alto_p` de 20 a 40 mm movió el centro de
(426.34, 15, 11.59) a (423.45, 15, 20) y el glifo lo siguió.

## Fallas nuevas que salieron de probar

Todas con su prueba. B-149 sigue Parcial en `docs/seguimiento/bugs.md`.

| ID | Qué | Causa | Prueba |
|---|---|---|---|
| B-147 | Un análisis guardado no se podía reabrir: el menú solo tenía Mostrar u ocultar y Suprimir | Faltaba Editar | pieza `inspeccionar`, «clic derecho › Editar»; `test_editar_analisis_conserva_nombre_y_se_deshace` |
| B-148 | El azul de la selección tapaba el mapa de entorno: la vista no cambiaba al elegir el entorno | La capa `seleccion` pinta el cuerpo entero | pieza `inspeccionar`, «aplica cromo a los elegidos» |
| B-149 | Radio mínimo pintaba de rojo las paredes enteras de un vaciado | Una cara plana con sus cuatro esquinas sobre aristas cóncavas quedaba marcada entera | `test_radio_minimo_degrade_entre_dos_radios`, captura `radio_minimo_cerca` |
| B-150 | La caja de Ángulo tapaba a la de Distancia en Sección | Dos asas juntas ubicaban sus cajas en el mismo lugar | pieza `inspeccionar`, «las cajas de Distancia y Ángulo no se pisan» |

## Contra Fusion, panel por panel

Mirado contra las capturas. Fusion real quedó cerrado: lo que solo se ve con él está al final.

| Panel | Se parece | No se parece |
|---|---|---|
| Medir | Filas, orden y 9 precisiones; Cerrar solo | Suma Centro a centro, a propósito. Puntos de forzado solo se ve con el filtro de geometría |
| Interferencia | Calcular, tabla, Mostrar todas | Sin captura de Fusion: sale de la ayuda. Quitar volumen siempre visible, porque no hay modo directo |
| Curvatura en peine | Densidad 50, Escala 10.000 | Nada que se note |
| Cebra | Filas iguales | Sin selección calcula todos: Fusion deja Aceptar gris |
| Mapas de entorno | 4 filas, Luz suave | Una cara plana refleja un solo color: H-56 |
| Ángulo de desmoldeo | Dos topes, Tolerancia, Opacidad, Calidad alta | Suma Invertir dirección, a propósito |
| Mapa de curvatura | Filas y panel de información | Los íconos de Tipo son otros dibujos |
| Isocurva | Filas iguales | Nada que se note |
| Accesibilidad | Filas y tres sentidos | Nada que se note |
| Radio mínimo | Filas, 25 mm y 0.000 mm | Nada que se note |
| Sección | Solo Plano de corte al abrir; información | Suma Cuerpos, Distancia y Ángulo una vez elegido el plano |
| Centro de masa | Selección de cuerpos o componentes | Sin selección calcula todos |
| Sustainability Insights | Dos pestañas y textos vacíos de la captura | El resultado es decisión propia: las capturas no lo muestran |

## Factores de CO₂

Consultados el 2026-11-01. kg de CO₂e por kg de material, de la materia prima a la salida de fábrica. Región y país no cambian
el cálculo: no hay un factor de red eléctrica con fuente (H-55). Densidades: las de `TABLA_MATERIALES`, y nominales para ASA, PTFE y PVC.

| Material | Factor | Fuente |
|---|---|---|
| ABS | 3.76 | [ICE V2.0, tablas resumen](https://kps.fsv.cvut.cz/upload/files/icev2.0summarytables.pdf) |
| ASA | Vacío, con aviso | No se encontró fuente |
| Aluminio | 9.16 | ICE V2.0, aluminio general |
| Cobre | 2.71 | ICE V2.0, tubo y chapa UE |
| Nylon | 9.14 | ICE V2.0, nylon 6 |
| PTFE | 133.0 | [Carbonfact](https://www.carbonfact.com/materials/polytetrafluoroethylene): base propia, sector textil |
| PVC | 3.10 | ICE V2.0, general |
| Policarbonato | 7.62 | ICE V2.0 |
| Polietileno | 2.54 | ICE V2.0, general |
| Polipropileno | 4.49 | ICE V2.0, inyección |
| Acero inoxidable | 6.15 | [ICE v1.6a](https://www.appropedia.org/w/images/5/56/ICE_Version_1.6a.pdf) |
| Acero | 1.77 | ICE v1.6a, general |
| Titanio | 31.55 | ICE V2.0, virgen: punto medio de 20,6 a 42,5, datos viejos |

## Decisiones

- **Quitar volumen:** OmniCAD no tiene modo directo, así que la columna está siempre, sin marcar, y Aceptar deja un paso Combinar por par.
- **Colores de componente:** pasan a ser por componente, con la paleta del timeline. Un cuerpo suelto conserva su aspecto, igual
  que en la API. `component_colors` de `get_viewport_image` cambió de colores para coincidir con la ventana.
- **Documentos viejos:** las opciones nuevas se guardan solo si vienen del panel. El modo viejo de Radio mínimo sigue pintando lo
  mismo, a propósito: por eso B-149 queda Parcial.
- **Panel de información:** se abre con el botón «i», en Sección y Mapa de curvatura, los dos con texto en las capturas. Más
  información abre el artículo local, nunca la web.

## Lo que no se pudo comprobar

Sin Fusion real no se pudo ver cómo reaccionan la Interferencia con componentes, Quitar volumen en modo directo, si Puntos de
forzado sigue visible con otro filtro, y cómo se ve Sustainability Insights con un cuerpo elegido. Está en la sección 0b de
[prueba_nocturna_2026-10-31.md](prueba_nocturna_2026-10-31.md).
