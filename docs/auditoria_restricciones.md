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

## Corridas de agentes

| Corrida | Ítem | Agente | Worktree / rama | Estado |
|---|---|---|---|---|
| restr-1 | B-223 | Sol (gpt-6.1-sol high) | `D:/PROGRAMA-r1` / `restr-1` | Fusionada (B-223 cerrado; Sol sin cupo al terminar) |
| restr-2 | Fase A: inventario + `test_restricciones_matriz.py` | DeepSeek v4.1 Flash (CodeBuddy): sin cupo a los 3 min (429); GLM 5.3 (CodeBuddy): créditos agotados (429); Qwen3.8-Flash (Qoder): «qfmodel unavailable»; DeepSeek v4.1 Flash free (OpenCode): colgado (sin CPU ni archivos a los 7 min), cortado; GLM 5.3 (OpenCode Go): sin suscripción; GLM 5.3 Flash free (OpenCode): colgado igual a los 7 min, cortado. Sigue el coordinador (Claude Opus) como última instancia | `D:/PROGRAMA-r2` / `restr-2` | Fusionada (inventario y matriz) |
| restr-3 | B-224 | Coordinador Opus (Qwen y Sol sin cupo) | main | Commit c81bd8c |
| restr-4 | B-226 y B-225 (elección de solución del solver) | Sol (gpt-6.1-sol high) | `D:/PROGRAMA-r4` / `restr-4` | Fusionada (cortada a los 25 min esperando turno; tests y revisión del coordinador) |
| restr-5 | B-227 | Sol (gpt-6.1-sol high) | `D:/PROGRAMA-r5` / `restr-5` | Fusionada (dos corridas cortadas a los 25 min) |
| restr-6 | B-228 | Sol (gpt-6.1-sol high) | `D:/PROGRAMA-r6` / `restr-6` | Fusionada (vio la regresión de B-227) |
| restr-7 | B-229 | Sol (gpt-6.1-sol high) | `D:/PROGRAMA-r7` / `restr-7` | Fusionada |
| restr-8 | B-230 y S7 | Sol (gpt-6.1-sol high) | `D:/PROGRAMA-r8` / `restr-8` | Fusionada |
| restr-9 | Fase D: integración ventana / API / archivo (S8, S12, S13, guardar-abrir-deshacer, ventana = MCP) | Sol (gpt-6.1-sol high) | `D:/PROGRAMA-r9` / `restr-9` | Fusionada (S13 y S8 corregidos, S12 → H-106) |
| restr-10 | Fase E: escenarios combinados de la sección 8 (`test_restricciones_escenarios.py`) | Sol (pendiente) | `D:/PROGRAMA-r10` / `restr-10` | Brief listo, sin lanzar |

### Brief restr-1 (B-223)

```text
Corrida restr-1 · B-223 · OmniCAD (CAD paramétrico en Python, PySide6 + OpenCascade). Todo en español.

## Dónde trabajás
- Worktree `D:/PROGRAMA-r1` (rama `restr-1`). Tocá SOLO archivos de este worktree. No commitees, no hagas push, no instales nada.
- Python: `D:/PROGRAMA/clon/.venv/Scripts/python.exe`, siempre desde `D:/PROGRAMA-r1/clon` y con `PYTHONPATH=D:/PROGRAMA-r1/clon` (si no, importa la copia de `D:/PROGRAMA`).
- Leé primero `AGENTS.md` y `CLAUDE.md` de la raíz (reglas, recetas A/B/C, cómo verificar).
- Reglas de trabajo (obligatorias): leé el archivo real antes de editar y mapeá sus llamadores; plan corto en pasos chicos; el cambio MÁS CHICO que resuelve el ítem entero (sin abstracciones, opciones ni código «para después»); llamá las herramientas de verdad, no narres.
- Conservá los finales de línea de cada archivo (CRLF o LF): al terminar, `git diff --stat` no puede mostrar archivos enteros reescritos.

## El ítem: B-223 (solo este)
Video de Gerardo `C:/Users/mosos/Videos/2026-11-06 19-31-01.mp4` (sacá cuadros con ffmpeg si querés verlo):
- **Fusion (0:54→1:02):** rectángulo de 2 puntos (x −120…−55, y 0…50) + diagonal de construcción. Con «Coincidente», clic en el
  punto medio de la diagonal (Fusion dibuja un triángulo de punto medio en el centro de la línea) y clic en el origen: el
  rectángulo entero se corre, sin cambiar de tamaño, y queda centrado en el origen.
- **OmniCAD (1:40→2:00):** el usuario pone un Punto «Sobre la curva» en la mitad de la diagonal, abre «Coincidente», clic en
  ese punto y clic en el origen (se ve el resaltado azul en el origen). No pasa nada: ni «Restricción agregada» ni error.

Ya comprobado por el coordinador (no lo repitas, usalo):
- El solver anda: `asegurar_referencias([0])` + `agregar_restriccion("punto_medio", [0, diagonal])` + `solver.resolver(b)` deja
  el rectángulo en (−32.5,−25)…(32.5,25). El problema está antes del solver.
- `_punto_cercano` (`clon/omnicad/ui/editor_boceto.py:1263`) solo encuentra puntos que están en `b.puntos`; el origen (id 0)
  entra ahí solo cuando `Boceto.asegurar_referencias` lo materializa (`restricciones/boceto.py:2031`). Flujo de clic de las
  restricciones: `_clic_restriccion` → `entidad_en` → `aplicar_restriccion` (`editor_boceto.py:4768-4854`).

Qué tenés que hacer:
1. Reproducí el caso de la ventana con eventos simulados de Qt (QTest / `scripts/prueba_ui/`, sin mover el cursor real;
   ventana `OMNICAD_PRUEBA_VENTANA=minimizada`): dibujar el rectángulo, la diagonal, el punto sobre la curva, herramienta
   Coincidente, clic en el punto, clic en el origen. Dejá la traza de qué devuelve `entidad_en` en cada clic y por qué no se
   aplica nada (¿el origen no es elegible? ¿la restricción se rechaza callada? ¿el chequeo de GDL de `aplicar_restriccion`
   la descarta?).
2. Test rojo en `clon/tests/` (en el archivo de tests del editor de boceto que ya cubra restricciones con clics; buscalo con
   grep) que haga exactamente ese recorrido con clics y compruebe coordenadas: el punto queda en (0,0) y el rectángulo se
   mueve sin deformarse más de lo necesario.
3. Corregí la CAUSA. Prohibido el parche «si es el origen…» en un solo comando: el origen tiene que ser elegible en todas las
   herramientas de restricción y cota igual que cualquier punto fijo (también si nunca se citó antes).
4. Punto medio como en Fusion: buscá en la ayuda oficial de Fusion
   `D:/PROGRAMA/clon/.venv/Scripts/python.exe D:/PROGRAMA/scripts/fusion_docs.py buscar midpoint -s fusion-sketch` (y `ver
   "<título>"`) y mirá el video. Si Fusion deja tomar el punto medio de una línea con Coincidente, hacé que un clic en el punto
   medio de una línea (con su marca visual) cree la restricción «Punto medio» con el otro punto. Si la ayuda no lo confirma,
   NO lo inventes: anotalo en el informe.
5. Segundo test (si hiciste el 4): diagonal + clic en su punto medio + clic en el origen → rectángulo centrado en el origen,
   ancho 65 y alto 50 intactos.
6. Si cambia lo que acepta o devuelve una herramienta de `clon/omnicad/api/`, ajustala (receta C) y regenerá
   `docs/agentes/herramientas.md` con `omnicad tools --markdown --output docs/agentes/herramientas.md` desde la raíz.
NO toques B-224, B-225 ni B-226 (orden de entidades en la API, deformación del rectángulo con punto sobre línea, coincidente
con la esquina opuesta): van en otras corridas. Si tu arreglo choca con ellos, decilo en el informe.

## Verificación (en primer plano, nunca en segundo plano; una cosa por vez)
Desde `D:/PROGRAMA-r1/clon`, con `PYTHONPATH=D:/PROGRAMA-r1/clon`:
- `D:/PROGRAMA/clon/.venv/Scripts/python.exe -m ruff check .`
- `D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/tests_afectados.py --correr` (elige y corre los tests afectados con
  turno; puede esperar en fila detrás de otra sesión: dejalo esperar). Prohibido la suite completa y `pytest -n`.
- Si tocaste la ventana, el o los tests de ventana que agregaste también pasan.

## Revisión antes de cerrar
Releé tu diff como revisor: ¿la lógica es correcta en los bordes (orden de clic, origen ya materializado o no, punto oculto)?
¿Cada línea hace falta? ¿Hay un test para cada rama nueva? ¿Algún llamador de lo que cambiaste se rompe? Arreglá lo que
encuentres.

## Informe (escribilo apenas termines el ítem, aunque falte algo)
`D:/PROGRAMA-r1/evidencias/restr1/informe.md`: causa raíz con archivo:línea y la traza; qué cambiaste (archivo y función);
tests nuevos (nombre); salida REAL de ruff y de tests_afectados (las últimas líneas); qué dice la ayuda de Fusion del punto
medio (ruta del artículo); lo que no pudiste hacer o verificar.
```

### Brief restr-2 (fase A, inventario)

```text
Corrida restr-2 · Fase A (inventario de restricciones) · OmniCAD (CAD paramétrico en Python). Todo en español.

## Dónde trabajás
- Worktree `D:/PROGRAMA-r2` (rama `restr-2`). Tocá SOLO archivos de este worktree. No commitees, no hagas push, no instales nada.
- Python: `D:/PROGRAMA/clon/.venv/Scripts/python.exe`, desde `D:/PROGRAMA-r2/clon`, con `PYTHONPATH=D:/PROGRAMA-r2/clon`.
- Leé `AGENTS.md` (reglas y cómo verificar). Leé el código real antes de afirmar algo; llamá las herramientas de verdad, no
  narres; el cambio más chico que cumple; conservá los finales de línea de cada archivo.

## Qué tenés que entregar (dos archivos nuevos, nada más)
1. `docs/auditorias/restricciones_inventario.md`: inventario de TODAS las restricciones y cotas del boceto 2D de OmniCAD.
   Fuentes a recorrer: `TIPOS_RESTRICCION`, `TIPOS_COTA`, `CAMBIABLES` y `_validar_restriccion` / `_validar_cota` en
   `clon/omnicad/restricciones/boceto.py`; las ecuaciones en `clon/omnicad/restricciones/solver.py`; las inferencias
   automáticas en `restricciones/inferencia.py` y `auto_candidatos.py`; la ventana en `clon/omnicad/ui/editor_boceto.py`
   (`RESTRICCIONES_HERRAMIENTA`, `aplicar_restriccion`); la cinta en `ui/cinta.py`; el MCP/CLI en
   `clon/omnicad/api/herramientas_boceto.py` (`add_constraint`, `add_dimension`, `replace_constraint`, `auto_constrain`,
   `find_redundant_constraints`, `find_underconstrained`…). Una tabla con una fila por restricción o cota:
   | Tipo (clave) | Nombre | Entidades que acepta (y en qué orden) | Ecuación del solver (función y línea) | GDL que quita |
   Botón en la cinta (sí/no) | Herramienta MCP | Tests que la cubren (archivo) | Observaciones |
   Después, una tabla «Fusion vs OmniCAD»: para cada restricción, qué dice la ayuda oficial de Fusion (buscá con
   `D:/PROGRAMA/clon/.venv/Scripts/python.exe D:/PROGRAMA/scripts/fusion_docs.py buscar <palabras> -s fusion-sketch` y
   `ver "<título>"`; anotá la ruta del artículo) y qué hace OmniCAD. Si la ayuda no lo dice, escribí «sin dato»: NO inventes
   comportamientos de Fusion ni de SOLIDWORKS.
2. `clon/tests/test_restricciones_matriz.py`: un test parametrizado por cada tipo de restricción y de cota, sin ventana
   (solo `Boceto` + `solver.resolver`), que compruebe con números: (a) que con entidades válidas la relación se cumple
   después de resolver (p. ej. paralela: producto vectorial ≈ 0; coincidente: distancia ≈ 0; cota de distancia: distancia =
   valor); (b) que `Boceto.desde_dict(b.a_dict())` conserva la restricción y vuelve a resolver igual; (c) que
   `solver.grados_de_libertad` baja lo que dice la tabla. Rápido (< 3 s el archivo entero).
   Si un caso falla porque OmniCAD tiene un bug, NO lo arregles: marcá ese caso con
   `pytest.param(..., marks=pytest.mark.xfail(strict=True, reason="B-nnn o hallazgo: <qué falla>"))` y anotalo en la sección
   «Hallazgos» del inventario con el caso mínimo (código de 5-10 líneas y lo que da contra lo esperado). Bugs ya anotados:
   B-223 (origen en Coincidente, ventana), B-224 (punto_medio y coincidente fallan con [curva, punto] por API),
   B-225 (coincidente origen sobre diagonal deforma el rectángulo), B-226 (coincidente origen + esquina opuesta da ok=False).

## Verificación (en primer plano, una cosa por vez)
Desde `D:/PROGRAMA-r2/clon` con `PYTHONPATH=D:/PROGRAMA-r2/clon`:
- `D:/PROGRAMA/clon/.venv/Scripts/python.exe -m ruff check .`
- `D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest tests/test_restricciones_matriz.py -q`
  (puede esperar en fila: dejalo esperar). Prohibido la suite completa y `pytest -n`.

## Informe (escribilo apenas termines, aunque falte algo)
`D:/PROGRAMA-r2/evidencias/restr2/informe.md`: cuántas restricciones y cotas inventariaste, cuántos casos de test y cuántos
xfail (con su motivo), salida REAL de ruff y pytest (últimas líneas), lo que no pudiste verificar.
```

### Brief restr-4 (B-226 y B-225)

```text
Corrida restr-4 · B-226 y B-225 (una sola causa: qué solución elige el solver) · OmniCAD (CAD paramétrico en Python). Todo en español.

## Dónde trabajás
- Worktree `D:/PROGRAMA-r4` (rama `restr-4`). Tocá SOLO archivos de este worktree. No commitees, no hagas push, no instales nada.
- Python: `D:/PROGRAMA/clon/.venv/Scripts/python.exe`, desde `D:/PROGRAMA-r4/clon`, con `PYTHONPATH=D:/PROGRAMA-r4/clon`.
- Leé `AGENTS.md` y `CLAUDE.md`. Leé el código real antes de editar y buscá todos los llamadores de lo que cambies; el cambio
  más chico que resuelve la causa; sin abstracciones ni opciones nuevas; llamá las herramientas de verdad, no narres.
- Conservá los finales de línea de cada archivo (`solver.py` y `boceto.py` son LF). NO edites `docs/seguimiento/` ni
  `PROJECT_LOG.md` (lo hace el coordinador).

## Los dos bugs (casos mínimos, sin ventana)
Rectángulo de 2 puntos y su diagonal de construcción, como en el video de Gerardo:
```python
from omnicad.restricciones.boceto import Boceto
from omnicad.restricciones.solver import resolver
b = Boceto()
lineas = b.agregar_rectangulo((-120, 0), (-55, 50))
P = [b.curvas[l].p1 for l in lineas]            # P[0]=(-120,0) … P[2]=(-55,50)
d = b.agregar_linea(P[0], P[2], construccion=True)
b.asegurar_referencias([Boceto.ORIGEN])
```
- **B-226:** `b.agregar_restriccion("coincidente", [Boceto.ORIGEN, P[2]])` + `resolver(b)` → `ok=False`. P[2] va a (0,0) y P[0]
  queda en (−120, 0): el alto pasa a 0 y `_curvas_colapsadas` lo rechaza (`clon/omnicad/restricciones/solver.py:937-942`).
  Con `[P[0], ORIGEN]` anda (P[0] ya estaba en y=0).
- **B-225:** `b.agregar_restriccion("coincidente", [Boceto.ORIGEN, d])` (origen sobre la diagonal) → `ok=True` pero
  P[0]=(−122.76, 6.63) y P[2]=(−17.70, 0.96): el rectángulo se da vuelta y queda de 54×−5,7 en vez de 65×50.
Los dos tienen un test `xfail(strict=True)` en `clon/tests/test_restricciones_matriz.py`
(`test_b225_…` y `test_b226_…`): cuando los arregles, sacales el `xfail` (si no, quedan rojos por XPASS).

Hipótesis del coordinador (comprobala, no la des por buena): `_resolver_grupo` (llamado en `solver.py:925`) busca la
solución de menor movimiento desde la posición actual. Esa solución aplasta (B-226) o da vuelta (B-225) el rectángulo, aunque
exista otra cercana que lo conserva: correrlo entero. La especificación pide: «Evitar soluciones matemáticamente válidas pero
visualmente inesperadas cuando existe una solución cercana que mantiene la intención del usuario. No reemplazar
indiscriminadamente el solver: primero identificar las causas reales y evaluar las correcciones mínimas suficientes.»
Comportamiento esperado (Fusion, video de Gerardo `C:/Users/mosos/Videos/2026-11-06 19-31-01.mp4`, 0:54→1:02): al llevar el
punto medio de la diagonal al origen, el rectángulo se corre entero sin cambiar de tamaño. Ayuda oficial:
`D:/PROGRAMA/clon/.venv/Scripts/python.exe D:/PROGRAMA/scripts/fusion_docs.py buscar coincident -s fusion-sketch`. No inventes
lo que la ayuda no dice.

## Qué tenés que hacer
1. Trazá el camino real (`resolver` → `_Sistema` → `_resolver_grupo`) con esos dos casos e imprimí qué solución sale y por qué.
2. Corregí la CAUSA en el solver con el cambio más chico que haga que, cuando la solución de menor movimiento colapsa una curva
   o da vuelta la orientación de una figura, el solver elija una solución cercana que no lo haga (si existe). Prohibido el
   parche «si es el origen…» o «si es un rectángulo…».
3. Criterios (tests): B-226 → `ok=True`, P[2] en (0,0) y ancho y alto ≠ 0 con el mismo signo que antes; B-225 → `ok=True`, el
   origen sobre la diagonal y el rectángulo con ancho 65 y alto 50 (±1 mm), corrido, no dado vuelta.
4. Sin regresiones: `clon/tests/test_restricciones_matematica.py` (invariantes y arrastre) y
   `clon/tests/test_restricciones_matriz.py` tienen que seguir verdes. Si tu cambio toca el arrastre (`_resolver_arrastre`),
   medí el tiempo antes y después con `scripts/medir_solver_boceto.py` o `scripts/bench_restricciones.py` (mirá cuál sirve).
5. Si un caso no tiene arreglo sin rehacer el solver, pará y explicalo en el informe con la traza: no reescribas el solver.

## Verificación (en primer plano, una cosa por vez, nunca en segundo plano)
Desde `D:/PROGRAMA-r4/clon` con `PYTHONPATH=D:/PROGRAMA-r4/clon`:
- `D:/PROGRAMA/clon/.venv/Scripts/python.exe -m ruff check .`
- `D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py --plazo 900 -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest tests/test_restricciones_matriz.py tests/test_restricciones_matematica.py tests/test_restricciones_ui.py -q -W error -p no:cacheprovider`
- Después, los tests que mencionan el solver: `grep -l "restricciones.solver\|resolver(" tests/test_*.py`, partidos en tandas
  de ~25 archivos, cada tanda con el mismo `turno.py --plazo 900`. Prohibido `tests_afectados.py --correr` (elige casi la suite
  completa), la suite completa y `pytest -n`. Si turno espera en fila, dejalo esperar.

## Revisión antes de cerrar
Releé tu diff como revisor: ¿qué pasa con un boceto sin solución cercana buena (sigue diciendo conflicto)? ¿con miles de
curvas (no puede multiplicar el tiempo)? ¿con el arrastre? ¿cada línea hace falta? ¿hay un test por rama nueva?

## Informe (escribilo apenas termines, aunque falte algo)
`D:/PROGRAMA-r4/evidencias/restr4/informe.md`: la traza de la causa (archivo:línea), qué cambiaste (archivo y función), las
coordenadas antes y después de los dos casos, tests (rojo antes, verde después) con la salida REAL de ruff y de cada tanda
(últimas líneas), tiempos si tocaste el arrastre, lo que no pudiste verificar.
```

### Brief restr-5 (B-227)

```text
Corrida restr-5 · B-227 · OmniCAD (CAD paramétrico en Python). Todo en español.

## Dónde trabajás
- Worktree `D:/PROGRAMA-r5` (rama `restr-5`). Tocá SOLO archivos de este worktree. No commitees, no hagas push, no instales nada.
- Python: `D:/PROGRAMA/clon/.venv/Scripts/python.exe`, desde `D:/PROGRAMA-r5/clon`, con `PYTHONPATH=D:/PROGRAMA-r5/clon`.
- Leé `AGENTS.md`. Leé el código real y buscá todos los llamadores antes de editar; el cambio más chico que resuelve la causa;
  conservá los finales de línea (`boceto.py` y `herramientas_boceto.py` son LF). NO edites `docs/seguimiento/` ni `PROJECT_LOG.md`.

## El ítem: B-227
Una cota de ángulo fuera de 0…180° entra sin error en el modelo y en la ventana, y el solver no la cumple:
`b.agregar_cota("angulo", [l1, l2], "200")` (o `"-30"`) + `resolver(b, {k: 200.0})` → `ok=False`.
La API ya lo frena (`clon/omnicad/api/herramientas_boceto.py › _cota_valida`, ~línea 2114: `0 < valor < 180`), pero el modelo
no: `clon/omnicad/restricciones/boceto.py › validar_valor_cota` (~línea 188) dice «Los ángulos no se validan acá». La ventana
(`clon/omnicad/ui/editor_boceto.py`, buscá `validar_valor_cota` y donde se escribe el valor de una cota de ángulo) y el
recálculo (`clon/omnicad/timeline/operaciones.py:945`) usan la del modelo, así que la ventana acepta lo que la API rechaza.

Arreglo pedido: que la regla viva en UN lugar, el modelo (`validar_valor_cota`), con un mensaje claro en español, y que la API
use esa (borrá la copia de `_cota_valida` si queda duplicada). Antes de elegir los límites, mirá cómo mide el solver el ángulo
(`clon/omnicad/restricciones/solver.py`, residuo de `angulo`, ~línea 464: `atan2(|cruz|, dot)` con cuadrantes) y la ayuda de
Fusion (`D:/PROGRAMA/clon/.venv/Scripts/python.exe D:/PROGRAMA/scripts/fusion_docs.py buscar angular dimension -s fusion-sketch`):
si 0 o 180 se pueden cumplir y Fusion los acepta, decidí con esa evidencia y anotala en el informe.

## Tests (escribilos primero, mirá que fallen)
En `clon/tests/test_restricciones_matriz.py`, al final:
- `test_b227_cota_de_angulo_fuera_de_rango_se_rechaza_en_el_modelo`: 200, −30 y NaN con `agregar_cota` o al recalcular dan
  `ErrorBoceto` con el mensaje; 60 sigue entrando y resolviendo.
- `test_b227_la_ventana_rechaza_el_angulo_fuera_de_rango`: el mismo valor tecleado en la caja de la cota de ángulo de la ventana
  (mirá cómo lo hacen los tests de `tests/test_restricciones_ui.py` o `tests/test_boceto_fase*_ui.py` que editan una cota con
  QTest) muestra el error y no cambia el boceto. Eventos simulados, sin mover el cursor real.

## Verificación (en primer plano, una cosa por vez)
Desde `D:/PROGRAMA-r5/clon` con `PYTHONPATH=D:/PROGRAMA-r5/clon`:
- `D:/PROGRAMA/clon/.venv/Scripts/python.exe -m ruff check .`
- `D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/turno.py --plazo 900 -- D:/PROGRAMA/clon/.venv/Scripts/python.exe -m pytest tests/test_restricciones_matriz.py <los archivos de tests que usan validar_valor_cota, _cota_valida o "angulo"> -q -W error -p no:cacheprovider`
  (buscalos con grep; en tandas de ~25 archivos). Prohibido `tests_afectados.py --correr`, la suite completa y `pytest -n`.

## Informe (apenas termines)
`D:/PROGRAMA-r5/evidencias/restr5/informe.md`: qué cambiaste (archivo y función), los límites elegidos y por qué, tests (rojo
antes, verde después) y la salida REAL de ruff y de cada tanda (últimas líneas), lo que no pudiste verificar.
```

### Brief restr-6 (B-228)

```text
Corrida restr-6 · B-228 · OmniCAD (CAD paramétrico en Python). Todo en español.

## Dónde trabajás
- Worktree `D:/PROGRAMA-r6` (rama `restr-6`). Tocá SOLO archivos de este worktree. No commitees, no hagas push, no instales nada.
- Python: `D:/PROGRAMA/clon/.venv/Scripts/python.exe`, desde `D:/PROGRAMA-r6/clon`, con `PYTHONPATH=D:/PROGRAMA-r6/clon`.
- Leé `AGENTS.md`. Leé el código real y buscá todos los llamadores antes de editar; el cambio más chico que resuelve la causa;
  conservá los finales de línea (`boceto.py`, `solver.py` y `herramientas_boceto.py` son LF). NO edites `docs/seguimiento/` ni
  `PROJECT_LOG.md`.
- Tests: un archivo chico con `-k` se corre SIN turno, directo con pytest. Las tandas de varios archivos van con
  `../scripts/turno.py --plazo 900 -- …` (puede esperar en fila). Escribí el informe ANTES de lanzar las tandas con turno.

## El ítem: B-228
Una cota de distancia entre dos líneas NO paralelas se acepta y mide solo un extremo de la segunda:
```python
from omnicad.restricciones.boceto import Boceto
from omnicad.restricciones.solver import resolver
b = Boceto()
l1, l2 = b.agregar_linea((0, 0), (10, 0)), b.agregar_linea((0, 5), (10, 15))
k = b.agregar_cota("distancia", [l1, l2], "7")
resolver(b, {k: 7.0})   # ok=True, pero l2 queda en y=6,03 y 15: solo su p1 está a 7
```
Modelo: `clon/omnicad/restricciones/boceto.py › _validar_cota` (~línea 2612) acepta línea-línea sin mirar si son paralelas;
la ecuación (`clon/omnicad/restricciones/solver.py`, ~línea 494) mide `p1` de la segunda contra la primera. La ventana ya
convierte ese caso en cota de ángulo (`clon/omnicad/ui/editor_boceto.py`, buscá dónde elige «angulo» para dos líneas no
paralelas, ~4755). La API (`clon/omnicad/api/herramientas_boceto.py › add_dimension`) usa el modelo.

En Fusion: «Línea sola o paralelas: lineal; no paralelas: angular» (ayuda: `D:/PROGRAMA/clon/.venv/Scripts/python.exe
D:/PROGRAMA/scripts/fusion_docs.py ver "Dimension sketch geometry" -s fusion-sketch`). Leela antes de decidir.

Arreglo pedido: que el modelo rechace (con un `ErrorBoceto` claro que diga que use una cota de ángulo) una distancia entre
dos líneas que NO son paralelas al crearla, con la misma tolerancia que usa la ventana para decidir. Ojo: una cota que YA
existe entre líneas que eran paralelas y después dejan de serlo (por otra restricción) no se puede romper al abrir un archivo
viejo: mirá cómo se cargan las cotas (`desde_dict`) y que la validación sea solo al crear. Si la descripción de `add_dimension`
cambia, regenerá `docs/agentes/herramientas.md` desde `D:/PROGRAMA-r6` con `PYTHONPATH=D:/PROGRAMA-r6/clon
D:/PROGRAMA/clon/.venv/Scripts/omnicad.exe tools --markdown --output docs/agentes/herramientas.md` y corré
`tests/test_doc_agentes.py`.

## Tests (escribilos primero, mirá que fallen)
Al final de `clon/tests/test_restricciones_matriz.py`:
- `test_b228_distancia_entre_lineas_no_paralelas_se_rechaza`: con `agregar_cota` da `ErrorBoceto`; por el MCP
  (`api.llamar(s, "add_dimension", {...})`, mirá `tests/test_api_boceto.py` para armar la sesión) da `ok: false`.
- `test_b228_distancia_entre_paralelas_sigue_andando`: dos paralelas a 5, cota 7 → quedan a 7 (las dos puntas).
- `test_b228_un_archivo_viejo_con_esa_cota_se_abre`: `Boceto.desde_dict` de un dict con esa cota no falla.

## Verificación
Desde `D:/PROGRAMA-r6/clon` con `PYTHONPATH=D:/PROGRAMA-r6/clon`: ruff (`-m ruff check .`); `pytest
tests/test_restricciones_matriz.py -q` sin turno; después, con turno, los tests que mencionan `agregar_cota` o `add_dimension`
(`grep -l`), en tandas de ~25 archivos. Prohibido `tests_afectados.py --correr`, la suite completa y `pytest -n`.

## Informe
`D:/PROGRAMA-r6/evidencias/restr6/informe.md`: qué cambiaste, qué dice la ayuda de Fusion (ruta), la tolerancia elegida y por
qué, tests (rojo antes, verde después) y la salida REAL de ruff y de cada tanda (últimas líneas), lo que no pudiste verificar.
```

### Brief restr-7 (B-229)

```text
Corrida restr-7 · B-229 · OmniCAD (CAD paramétrico en Python). Todo en español.

## Dónde trabajás
- Worktree `D:/PROGRAMA-r7` (rama `restr-7`). Tocá SOLO archivos de este worktree. No commitees, no hagas push, no instales nada.
- Python: `D:/PROGRAMA/clon/.venv/Scripts/python.exe`, desde `D:/PROGRAMA-r7/clon`, con `PYTHONPATH=D:/PROGRAMA-r7/clon`.
- Leé `AGENTS.md`. Leé el código real y buscá todos los llamadores antes de editar; el cambio más chico que resuelve la causa;
  conservá los finales de línea (`solver.py` y `boceto.py` son LF). NO edites `docs/seguimiento/` ni `PROJECT_LOG.md`.
- Tests: un archivo chico con `-k` se corre SIN turno. Las tandas de varios archivos van con `../scripts/turno.py --plazo 900 --
  …` (puede esperar en fila). Escribí el informe ANTES de lanzar las tandas con turno.

## El ítem: B-229
AutoConstrain sin dato crea un punto SUELTO nuevo en (0,0) en vez de usar el origen del boceto:
```python
from omnicad.restricciones.boceto import Boceto
from omnicad.restricciones.solver import auto_restringir
b = Boceto(); b.agregar_rectangulo((10, 10), (40, 30))
antes = set(b.puntos); auto_restringir(b); print(set(b.puntos) - antes)   # {19}: punto nuevo en (0,0) con «fijo»
```
Código: `clon/omnicad/restricciones/solver.py › _cotas_auto` (~línea 1453): `origen = b.agregar_punto(0.0, 0.0)` +
`b.agregar_restriccion("fijo", [origen])`, fuera de `probar`: no cuenta para `limite`, no aparece en lo agregado e ignora
`excluir`. El boceto ya tiene una referencia fija del origen, id `Boceto.ORIGEN` (0), que se materializa con
`b.asegurar_referencias([Boceto.ORIGEN])` (`restricciones/boceto.py`, ~línea 2031) y no aporta GDL ni perfiles.

Ojo con una interacción nueva: desde B-223 (commit c63f2a4) la ventana materializa el origen apenas el usuario hace clic cerca.
Comprobá qué devuelve `b.puntos_fijos()` cuando el origen (id 0) ya está en `b.puntos`: si lo cuenta como fijo, `_cotas_auto`
cree que el boceto ya tiene dato y no acota la posición de nada. Las dos cosas (usar el origen y no confundirlo con un dato
del usuario) son el mismo arreglo.

Ayuda de Fusion: `D:/PROGRAMA/clon/.venv/Scripts/python.exe D:/PROGRAMA/scripts/fusion_docs.py ver "Finish a sketch with
AutoConstrain" -s fusion-sketch` (qué es el datum y qué pasa si está vacío). No inventes lo que la ayuda no dice.

Arreglo pedido: cuando no hay dato, las cotas de posición se miden desde la referencia del origen (id 0), sin crear un punto
nuevo ni un `fijo` extra; y el origen materializado no cuenta como «dato ya puesto» por el usuario. Revisá también la API
(`clon/omnicad/api/herramientas_boceto.py › auto_constrain`, `suggest_auto_constraints`) por si lee los puntos nuevos.

## Tests (escribilos primero, mirá que fallen)
Al final de `clon/tests/test_restricciones_matriz.py`:
- `test_b229_autorestringir_usa_el_origen_sin_crear_puntos`: tras `auto_restringir`, ningún punto nuevo además del 0, el
  rectángulo queda con GDL 0 y las cotas de posición nombran el 0.
- `test_b229_origen_materializado_no_es_un_dato`: con `b.asegurar_referencias([Boceto.ORIGEN])` antes, el resultado es el mismo.
- `test_b229_con_un_punto_en_el_origen_lo_fija`: si un punto del usuario ya está en (0,0), se usa ese (como antes).

## Verificación
Desde `D:/PROGRAMA-r7/clon` con `PYTHONPATH=D:/PROGRAMA-r7/clon`: ruff; `pytest tests/test_restricciones_matriz.py -q` sin
turno; después, con turno, los tests que mencionan `auto_restringir`, `auto_constrain` o `autorestringir` (`grep -l`), en tandas
de ~25 archivos. Prohibido `tests_afectados.py --correr`, la suite completa y `pytest -n`.

## Informe
`D:/PROGRAMA-r7/evidencias/restr7/informe.md`: qué cambiaste, qué dice la ayuda de Fusion (ruta), tests (rojo antes, verde
después) y la salida REAL de ruff y de cada tanda (últimas líneas), lo que no pudiste verificar.
```

### Brief restr-8 (B-230 y S7)

```text
Corrida restr-8 · B-230 y S7 · OmniCAD (CAD paramétrico en Python). Todo en español.

## Dónde trabajás
- Worktree `D:/PROGRAMA-r8` (rama `restr-8`). Tocá SOLO archivos de este worktree. No commitees, no hagas push, no instales nada.
- Python: `D:/PROGRAMA/clon/.venv/Scripts/python.exe`, desde `D:/PROGRAMA-r8/clon`, con `PYTHONPATH=D:/PROGRAMA-r8/clon`.
- Leé `AGENTS.md`. Leé el código real antes de editar; el cambio más chico; conservá los finales de línea (LF). NO edites
  `docs/seguimiento/` ni `PROJECT_LOG.md`.
- Tests: un archivo chico con `-k` se corre SIN turno. Las tandas de varios archivos van con `../scripts/turno.py --plazo 900 --
  …`. Escribí el informe ANTES de lanzar las tandas con turno.

## Ítem 1: B-230
`Boceto().agregar_restriccion("inventada", [p, q])` da `KeyError: 'inventada'` (`clon/omnicad/restricciones/boceto.py ›
_validar_restriccion`, ~línea 2600: `validas[tipo]()` y `TIPOS_RESTRICCION[tipo]`). Llega por `execute_code` o por un
`.omnicad` alterado. Lo mismo puede pasar con `agregar_cota` y un tipo de cota desconocido (`_validar_cota`): comprobalo.
Arreglo: un `ErrorBoceto` claro en español («Tipo de restricción desconocido: …») en los dos, al principio de la validación.
Test: `test_b230_tipo_desconocido_da_error_claro` al final de `clon/tests/test_restricciones_matriz.py` (restricción y cota).

## Ítem 2: S7 (contradicción entre la doc de la API y lo que acepta)
En `clon/omnicad/api/herramientas_boceto.py`:
- `add_constraint` (descripción ~línea 1423-1437): no nombra `curvature` ni dice que `equal` acepta elipses; dice que
  `tangent` y `concentric` son «dos curvas», pero `tangent` rechaza línea-línea.
- `add_dimension` (~línea 1538-1543): dice «offset: dos líneas o dos círculos/arcos», pero también acepta spline con spline,
  elipse con spline y elipse con elipse (`boceto.py › _validar_cota`, ~línea 2621).
Corregí SOLO el texto para que diga lo que el código acepta de verdad (comprobalo leyendo `_validar_restriccion` y
`_validar_cota`), en español, corto. Después regenerá la doc desde `D:/PROGRAMA-r8`: `PYTHONPATH=D:/PROGRAMA-r8/clon
D:/PROGRAMA/clon/.venv/Scripts/omnicad.exe tools --markdown --output docs/agentes/herramientas.md`, y corré
`tests/test_doc_agentes.py`.

## Verificación
Desde `D:/PROGRAMA-r8/clon` con `PYTHONPATH=D:/PROGRAMA-r8/clon`: ruff; `pytest tests/test_restricciones_matriz.py
tests/test_doc_agentes.py -q` sin turno; con turno, `tests/test_api_boceto*.py` en una tanda. Prohibido
`tests_afectados.py --correr`, la suite completa y `pytest -n`.

## Informe
`D:/PROGRAMA-r8/evidencias/restr8/informe.md`: qué cambiaste (archivo, función, texto viejo → nuevo), tests (rojo antes, verde
después) y la salida REAL de ruff y pytest (últimas líneas), lo que no pudiste verificar.
```

### Brief restr-9 (fase D)

```text
Corrida restr-9 · Fase D (integración ventana / API / archivo) de la auditoría de restricciones · OmniCAD. Todo en español.

## Dónde trabajás
- Worktree `D:/PROGRAMA-r9` (rama `restr-9`). Tocá SOLO archivos de este worktree. No commitees, no hagas push, no instales nada.
- Python: `D:/PROGRAMA/clon/.venv/Scripts/python.exe`, desde `D:/PROGRAMA-r9/clon`, con `PYTHONPATH=D:/PROGRAMA-r9/clon`.
- Leé `AGENTS.md` y `CLAUDE.md` (sección «toda prueba se hace como un usuario humano habitual»). Pruebas de ventana con eventos
  simulados de Qt, `OMNICAD_PRUEBA_VENTANA=minimizada`, sin mover el cursor real ni pedir el foco.
- Conservá los finales de línea (`ui/editor_boceto.py` es MIXTO: tus líneas nuevas copian el final de la línea vecina).
  NO edites `docs/seguimiento/` ni `PROJECT_LOG.md`.
- A TODO pytest agregale `--basetemp=D:/PROGRAMA-r9/evidencias/restr9/tmp`. Un archivo chico con `-k` va sin turno; las tandas
  de varios archivos con `../scripts/turno.py --plazo 900 -- …`. Escribí el informe ANTES de lanzar tandas con turno.
- Contexto: inventario y resultados en `docs/auditorias/restricciones_inventario_2026-11-06.md` (§5 sospechas, §6 fase B).

## Qué tenés que verificar (y arreglar si falla), en este orden; cada uno con su test
1. **S12** — la herramienta Cota de la ventana con UNA línea sola: ¿deja crear una cota horizontal o vertical (como la API,
   `distancia_h`/`distancia_v` con `[línea]`)? Mirá qué hace Fusion: `D:/PROGRAMA/clon/.venv/Scripts/python.exe
   D:/PROGRAMA/scripts/fusion_docs.py ver "Dimension sketch geometry" -s fusion-sketch`. Si Fusion lo hace y OmniCAD no, es un
   faltante: NO lo implementes, anotalo en el informe con la evidencia.
2. **S13** — Simetría en la ventana eligiendo el eje PRIMERO: ¿qué mensaje sale? Si no orienta («elegí los dos elementos y
   después el eje»), mejorá solo el mensaje (`ui/editor_boceto.py`, flujo de `_clic_restriccion` / `aplicar_restriccion`).
3. **S8** — Fijo en la ventana: elegir el mismo conjunto en otro orden ¿desfija? (`aplicar_restriccion`, la comparación
   `r.entidades == ents` contra la del modelo, que usa conjuntos). Si no desfija, que compare conjuntos.
4. **Guardar, cerrar, abrir, deshacer:** un boceto con una restricción de cada tipo de `TIPOS_RESTRICCION` y una cota de cada
   tipo de `TIPOS_COTA` (armalo por la API o por `Boceto`), guardado en un `.omnicad` en tu `tmp`, abierto de nuevo: mismas
   restricciones, mismas cotas y `resolver` igual. Después, por la API: `add_constraint` + `undo` + `redo` deja el boceto igual
   que antes/después (compará `get_sketch`).
5. **Mismo resultado por la ventana y por el MCP:** coincidente con el origen, punto medio con la línea primero y tangente con
   el círculo primero, hechos con clics en la ventana y con `api.llamar(..., "add_constraint", ...)`: mismas coordenadas finales.

Cada bug confirmado que arregles va con su test rojo antes y verde después. Lo que no arregles (faltante, o arreglo grande) lo
anotás en el informe como «Para el seguimiento» con caso mínimo y archivo:línea.

## Verificación
ruff; tus tests nuevos; después con turno los archivos de tests que tocan `editor_boceto` o restricciones de la ventana
(`grep -l "Lienzo\|editor_boceto" tests/test_*restric*.py tests/test_boceto_fase*_ui.py`), en tandas de ~20. Si tocaste
`ui/editor_boceto.py`, corré también la pieza de ventana: desde `clon/`, `OMNICAD_PRUEBA_VENTANA=minimizada
D:/PROGRAMA/clon/.venv/Scripts/python.exe ../scripts/prueba_ui/todo.py restricciones_boceto` (con PYTHONPATH del worktree;
mirá en la primera línea del log que importe la copia del worktree). Prohibido `tests_afectados.py --correr`, la suite completa,
el humo general y `pytest -n`.

## Informe
`D:/PROGRAMA-r9/evidencias/restr9/informe.md`: por cada punto 1-5: VERIFICADO / CORREGIDO / FALTANTE / NO VERIFICADO, con
evidencia (test, salida real, archivo:línea); qué cambiaste; la salida REAL de ruff, de cada tanda y de la pieza.
```

### Brief restr-10 (fase E, pendiente de lanzar)

```text
Corrida restr-10 · Fase E (validación con escenarios combinados) de la auditoría de restricciones · OmniCAD. Todo en español.

## Dónde trabajás
- Worktree `D:/PROGRAMA-r10` (rama `restr-10`). Tocá SOLO archivos de este worktree. No commitees, no hagas push, no instales nada.
- Python: `D:/PROGRAMA/clon/.venv/Scripts/python.exe`, desde `D:/PROGRAMA-r10/clon`, con `PYTHONPATH=D:/PROGRAMA-r10/clon`.
- Leé `AGENTS.md`. NO edites código del programa en esta corrida: solo escribís tests y el informe. Si un escenario falla, lo
  dejás como `pytest.param(..., marks=pytest.mark.xfail(strict=True, reason="<qué falla>"))` y lo anotás en el informe con caso
  mínimo: el coordinador abre la fila y lo manda a arreglar.
- A TODO pytest agregale `--basetemp=D:/PROGRAMA-r10/evidencias/restr10/tmp`. Un archivo con `-k` va sin turno.

## Qué tenés que escribir
`clon/tests/test_restricciones_escenarios.py`: escenarios combinados de la sección 8 de `docs/auditoria_restricciones.md`,
sin ventana (`Boceto` + `solver.resolver`, o la API `omnicad.api.llamar` cuando el escenario sea de MCP/CLI o del timeline),
cada uno comprobando con números (coordenadas, largos, ángulos, GDL de `solver.grados_de_libertad`) y que `resolver(...).ok`:
1 rectángulo parcialmente restringido + coincidente con el origen; 2 rectángulo con cotas y H/V (GDL 0 con origen); 3 triángulo
con largo, ángulo y coincidencias; 4 dos círculos concéntricos con radios; 5 arcos tangentes a líneas (ranura); 6 cadena de
líneas con coincidencias; 7 perfil cerrado con varias restricciones (GDL 0); 8 geometría fija y libre (lo fijo no se mueve);
9 simetría respecto de un eje; 10 restricción redundante (la ventana/API la rechaza o el GDL no baja: comprobá cuál y que no
rompa nada); 11 restricciones contradictorias (`ok=False` y el boceto no se corrompe: los valores siguen finitos); 12 borrar
una restricción intermedia (el resto se sigue cumpliendo); 13 cambiar una cota después de restringir; 14 spline con
coincidente en sus extremos; 16 guardar y abrir (`a_dict`/`desde_dict`) da el mismo resultado; 18 boceto grande (200
rectángulos con cotas) resuelve en menos de 5 s; 19 las mismas restricciones por MCP (`api.llamar`) que por `Boceto` dan las
mismas coordenadas; 20 un boceto que alimenta una extrusión (por la API: `create_sketch`, `draw_rectangle`, `extrude`), cambiar
una cota del boceto y que el volumen del cuerpo cambie en proporción sin errores en el timeline (mirá `tests/test_api_*.py` para
los nombres reales de las herramientas y sus parámetros: no los inventes).
Los escenarios 15 (proyecciones) y 17 (SVG/DXF importados) solo si encontrás en `clon/tests/` cómo armarlos sin ventana; si no,
anotalos como NO VERIFICADO.

## Verificación
ruff; `pytest tests/test_restricciones_escenarios.py -q` sin turno (rápido: menos de 30 s el archivo entero).

## Informe
`D:/PROGRAMA-r10/evidencias/restr10/informe.md`: escenario por escenario VERIFICADO / XFAIL (con caso mínimo y archivo:línea
sospechado) / NO VERIFICADO; la salida REAL de ruff y pytest.
```
