# Reconstruir sólido: de una malla a una pieza paramétrica

Convierte un STL, OBJ o 3MF en una pieza nueva, hecha con pasos normales del timeline: bocetos, extrusiones, revoluciones,
agujeros, empalmes y patrones. No convierte triángulos en caras: mide la pieza y la vuelve a modelar.

Estado por fila en `docs/seguimiento/faltantes.md` (RI-2 a RI-6). Revisado el 2026-11-01. Las fases 0 a 3 están construidas
(`scripts/bench_reconstruir.py`, `compare_to_mesh`, `analyze_mesh_features`, `reconstruct_from_mesh`); las metas de abajo ya llevan lo medido.

## Por qué

Convertir malla de Fusion copia la malla en lugar de entenderla:

- **Facetado:** una cara por triángulo.
- **Prismático:** une caras por grupos.
- **Límite:** Autodesk avisa que con más de 10.000 triángulos no conviene convertir y que el rendimiento baja.
  Fuente: [artículo de soporte](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Fusion-360-performance-slows-after-inserting-mesh.html).

**Competencia:** Fusion no lo trae, pero sí existe como complemento pago. Backflip AI ofrece malla a CAD con historial, con
un agente que revisa su propio resultado; rinde mejor en piezas fresadas y torneadas de complejidad media, y arranca en
USD 20 por mes. Fuente: [DEVELOP3D, 2026-08-04](https://develop3d.com/ai/backflip-ai-reverse-engineering/). OmniCAD lo
tendría integrado, con la IA que elija cada usuario.

**Investigación:** [CADFit](https://arxiv.org/html/2605.01171v3) (ICML 2026) reconstruye con extrusión, revolución, empalme,
chaflán y booleanas. Saca perfiles de planos y cortes, ajusta medidas, valida con el kernel y corrige lo que sobra o falta.
Su red neuronal solo ordena candidatos. Sufre con superficies libres y mallas sucias. Se usa como idea: la licencia de su
código no está confirmada, y se escribe desde cero.

## Idea central

**La geometría la mide el código, la intención la decide la IA y el resultado lo juzga una medición.**

La IA nunca lee triángulos ni inventa medidas. Recibe una ficha con lo medido, imágenes y cortes, y propone cómo se modela.

| Paso | Quién | Qué hace |
|---|---|---|
| 1. Preparar | Código | Repara, pregunta las unidades del STL, orienta la pieza y distingue CAD de escaneo |
| 2. Medir | Código | Detecta planos, cilindros, conos, esferas y toros; simetrías, agujeros y patrones |
| 3. Proponer | Reglas o IA | Elige el orden de operaciones; redondea 19,98 a 20; reconoce un M6; nombra parámetros |
| 4. Construir | Código | Crea pasos normales del timeline con la API, en una sola transacción |
| 5. Juzgar | Código | Mide desviación, volumen, caja y solapamiento contra la malla |
| 6. Corregir | Reglas o IA | Agrega lo que falta y corta lo que sobra, con tope de vueltas y de gasto |
| 7. Entregar | Código | Deja la pieza, la malla oculta y un informe con lo que no pudo recuperar |

## Qué ya tiene OmniCAD

| Pieza | Dónde |
|---|---|
| Importar y reparar mallas, grupos de caras | `nucleo/malla.py`, `api/herramientas_malla.py` |
| Corte de malla y ajuste de curvas | `nucleo/malla_seccion.py`, `create_mesh_section_sketch`, `fit_curves_to_mesh_section` |
| Reconocer agujeros, empalmes, chaflanes, patrones, extrusión y revolución en un B-rep | `nucleo/reconocer_funciones.py`, `rebuild_features` |
| Todas las herramientas para construir | `api/`, MCP y CLI |
| Asistente con Claude, OpenAI, OpenRouter, modelo local y suscripciones, con tope en USD | `asistente/` |

**Falta lo central:** detectar primitivas en la malla (F11), medir la desviación (F10) y el armado de la pieza (RI-2).

## Decisiones

- **Primero las herramientas, después el botón.** Con ellas, cualquier agente por MCP ya puede reconstruir.
- **Anda sin IA.** Las reglas cubren lo simple. La IA suma intención y piezas difíciles.
- **El juez va antes que la IA.** Sin medición, la IA puede decir que quedó bien sin que sea cierto.
- **Cada usuario usa su proveedor.** Cada corrida muestra el tope de gasto. Sin clave, corre sin IA.
- **Privacidad:** la IA recibe ficha e imágenes, no el archivo. El panel lo dice antes de enviar.
- **Nunca finge.** Lo que no entra en la tolerancia queda marcado en rojo y en el informe.
- **Primer alcance:** piezas mecánicas, torneadas e impresas. Lo orgánico queda para RI-6.

## Opción del usuario

| Resultado | Qué entrega |
|---|---|
| **Paramétrico** (por defecto) | Timeline con bocetos acotados, parámetros con nombre, patrones y simetrías. Cambiar una medida recalcula la pieza |
| **Sólido limpio** | Timeline editable con medidas fijas, sin parámetros de usuario. Más rápido |

## Interfaz aprobada

Gerardo aprobó esta maqueta el 2026-11-01. Se ve en el tema Azul profesional, sin colores propios: el panel usa los tokens de
`ui/temas.py`. El botón **Reconstruir sólido** va en MALLA › MODIFICAR, al lado de Convertir malla. El panel va a la derecha de
la vista 3D, y los números de abajo son de ejemplo.

**1. Configurar.** La vista muestra la malla con sus triángulos.

| Fila | Control |
|---|---|
| Malla | Selección, con nombre del archivo y quitar |
| Unidades | Lista; solo para STL |
| Calidad | Texto detectado, por ejemplo «Origen CAD, sin ruido» |
| Tolerancia | Valor con unidad; 0,10 mm por defecto |
| Resultado | Dos botones: Paramétrico (por defecto) · Sólido limpio |
| Motor | Dos botones: Sin IA · Con IA |
| Proveedor · Gasto máximo | Solo con IA; lista y USD 0,50 por defecto |
| Nota | Con IA: «La IA recibe medidas e imágenes, no tu archivo.» Sin IA: «Usa reglas locales. No sale nada de tu PC.» |
| Pie | Cancelar · **Reconstruir** |

**2. Calculando.** La vista pinta las formas detectadas, con leyenda y cantidades: planos, cilindros y empalmes.

- Barra de avance, vuelta actual y tiempo.
- Lista de pasos con su estado: Preparar malla, Medir formas, Proponer modelado, Construir, Comparar con la malla.
- Gasto actual contra el máximo, solo con IA.
- Los pasos nuevos aparecen en el timeline mientras se crean.
- Pie: Cancelar.

**3. Resultado.** La vista pinta el mapa de desviación, con escala de 4 colores; el rojo marca lo que pasa la tolerancia.

- Cuatro medidas: desviación máxima, porcentaje dentro de tolerancia, caras y diferencia de volumen.
- Aviso con cada zona fuera de tolerancia.
- Paramétrico: lista de parámetros creados, con su valor editable. Sólido limpio: nota de medidas fijas.
- **Mostrar:** Mapa de desviación, sólido o malla original.
- La malla queda oculta en el timeline.
- Pie: Cancelar · **Otra vuelta** · **Aceptar**. Otra vuelta corrige lo que quedó en rojo sin empezar de cero.

## Fases

| Fase | Fila | Qué se hace | Terminada cuando |
|---|---|---|---|
| 0 · Banco | RI-1 | 30 piezas generadas con OmniCAD, exportadas a STL, OBJ y 3MF, más STL reales de Gerardo | Un script da tabla de resultados |
| 1 · Juez | F10 | `compare_to_mesh`: desviación en dos sentidos y mapa de color | Una pieza igual da casi 0 y una alterada marca la zona |
| 2 · Medir | F11 | `analyze_mesh_features`: ficha JSON de primitivas | Encuentra radios y ejes del banco |
| 3 · Reglas | RI-2 | `reconstruct_from_mesh` sin IA: cortes, extrusión, revolución, agujeros, empalmes, patrones | Metas de abajo en prismáticas y torneadas |
| 4 · Ventana | RI-3 | Panel, avance, cancelar, mapa e informe | Prueba como usuario de principio a fin |
| 5 · Paramétrico | RI-4 | Restricciones, cotas, parámetros, patrones y simetrías | Cambiar 3 medidas recalcula sin errores |
| 6 · IA | RI-5 | Ficha, vistas y cortes a la IA; vueltas de corrección; tope de gasto | Supera a las reglas en las piezas difíciles |
| 7 · Libre | RI-6 | Superficies libres para lo orgánico | Se decide con datos del banco |

La fase 3 ya es un primer producto: se puede usar por MCP y por ventana cuando esté la fase 4.

## Metas

Para mallas de origen CAD del banco. La tercera columna es lo medido el 2026-11-01 con `scripts/bench_reconstruir.py`, en 30 piezas.

| Medida | Meta | Medido |
|---|---|---|
| Desviación máxima | 0,1 mm o la tolerancia elegida | 30 de 30; la peor, 0,055 mm |
| Volumen | Diferencia menor a 0,5 % | 30 de 30; la peor, 0,25 % |
| Caras | Hasta 1,5 veces las del original | 30 de 30, y las 30 con la misma cantidad que el original |
| Timeline | Sin pasos en error; cuerpo válido | 30 de 30, también al guardar, reabrir, recalcular y editar una cota |
| Tiempo | Menos de 2 minutos para 200.000 triángulos, sin congelar la ventana | 311.296 triángulos: formas 4,4 s, reconstrucción 19,5 s; la ventana queda para RI-3 |
| Memoria | Dentro del tope de 3 GB por tarea de `scripts/turno.py` | Pico de 0,62 GB |

**STL reales de Gerardo (51 archivos):** 6 cumplen todo, 11 cumplen el volumen y 50 no dejan pasos en error. La mediana de la desviación es 4,2 mm. No alcanzan porque
combinan direcciones: vasos inclinados de pared fina, revolución con una caja oblicua, esquinas con esferas y moleteados. Lo que falta está en RI-2. Dos piezas tardan más de 5 minutos
(H-57) y una de ellas pasa los 10.

## Riesgos

| Riesgo | Respuesta |
|---|---|
| La IA inventa medidas | Solo usa valores de la ficha, y el juez mide todo |
| Escaneos con ruido | Tolerancia, reparar antes y avisar la calidad detectada |
| Piezas orgánicas | Informe honesto y RI-6; no se promete resultado |
| STL sin unidades | Preguntar siempre; sugerir por el tamaño |
| Lentitud en Python | Proceso aparte; medir, y pasar a Rust lo que el perfil señale |
| Costo de IA | Tope por corrida y modo sin IA |
| Patentes o licencias | Se escribe desde cero y se revisa antes de copiar una idea concreta de un paper |

## Prompt para el agente

Entregado el 2026-11-01. Modelo sugerido: Opus 5, esfuerzo alto. Antes de usarlo, revisar que los IDs y las rutas sigan vigentes.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá con la herramienta Skill: fable-method, ponytail, plan-then-do, tool-calling-guard, verify-before-commit y omnicad-test.
Antes de cerrar, invocá ponytail-review con la herramienta Skill y pegá su salida real en el informe.

OBJETIVO
Construir las fases 0 a 3 de Reconstruir sólido: banco, juez, medición de formas y reconstrucción sin IA de una malla a una pieza con timeline.

CONTEXTO DEL AGENTE
- Plataforma: Claude Code en D:\PROGRAMA, sobre main.
- Herramientas: archivos, Bash, Python del venv en clon/.venv, numpy, scipy, OpenCascade por OCP, pytest, ruff, MCP de OmniCAD, scripts/fusion_docs.py, scripts/turno.py y scripts/prueba_ui/.
- Reglas del proyecto: CLAUDE.md y AGENTS.md. Otros agentes pueden estar trabajando en la misma carpeta.

TAREA PRINCIPAL
Cerrar RI-1, F10, SC13, F11 y RI-2 con herramientas nuevas en la API, medidas sobre un banco de piezas con respuesta conocida.

ENTRADAS
- Plan: docs/plan_reconstruir_solido.md → [PROVIDED]
- Filas: docs/seguimiento/faltantes.md (RI-1, RI-2, F10, F11, SC13) → [PROVIDED]
- Especificación de comparar cuerpos: docs/brechas_solidcraft.md (SC13) → [PROVIDED]
- Ayuda de Fusion: docs/fusion_docs/contenido/fusion-mesh: convert-a-mesh-body-to-a-solid-body, create-a-mesh-section-sketch → [PROVIDED]
- Referencia de método: https://arxiv.org/html/2605.01171v3 → [PROVIDED]
- Código de partida: nucleo/malla.py, nucleo/malla_seccion.py, nucleo/reconocer_funciones.py, api/herramientas_malla.py, api/herramientas_malla_seccion.py, api/herramientas_reconocer.py, nucleo/analisis.py, nucleo/aislado.py → [PROVIDED]
- STL reales de Gerardo → [REQUIRED FROM USER]

PROCESO
1. Leer el plan, las filas, la ayuda, el paper y el código de ENTRADAS hasta poder citar qué existe y qué falta.
2. Fase 0, RI-1: crear scripts/bench_reconstruir.py y 30 piezas generadas con la API de OmniCAD: 12 prismáticas, 8 torneadas, 6 con empalmes y chaflanes, 4 con patrones. Exportarlas a STL, OBJ y 3MF. Guardar volumen, área, caja, cantidad de caras y pasos esperados como respuesta conocida. Terminar cuando el script imprima una tabla por pieza. Dejar los archivos generados fuera de git. [REQUIERE: paso 1]
3. Fase 1, F10 y SC13: crear en nucleo/ la comparación entre sólido y malla, y entre dos cuerpos: desviación en los dos sentidos, máximo, media, porcentaje dentro de tolerancia, volumen y solapamiento. Terminar cuando una pieza igual dé casi 0 y otra con un agujero corrido 1 mm marque esa zona. [REQUIERE: paso 2]
4. Agregar la herramienta `compare_to_mesh` y el análisis con mapa de color en INSPECCIONAR, con escala, mínimo, máximo y valor bajo el cursor. Seguir la Receta B y la Receta C de AGENTS.md. [REQUIERE: paso 3]
5. Fase 2, F11: crear en nucleo/ la medición de formas sobre la malla: planos, cilindros, conos, esferas y toros, más el resto sin clasificar. Usar semilla fija para que dos corridas den lo mismo. Detectar vecindad, simetrías, agujeros y patrones. [REQUIERE: paso 2]
6. Agregar la herramienta `analyze_mesh_features`, que devuelve una ficha JSON estable con cada forma, sus medidas, su área, su error de ajuste, sus vecinas y el porcentaje sin clasificar. Terminar cuando encuentre radios y ejes del banco dentro de la tolerancia. [REQUIERE: paso 5]
7. Medir tiempo y memoria de la fase 2 con 200.000 triángulos. Correr lo pesado en proceso aparte. Si el perfil señala un cuello de botella, anotarlo en docs/seguimiento/mejoras.md; no instalar Rust sin permiso. [REQUIERE: paso 6]
8. Fase 3, RI-2: crear la reconstrucción sin IA: orientar, elegir cortes, sacar perfiles, ajustar extrusiones, revoluciones, agujeros, empalmes, chaflanes y patrones, y crear pasos normales del timeline. [REQUIERE: pasos 4 y 6]
9. Agregar la vuelta de corrección: comparar, sumar lo que falta, cortar lo que sobra, con tope de vueltas. Terminar cuando la vuelta se detenga sola si no mejora. [REQUIERE: paso 8]
10. Agregar la herramienta `reconstruct_from_mesh`, atómica y con un solo deshacer. Tiene que dejar la malla oculta y devolver desviación, cantidad de caras, pasos creados, zonas fuera de tolerancia y lo que no pudo recuperar. Si no alcanza la tolerancia, igual lo informa con claridad. [REQUIERE: paso 9]
11. Correr el banco completo con scripts/turno.py y pegar la tabla contra las metas del plan. Si hay STL reales de Gerardo, sumarlos. [REQUIERE: paso 10]
12. Agregar tests con resultado numérico y `geo.es_valida`, y una pieza de ventana para el mapa de color. Probar con mallas vacías, abiertas, sucias, con unidades raras y con archivos enormes.
13. Regenerar docs/agentes/herramientas.md y actualizar con valores medidos las metas del plan.
14. Correr ruff, los tests tocados con scripts/turno.py y la pieza con la ventana minimizada. Mirar las capturas.
15. Borrar de docs/seguimiento/ las filas cerradas, anotar en PROJECT_LOG.md cada ID con su prueba, actualizar docs/auditorias/prueba_nocturna_2026-10-31.md y la hoja de ruta de los dos README.
16. Invocar ponytail-review con la herramienta Skill y corregir lo que encuentre.

DEPENDENCIAS
- 2 va antes de todo el código nuevo.
- 3 y 4 van antes de 8: sin juez no se reconstruye.
- 5 y 6 van antes de 8.
- 12 a 16 van después de la reconstrucción.

REGLAS
- SÍ crear pasos normales del timeline, que se puedan editar como cualquier otro.
- SÍ reutilizar nucleo/reconocer_funciones.py, las secciones de malla y las herramientas de la API.
- SÍ mantener funciones puras en nucleo/, sin Qt y con docstring.
- SÍ validar toda malla como archivo ajeno: tope de tamaño y mensaje claro.
- SÍ fijar la semilla de todo lo aleatorio.
- SÍ mostrar lo que no se pudo recuperar.
- NO usar IA ni llamar APIs pagas en estas fases.
- NO copiar código de CADFit: su licencia no está confirmada. Se usa el paper como idea y se escribe desde cero.
- NO cambiar convert_mesh ni su comportamiento.
- NO bajar una meta para que el banco pase.
- NO hacer el panel Reconstruir sólido, el resultado paramétrico ni las superficies libres: son RI-3 a RI-6.
- NO instalar paquetes ni toolchains sin permiso.
- NO correr el cierre completo ni la suite entera: va de noche, cuando Gerardo lo diga.
- NO hacer commit ni push sin que Gerardo lo pida.
- NO tocar archivos ajenos a estas filas. Si hace falta, anotarlo en el informe.

MANEJO DE ERRORES
- Paso 2: SALTAR Y CONTINUAR con los STL reales si Gerardo no los pasó, avisándolo con ⚠.
- Paso 3: PARAR Y REPORTAR si la comparación no detecta el agujero corrido.
- Paso 7: PARAR Y REPORTAR si la fase 2 pasa de 3 GB con 200.000 triángulos.
- Paso 11: si una pieza no llega a la meta, SALTAR Y CONTINUAR con la siguiente y dejarla marcada en la tabla.
- Paso 14: PARAR Y REPORTAR con la salida real si algo sigue rojo después de 2 intentos.
- Default: PARAR Y REPORTAR.

CRITERIO DE ÉXITO
- `compare_to_mesh`, `analyze_mesh_features` y `reconstruct_from_mesh` existen en la API, MCP y CLI.
- El mapa de color anda en la ventana.
- El banco da una tabla real por pieza contra las metas del plan.
- Las piezas reconstruidas se abren, se editan y recalculan sin pasos en error.
- ruff, tests tocados y pieza de ventana están en verde, con capturas revisadas.
- La salida real de ponytail-review está pegada en el informe.

SALIDA ESPERADA
Informe en español, corto:
- Tabla por tipo de pieza: cuántas alcanzan cada meta y cuántas no.
- Lista de piezas que fallaron y por qué.
- Firma de cada función pública nueva y qué hace.
- Tiempo y memoria medidos.
- Salida real de ruff, pytest, la pieza de ventana y ponytail-review.
- Una línea con ⚠ por cada cosa no verificada.
- Una línea sobre si el modelo alcanzó.

COMPORTAMIENTO DEL AGENTE
- Ejecutá las instrucciones literalmente. No parafrasees ni reinterpretes.
- No agregues contenido que no sea derivable de las entradas.
- No asumas intención más allá de lo explícitamente declarado.
- Priorizá precisión sobre velocidad.
- Si un paso falla, seguí la regla de MANEJO DE ERRORES correspondiente.
```
