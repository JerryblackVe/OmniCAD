# -*- coding: utf-8 -*-
"""Inventario estático reproducible de los imports geométricos y sus consumidores.

La correspondencia describe la API Rust disponible, no afirma paridad de resultados.
Ejecutar desde el repo: clon/.venv/Scripts/python.exe scripts/inventario_motor.py.
"""
import ast
import json
import os
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]

# API del kernel revisada en crates/kernel/src; son correspondencias estáticas,
# no sustituciones de clases de OCP ni garantías de paridad.
COBERTURA = {
    "BOPAlgo": "boolean::boolean / cbool::boolean / split::make_volume",
    "BRep": "topo::Model / topo::BodySpec / query::subshapes",
    "BRepAdaptor": "Model::{curves,surfaces} / query::{face_signature,edge_signature}",
    "BRepAlgoAPI": "cbool::boolean / split::{section,split_by_plane,split_face}",
    "BRepBndLib": "query::body_bbox",
    "BRepBuilderAPI": "Model::build_validated / transform::transformed / sew::sew / sketch::region_sheet",
    "BRepCheck": "Model::check / check::check",
    "BRepClass": "sketch::regions / query::Classifier",
    "BRepClass3d": "query::Classifier::{new,classify}",
    "BRepExtrema": "query::BodyIndex::distance / project::project_point",
    "BRepFill": "patch::patch / loft::loft",
    "BRepFilletAPI": "blend::{fillet,chamfer} / roll::blend",
    "BRepGProp": "mass::{mass_properties,face_area_centroid} / query::edge_signature",
    "BRepIntCurveSurface": "query::BodyIndex::ray",
    "BRepLProp": "query::{surface_curvature,curve_curvature} / Surface::normal",
    "BRepLib": "Model::build_validated / check::repair",
    "BRepMesh": "render::render_mesh / mesh::tessellate",
    "BRepOffset": "rebuild::{offset_faces,shell} / offset2d::offset_region",
    "BRepOffsetAPI": "rebuild::{offset_faces,shell,draft} / loft::{loft,sweep_along} / offset2d::offset_region",
    "BRepPrimAPI": "primitives::{block,cylinder,cone,sphere,torus} / sweep::{extrude_region,revolve_region}",
    "BRepTools": "query::{subshapes,face_uv_box} / io::{export,import}",
    "Bnd": "query::body_bbox / bounds::BBox",
    "ChFiDS": "roll::Section",
    "ElCLib": "Curve::{eval,project} / query::edge_signature",
    "Font": "font::{text_curves,text_regions}",
    "GC": "curves::{Line,Circle,Ellipse} / sketch::SketchCurve::arc",
    "GCPnts": "render::render_mesh / query::edge_signature / Curve::eval",
    "GProp": "mass::{mass_properties,face_area_centroid}",
    "Geom": "curves / surfaces / nurbs / sweep::{Extrusion,Revolution}",
    "Geom2d": "sketch::SketchCurve / topo::CoedgeSpec",
    "Geom2dAPI": "sketch::regions / interp::interpolate",
    "GeomAPI": "interp::interpolate / project::project_point",
    "GeomAbs": "query::{SurfaceKind,CurveKind} / roll::Section",
    "GeomLib": "interp::interpolate",
    "HLRAlgo": "draw::hidden_lines",
    "HLRBRep": "draw::hidden_lines",
    "IFSelect": "error::OpResult",
    "IGESControl": "iges::{import,export}",
    "IntCurvesFace": "query::BodyIndex::ray",
    "IntTools": "sketch::regions / query::Classifier",
    "Interface": "step::{import,export} / iges::{import,export}",
    "Message": "error::OpError (sin impresores globales)",
    "NCollection": "Vec / Model / Handle",
    "OCP.collections": "Vec / Model / Handle",
    "STEPControl": "step::{import,export}",
    "ShapeAnalysis": "query::{subshapes,edge_signature} / check::check",
    "ShapeFix": "check::repair",
    "ShapeUpgrade": "sew::sew / cbool::boolean (unificación según el dominio)",
    "StdPrs": "font::{text_curves,text_regions}",
    "TopAbs": "topo::{BodyKind,CheckLevel} / query::{Side,subshapes}",
    "TopExp": "query::subshapes",
    "TopLoc": "transform::transformed / geom::Transform3",
    "TopTools": "Vec / Model / io::{export,import}",
    "TopoDS": "topo::{Model,Body,Face,Edge,Vertex} / query::subshapes",
    "collections": "Vec / Model / Handle",
    "gp": "geom::{Point3,Vector3,Dir3,Frame,Transform3}",
}

CASOS_FALTANTES = {
    "acis": ("Lector completo ACIS/SAB de .f3d", "SAB de una caja de 1×2×3 cm, con body/lump/shell/face/loop/coedge/edge/vertex",
             "un sólido válido en mm: V=6000 mm³, A=2200 mm², caja 10×20×30, 6 caras y 12 aristas"),
    "BRepFeat": ("Edición directa/proyección y división de silueta", "cilindro R=10 mm, alto=20 mm, división por silueta mirando desde +X",
                 "mismo volumen y área, cara lateral partida por las dos generatrices; referencias equivalentes a OpenCascade"),
    "Law": ("Ley general de radio de empalme", "caja 30×30×30 mm, una arista, radios [(0,1),(0.5,3),(1,1)] mm",
            "empalme válido con radio variable según la ley; V/A, topología y referencias iguales a OpenCascade"),
    "xcaf": ("Árbol STEP con nombres, colores y componentes", "STEP de dos cajas 10×20×30 mm en componentes A/B, colores rojo/azul, B trasladado 40 mm en X",
             "dos componentes y dos cuerpos con sus nombres, colores y ubicaciones; V=6000 mm³ por cuerpo"),
}


def correspondencia(fila):
    modulo = fila["modulo"].removeprefix("OCP.")
    if fila["archivo"].endswith("/acis_occ.py"):
        return "acis", "FALTA EN OMNIKERNEL: lector completo ACIS/SAB (reader solo cubre bulk exact_spl_sur)"
    if modulo in {"STEPCAFControl", "XCAFDoc", "Quantity", "TCollection", "TDataStd", "TDF", "TDocStd"}:
        return "xcaf", "FALTA EN OMNIKERNEL: árbol STEP con nombres, colores y componentes"
    if modulo in CASOS_FALTANTES:
        return modulo, "FALTA EN OMNIKERNEL: " + CASOS_FALTANTES[modulo][0]
    return None, COBERTURA.get(modulo, "FALTA EN OMNIKERNEL: " + modulo)


def guardar(filas):
    ruta = RAIZ / "docs" / "inventario_motor.md"
    encabezado = ruta.read_text(encoding="utf-8").split("## Estado del paso 2")[0]
    encabezado = encabezado.replace("# Inventario de motores — revisión interrumpida", "# Inventario de motores")
    lineas = [encabezado.rstrip(), "", "## Estado del paso 2", "",
              f"Inventario AST: **{len(filas)} imports en {len({f['archivo'] for f in filas})} archivos**. Cada import",
              "tiene una fila; los usos indican funciones consumidoras y sus líneas. Snapshot previo al refactor.",
              "La cobertura es estática: ninguna fila equivale a una función conectada o a paridad verde.",
              "Regeneración: `clon/.venv/Scripts/python.exe scripts/inventario_motor.py --guardar`.", "",
              "FK-001 resuelto: `iges::export` existe. FK-002 retirado por corrección del encargo; `.3dm` fuera de alcance.", "",
              "| ID | Archivo:línea | Qué hace (símbolos y consumidores) | API OmniKernel / faltante |",
              "|---|---|---|---|"]
    faltantes = {}
    for i, fila in enumerate(filas, 1):
        clave, cobertura = correspondencia(fila)
        ubicacion = f"{fila['archivo']}:{fila['linea']}"
        usos = "; ".join(f"{n}: {','.join(map(str, ls))}" for n, ls in fila["usos"].items()) or "sin referencia nominal"
        descripcion = f"`{fila['modulo']}`: {', '.join(fila['simbolos'])}. {usos}"
        lineas.append(f"| IM-{i:03d} | `{ubicacion}` | {descripcion} | {cobertura} |")
        if clave:
            faltantes.setdefault(clave, []).append(f"IM-{i:03d}: {ubicacion}")
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")
    destino = Path(os.environ.get("OMNIKERNEL_DIR") or sys.exit("Definí OMNIKERNEL_DIR con la carpeta del repo del kernel.")) / "docs" / "faltantes_omnicad.md"
    anterior = destino.read_text(encoding="utf-8").split("## Inventario estático de la app")[0]
    bloques = [anterior.rstrip(), "", "## Inventario estático de la app", "",
               "Correspondencias sin API equivalente identificada; se documentan y no frenan la integración.", ""]
    for clave, referencias in faltantes.items():
        titulo, entrada, salida = CASOS_FALTANTES[clave]
        bloques += [f"### IM-{clave} — {titulo}", "", "- Estado: FALTA EN OMNIKERNEL.",
                    "- Filas del inventario: " + "; ".join(referencias),
                    "- Entrada mínima: " + entrada + ".", "- Salida esperada: " + salida + ".",
                    "- Reproducción/paridad: pendiente; la fachada debe informar MOTOR_SIN_SOPORTE.", ""]
    destino.write_text("\n".join(bloques), encoding="utf-8", newline="\n")
    assert sum(1 for l in lineas if l.startswith("| IM-")) == len(filas)


def inventariar(raiz):
    filas = []
    for ruta in sorted(raiz.rglob("*.py")):
        texto = ruta.read_text(encoding="utf-8-sig")
        arbol = ast.parse(texto)
        padres = {h: p for p in ast.walk(arbol) for h in ast.iter_child_nodes(p)}
        for nodo in ast.walk(arbol):
            modulo = nodo.module if isinstance(nodo, ast.ImportFrom) else ""
            if isinstance(nodo, ast.Import):
                nombres = [a.name for a in nodo.names if a.name == "OCP" or a.name.startswith("OCP.")]
                modulo = ", ".join(nombres)
            if not modulo or not (modulo == "OCP" or modulo.startswith("OCP.")):
                continue
            simbolos = {a.asname or a.name.split(".")[0] for a in nodo.names}
            usos = {}
            for uso in ast.walk(arbol):
                if not isinstance(uso, ast.Name) or not isinstance(uso.ctx, ast.Load) or uso.id not in simbolos:
                    continue
                padre = padres.get(uso)
                while padre is not None and not isinstance(padre, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    padre = padres.get(padre)
                clave = padre.name if padre is not None else "módulo"
                usos.setdefault(clave, set()).add(uso.lineno)
            filas.append({"archivo": ruta.relative_to(RAIZ).as_posix(), "linea": nodo.lineno,
                          "modulo": modulo, "simbolos": sorted(simbolos),
                          "usos": {k: sorted(v) for k, v in sorted(usos.items())}})
    return sorted(filas, key=lambda f: (f["archivo"], f["linea"]))


def comprobar():
    """Autochequeo del recorrido: imports multilínea, locales, alias y módulos."""
    import tempfile
    with tempfile.TemporaryDirectory(dir=RAIZ) as temporal:
        carpeta = Path(temporal)
        (carpeta / "caso.py").write_text(
            "from OCP.gp import (gp_Pnt as Punto, gp_Vec)\n"
            "def usar():\n    from OCP.BRep import BRep_Tool\n    return Punto(), BRep_Tool\n"
            "import OCP.TopoDS as topo\n", encoding="utf-8")
        filas = inventariar(carpeta)
        assert len(filas) == 3
        assert filas[0]["usos"] == {"usar": [4]}
        assert filas[1]["usos"] == {"usar": [4]}
        assert filas[2]["simbolos"] == ["topo"]


if __name__ == "__main__":
    import sys
    comprobar()
    filas = inventariar(RAIZ / "clon" / "omnicad")
    if "--guardar" in sys.argv:
        guardar(filas)
    print(json.dumps({"imports": len(filas), "archivos": len({f["archivo"] for f in filas}),
                      "modulos": sorted({f["modulo"] for f in filas}),
                      "filas": filas if "--detalle" in sys.argv else []},
                     ensure_ascii=False, indent=2))
