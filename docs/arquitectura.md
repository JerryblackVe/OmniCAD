# Arquitectura de OmniCAD

Versión 0.1.0 · ~52.000 líneas de aplicación y ~12.000 de pruebas (Python, 2026-10-09).
Las decisiones de abajo explican por qué OmniCAD está hecho así. Toman como referencia el flujo de trabajo de
Fusion 360 (su documentación y su API públicas), sin copiar código, textos ni recursos.

## 1. Capas

```
┌──────────────────────────────────────────────────────────────────────┐
│ ui/            PySide6: ventana estilo Fusion (cinta, navegador,     │
│                ViewCube, panel de datos, preferencias), visor 3D     │
│                OpenGL, boceto en la vista 3D, diálogos, timeline     │
├──────────────────────────────────────────────────────────────────────┤
│ timeline/      parametros.py  expresiones con unidades + tabla       │
│                operaciones.py features (objetos de entrada)          │
│                documento.py   timeline, marcador, recálculo, deshacer │
├───────────────────────────────┬──────────────────────────────────────┤
│ restricciones/                │ nucleo/                              │
│  boceto.py  modelo 2D         │  geometria.py  primitivas, extruir,  │
│  solver.py  mínimos cuadrados │   revolver, booleanos, teselado      │
│                               │  perfiles.py   regiones cerradas     │
│                               │  intercambio.py STEP / BREP          │
├───────────────────────────────┴──────────────────────────────────────┤
│ io_archivos/   exportar.py (STL, OBJ, STEP) · proyecto.py (.omnicad)  │
└──────────────────────────────────────────────────────────────────────┘
```

Reglas de dependencia (se respetan en el código):
- `ui` → `timeline`, `io_archivos`, `nucleo` (solo para medir/teselar). La UI no arma geometría.
- `timeline` → `restricciones`, `nucleo`. No conoce la UI.
- `restricciones` no depende de nadie (solo numpy/scipy).
- Solo `nucleo/` importa OpenCascade (`OCP`): cambiar de kernel toca una sola capa.

Punto de entrada: `clon/OmniCAD.py` (`--ejemplo`, `--prueba-humo`, o un `.omnicad` como argumento).

## 2. Decisiones y su justificación

| Decisión | Alternativas descartadas | Por qué |
|---|---|---|
| **Kernel B-rep OpenCascade** (`cadquery-ocp`) | Motor propio de mallas; pythonocc-core | Los CAD paramétricos trabajan sobre B-rep (sólidos exactos); STEP exige B-rep. `pythonocc-core` no está en PyPI; `cadquery-ocp` se instala con pip |
| **Interfaz PySide6 + OpenGL** | Tkinter, web | Qt es el estándar de las aplicaciones de escritorio técnicas; PySide6 es el Qt oficial para Python |
| **Timeline lineal con marcador, suprimir, reordenar y estado por paso** | Historial en árbol | Es el modelo de los CAD paramétricos de escritorio y el que conocen sus usuarios |
| **Operaciones = objetos de datos serializables + `ejecutar()`** | Llamadas directas al kernel desde la UI | La receta se guarda, se edita y se recalcula; la misma operación sirve a la UI y a la API de agentes |
| **Operación de cuerpo única para todas las features** (nuevo / unir / cortar / intersecar) | Booleanos solo como paso aparte | Una extrusión puede crear, sumar o restar sin pasos extra, como en Fusion |
| **Primitivas como pasos del timeline** | Cuerpos sueltos | Sus medidas quedan editables y paramétricas |
| **Rectángulo = 4 líneas + 2 horizontales + 2 verticales** | Entidad «rectángulo» | Cada lado se puede cotar, restringir y borrar por separado |
| **«Fijo» como restricción** | Propiedad del punto | Se guarda, se ve y se borra igual que las demás restricciones |
| **Cotas con expresiones** que usan parámetros | Solo números | Diseño paramétrico: cambiar un parámetro rehace la pieza |
| **Una unidad interna por magnitud** (mm, grados) + expresiones con unidades | Unidades mezcladas | mm es la unidad de STL, STEP e impresión 3D |
| **Perfiles derivados, no guardados**, referenciados por **firma** + centroide | Índice del perfil | Los índices cambian al editar el boceto; la firma sobrevive (problema de nombres topológicos) |
| **Boceto sobre una cara asociado a la cara** (referencia por firma + posición relativa a la caja, como los empalmes; el plano se recalcula en cada paso) | Marco congelado al crear | Como Fusion: si un parámetro mueve la cara, el boceto la sigue. Los proyectos viejos sin referencia conservan su marco |
| **Formato `.omnicad` = ZIP con receta JSON + caché B-rep + miniatura** | Guardar solo geometría | Abierto y legible: la receta es la fuente de verdad; la caché acelera la apertura |
| **Recalcular desde el paso editado**, con el estado de cada paso cacheado | Recalcular todo siempre | Editar el paso *i* reusa el estado *i-1* |
| **Error por paso sin romper el resto** | Abortar el recálculo | Un paso roto se marca y el resto del historial sigue visible |
| **Solver de restricciones propio** (scipy `least_squares` + regularización débil) | Solver externo | No hay un solver 2D simple instalable con pip en Windows |
| **Booleanas que fusionan caras coplanares** (`geo.unificar_caras`) | Dejar las caras partidas | Sin eso, un empalme que cruza la costura falla (prueba: L de 8 caras, no 14) |
| **Ejes Z hacia arriba** | Y hacia arriba | Lo habitual en CAD mecánico e impresión 3D |

### 2.1 Interfaz

| Decisión | Por qué |
|---|---|
| Disposición estilo Fusion: panel de datos a la izquierda, barra de app + cinta arriba, lienzo con navegador flotante, ViewCube y barra de navegación, timeline abajo | Es la disposición que ya conocen los usuarios de CAD paramétrico |
| Cinta con espacio de trabajo «DISEÑO ▾», pestañas y grupos con título desplegable | Igual que arriba: menos curva de aprendizaje |
| Lo no implementado aparece **grisado**, nunca como botón activo que no hace nada | Regla de honestidad del proyecto |
| Íconos **dibujados desde cero** con QPainter (`ui/iconos.py`, `ui/iconos_extra.py`) | No se copian recursos de otros programas |
| Preferencias con árbol, descripción y Restablecer / Aplicar / Aceptar / Cancelar, solo con opciones que funcionan | Regla de honestidad |
| Esquemas de ratón OmniCAD / Fusion / Tinkercad | Cada usuario elige el que ya conoce |
| **Boceto dentro de la vista 3D**: elegir plano o cara con un clic, «Mirar a» automático, pestaña BOCETO, paleta de boceto | Se dibuja en contexto, sin cambiar de ventana |
| Color por entidad del boceto (libre / totalmente restringida) | El solver calcula los grados de libertad que quedan |

## 3. Desviaciones conscientes respecto de Fusion

| En Fusion | En OmniCAD | Por qué |
|---|---|---|
| Primitivas sobre un plano elegido | Primitivas en coordenadas absolutas (posición X, Y, Z; eje Z) | Más simple de usar desde la API de agentes |
| Unidad interna cm | mm | Ver tabla anterior |
| Panel de datos en la nube, con versiones | Lista local de proyectos recientes con miniatura | OmniCAD no tiene nube |
| Preferencias de cuenta, red y recopilación de datos | No existen | Dependen de la nube o de una licencia |
| Sin API para agentes de IA | API única con servidor MCP, CLI y puente en vivo (sección 7) | Que cualquier agente pueda diseñar y mejorar el programa |

Lo que todavía falta respecto de Fusion está en [brechas_fusion.md](brechas_fusion.md).

## 4. Modelo de datos

- **Documento**: `parametros` (TablaParametros), `operaciones` (lista ordenada), `marcador`,
  `resultados` (estado por paso), estados cacheados, pilas de deshacer/rehacer (instantáneas JSON).
- **Operación**: `id` estable (`op7`), `nombre`, `suprimida`, `p` (parámetros como expresiones).
  `OpBoceto` lleva además un `Boceto`.
- **EstadoModelo** (resultado tras un paso): `cuerpos` {id → Cuerpo(forma OCC)} y `bocetos`
  {id → BocetoResuelto(plano, perfiles, resultado del solver)}. Ids de cuerpo: `op2.c1`.
- **Dependencias**: cada operación declara los pasos que usa (boceto, cuerpos). Con eso se
  bloquea borrar o reordenar algo que rompería el historial (como `canReorder`).

## 5. Formato `.omnicad`

ZIP (deflate) con:

| Entrada | Contenido |
|---|---|
| `manifiesto.json` | `formato: "OmniCAD-proyecto"`, `version_formato: 1`, app, fecha, unidades |
| `receta.json` | `version_receta`, parámetros, `marcador`, operaciones con sus parámetros y bocetos completos |
| `cache/cuerpos.brep` | Compuesto B-rep (opcional, sin la malla del visor): primero los cuerpos finales que no son malla (útil para otras herramientas), después las formas de los pasos lentos |
| `cache/pasos.json` | Resultado de los pasos que tardaron ≥ 0,1 s y solo cambiaron cuerpos: huella de la receta, cuántas formas son finales y, por paso, sus cuerpos y formas |
| `miniatura.png` | Captura del visor |

La receta es la única fuente de verdad. Al abrir, los pasos lentos se toman de la caché si la huella
(receta byte a byte + versión de la app) coincide; el resto se recalcula desde la receta. Si la huella no
coincide o la caché está dañada, se recalcula todo. Editar un paso recalcula como siempre.
La escritura es atómica (archivo temporal + reemplazo).
Autoguardado cada 60 s si hay cambios: `<proyecto>.autoguardado.omnicad` junto al proyecto, o
`%LOCALAPPDATA%\OmniCAD\autoguardado\` si todavía no se guardó. Al abrir se ofrece recuperar
el autoguardado si es más nuevo.

## 6. Equivalencias Fusion 360 ↔ OmniCAD

| Fusion 360 (API pública) | OmniCAD |
|---|---|
| `Design` (Parametric) | `timeline.documento.Documento` |
| `Timeline.markerPosition`, `TimelineObject.rollTo` | `Documento.marcador`, `mover_marcador()` |
| `TimelineObject.isSuppressed`, `reorder`, `canReorder` | `suprimir()`, `mover()`, `puede_mover()` |
| `FeatureHealthStates` | `ResultadoPaso.estado`: ok / aviso / error / suprimida / retrocedida |
| `UserParameters`, `ValueInput.createByString` | `TablaParametros`, `parametros.evaluar()` |
| `Sketch`, `SketchLines/Circles/Arcs` | `restricciones.boceto.Boceto` (`agregar_linea`, `agregar_circulo`, `agregar_arco_3_puntos`) |
| `addTwoPointRectangle` | `Boceto.agregar_rectangulo()` |
| `GeometricConstraints.add*` | `Boceto.agregar_restriccion(tipo, …)` (10 tipos) |
| `SketchDimensions.add*` | `Boceto.agregar_cota(tipo, …, expresion)` (6 tipos) |
| `isFullyConstrained` | `ResultadoSolver.totalmente_restringido` / grados de libertad |
| `Sketch.profiles` | `nucleo.perfiles.detectar()` |
| `ExtrudeFeatures` (+ `DistanceExtent`, `SymmetricExtent`) | `OpExtrusion` (`distancia`, `simetrica`) |
| `RevolveFeatures` (+ `AngleExtent`) | `OpRevolucion` (`eje`, `angulo`) |
| `CombineFeatures` | `OpCombinar` |
| `BoxFeature`, `CylinderFeature`, `SphereFeature`, `TorusFeature` | `OpPrimitiva` (`forma`) |
| `FeatureOperations` | `operacion`: nuevo / unir / cortar / intersecar |
| `ExportManager` STL / OBJ / STEP | `io_archivos.exportar` |
| `ImportManager.createSTEPImportOptions` | `OpImportarSTEP` (el STEP se embebe en la receta) |
| `.f3d` | `.omnicad` |

## 7. Capa de agentes

Una capa más, por encima del núcleo y del timeline, para que un agente IA use el programa sin ventana o mirándola en vivo
(plan y estado: [plan_mcp_cli.md](plan_mcp_cli.md)).

```
 agentes IA ──► servidor MCP (omnicad/servidor_mcp/) ─┐
 terminal  ──► CLI omnicad (omnicad/cli/)             ─┼─► omnicad/api/ (catálogo único) ─► timeline · nucleo · io_archivos
 scripts   ──► from omnicad import api                ─┘          │
                                                                  └─► docs/agentes/herramientas.md (generado)
```

| Pieza | Dónde | Qué hace |
|---|---|---|
| Catálogo único | `clon/omnicad/api/` (`registro.py`) | cada herramienta se define una vez con `@herramienta`; de ahí salen el MCP, la CLI y la documentación |
| Servidor MCP | `clon/omnicad/servidor_mcp/` | expone el catálogo por stdio o HTTP local; modo sin ventana o en vivo |
| CLI | `clon/omnicad/cli/` | el mismo catálogo desde la terminal, con `--json` y códigos de salida 0, 1 y 2 |
| Puente en vivo | `clon/omnicad/ui/puente.py` y `api/protocolo_puente.py` | deja que el servidor MCP controle la ventana abierta (apagado por defecto, solo 127.0.0.1) |
| Guía para agentes | `clon/omnicad/api/guia/*.md` | fuente única del flujo de trabajo; se sirve con `get_guide` |
| Documentación generada | `docs/agentes/herramientas.md` (`api/doc_markdown.py`) | `omnicad tools --markdown`; un test avisa si queda vieja |

- `api/` no importa Qt ni el paquete `mcp` (un test lo comprueba): solo `ui/` conoce Qt. El puente de la ventana es la única pieza de esta capa que usa Qt.
- Documentación para agentes: [docs/agentes/README.md](agentes/README.md). Ejemplos que corren dentro de pytest: [ejemplos/agentes](../ejemplos/agentes/README.md).
