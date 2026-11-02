# Extensiones de Fusion y herramientas de plástico

Especificación de PLA-1 a PLA-14 y EXT-1 a EXT-4. El estado vive solo en `docs/seguimiento/`.

**Fuente:** 92 capturas de `analisis/capturas_fusion (solo quedan las pendientes; ver su INDICE.md)`, la ayuda de `docs/fusion_docs/` y una prueba por API el 2026-11-01.

**Límite:** Fusion estaba cerrado. Lo que dice «comprobar en Fusion real» no se vio funcionando.

## Herramientas que se ven en las capturas

| Fusion (capturas) | OmniCAD | Estado | Fila |
|---|---|---|---|
| Grampa de fijación (Snap Fit) | Botón gris «Encaje a presión» | Falta | PLA-1 |
| Apoyo (Rest) | Botón gris «Apoyo» | Falta | PLA-2 |
| Saliente de fijación (Boss) | `saliente`: un solo lado | A medias | PLA-3 |
| Labio | `labio`: labio o ranura | A medias | PLA-4 |
| Asignar y Administrar reglas de plástico | Hechas, sin árbol ni editar | A medias | PLA-5 |
| Cinta PLÁSTICO | Tres grupos cortos | A medias | PLA-6 |
| Patrón geométrico | Casi completo | A medias | PLA-7 |
| Sólido delimitador | `cuerpo_envolvente` | A medias | PLA-8 |
| Simplificar | Submenú vacío | Falta | PLA-9 |
| Insertar fijador | 5 familias y 14 normas, sin biblioteca | A medias | PLA-10 |
| Menú del timeline | Casi completo | A medias | PLA-11 |
| Entramado volumétrico | `reticula_volumetrica`: 7 de 9 formas | A medias | SOL-22 |
| Valores predefinidos | `preajustes_ui.py` | Hecho, faltan detalles | PLA-14 |
| Consejos de diseño | `consejos_diseno` | Hecho | — |
| Sustainability Insights | `sustentabilidad` | Hecho | H-55 (mejora) |
| Duplicar con uniones | Está en ENSAMBLAR | Hecho, falta en INSERTAR | PLA-6 |
| Insertar malla, componente, derivación, SVG, DXF | Hechos | Hecho | — |
| McMaster, TraceParts, pieza de fabricante | No | Bloqueado | P-25g2 |

## Lo que dicen las páginas de extensiones

| Extensión | Función | OmniCAD | Fila |
|---|---|---|---|
| Design | Reglas de configuración | Botón gris | CFG-1 |
| Design | Conversión de malla orgánica | Solo facetado y prismático | PLA-12 |
| Design y Manufacturing | PMI (notas 3D de fabricación) | No existe | PLA-13 |
| Manufacturing | CAM de 3 a 5 ejes, inspección, aditiva | No existe | F20 |
| Manufacturing | Anidación y fabricación | No existe | EXT-1 |
| Simulation | Estudios de simulación | No existe | F19, EXT-2 |
| Simulation | Diseño generativo | No existe | EXT-3 |
| Fusion Manage | PLM en la nube | No existe | EXT-4 |

## Valores medidos

| Prueba | Resultado |
|---|---|
| Saliente en caja vaciada de 100 × 60 × 30, desde plano en Z 30 | Volumen 29472 → 30681,51 |
| Saliente con el boceto en el plano XY, debajo de la caja | Rechazo: «El cuerpo no está en la dirección del saliente» |
| Labio sobre las 4 aristas externas | Volumen 29946; caja de alto 31,5 |
| Ranura sobre las 4 aristas externas | Volumen 28916,54 |
| Labio con `>Z`, 8 aristas | Rechazo: pide una sola cadena |
| Patrón geométrico, 5 distribuciones | Corta en cara plana; radial 179743,22 |
| Patrón geométrico en cara de cilindro | Rechazo: «necesita una cara plana» |
| Sólido envolvente, cilindro de Ø60 × 60, margen 5 | Caja 70³ y cilindro Ø70 × 70 |
| Retícula Cruz, celda 10, solidez 30 | 8099,14 de 27000 |
| `octet_truss` y `honeycomb` | Tipo inválido |
| `delete_faces` sobre 4 empalmes | Vuelve a 50000. No tiene botón |
| `remove_fillets` | Vuelve a 50000. No cubre agujeros ni chaflanes |

## Detalle de cada fila

**PLA-1 Grampa de fijación.** Tres tipos: gancho y ranurado paralelos, gancho y ranurado perpendiculares, gancho y contorno. Modo de selección Automático o Manual. Giro Uniforme, Independiente o Alineado. Extensión Hasta el siguiente o Distancia. Ayuda: `Create a snap fit`.

**PLA-2 Apoyo.** Perfil cerrado y cuerpo. Desfase de posición, Grosor, Lado 1 y Lado 2, ángulo de desmoldeo, extensión Todo o Hasta objeto. Avanzado: Caras superiores y Recortar. Ayuda: `Create a rest`.

**PLA-3 Saliente.** Dos lados y dos cuerpos. Lado 1: agujero simple, escariado o avellanado, y escalón. Lado 2: profundidad desde abajo, desde arriba o pasante. Sección Fijador: cabeza, accionamiento, rosca, largo y material. Pestaña de nervios: cantidad, ángulo total, giro, perfil y grosor. Ayuda: `Create a boss`.

**PLA-4 Labio.** Falta el tipo Labio y acanalado sobre dos cuerpos, con la ranura calculada del labio y la holgura. Falta la casilla Cadena tangente, Guía de cara, extensiones y pestaña Avanzado. Ayuda: `Create a lip and groove`.

**PLA-5 Reglas de plástico.** Árbol «En este diseño» y «Biblioteca». Elegir el componente en el lienzo. Editar y Nueva regla desde una existente. Quitar la regla desde el navegador. Las reglas de fábrica de Fusion son ABS 1,5 mm, Nilón 2,5 mm y Polipropileno 3 mm, más sus versiones de 0,1 pulgadas. Las de OmniCAD son otras.

**PLA-6 Cinta y nombres.** Grupo CONFIGURACIÓN con las dos reglas. CREAR con todo lo del menú de SÓLIDO. «Duplicar con uniones» también en INSERTAR. Nombres de Fusion en español: Saliente de fijación, Grampa de fijación, Labio, Sólido delimitador, Entramado volumétrico, Insertar fijador. En el timeline, Fusion dice «Suprimir» para borrar y «Desactivar operaciones» para suprimir; OmniCAD dice «Eliminar» y «Suprimir». Quien venga de Fusion puede borrar o no borrar sin querer.

**PLA-7 Patrón geométrico.** Con objeto personalizado faltan Dirección perpendicular, Cambiar y Expandir con deslizador. Fusion arranca en Cuerpo nuevo y OmniCAD en Cortar. Falta comprobar en Fusion real si acepta caras curvas: la opción «Dirección de cara» sugiere que sí.

**PLA-8 Sólido delimitador.** Seis tipos: caja, cilindro y tubo, cada uno fijo o relativo. Modo de desfase: Sin desfase, Lados simétricos, Todas las direcciones, con desfase por lado. Redondeo. Modo de origen: Origen del modelo, Punto seleccionado, Punto del cuadro del modelo, Punto del cuadro sólido. Cotas en vivo: Anchura, Profundidad y Altura.

**PLA-9 Simplificar.** Eliminar operaciones: empalmes, agujeros, chaflanes, extrusiones y otras, con deslizador de tamaño y elección manual. Eliminar caras: ya existe `delete_faces`, falta el comando. Reemplazar con primitivas: caja, cilindro o esfera. Ayuda en `fusion-simulate`: `Remove Features`, `Remove Faces`, `Replace with Primitives`.

**PLA-10 Insertar fijador.** Buscador. Filtro por 16 organizaciones y por Imperial o Métricas. Árbol: Arandelas (Cuadrado, Muelle, Normal), Inserciones, Pernos y tornillos, Remaches, Tuercas. Favoritos. Vistas Lista y Azulejo. Columnas a elegir. Filtros por medida con deslizador. Ayuda: `Insert Fastener reference`, `Edit a fastener`, `Replace a fastener`.

**PLA-11 Timeline.** Falta «Convertir en operación de DM». La ayuda local no la explica: comprobar en Fusion real qué hace.

**PLA-12 Malla orgánica.** Método Orgánico, Operación Paramétrica o Base, resolución por precisión o por caras, Preprocesar agujeros. Ayuda: `Convert a mesh body to a solid body`. Se relaciona con F10, F11 y RI-1.

**PLA-13 PMI.** Utilidades › Crear PMI: nota de agujero o rosca y nota libre, sobre el modelo 3D. Ayuda: `Product Manufacturing Information (PMI)`.

**PLA-14 Valores predefinidos.** El menú de Fusion suma Restablecer y Ordenar por.

**SOL-22 Entramado.** Faltan OctetoTruss y Panal, que están en la captura y no en la ayuda local. Pestañas Configuración, Solidez y Desfase. Desplazar y girar con manipulador. Botón Restablecer.

## Prompt para el agente

Entregado el 2026-11-01. Modelo sugerido: Opus 5, esfuerzo alto. Antes de usarlo, revisar que los IDs y las rutas sigan vigentes.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá con la herramienta Skill: fable-method, ponytail, plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá ponytail-review con la herramienta Skill y pegá su salida real en el informe.

OBJETIVO
Completar en OmniCAD las herramientas de plástico y de la extensión de diseño de Fusion: cerrar PLA-1 a PLA-11, PLA-13, PLA-14 y lo que queda de entramado en SOL-22.

CONTEXTO DEL AGENTE
- Plataforma: Claude Code en D:\PROGRAMA, sobre main.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, pytest, ruff, MCP de OmniCAD, scripts/fusion_docs.py y scripts/prueba_ui/.
- Reglas del proyecto: CLAUDE.md y AGENTS.md. Otros agentes pueden estar trabajando en la misma carpeta.

TAREA PRINCIPAL
Agregar Grampa de fijación, Apoyo y Simplificar, completar las herramientas que están a medias y dejar la cinta PLÁSTICO como la de Fusion.

ENTRADAS
- Especificación y valores medidos: docs/brechas_extensiones.md → [PROVIDED]
- Filas: docs/seguimiento/faltantes.md, sección «Plástico y extensiones contra capturas de Fusion», y SOL-22 → [PROVIDED]
- Capturas: analisis/capturas_fusion (solo quedan las pendientes; ver su INDICE.md)→ [PROVIDED]
- Ayuda de Fusion: docs/fusion_docs/, con clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar y ver. Carpetas fusion-model, fusion-simulate, fusion-designs → [PROVIDED]
- Código de partida: ui/cinta.py, ui/comandos/plastico.py, ui/comandos/fijacion.py, ui/preajustes_ui.py, ui/panel_timeline.py, nucleo/fijaciones.py, nucleo/reticula.py → [PROVIDED]
- Qué hace «Convertir en operación de DM» en Fusion → [TO BE DISCOVERED BY AGENT]
- Si Patrón geométrico acepta caras curvas en Fusion → [TO BE DISCOVERED BY AGENT]

PROCESO
1. Leer docs/brechas_extensiones.md y el artículo de la ayuda de cada fila, hasta poder citar cada opción. Mirar las capturas de cada herramienta.
2. Reproducir por API la tabla «Valores medidos». [REQUIERE: paso 1]
3. PLA-6: ordenar la cinta PLÁSTICO y los nombres de Fusion, sin romper las claves de los comandos. Terminar cuando el grupo CONFIGURACIÓN exista, CREAR tenga los ítems del menú de SÓLIDO y «Duplicar con uniones» esté también en INSERTAR. En el timeline, dejar las etiquetas sin cambiar el comportamiento y anotar en el informe el cambio de nombres propuesto.
4. PLA-14, PLA-5, PLA-8 y PLA-7: completar los campos que faltan, cada uno con su herramienta de API. Terminar cuando cada opción de las capturas tenga su campo y una prueba numérica. [REQUIERE: paso 3]
5. PLA-7: probar en Fusion real si acepta caras curvas, usando el MCP fusion360. Si acepta, implementarlo. Si Fusion no conecta, dejar esa parte Parcial con lo probado.
6. SOL-22: agregar OctetoTruss y Panal y pasar el panel a las pestañas Configuración, Solidez y Desfase. Terminar cuando cada forma dé un volumen coherente con su solidez.
7. PLA-9: agregar Eliminar caras sobre delete_faces, Eliminar operaciones y Reemplazar con primitivas. Llenar el submenú Simplificar. Reusar lo que ya reconoce funciones en vez de escribirlo de nuevo.
8. PLA-4: agregar Labio y acanalado sobre dos cuerpos, Cadena tangente, guía y extensiones.
9. PLA-3: agregar el segundo lado, el fijador y los nervios. Lo que hoy hace `create_boss` debe seguir dando el mismo volumen: 30681,51 en la caja medida.
10. PLA-2: crear Apoyo en núcleo, timeline, comando, cinta y API. Terminar con una pieza vaciada que deje un área plana.
11. PLA-1: crear Grampa de fijación con sus tres tipos. Terminar cuando cada tipo una dos cuerpos sin interferencia.
12. PLA-10: construir el panel de biblioteca sobre las normas actuales: buscador, filtros, árbol, favoritos, vistas y columnas. Sumar las familias que falten solo con medidas de normas públicas. No copiar la biblioteca de Fusion.
13. PLA-11: comprobar en Fusion real «Convertir en operación de DM». Si se entiende, agregarla. Si no, dejar la fila abierta.
14. PLA-13: agregar las notas PMI de agujero o rosca y la nota libre, guardadas en el documento y visibles en el visor.
15. Dar a cada función nueva o cambiada su herramienta en clon/omnicad/api/ y regenerar docs/agentes/herramientas.md.
16. Agregar tests con resultado numérico en clon/tests/ y una pieza `plastico` en scripts/prueba_ui/: elegir, teclear, vista previa, Aceptar, reabrir, deshacer, Esc y ventana chica.
17. Correr ruff, los tests tocados con scripts/turno.py y la pieza de ventana con la ventana minimizada. Mirar las capturas y compararlas con las de Fusion.
18. Borrar de docs/seguimiento/ las filas resueltas, anotar en el Registro de PROJECT_LOG.md cada ID con su prueba, actualizar docs/auditorias/prueba_nocturna_2026-10-31.md y anotar la lección si hubo un error verificable.
19. Invocar ponytail-review con la herramienta Skill y corregir lo que encuentre.

DEPENDENCIAS
- 3 va antes de todo lo que agrega botones.
- 8 va antes de 9. 9 va antes de 11, porque comparten los dos lados y la transparencia.
- 4, 6, 7, 12 y 14 no dependen entre sí.
- 15 a 19 van después de todos los arreglos.

REGLAS
- SÍ leer el artículo de la ayuda antes de cambiar cada comportamiento.
- SÍ hacer el cambio más chico que resuelve cada fila.
- SÍ probar como una persona: clics, arrastres y teclado con eventos simulados.
- SÍ escribir todo en español, con nombres de herramientas y parámetros de la API en inglés.
- SÍ mantener Qt solo en ui/.
- SÍ abrir recetas viejas sin cambiar su volumen.
- NO hacer PLA-12, EXT-1, EXT-2, EXT-3 ni EXT-4: van aparte.
- NO cambiar qué hacen «Eliminar» y «Suprimir» en el timeline sin el OK de Gerardo.
- NO copiar datos ni archivos de la instalación de Fusion.
- NO correr el cierre completo ni la suite entera: va de noche, cuando Gerardo lo diga.
- NO tocar archivos ajenos a estas filas. Si hace falta, anotarlo en el informe.
- NO hacer commit ni push sin que Gerardo lo pida.
- NO gastar en APIs pagas ni instalar paquetes sin permiso.
- NO usar `git add -f` ni subir privado/, analisis/ ni evidencias/.

MANEJO DE ERRORES
- Paso 2: PARAR Y REPORTAR si los valores no coinciden con la tabla.
- Pasos 5 y 13: SALTAR Y CONTINUAR si Fusion real no está disponible, dejando la parte abierta.
- Pasos 9 a 11: PARAR Y REPORTAR si la operación deja un cuerpo inválido después de 2 intentos.
- Paso 17: PARAR Y REPORTAR con la salida real si algo sigue rojo después de 2 intentos de arreglo.
- Default: PARAR Y REPORTAR.

CRITERIO DE ÉXITO
- La cinta PLÁSTICO tiene los mismos grupos que la captura y ningún botón gris de esta tarea.
- Grampa, Apoyo y Simplificar funcionan por ventana, API y CLI.
- Los sólidos que resultan pasan `geo.es_valida`.
- El Saliente de hoy conserva su volumen.
- ruff y los tests tocados están en verde, con la pieza de ventana corrida y las capturas revisadas.
- Seguimiento, PROJECT_LOG y lista nocturna quedan al día.
- La salida real de ponytail-review está pegada en el informe.

SALIDA ESPERADA
Informe en español, corto:
- Tabla: ID, cerrado o abierto, prueba que lo cubre.
- Firma de cada función pública nueva y qué hace.
- Salida real de ruff, pytest, la pieza de ventana y ponytail-review.
- Una línea con ⚠ por cada cosa no verificada.
- Una línea sobre si el modelo alcanzó.

COMPORTAMIENTO DEL AGENTE
- Ejecutá las instrucciones literalmente. No parafrasees ni reinterpretes.
- Si falta una entrada marcada como TO BE DISCOVERED, seguí la regla del paso que la usa.
- No agregues contenido que no sea derivable de las entradas.
- No asumas intención más allá de lo explícitamente declarado.
- Priorizá precisión sobre velocidad.
- Si un paso falla, seguí la regla de MANEJO DE ERRORES correspondiente.
```
