# Prueba de un modelo gratis en Cline

Dos pendientes chicos para medir la calidad de un modelo gratis antes de darle más trabajo. No tocan archivos de la
tanda de `plan_bugs_faciles.md`. Al terminar la prueba se borran este documento y sus dos filas de índice
(`docs/README.md` y `docs/seguimiento/README.md`).

| ID | Qué | Archivo principal |
|---|---|---|
| AUD-13 | Una sola variable para la carpeta de los puentes | `io_archivos/puente_fusion.py` y el complemento de Fusion |
| PLA-14 | Valores predefinidos: recordar el orden y ordenar por uso | `nucleo/preajustes.py`, `ui/preajustes_ui.py` |

## Prompt para el agente

Entregado el 2026-11-02. Modelo sugerido: Nemotron Super VL en Cline, esfuerzo medio. Es la versión 3.5, gratis. Si se traba, repetir con Beam.

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá las skills fable-method y ponytail, plan-then-do, tool-calling-guard y verify-before-commit. Si no aparecen como
skills, leé su SKILL.md en C:\Users\mosos\.claude\skills\<nombre>\ y seguilo. Antes de cerrar aplicá ponytail-review
de la misma forma y pegá su salida completa en el informe.

OBJETIVO
Resolver dos pendientes de OmniCAD, uno por vez: primero AUD-13, después PLA-14.

CONTEXTO
- Repo D:\PROGRAMA, rama main. Leé AGENTS.md. Trabajá desde clon/ con clon/.venv.
- Otro agente está trabajando en la misma carpeta: tocá solo los archivos de estas dos tareas.
- Si ves cambios sin commitear en otros archivos, son de ese agente: no los toques ni los reviertas.

TAREA 1: AUD-13
Hoy hay dos variables para mover la carpeta de datos de los puentes: OMNICAD_PUENTE_DIR y OMNICAD_PUENTE_FUSION_DIR.
1. Hacé que el puente con Fusion también acepte OMNICAD_PUENTE_DIR.
2. Regla de carpeta, en este orden: OMNICAD_PUENTE_FUSION_DIR si está puesta (compatibilidad con lo viejo), después
   OMNICAD_PUENTE_DIR, después la carpeta normal.
3. La misma regla va en clon/omnicad/io_archivos/puente_fusion.py y en
   clon/omnicad/integraciones/fusion/OmniCADPuente/OmniCADPuente.py. El complemento corre dentro de Fusion: NO puede
   importar omnicad.
4. Buscá con grep todos los usos de las dos variables, también en tests y docs.
5. Actualizá docs/agentes/conectar.md: OMNICAD_PUENTE_DIR es la que se usa; la otra queda solo por compatibilidad.
6. Tests: solo la variable vieja, solo la nueva, las dos a la vez y ninguna.

TAREA 2: PLA-14
El menú de valores predefinidos ya ordena por creación y por nombre (clon/omnicad/ui/preajustes_ui.py). Faltan dos cosas.
1. Recordar el orden elegido entre diálogos, por comando. Se guarda en nucleo/preajustes.py. Hoy `self.orden` vive solo
   en el panel y vuelve a "creacion" al reabrir.
2. Ordenar también por última modificación y por último uso. Mirá primero cómo lo hace Fusion:
   clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar presets -s fusion-model
3. Un archivo de preajustes viejo, sin esos datos, tiene que abrir igual y sin error.
4. La herramienta `manage_command_presets` (clon/omnicad/api/herramientas_preajustes.py) tiene `sort_by`: sumale las
   opciones nuevas y documentalas en su docstring.
5. NO regeneres docs/agentes/herramientas.md: lo hace el coordinador. test_doc_agentes.py puede fallar por eso.
6. nucleo/ no importa Qt.
7. Tests: el orden se recuerda al reabrir, los dos órdenes nuevos dan la secuencia correcta, y un archivo viejo abre.
   La prueba del menú va con clic simulado sobre sus acciones, como la de tests/test_sol27_preajustes.py.

VERIFICACIÓN (desde clon/, tarea por tarea)
- .venv/Scripts/python.exe -m ruff check .
- .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe -m pytest tests/<archivo>.py -q -W error
- Corré tests/test_sol27_preajustes.py y los tests donde aparezcan las variables del puente.

REGLAS
- SÍ: el cambio más chico que resuelve la tarea completa, en español, con su test.
- NO: commit, push, instalar paquetes ni gastar en APIs.
- NO: tocar docs/seguimiento/ ni PROJECT_LOG.md. Eso lo hace el coordinador al revisar.
- NO: correr la suite completa, la prueba de humo ni cazar.py.
- NO: abrir ni tocar una app de OmniCAD abierta. No abrir Fusion.
- NO: leer privado/, analisis/, archivos .env ni nada fuera del repo, salvo los SKILL.md nombrados arriba.
- NO: convertir finales de línea. Si un archivo es CRLF, sigue CRLF.
- Si una tarea no sale después de dos intentos, dejala, decí por qué y pasá a la siguiente.

INFORME FINAL
Para cada ID: resuelto o no, archivos tocados, tests agregados y salida real de pytest. Después ruff y la salida completa
de ponytail-review.
```
