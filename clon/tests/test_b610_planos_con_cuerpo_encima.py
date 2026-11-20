"""B-610: con un cuerpo encima del origen, un campo que pide un plano muestra y deja elegir los planos de origen."""
import os

import pytest

from omnicad.nucleo import geometria as g


@pytest.fixture(scope="module")
def visor():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from omnicad.timeline.operaciones import EstadoModelo
    from omnicad.ui.visor3d import Visor3D
    QApplication.instance() or QApplication([])
    estado = EstadoModelo()
    estado.nuevo_cuerpo("op1", g.caja(40, 40, 40, origen=(-20, -20, -20)))   # tapa el origen
    v = Visor3D()
    v.resize(800, 600)
    v.set_modelo(estado)
    v.vista("iso")
    v.set_ortografica(True)
    v.ventana_libre = False          # hay un comando abierto
    yield v
    v.set_filtro(None)
    v.close()


def test_planos_cubren_la_caja_solo_al_pedir_un_plano(visor):
    chico = {r: rect for r, _p, rect in visor.planos_elegibles()}
    visor.modo = "elegir_plano"         # B-626: crecen solo al pedir un plano de boceto, no en cualquier comando
    visor.set_filtro({"plano"})
    grande = {r: rect for r, _p, rect in visor.planos_elegibles()}
    assert visor.eligiendo_planos()
    for r in ("XY", "XZ", "YZ"):
        assert grande[r][2] == grande[r][3] == pytest.approx(16.0)    # B-762: chicos, un 40 % de la pieza, pegados al origen
        assert chico[r][0] == 0.0       # sin pedir un plano, el tamaño de siempre
    visor.set_filtro(None)
    visor.modo = None
    assert {r: rect for r, _p, rect in visor.planos_elegibles()} == chico


def test_clic_sobre_el_plano_elige_el_plano_aunque_haya_cuerpo_detras(visor):   # B-762
    visor.modo = "elegir_plano"
    visor.set_filtro({"plano"})
    try:
        visor.vista("arriba")
        hit = visor.elegir_entidad(visor.proyectar((8, 8, 0)), {"plano"})   # dentro del plano chico, sobre el cuerpo
        assert hit is not None and hit["ref"] == {"tipo": "plano", "id": "XY"}
    finally:
        visor.set_filtro(None)
        visor.modo = None


def test_b626_tamano_del_plano_no_depende_del_zoom(visor):
    """B-626: los planos al pedir un plano miden ~0,4× la pieza aunque la cámara esté lejos (como Fusion)."""
    visor.modo = "elegir_plano"
    visor.set_filtro({"plano"})
    try:
        cerca = {r: rect for r, _p, rect in visor.planos_elegibles()}
        d0 = visor.distancia
        visor.distancia = d0 * 4
        lejos = {r: rect for r, _p, rect in visor.planos_elegibles()}
        visor.distancia = d0
        assert lejos == cerca
        for r in ("XY", "XZ", "YZ"):
            u0, v0, u1, v1 = cerca[r]
            assert max(u1 - u0, v1 - v0) <= 0.5 * 40      # la pieza mide 40 mm
    finally:
        visor.set_filtro(None)
        visor.modo = None
