# Índice de la documentación

Mapa de todos los documentos del proyecto: uno por línea, con qué hay en cada uno.
Al agregar, mover o borrar un documento se actualiza este índice en el mismo commit.

## Estado del proyecto

| Documento | Qué tiene |
|---|---|
| [seguimiento/README.md](seguimiento/README.md) | Método: dónde se anota cada cosa y cómo se borra al resolverse |
| [seguimiento/bugs.md](seguimiento/bugs.md) | Bugs pendientes, verificados contra el código |
| [seguimiento/agenda.md](seguimiento/agenda.md) | Tareas que Gerardo programa para una fecha (AG-n) |
| [seguimiento/faltantes.md](seguimiento/faltantes.md) | Funciones pendientes (todavía no existen) |
| [seguimiento/mejoras.md](seguimiento/mejoras.md) | Mejoras pendientes de lo que ya existe: rendimiento, interfaz, instalador |
| Página de seguimiento (Artifact) | Vista web de bugs, faltantes, mejoras, lo último resuelto y los prompts para agentes; se refresca con `scripts/seguimiento_json.py` (pasos en `CLAUDE.md`). No es fuente de verdad |
| [../PROJECT_LOG.md](../PROJECT_LOG.md) | Bitácora: estado en una tabla, registro de cada tarea y lecciones aprendidas |
| [../CHANGELOG.md](../CHANGELOG.md) | Cambios de cada versión publicada |

## Para programar

| Documento | Qué tiene |
|---|---|
| [../AGENTS.md](../AGENTS.md) | Manual para agentes: reglas, mapa de carpetas, cómo verificar, recetas A, B y C |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Cómo contribuir |
| [arquitectura.md](arquitectura.md) | Capas de la app, flujo de datos y motores de geometría |
| [guia_comandos.md](guia_comandos.md) | Cómo se agrega un comando de diseño |
| [grafo.md](grafo.md) | Grafo de nodos (programación visual sin ventana) |
| [boceto_organizacion.md](boceto_organizacion.md) | Organización del boceto: categorías, grupos, visible / bloqueado / en perfiles, aislar, solver, API y cómo sumar un tipo de objeto |
| [registro_uso.md](registro_uso.md) | Registro local optativo de uso: privacidad, activación, archivos, detector, herramientas e informe |
| [f3d_formato.md](f3d_formato.md) | Archivos `.f3d` de Fusion: qué se lee (cuerpos, ocultos, bocetos, tabla del historial), qué no y la evidencia de por qué; rendimiento medido de BINCHA |
| [../clon/rust/README.md](../clon/rust/README.md) | Módulo Rust del render: compilar y probar |
| [../instalador/README.md](../instalador/README.md) | Cómo se arman el instalador de Windows y el AppImage |
| [../SECURITY.md](../SECURITY.md) | Cómo reportar una vulnerabilidad |

## Para agentes de IA (MCP y CLI)

| Documento | Qué tiene |
|---|---|
| [agentes/README.md](agentes/README.md) | Punto de entrada |
| [agentes/conectar.md](agentes/conectar.md) | Conectar cada cliente al MCP |
| [agentes/cli.md](agentes/cli.md) | La CLI `omnicad` |
| [agentes/puente.md](agentes/puente.md) | Modo en vivo con la ventana abierta |
| [agentes/guia_diseno.md](agentes/guia_diseno.md) | Dónde está la guía de diseño (`clon/omnicad/api/guia/`) |
| [agentes/herramientas.md](agentes/herramientas.md) | Lista de herramientas. **Generado**: `omnicad tools --markdown` |
| [../ejemplos/agentes/README.md](../ejemplos/agentes/README.md) | Ejemplos ejecutables |
| [../.claude/skills/omnicad/SKILL.md](../.claude/skills/omnicad/SKILL.md) | Skill `omnicad` que instala `omnicad setup` |
| [../.claude/skills/omnicad-test/SKILL.md](../.claude/skills/omnicad-test/SKILL.md) | Skill `omnicad-test`: probar el programa y anotar lo que falla en `seguimiento/` (Claude Code y OpenCode la leen del repo) |

## Documentación externa local

| Ruta | Qué tiene |
|---|---|
| [fusion_docs/](fusion_docs/LEEME.txt) | **Recurso indispensable.** Documentación oficial completa de Fusion 360 con imágenes (3473 artículos distintos en 24 carpetas; SUPERFICIE está en `fusion-patch`, el boceto en `fusion-sketch`). Se consulta antes de corregir un bug o agregar un faltante. No se sube a git (4,4 GB). Buscar con `scripts/fusion_docs.py buscar <palabras>` (índice de texto completo); árbol oficial por libro en `fusion_docs/indice/<carpeta>.md`; tabla pestaña → carpeta en `CLAUDE.md` |

## Planes

| Documento | Qué tiene |
|---|---|
| [plan_mcp_cli.md](plan_mcp_cli.md) | Plan de la capa para agentes (paquetes A–L) |
| [plan_rust.md](plan_rust.md) | Qué pasa a Rust (R1–R13) y arreglos de Python (P1–P24) |
| [plan_cpp.md](plan_cpp.md) | Qué pasa a C++ (C1–C5) |
| [plan_boceto_organizar.md](plan_boceto_organizar.md) | Organización, agrupación y manipulación de objetos en Boceto (prompt maestro de Gerardo); se borra al terminarla |
| [plan_velocidad.md](plan_velocidad.md) | Pruebas y procesos más rápidos: medir, suite en paralelo, tests por impacto, humo sin cursor real (A–G) |
| [plan_caza_errores.md](plan_caza_errores.md) | Programa que busca errores solo (`scripts/caza/`): capas, jueces automáticos, comandos y cómo quedó |
| [plan_reconstruir_solido.md](plan_reconstruir_solido.md) | De una malla a una pieza paramétrica (RI-1–RI-6, F10, F11) |
| [plan_escaneo_celular.md](plan_escaneo_celular.md) | Escanear una pieza con el celular (ESC-1–ESC-7) |
| [plan_texto_vectores.md](plan_texto_vectores.md) | Plan de texto y vectores |
| [plan_boceto.md](plan_boceto.md) | Plan por fases para llevar el boceto al nivel de Fusion (auditoría 2026-10-23) |
| [plan_iconos.md](plan_iconos.md) | Plan de íconos, hecho el 2026-10-26: timeline con ícono propio por paso, insignias, gramática visual medida y tema en vivo; con el resultado de la prueba como usuario |
| [plan_asistente_ia.md](plan_asistente_ia.md) | Plan del Asistente IA: chat dentro de la app que diseña con el usuario, por API o con su suscripción (IA-1–IA-8) |

## Especificación de faltantes (brechas)

Describen cada función de otro programa que queremos tener. Lo que falta de cada ID está en
[seguimiento/faltantes.md](seguimiento/faltantes.md); si un ID no figura allá, ya está resuelto.

| Documento | IDs |
|---|---|
| [brechas_fusion.md](brechas_fusion.md) | Fusion 360 |
| [brechas_texto_curva.md](brechas_texto_curva.md) | Texto en curva: B-132–B-137, TXT-8 y TXT-9, con prompt |
| [brechas_superficie.md](brechas_superficie.md) | SUP-27–SUP-31: SUPERFICIE contra capturas de Fusion, con prompt |
| [brechas_ensamblar.md](brechas_ensamblar.md) | ASM-17–ASM-20: ENSAMBLAR contra capturas de Fusion, con prompt |
| [brechas_animacion.md](brechas_animacion.md) | ANI-1–ANI-5: ANIMACIÓN contra capturas de Fusion, con prompt |
| [brechas_extensiones.md](brechas_extensiones.md) | PLA-1–PLA-14 y EXT-1–EXT-4: plástico y extensiones contra capturas de Fusion, con prompt |
| [brechas_parametros.md](brechas_parametros.md) | PAR-1–PAR-11: Parámetros contra Fusion |
| [brechas_aspecto.md](brechas_aspecto.md) | Aspecto, materiales y colores contra Fusion; el video de la placa del 2026-11-05 (B-198–B-202, H-72–H-76) |
| [brechas_gizmos.md](brechas_gizmos.md) | H-60 (cerrado el 2026-11-02): asas que se vean y se entiendan |
| [brechas_previa_aislada.md](brechas_previa_aislada.md) | B-155 y RS-X6: error oculto y demora de la vista previa aparte |
| [brechas_inspeccionar.md](brechas_inspeccionar.md) | Especificación de INSPECCIONAR contra capturas de Fusion (resuelta, ver su auditoría) |
| [brechas_construir.md](brechas_construir.md) | CON-1–CON-8: CONSTRUIR contra capturas de Fusion |
| [brechas_proyeccion.md](brechas_proyeccion.md) | Proyectar/Incluir del boceto contra la ayuda de Fusion (B-119, B-203, B-204, H-77 a H-80) |
| [brechas_herramientas_solido.md](brechas_herramientas_solido.md) | CAP-1–CAP-14: herramientas de SÓLIDO contra capturas de Fusion |
| [brechas_freecad.md](brechas_freecad.md) | F1–F23 |
| [brechas_plasticity.md](brechas_plasticity.md) | PL1–PL13 |
| [brechas_blender.md](brechas_blender.md) | B1–B19 (no confundir con los bugs B-n) |
| [brechas_rhino.md](brechas_rhino.md) | RH1–RH22 |
| [brechas_grasshopper.md](brechas_grasshopper.md) | GH1–GH12 |
| [brechas_keyshot.md](brechas_keyshot.md) | KS1–KS15 |
| [brechas_vray.md](brechas_vray.md) | VR1–VR13 |
| [brechas_mcp.md](brechas_mcp.md) | MCP-0a–MCP-94: especificación de las herramientas para agentes (todas hechas; B-80 cerrado) |
| [brechas_solidcraft.md](brechas_solidcraft.md) | SC1–SC17 |
| [brechas_cad_libres.md](brechas_cad_libres.md) | CL1–CL8 |

## Informes (fotos de un momento: no se actualizan)

| Documento | Qué tiene |
|---|---|
| [auditorias/](auditorias/) | Auditoría total del 2026-10-14 (cuatro informes) y [fluidez del 2026-10-28](auditorias/fluidez-2026-10-28.md) (por qué la extrusión interactiva se ve a saltos; mediciones y plan) |
| [auditorias/previa-comandos-2026-10-28.md](auditorias/previa-comandos-2026-10-28.md) | Costo de las previas de Empalme, Chaflán, Cortar, Unir, Intersecar, Vaciado y patrones: 32 casos, 96 corridas, kernel/teselado/dibujo y límites; banco reproducible sin arreglos de producción |
| [auditorias/previa-asincrona-2026-10-29.md](auditorias/previa-asincrona-2026-10-29.md) | Previa en proceso aparte para Empalme, Chaflán, booleanas, patrones y Vaciado: cuadros, asas y latencia hasta el sólido exacto por comando, y la causa del «piso» del Vaciado (P-55). |
| [auditorias/inspeccionar_2026-11-01.md](auditorias/inspeccionar_2026-11-01.md) | Las 15 herramientas de INSPECCIONAR probadas como persona: antes y después con mediciones, comparación con Fusion por panel y fuentes de los factores de CO₂ |
| [auditorias/patrones-solidos-2026-10-31.md](auditorias/patrones-solidos-2026-10-31.md) | Patrón rectangular, circular, en trayectoria, en puntos y Multitransformación: qué dice la ayuda de Fusion, matriz por herramienta (problema, evidencia, causa, corrección, prueba, pendiente) y las filas PAT-1 a PAT-6 del seguimiento |
| [auditorias/desfase_boceto_2026-10-31.md](auditorias/desfase_boceto_2026-10-31.md) | Matriz de equivalencia del Desfase del boceto contra Fusion (31 filas, con su evidencia: video, ayuda, código, pruebas) y lo que no se pudo verificar |
| [auditorias/boceto_crear_modificar_inventario.md](auditorias/boceto_crear_modificar_inventario.md) | Inventario de los 55 comandos de CREAR y MODIFICAR del boceto, comparación con Fusion y hallazgos (fase 1 de la [auditoría de CREAR y MODIFICAR](auditoria_boceto_crear_modificar.md)) |
| [auditorias/restricciones_inventario_2026-11-06.md](auditorias/restricciones_inventario_2026-11-06.md) | Inventario de las 16 restricciones y 7 cotas del boceto (fase A de la [auditoría de restricciones](auditoria_restricciones.md)): entidades, ecuación del solver, GDL, botón, herramienta MCP, comparación con Fusion y sospechas a verificar |
| [auditorias/ui_paneles_2026-10-31.md](auditorias/ui_paneles_2026-10-31.md) | Paneles de herramienta: sistema común (cabecera por modo, jerarquía «Más opciones», selección legible, ancho fijo, mensajes tipados), matriz de los 148 comandos y 16 diálogos (antes/después, verificación) y límites; filas `UI-2` y `UI-6` del seguimiento (las demás `UI-n` ya se resolvieron) |
| [auditorias/rust-pipeline-2026-10-31.md](auditorias/rust-pipeline-2026-10-31.md) | Pipeline de rendimiento: qué pasa a Rust y qué no, estado de los planes anteriores, mediciones de hoy (proyectos de 292 pasos, `.f3d`, mallas, rayos, boceto), fases, permisos y pruebas de aceptación (filas `RS-X*`) |
| [auditoria_extruir.md](auditoria_extruir.md) | Extruir en SÓLIDO, SUPERFICIE, PLÁSTICO, CHAPA, FORMA y MCP/CLI contra la ayuda de Fusion: matriz por opción, bugs hallados (B-205, B-206, B-207, B-197) con su informe de arreglos (B-206 quedó en Parcial), faltantes (H-81 a H-85) y mejoras (H-86, H-87) |
| [auditoria_restricciones.md](auditoria_restricciones.md) | Auditoría y corrección de todo el sistema de restricciones del boceto (B-223: Coincidente con el origen no mueve la geometría); corridas de los agentes e informe final (completo: quedan H-106 y B-231) |
| [auditoria_boceto_crear_modificar.md](auditoria_boceto_crear_modificar.md) | Auditoría y reparación de todos los comandos de CREAR y MODIFICAR del boceto contra Fusion y SOLIDWORKS; arranca después de la de restricciones |
| [auditoria_revolucion_barrido_solevacion.md](auditoria_revolucion_barrido_solevacion.md) | Revolución, Barrido y Solevación en todos los espacios contra la ayuda de Fusion: matriz, bugs (B-208 a B-212), faltantes (H-88 a H-91) y mejoras (H-92 a H-94) |
| [auditoria_nervio_red_repujado.md](auditoria_nervio_red_repujado.md) | Nervio, Red y Repujado en todos los espacios contra la ayuda de Fusion: matriz, bugs (B-213 a B-217), faltantes (H-95 a H-97) y mejoras (H-98 a H-100) |
| [auditoria_herramientas_3d.md](auditoria_herramientas_3d.md) | Auditoría y reparación de Agujero, Rosca, primitivas, Bobina, Tubería, Engranaje, Eje, Patrón, Simetría, Engrosar, Llenado de contorno, Sólido delimitador y Volumen de fluido en todos los espacios, contra la ayuda de Fusion. Solo el prompt guardado: se hace otro día (agenda AG-2). |
| [modelos_gratis.md](modelos_gratis.md) | Modelos gratis de Cline, OpenCode, Kiro, Qoder, Kilo y CodeBuddy: cuáles responden, cuáles sirven para OmniCAD y cómo repetir la prueba |
| [arreglos_qwen.md](arreglos_qwen.md) | Arreglos con Qwen3.8-Flash en OpenCode: por qué el prompt es así, tandas de dos bugs con gemelos y tests obligatorios, prompt e informes |
| [corrida_nocturna_2026-11-05.md](corrida_nocturna_2026-11-05.md) | Corrida nocturna: Qwen (Qoder) en las tandas de `arreglos_qwen.md` y Sol (OpenCode, rama aparte) en la geometría difícil; plan, uso de tokens e informe de la mañana |
| [auditorias/informe_tortura_2026-10-17.md](auditorias/informe_tortura_2026-10-17.md) | Prueba de tortura del reductor y bugs T-01 a T-18 |
| [auditorias/asas_2026-11-01.md](auditorias/asas_2026-11-01.md) | Asas de 35 comandos en 4 vistas, antes y después: largo visible de las flechas y cajas de valor sobre las asas; Análisis de sección con la tríada |
| [auditorias/construir_2026-11-01.md](auditorias/construir_2026-11-01.md) | Las 20 herramientas de CONSTRUIR en la ventana, antes y después, contra las capturas de Fusion |
| [auditorias/prueba_nocturna_2026-10-31.md](auditorias/prueba_nocturna_2026-10-31.md) | Todo lo que falta probar sobre el código final y en qué orden correrlo de noche (se borra a medida que queda verde). Script: `scripts/cierre_completo.sh` |
| [comparacion_motores.md](comparacion_motores.md) | OpenCascade contra OmniKernel. **Generado**: `scripts/comparar_motores.py` |
| [inventario_motor.md](inventario_motor.md) | Funciones del núcleo por motor. **Generado**: `scripts/estado_motor.py` |
| [novedades/](novedades/) | Novedades mensuales de Fusion, Blender y Rhino. **Generado**: `scripts/novedades.py` |
| [diseno/](diseno/), [img/](img/) | Imágenes de referencia y del README |
