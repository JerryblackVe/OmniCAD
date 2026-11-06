# Auditoría y corrección del sistema de restricciones

Pedido de Gerardo (2026-11-06), a partir de un video que compara Fusion con OmniCAD: en Fusion, «Coincidente» entre el
punto medio de la diagonal de un rectángulo y el origen lleva el rectángulo al centro del lienzo; en OmniCAD queda donde
estaba (B-223 en `docs/seguimiento/bugs.md`). El pedido abarca TODO el sistema de restricciones, no solo ese caso.

Condiciones de Gerardo:
- Al final todo tiene que quedar verde.
- Ejecutan los agentes: Sol, Qwen, DeepSeek, GLM 5.3 y los demás registrados, combinados como haga falta.
- Claude resuelve solo en última instancia, cuando los agentes no pueden.

El estado vive en `docs/seguimiento/` (B-223 y las filas que abra la auditoría). Este documento es la especificación.

## Prompt para el agente

Entregado el 2026-11-06. Modelo sugerido: coordina una sesión Claude Opus 5 con esfuerzo alto; ejecutan Sol (OpenCode),
Qwen3.8-Flash (Qoder), DeepSeek v4.1 Flash y GLM 5.3 (CodeBuddy), un ítem por corrida y cada uno en su worktree.

```text
# PROMPT MAESTRO — AUDITORÍA, CORRECCIÓN Y OPTIMIZACIÓN INTEGRAL DEL SISTEMA DE RESTRICCIONES DE OMNICAD

## 1. ROL Y OBJETIVO
Actuá como Arquitecto Senior de Software CAD Paramétrico, especialista en geometría computacional, constraint solvers,
álgebra numérica, interfaces CAD y sistemas de bocetos 2D/3D.
Tu misión es realizar una auditoría exhaustiva y una corrección funcional integral del sistema de restricciones
geométricas y dimensionales de OmniCAD.
El resultado esperado es que todas las restricciones disponibles funcionen con la precisión, robustez, previsibilidad y
facilidad de uso de sistemas CAD profesionales como Autodesk Fusion 360 y SOLIDWORKS.
No quiero solamente un informe de errores. Quiero que investigues, reproduzcas, diagnostiques, corrijas, mejores y
pruebes los problemas encontrados.
Objetivo principal: que el usuario pueda crear, restringir, editar y manipular bocetos paramétricos sin errores,
comportamientos inesperados, saltos geométricos ni restricciones que aparenten funcionar pero no modifiquen
correctamente la geometría.

## 2. INSTRUCCIONES OBLIGATORIAS DEL PROYECTO
Antes de modificar código:
1. Leer AGENTS.md, CLAUDE.md, CLAUDE.local.md y PROJECT_CONTEXT.md.
2. Invocar mediante la herramienta Skill fable-method y ponytail.
3. Utilizar plan-then-do, tool-calling-guard y verify-before-commit.
4. Invocar omnicad-test para las pruebas reales de interfaz.
5. Utilizar ponytail-audit cuando corresponda.
6. Finalizar cada cambio con ponytail-review.
7. Respetar la arquitectura, convenciones, seguridad y reglas de colaboración existentes.
8. No copiar código propietario.
9. No instalar dependencias nuevas sin autorización.
10. No realizar git push.
Trabajar sobre el código real y no asumir que una función está correcta porque aparezca documentada o tenga tests verdes.

## 3. INVESTIGACIÓN Y COMPARACIÓN CON CAD PROFESIONALES
Utilizar como referencia prioritaria la documentación oficial de Fusion 360 almacenada en docs/fusion_docs/.
Consultar particularmente el índice fusion-sketch, utilizando scripts/fusion_docs.py buscar y ver.
Investigar también: documentación oficial de SOLIDWORKS sobre Sketch Relations; comportamiento de los solucionadores de
restricciones CAD; restricciones automáticas y manuales; manejo de geometría subrestringida, totalmente restringida y
sobrerrestringida; interacciones entre restricciones geométricas y cotas; comportamiento al arrastrar geometría
restringida.
Utilizar los materiales de referencia y pruebas existentes de Fusion 360 cuando estén disponibles.
Crear una matriz comparativa:
| Función | Fusion 360 | SOLIDWORKS | OmniCAD | Estado |
|---|---|---|---|---|
| Restricción geométrica | Comportamiento comprobado | Comportamiento comprobado | Resultado real | Correcto / Bug / Faltante |
Cuando los programas difieran, identificarlo y elegir un comportamiento consistente, priorizando Fusion 360 y
justificando la decisión.
No inventar comportamientos de referencia que no hayan sido comprobados.

## 4. AUDITORÍA COMPLETA DE RESTRICCIONES
Identificar automáticamente todas las restricciones disponibles en OmniCAD, incluyendo las expuestas en la interfaz y
las implementadas internamente.
Restricciones geométricas: Coincidente, Colineal, Concéntrica, Paralela, Perpendicular, Horizontal, Vertical, Tangente,
Igualdad, Simetría, Punto medio, Fijar / Desfijar, Punto sobre objeto, Continuidad o suavidad cuando corresponda, y
cualquier otra restricción encontrada en el código.
Restricciones dimensionales: distancia entre puntos, distancia horizontal y vertical, longitud, ángulo, radio,
diámetro, distancia punto-línea, cotas conductoras y de referencia, cotas con expresiones y parámetros, restricciones
dimensionales combinadas.
En cada caso, comprobar: 1. selección válida de entidades; 2. aplicación real de la restricción; 3. modificación
correcta de la geometría; 4. conservación de restricciones anteriores; 5. reacción ante el arrastre; 6. actualización de
grados de libertad; 7. persistencia al guardar y volver a abrir; 8. eliminación, edición y deshacer/rehacer;
9. comportamiento ante conflictos; 10. consistencia entre UI, API, MCP y CLI.
No limitarse a verificar que exista un botón o que el solver devuelva éxito.

## 5. BUG PRIORITARIO: RESTRICCIÓN COINCIDENTE (B-223)
Comportamiento esperado: al seleccionar un punto perteneciente a una geometría y aplicar Coincidente con el origen del
boceto, los puntos deben coincidir geométricamente; el solver debe actualizar las coordenadas; la geometría debe
desplazarse o ajustarse según sus grados de libertad; deben conservarse las relaciones previas; el resultado debe quedar
restringido paramétricamente; los grados de libertad deben actualizarse.
Comportamiento observado en OmniCAD: la geometría no se desplaza hasta el origen como en Fusion 360 (video de Gerardo:
rectángulo de 2 puntos + diagonal de construcción + Coincidente entre el punto medio de la diagonal y el origen).
Investigación obligatoria, con pruebas y trazas: si el origen es seleccionable como entidad de restricción; si el
sistema diferencia el origen de un punto ordinario; si ambas selecciones llegan al comando; si la relación se construye
con las referencias correctas; si el solver recibe la ecuación adecuada; si la solución se aplica a las entidades
reales; si la interfaz recibe y representa el resultado; si la restricción se registra, persiste y se conserva tras
recalcular; si hay errores en los grados de libertad; si el problema cambia según el orden de selección.
Probar coincidencias punto-punto, punto-origen, punto-curva, extremos de líneas, centros de círculos y arcos, y los
demás casos que admitan los comandos de referencia.
No crear parches específicos para el origen. Corregir la causa estructural.

## 6. AUDITORÍA PROFUNDA DEL SOLVER
Revisar clon/omnicad/restricciones/ (solver.py, boceto.py y todos los módulos que intervengan).
Analizar: formulación matemática de cada restricción; residuos y tolerancias; jacobianos y rango; grados de libertad;
condicionamiento numérico; convergencia; restricciones dependientes o redundantes; sistemas incompatibles; estabilidad;
selección de la solución más cercana a la configuración existente; preservación de geometrías parcialmente
restringidas; entidades degeneradas; solución incremental después de editar; estados numéricos inválidos; rendimiento
de bocetos complejos.
Evitar soluciones matemáticamente válidas pero visualmente inesperadas cuando existe una solución cercana que mantiene
la intención del usuario. No reemplazar indiscriminadamente el solver: primero identificar las causas reales y evaluar
las correcciones mínimas suficientes.

## 7. COMPORTAMIENTO INTERACTIVO Y UX
Verificar: selección mediante clic; orden de selección; resaltado; prioridad y tolerancia de selección; detección de
puntos, curvas y origen; indicaciones visuales de la restricción activa; vista previa; aplicación inmediata; arrastre de
entidades restringidas y parcialmente restringidas; bloqueo de geometría totalmente restringida; mensajes y
visualización de conflictos; eliminación y supresión; deshacer y rehacer; atajos y Esc; sincronización entre modelo,
solver y visor. Sin desplazamientos bruscos, selecciones ambiguas ni cambios que el usuario no pidió.

## 8. PRUEBAS COMBINADAS Y CASOS COMPLEJOS
Escenarios: 1. rectángulo parcialmente restringido y coincidencia con el origen; 2. rectángulo con dimensiones y
horizontales/verticales; 3. triángulo con longitud, ángulo y coincidencias; 4. dos círculos concéntricos; 5. arcos
tangentes a líneas; 6. cadenas de líneas; 7. perfiles cerrados con múltiples restricciones; 8. geometría fija y libre;
9. simetría respecto de ejes; 10. restricciones redundantes; 11. contradictorias; 12. eliminación de una restricción
intermedia; 13. modificación de cotas después de restringir; 14. splines; 15. geometrías proyectadas y referencias
externas; 16. guardado, recuperación y recálculo; 17. geometría importada de SVG/DXF cuando admita restricciones;
18. bocetos grandes; 19. restricciones por MCP y CLI; 20. edición de un boceto que alimenta una extrusión u otra
operación posterior. Comprobar que no se destruyan perfiles, referencias ni operaciones dependientes del timeline.

## 9. DETECCIÓN DE RESTRICCIONES Y CONFLICTOS
Auditar inferencias y restricciones automáticas: horizontal/vertical, coincidencia entre extremos, centros y puntos
medios, tangencias, paralelas y perpendiculares, duplicadas, conflictos entre automáticas y manuales, AutoConstrain,
diagnóstico de conflictos. No incorporar silenciosamente restricciones que causen estados inconsistentes; ante
conflictos, el usuario debe ver qué restricciones están involucradas; no eliminar restricciones válidas para converger.

## 10. GRADOS DE LIBERTAD Y ESTADOS DEL BOCETO
Verificar el cálculo de grados de libertad, entidades libres, totalmente restringido, sobrerrestricción, redundancia vs
contradicción, actualización inmediata, comportamiento después de eliminar restricciones y consistencia entre solver y
representación visual. No considerar totalmente restringido un boceto solo porque el solver convergió: validar con
análisis geométrico y matemático (rango del jacobiano).

## 11. CORRECCIÓN DE ERRORES Y OPTIMIZACIÓN
Por cada bug confirmado: caso mínimo; causa raíz; test que falla antes; corrección; test que pasa; regresión
relacionada (scripts/tests_afectados.py --correr); verificar que no cambie otras restricciones; seguimiento y
documentación; ponytail-review; integración según las reglas. Un problema verificable por vez, sin reescrituras
masivas. Mejoras de arquitectura del solver solo con evidencia matemática y pruebas. Optimizar solo después de medir;
Rust/PyO3 solo con ventaja comprobada y sin dependencias nuevas sin autorización.

## 12. AUTOMATIZACIÓN DE PRUEBAS
pytest (unitarias del solver, integración del boceto, API, persistencia), pruebas interactivas con PySide6, skill
omnicad-test, scripts/prueba_ui/, prueba de humo y caza de errores cuando corresponda. Es obligatorio probar la
interfaz como un usuario real: selección de entidades, clic en la herramienta, aplicación, arrastre, edición,
cancelación, eliminación, guardado y reapertura, con eventos simulados que no muevan el cursor físico. Respetar
scripts/turno.py y la política de pruebas pesadas. Comprobar con coordenadas, residuos y capturas.

## 13. COMPATIBILIDAD CON API, MCP Y CLI
Toda corrección funcional debe estar disponible de forma coherente en la interfaz, la API interna, el MCP y la CLI
(catálogo único de clon/omnicad/api/; regenerar docs/agentes/herramientas.md). Sin rutas alternativas del solver que
den resultados distintos según el mecanismo.

## 14. SEGURIDAD DEL DOCUMENTO Y REGRESIONES
Identificadores geométricos estables, referencias paramétricas, integridad de perfiles, transacciones atómicas,
recuperación ante error, deshacer/rehacer, compatibilidad con .omnicad existentes, recálculos reproducibles, sin cambios
inesperados en pasos posteriores del timeline. Cuidar la relación con objetos vectoriales (SVG/DXF, textos como objetos
lógicos) y operaciones de sólidos.

## 15. GESTIÓN Y ORGANIZACIÓN DEL TRABAJO
Fases: A Inventario; B Diagnóstico; C Corrección; D Integración; E Validación; F Revisión final. El coordinador las
gestiona sin pedir aprobación entre tareas ordinarias. Cada corrección se cierra y verifica antes de la siguiente. No
realizar push. Mantener al día docs/seguimiento/bugs.md, faltantes.md, mejoras.md, PROJECT_LOG.md, PROJECT_CONTEXT.md y
la documentación y pruebas afectadas.

## 16. CRITERIOS DE ACEPTACIÓN
Todas las restricciones identificadas tienen pruebas funcionales; producen relaciones geométricas correctas; el caso
Coincidente con el origen funciona; el solver conserva las restricciones compatibles; los grados de libertad son
coherentes; los bocetos parcialmente restringidos se manipulan bien y los totalmente restringidos no se deforman; las
contradicciones y redundancias se detectan; los errores no corrompen el documento; guardar y recuperar conserva las
relaciones; la UI representa fielmente el resultado; API, MCP y CLI se comportan igual; sin regresiones verificadas; las
pruebas relacionadas pasan; las diferencias pendientes con Fusion 360 y SOLIDWORKS quedan identificadas. No afirmar
equivalencia completa sin evidencia.

## 17. INFORME FINAL OBLIGATORIO
1. Cantidad de restricciones auditadas. 2. Inventario y cobertura de pruebas. 3. Bugs encontrados con causa raíz.
4. Bugs corregidos y archivos modificados. 5. Faltantes detectados e implementados. 6. Mejoras de solver e interfaz.
7. Resultados de pruebas con salidas reales. 8. Pruebas en la interfaz. 9. Comparación contra Fusion 360 y SOLIDWORKS.
10. Pendientes y limitaciones verificadas. 11. Rendimiento antes y después cuando corresponda. 12. Estado final y
evidencias. Clasificar cada resultado como VERIFICADO, CORREGIDO, PARCIAL, PENDIENTE o NO VERIFICADO.

## INSTRUCCIÓN FINAL
No quiero una auditoría superficial ni una corrección limitada al bug de Coincidente. Quiero una revisión de extremo a
extremo de todo el sistema de restricciones de OmniCAD: cada restricción, su comportamiento matemático, su integración
con el solver, su interacción con el usuario y su efecto sobre la geometría paramétrica. Fusion 360 y SOLIDWORKS como
estándares funcionales de referencia, con OmniCAD como implementación independiente. Ejecutá la investigación,
auditoría, correcciones y verificaciones. Documentá con precisión todo lo que haya quedado sin resolver.
```
