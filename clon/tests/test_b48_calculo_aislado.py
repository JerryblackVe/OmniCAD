# -*- coding: utf-8 -*-
"""B-48: el resultado del hijo se usa de verdad, sin volver a ejecutar el kernel en el padre."""
import subprocess
import sys

import pytest

from omnicad.io_archivos import proyecto
from omnicad.nucleo import aislado, motor
from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import ErrorDocumento
from omnicad.timeline.operaciones import OpPrimitiva
from test_b48_prevuelo import _caja_ancha, _crash, _documento, _instantanea, _tabla, _volumenes


@pytest.fixture(autouse=True)
def opencascade():
    with motor.fijar_motor("opencascade"):
        yield


@pytest.mark.parametrize("accion", ["parametros", "editar", "suprimir", "eliminar", "agregar",
                                    "previa_edicion", "previa_nueva", "recalcular", "abrir"])
def test_el_calculo_grande_no_ejecuta_operaciones_en_el_padre(monkeypatch, tmp_path, accion):
    doc = _documento(3)
    ruta = proyecto.guardar(doc, tmp_path / "grande.omnicad", incluir_cache=False)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)

    def no_calcular(*args):
        raise AssertionError("Se repitió el cálculo del kernel en el padre")

    # El hijo real importa la clase original; este reemplazo detecta solo el cálculo dentro del padre.
    monkeypatch.setattr(OpPrimitiva, "ejecutar", no_calcular)
    esperado = [30, 30, 30]
    if accion == "parametros":
        doc.aplicar_parametros(_tabla(doc))
        esperado = [70, 70, 70]
    elif accion == "editar":
        doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
        esperado = [30, 60, 30]
    elif accion == "suprimir":
        doc.suprimir("op1")
        esperado = [30, 30]
    elif accion == "eliminar":
        doc.eliminar("op1")
        esperado = [30, 30]
    elif accion == "agregar":
        doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="4", largo="5", alto="altura"))
        esperado = [30, 30, 30, 60]
    elif accion in ("previa_edicion", "previa_nueva"):
        nueva = _caja_ancha(doc.operacion("op2"))
        indice = 1
        if accion == "previa_nueva":
            nueva.id, indice = doc.nuevo_id(), doc.marcador
        antes = _instantanea(doc)
        estado, avisos = doc.previsualizar(nueva, indice)
        assert avisos == []
        assert [geo.volumen(c.forma) for c in estado.cuerpos.values()] == pytest.approx(
            [30, 60] if accion == "previa_edicion" else [30, 30, 30, 60])
        assert _instantanea(doc) == antes
    elif accion == "recalcular":
        doc.parametros.modificar("altura", "7 mm")
        doc.recalcular()
        esperado = [70, 70, 70]
    elif accion == "abrir":
        doc = proyecto.abrir(ruta)
    assert all(r.estado in ("ok", "suprimida") for r in doc.resultados)
    assert _volumenes(doc) == pytest.approx(esperado)
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())


def test_un_hijo_que_no_entrega_el_calculo_no_habilita_el_kernel_en_el_padre(monkeypatch):
    doc = _documento(3)
    antes = _instantanea(doc)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "correr_json", lambda *args: {"errores": 0, "pasos": 3})
    with pytest.raises(ErrorDocumento, match="resultado|cálculo"):
        doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    assert _instantanea(doc) == antes


@pytest.mark.parametrize("accion", ["deshacer", "rehacer", "marcador", "reordenar", "configuracion"])
def test_crash_al_cambiar_historial_conserva_receta_modelo_y_ambas_colas(monkeypatch, accion):
    doc = _documento(3)
    if accion in ("deshacer", "rehacer"):
        doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
        if accion == "rehacer":
            doc.deshacer()
    antes = _instantanea(doc)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    _crash(monkeypatch)
    with pytest.raises(ErrorDocumento, match="error nativo"):
        if accion == "deshacer":
            doc.deshacer()
        elif accion == "rehacer":
            doc.rehacer()
        elif accion == "marcador":
            doc.mover_marcador(1)
        elif accion == "reordenar":
            doc.mover("op3", 0)
        else:
            doc.aplicar_configuracion({"columnas": [{"tipo": "parametro", "nombre": "altura"}],
                                       "filas": [{"nombre": "Alta", "valores": ["7 mm"]}]}, "Alta")
    assert _instantanea(doc) == antes


def test_el_transporte_conserva_perfiles_formas_y_referencias_compartidas():
    from omnicad.ejemplo import crear_documento_ejemplo
    from omnicad.timeline.calculo_aislado import _empaquetar, _leer_calculo

    doc = crear_documento_ejemplo()
    datos = _leer_calculo(_empaquetar(doc))
    assert datos["receta"] == doc.a_dict()
    estados = datos["estados"]
    assert [geo.volumen(c.forma) for c in estados[-1].cuerpos.values()] == pytest.approx(_volumenes(doc))
    for estado in estados:
        for boceto in estado.bocetos.values():
            assert all(geo.es_valida(p.cara) and geo.area(p.cara) == pytest.approx(p.area) for p in boceto.perfiles)
        assert all(geo.es_valida(c.forma) for c in estado.cuerpos.values())
    for anterior, siguiente in zip(estados, estados[1:], strict=False):
        for cid, cuerpo in anterior.cuerpos.items():
            if cid in siguiente.cuerpos and cuerpo.forma.IsSame(siguiente.cuerpos[cid].forma):
                assert cuerpo.forma is siguiente.cuerpos[cid].forma


def test_el_transporte_no_reconstruye_clases_arbitrarias():
    from omnicad.timeline.calculo_aislado import _leer_calculo

    salida = {"calculo": {"version": 1, "raiz": {"ref": 0}, "nodos": [["os.system", "no ejecutar"]]}}
    with pytest.raises(ValueError, match="Tipo no admitido"):
        _leer_calculo(salida)


@pytest.mark.parametrize("familia", ["boceto", "ensamble", "chapa", "malla"])
def test_calculo_aislado_conserva_modelo_deshacer_y_marcador(monkeypatch, familia):
    from omnicad.timeline.operaciones import Operacion, operacion_desde_dict

    if familia == "boceto":
        from omnicad.ejemplo import crear_documento_ejemplo
        doc = crear_documento_ejemplo()
    elif familia == "ensamble":
        from test_gizmo_accionar import _doc_union
        doc, _ = _doc_union()
    elif familia == "chapa":
        from PySide6.QtWidgets import QApplication
        from test_chapa import _doc_pestana
        _app = QApplication.instance() or QApplication([])
        doc = _doc_pestana()
    else:
        doc = _documento(3)
        doc.agregar(operacion_desde_dict({"tipo": "teselar", "id": doc.nuevo_id(),
                                         "params": {"cuerpos": ["op1.c1"], "mantener": True}}))

    def volumenes():
        return {cid: abs(c.forma.volumen()) if c.tipo == "malla" else geo.volumen(c.forma)
                for cid, c in doc.estado_final.cuerpos.items()}

    def no_calcular(*args):
        raise AssertionError("El padre ejecutó una operación del kernel")

    antes, valores = doc.a_dict(), volumenes()
    dependencias = {o.id: o.dependencias() for o in doc.operaciones}
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(Operacion, "calcular", no_calcular)
    doc.recalcular()
    assert all(r.estado in ("ok", "aviso") for r in doc.resultados)
    assert doc.a_dict() == antes and volumenes() == pytest.approx(valores)
    assert {o.id: o.dependencias() for o in doc.operaciones} == dependencias
    for c in doc.estado_final.cuerpos.values():
        if getattr(c, "chapa", None):
            assert c.forma is c.forma_chapa
    doc.deshacer()
    doc.rehacer()
    assert doc.a_dict() == antes and volumenes() == pytest.approx(valores)
    doc.mover_marcador(0)
    assert not doc.estado_final.cuerpos
    doc.mover_marcador(len(doc.operaciones))
    assert volumenes() == pytest.approx(valores)
    assert all(r.estado in ("ok", "aviso") for r in doc.resultados)


def test_un_fallo_fatal_si_se_repite_el_kernel_no_alcanza_al_proceso_padre():
    codigo = '''
import os
from omnicad.nucleo import aislado, geometria as geo
from omnicad.timeline.documento import Documento
from omnicad.timeline.operaciones import OpPrimitiva
from omnicad.timeline.parametros import TablaParametros
doc = Documento()
doc.parametros.agregar("altura", "3 mm")
for i in range(2):
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="5", alto="altura", x=str(i * 4)))
aislado.UMBRAL_PREVUELO_PARAMETROS = 2
def caer(*args):
    os._exit(-1073741819)
OpPrimitiva.ejecutar = caer
tabla = TablaParametros.desde_lista(doc.parametros.a_lista())
tabla.modificar("altura", "7 mm")
doc.aplicar_parametros(tabla)
assert all(r.estado == "ok" for r in doc.resultados)
assert all(abs(geo.volumen(c.forma) - 70) < 1e-6 for c in doc.estado_final.cuerpos.values())
print("padre vivo; resultado del hijo correcto")
'''
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=aislado._RAIZ, capture_output=True,
                            text=True, encoding="utf-8", timeout=60)
    assert salida.returncode == 0, salida.stderr
    assert "padre vivo; resultado del hijo correcto" in salida.stdout


def test_el_hijo_conserva_el_directorio_y_actualiza_parametros_derivados(monkeypatch, tmp_path):
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.ops_derivacion import OpDerivacion

    fuente = Documento()
    fuente.parametros.agregar("externo", "3 mm")
    fuente.agregar(OpPrimitiva(fuente.nuevo_id(), forma="caja", ancho="externo", largo="2", alto="5"))
    proyecto.guardar(fuente, tmp_path / "fuente.omnicad")
    monkeypatch.chdir(tmp_path)
    doc = _documento(3)
    doc.agregar(OpDerivacion(doc.nuevo_id(), archivo="fuente.omnicad", cuerpos=["op1.c1"], parametros=["externo"]))
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="externo", largo="2", alto="5"))
    assert all(r.estado == "ok" for r in doc.resultados)
    fuente.parametros.modificar("externo", "4 mm")
    fuente.recalcular()
    proyecto.guardar(fuente, tmp_path / "fuente.omnicad")
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    doc.recalcular()
    assert all(r.estado == "ok" for r in doc.resultados)
    assert doc.parametros.valores()["externo"] == 4
    assert _volumenes(doc) == pytest.approx([30, 30, 30, 40, 40])


def test_el_que_llama_recibe_los_segundos_de_espera_del_hijo(monkeypatch):
    monkeypatch.setattr(aislado, "_comando", lambda tarea, carpeta: [
        sys.executable, "-c", "import sys, time; time.sleep(1.2); open(sys.argv[1] + '/salida.json', 'w').write('{}')",
        str(carpeta)])
    esperas = []
    assert aislado.correr_json("recalcular_documento", {"receta": {}}, 30, esperas.append) == {}
    assert len(esperas) > 10 and esperas[-1] >= 1.2 and esperas == sorted(esperas)
