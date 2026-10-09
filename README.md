# OmniCAD

**CAD 3D paramétrico, libre y abierto, hecho en Python.** Diseñás con un historial de pasos (timeline) que se recalcula
solo cuando cambiás una medida, como en los CAD profesionales. Y además lo pueden manejar **agentes de IA** (Claude Code,
OpenCode, Cursor, Codex…) por MCP o por línea de comandos.

<div align="center">

## ☕ Si OmniCAD te sirve, apoyalo

**OmniCAD es libre y gratis.** Lo hace una sola persona, en su tiempo.<br>
Si te ayuda, una donación me ayuda a seguir.

<a href="https://ko-fi.com/jerryblackve"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Apoyame en Ko-fi"></a>

</div>

[English version](README.en.md) · Licencia [GPL-3.0](LICENSE) · Estado: **alfa** (Windows probado; Linux pendiente)

![OmniCAD](docs/img/omnicad.png)

## Qué tiene

- **Diseño paramétrico:** parámetros con unidades y expresiones (`ancho / 2 + 3 mm`), timeline editable, deshacer y rehacer.
- **Bocetos 2D con restricciones:** líneas, arcos, círculos, polígonos, splines, cotas y un solver de restricciones.
- **Sólidos:** extrusión, revolución, barrido, solevación, primitivas, empalme, chaflán, vaciado, desmoldeo, agujeros,
  roscas, nervios, patrones, simetría, booleanas, dividir, escalar, mover y más.
- **Superficies, chapa metálica y mallas:** parches, recortar, coser, engrosar; pestañas, pliegues y desplegado;
  reparar, remallar, reducir y suavizar mallas.
- **Ensamblaje básico:** componentes, uniones, grupos rígidos y fijaciones (tornillería).
- **Archivos:** proyecto `.omnicad` abierto (ZIP con receta JSON); exporta STL, OBJ, 3MF, PLY, STEP, IGES y BREP;
  importa STEP; bocetos desde DXF y SVG.
- **Inspección:** volumen, masa, área, caja envolvente, distancias, ángulos e interferencias.
- **Interfaz:** 5 temas (oscuro moderno, claro moderno, azul profesional, minimalista y clásico) y temas propios del
  usuario en un archivo JSON; caja de herramientas con la tecla S (buscar y fijar comandos).
- **Kernel geométrico:** [OpenCascade](https://dev.opencascade.org/) (B-rep), el mismo tipo de núcleo que usan los CAD comerciales.

## Para agentes de IA

OmniCAD trae un **servidor MCP** y una **CLI** (`omnicad`) que salen de un único catálogo de herramientas: lo que hace
uno lo hace el otro. Un agente puede crear piezas, medirlas, mirar una imagen del resultado y exportarlas; también puede
trabajar **en vivo** sobre la ventana abierta.

```
omnicad setup --cliente todos            # muestra qué configuraría en Claude Code y OpenCode
omnicad setup --cliente todos --aplicar  # lo hace (con copia .bak de cada archivo)
```

Todo está en [docs/agentes/](docs/agentes/README.md): cómo conectar cada cliente, la CLI, el modo en vivo y la lista
completa de herramientas.

## Instalación (Windows)

Necesitás [Python 3.12](https://www.python.org/downloads/) y Git.

```
git clone https://github.com/JerryblackVe/OmniCAD.git
cd OmniCAD/clon
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe OmniCAD.py --ejemplo
```

- `OmniCAD.py` abre la app vacía; `OmniCAD.py pieza.omnicad` abre un proyecto.
- Después de `pip install -e .` quedan los comandos `omnicad` (CLI) y `omnicad-mcp` (servidor MCP).
- **Linux:** las dependencias existen para Linux, pero todavía no se probó. Es uno de los pendientes.

## Contribuir

El proyecto busca crecer de forma colaborativa. Empezá por [CONTRIBUTING.md](CONTRIBUTING.md).

- Para programar (personas o agentes de IA): [AGENTS.md](AGENTS.md) explica la arquitectura, las reglas y las recetas para
  agregar operaciones, comandos y herramientas.
- Arquitectura: [docs/arquitectura.md](docs/arquitectura.md). Bitácora y pendientes: [PROJECT_LOG.md](PROJECT_LOG.md).
- Errores e ideas: [Issues](https://github.com/JerryblackVe/OmniCAD/issues).

## Hoja de ruta

- Instalador fácil para Windows y Linux, para cualquiera (sepa programar o no).
- Funcionar en Linux sin problemas.
- Español e inglés en todo: interfaz, mensajes, herramientas y documentación.
- Integración con Blender en los dos sentidos.
- Mejor render: materiales, colores e iluminación.
- Vectores, SVG, texto y vectorizado.
- Ensamblajes, animación, simulaciones y movimiento de piezas.
- Funciones al estilo Rhino y programación visual al estilo Grasshopper.

Detalle en [PROJECT_LOG.md](PROJECT_LOG.md#pendientes).

## Aviso

OmniCAD es un proyecto independiente. Toma como referencia el **flujo de trabajo** de programas como Fusion 360, Blender
y Rhino, pero **no contiene código, textos ni recursos** de ellos. No está afiliado ni respaldado por Autodesk, la Blender
Foundation ni Robert McNeel & Associates. Fusion 360 es marca de Autodesk, Inc.; Rhinoceros y Grasshopper son marcas de
Robert McNeel & Associates.

## Licencia

[GNU GPL v3.0 o posterior](LICENSE). Podés usarlo, estudiarlo, modificarlo y compartirlo; si distribuís una versión
modificada, tiene que seguir siendo libre con la misma licencia.

## Apoyar el proyecto

OmniCAD es libre y gratis, y lo hace una sola persona. Si te sirve, podés apoyarlo con una donación en
[ko-fi.com/jerryblackve](https://ko-fi.com/jerryblackve). ¡Gracias!
