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
| Insertar SVG en boceto | Volteo horizontal (Casilla) | sí | sí | — |
| Insertar SVG en boceto | Volteo vertical (Casilla) | **no** | sí | — |
| Insertar SVG en boceto | Capas (Texto) | sí | sí (boceto_opciones) | — |
| Insertar SVG en boceto | Colores (Texto) | sí | sí (boceto_opciones) | — |
| Insertar SVG en boceto | Destino: boceto abierto (Info) | sí | sí | — |
| Insertar DXF en boceto | Archivo (Texto) | sí | sí (grupo_b_boceto) | — |
| Insertar DXF en boceto | Escala / desplazamiento / ángulo / volteos | sí | sí (opciones_dxf_vectorizar) | — |
| Insertar DXF en boceto | Destino: boceto abierto (Info) | sí | sí (grupo_b_boceto) | — |
| Vectorizar imagen en boceto | Imagen (Texto) | sí | sí (grupo_b_boceto) | — |
| Vectorizar imagen en boceto | Ancho final (Expresion) | sí | sí (grupo_b_boceto) | — |
| Vectorizar imagen en boceto | Tinta clara / Curvas suaves (Casilla) | sí | sí (opciones_dxf_vectorizar) | — |
| Vectorizar imagen en boceto | Umbral / Suavizado / Manchas / Tolerancia (Entero, Deslizador) | sí | sí (opciones_dxf_vectorizar) | — |
| Vectorizar imagen en boceto | Destino: boceto abierto (Info) | sí | sí (grupo_b_boceto) | — |
| Proyectar (paleta) | Proyectar | **no** | sí | — |
| Proyectar (paleta) | Intersecar | sí | sí | — |
| Proyectar (paleta) | Incluir geometría 3D | sí | sí | — |
| Proyectar (paleta) | Perfil giratorio | sí | sí | — |
| Proyectar (paleta) | Curva isoparamétrica | sí | sí | — |
| Rectángulo | 2 puntos / 3 puntos / Central | sí | sí | — |
| Círculo | Centro y diámetro / 2 puntos / 3 puntos / 2 tangentes / 3 tangentes | sí | sí (boceto_crear_formas) | — |
| Arco | 3 puntos / Punto central / Tangente | sí | sí | — |
| Polígono | Circunscrito / Inscrito / De aristas | sí | sí | — |
| Ranura | Centro a centro / Total / Punto central / Arco 3 puntos / Arco punto central | sí | sí (boceto_crear_formas) | — |
| Spline | Ajuste de puntos / Puntos de control | sí | sí (boceto_crear_formas) | — |
| Chaflán | Distancias iguales / Distancia y ángulo / Dos distancias | sí | sí | — |
| Spline de control | Grado: 5 / 3 | sí | sí (boceto_opciones) | — |
| Curva de fusión | Continuidad: G1 / G2 | sí | sí | — |
| Proyectar / Intersecar | Filtro: Entidades especificadas / Cuerpos | sí | sí | — |
| Desfase | Dirección: Un lado / Dos lados / Simétrico | sí | sí (desfase_boceto) | — |
| Perfil giratorio | Eje: X / Y / Z / Arista recta | sí | sí | — |
| Curva isoparamétrica | Dirección: U / V / Ambas | sí | sí (boceto_herramientas) | — |
| Curva isoparamétrica | Distribución: Una / Por distancia / Por cantidad | sí | sí (boceto_herramientas) | — |
| Perfil giratorio | Tolerancia (numérico) | sí | sí (opciones_sin_prueba) | — |
| Estrella | Interior / Redondeo de puntas / Redondeo de valles (numérico) | **no** | sí (boceto_opciones) | — |
| Curva isoparamétrica | Distancia (numérico) | sí | sí (boceto_herramientas) | — |
| Curva isoparamétrica | Cantidad (Entero) | sí | sí (boceto_herramientas) | — |
| Estrella | Puntas (Entero) | **no** | sí (boceto_opciones) | — |
| Estrella | Salto con Interior 0 (Entero) | **no** | sí (boceto_opciones) | — |
| Proyectar / Intersecar / Perfil / Iso | Vínculo de proyección (Casilla) | sí | sí (proyectar_cinco) | — |
| Desfase | Selección de cadena (Casilla) | sí | sí (opciones_desfase_cadena) | — |
| Desfase | Igualar topología (Casilla) | sí | sí (opciones_desfase_cadena) | — |
| Perfil giratorio | Invertir (Casilla) | sí | sí (opciones_sin_prueba) | — |
| Perfil giratorio | Solo contorno exterior (Casilla) | sí | sí (opciones_sin_prueba) | — |
| Perfil giratorio | Proyectar eje (Casilla) | sí | sí | — |
| Estrella | Círculos de construcción (Casilla) | **no** | sí (boceto_opciones) | — |
| Texto / Panel Carácter | Parámetro de texto y Contenido | **no** | sí (boceto_texto_panel) | — |
| Texto / Panel Carácter | Familia tipográfica y Filtro de fuentes | **no** | sí (boceto_texto_panel) | — |
| Texto / Panel Carácter | Tamaño / altura | sí | sí (boceto_texto_panel) | — |
| Texto / Panel Carácter | Kerning y par | sí | sí (opciones_kerning_3d) | — |
| Texto / Panel Carácter | Volteo horizontal / vertical | sí | sí | — |
| Texto / Panel Carácter | Espaciado de caracteres / Interlineado | sí | sí (boceto_texto_panel) | — |
| Texto / Panel Carácter | Alineación (izq / centro / der) | sí | sí | — |
| Texto / Panel Carácter | Anclaje (base / arriba / medio / abajo) | sí | sí (boceto_texto_panel) | — |
| Texto / Panel Carácter | Pivote de giro (6 opciones) | **no** | sí (boceto_texto_panel) | B-698 |
| Texto / Panel Carácter | Colocación en curva (arriba / abajo) | sí | sí | — |
| Texto / Panel Carácter | Lado en curva (a favor / al revés) | sí | sí | — |
| Texto / Panel Carácter | Desfase en curva / Ajustar a la curva | sí | sí (opciones_kerning_3d) | — |
| Texto / Panel Carácter | Subrayado / Tachado / Grosor | sí | sí (boceto_texto_panel) | — |
| Texto / Panel Carácter | Línea base / Inclinación / Ancho / Alto | sí | sí (boceto_texto_panel) | — |
| Texto / Panel Carácter | Mayúsculas y minúsculas | sí | sí (boceto_texto_panel) | — |
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
| Panel Simetría (boceto) | Eje / línea de simetría | sí | sí (simetria_boceto) | — |
| Desfase | Asa de distancia (1 o 2, sobre la normal) | sí (test_asas_boceto_valores_raros) | sí (desfase_boceto) | — |
| Escala del boceto | Asa de factor | sí (test_asas_boceto_valores_raros) | sí (asas) | — |
| Mover/copiar | Asa de traslación (ΔX y ΔY) | sí (test_asas_boceto_valores_raros) | sí | — |
| Mover/copiar | Asa de giro | sí (test_asas_boceto_valores_raros) | sí | — |
| Empalme | Asa de radio | sí (test_asas_boceto_valores_raros) | sí (asas) | — |
| Chaflán (3 variantes) | Asa de distancia / distancias / ángulo | sí (test_asas_boceto_valores_raros) | sí (asas) | — |
| Texto | Asa de giro del marco | sí (test_asas_boceto_valores_raros) | sí (asas) | — |
| Patrón rectangular | Asa de distancia y cantidad por dirección; giro sin línea | **no** | sí (patrones_boceto) | — |
| Patrón circular | Asa de ángulo total / paso y cantidad | **no** | sí (patrones_boceto) | — |
| Editor (curvas) | Arrastre de puntos y curvas (mover / cambiar radio) | sí | sí (boceto_opciones) | — |
| Editor (cotas) | Arrastre de la cota y su número | sí | sí | — |
| Editor (texto en ruta) | Arrastre del texto sobre la curva | sí | sí (texto_curva) | — |
| Marco de selección (boceto) | Manijas de escala (4 esquinas) | sí | sí | — |
| Marco de selección (boceto) | Manija de giro | sí | sí | — |
| Marco de selección (boceto) | Manija de mover | sí | sí (boceto_opciones) | — |
| Marco de selección (boceto) | Manijas de espejo horizontal / vertical | sí | sí (boceto_opciones) | — |

**Resumen (corregido 19/11 cruzando con los scripts de prueba_ui; el 19/11 sumó test automático el Volteo horizontal de Insertar SVG):** 106 filas; 21 sin test automático, 11 sin prueba como usuario, 0 sin ninguna de las dos. El contador literal de `cobertura_boceto.py` no ve claves dentro de f-strings ni bucles, por eso la tabla original marcaba «no» filas que sí tienen script; la celda dice qué script las cubre.

Catálogos de `scripts/prueba_ui/` excluidos por nombrar más de 25 claves de la cinta: `cm_ventana.py`. Las claves genéricas de la paleta pueden aparecer en `dialogos_inventario.py` (inventario de diálogos), no necesariamente en una prueba de uso.
