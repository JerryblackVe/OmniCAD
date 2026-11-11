# -*- coding: utf-8 -*-
"""B-170: la previa de Solevación con línea central cerraba la app dentro de `BRepOffsetAPI_MakePipeShell`.

Las secciones y líneas centrales que el cazador elige en su escena (rectángulo, línea, caras y aristas de una caja)
dan un sólido o un error claro; ninguna tumba el proceso. La sonda de 147 combinaciones (2026-11-11) no cayó."""
import pytest
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt

from omnicad.nucleo import geometria as geo, solidos_crear as sc


def _rectangulo():
    p = BRepBuilderAPI_MakePolygon()
    for q in ((0, 0, 0), (20, 0, 0), (20, 10, 0), (0, 10, 0)):
        p.Add(gp_Pnt(*q))
    p.Close()
    return p.Wire()


def _formas():
    rect = _rectangulo()
    caja = BRepPrimAPI_MakeBox(gp_Pnt(-115, -15, 0), 30, 30, 20).Shape()
    return {"rect_cara": BRepBuilderAPI_MakeFace(rect, True).Face(), "rect": rect,
            "linea": BRepBuilderAPI_MakeEdge(gp_Pnt(0, -30, 0), gp_Pnt(20, -30, 0)).Edge(),
            "cara_caja": geo.caras(caja)[4], "arista_caja": geo._aristas_unicas(caja)[5]}


@pytest.mark.parametrize("a, b, central", [("rect_cara", "cara_caja", "linea"), ("rect", "arista_caja", "linea"),
                                           ("rect_cara", "rect", "arista_caja"), ("linea", "cara_caja", "linea")])
def test_solevar_con_linea_central_da_solido_o_error_claro(a, b, central):
    f = _formas()
    try:
        forma = sc.solevar([f[a], f[b]], linea_central=f[central])
    except geo.ErrorGeometria:
        return
    assert not forma.IsNull()
