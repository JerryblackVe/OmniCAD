# Grafo de nodos: programación visual sin ventana

Primera parte de la programación visual tipo Grasshopper de [brechas_grasshopper.md](brechas_grasshopper.md): GH1
(árboles de datos), GH2 (motor), GH3 (catálogo de nodos), GH5 (hornear en el timeline) y GH8 (correr sin ventana).
El lienzo de nodos (GH4) todavía no existe: por ahora el grafo se escribe en JSON y lo usan los agentes y la CLI.
Se replicaron las FUNCIONES de Grasshopper (árboles, emparejado, hornear), escritas desde cero.

| Pieza | Dónde |
|---|---|
| Árboles, rutas y emparejado | `clon/omnicad/grafo/arbol.py` |
| Tipos de puerto y conversión | `clon/omnicad/grafo/tipos.py` |
| Catálogo y nodos | `clon/omnicad/grafo/nodos.py` y `nodos_*.py` |
| Grafo (JSON, validación, ciclos) y motor (caché, tiempos) | `clon/omnicad/grafo/motor.py` |
| Paso «Grafo» del timeline (hornear) | `clon/omnicad/timeline/ops_grafo.py` |
| Herramientas `list_graph_nodes`, `run_graph`, `bake_graph` | `clon/omnicad/api/herramientas_grafo.py` (MCP y CLI) |

Nada de esto importa Qt; importar `omnicad.grafo` tampoco carga OpenCascade (lo cargan los nodos de geometría).

## Formato JSON

```json
{
  "formato": "omnicad.grafo",
  "version": 1,
  "nodos": [
    {"id": "lado", "tipo": "deslizador", "entradas": {"valor": 10, "minimo": 1, "maximo": 50}},
    {"id": "grilla", "tipo": "puntos_grilla", "entradas": {"paso_x": {"de": "lado"}, "paso_y": {"de": "lado"}}},
    {"id": "cajas", "tipo": "caja", "entradas": {"centro": {"de": "grilla.puntos"}, "ancho": {"de": "lado"}}},
    {"id": "union", "tipo": "unir", "entradas": {"cuerpos": {"de": "cajas"}}},
    {"id": "pieza", "tipo": "salida", "entradas": {"valor": {"de": "union"}}}
  ]
}
```

- Nodo: `id` (letras, dígitos y `_`), `tipo` (ver la lista de abajo), `entradas`; opcionales `nombre` (cómo se lo
  cita desde afuera), `emparejado` (`larga`, `corta` o `cruzada`) y `posicion` `[x, y]` (para el lienzo futuro).
- Cada entrada es un **literal** (`10`, `"ancho / 2"` con parámetros del documento, `true`, `[0, 0, 0]` = un punto,
  `"XY"` = un plano, `[1, 2, 3]` en un puerto numérico = una lista), un **cable** `{"de": "nodo"}` (su primera
  salida), `{"de": "nodo.salida"}` o `{"de": ["a", "b"]}` (se fusionan), o un **árbol** `{"arbol": {"{0}": [1, 2],
  "{1}": [3]}}`. Con `"modificador"`: `aplanar`, `injertar`, `simplificar` o `invertir`, el árbol se transforma antes de
  usarlo. Una entrada que falta toma su valor por defecto; las obligatorias (marcadas con `*` abajo) no.
- `formato` y `version` son opcionales al leer; `a_json` siempre los escribe.

## Cómo se evalúa

- **Árboles**: los datos viajan como ramas con ruta (`{0;1}`) y lista de ítems; un valor suelto es `{0}: [valor]`.
- **Acceso de cada entrada**: `item` (el nodo corre una vez por ítem), `lista` (`[ ]` abajo: recibe la rama entera) o
  `arbol` (`{ }`: recibe el árbol entero).
- **Emparejado**: las ramas se emparejan como lista más larga (manda la entrada con más ramas y da las rutas de
  salida); dentro de cada rama, los ítems según `emparejado`. Una salida de lista de un nodo que corre varias veces en
  la misma rama va a sub-ramas `{ruta;vuelta}`.
- **Nulos y errores por nodo**: una vuelta que falla da nulo y el nodo queda en `error` con el mensaje; las demás
  vueltas y los demás nodos siguen. Un nulo que llega a una entrada da nulo con aviso. Sin datos en una entrada
  obligatoria, el nodo no corre (aviso).
- **Orden y ciclos**: orden topológico estable; un ciclo es un error que lo nombra («a → b → a»).
- **Caché**: cada nodo tiene una huella de sus literales (ya evaluados), de las huellas de los nodos de los que cuelga y
  de los parámetros del documento que lee. Al cambiar una entrada solo se recalcula lo que está aguas abajo; cada nodo
  informa su tiempo y si salió de la caché. `motor_para(grafo)` comparte el motor entre llamadas con el mismo grafo.
- **Entradas por nombre**: `{"lado": 20}` cambia el `valor` del nodo de entrada con ese nombre o id;
  `{"cajas.alto": 3}` cambia cualquier entrada de cualquier nodo (también una que tenía un cable).

## Hornear

`bake_graph` agrega un paso «Grafo» (`OpGrafo`, tipo `grafo`): guarda el JSON del grafo, las entradas, las salidas a
hornear y la operación (`nuevo`, `unir`, `cortar`, `intersecar` sobre `objetivo`). Se reevalúa en cada recálculo y
se guarda dentro del `.omnicad` como cualquier paso. Las entradas que son expresiones (`"ancho / 4"`) y los nodos
`parametro` quedan enlazados a la tabla de parámetros: al cambiar el parámetro el paso se recalcula, y el parámetro no
se puede borrar mientras el grafo lo use. Cada sólido de una salida es un cuerpo con el nombre de la salida
(«pieza», o «pieza 1», «pieza 2»… si son varios). Con `fixed=true` se hornean cuerpos fijos (operación base).

## Herramientas y CLI

- `list_graph_nodes(category, query)`: los nodos con sus puertos y el formato con un ejemplo.
- `run_graph(graph, inputs, outputs, export)`: evalúa sin tocar el documento; `export` a `.step`, `.stl`, `.3mf`…
- `bake_graph(graph, inputs, outputs, operation, target, fixed)`: el paso «Grafo».

`graph` acepta el objeto, su texto JSON o la ruta a un `.json` (con el grafo o con `{"graph", "inputs"}`). Ejemplo
ejecutable: [grilla_cajas.grafo.json](../ejemplos/agentes/grilla_cajas.grafo.json).

```
omnicad call list_graph_nodes category=solidos --json
omnicad call run_graph --args-file ejemplos/agentes/grilla_cajas.grafo.json --json
omnicad call run_graph graph=ejemplos/agentes/grilla_cajas.grafo.json inputs='{"lado": 20}' export=grilla.stl
omnicad call bake_graph --doc pieza.omnicad graph=ejemplos/agentes/grilla_cajas.grafo.json
```

## Nodos

`*` = entrada obligatoria; `[ ]` = lista; `{ }` = árbol. Unidades: mm y grados.

### entrada

| Tipo | Entradas → salidas | Qué hace |
|---|---|---|
| `numero` | valor → valor | Un número fijo o una expresión con parámetros del documento (p. ej. «ancho / 2»). |
| `deslizador` | valor, minimo, maximo, paso → valor | Número entre un mínimo y un máximo, con paso opcional (0 = continuo). Un valor fuera del rango se recorta (con aviso). |
| `entero` | valor → valor | Un número entero fijo. |
| `booleano` | valor → valor | Verdadero o falso. |
| `texto` | valor → valor | Un texto fijo. |
| `punto` | valor → valor | Un punto fijo [x, y, z] en mm (cada coordenada acepta expresiones). |
| `rango` | inicio, fin, pasos → numeros[ ] | Divide el intervalo [inicio, fin] en «pasos» partes iguales: pasos + 1 números. |
| `serie` | inicio, paso, cantidad → numeros[ ] | «cantidad» números que empiezan en «inicio» y crecen de a «paso». |
| `aleatorio` | minimo, maximo, cantidad, semilla → numeros[ ] | «cantidad» números al azar entre mínimo y máximo; la misma semilla da siempre los mismos números. |
| `parametro` | nombre* → valor | El valor de un parámetro del documento (mm, grados o sin unidad, según su tipo): el grafo se recalcula cuando el parámetro cambia. |

### matematica

| Tipo | Entradas → salidas | Qué hace |
|---|---|---|
| `sumar` | a, b → resultado | a + b. |
| `restar` | a, b → resultado | a − b. |
| `multiplicar` | a, b → resultado | a · b. |
| `dividir` | a, b → resultado | a / b (b = 0 es error). |
| `potencia` | a, b → resultado | a elevado a b. |
| `resto` | a, b → resultado | Resto de a / b, con el signo de b (como el módulo de Python). |
| `minimo` | a, b → resultado | El menor de a y b. |
| `maximo` | a, b → resultado | El mayor de a y b. |
| `absoluto` | x → resultado | \|x\|. |
| `redondear` | x, decimales → resultado | x redondeado a «decimales» decimales. |
| `seno` | angulo → resultado | Seno de un ángulo en grados. |
| `coseno` | angulo → resultado | Coseno de un ángulo en grados. |
| `comparar` | a, b, operador → resultado | Compara a y b con el operador (<, <=, >, >=, == o !=; == tolera 1e-9). |
| `expresion` | expresion, x, y, z → resultado | Evalúa una expresión con x, y, z y los parámetros del documento (+ − * / **, sin, cos, tan en grados, sqrt, abs, min, max, round, floor, ceil, pi; unidades mm, cm, m, in, ft, deg, rad). |
| `promedio` | numeros[ ]* → resultado | Promedio de una lista de números. |
| `total` | numeros[ ]* → resultado | Suma de una lista de números (los nulos no cuentan). |

### listas

| Tipo | Entradas → salidas | Qué hace |
|---|---|---|
| `largo` | lista[ ]* → largo | Cantidad de ítems de la lista (los nulos cuentan). |
| `item` | lista[ ]*, indice, envolver → item | El ítem en «indice» (0 = el primero; negativos desde el final). Fuera de rango: nulo con aviso, o da la vuelta con envolver. |
| `sublista` | lista[ ]*, inicio, fin → lista[ ] | Los ítems desde «inicio» (incluido) hasta «fin» (excluido); negativos cuentan desde el final; sin fin = hasta el final. |
| `invertir_lista` | lista[ ]* → lista[ ] | La lista al revés. |
| `ordenar` | lista[ ]*, claves[ ] → lista[ ], indices[ ] | Ordena de menor a mayor (números o textos). Con «claves», ordena la lista según esas claves (una por ítem). Devuelve también los índices originales. |
| `repetir` | lista[ ]*, veces → lista[ ] | La lista repetida «veces» veces seguidas. |
| `fusionar` | a[ ]*, b[ ] → lista[ ] | Los ítems de a seguidos de los de b. |
| `filtrar` | lista[ ]*, patron[ ] → lista[ ] | Deja los ítems cuyo valor del patrón es verdadero; el patrón se repite si es más corto que la lista. |
| `desplazar` | lista[ ]*, cantidad, envolver → lista[ ] | Corre los ítems «cantidad» lugares hacia el principio (negativo: hacia el final). Con envolver, los que salen entran por el otro lado; sin envolver se pierden. |

### arboles

| Tipo | Entradas → salidas | Qué hace |
|---|---|---|
| `aplanar` | arbol{ }* → arbol{ } | Todos los ítems en una sola rama {0}, en orden de ruta. |
| `injertar` | arbol{ }* → arbol{ } | Cada ítem a su propia rama: el ítem i de {a} va a {a;i}. |
| `simplificar` | arbol{ }* → arbol{ } | Quita los índices iniciales que comparten todas las rutas (cada ruta conserva al menos uno). |
| `invertir_matriz` | arbol{ }* → arbol{ } | Intercambia filas y columnas: el ítem j de la i-ésima rama pasa a la rama {j}; los huecos quedan nulos. |

### vectores

| Tipo | Entradas → salidas | Qué hace |
|---|---|---|
| `construir_punto` | x, y, z → punto | Punto (x, y, z) en mm. |
| `descomponer` | punto* → x, y, z | Las coordenadas x, y, z de un punto o vector. |
| `vector_2p` | a, b → vector, largo | El vector de a hacia b (b − a) y su largo. |
| `sumar_vectores` | a, b → resultado | a + b (un punto más un vector es el punto desplazado). |
| `escalar_vector` | vector, factor → vector | El vector multiplicado por un factor. |
| `distancia` | a, b → distancia | Distancia entre dos puntos (mm). |
| `largo_vector` | vector → largo | Largo (módulo) del vector. |
| `unitario` | vector → vector | El vector con largo 1 (el nulo es error). |
| `producto_escalar` | a, b → resultado | a · b. |
| `producto_vectorial` | a, b → vector | a × b (perpendicular a los dos). |
| `plano_origen` | nombre, origen → plano | Plano XY, XZ o YZ (como los del origen) pasando por un punto. |
| `construir_plano` | origen, normal, eje_x → plano | Plano por un punto con una normal; el eje x (opcional) fija el giro dentro del plano. |
| `descomponer_plano` | plano → origen, eje_x, eje_y, normal | Origen y ejes x, y, z (normal) de un plano. |
| `puntos_grilla` | plano, cantidad_x, cantidad_y, paso_x, paso_y → puntos[ ] | cantidad_x × cantidad_y puntos en una grilla rectangular sobre un plano (por defecto XY): filas a lo largo del eje y del plano, y en cada fila los puntos van en x. El primero está en el origen del plano. |
| `puntos_circulo` | plano, radio, cantidad, angulo_inicial → puntos[ ] | «cantidad» puntos repartidos en un círculo de radio dado alrededor del origen de un plano, desde el ángulo inicial (grados, medido desde el eje x del plano, antihorario mirando desde la normal). |

### curvas

| Tipo | Entradas → salidas | Qué hace |
|---|---|---|
| `linea` | a, b → curva | Segmento recto de a a b. |
| `circulo` | plano, radio → curva | Círculo de radio dado con centro en el origen del plano. |
| `rectangulo` | plano, ancho, largo → curva | Rectángulo de ancho (eje x del plano) por largo (eje y), centrado en el origen del plano. |
| `largo_curva` | curva* → largo | Largo de la curva (mm). |
| `extruir` | curva*, distancia → cuerpo | Sólido que sale de extruir la región encerrada por una curva cerrada, en la normal de su plano (distancia negativa = hacia el otro lado). |

### solidos

| Tipo | Entradas → salidas | Qué hace |
|---|---|---|
| `caja` | centro, ancho, largo, alto → cuerpo | Caja de ancho (X) × largo (Y) × alto (Z); «centro» es el centro de la base, como en create_box. |
| `cilindro` | base, radio, alto, eje → cuerpo | Cilindro de radio y alto dados; «base» es el centro de la base y «eje» su dirección. |
| `esfera` | centro, radio → cuerpo | Esfera de radio dado. |
| `toroide` | centro, radio_mayor, radio_menor, eje → cuerpo | Toroide (anillo) con radio mayor (al centro del tubo) y radio menor (del tubo). |
| `mover` | cuerpo*, vector → cuerpo | El cuerpo desplazado por un vector (una copia: el original no cambia). |
| `rotar` | cuerpo*, angulo, eje, centro → cuerpo | El cuerpo girado un ángulo (grados, regla de la mano derecha) alrededor del eje que pasa por «centro». |
| `escalar` | cuerpo*, factor, centro → cuerpo | El cuerpo escalado (uniforme) desde «centro». |
| `simetria` | cuerpo*, plano → cuerpo | Copia reflejada del cuerpo respecto de un plano. |
| `unir` | cuerpos[ ]* → cuerpo | Une todos los cuerpos de la lista en uno (los que no se tocan quedan como piezas separadas del mismo resultado). |
| `cortar` | cuerpo*, herramientas[ ]* → cuerpo | Resta del cuerpo todas las herramientas de la lista. |
| `intersecar` | a*, b* → cuerpo | Lo que tienen en común dos cuerpos. |
| `separar` | cuerpo* → piezas[ ] | Las piezas sólidas sueltas de un cuerpo (p. ej. tras unir cuerpos que no se tocan). |
| `volumen` | cuerpo* → volumen | Volumen del cuerpo (mm³). |
| `area` | cuerpo* → area | Área de la superficie del cuerpo (mm²). |
| `caja_envolvente` | cuerpo* → minimo, maximo, tamano | Esquinas mínima y máxima de la caja envolvente y su tamaño. |
| `centro_masa` | cuerpo* → punto | Centro de masa (de volumen) del cuerpo. |

### salida

| Tipo | Entradas → salidas | Qué hace |
|---|---|---|
| `salida` | valor{ }* → valor{ } | Resultado del grafo con un nombre: run_graph devuelve su valor y bake_graph hornea los cuerpos que lleguen acá. |

## Pendiente

Lienzo de nodos (GH4), grafo como comando (GH7), nodo de script (GH6), clústeres (GH9), bucles y campos (GH10). Las
curvas son planas (línea, círculo, rectángulo) y se hornean solo los cuerpos. Los nodos corren en un solo hilo.
Agregar un nodo: ver el docstring de `clon/omnicad/grafo/nodos.py`; `tests/test_grafo.py` lo corre solo y exige que
figure en esta lista.
