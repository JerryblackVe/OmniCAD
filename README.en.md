# OmniCAD

**Free and open parametric 3D CAD, written in Python.** You design with a history of steps (timeline) that recomputes
itself when you change a dimension, like professional CAD tools. And **AI agents** (Claude Code, OpenCode, Cursor,
Codex…) can drive it through MCP or the command line.

[Versión en español](README.md) · License [GPL-3.0](LICENSE) · Status: **alpha** (tested on Windows; Linux pending)

![OmniCAD](docs/img/omnicad.png)

> The program and most of the documentation are in **Spanish** today. Full English support (UI, messages, tools and
> docs) is on the roadmap. Contributions in English are welcome.

## Features

- **Parametric design:** parameters with units and expressions (`ancho / 2 + 3 mm`), editable timeline, undo/redo.
- **Constrained 2D sketches:** lines, arcs, circles, polygons, splines, dimensions and a constraint solver.
- **Solids:** extrude, revolve, sweep, loft, primitives, fillet, chamfer, shell, draft, holes, threads, ribs, patterns,
  mirror, booleans, split, scale, move and more.
- **Surfaces, sheet metal and meshes:** patch, trim, stitch, thicken; flanges, bends and flat pattern; repair, remesh,
  reduce and smooth meshes.
- **Basic assemblies:** components, joints, rigid groups and fasteners.
- **Files:** open `.omnicad` project format (ZIP with a JSON recipe); exports STL, OBJ, 3MF, PLY, STEP, IGES and BREP;
  imports STEP; sketches from DXF and SVG.
- **Inspection:** volume, mass, area, bounding box, distances, angles and interference.
- **Geometry kernel:** [OpenCascade](https://dev.opencascade.org/) (B-rep).

## For AI agents

OmniCAD ships an **MCP server** and a **CLI** (`omnicad`) generated from a single tool catalog, so both always match.
An agent can create parts, measure them, look at a rendered image and export them; it can also work **live** on the
open window.

```
omnicad setup --cliente todos            # shows what it would configure in Claude Code and OpenCode
omnicad setup --cliente todos --aplicar  # does it (backing up each file as .bak)
```

Tool names and parameters are in English (`create_box`, `fillet`, `radius`); descriptions and messages are in Spanish
for now. Docs: [docs/agentes/](docs/agentes/README.md).

## Install (Windows)

You need [Python 3.12](https://www.python.org/downloads/) and Git.

```
git clone https://github.com/JerryblackVe/OmniCAD.git
cd OmniCAD/clon
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe OmniCAD.py --ejemplo
```

**Linux:** all dependencies exist for Linux, but it has not been tested yet. It is on the roadmap.

## Contributing

The goal is to grow the project collaboratively. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and
[AGENTS.md](AGENTS.md) (architecture, rules and recipes, for humans and AI coding agents alike).

## Roadmap

Linux support · Spanish and English everywhere · two-way Blender integration · better rendering (materials, colors,
lighting) · vectors, SVG, text and vectorizing · assemblies, animation, simulations · Rhino-style tools and
Grasshopper-style visual programming.

## Disclaimer

OmniCAD is an independent project. It takes the **workflow** of tools like Fusion 360, Blender and Rhino as a reference,
but **contains no code, text or assets** from them, and is not affiliated with or endorsed by Autodesk, the Blender
Foundation or Robert McNeel & Associates. Fusion 360 is a trademark of Autodesk, Inc.; Rhinoceros and Grasshopper are
trademarks of Robert McNeel & Associates.

## License

[GNU GPL v3.0 or later](LICENSE).
