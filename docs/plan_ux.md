# Plan UX por fases

> **No ejecutar hasta el OK de Gerardo** (20/11: el protocolo [protocolo_ux.md](protocolo_ux.md) rige ya para todo trabajo nuevo de UI; este plan se ejecuta cuando él lo diga). Los ítems no están en `ahora.md`.


Modelos según el «Protocolo de ahorro»: Opus solo en solver, geometría, núcleo y velocidad; todo esto es UI: **Sonnet medio** salvo que se indique. Un ítem por sesión, un worktree por ítem, con `ponytail` y `ponytail-review` del brief. Cada ítem entra a `docs/seguimiento/` con su ID (siguiente P- libre mirando todos los worktrees).

**Orden de prioridad** (regla 1 de nivel 1): Bocetos → Sólido → Superficie → resto. F0 es base y va primero; F1 y F2 ya están en curso (P-186/187/188), por lo que F0.1 y F0.2 deben cerrarse antes de que sigan.

### F0. Base (bloquea al resto)

| Ítem | Qué | Archivos | Quién | Listo cuando |
|---|---|---|---|---|
| F0.1 | **Tokens de estilo**: radio (4/8/12), espaciado, sombra, `DURACION_ANIM_MS` y colores de peligro/aviso en `temas.py`; reemplazar los `setStyleSheet` fijos de los 16 archivos con `border-radius` por `objectName`/rol del QSS | `ui/temas.py`, `ui/comando.py:1075`, `ui/visor3d.py:130`, `ui/superposiciones.py:830`, `ui/registro_uso.py:65`, `ui/preferencias.py:471`, `ui/aspectos_ui.py:535` | E8 Sonnet medio | `tests/test_ux_estilo.py` falla ante `#rrggbb`/`border-radius` nuevo en `ui/` fuera de `temas.py`; capturas claro/oscuro/150 % iguales de coherentes |
| F0.2 | **Tarjeta común** (`Tarjeta`): cabecera, ≤ 5 campos, «Más opciones», pie Aceptar/Cancelar fijo, «?» y estado; la usan `PanelComando`, `panel_patron`, `panel_simetria`, `objetos_vectoriales`, `dialogo_autorestringir`, `dialogo_parametros` | `ui/formulario.py`, `ui/comando.py` | E3 Sonnet medio (Opus alto solo si toca `PanelComando` a fondo) | un test recorre `CATALOGO` y falla si algún comando muestra > 5 campos sin avanzados, o si el pie no es Aceptar-derecha/Cancelar-izquierda; lista de excepciones con ID |
| F0.3 | **Atajos**: verificar P-165 con prueba real, borrar o recortar la fila; test de que todo `CATALOGO` tiene atajo editable; ⋮ «Cambiar teclas…» por botón de cinta | `ui/pagina_atajos.py`, `api/atajos.py`, `ui/cinta_items.py` | E8 Sonnet medio | `list_shortcuts` cubre el 100 % de `CATALOGO`; test de choque; fila P-165 resuelta |
| F0.4 | **Modo simple/experto**: preferencia `interfaz/modo`, cinta simple por defecto, «Más opciones» recordado en experto | `ui/preferencias.py`, `api/cinta_personal.py`, `ui/cinta.py`, herramienta `set_preference` | E8 Sonnet medio (decisión de producto: pedir su «sí» al coordinador antes) | en simple, la cinta de cada pestaña tiene ≤ 12 botones; test de la preferencia y de la API |
| F0.5 | **Test de tooltips y mensajes**: tooltip en todo botón con ícono, mensajes ≤ 60 caracteres en todos los paneles (amplía `test_p158_mensajes_cortos.py`) | `tests/test_ux_tooltips.py`, `tests/test_p158_mensajes_cortos.py` | E7 Sonnet medio | los tests pasan en toda la app o con excepciones con ID |
| F0.6 | **Documentos**: crear `docs/protocolo_ux.md` desde la Parte 2; enlazar desde CLAUDE.md, AGENTS.md y brief; recortar S1/S2 | los de abajo | coordinador | `tests/test_reglas_coherentes.py` pasa con la constante única (5 campos, 60 caracteres, 0,2 s) |

### F1. Boceto (prioridad 1)

| Ítem | Qué | Archivos | Quién | Listo cuando |
|---|---|---|---|---|
| F1.1 | **P-188 Texto**: UNA tarjeta (contenido, fuente, altura, alineación); resto en «Más opciones»; la barra flotante y «Objetos vectoriales y texto» no se abren encima | `ui/editor_boceto_texto.py`, `ui/objetos_vectoriales.py` | E3 Sonnet medio (ya asignado) | checklist 1–6 con capturas; el panel Carácter pasa de ~15 a 5 campos visibles |
| F1.2 | **P-187 Cinta de boceto** como Fusion + ⋮ «Anclar» + arrastre | `ui/cinta_boceto.py`, `ui/pagina_cinta.py` | E8 Sonnet medio (ya asignado) | RESTRICCIONES con los ~12 botones de Fusion; test de la config por defecto; `set_ribbon_section` consistente |
| F1.3 | **P-186 Mosaico de restricciones** (miniatura dibujada, conteos, ⋮) | `ui/dialogo_autorestringir.py` | E4 Sonnet medio (ya asignado) | captura comparada con Fusion; dentro de la tarjeta común |
| F1.4 | Todos los comandos de boceto contra la lista de control | `ui/editor_boceto_*.py`, `ui/comandos/` | E1 Sonnet medio (UI de boceto; el solver no se toca) | checklist 1–15 por comando, sin excepciones sin ID |
| F1.5 | **Prueba del novato** del boceto: 5 tareas (rectángulo, cota, restricción, texto, extruir) | `scripts/prueba_ui/` | E7 + E11 (con OK de Gerardo si es cursor real) | cada tarea < 60 s sin ayuda; tiempos en `evidencias/` |

### F2. Sólido

| Ítem | Qué | Archivos | Quién | Listo cuando |
|---|---|---|---|---|
| F2.1 | Crear: extruir, revolución, barrido, solevación, nervio, red, repujado, agujero, rosca, primitivas, patrón, simetría, engrosar | `ui/comandos/crear.py`, `panel_patron.py`, `panel_simetria.py` | E2 Sonnet medio | checklist por comando; ≤ 5 campos visibles; previa en vivo |
| F2.2 | Modificar: pulsar/tirar, empalme, chaflán, vaciado, combinar, dividir, mover | `ui/comandos/modificar.py` | E3 Sonnet medio | ídem; el aviso del Empalme (6 renglones) ya en 1 |
| F2.3 | P-158 resto: tope rojo en el asa en vez de texto | `ui/asas_boceto.py`, `ui/manipuladores.py` | E3 Sonnet medio | test de largo + captura del asa en rojo |
| F2.4 | Prueba del novato del sólido (extruir, vaciar, empalmar) | `scripts/prueba_ui/` | E7 + E11 | < 60 s sin ayuda |

### F3. Superficie, Construir, Inspeccionar, Ensamblar

| Ítem | Qué | Archivos | Quién | Listo cuando |
|---|---|---|---|---|
| F3.1 | Superficie (crear y modificar) | `ui/comandos/superficie.py` | E4 Sonnet medio | checklist |
| F3.2 | Construir, Inspeccionar, Ensamblar | `ui/comandos/construir.py`, `inspeccionar.py`, `ensamblar.py` | E5 Sonnet medio | checklist |
| F3.3 | Mensajes de Malla, Chapa y resto (cierra P-158) | `ui/comandos/*` | E8 Sonnet medio | P-158 resuelta |

### F4. Preferencias, ayuda y accesibilidad

| Ítem | Qué | Archivos | Quién | Listo cuando |
|---|---|---|---|---|
| F4.1 | **P-157**: árbol de páginas como Fusion, muestras visuales, nada cortado a 1024×700 | `ui/preferencias.py` | E9/OpenCode prepara; E8 integra | captura a 1024×700, sin cortes |
| F4.2 | **NOV-tip-1**: letra 120–150 % sin títulos elididos | `ui/cinta.py`, `ui/temas.py` | E8 Sonnet medio | `evidencias/tipografia_ui/f3_ventana_150.py` en verde |
| F4.3 | **Ayuda con video**: lugar `docs/ayuda/`, reproductor chico (GIF/WebP animado primero, sin multimedia pesada), «?» con clip; 5 clips piloto | `ui/comando.py` (botón `?`), nuevo `ui/ayuda_clip.py` | E8 Sonnet medio; guiones y grabación: E11 | el «?» de Extruir muestra un clip < 15 s; sin clip no se rompe |
| F4.4 | **Animaciones**: ninguna hoy; si se agregan (fundido de tarjeta, plegado), con `DURACION_ANIM_MS` y «Reducir movimiento» | `ui/temas.py`, `ui/formulario.py` | E8 Sonnet medio | test que falla si una animación pasa de 200 ms |
| F4.5 | **Confirmaciones**: lista de acciones peligrosas (las 18 `QMessageBox`), mismo diálogo, mismo orden de botones | `ui/dialogos.py` | E8 Sonnet medio | test de la lista; «Cancelar» es el botón por defecto |

### F5. Medición continua

| Ítem | Qué | Archivos | Quién | Listo cuando |
|---|---|---|---|---|
| F5.1 | Tareas patrón del novato (10 tareas) y tiempo objetivo 60 s en `scripts/prueba_ui/novato/` | `scripts/prueba_ui/` | E7 Sonnet medio | informe nocturno con tiempo por tarea; lo rojo va a `docs/seguimiento/` |
| F5.2 | Barrido nocturno: tests UX (`test_ux_*.py`) dentro de la suite | `scripts/suite_noche.sh` | coordinador | resultado en `ultima.txt` |

**Cantidad: 6 fases (F0 a F5), 26 ítems.** F0 es la base; sin F0.1 y F0.2 no se debe avanzar con F1.2 ni F1.1 (ya en curso: pedir a E3 y E8 que lean el protocolo primero).

Decisiones tomadas (maestro, 20/11): (1) el modo simple trae la cinta con las herramientas por defecto de Fusion (las de P-187); (2) el «?» va solo con texto hasta que haya clips; los videos son una fase aparte (F4.3).

---
