# Índice de la documentación

Mapa de todos los documentos del proyecto: uno por línea, con qué hay en cada uno.
Al agregar, mover o borrar un documento se actualiza este índice en el mismo commit.

## Estado del proyecto

| Documento | Qué tiene |
|---|---|
| [seguimiento/README.md](seguimiento/README.md) | Método de seguimiento: estados, dificultad y evidencia |
| [seguimiento/bugs.md](seguimiento/bugs.md) | Bugs abiertos y cerrados, verificados contra el código |
| [seguimiento/faltantes.md](seguimiento/faltantes.md) | Funciones que todavía no existen |
| [seguimiento/mejoras.md](seguimiento/mejoras.md) | Mejoras de lo que ya existe: rendimiento, interfaz, instalador |
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

## Planes

| Documento | Qué tiene |
|---|---|
| [plan_mcp_cli.md](plan_mcp_cli.md) | Plan de la capa para agentes (paquetes A–L) |
| [plan_rust.md](plan_rust.md) | Qué pasa a Rust (R1–R13) y arreglos de Python (P1–P24) |
| [plan_cpp.md](plan_cpp.md) | Qué pasa a C++ (C1–C5) |
| [plan_texto_vectores.md](plan_texto_vectores.md) | Plan de texto y vectores |

## Especificación de faltantes (brechas)

Describen cada función de otro programa que queremos tener. El estado de cada ID está en
[seguimiento/faltantes.md](seguimiento/faltantes.md), no en estos archivos.

| Documento | IDs |
|---|---|
| [brechas_fusion.md](brechas_fusion.md) | Fusion 360 |
| [brechas_freecad.md](brechas_freecad.md) | F1–F23 |
| [brechas_plasticity.md](brechas_plasticity.md) | PL1–PL13 |
| [brechas_blender.md](brechas_blender.md) | B1–B19 (no confundir con los bugs B-n) |
| [brechas_rhino.md](brechas_rhino.md) | RH1–RH22 |
| [brechas_grasshopper.md](brechas_grasshopper.md) | GH1–GH12 |
| [brechas_keyshot.md](brechas_keyshot.md) | KS1–KS15 |
| [brechas_vray.md](brechas_vray.md) | VR1–VR13 |
| [brechas_mcp.md](brechas_mcp.md) | MCP-0a–MCP-77: herramientas para agentes que faltan |
| [brechas_solidcraft.md](brechas_solidcraft.md) | SC1–SC17 |
| [brechas_cad_libres.md](brechas_cad_libres.md) | CL1–CL8 |

## Informes (fotos de un momento: no se actualizan)

| Documento | Qué tiene |
|---|---|
| [auditorias/](auditorias/) | Auditoría total del 2026-10-14 (cuatro informes) |
| [informe_tortura_2026-10-17.md](informe_tortura_2026-10-17.md) | Prueba de tortura del reductor y bugs T-01 a T-18 |
| [comparacion_motores.md](comparacion_motores.md) | OpenCascade contra OmniKernel. **Generado**: `scripts/comparar_motores.py` |
| [inventario_motor.md](inventario_motor.md) | Funciones del núcleo por motor. **Generado**: `scripts/estado_motor.py` |
| [novedades/](novedades/) | Novedades mensuales de Fusion, Blender y Rhino. **Generado**: `scripts/novedades.py` |
| [diseno/](diseno/), [img/](img/) | Imágenes de referencia y del README |
