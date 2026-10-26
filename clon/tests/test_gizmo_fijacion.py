"""Insertar fijación: asas de lista de tamaño y largo (GZ-13). Se tira del disco y salta a la opción más cercana."""
from test_fijaciones import _hit_circulo, _placa
from test_manipuladores import _arrastrar, app_qt  # noqa: F401  (fixture)
from test_manipuladores import _panel

from omnicad.nucleo import fijaciones as fj
from omnicad.ui import manipuladores as mp
from omnicad.ui.comandos.fijacion import InsertarFijacion


def _abrir():
    doc = _placa((20, 20))
    valores = {"posiciones": [_hit_circulo(doc, (20, 20, 10))], "familia": "tornillo", "norma_tornillo": "ISO 4762"}
    p, visor, _ = _panel(InsertarFijacion(), doc, valores)
    p._calcular_previa()
    p.manipuladores.actualizar()
    return p, visor


def _asa(p, clave):
    return next(m for m in p.manipuladores.manips if isinstance(m, mp.AsaLista) and m.clave == clave)


def _tirar_a(p, asa, numero):
    g = p.manipuladores
    xy, ok = g.pantalla([asa._asa(), asa.origen + asa.direccion * numero * asa.factor])
    assert ok.all()
    _arrastrar(p.visor, *xy)


def test_hay_un_asa_para_el_tamano_y_otra_para_el_largo(app_qt):  # noqa: F811
    p, _ = _abrir()
    assert {m.clave for m in p.manipuladores.manips} == {"tamano", "largo"}
    assert _asa(p, "tamano").actual == fj.diametro_nominal("M6")                # el automático del agujero de Ø6.6
    p.cancelar()


def test_tirar_del_asa_del_largo_salta_al_siguiente_largo_de_la_norma(app_qt):  # noqa: F811
    p, _ = _abrir()
    asa = _asa(p, "largo")
    largos = fj.largos("ISO 4762", "M6")
    siguiente = largos[largos.index(asa.actual) + 2]
    _tirar_a(p, asa, siguiente)
    assert float(p.valores["largo"]) == siguiente
    p._calcular_previa()
    assert p._previa_ok
    assert _asa(p, "largo").actual == siguiente                              # el asa quedó en la opción nueva
    p.cancelar()


def test_tirar_del_asa_del_tamano_cambia_el_tamano_y_corrige_el_largo(app_qt):  # noqa: F811
    p, _ = _abrir()
    _tirar_a(p, _asa(p, "tamano"), fj.diametro_nominal("M10"))
    assert p.valores["tamano"] == "M10"
    p._calcular_previa()
    assert p._previa_ok and _asa(p, "tamano").actual == 10
    p.cancelar()


def test_el_asa_no_se_sale_de_la_lista(app_qt):  # noqa: F811
    p, _ = _abrir()
    _tirar_a(p, _asa(p, "largo"), 10000.0)
    assert float(p.valores["largo"]) == max(fj.largos("ISO 4762", "M6"))
    _tirar_a(p, _asa(p, "largo"), -50.0)
    assert float(p.valores["largo"]) == min(fj.largos("ISO 4762", "M6"))
    p.cancelar()


def test_una_tuerca_solo_tiene_el_asa_del_tamano_y_sin_posicion_no_hay_asas(app_qt):  # noqa: F811
    doc = _placa((20, 20))
    pos = [_hit_circulo(doc, (20, 20, 10))]
    p, _, _ = _panel(InsertarFijacion(), doc, {"posiciones": pos, "familia": "tuerca", "norma_tuerca": "ISO 4032"})
    p.manipuladores.actualizar()
    assert [m.clave for m in p.manipuladores.manips] == ["tamano"]
    p.cancelar()
    q, _, _ = _panel(InsertarFijacion(), doc, {})
    q.manipuladores.actualizar()
    assert q.manipuladores.manips == []
    q.cancelar()
