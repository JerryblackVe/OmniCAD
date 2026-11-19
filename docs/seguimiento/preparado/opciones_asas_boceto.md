# Opciones y asas del boceto — preparado

Inventario de las opciones de los comandos de boceto (`clon/omnicad/ui/comandos/`) y de los diálogos y paneles de `clon/omnicad/ui/modo_boceto.py`, más las asas de arrastre del editor (`ui/asas_boceto.py`, `ui/patron_boceto.py`, `ui/transformar_boceto.py` y `ui/editor_boceto*.py`). Es una tabla de preparación: no cierra bugs ni cambia código.

Criterio de cobertura (igual que `scripts/cobertura_boceto.py`): «test automático = sí» si algún test de `clon/tests/` distinto de `test_cobertura_ui_api.py`, `test_iconos_extra.py`, `test_cinta.py` y `test_iconos_interfaz.py` nombra la clave; «probado como usuario = sí» si algún script de `scripts/prueba_ui/` que no sea un catálogo (más de 25 claves) la nombra. «Fila abierta»: ID de `docs/seguimiento/` que menciona la clave. Una celda «sí» indica que el nombre aparece, no que la opción o el asa esté cubierta por un aserto específico.

| Comando | Opción o asa | Test automático (sí/no) | Probado como usuario (sí/no) | Fila abierta |
|---|---|---|---|---|
| Proyectar a superficie | Curvas (Seleccion) | sí | sí | — |
| Proyectar a superficie | Caras (Seleccion) | sí | sí | — |
| Proyectar a superficie | Tipo: Punto más cercano (closest) | sí | sí | — |
| Proyectar a superficie | Tipo: A lo largo de un vector (vector) | sí | sí | — |
| Proyectar a superficie | Dirección: eje o arista lineal (Seleccion) | sí | sí | — |
| Curva de intersección | Curvas (Seleccion) | sí | sí | — |
| Curva de intersección | Caras (Seleccion) | sí | sí | — |
| Insertar SVG en boceto | Archivo (Texto) | sí | sí | — |
| Insertar SVG en boceto | Escala (Expresion) | **no** | sí | — |
| Insertar SVG en boceto | Desplazamiento X (Expresion) | sí | sí | — |
| Insertar SVG en boceto | Desplazamiento Y (Expresion) | **no** | sí | — |
| Insertar SVG en boceto | Ángulo (Expresion) | **no** | sí | — |
| Insertar SVG en boceto | Volteo horizontal (Casilla) | **no** | sí | — |
| Insertar SVG en boceto | Volteo vertical (Casilla) | **no** | sí | — |
| Insertar SVG en boceto | Capas (Texto) | sí | **no** | — |
| Insertar SVG en boceto | Colores (Texto) | sí | **no** | — |
| Insertar SVG en boceto | Destino: boceto abierto (Info) | sí | sí | — |
| Insertar DXF en boceto | Archivo (Texto) | sí | **no** | — |
| Insertar DXF en boceto | Escala / desplazamiento / ángulo / volteos | sí | **no** | — |
| Insertar DXF en boceto | Destino: boceto abierto (Info) | sí | **no** | — |
| Vectorizar imagen en boceto | Imagen (Texto) | sí | **no** | — |
| Vectorizar imagen en boceto | Ancho final (Expresion) | sí | **no** | — |
| Vectorizar imagen en boceto | Tinta clara / Curvas suaves (Casilla) | sí | **no** | — |
| Vectorizar imagen en boceto | Umbral / Suavizado / Manchas / Tolerancia (Entero, Deslizador) | sí | **no** | — |
| Vectorizar imagen en boceto | Destino: boceto abierto (Info) | sí | **no** | — |
| Proyectar (paleta) | Proyectar | **no** | sí | — |
| Proyectar (paleta) | Intersecar | sí | sí | — |
| Proyectar (paleta) | Incluir geometría 3D | sí | sí | — |
| Proyectar (paleta) | Perfil giratorio | sí | sí | — |
| Proyectar (paleta) | Curva isoparamétrica | sí | sí | — |
| Rectángulo | 2 puntos / 3 puntos / Central | sí | sí | — |
| Círculo | Centro y diámetro / 2 puntos / 3 puntos / 2 tangentes / 3 tangentes | sí | **no** | — |
| Arco | 3 puntos / Punto central / Tangente | sí | sí | — |
| Polígono | Circunscrito / Inscrito / De aristas | sí | sí | — |
| Ranura | Centro a centro / Total / Punto central / Arco 3 puntos / Arco punto central | sí | **no** | — |
| Spline | Ajuste de puntos / Puntos de control | sí | **no** | — |
| Chaflán | Distancias iguales / Distancia y ángulo / Dos distancias | sí | sí | — |
| Spline de control | Grado: 5 / 3 | sí | **no** | — |
| Curva de fusión | Continuidad: G1 / G2 | sí | sí | — |
| Proyectar / Intersecar | Filtro: Entidades especificadas / Cuerpos | sí | sí | — |
| Desfase | Dirección: Un lado / Dos lados / Simétrico | sí | **no** | — |
| Perfil giratorio | Eje: X / Y / Z / Arista recta | sí | sí | — |
| Curva isoparamétrica | Dirección: U / V / Ambas | sí | **no** | — |
| Curva isoparamétrica | Distribución: Una / Por distancia / Por cantidad | sí | **no** | — |
| Perfil giratorio | Tolerancia (numérico) | sí | **no** | — |
| Estrella | Interior / Redondeo de puntas / Redondeo de valles (numérico) | **no** | **no** | — |
| Curva isoparamétrica | Distancia (numérico) | sí | **no** | — |
| Curva isoparamétrica | Cantidad (Entero) | sí | **no** | — |
| Estrella | Puntas (Entero) | **no** | **no** | — |
| Estrella | Salto con Interior 0 (Entero) | **no** | **no** | — |
| Proyectar / Intersecar / Perfil / Iso | Vínculo de proyección (Casilla) | sí | **no** | — |
| Desfase | Selección de cadena (Casilla) | sí | **no** | — |
| Desfase | Igualar topología (Casilla) | sí | **no** | — |
| Perfil giratorio | Invertir (Casilla) | sí | **no** | — |
| Perfil giratorio | Solo contorno exterior (Casilla) | sí | **no** | — |
| Perfil giratorio | Proyectar eje (Casilla) | sí | sí | — |
| Estrella | Círculos de construcción (Casilla) | **no** | **no** | — |
| Texto / Panel Carácter | Parámetro de texto y Contenido | **no** | **no** | — |
| Texto / Panel Carácter | Familia tipográfica y Filtro de fuentes | **no** | **no** | — |
| Texto / Panel Carácter | Tamaño / altura | sí | **no** | — |
| Texto / Panel Carácter | Kerning y par | sí | **no** | — |
| Texto / Panel Carácter | Volteo horizontal / vertical | sí | sí | — |
| Texto / Panel Carácter | Espaciado de caracteres / Interlineado | sí | **no** | — |
| Texto / Panel Carácter | Alineación (izq / centro / der) | sí | sí | — |
| Texto / Panel Carácter | Anclaje (base / arriba / medio / abajo) | sí | **no** | — |
| Texto / Panel Carácter | Pivote de giro (6 opciones) | **no** | **no** | — |
| Texto / Panel Carácter | Colocación en curva (arriba / abajo) | sí | sí | — |
| Texto / Panel Carácter | Lado en curva (a favor / al revés) | sí | sí | — |
| Texto / Panel Carácter | Desfase en curva / Ajustar a la curva | sí | **no** | — |
| Texto / Panel Carácter | Subrayado / Tachado / Grosor | sí | **no** | — |
| Texto / Panel Carácter | Línea base / Inclinación / Ancho / Alto | sí | **no** | — |
| Texto / Panel Carácter | Mayúsculas y minúsculas | sí | **no** | — |
| Texto / Panel Carácter | Sin división | sí | sí | — |
| Paleta de boceto | Rejilla del boceto | sí | sí | — |
| Paleta de boceto | Forzar | sí | sí | — |
| Paleta de boceto | Corte | sí | sí | — |
| Paleta de boceto | Perfil | sí | sí | — |
| Paleta de boceto | Puntos | sí | sí | — |
| Paleta de boceto | Cotas | sí | sí | — |
| Paleta de boceto | Restricciones | sí | sí | — |
| Paleta de boceto | Geometrías proyectadas | sí | sí | — |
| Paleta de boceto | Geometrías de construcción | sí | sí | — |
| Paleta de boceto | Boceto 3D | sí | sí | — |
| Boceto 3D | Herramienta / Tríada (bloqueos) / Puntos / Largo / Texto / Altura | sí | **no** | — |
| Panel Patrón (boceto) | Cantidad / distancia 1 y 2 / direcciones / ángulo | sí | sí | — |
| Panel Patrón (boceto) | Cantidad / espaciado / ángulo total (circular) | sí | sí | — |
| Panel Patrón (boceto) | Casillas de supresión por copia | sí | sí | — |
| Panel Transformar (boceto) | Factor de escala | sí | sí | — |
| Panel Transformar (boceto) | ΔX / ΔY / Ángulo (mover) | sí | sí | — |
| Panel Simetría (boceto) | Eje / línea de simetría | sí | **no** | — |
| Desfase | Asa de distancia (1 o 2, sobre la normal) | **no** | **no** | — |
| Escala del boceto | Asa de factor | **no** | **no** | — |
| Mover/copiar | Asa de traslación (ΔX y ΔY) | **no** | sí | — |
| Mover/copiar | Asa de giro | **no** | sí | — |
| Empalme | Asa de radio | **no** | **no** | — |
| Chaflán (3 variantes) | Asa de distancia / distancias / ángulo | **no** | **no** | — |
| Texto | Asa de giro del marco | **no** | **no** | — |
| Patrón rectangular | Asa de distancia y cantidad por dirección; giro sin línea | **no** | **no** | — |
| Patrón circular | Asa de ángulo total / paso y cantidad | **no** | **no** | — |
| Editor (curvas) | Arrastre de puntos y curvas (mover / cambiar radio) | sí | **no** | — |
| Editor (cotas) | Arrastre de la cota y su número | sí | sí | — |
| Editor (texto en ruta) | Arrastre del texto sobre la curva | sí | **no** | — |
| Marco de selección (boceto) | Manijas de escala (4 esquinas) | sí | sí | — |
| Marco de selección (boceto) | Manija de giro | sí | sí | — |
| Marco de selección (boceto) | Manija de mover | sí | **no** | — |
| Marco de selección (boceto) | Manijas de espejo horizontal / vertical | sí | **no** | — |

**Resumen:** 106 filas (90 opciones, 16 asas); 22 sin test automático, 53 sin prueba como usuario, 14 sin ninguna de las dos.

Catálogos de `scripts/prueba_ui/` excluidos por nombrar más de 25 claves de la cinta: `cm_ventana.py`. Las claves genéricas de la paleta pueden aparecer en `dialogos_inventario.py` (inventario de diálogos), no necesariamente en una prueba de uso.
