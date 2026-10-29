# -*- coding: utf-8 -*-
"""B-48: el cálculo aislado entrega estados reales y una caída del hijo conserva el documento."""
import json
import sys
import time
import zipfile

import pytest

from omnicad.nucleo import aislado, motor
from omnicad.nucleo import geometria as geo
from omnicad.restricciones import Boceto
from omnicad.timeline.documento import Documento, ErrorDocumento
from omnicad.timeline.operaciones import OpBoceto, OpPrimitiva
from omnicad.timeline.parametros import TablaParametros


@pytest.fixture(autouse=True)
def opencascade():
    with motor.fijar_motor("opencascade"):
        yield


def _documento(cantidad=2):
    doc = Documento()
    doc.parametros.agregar("altura", "3 mm")
    for i in range(cantidad):
        doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="2", largo="5", alto="altura", x=str(i * 4)))
    assert all(r.estado == "ok" for r in doc.resultados)
    return doc


def _tabla(doc):
    tabla = TablaParametros.desde_lista(doc.parametros.a_lista())
    tabla.modificar("altura", "7 mm")
    return tabla


def _volumenes(doc):
    return [geo.volumen(c.forma) for c in doc.estado_final.cuerpos.values()]


def _instantanea(doc):
    return (doc.a_dict(), _volumenes(doc), list(doc._deshacer), list(doc._rehacer), doc.modificado)


def test_crash_nativo_no_toca_documento_ni_deshacer(monkeypatch):
    doc = _documento()
    # Conserva también una entrada real de rehacer: el prevuelo no debe vaciarla.
    doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja"))
    doc.deshacer()
    doc.modificado = False
    antes, parametros, estados = _instantanea(doc), doc.parametros, list(doc._estados)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "_comando", lambda tarea, carpeta: [sys.executable, "-c",
                                                                 "import os; os._exit(-1073741819)"])
    with pytest.raises(ErrorDocumento, match="error nativo"):
        doc.aplicar_parametros(_tabla(doc))
    assert doc.parametros is parametros
    assert doc._estados == estados
    assert _instantanea(doc) == antes
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())


def test_hijo_real_permite_cambio_y_volumen_correcto(monkeypatch):
    doc = _documento()
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    antes = len(doc._deshacer)
    original, salidas = aislado.correr_json, []

    def registrar(*args):
        salida = original(*args)
        salidas.append({k: salida[k] for k in ("errores", "pasos", "cuerpos")})
        return salida

    monkeypatch.setattr(aislado, "correr_json", registrar)
    assert _volumenes(doc) == pytest.approx([30, 30])
    doc.aplicar_parametros(_tabla(doc))
    assert salidas == [{"errores": 0, "pasos": 2, "cuerpos": 2}]
    assert doc.parametros.valores()["altura"] == 7
    assert _volumenes(doc) == pytest.approx([70, 70])
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())
    assert len(doc._deshacer) == antes + 1


@pytest.mark.parametrize("motivo", ["chico", "suprimidos", "marcador", "omnikernel", "hijo"])
def test_omite_prevuelo_cuando_no_corresponde(monkeypatch, motivo):
    doc = _documento()
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 3 if motivo == "chico" else 2)
    if motivo == "suprimidos":
        doc.suprimir("op2")
    elif motivo == "marcador":
        doc.mover_marcador(1)
    elif motivo == "hijo":
        monkeypatch.setattr(aislado, "EN_HIJO", True)
    elif motivo == "omnikernel":
        # Solo prueba la decisión: conserva OCC para calcular las formas ya creadas.
        monkeypatch.setattr(motor, "motor_activo", lambda: "omnikernel")
        monkeypatch.setattr(doc, "recalcular", lambda desde: None)
    llamadas = []
    monkeypatch.setattr(aislado.subprocess, "run", lambda *args, **kwargs: llamadas.append(args))
    doc.aplicar_parametros(_tabla(doc))
    assert llamadas == []
    assert doc.parametros.valores()["altura"] == 7


def test_tope_del_hijo_no_toca_documento(monkeypatch):
    doc = _documento()
    antes = _instantanea(doc)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "TOPE_PREVUELO_PARAMETROS", 0.1)
    monkeypatch.setattr(aislado, "_comando", lambda tarea, carpeta: [sys.executable, "-c",
                                                                 "import time; time.sleep(60)"])
    with pytest.raises(ErrorDocumento, match="se cortó"):
        doc.aplicar_parametros(_tabla(doc))
    assert _instantanea(doc) == antes


def test_hijo_informa_errores_de_pasos_sin_rechazar_tabla(monkeypatch):
    doc = _documento()
    tabla = _tabla(doc)
    tabla.modificar("altura", "-1 mm")
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    salida = aislado.correr_json("prevuelo_parametros", {"receta": doc.a_dict(), "parametros": tabla.a_lista()}, 60)
    assert {k: salida[k] for k in ("errores", "pasos", "cuerpos")} == {"errores": 2, "pasos": 2, "cuerpos": 0}
    assert doc.parametros.valores()["altura"] == 3
    doc.aplicar_parametros(tabla)
    assert doc.parametros.valores()["altura"] == -1
    assert [r.estado for r in doc.resultados] == ["error", "error"]


def test_costo_calculo_aislado_60_pasos():
    """Medición reproducible de todo el cambio: cálculo en el hijo y adopción de su resultado."""
    doc = _documento(60)
    assert aislado.UMBRAL_PREVUELO_PARAMETROS == 60
    tabla = _tabla(doc)
    inicio = time.perf_counter()
    doc.aplicar_parametros(tabla)
    recalculo = time.perf_counter() - inicio
    assert _volumenes(doc) == pytest.approx([70] * 60)
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())
    print(f"B-48: 60 pasos; cálculo aislado y adopción={recalculo:.6f} s", flush=True)


# ---------------------------------------------------------------- B-48: editar, suprimir, eliminar y abrir
def _crash(monkeypatch):
    monkeypatch.setattr(aislado, "_comando", lambda tarea, carpeta: [sys.executable, "-c",
                                                                 "import os; os._exit(-1073741819)"])


def _caja_ancha(op):
    return OpPrimitiva(op.id, forma="caja", ancho="4", largo="5", alto="altura", x=op.p.get("x"))


def test_crash_nativo_al_editar_no_toca_documento(monkeypatch):
    doc = _documento(3)
    antes = _instantanea(doc)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    _crash(monkeypatch)
    op = doc.operaciones[1]
    with pytest.raises(ErrorDocumento, match="error nativo"):
        doc.reemplazar(op.id, _caja_ancha(op))
    assert _instantanea(doc) == antes


def test_crash_nativo_al_suprimir_no_toca_documento(monkeypatch):
    doc = _documento(3)
    antes = _instantanea(doc)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    _crash(monkeypatch)
    with pytest.raises(ErrorDocumento, match="error nativo"):
        doc.suprimir(doc.operaciones[1].id)
    assert _instantanea(doc) == antes


def test_crash_nativo_al_eliminar_no_toca_documento(monkeypatch):
    doc = _documento(3)
    antes = _instantanea(doc)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    _crash(monkeypatch)
    with pytest.raises(ErrorDocumento, match="error nativo"):
        doc.eliminar(doc.operaciones[-1].id)
    assert _instantanea(doc) == antes


def test_hijo_real_permite_editar_suprimir_y_eliminar(monkeypatch):
    doc = _documento(3)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    op = doc.operaciones[1]
    doc.reemplazar(op.id, _caja_ancha(op))
    assert _volumenes(doc) == pytest.approx([30, 60, 30])
    doc.suprimir(doc.operaciones[0].id)
    assert _volumenes(doc) == pytest.approx([60, 30])
    doc.eliminar(doc.operaciones[-1].id)
    assert _volumenes(doc) == pytest.approx([60])
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())


def test_crash_nativo_al_abrir_un_archivo_grande_no_lo_abre(monkeypatch, tmp_path):
    from omnicad.io_archivos import proyecto

    doc = _documento(3)
    ruta = tmp_path / "grande.omnicad"
    proyecto.guardar(doc, ruta)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    _crash(monkeypatch)
    with pytest.raises(proyecto.ErrorProyecto, match="error nativo"):
        proyecto.abrir(ruta)


def test_hijo_real_abre_un_archivo_grande(monkeypatch, tmp_path):
    from omnicad.io_archivos import proyecto

    doc = _documento(3)
    ruta = tmp_path / "grande.omnicad"
    proyecto.guardar(doc, ruta)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    abierto = proyecto.abrir(ruta)
    assert len(abierto.operaciones) == 3
    assert _volumenes(abierto) == pytest.approx([30, 30, 30])


def test_ensayo_de_cota_calcula_la_misma_geometria_que_el_padre(monkeypatch):
    doc = Documento()
    boceto = Boceto()
    circulo = boceto.agregar_circulo((0, 0), 5)
    cota = boceto.agregar_cota("radio", [circulo], "5 mm")
    doc.agregar(OpBoceto("op1", boceto=boceto))
    doc.agregar(OpPrimitiva("op2", forma="caja", ancho="d1", largo="2", alto="5"))
    nueva = doc.operacion("op1").copia()
    nueva.boceto.cotas[cota].expresion = "10 mm"
    mediciones = []
    recalcular = Documento.recalcular

    def medir(self, desde=0):
        recalcular(self, desde)
        mediciones.append((self.parametros.valores()["d1"], _volumenes(self)))

    def ensayar(tarea, datos, tope, esperar=None):
        with monkeypatch.context() as m:
            m.setattr(aislado, "EN_HIJO", True)
            m.setattr(Documento, "recalcular", medir)
            return aislado._TAREAS_JSON[tarea](**datos)

    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "correr_json", ensayar)
    doc.reemplazar("op1", nueva)
    valor, volumenes = mediciones[-1]
    assert valor == doc.parametros.valores()["d1"] == 10
    assert volumenes == pytest.approx([100])
    assert _volumenes(doc) == pytest.approx(volumenes)
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())


def test_ensayo_de_borrado_quita_los_parametros_de_sus_cotas(monkeypatch):
    doc = Documento()
    boceto = Boceto()
    linea = boceto.agregar_linea((0, 0), (5, 0))
    boceto.agregar_cota("distancia", [linea], "5 mm")
    doc.agregar(OpBoceto("op1", boceto=boceto))
    valores = []
    recalcular = Documento.recalcular

    def medir(self, desde=0):
        recalcular(self, desde)
        valores.append(self.parametros.valores())

    def ensayar(tarea, datos, tope, esperar=None):
        with monkeypatch.context() as m:
            m.setattr(aislado, "EN_HIJO", True)
            m.setattr(Documento, "recalcular", medir)
            return aislado._TAREAS_JSON[tarea](**datos)

    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 1)
    monkeypatch.setattr(aislado, "correr_json", ensayar)
    doc.eliminar("op1")
    assert valores[-1] == doc.parametros.valores() == {}


@pytest.mark.parametrize("accion", ["suprimir", "reemplazar"])
def test_reactivar_el_paso_que_alcanza_el_umbral_se_ensaya(monkeypatch, accion):
    doc = _documento()
    doc.suprimir("op2")
    antes = _instantanea(doc)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    _crash(monkeypatch)
    with pytest.raises(ErrorDocumento, match="error nativo"):
        if accion == "suprimir":
            doc.suprimir("op2", False)
        else:
            doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    assert _instantanea(doc) == antes


def test_hijo_real_abre_una_ruta_relativa_desde_otra_carpeta(monkeypatch, tmp_path):
    from omnicad.io_archivos import proyecto

    proyecto.guardar(_documento(), tmp_path / "pieza grande.omnicad")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    abierto = proyecto.abrir("pieza grande.omnicad")
    assert _volumenes(abierto) == pytest.approx([30, 30])


@pytest.mark.parametrize("rechazar", [False, True])
def test_abrir_ensaya_antes_de_leer_geometria_cacheada(monkeypatch, tmp_path, rechazar):
    from omnicad.io_archivos import proyecto
    from omnicad.timeline import documento

    monkeypatch.setattr(documento, "_SEGUNDOS_CACHE", 0)
    ruta = proyecto.guardar(_documento(), tmp_path / "con_cache.omnicad")
    eventos = []
    correr = aislado.correr_json

    def ensayar(*args):
        eventos.append("ensayo")
        if rechazar:
            raise aislado.TareaAislada("caída simulada del hijo")
        return correr(*args)

    def leer_cache(*args):
        pytest.fail("La caché BREP se leyó en el padre en vez de usar el cálculo del hijo")

    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "correr_json", ensayar)
    monkeypatch.setattr(proyecto.intercambio, "partes_de_brep", leer_cache)
    if rechazar:
        with pytest.raises(proyecto.ErrorProyecto, match="caída simulada"):
            proyecto.abrir(ruta)
        assert eventos == ["ensayo"]
    else:
        abierto = proyecto.abrir(ruta)
        assert eventos == ["ensayo"]
        assert _volumenes(abierto) == pytest.approx([30, 30])
        assert all(geo.es_valida(c.forma) for c in abierto.estado_final.cuerpos.values())


@pytest.mark.parametrize("receta", [None, [], {"operaciones": None}, {"operaciones": 0},
                                    {"operaciones": {}}, {"operaciones": "pasos"}])
def test_abrir_receta_mal_formada_da_error_de_proyecto(tmp_path, receta):
    from omnicad.io_archivos import proyecto

    ruta = tmp_path / "danado.omnicad"
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("manifiesto.json", json.dumps({"formato": proyecto.FORMATO}))
        z.writestr("receta.json", json.dumps(receta))
    with pytest.raises(proyecto.ErrorProyecto, match="receta.*dañada"):
        proyecto.abrir(ruta)


def test_crash_en_previa_de_edicion_no_ejecuta_kernel_del_padre(monkeypatch):
    doc = _documento()
    nueva = _caja_ancha(doc.operacion("op2"))
    antes = _instantanea(doc)
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    _crash(monkeypatch)

    def no_calcular(*args):
        pytest.fail("La vista previa entró al kernel antes del ensayo")

    monkeypatch.setattr(OpPrimitiva, "calcular", no_calcular)
    with pytest.raises(ErrorDocumento, match="error nativo"):
        doc.previsualizar(nueva, 1)
    assert _instantanea(doc) == antes


def test_previa_y_aceptar_reusan_ensayo_solo_si_documento_y_candidato_son_iguales(monkeypatch):
    doc = _documento(3)
    nueva = _caja_ancha(doc.operacion("op2"))
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    correr, ensayos = aislado.correr_json, []

    def registrar(*args):
        salida = correr(*args)
        ensayos.append(salida)
        return salida

    monkeypatch.setattr(aislado, "correr_json", registrar)
    doc.previsualizar(nueva, 1)
    doc.previsualizar(nueva, 1)
    assert len(ensayos) == 1
    doc.parametros.modificar("altura", "4 mm")
    doc.previsualizar(nueva, 1)
    assert len(ensayos) == 2
    nueva.p["ancho"] = "6"
    doc.previsualizar(nueva, 1)
    assert len(ensayos) == 3
    doc.reemplazar("op2", nueva)
    assert len(ensayos) == 3
    assert _volumenes(doc) == pytest.approx([40, 120, 40])
    assert all(geo.es_valida(c.forma) for c in doc.estado_final.cuerpos.values())


def test_no_reusa_ensayo_si_hay_pasos_con_fuentes_externas(monkeypatch):
    doc = _documento()
    nueva = _caja_ancha(doc.operacion("op2"))
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    # Derivaciones y otras operaciones no memorizables pueden cambiar sin modificar la receta.
    monkeypatch.setattr(OpPrimitiva, "MEMORIZABLE", False)
    ensayos = []
    correr = aislado.correr_json

    def registrar(*args):
        ensayos.append(args[0])
        return correr(*args)

    monkeypatch.setattr(aislado, "correr_json", registrar)
    doc.previsualizar(nueva, 1)
    doc.previsualizar(nueva, 1)
    doc.reemplazar("op2", nueva)
    assert ensayos == ["prevuelo_cambio"] * 3


@pytest.mark.parametrize("estado_paso", ["suprimida", "retrocedida"])
def test_hijo_ensaya_la_previa_aunque_el_recalculo_omita_el_paso(monkeypatch, estado_paso):
    doc = _documento(3)
    if estado_paso == "suprimida":
        doc.suprimir("op3")
    else:
        doc.mover_marcador(2)
    nueva = _caja_ancha(doc.operacion("op3"))
    nueva.suprimida = doc.operacion("op3").suprimida
    calculados = []
    calcular = OpPrimitiva.calcular

    def registrar(self, estado, ctx):
        if aislado.EN_HIJO and self.p["ancho"] == "4":
            calculados.append(self.id)
        return calcular(self, estado, ctx)

    def ensayar(tarea, datos, tope, esperar=None):
        with monkeypatch.context() as m:
            m.setattr(aislado, "EN_HIJO", True)
            return aislado._TAREAS_JSON[tarea](**datos)

    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 2)
    monkeypatch.setattr(aislado, "correr_json", ensayar)
    monkeypatch.setattr(OpPrimitiva, "calcular", registrar)
    estado, _ = doc.previsualizar(nueva, 2)
    assert calculados == ["op3"]
    assert geo.volumen(estado.cuerpos["op3.c1"].forma) == pytest.approx(60)
