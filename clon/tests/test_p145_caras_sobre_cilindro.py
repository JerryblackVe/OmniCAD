"""P-145: lo que quedó de la cara roscada (tramos de afuera y crestas), sin el escalón de otro Ø del mismo eje."""
from OCP.BRepAdaptor import BRepAdaptor_Surface

from omnicad.nucleo import geometria as geo, referencias as refs, solidos_crear as sc


def test_las_caras_que_quedan_de_la_cara_roscada():
    eje = geo.booleano(geo.cilindro(5, 30), geo.cilindro(8, 10, base=(0, 0, 30)), "unir")
    cara = next(c for c in refs.subformas(eje, "cara") if refs.firma_cara(c).get("geom") == "cilindro"
                and abs(BRepAdaptor_Surface(c).Cylinder().Radius() - 5) < 1e-9)
    roscado = sc.rosca(eje, cara, designacion="M10", longitud=10, desfase=5)
    caras = sc.caras_sobre_cilindro(roscado, cara)
    radios = [BRepAdaptor_Surface(c).Cylinder().Radius() for c in caras]
    assert len(caras) >= 4 and all(abs(r - 5) < 1e-6 for r in radios)    # 2 tramos de afuera y las crestas; no el de Ø16
    assert sum(geo.area(c) for c in caras) < geo.area(cara)                # el surco se llevó parte de la cara
