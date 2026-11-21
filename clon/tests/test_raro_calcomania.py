# -*- coding: utf-8 -*-
"""Valores raros del panel de «Calcomanía» (Fusion: Insert > Decal): cada campo escrito en vacío, 0, negativo,
enorme, con unidades y con expresión. Aceptar nunca cierra la app ni deja el panel roto; todo aviso es de un renglón.
La ayuda de Fusion (`add-a-decal-1c017a711b1`) fija opacidad, posición, escala y volteos, sin topes publicados."""
import os

import pytest
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from omnicad import api  # noqa: E402
from omnicad.timeline.documento import Documento  # noqa: E402
from omnicad.timeline.operaciones import OpPrimitiva  # noqa: E402
from omnicad.timeline.parametros import ANGULO, ESCALAR, LONGITUD  # noqa: E402
from omnicad.ui.comando import hit_desde_ref  # noqa: E402
from omnicad.ui.comandos.insertar import Calcomania  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from test_p23_navegador import ventana as ventana  # noqa: E402


@pytest.fixture
def imagen(tmp_path):
    ruta = tmp_path / "calcomania.png"
    Image.new("RGBA", (80, 40), "white").save(ruta)
    return ruta


@pytest.fixture
def v(ventana):
    doc = Documento()
    doc.agregar(OpPrimitiva(doc.nuevo_id(), "Caja", forma="caja", ancho=40, largo=30, alto=20))
    ventana.set_documento(doc)
    yield ventana
    if ventana.panel is not None:
        ventana.panel.cancelar()


def _cara(v):
    """Referencia persistente de una cara plana, como la que el usuario elige en el visor."""
    s = api.Sesion(v.doc)
    cid = next(iter(v.doc.estado_final.cuerpos))
    r = api.llamar(s, "find_faces", {"body": cid, "selector": ">Z"})
    assert r["ok"], r
    from omnicad.api.selectores import elegir
    from omnicad.nucleo import referencias
    elegida = elegir(s, r["result"]["faces"][0]["id"], "cara")[0]
    ref = referencias.referencia(cid, elegida[1].sub, v.doc.estado_final.cuerpos[cid].forma)
    return hit_desde_ref(ref, v.doc.estado_final)


def _abrir(v, imagen, cara=True):
    valores = {"archivo": str(imagen)}
    if cara:
        valores["plano"] = [_cara(v)]
    p = v.ejecutar_comando(Calcomania(), valores=valores)
    assert p is not None and p.comando.CLAVE == "calcomania"
    p._calcular_previa()
    return p


def _escribir(p, clave, texto):
    if clave == "opacidad":
        numero = p.widgets["opacidad"].numero
        numero.lineEdit().setText(texto)
        numero.interpretText()
    else:
        p.set_valor(clave, texto)


def _sano(p):
    """La app sigue abierta, el panel dibuja y el aviso cabe en un renglón sin errores crudos de Python."""
    assert QApplication.instance() is not None
    assert p.isVisible()
    p.grab()
    texto = p.mensaje.text()
    assert "\n" not in texto and "\r" not in texto, texto
    for crudo in ("traceback", "could not convert", "valueerror", "typeerror", "nameerror", "float()", "invalid literal"):
        assert crudo not in texto.lower(), texto


def _estado(doc):
    """El recuento de números internos sube al calcular la previa; no es un cambio del documento."""
    datos = doc.a_dict()
    datos.pop("contador", None)
    return datos


def _recuperar(p, clave, imagen):
    valido = {"archivo": str(imagen), "opacidad": 50, "ancho": "0 mm", "alto": "0 mm", "dx": "0 mm",
              "dy": "0 mm", "angulo": "0 deg", "escala": "1"}[clave]
    p.set_valor(clave, valido)
    p._calcular_previa()
    assert p._previa_ok and p.ultima_op is not None, p.mensaje.text()
    _sano(p)


CAMPOS = ["archivo", "opacidad", "ancho", "alto", "dx", "dy", "angulo", "escala"]
VALORES = [("", "vacio"), ("0", "cero"), ("-1", "negativo"), ("1e9", "enorme"),
           ("10 mm", "unidad"), ("2*3", "expresion")]


@pytest.mark.parametrize("clave", CAMPOS)
@pytest.mark.parametrize("texto, caso", VALORES, ids=[c for _, c in VALORES])
def test_valor_raro_no_rompe_el_panel_ni_el_documento(v, imagen, clave, texto, caso):
    p = _abrir(v, imagen)
    antes = _estado(v.doc)
    _escribir(p, clave, texto)
    p._calcular_previa()
    _sano(p)
    _recuperar(p, clave, imagen)
    p.cancelar()
    assert _estado(v.doc) == antes


def test_sin_cara_avisa_en_un_renglon_y_no_rompe_la_app(v, imagen):
    p = _abrir(v, imagen, cara=False)
    antes = _estado(v.doc)
    p._calcular_previa()
    _sano(p)
    assert p.mensaje.text() and not p._previa_ok
    p.set_valor("plano", [_cara(v)])
    p._calcular_previa()
    assert p._previa_ok and p.ultima_op is not None, p.mensaje.text()
    p.cancelar()
    assert _estado(v.doc) == antes


@pytest.mark.parametrize("clave", ["encadenar", "mantener_proporcion", "voltear", "voltear_v"])
def test_casillas_aceptan_ambos_estados_sin_romper(v, imagen, clave):
    p = _abrir(v, imagen)
    antes = _estado(v.doc)
    for estado in (False, True, False):
        p.set_valor(clave, estado)
        p._calcular_previa()
        assert p._previa_ok and p.ultima_op is not None, p.mensaje.text()
        _sano(p)
    p.cancelar()
    assert _estado(v.doc) == antes


def test_casilla_usar_opacidad_acepta_ambos_estados(v, imagen):
    p = _abrir(v, imagen)
    antes = _estado(v.doc)
    for estado in (False, True, False):
        p.widgets["opacidad"].casilla.setChecked(estado)
        p._calcular_previa()
        assert p._previa_ok and p.ultima_op is not None, p.mensaje.text()
        _sano(p)
    p.cancelar()
    assert _estado(v.doc) == antes


@pytest.mark.parametrize("clave,texto,tipo,esperado", [
    ("ancho", "10 mm", "longitud", 10.0), ("alto", "20 mm", "longitud", 20.0),
    ("dx", "1 cm", "longitud", 10.0), ("dy", "2*3 mm", "longitud", 6.0),
    ("angulo", "45 deg", "angulo", 45.0), ("escala", "2*0.5", "escalar", 1.0)])
def test_unidades_y_expresiones_se_aplican(v, imagen, clave, texto, tipo, esperado):
    p = _abrir(v, imagen)
    p.set_valor("mantener_proporcion", False)
    _escribir(p, clave, texto)
    p._calcular_previa()
    assert p._previa_ok and p.ultima_op is not None, p.mensaje.text()
    tipo_parametro = {"longitud": LONGITUD, "angulo": ANGULO, "escalar": ESCALAR}[tipo]
    assert p.ctx.evaluar(p.ultima_op.p[clave], tipo_parametro) == pytest.approx(esperado)
    p.cancelar()


def test_despues_de_un_valor_raro_aceptar_sigue_creando_la_calcomania(v, imagen):
    p = _abrir(v, imagen)
    _escribir(p, "ancho", "-1")
    p._calcular_previa()
    _sano(p)
    _recuperar(p, "ancho", imagen)
    p.aceptar()
    assert QApplication.instance() is not None and v.panel is None
    assert len(v.doc.operaciones) == 2 and len(v.doc.estado_final.lienzos) == 1
