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


def test_el_paso_que_se_borra_o_suprime_no_cuenta():
    """Borrar la última extrusión de 145 s no recalcula nada: no se manda a un proceso aparte frío que la rehace entera."""
    d = _doc()
    d._duraciones = [0.0, 0.0, 145.0]
    assert d._prevuelo_corresponde(desde=2)
    assert not d._prevuelo_corresponde(desde=2, quitados={2})
    assert d._prevuelo_corresponde(desde=1, quitados={1})            # el caro (2) sigue en pie: se recalcula


def _espiar_aparte(monkeypatch, d):
    pedidos = []
    monkeypatch.setattr(d, "_solicitar_calculo", lambda tarea, datos: pedidos.append(tarea))
    return pedidos


def test_eliminar_el_ultimo_paso_caro_se_calcula_aca_y_alinea_las_duraciones(monkeypatch):
    d = _doc(4)
    d._duraciones = [0.0, 0.1, 0.2, 145.0]
    pedidos = _espiar_aparte(monkeypatch, d)
    d.eliminar_varios([d.operaciones[3].id])
    assert not pedidos and len(d.operaciones) == 3 and d._duraciones == [0.0, 0.1, 0.2]
    # un cuerpo ya modificado por un paso anterior se recalcula igual que de cero
    d.eliminar_varios([d.operaciones[1].id])
    assert not pedidos and len(d._duraciones) == len(d.operaciones) == 2
    assert [c.forma.ShapeType() for c in d.estado_en(1).cuerpos.values()]


def test_eliminar_un_paso_del_medio_con_otro_caro_despues_si_va_al_proceso_aparte(monkeypatch):
    d = _doc(4)
    d._duraciones = [0.0, 0.1, 0.2, 145.0]
    pedidos = _espiar_aparte(monkeypatch, d)
    d.eliminar_varios([d.operaciones[1].id])
    assert pedidos == ["prevuelo_cambio"] and len(d._duraciones) == len(d.operaciones) == 3


def test_suprimir_el_paso_caro_no_va_al_proceso_aparte(monkeypatch):
    d = _doc(4)
    d._duraciones = [0.0, 0.1, 0.2, 145.0]
    pedidos = _espiar_aparte(monkeypatch, d)
    d.suprimir(d.operaciones[3].id, True)
    assert not pedidos
    # reactivarlo vuelve a costar; mientras está suprimido, no cuenta para editar uno anterior
    assert not d._prevuelo_corresponde(desde=1)
    d._duraciones[3] = 145.0
    assert d._prevuelo_corresponde(desde=3)
