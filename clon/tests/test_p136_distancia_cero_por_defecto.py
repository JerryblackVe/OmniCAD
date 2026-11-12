"""P-136: distancias del diálogo en cero, sin pasos vacíos y con asas utilizables desde el origen."""
import numpy as np
import pytest
from PySide6.QtCore import QPointF
from test_manipuladores import (  # noqa: F401 — fixture y gestos de ratón ya usados por los tests de comandos
    _arrastrar, _cara_de_arriba, _doc_caja, _doc_rectangulo, _hit_cuerpo, _manip, _panel, _perfil,
    _sobre_flecha, app_qt,
)

from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.ui.comando import ContextoComando, PanelComando, hit_desde_ref
from omnicad.ui.comandos import CATALOGO


CLAVES = ("extruir", "sup_extruir", "plano_desfase", "mover_copiar", "sup_desfase", "pulsar_tirar",
          "desfase_cara", "extruir_cara", "desfase")
pytestmark = pytest.mark.usefixtures("app_qt")


@pytest.fixture(autouse=True)
def preajustes_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("OMNICAD_PREAJUSTES", str(tmp_path / "preajustes.json"))


def _caso(clave):
    if clave in ("extruir", "sup_extruir"):
        doc = _doc_rectangulo()
        if clave == "extruir":
            return doc, {"perfiles": [_perfil(doc)]}
        curva = next(iter(doc.estado_final.bocetos["op1"].boceto.curvas))
        return doc, {"curvas": [hit_desde_ref({"tipo": "curva_boceto", "boceto": "op1", "curva": curva}, doc.estado_final)]}
    if clave == "plano_desfase":
        doc = Documento()
        return doc, {"r0": [hit_desde_ref({"tipo": "plano", "id": "XY"}, doc.estado_final)]}
    doc = _doc_caja()
    if clave == "mover_copiar":
        return doc, {"cuerpos": [_hit_cuerpo(doc)], "tipo": "traslacion",
                     "direccion": [hit_desde_ref({"tipo": "eje", "id": "Z"}, doc.estado_final)]}
    return doc, {"objetos" if clave in ("pulsar_tirar", "desfase") else "caras": [_cara_de_arriba(doc)]}


def _teclear(panel, clave, texto):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    campo = panel.widgets[clave]
    campo.selectAll()
    QTest.keyClicks(campo, texto)
    QTest.keyClick(campo, Qt.Key_Tab)
    assert panel.valores[clave] == texto


@pytest.mark.parametrize("clave", CLAVES)
def test_dialogo_arranca_en_cero_rechaza_aceptar_y_diez_crea_la_geometria(monkeypatch, clave):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    doc, valores = _caso(clave)
    panel, visor, previas = _panel(CATALOGO[clave](), doc, valores)
    receta = doc.a_dict()
    aceptadas = []

    def aplicar(op):
        aceptadas.append(op)
        resultado = doc.agregar(op)
        assert resultado.estado in ("ok", "aviso"), resultado.mensaje

    panel.aceptado.connect(aplicar)
    try:
        assert panel.widgets["distancia"].text() == panel.valores["distancia"] == "0 mm"
        if clave in ("extruir", "sup_extruir"):
            assert panel.valores["distancia2"] == "0 mm"
        # Ni la previa ni Aceptar deben llegar al kernel con el cero inicial.
        with monkeypatch.context() as parche:
            parche.setattr(doc, "previsualizar", lambda *a, **k: pytest.fail("Se calculó una previa con distancia cero."))
            panel._t_previa.stop()
            panel._calcular_previa()
            QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert not panel._previa_ok and panel.ultima_op is None
        assert previas[-1] is None and "cero" in panel.mensaje.text()
        assert aceptadas == [] and doc.a_dict() == receta

        _teclear(panel, "distancia", "10")
        panel._t_previa.stop()
        panel._calcular_previa()
        assert panel._previa_ok, panel.mensaje.text()
        # Volver a cero borra también una previa válida, sin aceptar la operación anterior.
        receta = doc.a_dict()
        _teclear(panel, "distancia", "0")
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert previas[-1] is None and aceptadas == [] and doc.a_dict() == receta

        _teclear(panel, "distancia", "10")
        QTest.mouseClick(panel.boton_ok, Qt.LeftButton)
        assert len(aceptadas) == 1
        assert len(doc.operaciones) == len(receta["operaciones"]) + 1
        op = aceptadas[0]
        assert doc.resultado(op.id).estado in ("ok", "aviso")
        if clave == "plano_desfase":
            assert doc.estado_final.planos[op.id].origen == pytest.approx((0, 0, 10))
        else:
            cuerpo = list(doc.estado_final.cuerpos.values())[-1]
            assert geo.es_valida(cuerpo.forma)
            if clave in ("sup_extruir", "sup_desfase"):
                assert geo.area(cuerpo.forma) == pytest.approx(200 if clave == "sup_extruir" else 400)
            else:
                esperado = 2000 if clave == "extruir" else 8000 if clave == "mover_copiar" else 12000
                assert geo.volumen(cuerpo.forma) == pytest.approx(esperado)
            if clave == "mover_copiar":
                assert np.array(geo.caja_envolvente(cuerpo.forma))[:, 2] == pytest.approx((10, 30), abs=1e-6)
            elif clave == "sup_desfase":
                assert np.array(geo.caja_envolvente(cuerpo.forma))[:, 2] == pytest.approx((30, 30), abs=1e-6)
        # Editar conserva lo escrito: el defecto nuevo no pisa pasos existentes.
        comando = CATALOGO[clave]()
        if comando.CLASE_OP is not None:
            editado = PanelComando(comando, ContextoComando(doc, op=op), visor)
            assert editado.valores["distancia"] == "10"
            editado.cancelar()
            editado.deleteLater()
    finally:
        if not panel.cerrando:          # tras Aceptar el panel ya se cerró: cancelar de nuevo desconecta dos veces
            panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()


@pytest.mark.parametrize("tipo", ["libre", "traslacion"])
def test_mover_sin_direccion_no_acepta_un_desplazamiento_vacio(tipo):
    doc, valores = _caso("mover_copiar")
    valores.update(tipo=tipo, direccion=[])
    panel, visor, previas = _panel(CATALOGO["mover_copiar"](), doc, valores)
    aceptadas = []
    panel.aceptado.connect(aceptadas.append)
    try:
        panel.aceptar()
        assert aceptadas == [] and previas[-1] is None and "cero" in panel.mensaje.text()
        _teclear(panel, "dx", "10")
        panel._t_previa.stop()
        panel._calcular_previa()
        assert panel._previa_ok, panel.mensaje.text()
        forma = next(iter(previas[-1].cuerpos.values())).forma
        assert geo.es_valida(forma) and geo.volumen(forma) == pytest.approx(8000)
        assert np.array(geo.caja_envolvente(forma))[:, 0] == pytest.approx((10, 30), abs=1e-6)
        panel.aceptar()
        assert len(aceptadas) == 1 and aceptadas[0].p["dx"] == "10"
    finally:
        if not panel.cerrando:          # tras Aceptar el panel ya se cerró: cancelar de nuevo desconecta dos veces
            panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()


@pytest.mark.parametrize("clave", CLAVES)
def test_la_flecha_arranca_en_cero_sin_salto_y_se_puede_arrastrar(clave):
    doc, valores = _caso(clave)
    panel, visor, _ = _panel(CATALOGO[clave](), doc, valores)
    try:
        gestor = panel.manipuladores
        flecha = _manip(panel, "flecha:distancia")
        assert flecha.puntos(gestor)[0] == pytest.approx(flecha.origen)
        medio, direccion = _sobre_flecha(panel, "flecha:distancia")
        pos = QPointF(float(medio[0]), float(medio[1]))
        arrastre = flecha.empezar(gestor, pos, "flecha")
        assert arrastre is not None and arrastre["v0"] == 0
        assert flecha.mover(gestor, arrastre, pos)["distancia"] == pytest.approx(0, abs=1e-9)
        _arrastrar(visor, medio, medio + direccion * 80)
        assert panel.ctx.evaluar(panel.valores["distancia"]) > 0
        panel._t_previa.stop()
        panel._calcular_previa()
        assert panel._previa_ok, panel.mensaje.text()
    finally:
        if not panel.cerrando:          # tras Aceptar el panel ya se cerró: cancelar de nuevo desconecta dos veces
            panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()


@pytest.mark.parametrize("clave,direccion", [("extruir", "direccion"), ("sup_extruir", "lados")])
def test_dos_lados_pide_las_dos_distancias_y_conserva_sus_asas(clave, direccion):
    doc, valores = _caso(clave)
    panel, visor, previas = _panel(CATALOGO[clave](), doc, dict(valores, **{direccion: "dos_lados"}))
    try:
        assert panel.valores["distancia"] == panel.valores["distancia2"] == "0 mm"
        gestor = panel.manipuladores
        for campo in ("distancia", "distancia2"):
            flecha = _manip(panel, f"flecha:{campo}")
            assert flecha.puntos(gestor)[0] == pytest.approx(flecha.origen)
        _teclear(panel, "distancia", "10")
        panel._t_previa.stop()
        panel._calcular_previa()
        assert not panel._previa_ok and "lado 2" in panel.mensaje.text()
        _teclear(panel, "distancia2", "10")
        panel._t_previa.stop()
        panel._calcular_previa()
        assert panel._previa_ok, panel.mensaje.text()
        forma = list(previas[-1].cuerpos.values())[-1].forma
        assert geo.es_valida(forma)
        assert np.array(geo.caja_envolvente(forma))[:, 2] == pytest.approx((-10, 10), abs=1e-6)
        assert (geo.volumen(forma) if clave == "extruir" else geo.area(forma)) == pytest.approx(4000 if clave == "extruir" else 400)
    finally:
        if not panel.cerrando:          # tras Aceptar el panel ya se cerró: cancelar de nuevo desconecta dos veces
            panel.cancelar()
        panel.deleteLater()
        visor.deleteLater()
