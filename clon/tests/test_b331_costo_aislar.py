"""B-331: un documento de pocos pasos pero lento de recalcular también se calcula en el proceso aparte (la ventana sigue
repintando); uno rápido sigue en el hilo (sin el costo de mandarlo)."""
from omnicad.nucleo import aislado
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva


def _doc(n=3):
    d = Documento()
    for _ in range(n):
        d.agregar(OpPrimitiva(d.nuevo_id(), forma="caja", ancho="40", largo="30", alto="20"))
    return d


def test_documento_chico_y_rapido_sigue_en_el_hilo():
    d = _doc()
    assert len(d.operaciones) < aislado.UMBRAL_PREVUELO_PARAMETROS
    d._duraciones = [0.1, 0.1, 0.1]
    assert not d._prevuelo_corresponde()


def test_documento_chico_pero_lento_va_al_proceso_aparte():
    d = _doc()
    d._duraciones = [0.3, 0.3, 0.0]
    assert d._prevuelo_corresponde()


def test_solo_cuenta_lo_que_hay_que_recalcular_desde_el_cambio():
    d = _doc()
    d._duraciones = [4.0, 0.1, 0.1]            # el paso caro es el primero
    assert d._prevuelo_corresponde(desde=0)
    assert not d._prevuelo_corresponde(desde=1)  # editar el segundo no lo vuelve a calcular


def test_dentro_del_hijo_nunca(monkeypatch):
    d = _doc()
    d._duraciones = [4.0, 0.0, 0.0]
    monkeypatch.setattr(aislado, "EN_HIJO", True)
    assert not d._prevuelo_corresponde()


def test_con_proyecciones_de_boceto_el_costo_manda_al_proceso_aparte():
    """B-401: el proceso aparte también devuelve los atributos calculados de los bocetos."""
    from omnicad import api

    s = api.Sesion()
    api.llamar(s, "create_box", {"length": 20, "width": 20, "height": 20})
    api.llamar(s, "create_sketch", {"plane": "XZ", "name": "Costado"})
    assert api.llamar(s, "project_to_sketch", {"bodies": ["Cuerpo1"], "sketch": "Costado"})["ok"]
    s.doc._duraciones = [4.0] * len(s.doc.operaciones)
    assert s.doc._prevuelo_corresponde()
