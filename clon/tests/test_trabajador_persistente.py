# -*- coding: utf-8 -*-
"""RS-X1: el trabajador persistente conserva la memoria por paso entre ediciones y da lo mismo que recalcular todo."""
import json
import os
import sys
import time

import pytest

from omnicad.io_archivos import proyecto
from omnicad.nucleo import aislado, motor
from omnicad.nucleo import geometria as geo
from omnicad.timeline.documento import Documento, ErrorDocumento
from omnicad.timeline.operaciones import OpPrimitiva, operacion_desde_dict
from test_b48_prevuelo import _caja_ancha, _documento, _instantanea, _tabla


@pytest.fixture(autouse=True)
def opencascade(monkeypatch):
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 3)
    with motor.fijar_motor("opencascade"):
        yield


def _medidas(doc):
    return {cid: (geo.volumen(c.forma), geo.caja_envolvente(c.forma), geo.es_valida(c.forma))
            for cid, c in doc.estado_final.cuerpos.items()}


def _igual_a_recalcular_todo(doc):
    """Compara contra el mismo documento recalculado de cero en este proceso, sin hijo ni memoria."""
    aparte = aislado.EN_HIJO
    aislado.EN_HIJO = True
    try:
        limpio = Documento.desde_dict(json.loads(json.dumps(doc.a_dict())))
    finally:
        aislado.EN_HIJO = aparte
    a, b = _medidas(doc), _medidas(limpio)
    assert list(a) == list(b)
    for cid in a:
        assert a[cid][0] == pytest.approx(b[cid][0], rel=1e-9)
        assert sum(a[cid][1], ()) == pytest.approx(sum(b[cid][1], ()), rel=1e-6, abs=1e-6)
        assert a[cid][2] is b[cid][2] is True
    assert [r.estado for r in doc.resultados] == [r.estado for r in limpio.resultados]
    for estado, referencia in zip(doc._estados, limpio._estados, strict=True):      # también los que no viajaron
        assert list(estado.cuerpos) == list(referencia.cuerpos)
        for cid, c in estado.cuerpos.items():
            assert geo.volumen(c.forma) == pytest.approx(geo.volumen(referencia.cuerpos[cid].forma), rel=1e-9)
    assert doc.parametros.valores() == limpio.parametros.valores()
    return a


def _pid():
    return aislado._trabajador.proceso.pid


def test_el_mismo_trabajador_atiende_todas_las_ediciones_y_viajan_solo_las_formas_nuevas(monkeypatch):
    doc = _documento(5)
    op = doc.operacion("op2")
    enviados = []
    correr = aislado.correr_json

    def registrar(*args):
        salida = correr(*args)
        enviados.append(len(salida["calculo"].get("brep") or ""))
        return salida

    monkeypatch.setattr(aislado, "correr_json", registrar)
    doc.reemplazar(op.id, _caja_ancha(op))
    pid = _pid()
    doc.suprimir("op5")
    doc.reemplazar("op4", _caja_ancha(doc.operacion("op4")))
    doc.deshacer()
    assert _pid() == pid
    assert enviados[1] == 0            # suprimir el último no crea formas: el padre ya tiene todas
    assert 0 < enviados[2] < 1.5 * enviados[0]      # una sola forma, no las cinco
    _igual_a_recalcular_todo(doc)


def test_una_edicion_vieja_despues_de_una_nueva_no_vuelve_a_mandar_lo_que_el_padre_tiene(monkeypatch):
    """Una edición del final no manda los estados de antes: sus formas siguen en las dos tablas para la edición siguiente."""
    doc = _documento(6)
    enviados = []
    correr = aislado.correr_json

    def registrar(*args):
        salida = correr(*args)
        enviados.append((salida["calculo"]["brep"], salida["calculo"]["parcial"]))
        return salida

    monkeypatch.setattr(aislado, "correr_json", registrar)
    doc.reemplazar("op6", _caja_ancha(doc.operacion("op6")))
    primera = doc.estado_final.cuerpos["op1.c1"].forma
    doc.reemplazar("op3", _caja_ancha(doc.operacion("op3")))
    assert doc.estado_final.cuerpos["op1.c1"].forma is primera
    assert all(parcial for _, parcial in enviados)
    _igual_a_recalcular_todo(doc)


def test_un_renombre_no_recalcula_los_pasos_de_otros_cuerpos():
    """Antes un solo renombre (también `name=` al crear un cuerpo) invalidaba la memoria de todo el historial."""
    aislado.EN_HIJO, aparte = True, aislado.EN_HIJO
    try:
        doc = _documento(4)
        calculados = []
        calcular = OpPrimitiva.calcular

        def registrar(self, estado, ctx):
            calculados.append(self.id)
            return calcular(self, estado, ctx)

        OpPrimitiva.calcular = registrar
        try:
            doc.set_propiedad(["op2.c1"], "nombre", "Placa")
            doc.recalcular(0)
            assert calculados == []
            doc.reemplazar("op4", _caja_ancha(doc.operacion("op4")))
            assert calculados == ["op4"]
            calculados.clear()
            doc.set_propiedad(["op2.c1"], "nombre", None)         # quitarlo: vuelve el nombre que puso la operación
            assert doc.estado_final.cuerpos["op2.c1"].nombre != "Placa"
            assert calculados == ["op2"]
        finally:
            OpPrimitiva.calcular = calcular
    finally:
        aislado.EN_HIJO = aparte


def test_lo_que_no_cambio_conserva_la_misma_forma_en_el_padre():
    """La memoria del trabajador se nota en el padre: los cuerpos que no cambiaron son los mismos objetos."""
    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    antes = doc.estado_final.cuerpos
    doc.reemplazar("op4", _caja_ancha(doc.operacion("op4")))
    despues = doc.estado_final.cuerpos
    assert despues["op1.c1"].forma is antes["op1.c1"].forma
    assert despues["op5.c1"].forma is antes["op5.c1"].forma
    assert despues["op4.c1"].forma is not antes["op4.c1"].forma


@pytest.mark.parametrize("accion", ["parametros", "editar", "suprimir", "eliminar", "agregar", "marcador", "mover",
                                    "deshacer", "rehacer"])
def test_cada_cambio_da_lo_mismo_que_recalcular_todo(accion):
    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))       # el trabajador ya está caliente
    if accion == "parametros":
        doc.aplicar_parametros(_tabla(doc))
    elif accion == "editar":
        doc.reemplazar("op4", _caja_ancha(doc.operacion("op4")))
    elif accion == "suprimir":
        doc.suprimir("op3")
    elif accion == "eliminar":
        doc.eliminar("op3")
    elif accion == "agregar":
        doc.agregar(OpPrimitiva(doc.nuevo_id(), forma="caja", ancho="9", largo="5", alto="altura"))
    elif accion == "marcador":
        doc.mover_marcador(3)
    elif accion == "mover":
        doc.mover("op5", 0)
    elif accion == "deshacer":
        doc.deshacer()
    else:
        doc.deshacer()
        doc.rehacer()
    _igual_a_recalcular_todo(doc)


def test_caida_del_trabajador_no_pierde_el_documento_y_el_siguiente_arranca_otro():
    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    pid, antes = _pid(), _instantanea(doc)
    aislado._trabajador.proceso.kill()
    aislado._trabajador.proceso.wait()
    # Murió entre dos pedidos: el próximo cálculo arranca otro y sale igual que recalcular todo.
    doc.reemplazar("op3", _caja_ancha(doc.operacion("op3")))
    assert _pid() != pid
    assert doc.a_dict() != antes[0]
    medidas = _igual_a_recalcular_todo(doc)
    assert medidas["op3.c1"][0] == pytest.approx(60)


def test_caida_a_mitad_de_un_calculo_informa_y_conserva_todo(monkeypatch):
    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    pid, antes, estados = _pid(), _instantanea(doc), list(doc._estados)
    original = aislado._Trabajador._avisar

    def caer_al_pedir(self, tarea):
        original(self, tarea)
        self.proceso.kill()

    monkeypatch.setattr(aislado._Trabajador, "_avisar", caer_al_pedir)
    with pytest.raises(ErrorDocumento, match="sigue andando"):
        doc.reemplazar("op3", _caja_ancha(doc.operacion("op3")))
    assert _instantanea(doc) == antes and doc._estados == estados
    monkeypatch.undo()
    monkeypatch.setattr(aislado, "UMBRAL_PREVUELO_PARAMETROS", 3)
    doc.reemplazar("op3", _caja_ancha(doc.operacion("op3")))
    assert _pid() != pid
    _igual_a_recalcular_todo(doc)


@pytest.mark.skipif(sys.platform != "win32", reason="el código de salida de una caída nativa es de Windows")
def test_caida_nativa_del_trabajador_vivo_da_el_mensaje_de_b48(monkeypatch):
    import ctypes

    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    antes = _instantanea(doc)
    terminar = ctypes.WinDLL("kernel32").TerminateProcess
    terminar.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    monkeypatch.setattr(aislado._Trabajador, "_avisar",
                        lambda self, tarea: terminar(int(self.proceso._handle), 0xC0000005))
    with pytest.raises(ErrorDocumento, match="error nativo.*0xc0000005"):
        doc.reemplazar("op3", _caja_ancha(doc.operacion("op3")))
    assert _instantanea(doc) == antes


def test_calculo_colgado_se_corta_y_el_documento_sigue(monkeypatch):
    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    pid, antes = _pid(), _instantanea(doc)
    original = aislado._Trabajador._avisar
    monkeypatch.setattr(aislado._Trabajador, "_avisar", lambda self, tarea: None)      # el hijo nunca contesta
    monkeypatch.setattr(aislado, "TOPE_PREVUELO_PARAMETROS", 0.2)
    with pytest.raises(ErrorDocumento, match="se cortó"):
        doc.reemplazar("op3", _caja_ancha(doc.operacion("op3")))
    assert _instantanea(doc) == antes
    monkeypatch.setattr(aislado._Trabajador, "_avisar", original)
    monkeypatch.setattr(aislado, "TOPE_PREVUELO_PARAMETROS", 900)
    doc.reemplazar("op3", _caja_ancha(doc.operacion("op3")))
    assert _pid() != pid
    _igual_a_recalcular_todo(doc)


def test_un_error_de_la_previa_no_mata_al_trabajador():
    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    pid, antes = _pid(), _instantanea(doc)
    mala = operacion_desde_dict(dict(doc.operacion("op3").a_dict()))
    mala.p["ancho"] = "no_existe"
    with pytest.raises(ErrorDocumento, match="falló"):
        doc.previsualizar(mala, 2)
    assert _pid() == pid and _instantanea(doc) == antes
    doc.reemplazar("op3", _caja_ancha(doc.operacion("op3")))
    assert _pid() == pid
    _igual_a_recalcular_todo(doc)


def test_previa_rechazada_no_deja_al_trabajador_adelantado():
    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    doc.previsualizar(_caja_ancha(doc.operacion("op3")), 2)     # Esc: el padre no aplica nada
    doc.reemplazar("op4", _caja_ancha(doc.operacion("op4")))
    medidas = _igual_a_recalcular_todo(doc)
    assert medidas["op3.c1"][0] == pytest.approx(30)


def test_si_el_padre_no_leyo_una_respuesta_el_trabajador_vuelve_a_mandar_todo():
    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    # Una respuesta que nadie decodifica deja al padre con la marca anterior.
    tabla = _tabla(doc)
    aislado.correr_json("prevuelo_parametros", {"receta": doc.a_dict(), "parametros": tabla.a_lista()}, 60)
    doc.aplicar_parametros(tabla)
    assert list(_igual_a_recalcular_todo(doc).values())[0][0] == pytest.approx(70)


def test_calcular_todo_ejecuta_de_verdad_aunque_la_memoria_del_trabajador_este_llena():
    """«Calcular todo» (Compute All) no contesta con la memoria: la duración de cada paso es la de un cálculo nuevo."""
    doc = _documento(5)
    doc.recalcular()
    duraciones = list(doc._duraciones)
    doc.recalcular()
    assert doc._duraciones == duraciones              # con memoria, el paso guarda lo que tardó aquella vez
    doc.olvidar_memoria()
    doc.recalcular()
    assert not set(doc._duraciones) & set(duraciones)
    assert not doc._calcular_todo
    duraciones = list(doc._duraciones)
    doc.recalcular()                                  # se pide una sola vez
    assert doc._duraciones == duraciones
    _igual_a_recalcular_todo(doc)


def test_el_directorio_del_padre_no_queda_tomado_por_el_trabajador(tmp_path, monkeypatch):
    """En Windows una carpeta no se puede borrar ni renombrar mientras un proceso la tenga de directorio actual."""
    monkeypatch.chdir(tmp_path)
    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    monkeypatch.chdir(aislado._RAIZ)
    os.rename(tmp_path, tmp_path.with_name(tmp_path.name + "_movida"))
    os.rename(tmp_path.with_name(tmp_path.name + "_movida"), tmp_path)


def test_abrir_deja_el_documento_listo_en_el_trabajador(tmp_path):
    doc = _documento(5)
    ruta = proyecto.guardar(doc, tmp_path / "grande.omnicad", incluir_cache=False)
    abierto = proyecto.abrir(ruta)
    pid = _pid()
    abierto.reemplazar("op3", _caja_ancha(abierto.operacion("op3")))
    assert _pid() == pid
    _igual_a_recalcular_todo(abierto)


def test_pasado_el_tope_de_memoria_responde_y_se_reinicia(monkeypatch):
    """Tope de memoria: el trabajador contesta, el padre lo cierra y el próximo cálculo arranca limpio."""
    monkeypatch.setattr(aislado, "TOPE_MEMORIA_TRABAJADOR", 1)
    doc = _documento(5)
    doc.reemplazar("op2", _caja_ancha(doc.operacion("op2")))
    proceso = aislado._trabajador.proceso
    assert proceso.poll() is not None
    doc.reemplazar("op3", _caja_ancha(doc.operacion("op3")))
    assert aislado._trabajador.proceso is not proceso
    _igual_a_recalcular_todo(doc)


def test_sin_proc_la_memoria_da_cero_y_no_tumba_al_trabajador(monkeypatch):
    assert aislado._memoria_mb() > 0
    monkeypatch.setattr(aislado.sys, "platform", "darwin")
    monkeypatch.setattr("builtins.open", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError(a[0])))
    assert aislado._memoria_mb() == 0


def test_otro_documento_en_el_mismo_trabajador_no_se_mezcla():
    a = _documento(5)
    a.reemplazar("op2", _caja_ancha(a.operacion("op2")))
    b = Documento()
    b.parametros.agregar("altura", "11 mm")
    for i in range(4):
        b.agregar(OpPrimitiva(b.nuevo_id(), forma="esfera", radio="3", x=str(i * 9)))
    b.reemplazar("op2", OpPrimitiva("op2", forma="esfera", radio="4", x="9"))
    _igual_a_recalcular_todo(b)
    a.reemplazar("op3", _caja_ancha(a.operacion("op3")))
    _igual_a_recalcular_todo(a)


def test_el_trabajador_termina_cuando_muere_el_padre():
    import subprocess

    codigo = (
        "import os, sys\n"
        "from omnicad.nucleo import aislado\n"
        "from omnicad.timeline.documento import Documento\n"
        "from omnicad.timeline.operaciones import OpPrimitiva\n"
        "aislado.UMBRAL_PREVUELO_PARAMETROS = 1\n"
        "d = Documento()\n"
        "d.agregar(OpPrimitiva(d.nuevo_id(), forma='caja'))\n"
        "print(aislado._trabajador.proceso.pid, flush=True)\n"
        "os._exit(0)\n")
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=aislado._RAIZ, capture_output=True, text=True, timeout=60,
                            encoding="utf-8")
    pid = int(salida.stdout.split()[-1])
    assert _espera_que_muera(pid)


def _espera_que_muera(pid, plazo=15):
    fin = time.monotonic() + plazo
    while time.monotonic() < fin:
        if not _vive(pid):
            return True
        time.sleep(0.1)
    return False


def _vive(pid):
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
    import ctypes
    k = ctypes.WinDLL("kernel32")
    k.OpenProcess.restype = ctypes.c_void_p
    h = k.OpenProcess(0x1000, False, pid)
    if not h:
        return False
    codigo = ctypes.c_ulong()
    k.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    k.GetExitCodeProcess(h, ctypes.byref(codigo))
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    k.CloseHandle(h)
    return codigo.value == 259
