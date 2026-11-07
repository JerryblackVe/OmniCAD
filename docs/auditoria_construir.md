# Auditoría, reparación y paridad del sistema CONSTRUIR contra Fusion 360

Pedido de Gerardo (2026-11-07): auditar, reparar y completar contra Fusion 360 las 20 herramientas de CONSTRUIR (SCU,
8 planos, 5 ejes y 6 puntos de construcción) en todos los espacios donde se usan. Mismo procedimiento que
[auditoria_boceto_crear_modificar.md](auditoria_boceto_crear_modificar.md): ejecutan los agentes, Claude solo como
última instancia, y al final todo verde.

**Cuándo:** otro día, el que elija Gerardo. Va 1.ª de 6; orden y reparto en [agenda.md](seguimiento/agenda.md) (sección «Orden y reparto de las auditorías»).

## Prompt para el agente

Guardado el 2026-11-07. Modelo sugerido: coordina una sesión Claude Opus 5 con esfuerzo alto; ejecutan Sol (OpenCode) y los agentes gratis aprobados, un ítem por corrida y cada uno en su worktree.

```text
AJUSTE DEL COORDINADOR (2026-11-08; manda sobre todo lo que sigue)
- Orden de las seis auditorías (de a una; la siguiente arranca cuando la anterior quedó cerrada y commiteada): 1) CONSTRUIR (AG-7), 2) herramientas 3D (AG-2), 3) MODIFICAR (AG-4), 4) INSERTAR (AG-6), 5) ENSAMBLAR (AG-5), 6) RENDERIZAR (AG-3). Cada herramienta tiene UNA sola auditoría dueña. Las demás solo la usan en sus pruebas combinadas: si encuentran un bug en una herramienta ajena, cargan la fila en docs/seguimiento/ y la arreglan solo si la dueña ya pasó (está antes en el orden); si la dueña viene después, dejan la fila para ella.
- Sos la dueña de SCU, planos, ejes y puntos de construcción y del sistema de referencias persistentes (caras, aristas y vértices referenciados). Vas primera: las otras cinco se apoyan en lo que dejes.

# PROMPT MAESTRO — AUDITORÍA, REPARACIÓN Y PARIDAD FUNCIONAL DEL SISTEMA CONSTRUIR DE OMNICAD CON FUSION 360

## 1. MISIÓN PRINCIPAL

Actuá como un equipo senior de ingeniería CAD paramétrica, especializado en:

- Geometría computacional 2D y 3D.
- OpenCascade y geometría B-Rep.
- Sistemas de coordenadas y transformaciones.
- Planos, ejes y puntos de referencia.
- Álgebra lineal y geometría analítica.
- Modelado paramétrico y asociatividad.
- Dependencias geométricas y topológicas.
- Sistemas de referencias CAD.
- Arquitectura Python, PySide6 y OpenGL.
- Automatización y pruebas geométricas.
- Optimización y estabilidad numérica.

Tu misión es realizar una **AUDITORÍA EXHAUSTIVA, REPARACIÓN DE BUGS, IMPLEMENTACIÓN DE FUNCIONES FALTANTES Y OPTIMIZACIÓN INTEGRAL DEL SISTEMA CONSTRUIR DE OMNICAD**.

La referencia funcional obligatoria es Autodesk Fusion 360.

### OBJETIVO FUNDAMENTAL

Conseguir que OmniCAD permita crear, seleccionar, posicionar, modificar y reutilizar sistemas de coordenadas, planos, ejes y puntos de construcción con la precisión y confiabilidad de Fusion 360.

**No quiero únicamente un informe. Quiero que investigues, audites, detectes errores, los repares, completes las opciones faltantes y compruebes que todas las herramientas funcionan correctamente.**

Los elementos de construcción deben ser completamente funcionales dentro del sistema paramétrico.

Una modificación de una referencia debe actualizar correctamente las operaciones dependientes, sin generar desplazamientos inesperados ni romper geometrías válidas.

---

# PARTE I — REGLAS OBLIGATORIAS

## 2. INSTRUCCIONES DEL PROYECTO

Antes de comenzar:

1. Leer `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` y `PROJECT_CONTEXT.md`.
2. Invocar mediante la herramienta Skill `fable-method` y `ponytail`, conforme a las reglas vigentes del repositorio.
3. Utilizar `plan-then-do`, `tool-calling-guard` y `verify-before-commit`.
4. Utilizar `ponytail-audit` cuando corresponda.
5. Invocar `omnicad-test` para las pruebas reales de interfaz.
6. Finalizar cada cambio con `ponytail-review`.
7. Respetar la arquitectura y convenciones del proyecto.
8. No copiar código propietario de Autodesk.
9. No instalar dependencias nuevas sin autorización.
10. No ejecutar `git push`.

Respetar la política de sesiones, commits, memoria y pruebas pesadas del proyecto.

Cada corrección debe verificarse individualmente antes de pasar a la siguiente.

No declarar ninguna herramienta como completamente funcional sin evidencia.

---

# PARTE II — DOCUMENTACIÓN OFICIAL DE FUSION 360

## 3. INVESTIGACIÓN OBLIGATORIA

Utilizar prioritariamente la documentación oficial de Autodesk Fusion 360 almacenada en:

`docs/fusion_docs/`

Consultar especialmente:

- `fusion-model`
- `fusion-sketch`
- `fusion-patch`
- `fusion-sheet-metal`
- `fusion-assemble`
- `fusion-designs`

Buscar las herramientas relacionadas con:

- Construction Geometry.
- Offset Plane.
- Plane at Angle.
- Tangent Plane.
- Midplane.
- Plane Perpendicular at Point.
- Plane Through Two Edges.
- Plane Through Three Points.
- Plane Along Path.
- Axis Through Cylinder/Cone/Torus.
- Axis Perpendicular at Point.
- Axis Through Two Planes.
- Axis Through Two Points.
- Axis Through Edge.
- Point at Vertex.
- Point Through Two Edges.
- Point at Three Planes.
- Point at Center of Circle/Sphere/Torus.
- Point at Edge and Plane.
- Point Along Path.
- Coordinate Systems.

Utilizar el buscador oficial disponible en el proyecto:

`scripts/fusion_docs.py buscar`

`scripts/fusion_docs.py ver`

Consultar los índices de documentación y, cuando corresponda, las imágenes asociadas.

Si la documentación local resulta insuficiente, investigar la documentación oficial actual de Autodesk en Internet.

### REGLA ESTRICTA

Antes de corregir o implementar cualquier herramienta:

1. Identificar su equivalente en Fusion 360.
2. Investigar su funcionamiento.
3. Identificar todas sus opciones.
4. Comprobar sus valores predeterminados.
5. Investigar cómo se seleccionan las referencias.
6. Investigar cómo se posiciona la geometría.
7. Investigar cómo se edita posteriormente.
8. Investigar su comportamiento paramétrico.
9. Comprobar los casos límite documentados.

No inventar opciones ni suponer comportamientos.

Cuando OmniCAD disponga de una función sin equivalente directo, documentar la diferencia y verificar su comportamiento propio.

---

# PARTE III — ALCANCE TRANSVERSAL

## 4. AUDITAR TODOS LOS ESPACIOS

La auditoría deberá cubrir las herramientas de construcción en:

### SÓLIDO

Verificar el uso de planos, ejes y puntos en creación, modificación y posicionamiento de sólidos.

### SUPERFICIE

Comprobar las referencias de construcción utilizadas por operaciones de superficies, revoluciones, barridos, solevaciones y demás herramientas compatibles.

### PLÁSTICO

Verificar las referencias utilizadas en operaciones de diseño plástico, como nervios, redes, fijaciones, apoyos, salientes y geometría dependiente.

### CHAPA

Comprobar las referencias de planos, ejes y puntos utilizadas por operaciones de chapa y su compatibilidad con las reglas de plegado y desarrollo.

### ENSAMBLAR

Comprobar su uso en posicionamiento, componentes, uniones, orígenes y transformaciones.

### BOCETO

Verificar la creación de bocetos sobre planos de construcción y la utilización de ejes, puntos y referencias.

### OTROS ESPACIOS

Incluir cualquier otro espacio donde se utilicen estas herramientas, directamente o mediante funciones compartidas.

**No limitar la auditoría al menú visible. Identificar todas las implementaciones y dependencias reales.**

No duplicar innecesariamente la lógica geométrica entre espacios.

---

# PARTE IV — INVENTARIO COMPLETO DE CONSTRUIR

## 5. HERRAMIENTAS OBLIGATORIAS

La captura del usuario contiene las siguientes herramientas.

### A. Sistemas de coordenadas

1. Sistema de coordenadas de usuario (SCU).

### B. Planos de construcción

2. Plano de desfase.
3. Plano en el ángulo.
4. Plano tangente.
5. Plano medio.
6. Plano perpendicular.
7. Plano a través de dos aristas.
8. Plano a través de tres puntos.
9. Plano en ruta.

### C. Ejes de construcción

10. Eje a través de cilindro/cono/toroide.
11. Eje perpendicular a la cara.
12. Eje a través de dos planos.
13. Eje a través de dos puntos.
14. Eje a través de arista.

### D. Puntos de construcción

15. Punto en vértice.
16. Punto a través de dos aristas.
17. Punto a través de tres planos.
18. Punto en el centro de círculo/esfera/toroide.
19. Punto en arista y plano.
20. Punto a lo largo de la ruta.

**Las 20 herramientas deberán auditarse individualmente.**

Además, investigar:

- Opciones adicionales.
- Submenús.
- Parámetros.
- Modos de selección.
- Comandos contextuales.
- Variantes disponibles.
- Funciones internas relacionadas.
- Herramientas expuestas por API/MCP/CLI.

Si Fusion 360 incorpora variantes documentadas que OmniCAD no ofrece, registrarlas e implementarlas dentro del alcance cuando sea técnicamente viable.

---

# PARTE V — SISTEMAS DE COORDENADAS

## 6. SISTEMA DE COORDENADAS DE USUARIO (SCU)

Auditar exhaustivamente:

- Definición de origen.
- Posición.
- Orientación.
- Eje X.
- Eje Y.
- Eje Z.
- Sistema de coordenadas local.
- Sistema de coordenadas global.
- Selección de referencias.
- Definición mediante caras.
- Definición mediante planos.
- Definición mediante puntos y ejes.
- Transformaciones.
- Rotaciones.
- Edición posterior.
- Visibilidad.
- Persistencia.

### VALIDACIÓN MATEMÁTICA

Verificar:

- Ortogonalidad de ejes.
- Normalización.
- Orientación del sistema.
- Determinante de la matriz de rotación.
- Transformaciones locales/globales.
- Conversión de coordenadas.
- Coherencia con sistemas de mano derecha.

### CASOS DE PRUEBA

1. SCU en el origen global.
2. SCU trasladado.
3. SCU rotado 90°.
4. SCU inclinado arbitrariamente.
5. SCU definido sobre una cara.
6. SCU vinculado a un componente.
7. SCU dentro de un subensamblaje.
8. SCU actualizado tras modificar geometría.

Comprobar que los sistemas de coordenadas no produzcan inversiones inesperadas ni transformaciones duplicadas.

---

# PARTE VI — PLANOS DE CONSTRUCCIÓN

## 7. PLANO DE DESFASE

Comparar con Offset Plane de Fusion 360.

Auditar:

- Selección de plano.
- Selección de cara plana.
- Distancia.
- Dirección.
- Desfase positivo.
- Desfase negativo.
- Desfase cero.
- Manipulador.
- Entrada numérica.
- Expresiones.
- Edición.
- Persistencia.

### VALIDACIÓN

El plano resultante debe ser paralelo a la referencia y estar situado a la distancia geométrica solicitada.

Probar:

- Planos globales.
- Caras inclinadas.
- Caras rotadas.
- Referencias dentro de componentes.
- Valores extremos.
- Cambios posteriores de la referencia.

---

## 8. PLANO EN EL ÁNGULO

Comparar con Plane at Angle.

Auditar:

- Selección del eje de rotación.
- Selección de referencia.
- Ángulo.
- Sentido.
- Inversión.
- Manipulador.
- Entrada de grados.
- Expresiones.
- Edición.
- Persistencia.

### VALIDACIÓN

Calcular la normal del plano resultante y compararla matemáticamente con la rotación solicitada.

Probar:

- 0°.
- 45°.
- 90°.
- 180°.
- Ángulos negativos.
- Ángulos extremos válidos.

Comprobar el comportamiento con aristas inclinadas y ejes de componentes transformados.

---

## 9. PLANO TANGENTE

Comparar con Tangent Plane.

Auditar:

- Selección de superficie.
- Selección de posición.
- Tangencia.
- Orientación.
- Punto de contacto.
- Dirección de normal.
- Edición posterior.

### SUPERFICIES DE PRUEBA

- Cilindro.
- Cono.
- Esfera.
- Toroide.
- Superficie libre compatible.
- Cara curva importada.

### VALIDACIÓN MATEMÁTICA

En el punto de contacto, la normal del plano debe ser paralela a la normal geométrica de la superficie, dentro de la tolerancia establecida.

Verificar que el plano realmente toque la superficie en la posición indicada.

No considerar correcto un plano simplemente porque visualmente parezca tangente.

---

## 10. PLANO MEDIO

Comparar con Midplane.

Auditar:

- Selección de dos planos.
- Selección de dos caras planas.
- Planos paralelos.
- Planos inclinados.
- Planos que se intersectan, según las reglas documentadas.
- Orientación.
- Posición.
- Edición.
- Persistencia.

### VALIDACIÓN

Comprobar que el resultado cumpla la relación geométrica de plano medio definida por Fusion 360 para cada tipo válido de referencia.

En referencias paralelas, verificar equidistancia.

En otras configuraciones admitidas, verificar matemáticamente la bisectriz correspondiente.

Rechazar configuraciones ambiguas o no admitidas con un mensaje claro.

---

## 11. PLANO PERPENDICULAR

Comparar con Plane Perpendicular at Point.

Auditar:

- Selección de curva.
- Selección de arista.
- Punto sobre trayectoria.
- Posicionamiento.
- Normal.
- Tangente de referencia.
- Edición.
- Persistencia.

### VALIDACIÓN

El plano debe ser perpendicular a la tangente de la curva en la posición seleccionada.

Probar:

- Línea recta.
- Arco.
- Círculo.
- Spline.
- Curva espacial.
- Arista de cuerpo.

Comprobar estabilidad en puntos cercanos a extremos y zonas de alta curvatura.

---

## 12. PLANO A TRAVÉS DE DOS ARISTAS

Comparar con Plane Through Two Edges.

Auditar:

- Selección de aristas.
- Orden de selección.
- Aristas paralelas.
- Aristas que se intersectan.
- Aristas coplanares.
- Aristas no coplanares.
- Casos degenerados.
- Edición.

### VALIDACIÓN

Determinar las condiciones geométricas necesarias para que exista un plano válido.

Si no existe un plano que satisfaga las referencias, informar el problema.

No fabricar un resultado arbitrario.

Comprobar que las entidades seleccionadas pertenezcan al plano calculado dentro de las tolerancias correspondientes.

---

## 13. PLANO A TRAVÉS DE TRES PUNTOS

Comparar con Plane Through Three Points.

Auditar:

- Selección de tres puntos.
- Orden.
- Referencias.
- Posición.
- Orientación.
- Normal.
- Edición.
- Persistencia.

### PRUEBAS

- Tres puntos no colineales.
- Tres puntos colineales.
- Puntos coincidentes.
- Puntos muy cercanos.
- Puntos alejados del origen.
- Puntos en componentes distintos.

### VALIDACIÓN

Los tres puntos deben pertenecer al plano resultante.

La normal debe corresponder al producto vectorial de las direcciones definidas, con la orientación prevista.

Rechazar configuraciones degeneradas.

---

## 14. PLANO EN RUTA

Comparar con Plane Along Path.

Auditar:

- Selección de trayectoria.
- Posición sobre ruta.
- Distancia.
- Parámetro normalizado.
- Punto.
- Orientación.
- Normal.
- Tangente.
- Manipulador.
- Edición.
- Persistencia.

### PRUEBAS

- Ruta recta.
- Ruta circular.
- Arco.
- Spline.
- Curva espacial.
- Cadena de aristas.
- Ruta abierta.
- Ruta cerrada.

### VALIDACIÓN

Comprobar que:

- La posición sea correcta.
- El plano cumpla la orientación documentada.
- La tangente se calcule correctamente.
- Los extremos sean estables.
- Modificar la trayectoria actualice la posición cuando corresponda.

---

# PARTE VII — EJES DE CONSTRUCCIÓN

## 15. EJE A TRAVÉS DE CILINDRO/CONO/TOROIDE

Auditar:

- Selección de superficie cilíndrica.
- Selección de superficie cónica.
- Selección de toroide.
- Detección de eje.
- Dirección.
- Posición.
- Orientación.
- Edición.
- Persistencia.

### VALIDACIÓN

El eje debe coincidir con el eje geométrico real de la superficie seleccionada.

Probar:

- Cilindros verticales.
- Cilindros inclinados.
- Conos.
- Toroides.
- Superficies importadas.
- Geometría transformada.

Verificar que no dependa incorrectamente de las coordenadas globales.

---

## 16. EJE PERPENDICULAR A LA CARA

Comparar con Axis Perpendicular at Point.

Auditar:

- Selección de cara.
- Selección de punto.
- Normal geométrica.
- Orientación.
- Posición.
- Edición posterior.

### VALIDACIÓN

El eje debe corresponder a la dirección normal de la superficie en el punto seleccionado.

Probar:

- Cara plana.
- Cara cilíndrica.
- Cara esférica.
- Superficie libre compatible.
- Cara inclinada.

Verificar matemáticamente la perpendicularidad.

---

## 17. EJE A TRAVÉS DE DOS PLANOS

Comparar con Axis Through Two Planes.

Auditar:

- Selección de planos.
- Selección de caras planas.
- Intersección.
- Dirección.
- Posición.
- Edición.
- Persistencia.

### VALIDACIÓN

El eje debe coincidir con la línea de intersección geométrica de los planos.

Probar:

- Planos perpendiculares.
- Planos oblicuos.
- Planos paralelos.
- Planos coincidentes.
- Planos casi paralelos.

Las configuraciones sin intersección única deben manejarse correctamente.

---

## 18. EJE A TRAVÉS DE DOS PUNTOS

Comparar con Axis Through Two Points.

Auditar:

- Selección de puntos.
- Orden de selección.
- Dirección.
- Referencias.
- Edición.
- Persistencia.

### VALIDACIÓN

El eje debe pasar exactamente por ambos puntos dentro de la tolerancia geométrica.

Probar:

- Puntos separados.
- Puntos coincidentes.
- Puntos muy próximos.
- Puntos de distintos componentes.
- Puntos con coordenadas extremas.

Evitar direcciones indefinidas o vectores nulos.

---

## 19. EJE A TRAVÉS DE ARISTA

Comparar con Axis Through Edge.

Auditar:

- Selección de arista.
- Arista lineal.
- Dirección.
- Posición.
- Orientación.
- Edición.
- Persistencia.

Investigar qué tipos de aristas admite Fusion 360.

No asumir que una arista curva puede representar un eje recto si la referencia no lo permite.

Verificar que el eje coincida con la dirección y posición geométrica esperadas.

---

# PARTE VIII — PUNTOS DE CONSTRUCCIÓN

## 20. PUNTO EN VÉRTICE

Auditar:

- Selección de vértice.
- Posición exacta.
- Referencia.
- Transformación.
- Edición.
- Persistencia.

Verificar que el punto coincida con el vértice seleccionado.

Probar vértices de sólidos, superficies, bocetos y geometría importada compatible.

---

## 21. PUNTO A TRAVÉS DE DOS ARISTAS

Comparar con Point Through Two Edges.

Auditar:

- Selección.
- Intersección.
- Prolongación geométrica cuando corresponda.
- Aristas que se cruzan.
- Aristas separadas.
- Aristas coincidentes.
- Casos degenerados.

Comprobar las condiciones de existencia del punto.

No inventar una intersección tridimensional cuando las rectas sean alabeadas.

Investigar el comportamiento exacto de Fusion 360 ante estos casos.

---

## 22. PUNTO A TRAVÉS DE TRES PLANOS

Comparar con Point at Three Planes.

Auditar:

- Selección de planos.
- Intersección tridimensional.
- Posición.
- Edición.
- Persistencia.

### VALIDACIÓN

El punto calculado debe pertenecer simultáneamente a los tres planos.

Probar:

- Intersección única.
- Planos paralelos.
- Planos coincidentes.
- Intersección lineal.
- Configuraciones casi degeneradas.

Verificar el condicionamiento numérico y rechazar resultados no únicos o inestables.

---

## 23. PUNTO EN EL CENTRO DE CÍRCULO/ESFERA/TOROIDE

Comparar con Point at Center of Circle/Sphere/Torus.

Auditar:

- Selección de círculo.
- Selección de arco circular.
- Selección de esfera.
- Selección de toroide.
- Identificación de centro.
- Posición.
- Referencia.
- Edición.
- Persistencia.

### VALIDACIÓN

Calcular el centro geométrico exacto según el tipo de entidad.

No utilizar el centro de la caja envolvente como sustituto general del centro geométrico.

Probar objetos trasladados, rotados y procedentes de archivos STEP.

---

## 24. PUNTO EN ARISTA Y PLANO

Comparar con Point at Edge and Plane.

Auditar:

- Selección de arista.
- Selección de plano.
- Intersección.
- Posición.
- Edición.
- Persistencia.

### PRUEBAS

- Arista perpendicular al plano.
- Arista oblicua.
- Arista paralela.
- Arista contenida en el plano.
- Arista curva.
- Intersección fuera del tramo finito.
- Múltiples intersecciones posibles.

Verificar que el tratamiento coincida con las reglas documentadas de Fusion 360.

Si no existe una solución única admitida, informar claramente el problema.

---

## 25. PUNTO A LO LARGO DE LA RUTA

Comparar con Point Along Path.

Auditar:

- Selección de trayectoria.
- Distancia.
- Fracción de longitud.
- Posición.
- Dirección.
- Parámetro.
- Manipulador.
- Edición.
- Persistencia.

### PRUEBAS

- Línea.
- Arco.
- Círculo.
- Spline.
- Ruta espacial.
- Cadena de aristas.
- Ruta abierta.
- Ruta cerrada.

### VALIDACIÓN

El punto debe estar situado sobre la trayectoria a la distancia o parámetro indicado.

No confundir longitud real de arco con parámetro interno de una spline.

Comprobar el comportamiento cuando cambia la geometría original.

---

# PARTE IX — SISTEMA PARAMÉTRICO Y ASOCIATIVIDAD

## 26. AUDITORÍA DE DEPENDENCIAS

Esta parte es crítica.

Los planos, ejes y puntos de construcción deben funcionar como referencias paramétricas estables.

Comprobar:

- Referencias a caras.
- Referencias a aristas.
- Referencias a vértices.
- Referencias a bocetos.
- Referencias entre planos.
- Referencias entre ejes.
- Referencias entre puntos.
- Referencias a componentes.
- Dependencias del timeline.
- Identificadores estables.
- Recalculo.
- Supresión.
- Reactivación.
- Deshacer.
- Rehacer.
- Persistencia.

### CASO FUNDAMENTAL

1. Crear un sólido.
2. Crear un plano basado en una cara.
3. Crear un boceto sobre ese plano.
4. Crear una extrusión.
5. Modificar el sólido original.
6. Recalcular.

El plano, el boceto y la extrusión deben actualizarse de manera coherente cuando las referencias continúen siendo válidas.

No permitir que el sistema asocie silenciosamente una referencia perdida con una cara, arista o vértice incorrecto.

---

# PARTE X — GEOMETRÍA Y PRECISIÓN

## 27. AUDITORÍA MATEMÁTICA

Revisar las operaciones de:

- Intersección línea-plano.
- Intersección plano-plano.
- Intersección de tres planos.
- Cálculo de normales.
- Cálculo de tangentes.
- Producto vectorial.
- Producto escalar.
- Transformaciones.
- Distancias.
- Rotaciones.
- Parametrización de curvas.
- Geometría analítica de superficies.
- Clasificación de referencias degeneradas.

### TOLERANCIAS

Investigar:

- Tolerancias absolutas.
- Tolerancias relativas.
- Dependencia de escala.
- Precisión de operaciones OCC.
- Condicionamiento numérico.
- Geometría casi paralela.
- Geometría casi coincidente.
- Longitudes cercanas a cero.
- Valores extremos.

No utilizar tolerancias arbitrarias sin justificar su relación con la escala y las convenciones geométricas del proyecto.

**No aceptar geometría incorrecta simplemente porque OpenCascade devuelva un resultado sin excepción.**

---

# PARTE XI — AUDITORÍA DE INTERFAZ

## 28. EXPERIENCIA DE USUARIO COMO FUSION 360

Para cada herramienta comprobar:

- Acceso desde la cinta.
- Apertura del menú.
- Selección del comando.
- Selección de referencias.
- Orden de selección.
- Resaltado.
- Preselección.
- Vista previa.
- Manipuladores.
- Flechas.
- Controles de rotación.
- Entrada numérica.
- Valores predeterminados.
- Inversión.
- Aceptar.
- Cancelar.
- Escape.
- Edición posterior.

### PROBLEMAS A DETECTAR

- Botones que no funcionan.
- Referencias que no pueden seleccionarse.
- Selección de entidades equivocadas.
- Planos mal orientados.
- Ejes desplazados.
- Puntos mal posicionados.
- Manipuladores invertidos.
- Vista previa incorrecta.
- Valores que no se actualizan.
- Errores silenciosos.
- Diálogos incompletos.
- Cambios inesperados al editar.

### VISIBILIDAD

Verificar:

- Mostrar/ocultar planos.
- Mostrar/ocultar ejes.
- Mostrar/ocultar puntos.
- Selección desde el navegador.
- Selección desde el visor.
- Estados visuales.
- Diferenciación respecto de geometría real.

Los elementos de construcción deben ser fáciles de identificar y seleccionar sin interferir innecesariamente con el modelado.

---

# PARTE XII — INTEGRACIÓN CON HERRAMIENTAS CAD

## 29. PRUEBAS CRUZADAS

Comprobar el funcionamiento de las referencias con operaciones reales.

### ESCENARIOS OBLIGATORIOS

1. Plano de desfase → Boceto → Extrusión.
2. Plano en ángulo → Boceto → Revolución.
3. Plano tangente → Boceto → Operación sobre cilindro.
4. Plano medio → Simetría.
5. Plano perpendicular → Barrido.
6. Plano a través de tres puntos → Boceto.
7. Plano en ruta → Sección de trayectoria.
8. Eje de cilindro → Patrón circular.
9. Eje a través de dos puntos → Revolución.
10. Eje a través de dos planos → Simetría o rotación compatible.
11. Punto en centro → Agujero.
12. Punto en vértice → Referencia de construcción.
13. Punto a lo largo de ruta → Patrón basado en puntos.
14. SCU → Transformaciones.
15. Plano de construcción → Herramienta de superficie.
16. Eje de construcción → Componente de ensamblaje.
17. Referencia de construcción → Operación de chapa compatible.
18. Geometría importada STEP → Crear plano/eje/punto.
19. Modificación de referencia → Recalculo completo.
20. Guardar → Cerrar → Reabrir → Editar referencias.

Cuando una combinación no sea compatible con el comportamiento documentado de Fusion 360, comprobar que OmniCAD la rechace correctamente.

---

# PARTE XIII — REPARACIÓN DE BUGS

## 30. CORREGIR TODOS LOS ERRORES CONFIRMADOS

**La auditoría incluye la autorización para reparar todos los bugs encontrados dentro de este alcance.**

Para cada error:

1. Reproducirlo.
2. Registrar evidencia.
3. Identificar su causa raíz.
4. Crear una prueba que falle antes de la corrección.
5. Corregir el código.
6. Ejecutar nuevamente la prueba.
7. Comprobar matemáticamente el resultado.
8. Verificarlo desde la interfaz.
9. Ejecutar pruebas de regresión.
10. Invocar `ponytail-review`.
11. Documentar e integrar.

### PROHIBIDO

- Ocultar errores.
- Ignorar tests fallidos.
- Eliminar tests para obtener resultados verdes.
- Crear geometría aproximada cuando se requiere exactitud.
- Corregir un caso específico rompiendo otros.
- Sustituir referencias perdidas por entidades incorrectas.
- Cambiar resultados esperados sin justificación.
- Declarar herramientas terminadas sin evidencia.

Priorizar la causa estructural frente a parches aislados.

---

# PARTE XIV — FUNCIONES FALTANTES

## 31. COMPLETAR LA PARIDAD CON FUSION 360

Comparar cada herramienta con la documentación oficial.

Identificar:

- Opciones faltantes.
- Variantes ausentes.
- Selecciones incompletas.
- Parámetros no implementados.
- Manipuladores inexistentes.
- Errores de orientación.
- Problemas de asociatividad.
- Edición incompleta.
- Diferencias entre espacios.
- Funciones disponibles en API pero no en UI.
- Funciones visibles sin implementación real.

**Implementar las funcionalidades faltantes que pertenezcan al alcance**, mediante cambios incrementales y verificables.

No habilitar herramientas que todavía carezcan de funcionamiento real.

No declarar paridad completa cuando existan diferencias comprobadas.

---

# PARTE XV — RENDIMIENTO

## 32. OPTIMIZACIÓN

Medir:

- Tiempo de creación.
- Tiempo de vista previa.
- Tiempo de selección.
- Tiempo de recalculo.
- Uso de RAM.
- Uso de CPU.
- Coste de referencias dependientes.
- Actualización de geometría.
- Rendimiento del visor.

### PRUEBAS DE CARGA

Crear modelos con:

- Decenas de planos.
- Cientos de ejes.
- Cientos de puntos.
- Referencias encadenadas.
- Componentes anidados.
- Geometría importada compleja.
- Múltiples operaciones dependientes.

Buscar cálculos redundantes y recálculos innecesarios.

Medir antes de optimizar.

Evaluar Rust/PyO3 únicamente cuando exista un beneficio medible y se respeten las políticas de dependencias.

---

# PARTE XVI — API, MCP Y CLI

## 33. CONSISTENCIA TOTAL

Todas las herramientas y opciones relevantes deben estar disponibles de manera coherente desde:

- Interfaz gráfica.
- API Python.
- MCP.
- CLI.

Auditar:

- Argumentos.
- Selección de referencias.
- Validaciones.
- Coordenadas.
- Unidades.
- Orientaciones.
- Resultados geométricos.
- Errores.
- Persistencia.
- Edición.
- Supresión.
- Recalculo.

Corregir diferencias funcionales.

Actualizar el catálogo único de OmniCAD y regenerar la documentación correspondiente.

---

# PARTE XVII — PRUEBAS AUTOMATIZADAS

## 34. VALIDACIÓN OBLIGATORIA

Utilizar:

- `pytest`.
- `omnicad-test`.
- `scripts/prueba_ui/`.
- Pruebas de API.
- Pruebas MCP.
- Pruebas de persistencia.
- Pruebas de regresión.
- Pruebas de humo.

### PRUEBA COMO USUARIO REAL

Para cada herramienta:

1. Abrir el espacio de trabajo.
2. Abrir CONSTRUIR.
3. Seleccionar el comando.
4. Elegir las referencias en el visor.
5. Introducir parámetros.
6. Comprobar la vista previa.
7. Confirmar.
8. Verificar posición y orientación.
9. Editar el elemento.
10. Cambiar una referencia.
11. Deshacer.
12. Rehacer.
13. Guardar.
14. Reabrir.
15. Comprobar la geometría y el timeline.

No considerar suficiente una prueba realizada únicamente mediante llamadas Python.

No mover el cursor físico del usuario durante las pruebas automatizadas.

---

# PARTE XVIII — PLAN DE EJECUCIÓN

## 35. FASES

### FASE 1 — INVENTARIO

Identificar las 20 herramientas, variantes e implementaciones reales.

### FASE 2 — DOCUMENTACIÓN

Investigar el comportamiento de Fusion 360.

### FASE 3 — AUDITORÍA FUNCIONAL

Probar cada comando y detectar defectos.

### FASE 4 — AUDITORÍA MATEMÁTICA

Validar geometría analítica, transformaciones y tolerancias.

### FASE 5 — AUDITORÍA PARAMÉTRICA

Revisar dependencias, referencias y recalculo.

### FASE 6 — REPARACIÓN

Corregir bugs identificados.

### FASE 7 — FUNCIONES FALTANTES

Implementar las opciones ausentes del alcance.

### FASE 8 — INTEGRACIÓN

Verificar todos los espacios, el timeline, API, MCP y CLI.

### FASE 9 — OPTIMIZACIÓN

Medir y corregir cuellos de botella.

### FASE 10 — VALIDACIÓN FINAL

Comparar con Fusion 360 y ejecutar las verificaciones correspondientes.

El agente coordinador deberá gestionar las fases sin solicitar aprobaciones entre tareas ordinarias.

Respetar las reglas del repositorio sobre permisos, dependencias, sesiones, integración y pruebas completas.

No iniciar una nueva corrección antes de verificar la anterior.

---

# PARTE XIX — DOCUMENTACIÓN

## 36. SEGUIMIENTO

Actualizar:

- `docs/seguimiento/bugs.md`
- `docs/seguimiento/faltantes.md`
- `docs/seguimiento/mejoras.md`
- `PROJECT_LOG.md`
- `PROJECT_CONTEXT.md`
- Documentación técnica afectada.
- Tests automatizados.
- Documentación API/MCP.

Respetar la fuente única de pendientes del proyecto.

Documentar cada corrección con evidencia.

No declarar resueltos problemas que no hayan superado las pruebas.

---

# PARTE XX — INFORME FINAL

## 37. MATRIZ OBLIGATORIA

Entregar una matriz de todas las herramientas y espacios:

| Herramienta | Espacio | Variantes | Bugs encontrados | Bugs corregidos | Faltantes resueltos | Estado |
|---|---|---|---|---|---|---|
| SCU | SÓLIDO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Plano de desfase | PLÁSTICO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Plano tangente | SUPERFICIE | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Eje por cilindro | SÓLIDO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Punto en centro | CHAPA | Resultado | Cantidad | Cantidad | Cantidad | Estado |

Completar con todas las herramientas y apariciones reales.

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
7. Mejoras matemáticas.
8. Mejoras de interfaz.
9. Mejoras paramétricas.
10. Mejoras de rendimiento.
11. Pruebas ejecutadas.
12. Evidencias visuales.
13. Casos geométricos reproducibles.
14. Limitaciones pendientes.
15. Estado final del sistema CONSTRUIR.

---

# PARTE XXI — CRITERIOS DE ACEPTACIÓN

## 38. CONDICIONES PARA FINALIZAR

La auditoría solamente podrá considerarse completa cuando:

1. Se hayan inventariado todas las herramientas.
2. Se hayan investigado todas las variantes.
3. Se hayan identificado todos los espacios aplicables.
4. Se haya consultado la documentación oficial de Fusion 360.
5. Los sistemas de coordenadas sean matemáticamente correctos.
6. Los planos tengan posiciones y orientaciones correctas.
7. Los ejes coincidan con sus referencias.
8. Los puntos estén correctamente calculados.
9. Las tolerancias geométricas estén justificadas.
10. Las referencias sean estables.
11. La geometría dependiente se actualice correctamente.
12. El timeline recalcule sin errores.
13. Las herramientas funcionen desde la interfaz.
14. Los manipuladores respondan correctamente.
15. El guardado y recuperación conserven las referencias.
16. API, MCP y CLI sean consistentes.
17. Los bugs confirmados se hayan corregido o estén documentados como pendientes.
18. Las funciones faltantes estén implementadas o sus limitaciones justificadas.
19. No existan regresiones nuevas sin registrar.
20. La documentación esté actualizada.

**No declarar paridad completa con Fusion 360 sin evidencia suficiente.**

---

# ORDEN FINAL DE EJECUCIÓN

**REALIZÁ UNA AUDITORÍA INTEGRAL DE TODO EL SISTEMA CONSTRUIR DE OMNICAD, EN SÓLIDO, SUPERFICIE, PLÁSTICO, CHAPA Y TODOS LOS DEMÁS ESPACIOS DONDE SE UTILICEN SUS HERRAMIENTAS.**

Investigá exhaustivamente el comportamiento de Fusion 360 mediante su documentación oficial.

Auditá las 20 herramientas de la captura, todas sus variantes, parámetros, referencias y funciones internas.

**INVESTIGÁ → AUDITÁ → REPRODUCÍ → DIAGNOSTICÁ → REPARÁ → COMPLETÁ → OPTIMIZÁ → PROBÁ → VERIFICÁ.**

No quiero únicamente un informe.

**Quiero bugs reparados, opciones faltantes implementadas, geometría matemáticamente correcta, referencias paramétricas estables, interfaz profesional y pruebas reales.**

Prestar especial atención a:

- Sistemas de coordenadas.
- Planos de construcción.
- Ejes de referencia.
- Puntos de construcción.
- Precisión geométrica.
- Transformaciones.
- Referencias entre componentes.
- Asociatividad.
- Actualización del timeline.
- Selección de geometría.
- Manipuladores.
- Persistencia.
- Rendimiento.
- Integración con operaciones CAD.

**La prioridad absoluta es que OmniCAD disponga de un sistema de geometría de construcción preciso, robusto, totalmente paramétrico y funcionalmente comparable con Autodesk Fusion 360.**

No declares el trabajo terminado sin demostrar que cada herramienta funciona correctamente mediante pruebas matemáticas, geométricas, paramétricas y visuales.
```
