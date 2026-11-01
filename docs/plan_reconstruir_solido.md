# Reconstruir sólido: de una malla a una pieza paramétrica

Convierte un STL, OBJ o 3MF en una pieza nueva, hecha con pasos normales del timeline: bocetos, extrusiones, revoluciones,
agujeros, empalmes y patrones. No convierte triángulos en caras: mide la pieza y la vuelve a modelar.

Estado por fila en `docs/seguimiento/faltantes.md` (RI-1 a RI-6, F10 y F11). Revisado el 2026-11-01. No hay prototipo: las
metas de abajo son propuestas, no mediciones.

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

## Metas propuestas

Para mallas de origen CAD del banco. Se ajustan después de la fase 0.

| Medida | Meta |
|---|---|
| Desviación máxima | 0,1 mm o la tolerancia elegida |
| Volumen | Diferencia menor a 0,5 % |
| Caras | Hasta 1,5 veces las del original |
| Timeline | Sin pasos en error; cuerpo válido |
| Tiempo | Menos de 2 minutos para 200.000 triángulos, sin congelar la ventana |
| Memoria | Dentro del tope de 3 GB por tarea de `scripts/turno.py` |

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
