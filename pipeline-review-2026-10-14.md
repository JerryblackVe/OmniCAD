# Pipeline Review — OmniCAD

2026-10-14 · 6 de ~10 flujos/entry-points mapeados (los 4 restantes son herramientas de desarrollo: `instalador/armar.py`, `scripts/capturas_*.py`, `scripts/turno.py` — no forman parte del producto y quedaron fuera del mapa)

## En criollo (3 líneas)

El programa está bien armado de punta a punta: no se encontró nada roto entre las piezas (ningún CRÍTICO). Lo que más choca es **el papel contra la realidad**: hay 5 pendientes escritos como «sin programar» que el código YA hace (texto sobre curva, patrones en puntos/ruta, export glTF, limpieza de malla, nodos grasshopper), así que quien lea las listas va a creer que falta cosas que ya están. Además, el mismo diccionario de nombres de piezas («Cara», «Arista», «Boceto»…) está escrito dos veces en dos archivos distintos: si un día se renombra uno, la interfaz va a mostrar las dos versiones a la vez.

## 1. El mapa

```
FLUJO 1 · App de escritorio (GUI)
  entrada   main()                                   clon/OmniCAD.py
  → ventana VentanaPrincipal                          clon/omnicad/ui/ventana.py
  → comandos CATALOGO → crear_op                      clon/omnicad/ui/comandos/*
  → ejecuta Operacion.ejecutar                        clon/omnicad/timeline/operaciones.py
  → geometría OCC pura                                clon/omnicad/nucleo/*
  → pinta    Visor3D.update (teselar_cuerpo)          clon/omnicad/ui/visor3d.py
  salida    .omnicad / STEP / STL / DXF               clon/omnicad/io_archivos/*
```

```
FLUJO 2 · CLI (omnicad)
  entrada   main() → Parser → cmd_* autodescubiertos  clon/omnicad/cli/__init__.py:77
  → Sesion + api.llamar sobre el catálogo             clon/omnicad/api/registro.py
  salida    JSON por stdout / archivo exportado       clon/omnicad/cli/util.py
```

```
FLUJO 3 · Servidor MCP (omnicad-mcp)
  entrada   main() → ServidorOmniCAD                  clon/omnicad/servidor_mcp/principal.py
  → mismo catálogo api (herramientas_* autoregistran  clon/omnicad/api/__init__.py:19-21
    via pkgutil)
  salida    JSON-RPC por stdio al agente
```

```
FLUJO 4 · Puente en vivo (MCP → ventana abierta)
  ClientePuente.llamar                                 clon/omnicad/servidor_mcp/puente_cliente.py:16
  ↔ protocolo compartido                               clon/omnicad/api/protocolo_puente.py
  ↔ ui/puente.py:32 (servidor dentro de la app)        clon/omnicad/ui/puente.py
  salida    actúa sobre el documento ABIERTO (recálculo + repaint)
```

```
FLUJO 5 · Grafo de nodos (programación visual)
  entrada   run_graph / bake_graph                     clon/omnicad/api/herramientas_grafo.py:21-22
  → motor de árboles de datos                          clon/omnicad/grafo/*
  salida    cuerpos (salida) u operación horneada      timeline/ops_grafo.py
```

```
FLUJO 6 · Fusion 360 (solo lectura .f3d/.f3z vía add-in, unidireccional)
  io_archivos/puente_fusion.py:30 (cliente HTTP)
  → integraciones/fusion/OmniCADPuente (add-in que corre EN Fusion)
  salida    documento_desde_archivo (abrir_externo.py) — sin duplicar al MCP
```

Fuera del mapa: ningún módulo de `clon/omnicad/` quedó sin importador (conteo automático sobre 161 archivos + re-verificación manual de todo candidato con ≤2 hits). `ui/bench.py` y `ui/captura.py` (que parecen sueltos) los lanzan como subprocesos `api/herramientas_dev.py:174,235` y `cli/cmd_dev.py:51,78`.

## 2. Hallazgos

### CRÍTICO

Sin hallazgos CRÍTICOS. (Se intentó refutar tres sospechas: «dos despachadores MCP» — refutada, `servidor_mcp/principal.py` no referencia `integraciones`; «grafo/ muerto» — refutada, autoregistrado y testeado por `test_api_grafo.py`; «docs MCP desactualizadas» — refutada, `tests/test_doc_agentes.py` falla si la doc generada envejece.)

### MEDIO

- **`ui/ventana.py:1423` y `ui/medidas.py:6` — la misma tabla de nombres de entidad (11 claves idénticas: cara/Cara, arista/Arista…) escrita dos veces** — dos fuentes de verdad para el mismo vocabulario; si se renombra un tipo, la barra de medidas y el diálogo «Seleccionar otro» mostrarán palabras distintas — dejar solo `ui/medidas.py:6` (la de plural+singular) e importarla desde ventana.
- **`PROJECT_LOG.md` y `docs/brechas_indice.md` — 5 pendientes marcados «sin programar» / «falta» cuyo código YA existe** (detalle en §3) — quien planifique desde esos documentos va a re-hacer trabajo ya hecho — actualizar las listas (no el código).
- **`docs/plan_mcp_cli.md` dice «~35 por defecto / 85 operaciones» y el catálogo real ya es de 167 herramientas** (Registro 2026-10-13) — la cifra guía del plan quedó muy vieja.

### BAJO

- **`cli/__init__.py:119` emite el kind `CLI_USAGE` sin registrarlo en `api/errores.PISTAS`** — excepción implícita a la regla escrita en AGENTS.md («un kind nuevo se agrega en errores.PISTAS»); inofensiva hoy porque la CLI arma ese JSON sí misma, pero rompe la convención — agregar la entrada en PISTAS o documentar la excepción.

## 3. Plan contra realidad

Plan encontrado en: `PROJECT_LOG.md` (2026-10-13/14, lista de pendientes) + `docs/plan_mcp_cli.md` + `docs/brechas_indice.md`.

| Ítem | Estado | Propuesta |
|---|---|---|
| Pendiente 12b-1 «texto sobre una curva: falta» | SUPERADO — `restricciones/boceto.py:237-275` (`Texto.camino`…), API `add_text(path_entity=…)` | actualizar plan — el código lo hace desde la tanda de texto |
| Pendiente 13 «Patrones (F1/F2/F3): sin programar» | SUPERADO — F2 `nucleo/revision.py`, F1 `nucleo/engranajes.py`, F3 `api/herramientas_solido.py:612,640` (`point_pattern`, `path_pattern` con twist) | actualizar plan — solo falta F4 (patrón sobre tabla) según la ficha |
| Pendiente 15 «Blender B3/B9/B4: sin programar» | SUPERADO — B3 `io_archivos/gltf.py`, B9 limpieza de malla, B4 `io_archivos/vectorizar.py:92` + `trace_image` | actualizar plan |
| Pendiente 17 «Grasshopper GH1–3/GH5/GH8: sin programar» | SUPERADO — `grafo/` + `run_graph`/`bake_graph`; GH4 (lienzo visual) sigue FALTA correctamente | actualizar plan marcando GH4 como lo único vivo |
| Brecha B4 (vectorizar imagen) | SUPERADO y no marcada ni en «Hecho» ni en pendiente 5 | actualizar índice |
| Cifra «~85 operaciones» del plan MCP/CLI | DISTINTO — catálogo real: 167 herramientas | actualizar plan |
| Pendiente 8 «instalador: pendiente» | DISTINTO — `instalador/README.md` + v0.1.0 publicada; falta validar el .exe y el arranque guiado | actualizar plan (queda lo de validación) |
| Pendiente 21 «recuperación: diálogo tabla estilo Fusion» | DISTINTO — multi-huérfano con token por doc ya hecho (`ui/ventana.py:2051-2065`); falta la tabla Abrir/Suprimir | actualizar plan |
| Bilingüe, MP4/cámara en ruta, boceto 3D, hélice de boceto, aspecto por cara, grupos de timeline, excepthook/«Reportar problema», Rust/C++ | FALTA confirmado en código (0 usos de QTranslator/ffmpeg/sys.excepthook/…) | corregir código (son pendientes reales) o bajarles prioridad — a elección |

## 4. Qué conviene correr después

1. `/vibe-coding-audit` — pendiente 20 sin implementar (0 usos de `sys.excepthook`/`faulthandler` fuera de tests) deja a la app sin el informe automático en un crash nativo: amerita el barrido completo de severidad.
2. `/ponytail-audit` — la duplicación `ventana.py:1423`/`medidas.py:6` sugiere que puede haber más vocabulario o constantes duplicadas a nivel repo.

## 5. Qué no pude ver

- Los flujos de dev-tooling (`instalador/armar.py`, `scripts/capturas_*.py`, `scripts/turno.py`) no se mapearon internamente; solo se verificó que son invocables desde fuera y no son muertos.
- Pendiente 1 (Linux/Wayland) y paquete K del plan MCP no son verificables por lectura de código — son pruebas en entorno real.
- El recorrido de UI «a mano» (qué hace cada botón de la cinta) no se ejercitó: el mapa cubre el pipeline, no cada pantalla.
