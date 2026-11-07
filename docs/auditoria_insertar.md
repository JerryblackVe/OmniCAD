# Auditoría, reparación y paridad de la sección INSERTAR contra Fusion 360

Pedido de Gerardo (2026-11-07): auditar, reparar y completar contra Fusion 360 las 11 herramientas de INSERTAR
(Calcomanía, Lienzo, Insertar SVG, Vectorizar imagen, Insertar DXF, Insertar malla, Insertar STEP, Insertar fijador,
Duplicar con uniones, Insertar componente e Insertar derivación) en todos los espacios donde aparecen. Mismo
procedimiento que [auditoria_boceto_crear_modificar.md](auditoria_boceto_crear_modificar.md): ejecutan los agentes,
Claude solo como última instancia, y al final todo verde.

**Cuándo:** otro día, el que elija Gerardo. Va 4.ª de 6; orden y reparto en [agenda.md](seguimiento/agenda.md) (sección «Orden y reparto de las auditorías»).

## Prompt para el agente

Guardado el 2026-11-07. Modelo sugerido: coordina una sesión Claude Opus 5 con esfuerzo alto; ejecutan Sol (OpenCode) y los agentes gratis aprobados, un ítem por corrida y cada uno en su worktree.

```text
AJUSTE DEL COORDINADOR (2026-11-08; manda sobre todo lo que sigue)
- Orden de las seis auditorías (de a una; la siguiente arranca cuando la anterior quedó cerrada y commiteada): 1) CONSTRUIR (AG-7), 2) herramientas 3D (AG-2), 3) MODIFICAR (AG-4), 4) INSERTAR (AG-6), 5) ENSAMBLAR (AG-5), 6) RENDERIZAR (AG-3). Cada herramienta tiene UNA sola auditoría dueña. Las demás solo la usan en sus pruebas combinadas: si encuentran un bug en una herramienta ajena, cargan la fila en docs/seguimiento/ y la arreglan solo si la dueña ya pasó (está antes en el orden); si la dueña viene después, dejan la fila para ella.
- Sos la dueña de Calcomanía, Lienzo, Insertar SVG, Vectorizar imagen, DXF, malla, STEP, fijador y derivación. Duplicar con uniones e Insertar componente son de ENSAMBLAR (AG-5): salteá sus partes XII y XIII.

# PROMPT MAESTRO — AUDITORÍA, REPARACIÓN Y PARIDAD FUNCIONAL DE TODA LA SECCIÓN INSERTAR DE OMNICAD

## 1. MISIÓN PRINCIPAL

Actuá como un equipo senior de ingeniería de software CAD paramétrico, especializado en:

- Arquitectura de sistemas CAD profesionales.
- OpenCascade y modelado B-Rep.
- Importación y conversión de formatos CAD.
- Geometría vectorial SVG/DXF.
- Procesamiento y vectorización de imágenes.
- Geometría de mallas tridimensionales.
- Transformaciones y sistemas de coordenadas.
- Referencias externas y geometría asociativa.
- Ensamblajes y componentes.
- Bibliotecas de elementos mecánicos.
- Gestión de texturas y calcomanías.
- Interfaces gráficas PySide6/OpenGL.
- Seguridad y validación de archivos.
- Optimización y automatización de pruebas.

Tu misión es realizar una **AUDITORÍA EXHAUSTIVA, REPARACIÓN DE BUGS, IMPLEMENTACIÓN DE FUNCIONES FALTANTES Y OPTIMIZACIÓN DE TODA LA SECCIÓN INSERTAR DE OMNICAD**.

### OBJETIVO PRINCIPAL

Conseguir que todas las herramientas auditadas tengan el comportamiento funcional, la precisión geométrica, la facilidad de uso y las capacidades de sus equivalentes en Autodesk Fusion 360.

La auditoría debe ejecutarse en todos los espacios donde las herramientas estén disponibles:

- SÓLIDO.
- SUPERFICIE.
- PLÁSTICO.
- CHAPA.
- MALLA.
- BOCETO.
- ENSAMBLAR.
- RENDERIZAR.
- Otros espacios aplicables.

**NO quiero únicamente un informe de errores. Quiero que investigues, detectes, reproduzcas, repares, mejores, completes y verifiques las funciones.**

El resultado esperado es un sistema INSERTAR robusto, preciso, profesional y compatible con el resto de OmniCAD.

---

# PARTE I — INSTRUCCIONES OBLIGATORIAS

## 2. REGLAS DEL PROYECTO

Antes de modificar código:

1. Leer `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` y `PROJECT_CONTEXT.md`.
2. Invocar mediante la herramienta Skill `fable-method` y `ponytail`.
3. Utilizar `plan-then-do`, `tool-calling-guard` y `verify-before-commit`.
4. Utilizar `ponytail-audit` cuando corresponda.
5. Invocar `omnicad-test` para pruebas reales de interfaz.
6. Ejecutar `ponytail-review` antes de cerrar cada corrección.
7. Respetar la arquitectura, convenciones y reglas de Git.
8. No instalar dependencias sin autorización.
9. No copiar código propietario de Autodesk.
10. No realizar `git push`.

Respetar las reglas de sesiones, pruebas pesadas, memoria, integración y commits del proyecto.

Cada bug debe cerrarse individualmente, con pruebas, antes de continuar con la siguiente corrección.

No declarar un problema solucionado sin evidencia.

---

# PARTE II — INVESTIGACIÓN DE FUSION 360

## 3. DOCUMENTACIÓN OFICIAL OBLIGATORIA

La fuente principal será la documentación oficial de Fusion 360 descargada en:

`docs/fusion_docs/`

Consultar especialmente:

- `fusion-model`
- `fusion-sketch`
- `fusion-mesh`
- `fusion-assemble`
- `fusion-patch`
- `fusion-sheet-metal`
- `fusion-render`
- `fusion-designs`

Utilizar:

`scripts/fusion_docs.py buscar`

`scripts/fusion_docs.py ver`

Consultar también la documentación oficial en línea cuando la información local sea insuficiente o se requiera verificar funcionalidades más recientes.

### INVESTIGAR

- Insert Component.
- Insert Fastener.
- Insert Derive.
- Decal.
- Canvas.
- Insert SVG.
- Insert DXF.
- Insert Mesh.
- Import CAD.
- External Components.
- Linked Components.
- Derive Design Features.
- Component Patterns.
- As-Built Joints.
- Insert Manufacturer Parts.
- Bibliotecas de componentes y fijadores.

Investigar las capacidades que realmente estén documentadas.

### PARA CADA HERRAMIENTA IDENTIFICAR

1. Funcionalidad.
2. Ubicación.
3. Opciones disponibles.
4. Submenús.
5. Parámetros.
6. Valores predeterminados.
7. Tipos de archivos.
8. Selección de geometría.
9. Posicionamiento.
10. Transformaciones.
11. Vista previa.
12. Edición posterior.
13. Asociatividad.
14. Persistencia.
15. Integración con el timeline.
16. Limitaciones documentadas.

**Prohibido inventar características de Fusion 360. Toda comparación debe estar respaldada por documentación o pruebas verificables.**

Cuando una función de OmniCAD no tenga un equivalente directo, distinguirla y auditar su comportamiento propio.

---

# PARTE III — INVENTARIO COMPLETO DE INSERTAR

## 4. HERRAMIENTAS OBLIGATORIAS

La captura del usuario muestra:

1. Calcomanía.
2. Lienzo.
3. Insertar SVG.
4. Vectorizar imagen.
5. Insertar DXF.
6. Insertar malla.
7. Insertar STEP.
8. Insertar fijador.
9. Duplicar con uniones.
10. Insertar componente.
11. Insertar derivación.

También aparecen accesos directos:

- Insertar componente.
- Lienzo.
- Insertar fijador.

### OBLIGACIÓN

Inspeccionar todos los submenús, cuadros de diálogo, opciones adicionales y comandos relacionados.

No limitarse a los elementos visibles.

Buscar todas las implementaciones presentes en:

- `clon/omnicad/ui/`
- `clon/omnicad/ui/comandos/`
- `clon/omnicad/io_archivos/`
- `clon/omnicad/nucleo/`
- `clon/omnicad/timeline/`
- `clon/omnicad/restricciones/`
- `clon/omnicad/api/`

Identificar los módulos concretos utilizados por cada herramienta.

Comprobar también si existen funciones internas no expuestas en la interfaz.

---

# PARTE IV — CALCOMANÍA

## 5. AUDITORÍA COMPLETA DE DECAL

Comparar con Decal de Fusion 360.

### FUNCIONES A REVISAR

- Selección de imagen.
- Selección de cara.
- Selección de varias caras.
- Encadenamiento de caras.
- Posición.
- Desplazamiento.
- Escala.
- Rotación.
- Volteo horizontal.
- Volteo vertical.
- Proporciones.
- Opacidad.
- Transparencia.
- Proyección sobre superficies.
- Edición posterior.
- Visibilidad.
- Persistencia.

### GEOMETRÍAS

Probar calcomanías sobre:

1. Cara plana.
2. Cilindro.
3. Esfera.
4. Superficie cónica.
5. Superficie curva.
6. Varias caras tangentes.
7. Varias caras con distintas orientaciones.
8. Cuerpo con empalmes.
9. Superficies importadas desde STEP.

### VALIDACIÓN

Comprobar:

- Posición real.
- Proporciones.
- Orientación.
- Deformación.
- Mapeo UV.
- Recorte.
- Transparencia.
- Calidad de textura.
- Ausencia de artefactos.
- Continuidad visual entre caras.

La calcomanía debe mantener su relación con la geometría cuando el cuerpo se mueve o transforma, según el comportamiento documentado.

### INTEGRACIÓN

Comprobar que funcione correctamente en:

- SÓLIDO.
- SUPERFICIE.
- RENDERIZAR.
- Otros espacios compatibles.

Verificar que una calcomanía no altere el B-Rep original cuando su función sea exclusivamente visual.

---

# PARTE V — LIENZO

## 6. AUDITORÍA COMPLETA DE CANVAS

Comparar con Canvas de Fusion 360.

### FUNCIONES

- Insertar imagen.
- Seleccionar plano.
- Seleccionar cara plana.
- Posición.
- Escala.
- Rotación.
- Volteo.
- Opacidad.
- Visibilidad.
- Mostrar a través.
- Calibración.
- Edición.
- Ocultar.
- Eliminar.
- Persistencia.

### CALIBRACIÓN

Auditar especialmente:

1. Selección de dos puntos en la imagen.
2. Introducción de distancia real.
3. Cálculo de escala.
4. Actualización de dimensiones.
5. Conservación de proporciones.
6. Posicionamiento posterior.
7. Precisión numérica.

La distancia calibrada debe corresponder exactamente a las unidades seleccionadas, dentro de las tolerancias numéricas establecidas.

### PRUEBAS

Insertar:

- Plano técnico.
- Fotografía.
- Imagen PNG transparente.
- Imagen JPG.
- Imagen de dimensiones conocidas.
- Imagen de gran resolución.

Verificar:

- Orientación correcta.
- Relación de aspecto.
- Calidad visual.
- Selección.
- Transformaciones.
- Visibilidad.
- Persistencia.

### DIFERENCIACIÓN

**Lienzo y Calcomanía no deben utilizarse como si fueran la misma herramienta.**

Investigar y conservar sus diferencias funcionales.

---

# PARTE VI — INSERTAR SVG

## 7. AUDITORÍA COMPLETA DE SVG

Comparar con Insert SVG de Fusion 360.

Esta herramienta requiere una auditoría especialmente profunda porque OmniCAD utiliza geometría vectorial para generar perfiles CAD.

### IMPORTACIÓN

Comprobar:

- Lectura de SVG.
- Unidades.
- `viewBox`.
- Tamaño.
- Transformaciones.
- Escala.
- Posición.
- Rotación.
- Grupos.
- Capas.
- Trazados.
- Curvas Bézier.
- Líneas.
- Arcos.
- Círculos.
- Elipses.
- Contornos.
- Agujeros.
- Rellenos.
- Regla `evenodd`.
- Regla `nonzero`.
- Transformaciones anidadas.

### GEOMETRÍA

Validar:

- Fidelidad dimensional.
- Continuidad de curvas.
- Cierre de perfiles.
- Curvas degeneradas.
- Contornos duplicados.
- Intersecciones.
- Curvas abiertas.
- Agujeros internos.
- Clasificación de regiones.
- Calidad de la aproximación geométrica.

### OBJETOS VECTORIALES

OmniCAD permite manipular SVG como objetos lógicos.

Respetar este diseño.

Auditar:

- Selección del objeto completo.
- Mover.
- Rotar.
- Escalar.
- Cambiar pivote.
- Duplicar.
- Agrupar.
- Desagrupar.
- Alinear.
- Distribuir.
- Editar dimensiones.
- Visibilidad.
- Bloqueo.
- Persistencia.

**No convertir innecesariamente cada elemento del SVG en cientos o miles de puntos visibles al usuario.**

La interacción debe ser cómoda y profesional.

### PRUEBAS

Importar:

1. Logotipo simple.
2. Logotipo complejo.
3. SVG con múltiples grupos.
4. SVG con curvas Bézier.
5. SVG con agujeros.
6. SVG con transformaciones anidadas.
7. SVG con unidades diferentes.
8. SVG con cientos de curvas.
9. SVG con trazados abiertos.
10. SVG con regiones superpuestas.

### INTEGRACIÓN 3D

Comprobar que los perfiles resultantes puedan utilizarse en:

- Extrusión.
- Corte.
- Revolución, cuando corresponda.
- Barrido.
- Repujado.
- Otras operaciones compatibles.

No considerar exitosa una importación solamente porque se vea correctamente en el visor.

**Los perfiles deben ser geométricamente válidos y utilizables para operaciones CAD.**

---

# PARTE VII — VECTORIZAR IMAGEN

## 8. AUDITORÍA COMPLETA DE VECTORIZE IMAGE

Esta función debe evaluarse como una capacidad propia de OmniCAD, sin asumir que Fusion 360 dispone de un comando nativo idéntico.

Investigar referencias técnicas apropiadas para su implementación.

### FUNCIONES

- Carga de imagen.
- Conversión de colores.
- Detección de contornos.
- Umbral.
- Segmentación.
- Reconocimiento de regiones.
- Generación de curvas.
- Suavizado.
- Simplificación.
- Tolerancia.
- Eliminación de ruido.
- Separación de elementos.
- Detección de agujeros.
- Cierre de perfiles.
- Escala.
- Posicionamiento.

### CALIDAD DE VECTORIZACIÓN

Comprobar:

- Fidelidad respecto de la imagen.
- Número de curvas.
- Cantidad de puntos de control.
- Precisión.
- Suavidad.
- Continuidad.
- Ausencia de curvas duplicadas.
- Ausencia de perfiles falsos.
- Calidad de las esquinas.
- Conservación de agujeros.

### OBJETIVO

Generar geometría útil para modelado CAD.

No producir miles de segmentos innecesarios cuando puedan representarse mediante curvas más simples y precisas.

### PRUEBAS

Vectorizar:

1. Logo monocromático.
2. Logo multicolor.
3. Silueta geométrica.
4. Texto rasterizado.
5. Imagen con agujeros internos.
6. Imagen con bordes suaves.
7. Imagen con ruido.
8. Imagen de baja resolución.
9. Imagen con fondo transparente.
10. Imagen de alta resolución.

### VALIDACIÓN

Comparar las curvas generadas contra las regiones originales mediante métricas de desviación.

Probar extrusión y otras operaciones compatibles.

Documentar los límites de precisión del método.

---

# PARTE VIII — INSERTAR DXF

## 9. AUDITORÍA COMPLETA DE DXF

Comparar con Insert DXF de Fusion 360.

### IMPORTACIÓN

Auditar:

- Unidades.
- Capas.
- Selección de capas.
- Inserción en un único boceto.
- Inserción de un boceto por capa.
- Plano de destino.
- Posición.
- Rotación.
- Escala.
- Coordenadas.
- Entidades compatibles.
- Bloques.
- Transformaciones.
- Arcos.
- Líneas.
- Polilíneas.
- Splines.
- Círculos.
- Elipses.
- Contornos cerrados.

### VALIDACIÓN

Comprobar:

- Dimensiones originales.
- Coordenadas.
- Orientación.
- Capas.
- Fidelidad geométrica.
- Perfiles.
- Duplicaciones.
- Continuidad.
- Referencias.
- Edición posterior.

### PRUEBAS

Importar DXF con:

- Una capa.
- Múltiples capas.
- Distintas unidades.
- Polilíneas cerradas.
- Arcos y círculos.
- Splines.
- Bloques anidados compatibles.
- Cientos de entidades.
- Entidades repetidas.
- Geometría alejada del origen.

### PRUEBA CRÍTICA

Insertar un DXF de dimensiones conocidas.

Medirlo en OmniCAD.

Comprobar que las dimensiones coincidan con el archivo original.

Extruir sus perfiles cuando sean compatibles.

---

# PARTE IX — INSERTAR MALLA

## 10. AUDITORÍA COMPLETA DE MESH IMPORT

Comparar con Insert Mesh de Fusion 360.

### FORMATOS

Auditar los formatos realmente soportados por OmniCAD, incluyendo cuando correspondan:

- STL.
- OBJ.
- 3MF.
- PLY.
- Otros formatos de malla disponibles.

### FUNCIONES

- Selección de archivo.
- Lectura.
- Unidades.
- Escala.
- Orientación.
- Posición.
- Rotación.
- Ejes.
- Materiales.
- Colores.
- Texturas.
- Normales.
- Triangulación.
- Jerarquía.
- Componentes.
- Edición posterior.

### VALIDACIÓN GEOMÉTRICA

Comprobar:

- Número de vértices.
- Número de triángulos.
- Dimensiones.
- Caja envolvente.
- Orientación de normales.
- Mallas abiertas.
- Mallas cerradas.
- Autointersecciones.
- Geometría no manifold.
- Triángulos degenerados.
- Caras duplicadas.
- Componentes desconectados.

### PRUEBAS

Importar:

1. STL simple.
2. STL complejo.
3. STL binario.
4. STL ASCII.
5. OBJ con materiales.
6. 3MF multicomponente.
7. 3MF con colores, cuando corresponda.
8. Malla abierta.
9. Malla con errores.
10. Malla con cientos de miles de triángulos.

### INTEGRACIÓN

Verificar que las mallas importadas puedan utilizarse en todas las herramientas compatibles del espacio MALLA.

Cuando corresponda, comprobar los flujos de conversión a B-Rep y reconstrucción paramétrica.

**No realizar conversiones silenciosas que alteren la geometría original.**

---

# PARTE X — INSERTAR STEP

## 11. AUDITORÍA COMPLETA DE STEP

Investigar el comportamiento de importación de archivos STEP de Fusion 360 y sus diferencias según el flujo de apertura, inserción o carga.

### FUNCIONES

- Lectura de STEP.
- Versiones y esquemas admitidos.
- Unidades.
- Geometría B-Rep.
- Cuerpos sólidos.
- Superficies.
- Ensamblajes.
- Jerarquías.
- Componentes.
- Transformaciones.
- Nombres.
- Colores.
- Metadatos disponibles.
- Tolerancias.
- Reparación cuando corresponda.

### VALIDACIÓN

Comprobar:

- Cantidad de cuerpos.
- Cantidad de componentes.
- Posiciones.
- Orientaciones.
- Dimensiones.
- Volumen.
- Área.
- Topología.
- Solidez.
- Normales.
- Referencias de componentes.

### PRUEBAS

Importar:

1. Pieza simple.
2. Pieza con agujeros.
3. Pieza con superficies curvas.
4. Pieza con empalmes.
5. Ensamblaje de varios componentes.
6. Ensamblaje con jerarquía.
7. Archivo con cuerpos abiertos.
8. Archivo con varias unidades.
9. Archivo con errores geométricos recuperables.
10. Archivo complejo.

### PRUEBA CRÍTICA

Importar un ensamblaje STEP con posiciones conocidas.

Comprobar que cada componente conserve su posición y orientación.

No permitir que aparezcan cuerpos desplazados, duplicados o transformados incorrectamente.

### INTEGRACIÓN

Probar los modelos importados con:

- Extrusión y corte compatibles.
- Empalme.
- Chaflán.
- Vaciado.
- Combinar.
- Dividir cuerpo.
- Mover/copiar.
- Ensamblar.
- Renderizar.
- Exportación.

Validar que la importación produzca geometría realmente utilizable.

---

# PARTE XI — INSERTAR FIJADOR

## 12. AUDITORÍA COMPLETA DE FASTENERS

Comparar con Insert Fastener de Fusion 360.

### ELEMENTOS

Auditar las familias disponibles:

- Tornillos.
- Pernos.
- Tuercas.
- Arandelas.
- Remaches.
- Otros fijadores implementados.

### PARÁMETROS

- Tipo.
- Norma.
- Familia.
- Tamaño.
- Diámetro.
- Longitud.
- Paso.
- Rosca.
- Material.
- Acabado.
- Identificación.
- Posicionamiento.
- Orientación.

### POSICIONAMIENTO

Probar:

- Agujeros.
- Aristas circulares.
- Caras cilíndricas.
- Puntos de boceto.
- Centros.
- Caras cónicas compatibles.
- Múltiples agujeros.
- Selección de fijador existente.

Comprobar la selección automática de tamaño cuando corresponda.

### VALIDACIÓN

- Dimensiones correctas.
- Norma correspondiente.
- Rosca compatible.
- Posición.
- Orientación.
- Ausencia de penetraciones indebidas.
- Relación con componente.
- Persistencia.
- Edición.

### PRUEBA REAL

Crear una placa con varios agujeros.

Insertar distintos fijadores.

Comprobar diámetro, longitud, posición y orientación.

No considerar correcto un fijador únicamente porque visualmente parezca un tornillo.

---

# PARTE XII — DUPLICAR CON UNIONES

## 13. AUDITORÍA COMPLETA

Comparar con la función equivalente documentada de Fusion 360.

### INVESTIGAR

- Selección de componentes.
- Duplicación.
- Posicionamiento.
- Conservación de uniones.
- Duplicación de referencias.
- Jerarquía.
- Relaciones internas.
- Relaciones externas.
- Identificadores.
- Transformaciones.
- Edición posterior.

### PRUEBAS

1. Duplicar un componente unido.
2. Duplicar dos componentes unidos entre sí.
3. Duplicar un subensamblaje.
4. Duplicar un grupo rígido.
5. Duplicar un mecanismo con varias uniones.
6. Modificar las copias.
7. Modificar el original.
8. Guardar y recuperar.

### VALIDACIÓN

Las copias deben conservar las relaciones esperadas sin crear uniones cruzadas incorrectas.

No reutilizar identificadores que deban ser únicos.

No desplazar componentes dos veces por errores de transformación.

---

# PARTE XIII — INSERTAR COMPONENTE

## 14. AUDITORÍA COMPLETA DE COMPONENT INSERT

Comparar con Insert Component de Fusion 360.

### FUNCIONES

- Selección de diseño.
- Inserción.
- Componentes externos.
- Componentes internos cuando corresponda.
- Instancias.
- Posicionamiento.
- Orientación.
- Transformación.
- Activación.
- Jerarquía.
- Referencias.
- Edición.
- Actualización.
- Persistencia.

### REFERENCIAS EXTERNAS

Auditar:

- Asociación con el archivo original.
- Actualización cuando cambia el origen.
- Gestión de enlaces.
- Referencias perdidas.
- Sustitución de archivo.
- Rutas.
- Versiones.
- Dependencias.
- Prevención de referencias circulares.

### PRUEBAS

Insertar:

1. Componente simple.
2. Componente complejo.
3. Componente con varios cuerpos.
4. Subensamblaje.
5. Componente externo vinculado.
6. Varias instancias del mismo componente.
7. Componentes con materiales.
8. Componentes con posiciones predefinidas.

### VALIDACIÓN

Comprobar que la posición del componente se mantenga al guardar, mover el ensamblaje y reabrir.

Verificar que una instancia vinculada refleje correctamente los cambios de su origen cuando la asociatividad esté habilitada.

---

# PARTE XIV — INSERTAR DERIVACIÓN

## 15. AUDITORÍA COMPLETA DE INSERT DERIVE

Comparar con Insert Derive de Fusion 360.

### FUNCIONES

Investigar derivación de:

- Componentes.
- Cuerpos.
- Bocetos.
- Geometría de construcción.
- Parámetros.
- Desarrollos de chapa, cuando corresponda.
- Otras entidades compatibles.

### ASOCIATIVIDAD

Verificar:

- Selección del diseño origen.
- Selección de elementos.
- Inserción.
- Referencias.
- Dependencias.
- Actualización.
- Edición.
- Supresión.
- Eliminación.
- Persistencia.

### PRUEBAS

1. Derivar un cuerpo.
2. Derivar varios cuerpos.
3. Derivar un boceto.
4. Derivar parámetros.
5. Derivar un componente.
6. Modificar el archivo origen.
7. Actualizar el destino.
8. Guardar y recuperar.
9. Modificar la lista de elementos derivados.
10. Probar una referencia faltante.

### REGLA CRÍTICA

Una derivación asociativa debe actualizarse cuando cambie su origen, según el flujo de actualización documentado.

No convertir silenciosamente las referencias en geometría independiente.

No permitir dependencias circulares que corrompan el documento.

---

# PARTE XV — AUDITORÍA TRANSVERSAL DE ESPACIOS

## 16. COMPROBAR TODAS LAS IMPLEMENTACIONES

Para cada herramienta, identificar dónde aparece realmente en OmniCAD.

### SÓLIDO

Validar inserción de cuerpos, componentes, geometría vectorial, imágenes y referencias.

### SUPERFICIE

Validar inserción y posicionamiento sobre superficies, cuando el comando lo admita.

### PLÁSTICO

Comprobar la inserción de componentes, fijadores y referencias utilizadas en diseños plásticos.

### CHAPA

Validar componentes, geometría importada, referencias y derivaciones compatibles con chapa.

### MALLA

Verificar importación, posicionamiento, materiales y uso posterior de mallas.

### BOCETO

Comprobar SVG, DXF, imágenes, geometría proyectada y objetos vectoriales.

### ENSAMBLAR

Verificar componentes, fijadores, duplicaciones, referencias y uniones.

### RENDERIZAR

Comprobar lienzos, calcomanías, materiales y su correcta visualización cuando correspondan.

### REGLA OBLIGATORIA

No considerar suficiente probar una herramienta desde un único espacio.

Cuando existan diferencias de contexto, documentarlas y verificar que coincidan con el comportamiento de referencia.

---

# PARTE XVI — MANIPULACIÓN Y EXPERIENCIA DE USUARIO

## 17. AUDITORÍA DE INTERFAZ

Probar para cada comando:

- Menús.
- Submenús.
- Botones.
- Iconos.
- Atajos.
- Selección de archivo.
- Selector de plano.
- Selección de caras.
- Selección de cuerpos.
- Vista previa.
- Posicionamiento.
- Escalado.
- Rotación.
- Manipuladores.
- Campos numéricos.
- Confirmación.
- Cancelación.
- Edición.
- Deshacer.
- Rehacer.

### PROBLEMAS A BUSCAR

- Botones sin acción.
- Menús que se cierran incorrectamente.
- Diálogos incompletos.
- Archivos que no cargan.
- Imágenes invertidas.
- Escalas erróneas.
- Objetos fuera de posición.
- Previsualizaciones incorrectas.
- Falta de actualización.
- Manipuladores defectuosos.
- Comandos que dejan estados activos después de cancelar.

**La experiencia de inserción debe resultar tan intuitiva y predecible como la de Fusion 360.**

---

# PARTE XVII — SEGURIDAD DE ARCHIVOS

## 18. VALIDACIÓN OBLIGATORIA

Todos los archivos importados deben tratarse como datos externos no confiables.

Auditar:

- Validación de formatos.
- Tamaños máximos.
- Archivos truncados.
- Archivos corruptos.
- Entradas malformadas.
- Referencias externas.
- Rutas relativas.
- Rutas absolutas.
- ZIP y 3MF.
- Recursos SVG externos.
- Entidades DXF inválidas.
- Estructuras STEP defectuosas.
- Mallas de tamaño excesivo.
- Uso de memoria.
- Cancelación.
- Errores de lectura.

No permitir:

- Ejecución accidental de código.
- Lectura no autorizada de archivos.
- Extracción de ZIP fuera del destino.
- Bloqueos permanentes.
- Corrupción del proyecto.
- Consumo de memoria sin límites razonables.

Si un archivo no puede importarse correctamente, mostrar un error claro y conservar intacto el documento original.

---

# PARTE XVIII — PERSISTENCIA Y TIMELINE

## 19. PRUEBA DE CICLO COMPLETO

Para cada herramienta:

1. Insertar elemento.
2. Posicionarlo.
3. Editarlo.
4. Crear operaciones dependientes.
5. Guardar.
6. Cerrar OmniCAD.
7. Abrir nuevamente.
8. Verificar posición y escala.
9. Verificar referencias.
10. Modificar el origen cuando corresponda.
11. Recalcular.
12. Deshacer y rehacer.

### VERIFICAR

- Identificadores estables.
- Transformaciones.
- Referencias.
- Parámetros.
- Dependencias.
- Materiales.
- Texturas.
- Archivos asociados.
- Compatibilidad con proyectos anteriores.

Las imágenes y recursos vinculados no deben perderse silenciosamente al mover un proyecto a otra carpeta.

Evaluar portabilidad mediante recursos embebidos o referencias gestionadas, según el comportamiento definido para el formato `.omnicad`.

---

# PARTE XIX — PRUEBAS COMBINADAS

## 20. ESCENARIOS REALES

Crear casos integrados:

1. Lienzo → Calibrar → Boceto → Extruir.
2. SVG → Escalar → Extruir.
3. SVG → Manipular objeto → Cortar sólido.
4. Imagen → Vectorizar → Generar perfiles → Extruir.
5. DXF multicapa → Boceto → Modelado 3D.
6. STL → Insertar malla → Transformar.
7. Malla → Reconstrucción paramétrica compatible.
8. STEP → Modificar sólido.
9. STEP → Crear ensamblaje.
10. Agujero → Insertar fijador.
11. Componente → Duplicar con uniones.
12. Componente externo → Actualizar origen.
13. Cuerpo → Insertar derivación → Modificar origen.
14. Calcomanía → Mover cuerpo → Renderizar.
15. Lienzo → Guardar → Reabrir → Calibrar.
16. SVG complejo → Extruir múltiples regiones.
17. DXF con diferentes unidades → Medir dimensiones.
18. 3MF multicomponente → Verificar estructura.
19. Subensamblaje importado → Aplicar uniones.
20. Proyecto con múltiples recursos → Guardar y recuperar.

Cada prueba deberá comprobar el resultado real, no únicamente la ausencia de excepciones.

---

# PARTE XX — DETECCIÓN Y REPARACIÓN DE BUGS

## 21. REPARACIÓN OBLIGATORIA

**Esta auditoría incluye corregir todos los bugs confirmados dentro del alcance.**

Para cada defecto:

1. Reproducir el problema.
2. Registrar evidencia.
3. Localizar la causa raíz.
4. Crear un test que falle.
5. Corregir la implementación.
6. Ejecutar el test.
7. Verificar la geometría o recurso.
8. Probar desde la interfaz.
9. Ejecutar regresiones.
10. Ejecutar `ponytail-review`.
11. Registrar la corrección.

### PROHIBIDO

- Ocultar errores.
- Ignorar tests fallidos.
- Eliminar pruebas para obtener resultados verdes.
- Cambiar resultados esperados sin justificación.
- Modificar archivos originales del usuario.
- Alterar silenciosamente dimensiones o unidades.
- Romper funciones existentes.
- Crear parches exclusivos para un archivo de ejemplo.
- Declarar funciones terminadas sin evidencia.

Buscar soluciones estructurales y reutilizables.

---

# PARTE XXI — IMPLEMENTACIÓN DE FALTANTES

## 22. COMPLETAR FUNCIONALIDADES

Comparar cada comando con Fusion 360.

Detectar:

- Opciones faltantes.
- Modos incompletos.
- Formatos no soportados.
- Parámetros ausentes.
- Escalado incorrecto.
- Posicionamiento incompleto.
- Funciones de edición ausentes.
- Asociatividad incompleta.
- Referencias externas defectuosas.
- Problemas con capas.
- Problemas con grupos.
- Manipuladores faltantes.
- Funciones disponibles en API pero no en UI.
- Funciones mostradas en UI pero no implementadas.

**Implementar las funciones faltantes correspondientes al alcance**, mediante cambios incrementales y con pruebas.

No declarar una función equivalente a Fusion 360 cuando solo se haya implementado una parte.

Las capacidades adicionales exclusivas de OmniCAD también deberán quedar verificadas.

---

# PARTE XXII — RENDIMIENTO

## 23. OPTIMIZACIÓN

Medir:

- Tiempo de importación.
- Tiempo de previsualización.
- Tiempo de transformación.
- Tiempo de actualización.
- Consumo de RAM.
- Uso de CPU.
- Rendimiento de OpenGL.
- Tiempo de guardado.
- Tiempo de recuperación.
- Tiempo de recálculo.

### PRUEBAS DE CARGA

Utilizar:

- SVG con miles de curvas.
- DXF de gran tamaño.
- STL con cientos de miles de triángulos.
- Ensamblajes STEP complejos.
- Imágenes de alta resolución.
- Escenas con numerosas calcomanías.
- Bibliotecas de fijadores.
- Múltiples referencias derivadas.

Identificar cuellos de botella mediante mediciones.

Optimizar únicamente después de localizar la causa.

Evaluar Rust/PyO3 cuando exista una mejora demostrable y se respeten las reglas de dependencias.

No reemplazar indiscriminadamente los importadores o motores existentes.

---

# PARTE XXIII — API, MCP Y CLI

## 24. CONSISTENCIA

Verificar que las herramientas de inserción estén disponibles coherentemente desde:

- UI.
- API Python.
- MCP.
- CLI.

Comprobar:

- Parámetros.
- Rutas.
- Formatos.
- Unidades.
- Escalas.
- Transformaciones.
- Referencias.
- Validaciones.
- Errores.
- Persistencia.
- Resultados geométricos.

Corregir diferencias.

Actualizar el catálogo único de herramientas y regenerar la documentación correspondiente.

Las operaciones realizadas mediante MCP o CLI deben producir los mismos resultados que las realizadas desde la interfaz, cuando se utilicen los mismos parámetros y contexto.

---

# PARTE XXIV — PRUEBAS COMO USUARIO REAL

## 25. VERIFICACIÓN OBLIGATORIA

Utilizar:

- `pytest`.
- `omnicad-test`.
- `scripts/prueba_ui/`.
- Pruebas de API.
- Pruebas MCP.
- Pruebas de importación.
- Pruebas de persistencia.
- Pruebas de regresión.
- Pruebas de humo.

### PROCEDIMIENTO

Para cada herramienta:

1. Abrir OmniCAD.
2. Entrar al espacio correspondiente.
3. Abrir INSERTAR.
4. Seleccionar la herramienta.
5. Elegir un archivo o entidad.
6. Introducir parámetros.
7. Verificar la vista previa.
8. Posicionar el elemento.
9. Confirmar.
10. Comprobar dimensiones y geometría.
11. Editar.
12. Deshacer.
13. Rehacer.
14. Guardar.
15. Recuperar.

No considerar suficiente una prueba mediante funciones internas.

Las pruebas de interfaz deben simular el uso real sin mover el cursor físico del usuario.

---

# PARTE XXV — PLAN DE EJECUCIÓN

## 26. FASES

### FASE 1 — INVENTARIO

Identificar todas las herramientas, variantes, espacios e implementaciones.

### FASE 2 — INVESTIGACIÓN

Estudiar la documentación oficial de Fusion 360.

### FASE 3 — AUDITORÍA FUNCIONAL

Probar los comandos y registrar diferencias.

### FASE 4 — AUDITORÍA GEOMÉTRICA

Validar curvas, mallas, cuerpos, transformaciones y referencias.

### FASE 5 — AUDITORÍA DE SEGURIDAD

Comprobar la robustez de lectura de archivos externos.

### FASE 6 — REPARACIÓN

Corregir todos los bugs reproducibles del alcance.

### FASE 7 — FUNCIONES FALTANTES

Implementar las opciones necesarias para alcanzar la paridad funcional.

### FASE 8 — INTEGRACIÓN

Verificar todos los espacios, timeline, UI, API, MCP y CLI.

### FASE 9 — RENDIMIENTO

Medir y optimizar.

### FASE 10 — VALIDACIÓN FINAL

Realizar pruebas integrales y comparación contra Fusion 360.

El agente coordinador deberá organizar las fases sin solicitar aprobación entre tareas ordinarias.

Respetar las reglas vigentes del repositorio respecto de permisos, dependencias, sesiones, commits y pruebas completas.

No iniciar una nueva corrección antes de verificar la anterior.

---

# PARTE XXVI — SEGUIMIENTO

## 27. DOCUMENTACIÓN

Actualizar:

- `docs/seguimiento/bugs.md`
- `docs/seguimiento/faltantes.md`
- `docs/seguimiento/mejoras.md`
- `PROJECT_LOG.md`
- `PROJECT_CONTEXT.md`
- Documentación técnica afectada.
- Tests.
- Documentación API/MCP.

Los pendientes resueltos deben cerrarse siguiendo las reglas del repositorio.

No registrar como reparado ningún problema que no tenga pruebas satisfactorias.

---

# PARTE XXVII — INFORME FINAL

## 28. MATRIZ COMPLETA

Crear una matriz por herramienta y espacio:

| Herramienta | Espacio | Opciones auditadas | Bugs encontrados | Bugs corregidos | Faltantes resueltos | Estado |
|---|---|---|---|---|---|---|
| Calcomanía | SÓLIDO / RENDER | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Lienzo | SÓLIDO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| SVG | BOCETO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Vectorizar imagen | BOCETO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| DXF | BOCETO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Malla | MALLA | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| STEP | SÓLIDO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Fijador | ENSAMBLAR | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Duplicar con uniones | ENSAMBLAR | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Componente | ENSAMBLAR | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Derivación | SÓLIDO | Resultado | Cantidad | Cantidad | Cantidad | Estado |

Completar con todas las apariciones y variantes realmente encontradas.

### ESTADOS

- VERIFICADO.
- CORREGIDO.
- MEJORADO.
- PARCIAL.
- PENDIENTE.
- NO VERIFICADO.
- NO APLICA.

### ENTREGABLES

1. Inventario completo.
2. Comparación con Fusion 360.
3. Bugs detectados.
4. Bugs corregidos.
5. Funciones faltantes.
6. Funciones implementadas.
7. Mejoras geométricas.
8. Mejoras de interfaz.
9. Mejoras de importación.
10. Mejoras de seguridad.
11. Mejoras de rendimiento.
12. Pruebas ejecutadas y resultados reales.
13. Evidencias visuales.
14. Archivos de prueba reproducibles.
15. Limitaciones pendientes.
16. Estado final de cada herramienta.

---

# PARTE XXVIII — CRITERIOS DE ACEPTACIÓN

## 29. CONDICIONES PARA FINALIZAR

La auditoría únicamente podrá considerarse completa cuando:

1. Se hayan inventariado todas las herramientas.
2. Se hayan auditado todos los submenús y variantes.
3. Se hayan identificado todos los espacios aplicables.
4. Se haya investigado la documentación oficial de Fusion 360.
5. Las importaciones produzcan geometría válida.
6. Las unidades y escalas sean correctas.
7. Las transformaciones funcionen correctamente.
8. Los SVG/DXF generen perfiles utilizables.
9. La vectorización genere geometría válida dentro de su alcance.
10. Las mallas se importen correctamente.
11. Los modelos STEP conserven geometría y posiciones.
12. Los fijadores tengan dimensiones correctas.
13. Los componentes conserven sus referencias.
14. Las derivaciones sean asociativas cuando corresponda.
15. Las calcomanías y lienzos funcionen.
16. Las herramientas puedan editarse correctamente.
17. El guardado y la recuperación conserven los elementos.
18. Los archivos externos se validen de forma segura.
19. Las herramientas se hayan probado como usuario real.
20. API, MCP y CLI sean coherentes.
21. Los bugs confirmados se hayan corregido o estén documentados como pendientes.
22. Las funciones faltantes estén implementadas o sus limitaciones justificadas.
23. No existan regresiones nuevas sin registrar.
24. La documentación esté actualizada.

**No declarar paridad total con Fusion 360 si quedan funciones incompletas o sin verificar.**

---

# ORDEN FINAL DE EJECUCIÓN

**REALIZÁ UNA AUDITORÍA INTEGRAL DE TODA LA SECCIÓN INSERTAR DE OMNICAD, EN SÓLIDO, SUPERFICIE, PLÁSTICO, CHAPA, MALLA, BOCETO, ENSAMBLAR, RENDERIZAR Y CUALQUIER OTRO ESPACIO DONDE SE UTILICEN ESTAS HERRAMIENTAS.**

Investigá exhaustivamente el comportamiento de Fusion 360 utilizando su documentación oficial.

Auditá todas las variantes, submenús, parámetros y funciones internas.

**INVESTIGÁ → AUDITÁ → REPRODUCÍ → DIAGNOSTICÁ → REPARÁ → COMPLETÁ → OPTIMIZÁ → PROBÁ → VERIFICÁ.**

No quiero únicamente un informe.

**Quiero bugs reparados, opciones faltantes implementadas, importaciones geométricamente correctas, referencias paramétricas estables, interfaz profesional y pruebas reales.**

Prestar especial atención a:

- Fidelidad de importación.
- Unidades y dimensiones.
- Escala y posicionamiento.
- Manipulación de SVG y DXF.
- Calidad de vectorización.
- Compatibilidad de mallas.
- Integridad de STEP.
- Bibliotecas de fijadores.
- Posicionamiento de componentes.
- Duplicaciones con uniones.
- Derivaciones asociativas.
- Calidad de lienzos y calcomanías.
- Seguridad de archivos.
- Persistencia.
- Rendimiento.
- Integración con los demás espacios.

**La prioridad absoluta es que OmniCAD permita insertar, posicionar, editar y reutilizar geometría, imágenes, componentes y referencias con la precisión, estabilidad y facilidad de uso de Fusion 360.**

No declares el trabajo terminado sin comprobar su funcionamiento mediante pruebas geométricas, funcionales y visuales.
```
