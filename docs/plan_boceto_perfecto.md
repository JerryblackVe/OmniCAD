# Plan: boceto y restricciones perfectos (Gerardo, 2026-11-19)

«Es importante que sketch quede perfecto porque es la parte más básica en CAD. Debes hacer un plan integral.»
Desde el 19/11 todo el foco está en Boceto y Restricciones. La cola sigue siendo [seguimiento/ahora.md](seguimiento/ahora.md);
este archivo dice quién hace qué y cuándo está listo. Los bugs viven en [seguimiento/bugs.md](seguimiento/bugs.md).

## Punto de partida
Video de Gerardo del 19/11 (`~/coordinador/casos/video_boceto_1119/`, fuera del repo): B-649, B-650 y B-651.

## Quién hace qué
| Quién | Qué |
|---|---|
| E1 (Opus alto) | Solver y arrastre: B-649, B-650, B-651 y todo bug nuevo del solver. Lee `docs/fusion_docs` antes (regla 6) |
| E3, E8 | Boceto fuera del solver: herramientas, Recortar, Alargar, Desfase, selección |
| E6 | Termina B-644 y pasa a velocidad del solver (arrastre fluido, sin saltos) |
| E7 | Caza `tema` boceto en Linux (`scripts/caza/`) y `scripts/prueba_ui` de boceto, con arrastres y valores raros |
| OpenCode | Un test de restricciones por bug (casos chicos) y la doc |
| E11 (PC) | Batería con mouse real; cada falla en `evidencias/reportes_pc/<fecha>_<tema>/`, informa al coordinador |
| Coordinador | Da el ID, ordena `ahora.md`, integra |

Lo que no es boceto se frena al cerrar su ítem actual (E4 con SUP-28, E7 con AG-20).

## Ciclo
E11 o E7 encuentran → el coordinador da ID → E1, E3 o E8 arreglan con su test → E11 vuelve a probar.

## Listo cuando (Gerardo, 19/11: «boceto tiene que quedar 100 % operativo y sin errores; no avanzamos si eso no está listo»)
Mientras no se cumplan los 4 puntos, Ahora, Sigue y la cola de OpenCode son solo de boceto, sin fecha de corte.
1. La tabla de cobertura (abajo) con cada comando y cada opción probados: test automático **y** prueba como usuario.
2. Cero filas abiertas de boceto en `docs/seguimiento/`.
3. La caza `tema` boceto (`scripts/caza/cazar.py tema`) y la `prueba_ui` de boceto en verde dos noches seguidas.
4. E11 con mouse real en Windows: la batería entera OK.

## Cobertura de comandos del boceto (Gerardo, 19/11: «trabajar en boceto» = TODO el boceto)
El plan no se arma solo con los bugs conocidos: lo que nunca se probó no tiene fila y queda afuera (pasó con 4 de los 5 tipos de
Proyectar). La tabla sale de la cinta (`ui/cinta.py` › BOCETO: CREAR, MODIFICAR, RESTRICCIONES, CONFIGURAR, INSPECCIONAR, INSERTAR,
SELECCIONAR y TERMINAR) y se rehace con `scripts/cobertura_boceto.py` (desde `clon/`). «Test automático» = algún test que no es de
catálogo nombra su clave; «Probado como usuario» = lo nombra algún script de `scripts/prueba_ui/`.
**Resumen (19/11): 149 comandos; 20 sin test automático; 61 sin prueba como usuario; 11 sin ninguna de las dos.**
Faltan por contar a mano: las opciones de cada diálogo (p. ej. los 5 tipos de Proyectar, ver PRUEBA-PROY en `ahora.md`) y las asas.
Todo lo que figura **no** entra en la cola: tests a OpenCode, prueba de ventana a E7 y E11.

| Grupo | Comando | Clave | Test automático | Probado como usuario | Fila abierta |
|---|---|---|---|---|---|
| CONFIGURAR | Configurar | `configurar` | sí (13) | sí (2) | B-591 |
| CONFIGURAR | Mostrar tabla de configuración | `mostrar_configuracion` | **no** | **no** | — |
| CREAR | Cota de boceto | `sk_cota` | sí (12) | sí (5) | — |
| CREAR | Curva cónica | `sk_conica` | sí (9) | **no** | — |
| CREAR | Editar patrón | `sk_editar_patron` | sí (3) | sí (1) | — |
| CREAR | Elipse | `sk_elipse` | sí (21) | sí (2) | — |
| CREAR | Espiral | `sk_espiral` | sí (6) | **no** | — |
| CREAR | Línea | `sk_linea` | sí (76) | sí (13) | — |
| CREAR | Línea de punto medio | `sk_linea_medio` | sí (5) | sí (1) | — |
| CREAR | Patrón circular | `sk_patron_circular` | sí (10) | sí (2) | — |
| CREAR | Patrón rectangular | `sk_patron_rectangular` | sí (12) | sí (1) | — |
| CREAR | Punto | `sk_punto` | sí (56) | sí (9) | — |
| CREAR | Simetría | `sk_simetria` | sí (19) | sí (6) | — |
| CREAR › Arco | sk_arco | `sk_arco` | sí (33) | sí (4) | — |
| CREAR › Arco | sk_arco_centro | `sk_arco_centro` | sí (5) | sí (1) | — |
| CREAR › Arco | sk_arco_tangente | `sk_arco_tangente` | sí (2) | **no** | — |
| CREAR › Círculo | sk_circulo | `sk_circulo` | sí (60) | sí (11) | — |
| CREAR › Círculo | sk_circulo_2p | `sk_circulo_2p` | sí (4) | **no** | — |
| CREAR › Círculo | sk_circulo_2t | `sk_circulo_2t` | sí (2) | **no** | — |
| CREAR › Círculo | sk_circulo_3p | `sk_circulo_3p` | sí (3) | **no** | — |
| CREAR › Círculo | sk_circulo_3t | `sk_circulo_3t` | sí (2) | **no** | — |
| CREAR › Polígono | sk_estrella | `sk_estrella` | sí (1) | sí (1) | — |
| CREAR › Polígono | sk_poligono_arista | `sk_poligono_arista` | sí (4) | **no** | — |
| CREAR › Polígono | sk_poligono_circunscrito | `sk_poligono_circunscrito` | sí (2) | **no** | — |
| CREAR › Polígono | sk_poligono_inscrito | `sk_poligono_inscrito` | sí (7) | sí (2) | — |
| CREAR › Proyectar/Incluir | Proyectar eje | `sk_proyectar_eje` | sí (2) | sí (4) | — |
| CREAR › Proyectar/Incluir | sk_curva_interseccion | `sk_curva_interseccion` | sí (2) | sí (2) | — |
| CREAR › Proyectar/Incluir | sk_incluir_3d | `sk_incluir_3d` | sí (2) | sí (2) | — |
| CREAR › Proyectar/Incluir | sk_intersecar | `sk_intersecar` | sí (35) | sí (2) | — |
| CREAR › Proyectar/Incluir | sk_isoparametrica | `sk_isoparametrica` | sí (2) | sí (3) | — |
| CREAR › Proyectar/Incluir | sk_perfil_giratorio | `sk_perfil_giratorio` | sí (3) | sí (2) | — |
| CREAR › Proyectar/Incluir | sk_proyecciones_perdidas | `sk_proyecciones_perdidas` | sí (2) | sí (1) | — |
| CREAR › Proyectar/Incluir | sk_proyectar | `sk_proyectar` | sí (2) | sí (4) | — |
| CREAR › Proyectar/Incluir | sk_proyectar_superficie | `sk_proyectar_superficie` | sí (2) | sí (2) | — |
| CREAR › Proyectar/Incluir | sk_romper_vinculo | `sk_romper_vinculo` | sí (2) | sí (1) | — |
| CREAR › Ranura | sk_ranura_arco_3p | `sk_ranura_arco_3p` | sí (2) | **no** | — |
| CREAR › Ranura | sk_ranura_arco_centro | `sk_ranura_arco_centro` | sí (3) | **no** | — |
| CREAR › Ranura | sk_ranura_centro | `sk_ranura_centro` | sí (7) | **no** | — |
| CREAR › Ranura | sk_ranura_punto | `sk_ranura_punto` | sí (3) | **no** | — |
| CREAR › Ranura | sk_ranura_total | `sk_ranura_total` | sí (3) | **no** | — |
| CREAR › Rectángulo | sk_rectangulo | `sk_rectangulo` | sí (15) | sí (3) | — |
| CREAR › Rectángulo | sk_rectangulo_3p | `sk_rectangulo_3p` | sí (7) | sí (1) | — |
| CREAR › Rectángulo | sk_rectangulo_centro | `sk_rectangulo_centro` | sí (5) | **no** | — |
| CREAR › Spline | sk_spline_ajuste | `sk_spline_ajuste` | sí (5) | sí (1) | — |
| CREAR › Spline | sk_spline_control | `sk_spline_control` | sí (5) | **no** | — |
| CREAR › Texto | sk_desglosar_texto | `sk_desglosar_texto` | sí (2) | **no** | — |
| CREAR › Texto | sk_texto | `sk_texto` | sí (57) | sí (7) | — |
| ENSAMBLAR | Activar conjuntos de contactos | `contactos_activar` | sí (1) | **no** | — |
| ENSAMBLAR | Activar todos los contactos | `contactos_todos` | sí (1) | **no** | — |
| ENSAMBLAR | Anclar / desanclar componente | `anclar_componente` | **no** | sí (1) | — |
| ENSAMBLAR | Capturar posición | `capturar_posicion` | sí (3) | sí (1) | — |
| ENSAMBLAR | Desactivar todos los contactos | `contactos_desactivar` | sí (1) | **no** | — |
| ENSAMBLAR | Editar posición inicial | `posicion_inicial` | sí (3) | sí (1) | — |
| ENSAMBLAR | Estudio de movimiento | `estudio_movimiento` | sí (1) | sí (1) | — |
| ENSAMBLAR | Fijar / liberar componente | `fijar_componente` | **no** | sí (1) | — |
| ENSAMBLAR | Grupo rígido | `grupo_rigido` | sí (3) | sí (2) | — |
| ENSAMBLAR | Nuevo componente | `nuevo_componente` | sí (1) | sí (2) | — |
| ENSAMBLAR | Nuevo conjunto de contactos | `contactos_nuevo` | sí (1) | **no** | — |
| ENSAMBLAR | Origen de la unión | `origen_union` | sí (3) | sí (3) | — |
| ENSAMBLAR | Restricción de componentes | `restriccion_componentes` | sí (1) | sí (1) | — |
| ENSAMBLAR | Revertir posición | `revertir_posicion` | sí (1) | sí (2) | — |
| ENSAMBLAR | Uniones de animación | `accionar_uniones` | **no** | sí (3) | — |
| ENSAMBLAR | Unión | `union` | sí (27) | sí (4) | B-646,H-4,P-163,P-32 |
| ENSAMBLAR | Unión conforme a obra | `union_construida` | sí (1) | sí (1) | — |
| ENSAMBLAR | Vínculo de movimiento | `vinculo_movimiento` | sí (4) | sí (3) | — |
| INSERTAR | Calcomanía | `calcomania` | sí (6) | sí (1) | — |
| INSERTAR | Duplicar con uniones | `duplicar_con_uniones` | sí (1) | sí (1) | H-4 |
| INSERTAR | Insertar STEP… | `importar_step` | sí (4) | **no** | — |
| INSERTAR | Insertar SVG | `insertar_svg` | sí (1) | sí (3) | — |
| INSERTAR | Insertar archivos DXF | `insertar_dxf` | sí (1) | **no** | — |
| INSERTAR | Insertar componente | `insertar_diseno` | sí (2) | **no** | — |
| INSERTAR | Insertar derivación | `insertar_derivacion` | sí (2) | **no** | — |
| INSERTAR | Insertar fijador | `fijacion` | sí (8) | sí (1) | — |
| INSERTAR | Insertar malla | `insertar_malla` | sí (2) | **no** | — |
| INSERTAR | Lienzo | `lienzo` | sí (66) | sí (27) | B-411 |
| INSERTAR | Placa de holguras | `calibracion_holguras` | sí (2) | **no** | — |
| INSERTAR | Vectorizar imagen | `vectorizar_imagen` | sí (1) | **no** | — |
| INSPECCIONAR | Análisis cebra | `cebra` | sí (5) | sí (2) | — |
| INSPECCIONAR | Análisis de accesibilidad | `accesibilidad` | sí (2) | sí (1) | — |
| INSPECCIONAR | Análisis de curvatura en peine | `curvatura_peine` | sí (1) | sí (1) | — |
| INSPECCIONAR | Análisis de la isocurva | `isocurva` | sí (3) | sí (2) | B-515 |
| INSPECCIONAR | Análisis de mapas de entorno | `mapa_entorno` | sí (2) | sí (1) | — |
| INSPECCIONAR | Análisis de radio mínimo | `radio_minimo` | sí (2) | sí (1) | — |
| INSPECCIONAR | Análisis de sección | `seccion` | sí (29) | sí (10) | P-181,P-22c |
| INSPECCIONAR | Análisis de ángulo de desmoldeo | `angulo_desmoldeo` | sí (4) | sí (2) | — |
| INSPECCIONAR | Análisis del mapa de curvatura | `mapa_curvatura` | sí (1) | sí (2) | — |
| INSPECCIONAR | Barrido de parámetros | `barrido_parametros` | **no** | **no** | — |
| INSPECCIONAR | Buscar componentes similares | `buscar_similares` | **no** | **no** | — |
| INSPECCIONAR | Centro de masa | `centro_masa` | sí (25) | sí (1) | — |
| INSPECCIONAR | Interferencia | `interferencia` | sí (5) | sí (1) | B-481 |
| INSPECCIONAR | Mapa de desviación | `mapa_desviacion` | **no** | sí (2) | — |
| INSPECCIONAR | Medir | `medir` | sí (37) | sí (14) | B-335,B-411,B-461,B-503,B-515,B-546,B-598,B-672,P-99 |
| INSPECCIONAR | Mostrar colores de componente | `colores_componente` | sí (1) | sí (1) | — |
| INSPECCIONAR | Mostrar grupos de caras de malla | `ver_grupos_caras` | **no** | sí (1) | — |
| INSPECCIONAR | Propiedades | `propiedades` | sí (31) | sí (1) | B-172 |
| INSPECCIONAR | Reparar cuerpo | `reparar_cuerpo` | sí (3) | **no** | — |
| INSPECCIONAR | Revisar geometría | `revisar_geometria` | **no** | **no** | — |
| INSPECCIONAR | Sustainability Insights | `sustentabilidad` | sí (2) | sí (1) | — |
| MODIFICAR | Alargar | `sk_alargar` | sí (4) | **no** | — |
| MODIFICAR | Cambiar parámetros | `parametros` | sí (103) | sí (3) | H-68 |
| MODIFICAR | Curva de fusión | `sk_curva_fusion` | sí (3) | **no** | — |
| MODIFICAR | Desfase | `sk_desfase` | sí (43) | sí (12) | — |
| MODIFICAR | Empalme | `sk_empalme` | sí (35) | sí (5) | — |
| MODIFICAR | Escala del boceto | `sk_escala` | sí (24) | sí (4) | — |
| MODIFICAR | Mover/copiar | `sk_mover` | sí (14) | sí (2) | — |
| MODIFICAR | Partir | `sk_partir` | sí (5) | **no** | — |
| MODIFICAR | Recortar | `sk_recortar` | sí (5) | **no** | — |
| MODIFICAR | Soltar desfase | `sk_soltar_desfase` | sí (4) | **no** | — |
| MODIFICAR › Chaflán | sk_chaflan | `sk_chaflan` | sí (18) | sí (4) | — |
| MODIFICAR › Chaflán | sk_chaflan_dist_angulo | `sk_chaflan_dist_angulo` | sí (2) | sí (1) | — |
| MODIFICAR › Chaflán | sk_chaflan_dos_dist | `sk_chaflan_dos_dist` | sí (2) | sí (1) | — |
| RESTRICCIONES | sk_autorestringir | `sk_autorestringir` | sí (2) | **no** | — |
| RESTRICCIONES | sk_r_coincidente | `sk_r_coincidente` | sí (3) | sí (2) | — |
| RESTRICCIONES | sk_r_colineal | `sk_r_colineal` | **no** | sí (2) | — |
| RESTRICCIONES | sk_r_concentrica | `sk_r_concentrica` | **no** | sí (2) | — |
| RESTRICCIONES | sk_r_curvatura | `sk_r_curvatura` | sí (1) | sí (2) | — |
| RESTRICCIONES | sk_r_fijo | `sk_r_fijo` | sí (1) | sí (2) | — |
| RESTRICCIONES | sk_r_horizontal_vertical | `sk_r_horizontal_vertical` | sí (1) | sí (2) | — |
| RESTRICCIONES | sk_r_igual | `sk_r_igual` | **no** | sí (2) | — |
| RESTRICCIONES | sk_r_paralela | `sk_r_paralela` | sí (2) | sí (3) | — |
| RESTRICCIONES | sk_r_perpendicular | `sk_r_perpendicular` | **no** | sí (2) | — |
| RESTRICCIONES | sk_r_poligono | `sk_r_poligono` | sí (2) | sí (1) | — |
| RESTRICCIONES | sk_r_punto_medio | `sk_r_punto_medio` | sí (3) | sí (2) | — |
| RESTRICCIONES | sk_r_simetria | `sk_r_simetria` | sí (1) | sí (2) | — |
| RESTRICCIONES | sk_r_tangente | `sk_r_tangente` | sí (6) | sí (3) | — |
| SELECCIONAR | Seleccionar | `seleccionar` | sí (39) | sí (20) | — |
| SELECCIONAR | Selección de forma libre | `sel_libre` | **no** | **no** | — |
| SELECCIONAR | Selección de pintura | `sel_pintura` | sí (1) | **no** | — |
| SELECCIONAR | Selección en ventana | `sel_ventana` | **no** | **no** | — |
| SELECCIONAR › Filtros de selección | Aristas | `filtro_aristas` | sí (1) | **no** | — |
| SELECCIONAR › Filtros de selección | Caras | `filtro_caras` | sí (2) | **no** | — |
| SELECCIONAR › Filtros de selección | Cuerpos | `filtro_cuerpos` | sí (1) | **no** | — |
| SELECCIONAR › Filtros de selección | Perfiles y curvas de boceto | `filtro_bocetos` | sí (1) | **no** | — |
| SELECCIONAR › Filtros de selección | Planos, ejes y puntos | `filtro_construccion` | sí (1) | **no** | — |
| SELECCIONAR › Filtros de selección | Vértices | `filtro_vertices` | sí (1) | **no** | — |
| SELECCIONAR › Herramientas de selección | Crear conjunto de selección | `conjunto_seleccion` | sí (1) | **no** | — |
| SELECCIONAR › Herramientas de selección | Elegir conjunto de selección | `elegir_conjunto` | sí (1) | **no** | — |
| SELECCIONAR › Herramientas de selección | Invertir selección | `invertir_seleccion` | **no** | **no** | — |
| SELECCIONAR › Herramientas de selección | Seleccionar por límite | `seleccion_limite` | sí (1) | **no** | — |
| SELECCIONAR › Herramientas de selección | Seleccionar por nombre | `seleccion_nombre` | **no** | **no** | — |
| SELECCIONAR › Herramientas de selección | Seleccionar por tamaño | `seleccion_tamano` | **no** | **no** | — |
| SELECCIONAR › Herramientas de selección | Seleccionar todo | `seleccionar_todo` | **no** | **no** | — |
| SELECCIONAR › Herramientas de selección | Semilla y límite | `seleccion_semilla` | sí (1) | **no** | — |
| SELECCIONAR › Prioridad de selección | Prioridad de arista | `prioridad_arista` | sí (1) | **no** | — |
| SELECCIONAR › Prioridad de selección | Prioridad de cara | `prioridad_cara` | sí (1) | **no** | — |
| SELECCIONAR › Prioridad de selección | Prioridad de componente | `prioridad_componente` | sí (1) | **no** | — |
| SELECCIONAR › Prioridad de selección | Prioridad de cuerpo | `prioridad_cuerpo` | sí (1) | **no** | — |
| TERMINAR BOCETO | sk_terminar | `sk_terminar` | sí (1) | sí (3) | — |
| TERMINAR BOCETO | sk_terminar_auto | `sk_terminar_auto` | **no** | **no** | — |
