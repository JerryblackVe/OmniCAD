# Auditoría y reparación de CREAR y MODIFICAR del boceto

Pedido de Gerardo (2026-11-06): auditar, reparar y completar todos los comandos de los menús CREAR y MODIFICAR del
entorno BOCETO contra Fusion 360 y SOLIDWORKS, con el mismo procedimiento que `auditoria_restricciones.md`: ejecutan
los agentes (Sol, Qwen, DeepSeek, GLM 5.3), Claude solo como última instancia, y al final todo verde.

**Orden:** arranca cuando cierre la auditoría de restricciones. Las dos tocan el mismo código del boceto
(`clon/omnicad/restricciones/`, `ui/boceto*`) y Recortar, Partir, Empalme y Desfase dependen de cómo quede el solver.

## Prompt para el agente

Entregado el 2026-11-06. Modelo sugerido: coordina una sesión Claude Opus 5 con esfuerzo alto; ejecutan Sol (OpenCode),
Qwen3.8-Flash (Qoder), DeepSeek v4.1 Flash y GLM 5.3 (CodeBuddy), un ítem por corrida y cada uno en su worktree.

```text
PROMPT MAESTRO — AUDITORÍA Y REPARACIÓN INTEGRAL DE CREAR Y MODIFICAR EN BOCETOS DE OMNICAD

1. MISIÓN PRINCIPAL
Actuá como un equipo de ingeniería CAD de nivel senior, especializado en arquitectura de software CAD paramétrico,
geometría computacional 2D y 3D, modelado geométrico y topología, OpenCascade, sistemas de bocetos paramétricos,
interacción gráfica y experiencia de usuario CAD, algoritmos geométricos y estabilidad numérica, automatización de
pruebas y detección de errores, y optimización de rendimiento.
Tu misión es realizar una auditoría funcional, geométrica, matemática y técnica de TODOS los comandos de los menús CREAR
y MODIFICAR del entorno BOCETO de OmniCAD. Debe incluir la identificación de defectos, la corrección de todos los errores
que puedas resolver, la implementación de funcionalidades incompletas y la optimización del comportamiento general.
La referencia de calidad y comportamiento serán Autodesk Fusion 360 y SOLIDWORKS. El objetivo no es imitar visualmente
estos programas, sino conseguir que las herramientas de OmniCAD tengan un comportamiento funcional equivalente, estable,
preciso y profesional. No entregues únicamente diagnósticos: ejecutá las correcciones y comprobá sus resultados.

2. INSTRUCCIONES DEL PROYECTO
1. Leer AGENTS.md, CLAUDE.md, CLAUDE.local.md y PROJECT_CONTEXT.md.
2. Invocar las skills fable-method y ponytail mediante la herramienta Skill.
3. Utilizar plan-then-do, tool-calling-guard y verify-before-commit.
4. Utilizar ponytail-audit para el análisis técnico cuando corresponda.
5. Invocar omnicad-test para las pruebas de interacción real.
6. Invocar ponytail-review antes de cerrar cada corrección.
7. Respetar todas las normas de arquitectura, desarrollo, tests, documentación y Git del proyecto.
No instalar nuevas dependencias sin autorización. No copiar código propietario de Fusion 360 o SOLIDWORKS. No ejecutar
git push. Seguir la política de commits del coordinador y verificar cada corrección antes de comenzar la siguiente.

3. INVESTIGACIÓN DE LOS PROGRAMAS DE REFERENCIA
Autodesk Fusion 360: consultar obligatoriamente docs/fusion_docs/, especialmente docs/fusion_docs/indice/fusion-sketch.md,
con scripts/fusion_docs.py buscar y ver. Revisar también las capturas y análisis de referencia del proyecto.
SOLIDWORKS: investigar en su documentación oficial el comportamiento de las herramientas equivalentes de Sketch.
Comparar opciones y parámetros, valores predeterminados, selección de entidades, modos de creación, interacción con el
mouse, vista previa, modificación y edición posterior, comportamiento geométrico, restricciones generadas
automáticamente, errores y validaciones, y resultados ante geometrías complejas.
No asumir que dos herramientas son equivalentes solo porque tienen nombres similares. Documentar las diferencias reales y
seleccionar el comportamiento más consistente para OmniCAD, priorizando Fusion 360 cuando corresponda.

PARTE I — AUDITORÍA DEL MENÚ CREAR
4. INVENTARIO COMPLETO
Auditar individualmente: 1. Línea. 2. Línea de punto medio. 3. Rectángulo y todas sus variantes. 4. Círculo y todas sus
variantes. 5. Arco y todas sus variantes. 6. Polígono y todas sus variantes. 7. Elipse. 8. Ranura y todas sus variantes.
9. Spline y todas sus variantes. 10. Curva cónica. 11. Punto. 12. Texto. 13. Simetría. 14. Patrón circular. 15. Patrón
rectangular. 16. Editar patrón. 17. Proyectar/Incluir y todas sus variantes. 18. Cota de boceto. 19. Espiral.
Obligatorio: inspeccionar todos los submenús desplegables y registrar cada herramienta disponible, sin limitarse a los
nombres visibles en las capturas. Comparar el inventario con la documentación oficial. Identificar comandos inexistentes,
opciones ausentes, comandos incompletos, elementos deshabilitados y funciones que muestran una interfaz pero no ejecutan
correctamente su operación.

5. AUDITORÍA DE HERRAMIENTAS DE CREACIÓN (cada comando y variante)
A. Funcionamiento geométrico: geometría matemáticamente correcta; posiciones y dimensiones iguales a las entradas;
puntos de construcción correctos; centros, extremos, radios y ángulos bien calculados; curvas continuas cuando
corresponda; sin segmentos duplicados o degenerados inesperados; perfiles cerrados detectados; geometría editable y con
identidad paramétrica.
B. Interacción con el usuario: inicio de herramienta, primer clic, clics siguientes, movimiento del cursor, vista previa
dinámica, entrada por teclado, cambio de opciones con el comando activo, Enter, Escape, clic derecho cuando corresponda,
repetición, cambio de herramienta, selección, edición y eliminación del resultado. Al cancelar no debe quedar geometría
fantasma, operaciones incompletas ni estados internos activos.
C. Parámetros: positivos, negativos cuando sean válidos, cero, extremadamente pequeños, extremadamente grandes, unidades,
expresiones, parámetros vinculados, campos vacíos, valores inválidos, cambios durante la vista previa. Los errores se
comunican claramente sin corromper el boceto.

6. CASOS ESPECÍFICOS DE CREACIÓN
Líneas: conectadas, independientes, horizontales, verticales, diagonales, cadenas abiertas y cerradas, entrada precisa
de longitud y ángulo, líneas de construcción y línea de punto medio.
Rectángulos: todas las variantes, puntos de referencia, dimensiones, orientación, edición y restricciones generadas.
Círculos y arcos: centros, radios, diámetros, puntos de paso, sentidos de giro, arcos completos o degenerados y
tangencias.
Polígonos: número de lados, centros, orientación, inscritos o circunscritos y edición de parámetros.
Elipses, ranuras, splines y curvas cónicas: continuidad geométrica, control de curvatura, puntos y manipuladores,
tangencias, extremos, edición posterior, estabilidad bajo transformaciones, conversión y generación de perfiles.
Texto: conserva su comportamiento como objeto lógico editable sin exponer cada segmento vectorial; edición, fuente,
escala, rotación, posición, perfiles, contornos y generación de sólidos.
Simetría y patrones: selección, ejes, centros y direcciones, cantidad de instancias, separación y distribución,
previsualización, edición posterior, asociatividad, persistencia, restricciones e integridad de las copias. Editar patrón
modifica correctamente el patrón original sin resultados inconsistentes.
Proyectar/Incluir: todas las variantes; referencias a geometría 3D, aristas, cuerpos y bocetos; asociatividad,
actualización del origen y referencias perdidas.
Cotas de boceto: creación, posicionamiento, edición, expresiones, referencias y actualización geométrica.
Espiral: parámetros geométricos, orientación, número de vueltas, extremos, continuidad, edición y uso posterior.

PARTE II — AUDITORÍA DEL MENÚ MODIFICAR
7. INVENTARIO COMPLETO
1. Empalme. 2. Chaflán y todas sus variantes. 3. Curva de fusión. 4. Desfase. 5. Soltar desfase. 6. Recortar.
7. Alargar. 8. Partir. 9. Escala del boceto. 10. Mover/copiar. 11. Cambiar parámetros. Inspeccionar también todas las
opciones secundarias, submenús y herramientas relacionadas.

8. AUDITORÍA FUNCIONAL DE MODIFICAR
Empalme: líneas que se intersectan y separadas, ángulos agudos y obtusos, radios pequeños y grandes, curvas y arcos
compatibles, radio imposible, modificación posterior, continuidad y tangencia, geometría original, perfiles cerrados. No
permitir empalmes aparentemente correctos que generen geometría inválida.
Chaflán: todas las variantes; distancias, ángulos, orientación, recorte y prolongación, geometrías límite y edición.
Curva de fusión: continuidad posicional y tangencial y, si está implementada, de curvatura; puntos de conexión,
manipuladores, entidades originales y estabilidad durante la edición.
Desfase y Soltar desfase: ambos lados, líneas abiertas, perfiles cerrados, círculos y arcos, splines, curvas combinadas,
distancias positivas y negativas, autointersecciones, esquinas, asociatividad, eliminación y edición, liberación correcta
con Soltar desfase. El desfase no debe generar silenciosamente perfiles inválidos.
Recortar: líneas, arcos, círculos, splines, intersecciones múltiples, entidades coincidentes, extremos próximos,
elementos cerrados, geometría con restricciones. Se elimina únicamente la sección esperada.
Alargar: extensión hasta el límite correcto; intersecciones reales y virtuales, múltiples candidatos, curvas,
restricciones existentes y casos sin intersección válida.
Partir: división en puntos y cruces válidos, preservación de la geometría, nuevas entidades, referencias, restricciones y
perfiles resultantes.
Escala del boceto: punto base, factor, escalado uniforme, valores límite, vista previa, restricciones, cotas, perfiles
cerrados, texto y vectores, edición posterior; dimensiones y geometría responden de forma consistente.
Mover/copiar: traslación, rotación, copia, punto base, entrada numérica, mouse, selección múltiple, geometría parcial y
totalmente restringida, objetos agrupados, texto, SVG/DXF, conservación de perfiles. No modifica entidades no
seleccionadas salvo los ajustes de sus relaciones paramétricas.
Cambiar parámetros: edición de valores, actualización de geometría, expresiones, dependencias, referencias, parámetros
compartidos, detección de ciclos, errores de evaluación, recálculo del boceto y del timeline, persistencia al guardar.

PARTE III — AUDITORÍA TRANSVERSAL
9. INTEGRACIÓN CON LAS RESTRICCIONES
Restricciones automáticas durante la creación, conservación de relaciones al modificar, actualización del solver, grados
de libertad, restricciones incompatibles, relaciones perdidas, cambios de topología, cotas asociadas, geometría fijada y
parcialmente restringida. Recortar, Partir, Empalme y Desfase cambian la topología: sus referencias y restricciones se
actualizan o se notifica la relación que ya no se puede conservar. No ocultar ni eliminar conflictos silenciosamente.

10. AUDITORÍA DE LA INTERFAZ
Menús y submenús, activación de herramientas, íconos y etiquetas, atajos, selección, preselección y resaltado, vista
previa, snap y ayudas, manipuladores, cuadros de valores, cursor y estado activo, Aceptar y Cancelar, mensajes de error,
deshacer y rehacer, actualización del visor, rendimiento durante el arrastre. Todos los botones ejecutan realmente su
comando. Detectar comandos que no hacen nada, ejecutan otra acción, se bloquean, dejan herramientas activas al
cancelar, dan resultados distintos según el modo de selección o muestran una vista previa distinta del resultado.
Corregir cualquier problema confirmado.

11. AUDITORÍA DE PERFILES Y TOPOLOGÍA
Los perfiles resultantes se prueban con Extrusión, Revolución, Barrido cuando corresponda y operaciones posteriores del
timeline. Detectar perfiles abiertos involuntariamente, intersecciones no deseadas, segmentos superpuestos, curvas
duplicadas, contornos degenerados, agujeros mal clasificados, pérdida de referencias y geometría que parece cerrada pero
no lo está matemáticamente. Corregir la causa de cada problema.

12. OBJETOS VECTORIALES Y TEXTO
OmniCAD utiliza SVG, DXF y textos como objetos lógicos para facilitar su manipulación. Las modificaciones a las
herramientas de boceto no deben perjudicar este sistema. Auditar especialmente: selección de objetos completos, mover,
rotar, escalar, copiar, agrupar, editar transformaciones, preservar contornos, generar perfiles para sólidos, deshacer y
rehacer. Respetar las diferencias entre editar una entidad geométrica de boceto y transformar un objeto vectorial
completo. No convertir innecesariamente los objetos en cientos de entidades seleccionables.

13. PERSISTENCIA Y PARAMETRIZACIÓN
Probar el ciclo completo: 1. crear geometría; 2. modificarla; 3. aplicar restricciones y cotas; 4. crear una operación
3D; 5. guardar el proyecto; 6. cerrar OmniCAD; 7. abrir nuevamente; 8. editar el boceto original; 9. modificar un
parámetro; 10. recalcular el diseño. El resultado debe conservar las relaciones paramétricas y la geometría esperada.
Incluir proyectos antiguos compatibles y documentos con varios pasos en el timeline.

PARTE IV — DETECCIÓN Y CORRECCIÓN
14. BUSCAR ERRORES SISTEMÁTICAMENTE
Para CADA comando y variante, pruebas funcionales, geométricas, matemáticas, de interfaz, de integración, de regresión,
de persistencia y de rendimiento cuando corresponda. No limitarse al caso más sencillo. Incluir combinaciones:
Rectángulo → Empalme → Desfase → Recortar; Círculo → Patrón circular → Partir; Línea → Arco tangente → Alargar;
Polígono → Escalar → Mover → Extruir; Texto → Mover/copiar → Escalar → Extruir; Spline → Desfase → Recortar → Extruir;
Proyección de aristas → Modificación → Cambio del sólido original; Patrón rectangular → Editar patrón → Cambiar
parámetros. Crear también casos adversariales y límites numéricos.

15. CORREGIR TODOS LOS BUGS CONFIRMADOS (obligatorio)
El agente no debe detenerse después de detectar los problemas: debe repararlos. Para cada defecto: 1. reproducirlo;
2. registrar evidencia; 3. identificar la causa raíz; 4. crear un test que demuestre el error; 5. corregir el código;
6. ejecutar nuevamente el test; 7. comprobar el resultado geométrico; 8. verificar el comportamiento desde la interfaz;
9. ejecutar pruebas de regresión; 10. revisar con ponytail-review; 11. registrar el arreglo e integrarlo.
Evitar soluciones temporales, parches frágiles o tratamientos especiales que solo funcionan para el ejemplo probado. Si
dos herramientas comparten una causa raíz, corregirla en la capa apropiada sin duplicar código. Completar opciones y
comportamientos faltantes del alcance auditado. Si una corrección no puede resolverse de forma segura, documentar la
causa, las pruebas efectuadas y el bloqueo real; no declararla finalizada.

16. RENDIMIENTO Y ESTABILIDAD
Medir con bocetos pequeños, medianos y de cientos de entidades, geometría importada, patrones con muchas instancias,
splines complejas, recorte y desfase, y bocetos con muchas restricciones. Investigar congelamientos de interfaz, cálculos
redundantes y actualizaciones excesivas. Medir primero y optimizar después. Rust/PyO3 solo con un cuello de botella
comprobado y una mejora medible. Evitar regresiones en memoria y tiempos de respuesta.

17. PRUEBAS REALES OBLIGATORIAS
Usar el sistema de pruebas existente, omnicad-test, pytest, scripts/prueba_ui/ y las herramientas MCP/CLI. Cada
herramienta se prueba como la usaría una persona: clic en CREAR o MODIFICAR, apertura de submenús, selección del
comando, clics en el visor, movimiento y arrastre, introducción de valores, confirmación, edición posterior,
cancelación, deshacer y rehacer, guardar y recuperar. Las pruebas por Python o MCP no sustituyen las de interfaz.
Verificar con valores numéricos y capturas. No mover el cursor físico del usuario.

18. API, MCP Y CLI
Todos los comandos y opciones relevantes disponibles de forma coherente en UI, API, MCP y CLI, con resultados
equivalentes. Corregir diferencias de parámetros, valores predeterminados y resultados. Actualizar herramientas y
documentación generada según las reglas de OmniCAD.

PARTE V — GESTIÓN Y RESULTADOS
19. PLAN DE EJECUCIÓN
Fase 1 Inventario completo; Fase 2 Investigación (Fusion 360 y SOLIDWORKS); Fase 3 Auditoría; Fase 4 Reparación;
Fase 5 Integración (solver, geometría, perfiles, UI, API, MCP, CLI, timeline y archivos); Fase 6 Validación; Fase 7
Revisión final. No solicitar aprobación entre fases ordinarias. Cada problema se resuelve, prueba y cierra
individualmente antes de avanzar. Mantener al día docs/seguimiento/, PROJECT_LOG.md, PROJECT_CONTEXT.md, documentación
y tests afectados.

20. MATRIZ DE VERIFICACIÓN FINAL
| Herramienta | Variantes | Pruebas | Bugs encontrados | Bugs corregidos | Estado |, con TODAS las herramientas
auditadas. Clasificar VERIFICADO, CORREGIDO, PARCIAL, PENDIENTE o NO VERIFICADO. No marcar como completamente funcional
un comando que solo tenga pruebas unitarias y nunca se haya probado desde la interfaz.

21. CRITERIOS PARA CONSIDERAR COMPLETADA LA TAREA
1. Todos los comandos y variantes inventariados. 2. Cobertura de pruebas adecuada en cada herramienta. 3. Bugs
corregidos o identificados explícitamente como pendientes. 4. Geometría válida. 5. Comandos funcionando desde la
interfaz. 6. Las modificaciones no destruyen indebidamente restricciones o referencias. 7. Perfiles utilizables para
modelado 3D. 8. Guardado y recálculo consistentes. 9. UI, API, MCP y CLI sincronizados. 10. Sin regresiones nuevas sin
registrar. 11. Resultados contrastados con la referencia CAD. 12. Documentación y tests actualizados. No afirmar paridad
completa con Fusion 360 o SOLIDWORKS si quedan diferencias.

22. INFORME FINAL
Cantidad total de comandos y variantes auditados; errores detectados y reparados; funciones completadas; mejoras;
archivos modificados; resultados reales de las pruebas; cambios de rendimiento medidos; comparación con Fusion 360 y
SOLIDWORKS; problemas pendientes; evidencias; estado final de CREAR y MODIFICAR.

ORDEN FINAL
Auditar y reparar integralmente las secciones CREAR y MODIFICAR de BOCETO de OmniCAD, con todos sus submenús, variantes,
parámetros, interacciones y dependencias. Detectar, reproducir y corregir los bugs; implementar lo incompleto; mejorar lo
que funcione mal o esté por debajo de un CAD profesional. El objetivo son herramientas de dibujo y edición precisas,
robustas, fluidas, paramétricas y confiables, comparables con Fusion 360 y SOLIDWORKS. No dar la tarea por terminada por
documentación, tests superficiales o ausencia de excepciones: verificar siempre el resultado geométrico y la
experiencia real del usuario.
```
