# Auditoría y reparación de CREAR y MODIFICAR del boceto

Pedido de Gerardo (2026-11-06): auditar, reparar y completar todos los comandos de los menús CREAR y MODIFICAR del
entorno BOCETO contra Fusion 360 y SOLIDWORKS, con el mismo procedimiento que `auditoria_restricciones.md`: ejecutan
los agentes (Sol, Qwen, DeepSeek, GLM 5.3), Claude solo como última instancia, y al final todo verde.

**Orden:** arranca cuando cierre la auditoría de restricciones. Las dos tocan el mismo código del boceto
(`clon/omnicad/restricciones/`, `ui/boceto*`) y Recortar, Partir, Empalme y Desfase dependen de cómo quede el solver.

⚠ El texto que pasó Gerardo llegó cortado en la sección 12 («Editar transforma…»). Falta el resto.

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
rotar, escalar, copiar, agrupar, editar transforma[ciones]… (EL TEXTO ORIGINAL LLEGÓ CORTADO ACÁ)
```
