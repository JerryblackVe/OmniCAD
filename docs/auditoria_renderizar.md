# Auditoría, reparación y mejora del espacio RENDERIZAR contra Fusion 360

Pedido de Gerardo (2026-11-07): auditar, reparar, completar y optimizar todo el espacio RENDERIZAR (CONFIGURAR,
RENDERIZAR EN EL LIENZO, RENDERIZAR, TERMINAR RENDERIZAR, galería, exportación, API/MCP/CLI) contra el espacio RENDER
de Fusion 360. Primera prioridad: la corrupción gráfica de la interfaz (elementos invertidos y duplicados, visor negro).
Mismo procedimiento que [auditoria_boceto_crear_modificar.md](auditoria_boceto_crear_modificar.md): ejecutan los
agentes, Claude solo como última instancia, y al final todo verde.

**Cuándo:** otro día, el que elija Gerardo (agenda AG-3). ⚠ El prompt nombra «la captura proporcionada», pero la
captura no se guardó con el pedido: al arrancar, pedírsela a Gerardo (o reproducir el defecto entrando a RENDERIZAR).

## Prompt para el agente

Guardado el 2026-11-07. Modelo sugerido: coordina una sesión Claude Opus 5 con esfuerzo alto; ejecutan Sol (OpenCode) y los agentes gratis aprobados, un ítem por corrida y cada uno en su worktree.

```text
# PROMPT MAESTRO — AUDITORÍA, REPARACIÓN Y MEJORA INTEGRAL DEL ESPACIO RENDERIZAR DE OMNICAD

## 1. MISIÓN PRINCIPAL

Actuá como un equipo de ingeniería senior especializado en:

- Arquitectura de aplicaciones CAD profesionales.
- Motores de renderizado 3D.
- Gráficos OpenGL y GLSL.
- Renderizado físicamente basado (PBR).
- Ray tracing y path tracing.
- Iluminación y fotografía virtual.
- Materiales, shaders y texturas.
- Cámaras, composición y óptica.
- Gestión de color y procesamiento de imágenes.
- Interfaces gráficas PySide6/Qt.
- Optimización de CPU, GPU y memoria.
- Automatización de pruebas visuales.
- Geometría B-Rep y OpenCascade.

Tu misión es realizar una **AUDITORÍA EXHAUSTIVA, REPARACIÓN Y MODERNIZACIÓN DEL ESPACIO RENDERIZAR DE OMNICAD**.

El objetivo es alcanzar una experiencia funcional comparable a la del espacio RENDER de Autodesk Fusion 360.

### OBJETIVOS OBLIGATORIOS

1. Auditar absolutamente todas las herramientas de renderizado existentes.
2. Detectar errores funcionales, gráficos y de interfaz.
3. Reparar todos los bugs que puedan resolverse.
4. Investigar e implementar las opciones faltantes respecto de Fusion 360.
5. Mejorar la calidad visual de los renders.
6. Optimizar el rendimiento del motor de renderizado.
7. Corregir problemas de materiales, luces, cámaras y entorno.
8. Garantizar consistencia entre la vista previa y la imagen final.
9. Verificar el funcionamiento real mediante pruebas automatizadas y visuales.
10. Preservar la arquitectura existente de OmniCAD.

**No quiero únicamente un diagnóstico o informe. Quiero correcciones reales, mejoras implementadas y pruebas verificables.**

---

# PARTE I — INSTRUCCIONES DEL PROYECTO

## 2. REGLAS OBLIGATORIAS

Antes de modificar código:

1. Leer `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` y `PROJECT_CONTEXT.md`.
2. Invocar mediante la herramienta Skill `fable-method` y `ponytail`.
3. Utilizar `plan-then-do`, `tool-calling-guard` y `verify-before-commit`.
4. Utilizar `ponytail-audit` cuando corresponda.
5. Invocar `omnicad-test` para probar la interfaz.
6. Ejecutar `ponytail-review` antes de cerrar cada corrección.
7. Respetar todas las normas de arquitectura y Git.
8. No instalar dependencias nuevas sin autorización.
9. No copiar código propietario.
10. No ejecutar `git push`.

Trabajar sobre el código real, no basarse únicamente en documentación o reportes anteriores.

Identificar el estado actual de las implementaciones antes de proponer cambios.

---

# PARTE II — INVESTIGACIÓN DE FUSION 360

## 3. DOCUMENTACIÓN OFICIAL

Utilizar obligatoriamente la documentación oficial de Autodesk Fusion 360 descargada en:

`docs/fusion_docs/`

Consultar especialmente el índice y los artículos del espacio:

`fusion-render`

Utilizar:

`scripts/fusion_docs.py buscar`

`scripts/fusion_docs.py ver`

Investigar también la documentación oficial en Internet cuando sea necesario.

### ELEMENTOS DE FUSION 360 QUE DEBEN INVESTIGARSE

- Render Workspace.
- Appearance.
- Scene Settings.
- Environment Library.
- Positioning.
- Camera.
- In-Canvas Render.
- Render.
- Render Gallery.
- Texture Map Controls.
- Physical Materials, cuando corresponda.
- Render Quality.
- Image Resolution.
- Render Output.
- Local Rendering.
- Cloud Rendering y sus diferencias con el procesamiento local.

Investigar los nombres, opciones, valores predeterminados, diálogos y comportamientos de cada herramienta.

### REGLA FUNDAMENTAL

No asumir que Fusion 360 y OmniCAD tienen las mismas capacidades tecnológicas.

El objetivo es reproducir el comportamiento funcional y la calidad visual de referencia utilizando una implementación independiente.

No depender de servicios propietarios de Autodesk.

Si una función de Fusion 360 utiliza renderizado en la nube, investigar su equivalente local técnicamente viable.

---

# PARTE III — BUGS VISIBLES EN LA CAPTURA

## 4. REPARACIÓN PRIORITARIA DE LA INTERFAZ

La captura proporcionada muestra problemas gráficos importantes en el espacio RENDERIZAR de OmniCAD.

### SÍNTOMAS OBSERVADOS

1. Elementos de interfaz aparecen invertidos verticalmente.
2. Se observan textos y controles visualmente duplicados.
3. Aparecen representaciones del área de herramientas en posiciones incorrectas.
4. El visor presenta una región negra predominante.
5. Se observan elementos de navegación tridimensional en diferentes posiciones.
6. La composición general de la interfaz está visualmente corrompida.

Estos síntomas deben investigarse y reproducirse. La captura por sí sola no permite confirmar la causa técnica.

### INVESTIGACIÓN OBLIGATORIA

Inspeccionar:

- Renderizado de widgets Qt.
- Composición PySide6/OpenGL.
- OpenGL Framebuffers.
- Framebuffer Objects (FBO).
- Texturas intermedias.
- Buffers de color y profundidad.
- Coordenadas de pantalla.
- Inversión del eje Y.
- Conversión entre coordenadas OpenGL y Qt.
- Transformaciones gráficas.
- Escalado por DPI.
- `devicePixelRatio`.
- Viewports.
- Scissor tests.
- Composición de overlays.
- Limpieza de buffers.
- Estados persistentes de OpenGL.
- Recursos compartidos entre render y visor.
- Contextos gráficos.
- Recreación de buffers al redimensionar.
- Actualizaciones parciales y completas.

Verificar si los defectos proceden del visor, de la interfaz Qt, de la composición de imágenes o de la restauración incorrecta de estados gráficos.

### CRITERIOS DE CORRECCIÓN

- Los textos deben verse correctamente orientados.
- No debe existir duplicación visual injustificada.
- Los controles deben aparecer únicamente en sus áreas correspondientes.
- El visor debe representar correctamente la escena.
- El ViewCube debe funcionar y mostrarse correctamente.
- Los paneles y menús no deben corromperse.
- Cambiar entre espacios no debe provocar defectos gráficos.
- Redimensionar o minimizar la ventana no debe alterar el resultado.
- No deben quedar imágenes residuales de fotogramas anteriores.

**No ocultar el problema mediante repintados forzados innecesarios. Identificar y corregir su causa raíz.**

---

# PARTE IV — AUDITORÍA DE TODAS LAS HERRAMIENTAS

## 5. INVENTARIO COMPLETO DEL ESPACIO RENDERIZAR

Auditar todos los menús, submenús, herramientas y opciones disponibles.

La captura muestra los siguientes grupos principales:

1. CONFIGURAR.
2. RENDERIZAR EN EL LIENZO.
3. RENDERIZAR.
4. TERMINAR RENDERIZAR.

También deben revisarse:

- Galería de renders.
- Paneles de propiedades.
- Visor.
- Herramientas contextuales.
- Menús desplegables.
- Menús del botón derecho.
- Configuraciones.
- Opciones de exportación.
- Integración con el navegador de objetos.
- Integración con el espacio DISEÑO.

No limitar la auditoría a los comandos visibles en la captura.

Inspeccionar el código para descubrir todas las funciones existentes, incluidos los comandos ocultos, incompletos o incorrectamente conectados.

---

# PARTE V — CONFIGURAR

## 6. APARIENCIAS Y MATERIALES

Comparar con Appearance de Fusion 360.

Auditar:

- Biblioteca de materiales.
- Categorías.
- Búsqueda.
- Previsualización.
- Asignación de apariencias.
- Material aplicado a un cuerpo.
- Material aplicado a una cara.
- Material aplicado a un componente.
- Herencia de apariencias.
- Modificación de materiales.
- Duplicación.
- Materiales personalizados.
- Persistencia.
- Importación de texturas.
- Selección y arrastre de materiales.

### PROPIEDADES VISUALES

Investigar y comprobar según las capacidades documentadas:

- Color base.
- Metalicidad.
- Rugosidad.
- Brillo.
- Reflectividad.
- Transparencia.
- Opacidad.
- Índice de refracción.
- Emisión.
- Mapas normales.
- Relieve.
- Texturas.
- Escala de textura.
- Rotación.
- Posicionamiento.
- Mapeo UV.
- Anisotropía.
- Propiedades especiales de materiales.

### MATERIALES DE PRUEBA

Crear escenas con:

- Plástico mate.
- Plástico brillante.
- Metal pulido.
- Metal cepillado.
- Aluminio.
- Acero.
- Cromo.
- Vidrio.
- Caucho.
- Madera.
- Materiales translúcidos.

Verificar que cada uno tenga un comportamiento visual coherente.

No considerar correcto un material únicamente porque cambia de color.

Comprobar reflejos, rugosidad, transparencia y respuesta a la iluminación.

---

## 7. CONFIGURACIÓN DE ESCENA

Comparar con Scene Settings de Fusion 360.

Auditar:

- Selección de entorno.
- Fondos.
- Color de fondo.
- Entornos HDRI.
- Posicionamiento del entorno.
- Rotación.
- Intensidad luminosa.
- Exposición.
- Brillo.
- Suelo.
- Sombras.
- Reflejos.
- Visibilidad del entorno.
- Configuración de cámara.
- Opciones adicionales documentadas.

Comprobar que modificar cualquier parámetro produzca un cambio visible y correcto en la escena.

### PRUEBAS

Crear un mismo objeto y renderizarlo con diferentes entornos.

Verificar que:

- La iluminación cambie correctamente.
- Los reflejos respondan al entorno.
- Las sombras sean coherentes.
- Los objetos no aparezcan excesivamente oscuros.
- Los materiales no pierdan sus propiedades.
- La configuración se conserve al guardar.

---

## 8. CÁMARAS Y COMPOSICIÓN

Auditar:

- Cámara perspectiva.
- Cámara ortográfica.
- Distancia.
- Orientación.
- Encuadre.
- Campo de visión.
- Zoom.
- Órbita.
- Desplazamiento.
- Posición.
- Punto de interés.
- Vistas predefinidas.
- Relación de aspecto.
- Cámara activa.
- Persistencia de configuración.

Investigar profundidad de campo y otros controles fotográficos cuando existan en Fusion 360.

Comprobar que los cambios de cámara se reflejen correctamente en el render final.

El resultado no debe presentar recortes inesperados ni deformaciones de perspectiva.

---

# PARTE VI — RENDERIZAR EN EL LIENZO

## 9. AUDITORÍA DEL RENDER INTERACTIVO

Investigar el comportamiento documentado de In-Canvas Render de Fusion 360.

Auditar:

- Activar renderizado.
- Detener renderizado.
- Reiniciar acumulación.
- Cambiar resolución.
- Calidad.
- Actualización progresiva.
- Movimiento de cámara.
- Modificación de materiales.
- Cambio de iluminación.
- Cambio de entorno.
- Actualización tras modificar geometría.

### COMPORTAMIENTO ESPERADO

El usuario debe poder visualizar progresivamente una escena renderizada, según las capacidades del motor.

Si el motor es progresivo, comprobar que la imagen mejore correctamente con nuevas muestras.

Cuando cambia la cámara, geometría, material o iluminación, el resultado anterior no debe contaminar la nueva imagen.

### AUDITORÍA TÉCNICA

Comprobar:

- Buffers de acumulación.
- Reinicios.
- Sincronización.
- Trabajo asíncrono.
- Cancelaciones.
- Uso de CPU/GPU.
- Gestión de memoria.
- Redibujado del visor.
- Tiempo de respuesta.
- Calidad de imagen.
- Integración con OpenGL.

Evitar que el render interactivo congele la ventana.

---

# PARTE VII — MOTOR DE RENDERIZADO

## 10. AUDITORÍA DEL MOTOR ACTUAL

Identificar todos los motores y rutas de render existentes.

Investigar especialmente:

- Renderizado mediante OpenGL.
- Shaders GLSL.
- Renderizado CPU.
- Implementaciones Rust/PyO3.
- Rasterización.
- Iluminación.
- Sombras.
- Reflexiones.
- Transparencia.
- Técnicas PBR.
- Procesamiento de imágenes.

Comprobar si existen diferencias visuales importantes entre los motores disponibles.

### VALIDACIÓN

Con una escena idéntica:

1. Renderizar mediante cada motor disponible.
2. Comparar geometría.
3. Comparar materiales.
4. Comparar iluminación.
5. Comparar sombras.
6. Comparar orientación.
7. Comparar cámara.
8. Comprobar artefactos.
9. Medir rendimiento.
10. Documentar diferencias.

No asumir que dos motores deben generar imágenes idénticas píxel por píxel. Validar que sus resultados sean geométrica y visualmente coherentes dentro de las capacidades de cada implementación.

---

## 11. CALIDAD VISUAL PROFESIONAL

Investigar las capacidades necesarias para mejorar:

- Sombras suaves.
- Sombras de contacto.
- Oclusión ambiental.
- Reflejos.
- Iluminación indirecta.
- Respuesta de materiales.
- Transparencias.
- Antialiasing.
- Ruido.
- Banding.
- Precisión del color.
- Tonemapping.
- Exposición.
- Detalle de superficies.
- Calidad de bordes.
- Calidad de texturas.

Comparar resultados con escenas equivalentes en Fusion 360.

### OBJETIVO

Conseguir imágenes de productos y piezas mecánicas con aspecto profesional.

Los materiales deben verse convincentes y permitir distinguir propiedades como metal, plástico, vidrio y superficies mates o brillantes.

No implementar funciones visuales complejas sin medir primero su coste y verificar su necesidad.

---

# PARTE VIII — RENDER FINAL

## 12. AUDITORÍA DEL COMANDO RENDERIZAR

Comparar con Render de Fusion 360.

Investigar y auditar:

- Configuración de calidad.
- Resolución.
- Relación de aspecto.
- Tamaños personalizados.
- Configuración de imagen.
- Selección de cámara.
- Entorno.
- Motor utilizado.
- Procesamiento.
- Indicador de progreso.
- Cancelación.
- Resultado final.
- Almacenamiento.
- Historial.

### RESOLUCIONES DE PRUEBA

Verificar como mínimo:

- 512 × 512.
- 1024 × 1024.
- 1920 × 1080.
- 1080 × 1920.
- Resoluciones personalizadas compatibles.

Comprobar que las imágenes se exporten con las dimensiones solicitadas y sin deformaciones.

---

## 13. EXPORTACIÓN DE IMÁGENES

Auditar los formatos realmente compatibles y compararlos con Fusion 360.

Investigar:

- PNG.
- JPEG.
- Otros formatos admitidos.
- Transparencia.
- Canal alfa.
- Color de fondo.
- Compresión.
- Calidad.
- Metadatos cuando correspondan.
- Resolución.
- Nombre de archivo.
- Ruta de guardado.

Probar apertura de los archivos exportados en programas externos.

Verificar que la imagen final no contenga:

- Controles del visor.
- ViewCube.
- Paneles.
- Bordes de interfaz.
- Textos superpuestos.
- Imágenes residuales.
- Colores alterados accidentalmente.

**El render final debe contener únicamente la imagen de la escena solicitada.**

---

# PARTE IX — GALERÍA DE RENDERS

## 14. AUDITORÍA DE LA GALERÍA

Revisar:

- Creación de renders.
- Miniaturas.
- Visualización.
- Selección.
- Apertura.
- Exportación.
- Eliminación.
- Persistencia.
- Información de resolución.
- Estado de procesamiento.
- Gestión de archivos.
- Actualización de la interfaz.

Comprobar que cada miniatura represente correctamente el render correspondiente.

Investigar diferencias con Render Gallery de Fusion 360.

No declarar completadas funciones de almacenamiento persistente si la implementación solo conserva datos durante la sesión.

---

# PARTE X — INTEGRACIÓN CON OMNICAD

## 15. GEOMETRÍA Y TOPOLOGÍA

Verificar que el motor represente correctamente:

- Prismas.
- Cilindros.
- Esferas.
- Toroides.
- Engranajes.
- Roscas.
- Empalmes.
- Chaflanes.
- Curvas.
- Superficies.
- Cuerpos de chapa.
- Componentes.
- Ensamblajes.
- Geometría importada.

Prestar atención a:

- Normales.
- Triangulación.
- Mallado.
- Caras invertidas.
- Culling.
- Sombreado.
- Continuidad visual.
- Aristas.
- Superficies curvas.
- Artefactos de z-buffer.
- Geometría ausente.
- Piezas desplazadas.

El render no debe modificar la geometría CAD original.

---

## 16. SINCRONIZACIÓN CON DISEÑO

Verificar el flujo:

1. Crear una pieza en SÓLIDO.
2. Asignar una apariencia.
3. Entrar a RENDERIZAR.
4. Configurar la escena.
5. Generar una imagen.
6. Volver a DISEÑO.
7. Modificar la pieza.
8. Regresar a RENDERIZAR.
9. Actualizar el resultado.
10. Guardar y reabrir el proyecto.

Comprobar que:

- Los materiales se conserven.
- Las cámaras no cambien inesperadamente.
- Las luces y entornos permanezcan configurados.
- La nueva geometría se represente correctamente.
- Los materiales de las caras se mantengan cuando sus referencias sigan siendo válidas.
- Los cambios de escena no alteren el timeline.
- No se creen operaciones geométricas innecesarias.

---

# PARTE XI — AUDITORÍA DE INTERFAZ

## 17. PRUEBAS REALES DE USUARIO

Utilizar `omnicad-test` y `scripts/prueba_ui/`.

Probar:

- Entrada al espacio RENDERIZAR.
- Salida del espacio.
- Menús.
- Submenús.
- Diálogos.
- Materiales.
- Selección de cuerpos.
- Aplicación de apariencias.
- Movimiento de cámara.
- Configuración del entorno.
- Render en el lienzo.
- Render final.
- Galería.
- Exportación.
- Cancelación.
- Deshacer y rehacer cuando corresponda.

### RESOLUCIONES DE VENTANA

Probar:

- 800 × 520.
- 1024 × 640.
- 1366 × 768.
- 1920 × 1080.
- Escalado DPI compatible, incluyendo 100 %, 125 % y 150 %.

Verificar:

- Legibilidad.
- Posicionamiento.
- Ausencia de solapamientos.
- Correcta orientación.
- Ausencia de duplicaciones.
- Correcta distribución de paneles.
- Menús utilizables.
- Vista previa consistente.

Reproducir y corregir especialmente el defecto visual observado en la captura del usuario.

---

# PARTE XII — OPTIMIZACIÓN

## 18. RENDIMIENTO Y CONSUMO DE RECURSOS

Medir:

- Tiempo de inicialización del espacio RENDERIZAR.
- Tiempo de carga de materiales.
- Tiempo de previsualización.
- Tiempo hasta el primer fotograma.
- Tiempo de render final.
- Uso de CPU.
- Uso de GPU.
- Memoria RAM.
- Memoria gráfica, cuando pueda medirse.
- Comportamiento al cancelar.
- Liberación de recursos.
- Rendimiento en escenas complejas.

Probar escenas de:

- Una pieza simple.
- Diez cuerpos.
- Cien cuerpos.
- Ensamblajes complejos.
- Objetos con materiales diferentes.
- Geometría con numerosas caras.
- Texturas de diferentes resoluciones.

### REGLA

Medir antes de optimizar.

Investigar cuellos de botella reales.

Aprovechar las implementaciones Rust existentes cuando corresponda.

No sustituir indiscriminadamente el motor de renderizado.

Si se propone una arquitectura nueva, justificarla mediante pruebas de calidad, rendimiento, compatibilidad y mantenimiento.

No introducir dependencias sin autorización.

---

# PARTE XIII — PRUEBAS VISUALES AUTOMATIZADAS

## 19. ESCENAS PATRÓN

Crear un banco reproducible de escenas que permita evaluar el motor.

### Escena A — Materiales

Esferas y prismas con distintos materiales.

### Escena B — Iluminación

Una pieza con diferentes entornos e intensidades.

### Escena C — Sombras

Objetos apoyados sobre una superficie.

### Escena D — Reflexiones

Metales con diferentes niveles de rugosidad.

### Escena E — Transparencia

Objetos transparentes y opacos superpuestos.

### Escena F — Geometría compleja

Pieza mecánica con agujeros, empalmes, chaflanes y roscas.

### Escena G — Ensamblaje

Múltiples componentes con materiales y posiciones diferentes.

### Escena H — Cámara

Mismo objeto desde distintas perspectivas y relaciones de aspecto.

### Escena I — Interfaz

Entrada y salida del espacio RENDERIZAR, redimensionamiento de ventana y cambios de contexto gráfico.

### Escena J — Exportación

Render final en diferentes resoluciones y formatos.

Cada escena debe contar con:

- Parámetros reproducibles.
- Resultados esperados.
- Verificaciones técnicas.
- Capturas.
- Pruebas de regresión.

Cuando sea útil, emplear métricas de diferencia visual, manteniendo tolerancias adecuadas para variaciones de GPU y controladores.

No aprobar una escena únicamente porque se haya generado un archivo PNG.

---

# PARTE XIV — REPARACIÓN DE BUGS

## 20. CORREGIR TODOS LOS DEFECTOS ENCONTRADOS

**La autorización incluye modificar y reparar las implementaciones afectadas del sistema de renderizado.**

Por cada problema:

1. Reproducir el error.
2. Identificar su causa.
3. Registrar evidencia.
4. Crear una prueba que falle.
5. Corregir el código.
6. Ejecutar la prueba.
7. Comprobar visualmente el resultado.
8. Verificar que no aparezcan regresiones.
9. Ejecutar `ponytail-review`.
10. Registrar el cambio.

No resolver bugs visuales mediante parches que oculten su causa.

No cambiar algoritmos geométricos ajenos al render si no existe evidencia de que sean responsables.

### PRIORIDAD DE REPARACIÓN

**P0 — Críticos:** interfaz corrupta, render inexistente, cierres inesperados, pérdida de datos o bloqueo permanente.

**P1 — Altos:** materiales incorrectos, geometría faltante, cámaras defectuosas, imágenes exportadas incorrectamente.

**P2 — Medios:** opciones incompletas, diferencias funcionales, problemas de previsualización, errores de persistencia no destructivos.

**P3 — Mejoras:** optimización, refinamientos visuales, controles adicionales y experiencia de usuario.

Resolver primero los errores que impidan utilizar normalmente el espacio RENDERIZAR.

---

# PARTE XV — IMPLEMENTACIÓN DE FALTANTES

## 21. COMPLETAR LAS FUNCIONES

Comparar OmniCAD con la documentación oficial de Fusion 360.

Identificar:

- Herramientas faltantes.
- Parámetros ausentes.
- Opciones incompletas.
- Modos no implementados.
- Materiales no soportados.
- Configuraciones de entorno faltantes.
- Problemas de cámara.
- Capacidades de exportación.
- Funciones de galería.
- Diferencias entre render interactivo y final.

Implementar las funcionalidades faltantes que sean técnicamente viables y pertenezcan al alcance.

Realizar la implementación de forma incremental y comprobable.

No declarar que una opción está implementada si solo aparece en el menú y no modifica realmente el resultado.

---

# PARTE XVI — API, MCP Y CLI

## 22. INTEGRACIÓN COMPLETA

Auditar las herramientas existentes de renderizado en:

- Interfaz gráfica.
- API Python.
- MCP.
- CLI.

Comprobar:

- Parámetros.
- Validaciones.
- Aplicación de materiales.
- Configuración de cámara.
- Configuración de iluminación.
- Solicitud de renders.
- Exportación.
- Recuperación de resultados.
- Manejo de errores.
- Persistencia.

Corregir diferencias de comportamiento entre interfaces.

Respetar el catálogo único de herramientas de OmniCAD y actualizar su documentación generada.

---

# PARTE XVII — ORGANIZACIÓN DEL TRABAJO

## 23. EJECUCIÓN POR FASES

### FASE 1 — INVENTARIO

Identificar todos los módulos, motores, herramientas y funciones del espacio RENDERIZAR.

### FASE 2 — INVESTIGACIÓN

Comparar las capacidades actuales con la documentación oficial de Fusion 360.

### FASE 3 — AUDITORÍA DE INTERFAZ

Reproducir y corregir los defectos gráficos de la captura y demás problemas detectados.

### FASE 4 — AUDITORÍA FUNCIONAL

Comprobar materiales, escena, cámara, render en lienzo, render final, galería y exportación.

### FASE 5 — REPARACIÓN

Corregir los errores detectados, uno por uno, con pruebas de regresión.

### FASE 6 — FUNCIONES FALTANTES

Implementar las capacidades necesarias para acercarse a la paridad funcional con Fusion 360.

### FASE 7 — CALIDAD Y RENDIMIENTO

Mejorar la representación visual y optimizar los cuellos de botella demostrados.

### FASE 8 — VALIDACIÓN FINAL

Ejecutar pruebas integrales y comprobar los resultados visuales.

No solicitar aprobaciones entre fases ordinarias.

Respetar las reglas existentes sobre sesiones, permisos, dependencias, verificaciones y commits.

Mantener los cambios separados y verificables.

No iniciar una nueva corrección antes de cerrar correctamente la anterior.

---

# PARTE XVIII — DOCUMENTACIÓN

## 24. ACTUALIZAR EL PROYECTO

Registrar bugs, mejoras y faltantes en:

- `docs/seguimiento/bugs.md`
- `docs/seguimiento/mejoras.md`
- `docs/seguimiento/faltantes.md`

Actualizar:

- `PROJECT_LOG.md`
- `PROJECT_CONTEXT.md`
- Documentación afectada.
- Tests.
- Documentación API/MCP.

Cumplir con las reglas del proyecto para retirar pendientes resueltos.

No registrar como corregido ningún defecto que carezca de evidencia satisfactoria.

---

# PARTE XIX — INFORME FINAL

## 25. MATRIZ DE RESULTADOS

Entregar una tabla que incluya todas las herramientas auditadas:

| Área | Función | Bugs detectados | Bugs corregidos | Faltantes implementados | Estado |
|---|---|---|---|---|---|
| Interfaz | Visor y composición | Resultado | Resultado | Resultado | Estado |
| Materiales | Apariencias | Resultado | Resultado | Resultado | Estado |
| Escena | Iluminación y entorno | Resultado | Resultado | Resultado | Estado |
| Cámara | Configuración | Resultado | Resultado | Resultado | Estado |
| Render en lienzo | Motor interactivo | Resultado | Resultado | Resultado | Estado |
| Render final | Generación de imagen | Resultado | Resultado | Resultado | Estado |
| Galería | Gestión de renders | Resultado | Resultado | Resultado | Estado |
| Exportación | Archivos de imagen | Resultado | Resultado | Resultado | Estado |

Clasificación:

- VERIFICADO.
- CORREGIDO.
- MEJORADO.
- PARCIAL.
- PENDIENTE.
- NO VERIFICADO.

### ENTREGABLES

1. Inventario de herramientas.
2. Comparación con Fusion 360.
3. Informe de defectos.
4. Errores corregidos.
5. Funciones implementadas.
6. Mejoras de calidad visual.
7. Mejoras de rendimiento.
8. Pruebas automatizadas.
9. Evidencias visuales.
10. Resultados de exportación.
11. Limitaciones pendientes.
12. Estado final del espacio RENDERIZAR.

Incluir las salidas reales de los tests y mediciones.

---

# PARTE XX — CRITERIOS DE ACEPTACIÓN

## 26. CONDICIONES PARA FINALIZAR

No considerar completada la tarea hasta comprobar que:

- El espacio RENDERIZAR abre correctamente.
- La interfaz no presenta elementos invertidos, duplicados ni corruptos.
- El visor funciona.
- El ViewCube funciona.
- Todos los menús responden.
- Los materiales se aplican correctamente.
- La iluminación responde a sus parámetros.
- Las cámaras conservan sus configuraciones.
- El render en el lienzo funciona según sus capacidades.
- El render final genera imágenes válidas.
- La exportación respeta resolución y formato.
- La galería funciona correctamente.
- Los datos de render persisten donde corresponda.
- Cambiar entre DISEÑO y RENDERIZAR no genera problemas.
- Las funciones reparadas tienen pruebas de regresión.
- Las herramientas API/MCP/CLI están sincronizadas.
- El rendimiento ha sido evaluado.
- La documentación está actualizada.

No afirmar paridad total con Fusion 360 sin evidencia funcional y visual.

Los problemas no resueltos deben quedar identificados claramente.

---

# ORDEN FINAL DE EJECUCIÓN

**AUDITAR, REPARAR, COMPLETAR Y OPTIMIZAR INTEGRALMENTE EL ESPACIO RENDERIZAR DE OMNICAD.**

La investigación debe abarcar:

- Interfaz completa.
- Visor OpenGL.
- Motor de renderizado.
- Materiales.
- Texturas.
- Iluminación.
- Entornos.
- Cámaras.
- Render en el lienzo.
- Render final.
- Galería.
- Exportación.
- Persistencia.
- Rendimiento.
- API, MCP y CLI.

**PRIMERA PRIORIDAD:** investigar y corregir la corrupción gráfica visible en la captura del usuario.

**SEGUNDA PRIORIDAD:** verificar y reparar el funcionamiento de todas las herramientas existentes.

**TERCERA PRIORIDAD:** implementar las funciones faltantes necesarias para conseguir una experiencia comparable con el espacio RENDER de Autodesk Fusion 360.

**CUARTA PRIORIDAD:** mejorar la calidad visual y el rendimiento del motor, demostrando los resultados mediante escenas reproducibles y pruebas comparativas.

No detenerte después de detectar errores.

**INVESTIGÁ → AUDITÁ → DIAGNOSTICÁ → REPARÁ → IMPLEMENTÁ → OPTIMIZÁ → PROBÁ → VERIFICÁ.**

El resultado esperado es un espacio RENDERIZAR estable, funcional, profesional y preparado para generar imágenes de calidad de los modelos CAD creados en OmniCAD.

No declarar el trabajo terminado hasta presentar evidencia real del funcionamiento de las herramientas y de las correcciones realizadas.
```
