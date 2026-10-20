# -*- coding: utf-8 -*-
"""B-74: el detalle del render CPU sigue los píxeles, sin perder calidad de cerca."""
import math
import time
from io import BytesIO
from types import SimpleNamespace

import numpy as np
import pytest
from OCP.BRep import BRep_Tool
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Ax2, gp_Dir, gp_Elips, gp_Pnt
from PIL import Image

from omnicad.api import herramientas_inspeccion as hi
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import render_cpu as rc
from omnicad.nucleo import solidos_crear as sc
from omnicad.timeline.operaciones import EstadoModelo


def _alabe():
    """Perfil elíptico: radio de curvatura mínimo b²/a = 0,2 mm."""
    secciones = []
    for z, giro, x in ((0, 0, 0), (12, 3, 1), (25, 7, 3), (38, 11, 5), (50, 14, 6)):
        a = math.radians(giro)
        eje = gp_Ax2(gp_Pnt(x, 0, z), gp_Dir(0, 0, 1), gp_Dir(math.cos(a), math.sin(a), 0))
        secciones.append(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(gp_Elips(eje, 10, math.sqrt(2))).Edge()).Wire())
    forma = sc.solevar(secciones)
    assert geo.es_valida(forma)
    return forma


def _sesion(cantidad):
    forma = _alabe()
    estado = EstadoModelo()
    for i in range(cantidad):
        copia = BRepBuilderAPI_Copy(forma, False, False).Shape()
        copia = geo.trasladar(copia, ((i % 10) * 40, (i // 10) * 40, 0))
        estado.nuevo_cuerpo("alabes", copia)
    doc = SimpleNamespace(estado_final=estado, propiedades={}, propiedad=lambda *args: 1.0)
    return SimpleNamespace(doc=doc)


def test_escena_de_80_alabes():
    sesion = _sesion(80)
    inicio = time.perf_counter()
    resultado = hi.get_viewport_image(sesion, width=800, height=600)
    segundos = time.perf_counter() - inicio
    print(f"80 álabes a 800×600: {segundos:.3f} s")
    assert resultado["image"].ancho == 800 and resultado["image"].alto == 600
    # Antes de B-74: 17,867 s; 5,95 s exige 3× y deja margen sobre los 2,735 s medidos.
    assert segundos < 5.95


def test_pieza_cerca_cambia_menos_del_uno_por_ciento(monkeypatch):
    sesion = _sesion(1)
    objetos_render = hi._objetos_render
    with monkeypatch.context() as m:
        m.setattr(hi, "_objetos_render", lambda s, cuerpos, cam, alto, cajas: objetos_render(s, cuerpos))
        antes = hi.get_viewport_image(sesion, width=400, height=300)["image"]
    despues = hi.get_viewport_image(sesion, width=400, height=300)["image"]
    a, b = (np.array(Image.open(BytesIO(imagen.png))) for imagen in (antes, despues))
    distintos = np.any(a != b, axis=2).mean()
    print(f"Píxeles distintos de cerca: {distintos:.3%}")
    assert a.std() > 5
    assert distintos <= 0.01


@pytest.mark.parametrize("ortografica", [False, True])
def test_deflexion_depende_de_pixeles_y_conserva_el_primer_plano(ortografica):
    forma = _alabe()
    fina = rc.deflexion_para(forma)
    cerca = rc.camara(np.identity(3), (0, 0, 25), 100, ortografica=ortografica)
    lejos = dict(cerca, distancia=2000)
    gruesa = rc.deflexion_para(forma, cam=lejos, alto=600)
    assert rc.deflexion_para(forma, cam=cerca, alto=600) == fina
    assert gruesa > fina
    assert rc.deflexion_para(forma, cam=lejos, alto=4800) < gruesa
    assert rc.deflexion_para(forma, 0.03, cam=lejos) == 0.03
    assert rc.deflexion_para(forma, cam=dict(cerca, distancia=1)) == fina


def test_malla_cpu_independiente_respeta_caras_y_no_altera_la_del_visor():
    forma = _alabe()
    fina, _ = rc.malla_suave(forma, rc.deflexion_para(forma))
    cara = geo.caras(forma)[0]
    tri = BRep_Tool.Triangulation_s(cara, TopLoc_Location())
    cantidad = tri.NbTriangles()
    v, n, partes = rc.malla_suave_aparte(forma, [cara], 0.25, 0.5, independiente=True)
    cv, cn = partes[0]
    assert len(cv) > 0 and len(cv) == len(cn) and len(v) == len(n)
    assert len(v) + len(cv) < len(fina) / 3
    assert BRep_Tool.Triangulation_s(cara, TopLoc_Location()).NbTriangles() == cantidad
    assert np.array_equal(rc.malla_suave(forma, rc.deflexion_para(forma))[0], fina)


def test_malla_independiente_ignora_caras_ajenas():
    forma = geo.caja(10, 10, 10)
    ajena = geo.caras(geo.caja(5, 5, 5))[0]
    v, n, partes = rc.malla_suave_aparte(forma, [ajena], independiente=True)
    assert v.shape == n.shape == (36, 3)
    assert partes[0][0].shape == partes[0][1].shape == (0, 3)


def test_malla_independiente_conserva_caras_sin_superficie():
    from OCP.BRep import BRep_Builder
    from OCP.Poly import Poly_Triangle, Poly_Triangulation
    from OCP.TopoDS import TopoDS_Face

    tri = Poly_Triangulation(3, 1, False)
    for i, p in enumerate(((0, 0, 0), (10, 0, 0), (0, 10, 0)), 1):
        tri.SetNode(i, gp_Pnt(*p))
    tri.SetTriangle(1, Poly_Triangle(1, 2, 3))
    cara = TopoDS_Face()
    BRep_Builder().MakeFace(cara, tri)
    v, n, _ = rc.malla_suave_aparte(cara, [], independiente=True)
    assert v.shape == n.shape == (3, 3)
    assert np.allclose(n, (0, 0, 1))
