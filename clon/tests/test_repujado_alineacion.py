"""Alineación, sentido y cadena tangente del Repujado (Emboss de Fusion)."""
import copy
import math

import numpy as np
import pytest
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.gp import gp_Pnt

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc
from omnicad.nucleo import solidos_modificar as sm


def _rectangulo():
    contorno = BRepBuilderAPI_MakePolygon()
    for p in [(10, 8, 15), (18, 8, 15), (18, 12, 15), (10, 12, 15)]:
        contorno.Add(gp_Pnt(*p))
    contorno.Close()
    return BRepBuilderAPI_MakeFace(contorno.Wire()).Face()


def _tapa(cuerpo):
    return next(c for c in geo.caras(cuerpo)
                if (pl := geo.plano_de_cara(c)) is not None and pl.normal[2] > 0.9)


def _material_nuevo(cuerpo, resultado):
    assert geo.es_valida(resultado)
    nuevo = geo.booleano(resultado, cuerpo, "cortar")
    assert geo.es_valida(nuevo)
    assert geo.volumen(nuevo) == pytest.approx(64)
    return nuevo


@pytest.mark.parametrize("desfase_h,desfase_v", [(5, 0), (0, -3), (5, -3)])
def test_desfases_en_ejes_locales(desfase_h, desfase_v):
    cuerpo = geo.caja(40, 30, 10)
    cara = _tapa(cuerpo)
    resultado = sc.repujado(cuerpo, [_rectangulo()], cara, 2, desfase_h=desfase_h, desfase_v=desfase_v)
    extra = _material_nuevo(cuerpo, resultado)
    centro = np.array(geo.centro_masa(extra))
    plano = geo.plano_de_cara(cara)
    assert centro == pytest.approx(np.array([14, 10, 11]) + plano.u * desfase_h + plano.v * desfase_v)


def test_giro_rota_la_caja_sin_mover_el_centro():
    cuerpo = geo.caja(40, 30, 10)
    resultado = sc.repujado(cuerpo, [_rectangulo()], _tapa(cuerpo), 2, giro=90)
    extra = _material_nuevo(cuerpo, resultado)
    minimo, maximo = np.array(geo.caja_envolvente(extra))
    assert maximo - minimo == pytest.approx([4, 8, 2], abs=1e-6)
    assert geo.centro_masa(extra) == pytest.approx([14, 10, 11])


def test_desfases_en_una_cara_vertical():
    cuerpo = geo.caja(40, 30, 10)
    cara = next(c for c in geo.caras(cuerpo)
                if (pl := geo.plano_de_cara(c)) is not None and pl.normal[0] > 0.9)
    base = sc.repujado(cuerpo, [_rectangulo()], cara, 2)
    movido = sc.repujado(cuerpo, [_rectangulo()], cara, 2, desfase_h=3, desfase_v=1)
    assert geo.es_valida(base) and geo.es_valida(movido)
    extra_base = geo.booleano(base, cuerpo, "cortar")
    extra_movido = geo.booleano(movido, cuerpo, "cortar")
    assert geo.es_valida(extra_base) and geo.es_valida(extra_movido)
    plano = geo.plano_de_cara(cara)
    diferencia = np.array(geo.centro_masa(extra_movido)) - geo.centro_masa(extra_base)
    assert diferencia == pytest.approx(plano.u * 3 + plano.v, abs=1e-6)


def test_alineacion_al_envolver_un_cilindro():
    cuerpo = geo.cilindro(10, 30)
    cara = next(c for c in geo.caras(cuerpo) if geo.plano_de_cara(c) is None)
    contorno = BRepBuilderAPI_MakePolygon()
    for p in [(10, -2, 12), (10, 2, 12), (10, 2, 18), (10, -2, 18)]:
        contorno.Add(gp_Pnt(*p))
    contorno.Close()
    perfil = BRepBuilderAPI_MakeFace(contorno.Wire()).Face()
    resultado = sc.repujado(cuerpo, [perfil], cara, 1, envolver=True, desfase_h=5, desfase_v=3, giro=90)
    assert geo.es_valida(resultado)
    extra = geo.booleano(resultado, cuerpo, "cortar")
    assert geo.es_valida(extra)
    assert geo.volumen(extra) == pytest.approx(25.2, rel=1e-5)
    x, y, z = geo.centro_masa(extra)
    assert math.atan2(y, x) == pytest.approx(0.5, abs=1e-5)
    assert z == pytest.approx(18)
    minimo, maximo = geo.caja_envolvente(extra)
    assert maximo[2] - minimo[2] == pytest.approx(4, abs=1e-6)


def test_invertir_relieve_agrega_material_hacia_el_otro_lado():
    cuerpo = geo.caja(40, 30, 10)
    resultado = sc.repujado(cuerpo, [_rectangulo()], _tapa(cuerpo), 12, invertir=True)
    assert geo.es_valida(resultado)
    assert geo.volumen(resultado) == pytest.approx(12000 + 64)
    extra = _material_nuevo(cuerpo, resultado)
    assert geo.centro_masa(extra) == pytest.approx([14, 10, -1])
    assert np.array(geo.caja_envolvente(extra))[:, 2] == pytest.approx([-2, 0], abs=1e-6)


def test_invertir_no_convierte_relieve_en_grabado():
    cuerpo = geo.caja(40, 30, 10)
    resultado = sc.repujado(cuerpo, [_rectangulo()], _tapa(cuerpo), 2, invertir=True)
    assert geo.es_valida(resultado)
    assert geo.volumen(resultado) == pytest.approx(12000)


def test_cadena_tangente_agrega_el_empalme_sin_duplicar_caras():
    cuerpo = geo.caja(40, 30, 10)
    def es_arista_superior(e):
        curva = BRepAdaptor_Curve(e)
        p = curva.Value((curva.FirstParameter() + curva.LastParameter()) / 2)
        return np.allclose([p.X(), p.Y(), p.Z()], [40, 15, 10])

    arista = next(e for e in sc._aristas_de(cuerpo) if es_arista_superior(e))
    cuerpo = sm.empalme(cuerpo, [{"aristas": [arista], "radio": 3}])
    cara = _tapa(cuerpo)
    cadena = sm.caras_tangentes(cuerpo, cara)
    assert len(cadena) == 3
    perfil = geo.trasladar(_rectangulo(), [23, 0, 0])
    solo = sc.repujado(cuerpo, [perfil], cara, 1)
    resultado = sc.repujado(cuerpo, [perfil], [cara, cara], 1, cadena_tangente=True)
    explicito = sc.repujado(cuerpo, [perfil], cadena, 1, envolver=True, cadena_tangente=True)
    assert all(geo.es_valida(f) for f in (cuerpo, solo, resultado, explicito))
    assert geo.volumen(resultado) > geo.volumen(solo) + 1
    assert geo.volumen(resultado) == pytest.approx(geo.volumen(explicito))


def _llamar(sesion, nombre, argumentos):
    respuesta = api.llamar(sesion, nombre, argumentos)
    assert respuesta["ok"], respuesta
    return respuesta["result"]


def _sesion():
    sesion = api.Sesion()
    _llamar(sesion, "create_box", {"length": 40, "width": 30, "height": 10})
    _llamar(sesion, "create_sketch", {"plane": ">Z", "name": "Marca"})
    _llamar(sesion, "draw_circle", {"radius": 2, "sketch": "Marca"})
    return sesion


def test_receta_vieja_y_opciones_disponibles_por_api():
    sesion = _sesion()
    resultado = _llamar(sesion, "run_operation", {"type": "repujado", "params": {
        "perfiles": [{"sketch": "Marca", "profile": 0}], "cara": ">Z", "profundidad": "1 mm"}})
    cuerpo = sesion.cuerpo("Cuerpo1").forma
    assert geo.es_valida(cuerpo)
    assert geo.volumen(cuerpo) == pytest.approx(12000 + 4 * math.pi)
    op = sesion.paso(resultado["id"])
    assert op.p["cadena_tangente"] is False and op.p["invertir"] is False

    sesion = _sesion()
    resultado = _llamar(sesion, "run_operation", {"type": "repujado", "params": {
        "perfiles": [{"sketch": "Marca", "profile": 0}], "cara": ">Z", "profundidad": "12 mm",
        "desfase_h": "2 mm + 3 mm", "desfase_v": "-2 mm", "giro": "45 deg * 2",
        "cadena_tangente": True, "invertir": True}})
    op = sesion.paso(resultado["id"])
    parametros = copy.deepcopy(op.p)
    sesion.doc.recalcular()
    assert op.p == parametros
    cuerpo = sesion.cuerpo("Cuerpo1").forma
    assert geo.es_valida(cuerpo)
    assert geo.volumen(cuerpo) == pytest.approx(12000 + 8 * math.pi)
    assert geo.caja_envolvente(cuerpo)[0][2] == pytest.approx(-2, abs=1e-6)


def test_dialogo_conserva_las_opciones_al_editar():
    from omnicad.ui.comando import ContextoComando
    from omnicad.ui.comandos.crear import Repujado

    sesion = _sesion()
    resultado = _llamar(sesion, "run_operation", {"type": "repujado", "params": {
        "perfiles": [{"sketch": "Marca", "profile": 0}], "cara": ">Z"}})
    op = sesion.paso(resultado["id"])
    contexto = ContextoComando(sesion.doc, op=op)
    comando = Repujado()
    campos = {c.clave: c for c in comando.campos(contexto)}
    valores = comando.desde_op(op, contexto)
    valores.update(desfase_h="5 mm", desfase_v="-2 mm", giro="90 deg", cadena_tangente=True, invertir=True)
    nueva = comando.construir(valores, contexto)
    for clave in ("desfase_h", "desfase_v", "giro", "cadena_tangente", "invertir"):
        assert clave in campos and nueva.p[clave] == valores[clave]


@pytest.mark.parametrize("clave", ["desfase_h", "desfase_v", "giro"])
def test_alineacion_rechaza_valores_no_finitos(clave):
    cuerpo = geo.caja(40, 30, 10)
    with pytest.raises(geo.ErrorGeometria, match="finitos"):
        sc.repujado(cuerpo, [_rectangulo()], _tapa(cuerpo), 1, **{clave: math.nan})
