# Organización, agrupación y manipulación de objetos en Boceto

Prompt maestro escrito por Gerardo el 2026-11-04, copiado tal cual. Al terminar se borran este documento y sus dos filas de índice (`docs/README.md` y `docs/seguimiento/README.md`).

## Prompt para el agente

Entregado el 2026-11-05. Modelo sugerido: Opus 5, esfuerzo alto.

```text
PROMPT MAESTRO — OMNICAD
Sistema avanzado de organización, agrupación y manipulación de objetos en Boceto
0. INSTRUCCIONES OBLIGATORIAS
Antes de comenzar, invocá mediante la herramienta Skill:

* `/fable-method`
* `/ponytail`
* `plan-then-do`
* `tool-calling-guard`
* `verify-before-commit`
* `omnicad-test` para las pruebas de interfaz.

Al finalizar, invocá `/ponytail-review` y registrá su resultado real.
Leé íntegramente `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`, `PROJECT_CONTEXT.md`, `PROJECT_LOG.md` y la documentación relevante de OmniCAD.
OBJETIVO GENERAL
Diseñar e implementar un sistema completo de organización y manipulación independiente de geometrías, textos y archivos SVG/DXF dentro del editor de Boceto de OmniCAD.
La implementación debe sentirse nativa, profesional, rápida, intuitiva y totalmente integrada con la arquitectura existente.
NO SE ACEPTA UNA IMPLEMENTACIÓN SUPERFICIAL QUE SOLAMENTE AGREGUE CARPETAS AL NAVEGADOR.
El sistema debe tener una representación real en el modelo de datos, persistencia, operaciones funcionales, integración con el solver, el timeline, el visor y herramientas MCP/CLI.
1. AUDITORÍA INICIAL OBLIGATORIA
Antes de escribir código:

1. Identificá cómo se representan actualmente las geometrías, textos, SVG y DXF.
2. Estudiá el editor de Boceto, su navegador, el visor y los sistemas de selección.
3. Revisá las transformaciones existentes: mover, rotar, escalar, copiar y reflejar.
4. Investigá cómo funcionan las restricciones y el solver.
5. Revisá la detección de perfiles cerrados y las operaciones que consumen esos perfiles.
6. Identificá cómo se guardan y recuperan los documentos `.omnicad`.
7. Revisá el timeline, deshacer y rehacer.
8. Auditá todos los menús contextuales y acciones del clic derecho.
9. Identificá herramientas MCP/CLI existentes que puedan reutilizarse.
10. Revisá los tests actuales para evitar regresiones.

Consultá la documentación local de Fusion 360 en `docs/fusion_docs/` mediante `scripts/fusion_docs.py buscar`, cuando corresponda, y usá otras aplicaciones únicamente como referencia funcional.
No copiar código propietario.
Antes de modificar cualquier módulo, comprobá si existen otros agentes trabajando sobre él.
Elaborá un plan técnico con dependencias, riesgos y criterios de aceptación, y luego ejecutalo por fases hasta completar el alcance.
2. ESTRUCTURA DEL NAVEGADOR
Cuando el usuario entre a editar un Boceto, el navegador debe mostrar una estructura como esta:

```
▼ Boceto1 — En edición
  │
  ├─ ▼ Geometrías (3)
  │    ├─ Rectángulo1
  │    ├─ Círculo1
  │    └─ Línea1
  │
  ├─ ▼ Textos (2)
  │    ├─ HOLA
  │    └─ Nombre de marca
  │
  ├─ ▼ SVG / DXF (2)
  │    ├─ Logo.svg
  │    └─ Diseño.dxf
  │
  └─ ▼ Grupos personalizados
       └─ Composición1
```

Reglas fundamentales:

* Las categorías se generan automáticamente.
* Cada objeto tiene un identificador interno estable.
* Cada objeto puede tener nombre propio.
* Las categorías pueden expandirse y contraerse.
* Los elementos deben admitir búsqueda por nombre.
* El usuario puede crear grupos personalizados.
* Los grupos personalizados pueden contener objetos de diferentes categorías sin perder su clasificación original.
* Un SVG/DXF importado se representa inicialmente como una unidad, no como cientos de curvas sueltas.
* Cuando sea necesario, el usuario puede expandir su contenido.
* Evitá crear miles de nodos visibles automáticamente.
* Los contadores deben reflejar la cantidad real de elementos.

IMPORTANTE: los elementos continúan perteneciendo al mismo boceto. No crear un boceto independiente por cada categoría.
Las agrupaciones deben representar relaciones reales entre objetos y no simples etiquetas visuales.
3. COMPORTAMIENTO DENTRO Y FUERA DE BOCETO
Dentro de Boceto:
Se habilitan las categorías, objetos, grupos y herramientas de organización.
Fuera de Boceto:
El navegador vuelve a su presentación normal.
No deben aparecer las categorías internas de edición.
Los grupos y su contenido siguen existiendo internamente, aunque estén ocultos en el navegador principal.
Al volver a editar el boceto, se recupera la organización guardada.
Este comportamiento no debe afectar otras áreas de OmniCAD.
4. IDENTIDAD E INDEPENDENCIA DE LOS OBJETOS
Cada elemento debe poder manipularse independientemente.
Operaciones requeridas:

* Seleccionar.
* Selección múltiple.
* Mover.
* Rotar.
* Escalar.
* Reflejar.
* Duplicar.
* Renombrar.
* Ocultar y mostrar.
* Bloquear y desbloquear.
* Aislar temporalmente.
* Agrupar y desagrupar.
* Cambiar su pertenencia a un grupo.
* Eliminar.
* Restaurar mediante deshacer.

Un cambio sobre un elemento no debe modificar involuntariamente otros objetos.
Sin embargo, deben respetarse las dependencias y restricciones paramétricas legítimas.
No romper el solver para conseguir independencia visual.
Las transformaciones deben utilizar los mecanismos existentes cuando sea posible.
5. MANIPULACIÓN VISUAL PROFESIONAL
El objetivo es permitir que cualquier usuario manipule objetos sin dificultades.
Implementar o integrar:
A. Selección claramente identificada

* El objeto seleccionado debe diferenciarse visualmente.
* Los grupos deben tener una indicación clara.
* La selección en el navegador debe sincronizarse con el visor.
* La selección en el visor debe sincronizarse con el navegador.

B. Marco de transformación
Para textos y SVG/DXF, usar un marco visual con:

* Desplazamiento.
* Rotación.
* Escalado.
* Punto de pivote.
* Controles identificables.
* Entrada numérica cuando corresponda.

No mostrar cientos de puntos de control innecesarios.
El usuario debe poder manipular el objeto completo sin editar sus nodos internos.
C. Selección múltiple
Permitir transformar varios objetos simultáneamente sin necesidad de crear un grupo permanente.
D. Aislamiento
Permitir trabajar temporalmente sobre un objeto mientras los demás quedan ocultos.
Restaurar correctamente el estado anterior al terminar el aislamiento.
E. Duplicación
Las copias deben tener identidad propia y conservar las propiedades pertinentes.
F. Selección de objetos superpuestos
Cuando varios elementos ocupen la misma zona, permitir elegir cuál seleccionar.
Utilizar prioridad de selección, listado contextual o un mecanismo equivalente que no interfiera con las herramientas actuales.
G. Rendimiento
La manipulación de SVG complejos debe permanecer fluida.
No recalcular toda la geometría innecesariamente en cada movimiento del cursor.
Medir antes de optimizar y reutilizar las soluciones existentes.
6. TEXTO COMO OBJETO INDEPENDIENTE
Un texto no debe perder su condición de texto editable por pertenecer a un grupo.
Debe conservar:

* Contenido.
* Fuente.
* Tamaño.
* Alineación.
* Espaciado.
* Parámetros tipográficos.
* Posición.
* Rotación.
* Escala.
* Texto sobre curva.
* Referencias y propiedades paramétricas.

Al hacer doble clic sobre un texto, debe abrirse el mecanismo de edición correspondiente sin interferir con el movimiento del objeto.
La manipulación visual no debe convertir automáticamente el texto en geometría individual.
7. SVG Y DXF COMO OBJETOS ORGANIZADOS
Los SVG/DXF importados deben conservar una identidad de origen, incluso cuando internamente contengan muchas curvas.
Funciones requeridas:

* Selección del archivo completo.
* Transformación conjunta.
* Duplicación.
* Visibilidad independiente.
* Bloqueo.
* Renombrado.
* Acceso opcional a capas o entidades internas, cuando existan.
* Participación controlada en los perfiles CAD.

Si es posible aprovechar la estructura de capas del archivo importado, conservarla de forma compatible con la arquitectura existente.
No convertir por defecto cada segmento en un elemento independiente del navegador.
No destruir información geométrica ni relaciones necesarias para editar o generar sólidos.
8. PARTICIPACIÓN EN PERFILES CAD
Agregar controles independientes para determinar qué objetos participan en la generación de perfiles utilizables por operaciones CAD.
Ejemplos:

* Incluir un SVG en los perfiles.
* Excluir temporalmente un texto de los perfiles.
* Utilizar geometrías seleccionadas.
* Recuperar la participación anterior.

Diferenciar estrictamente tres conceptos:

1. Visibilidad del objeto.
2. Bloqueo de edición.
3. Participación en la generación de perfiles.

Ocultar un objeto no debe implicar automáticamente su exclusión del modelo geométrico.
Bloquearlo tampoco debe alterar su participación.
Estas propiedades deben persistirse correctamente y respetarse durante la generación de extrusiones y demás operaciones.
No modificar silenciosamente el comportamiento de proyectos existentes.
9. MENÚS CONTEXTUALES — CLIC DERECHO
Realizá una auditoría exhaustiva de los menús contextuales existentes.
No reemplaces indiscriminadamente el menú actual.
Reutilizá acciones existentes y agregá solamente las necesarias.
9.1 Clic derecho sobre un objeto
Propuesta de acciones:

```
Editar
Renombrar
-------------------------
Mover / Rotar
Escalar
Reflejar
Duplicar
-------------------------
Agrupar
Mover a grupo...
-------------------------
Ocultar / Mostrar
Aislar
Bloquear / Desbloquear
Participar en perfiles
-------------------------
Propiedades
Eliminar
```

La disponibilidad de cada acción depende del tipo de objeto.
9.2 Clic derecho sobre un grupo

```
Renombrar grupo
Seleccionar contenido
-------------------------
Mover / Rotar grupo
Escalar grupo
-------------------------
Ocultar / Mostrar contenido
Aislar grupo
Bloquear / Desbloquear
-------------------------
Agregar objetos...
Desagrupar
Eliminar grupo...
```

Definir claramente la diferencia entre eliminar solamente el contenedor y eliminar también sus objetos.
Las operaciones destructivas deben advertirlo cuando corresponda.
9.3 Clic derecho sobre una categoría

```
Crear grupo
Seleccionar contenido
Mostrar todo
Ocultar todo
Aislar categoría
Expandir / Contraer
```

9.4 Clic derecho en un área vacía del navegador

```
Crear grupo
Expandir todo
Contraer todo
Mostrar todos los objetos
Restaurar aislamiento
```

9.5 Clic derecho sobre el visor
Conservar el menú radial y las funciones actuales.
Agregar accesos contextuales únicamente cuando sean compatibles.
Revisar especialmente:

* Clic derecho para finalizar herramientas activas.
* Clic derecho sobre una selección.
* Clic derecho durante una transformación.
* Clic derecho sobre objetos superpuestos.
* Clic derecho sobre espacio vacío.
* Menús contextuales de boceto ya existentes.

REGLA CRÍTICA:
El nuevo sistema no puede apropiarse de eventos del mouse que actualmente utilizan otras herramientas.
Definí y probá la precedencia de eventos.
No crear dos acciones diferentes que compitan por el mismo evento.
10. DISEÑO DE INTERFAZ Y EXPERIENCIA DE USUARIO
La interfaz debe integrarse visualmente con OmniCAD.
Requisitos:

* Íconos claros y diferenciados para geometría, texto, SVG/DXF y grupos.
* Nombres legibles.
* Estados de visibilidad y bloqueo identificables.
* Selección claramente resaltada.
* Indicadores de grupo expandido o contraído.
* Menús organizados por función.
* Acciones destructivas separadas de acciones habituales.
* Tooltips informativos.
* Retroalimentación visual inmediata.
* Estados deshabilitados cuando una acción no aplica.
* Compatibilidad con temas existentes.
* Soporte para ventanas pequeñas.
* Navegación con teclado.
* Sin saturación de botones.

Preferí mostrar acciones frecuentes de forma directa y mantener funciones avanzadas en menús contextuales.
No agregar paneles flotantes innecesarios.
No duplicar controles que ya existen en OmniCAD.
11. ARQUITECTURA Y COMPATIBILIDAD
Implementar el sistema respetando las capas existentes:

* `restricciones/`
* `timeline/`
* `nucleo/`
* `io_archivos/`
* `ui/`
* `api/`

No introducir dependencias de Qt en el núcleo, timeline, restricciones ni entrada/salida.
Los objetos, grupos, identificadores, propiedades y relaciones deben tener representación persistente.
Requisitos estrictos:

1. Mantener compatibilidad con documentos anteriores.
2. No cambiar innecesariamente el formato de datos existente.
3. Crear migraciones cuando sean imprescindibles.
4. Mantener identificadores y referencias estables.
5. Conservar asociaciones paramétricas.
6. Respetar el solver y las restricciones.
7. Integrar deshacer y rehacer.
8. Evitar operaciones parcialmente aplicadas.
9. No alterar el comportamiento de comandos no relacionados.
10. Reutilizar implementaciones existentes.
11. No introducir dependencias nuevas sin autorización.
12. No generar estructuras duplicadas que representen lo mismo.

La arquitectura debe soportar múltiples bocetos, cada uno con su propia organización.
Los grupos no deben convertirse accidentalmente en pasos independientes del timeline.
12. MCP Y CLI — OBLIGATORIO SIN EXCEPCIONES
CADA FUNCIÓN NUEVA O MODIFICADA DEBE QUEDAR ACCESIBLE MEDIANTE MCP Y CLI.
No se acepta implementar una función exclusivamente en la interfaz gráfica.
Todas las operaciones funcionales del nuevo sistema deben incorporarse al catálogo único de herramientas de OmniCAD en `clon/omnicad/api/`.
Incluir capacidades para:

* Consultar categorías y objetos del boceto.
* Obtener identificadores y propiedades.
* Crear grupos.
* Consultar grupos.
* Renombrarlos.
* Modificar su contenido.
* Eliminar o desagrupar.
* Seleccionar objetos.
* Seleccionar múltiples objetos.
* Mover.
* Rotar.
* Escalar.
* Reflejar.
* Duplicar.
* Ocultar y mostrar.
* Bloquear y desbloquear.
* Aislar y restaurar.
* Consultar y modificar participación en perfiles.
* Manipular las propiedades de organización de textos y SVG/DXF.
* Recuperar jerarquías guardadas.

Agregar también las operaciones de consulta necesarias para que un agente pueda comprender el estado real del boceto sin depender de capturas de pantalla.
Reutilizar herramientas existentes cuando ya cubran exactamente el comportamiento necesario.
No crear APIs duplicadas.
Mantener la convención del proyecto: nombres de herramientas y argumentos en inglés, mensajes y descripciones para el usuario en español.
Las operaciones modificadoras deben ser atómicas y compatibles con deshacer/rehacer.
Regenerar la documentación oficial del catálogo MCP/CLI.
Agregar pruebas que demuestren que la interfaz, MCP y CLI ejecutan la misma lógica.
Ninguna funcionalidad se considera terminada si carece de su herramienta MCP/CLI correspondiente.
13. PRUEBAS OBLIGATORIAS DE NO REGRESIÓN
Crear pruebas automatizadas e interactivas que cubran:
A. Organización

* Crear objetos de diferentes categorías.
* Crear grupos.
* Renombrarlos.
* Cambiar la pertenencia de elementos.
* Expandir y contraer.
* Eliminar grupos sin perder geometría cuando esa sea la opción elegida.
* Guardar y recuperar jerarquías.

B. Manipulación

* Movimiento individual.
* Movimiento de grupos.
* Selección múltiple.
* Rotación.
* Escala.
* Duplicación.
* Reflejo.
* Bloqueo.
* Visibilidad.
* Aislamiento.
* Objetos superpuestos.

C. Texto y vectores

* Textos editables después de transformar.
* Textos sobre curva.
* SVG complejos.
* DXF con múltiples entidades.
* Importaciones con capas.
* Transformaciones repetidas sin degradación innecesaria.

D. CAD paramétrico

* Restricciones.
* Solver.
* Detección de perfiles.
* Extrusiones.
* Operaciones que consumen perfiles.
* Edición de pasos anteriores.
* Referencias a geometría.
* Recalcular.
* Deshacer y rehacer.
* Guardar y reabrir.

E. Interfaz
Probar el uso real con mouse y teclado.
Verificar clic izquierdo, doble clic, clic derecho, arrastre, Ctrl, Shift, Escape, Enter y las interacciones existentes.
Comprobar que ninguna herramienta pierda su menú contextual.
F. Compatibilidad
Abrir proyectos antiguos y verificar que su geometría, perfiles y operaciones produzcan el mismo resultado.
Comprobar que las características nuevas no alteren documentos que no las utilizan.
G. MCP/CLI
Probar cada herramienta nueva, sus argumentos válidos, inválidos, referencias perdidas y resultados.
Incluir pruebas de consistencia entre llamadas API, interfaz y persistencia.
Ejecutar las verificaciones del proyecto, incluidas ruff, pytest y prueba de humo cuando corresponda.
Las pruebas pesadas deben ejecutarse secuencialmente conforme a las reglas de OmniCAD.
No declarar éxito sin registrar la salida real de las pruebas.
14. REGISTRO DE AUTORÍA Y TRAZABILIDAD OBLIGATORIO
Esta condición es especialmente importante.
TODO CAMBIO DEBE DEJAR CONSTANCIA DE QUÉ SE HIZO, QUIÉN LO HIZO, POR QUÉ Y CÓMO SE VERIFICÓ.
El registro debe permitir que cualquier agente IA que trabaje posteriormente en OmniCAD pueda comprender la implementación sin reconstruirla desde cero.
Registrar como mínimo:

* Fecha y hora.
* Nombre o identificador del agente responsable.
* Proveedor y modelo de IA, cuando puedan verificarse.
* Agente coordinador, si corresponde.
* Nombre de la tarea o fase.
* Objetivo.
* Decisiones de arquitectura.
* Archivos creados.
* Archivos modificados.
* Funciones agregadas.
* Funciones modificadas.
* Herramientas MCP/CLI incorporadas o reutilizadas.
* Cambios de modelo de datos.
* Cambios de persistencia.
* Compatibilidades garantizadas.
* Pruebas ejecutadas.
* Resultados reales.
* Problemas encontrados.
* Limitaciones pendientes.
* Riesgos conocidos.
* Identificador de commit, solo si existe.
* Estado final: completado, parcial o bloqueado.

No inventar la identidad del modelo ejecutor. Si un dato no está disponible, indicarlo expresamente.
Fuentes de registro:

1. Actualizar `PROJECT_LOG.md` con el resumen verificable de cada fase.
2. Mantener `PROJECT_CONTEXT.md` actualizado con la arquitectura y las decisiones técnicas.
3. Actualizar `docs/seguimiento/` siguiendo sus reglas de fuente única de verdad.
4. Crear o actualizar una especificación técnica del sistema dentro de `docs/`, con enlace desde `docs/README.md`.
5. Registrar las herramientas MCP/CLI en su documentación generada.
6. Dejar documentación de mantenimiento sobre las relaciones entre grupos, objetos, perfiles y solver.

El documento técnico debe explicar cómo agregar nuevos tipos de objetos al sistema en el futuro.
No duplicar listas de pendientes en diferentes documentos.
No incorporar secretos, rutas privadas innecesarias ni información sensible en registros públicos.
No modificar ni borrar registros anteriores para ocultar errores o problemas.
15. CONTROL DE CAMBIOS Y TRABAJO CON OTROS AGENTES

* Revisar el estado del repositorio antes de modificarlo.
* Detectar cambios ajenos sin integrar.
* Respetar archivos asignados a otros agentes.
* No sobrescribir trabajo paralelo.
* No revertir cambios ajenos.
* No eliminar funcionalidades para simplificar la implementación.
* No realizar refactorizaciones globales innecesarias.
* No modificar módulos fuera del alcance salvo dependencia técnica justificada.
* No instalar dependencias sin autorización.
* No ejecutar `git push` ni crear commits sin autorización expresa.
* No incluir archivos privados ni evidencias ignoradas en Git.

Implementar fases pequeñas, verificables y coherentes.
No marcar una fase como completada hasta validar sus pruebas y registrar los cambios.
Si se detecta un conflicto arquitectónico, resolver primero la compatibilidad antes de continuar con funcionalidades dependientes.
16. CRITERIOS DE ACEPTACIÓN FINAL
La tarea solamente estará completa cuando se demuestre lo siguiente:

1. Al entrar en Boceto aparecen las categorías correctas en el navegador.
2. Al salir de Boceto desaparece la jerarquía interna de edición.
3. El usuario puede identificar y seleccionar fácilmente cada objeto.
4. Los textos conservan su editabilidad.
5. Los SVG/DXF pueden manipularse como unidades completas.
6. Los grupos funcionan realmente y persisten.
7. Todas las transformaciones respetan la geometría y las restricciones.
8. Se pueden controlar visibilidad, bloqueo y participación en perfiles de forma independiente.
9. La selección múltiple, duplicación, aislamiento y selección de objetos superpuestos funcionan.
10. Los menús del clic derecho son contextuales, comprensibles y no entran en conflicto.
11. Las operaciones CAD siguen funcionando.
12. Los documentos anteriores conservan su comportamiento.
13. Guardar, reabrir, deshacer y rehacer funcionan correctamente.
14. Todas las funcionalidades están disponibles por MCP/CLI.
15. Las pruebas pasan sin regresiones introducidas por este trabajo.
16. La documentación técnica refleja el resultado real.
17. Quedan registrados los agentes responsables y sus cambios.

17. INFORME FINAL
Al finalizar, entregar un informe estructurado con:
A. Resumen de implementación: qué se agregó realmente.
B. Arquitectura: cómo se relacionan objetos, categorías, grupos, solver, perfiles y timeline.
C. Interfaz: cómo se utilizan las nuevas funciones y cuáles son los menús contextuales definitivos.
D. MCP/CLI: catálogo de herramientas creadas, modificadas o reutilizadas.
E. Compatibilidad: qué pruebas demuestran que no se rompieron herramientas existentes.
F. Verificación: comandos ejecutados y resultados reales.
G. Autoría: registro de cada agente participante, sus responsabilidades y archivos intervenidos.
H. Pendientes: cualquier limitación que no se haya conseguido resolver.
ORDEN FINAL
Implementá el sistema completo, no solamente su diseño o planificación.
Priorizá:

1. Integridad del proyecto.
2. Compatibilidad con funciones existentes.
3. Facilidad de uso.
4. Independencia real de los objetos.
5. Integración paramétrica.
6. Rendimiento.
7. MCP/CLI obligatorio.
8. Pruebas verificables.
9. Trazabilidad y documentación.

PROHIBIDO DAR POR FINALIZADO EL TRABAJO CON FUNCIONES SIMULADAS, BOTONES SIN ACCIÓN, HERRAMIENTAS MCP/CLI AUSENTES, PRUEBAS SIN EJECUTAR O CAMBIOS SIN REGISTRO DE AUTORÍA.
Aplicá las mejoras necesarias sin romper el funcionamiento actual de OmniCAD. Cerrá con `/ponytail-review` y dejá el proyecto documentado para que cualquier otro agente pueda continuar su desarrollo.
```
