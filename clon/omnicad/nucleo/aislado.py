# -*- coding: utf-8 -*-
"""
Tareas del kernel que pueden no terminar nunca, corridas en un PROCESO APARTE con tope de tiempo.

OpenCascade no se corta desde Python: el análisis de autointersecciones (BOPAlgo_ArgumentAnalyzer) o la
eliminación exacta de líneas ocultas (HLRBRep_Algo) sobre una rosca modelada (caras B-spline helicoidales) pueden
tardar horas, y en la app congelan la ventana (prueba de tortura del 2026-10-17, T-01 y T-02). Acá la forma viaja
como BREP a un hijo que hace la cuenta; si pasa el tope se lo mata y la app sigue viva.

`correr(tarea, forma, tope, **args)` y `correr_json(tarea, datos, tope)` devuelven JSON o lanzan `TareaAislada`
(`TiempoAgotado` si pasó el tope). Sin Qt; solo el hijo de prevuelo importa timeline para reconstruir la receta.
En la app instalada el hijo es la misma `OmniCAD.exe --tarea-aislada`.

RS-X1: `correr_json` no arranca un hijo por cálculo. Un solo trabajador sigue vivo entre cálculos con el documento al
día y su memoria por paso (`_Trabajador`, `_trabajar`). No guarda nada que no se pueda rehacer: cada pedido trae la
receta completa, y si el hijo cae o se lo mata por tiempo, el siguiente pedido arranca otro desde esa receta.

RS-X6: las previas de `CalculoPendiente` también van a ese trabajador. Cancelar no lo mata (perdería el documento vivo):
se deja de esperar su respuesta y solo se lo cierra si no termina en `PACIENCIA_PREVIA`.
"""
import atexit
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from pathlib import Path

from . import intercambio
from . import motor as _motor

_RAIZ = Path(__file__).resolve().parents[2]      # la carpeta que contiene el paquete `omnicad`
_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
UMBRAL_PREVUELO_PARAMETROS = 60       # pasos no suprimidos anteriores al marcador
TOPE_PREVUELO_PARAMETROS = 900        # segundos, incluida la reconstrucción del documento
TOPE_PREVUELO_ABRIR = 900             # segundos para el ensayo de apertura de un archivo grande (B-48)
TOPE_MEMORIA_TRABAJADOR = 2048        # MB: pasado esto se cierra el trabajador al contestar (su memoria se libera con él)
PACIENCIA_PREVIA = 10                 # segundos para una previa vieja antes de cerrar al trabajador (rehacer el documento cuesta más)
EN_HIJO = False
# En el trabajador: el documento al día y lo que el padre ya tiene (id(objeto) → (número, huella, objeto); huella → número),
# que no se vuelve a mandar. `formas_enviadas` es None en un hijo de una sola tarea. Las mantiene `_codificar`.
documento_vivo = None
formas_enviadas = None
huellas_enviadas = {}
estados_enviados = []
marca_enviada = None
proxima_forma = 0
# En el padre: lo del último cálculo recibido (número → objeto) y su marca, que mantiene `_decodificar`. Si la marca no
# es la del trabajador (es otro, o nadie leyó su última respuesta), él vuelve a mandar todo.
formas_recibidas = {}
estados_recibidos = []
marca_recibida = None


class TareaAislada(Exception):
    """El hijo no pudo hacer la tarea (no arrancó, falló o devolvió basura)."""


class TiempoAgotado(TareaAislada):
    """El hijo pasó el tope y se lo mató."""


# ---------------------------------------------------------------- lo que corre el hijo
def _autointersecciones(forma, limite):
    from . import revision
    return revision._autointersecciones(forma, limite)


def _proyeccion_exacta(forma, e, x, deflexion):
    from . import dibujo
    return dibujo._hlr(forma, dibujo.Marco(e, x), "exacto", deflexion)


_TAREAS = {"autointersecciones": _autointersecciones, "proyeccion_exacta": _proyeccion_exacta}


def _documento(receta):
    """`receta` calculada. En el trabajador sale del documento vivo: se recalcula solo lo que cambió, y la memoria por
    paso reusa el resto. Lo que un paso no memorizable lee de afuera se vuelve a leer, como en un documento recién hecho."""
    global documento_vivo
    from ..timeline.documento import Documento

    if formas_enviadas is None:
        return Documento.desde_dict(receta)
    if documento_vivo is None:
        documento_vivo = Documento.desde_dict(receta)
        return documento_vivo
    if documento_vivo.a_dict() != receta:
        documento_vivo._cargar(receta)
    if not all(op.MEMORIZABLE for op in documento_vivo.operaciones):
        documento_vivo.recalcular(0)
    return documento_vivo


def _prevuelo_parametros(receta, parametros):
    from ..timeline.calculo_aislado import _empaquetar
    from ..timeline.parametros import TablaParametros

    with _motor.fijar_motor("opencascade"):
        doc = _documento(receta)
        doc.aplicar_parametros(TablaParametros.desde_lista(parametros))
        return _empaquetar(doc)


def _prevuelo_cambio(receta, cambio, previa=False):
    """Ensaya editar, suprimir o eliminar un paso (B-48): un cambio del historial también recalcula y podía
    tumbar el proceso con una caída nativa del kernel."""
    from ..timeline.calculo_aislado import _empaquetar
    from ..timeline.operaciones import operacion_desde_dict

    with _motor.fijar_motor("opencascade"):
        doc = _documento(receta)
        i = int(cambio["indice"])
        estado_previo = None
        if cambio["tipo"] in ("reemplazar", "agregar"):
            nueva = operacion_desde_dict(cambio["operacion"])
            if previa:
                estado, avisos = doc.previsualizar(nueva, cambio.get("indice_previa", i))
                estado_previo = {"estado": estado, "avisos": avisos, "usados": set(nueva._usados)}
            if cambio["tipo"] == "agregar":
                doc.mover_marcador(i)
                doc.agregar(nueva)
            else:
                doc.reemplazar(doc.operaciones[i].id, nueva)
        elif cambio["tipo"] == "suprimir":
            doc.suprimir(doc.operaciones[i].id, bool(cambio["suprimida"]))
        elif cambio["tipo"] == "eliminar":
            doc.eliminar(doc.operaciones[i].id)
        else:
            raise ValueError(f"Cambio desconocido: {cambio['tipo']}")
        return _empaquetar(doc, estado_previo)


def _prevuelo_abrir(ruta):
    """Ensaya abrir un proyecto grande (B-48): si el kernel cae al reconstruirlo, la app no lo abre y sigue viva."""
    global documento_vivo
    from ..io_archivos import proyecto
    from ..timeline.calculo_aislado import _empaquetar

    with _motor.fijar_motor("opencascade"):
        doc = proyecto.abrir(ruta)
        if formas_enviadas is not None:
            documento_vivo = doc
        return _empaquetar(doc)


def _recalcular_documento(receta, sin_memoria=False):
    """`sin_memoria`: «Calcular todo» ejecuta de verdad cada paso, también los que el trabajador tiene en memoria."""
    from ..timeline.calculo_aislado import _empaquetar

    with _motor.fijar_motor("opencascade"):
        doc = _documento(receta)
        if sin_memoria and formas_enviadas is not None:
            doc.olvidar_memoria()
            doc.recalcular(0)
        return _empaquetar(doc)


def _previa_visual(receta, operacion, indice, deflexion, angular):
    from ..timeline.calculo_aislado import previa_visual

    with _motor.fijar_motor("opencascade"):
        return previa_visual(receta, operacion, indice, deflexion, angular)


def _solape_herramienta(receta, operacion, indice, cuerpos):
    from ..timeline.calculo_aislado import solape_herramienta

    with _motor.fijar_motor("opencascade"):
        return solape_herramienta(receta, operacion, indice, cuerpos)


_TAREAS_JSON = {"prevuelo_parametros": _prevuelo_parametros, "prevuelo_cambio": _prevuelo_cambio,
                "prevuelo_abrir": _prevuelo_abrir, "recalcular_documento": _recalcular_documento,
                "previa_visual": _previa_visual, "solape_herramienta": _solape_herramienta}


def _a_json(o):
    if hasattr(o, "tolist"):
        return o.tolist()
    raise TypeError(f"{type(o).__name__} no se guarda como JSON")


def _memoria_mb():
    """Memoria residente de este proceso en MB (`/proc` en Linux; la API de Windows, sin dependencias). 0 sin `/proc`."""
    if sys.platform != "win32":
        try:
            with open("/proc/self/statm", encoding="ascii") as f:
                return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 2 ** 20
        except OSError:        # macOS: sin tope, antes que tumbar al trabajador en cada pedido
            return 0
    import ctypes
    from ctypes import wintypes

    class _Contadores(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t)] + [(f"_{i}", ctypes.c_size_t) for i in range(6)]

    k32 = ctypes.WinDLL("kernel32")
    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Contadores), wintypes.DWORD]
    c = _Contadores()
    c.cb = ctypes.sizeof(c)
    k32.K32GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return c.WorkingSetSize / 2 ** 20


def _motivo(e):
    """El texto que la persona ve de un error: el mismo de una previa en el proceso principal."""
    return str(e) or traceback.format_exception_only(e)[-1].strip()


def _atender(tarea, args):
    """Un pedido del trabajador. Un error (una previa con un valor imposible) no lo mata: vuelve como texto, y solo si
    el documento quedó a medias se descarta (el próximo pedido lo arma de la receta)."""
    global documento_vivo, formas_enviadas, huellas_enviadas
    if args.pop("_marca") != marca_enviada:
        formas_enviadas, huellas_enviadas = {}, {}
    os.chdir(args.pop("_cwd"))     # las rutas relativas del documento (derivaciones) valen desde el padre
    try:
        return _TAREAS_JSON[tarea](**args)
    except Exception as e:      # noqa: BLE001 — lo que falle en un pedido se informa y el trabajador sigue
        doc = documento_vivo
        if doc is not None and (doc.a_dict() != args.get("receta") or len(doc._estados) != len(doc.operaciones)):
            documento_vivo = None
        return {"_fallo": _motivo(e)}
    finally:
        os.chdir(_RAIZ)         # una carpeta tomada de directorio actual no se puede mover ni borrar en Windows
        if documento_vivo is not None:
            documento_vivo._deshacer.clear()
            documento_vivo._rehacer.clear()


def _trabajar(carpeta):
    """El bucle del trabajador: un pedido por línea de la entrada, hasta que el padre la cierra (también si muere).
    `args.json` trae el pedido; `listo` avisa que `salida.json` ya está completa."""
    global formas_enviadas
    formas_enviadas = {}
    for linea in os.fdopen(0, "rb"):
        args = json.loads((carpeta / "args.json").read_text(encoding="utf-8"))
        tope = args.pop("_tope_mb")
        salida = _atender(linea.decode("ascii").strip(), args)
        if _memoria_mb() > tope:
            salida["_cerrar"] = True     # lo cierra el padre: si se fuera solo, el próximo pedido lo encontraría saliendo
        (carpeta / "salida.json").write_text(json.dumps(salida, default=_a_json), encoding="utf-8", newline="\n")
        (carpeta / "listo").touch()
    return 0


def principal(argv):
    """Punto de entrada del hijo: `tarea carpeta`. Lee args.json y, si corresponde, forma.brep; escribe salida.json."""
    # Con «-m» este módulo es __main__; timeline importa la instancia con su nombre de paquete.
    from . import aislado
    aislado.EN_HIJO = True
    tarea, carpeta = argv[0], Path(argv[1])
    if tarea == "trabajador":
        return aislado._trabajar(carpeta)
    args = json.loads((carpeta / "args.json").read_text(encoding="utf-8"))
    if tarea in _TAREAS_JSON:
        os.chdir(args.pop("_cwd"))     # las rutas relativas del documento (derivaciones) valen desde el padre
        try:
            salida = _TAREAS_JSON[tarea](**args)
        except Exception as e:  # noqa: BLE001 — como en el trabajador: el motivo vuelve como texto
            salida = {"_fallo": _motivo(e)}
    else:
        forma = intercambio.leer_brep(carpeta / "forma.brep")
        salida = _TAREAS[tarea](forma, **args)
    (carpeta / "salida.json").write_text(json.dumps(salida, default=_a_json), encoding="utf-8", newline="\n")
    return 0


# ---------------------------------------------------------------- lo que llama la app
def _comando(tarea, carpeta):
    if getattr(sys, "frozen", False):            # app instalada: no hay «python -m»; OmniCAD.py atiende el flag
        # También se llama desde omnicad-cli / omnicad-mcp, que no atienden ese flag.
        app = Path(sys.executable).with_name("OmniCAD.exe" if sys.platform == "win32" else "OmniCAD")
        return [str(app), "--tarea-aislada", tarea, str(carpeta)]
    return [sys.executable, "-m", "omnicad.nucleo.aislado", tarea, str(carpeta)]


def correr(tarea, forma, tope, **args):
    """Hace `tarea` sobre `forma` en un proceso aparte y devuelve su resultado. `tope`: segundos como máximo."""
    if tarea not in _TAREAS:
        raise ValueError(f"Tarea aislada desconocida: {tarea}")
    return _correr(tarea, tope, args, forma)


def correr_json(tarea, datos, tope, esperar=None):
    """Hace `tarea` en el trabajador con argumentos JSON (`datos`), sin BREP. `tope`: segundos como máximo.
    `esperar(segundos)`: la ventana la usa para avisar y repintar mientras el hijo trabaja (B-48)."""
    if tarea not in _TAREAS_JSON:
        raise ValueError(f"Tarea aislada desconocida: {tarea}")
    datos = dict(datos, _cwd=os.getcwd())
    if _ocupado.acquire(blocking=False):
        try:
            _esperar_previa_cancelada(esperar)
            if _previa_en_curso is None:
                return _pedir(tarea, dict(datos, _marca=marca_recibida, _tope_mb=TOPE_MEMORIA_TRABAJADOR), tope, esperar)
        finally:
            _ocupado.release()
    return _correr(tarea, tope, datos, esperar=esperar)     # otro hilo, documento o previa lo usa: un hijo de una sola tarea


class _Trabajador:
    """El hijo que queda vivo entre cálculos (RS-X1). Si cae, se cuelga o pasa el tope, se lo cierra y se informa como
    en una tarea de una sola vez: el documento del padre no se toca y el pedido siguiente arranca otro."""

    def __init__(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="omnicad_trabajador_", ignore_cleanup_errors=True)
        self.carpeta = Path(self.temporal.name)
        self.proceso = None
        try:
            self.errores = (self.carpeta / "errores.txt").open("wb")
            self.proceso = subprocess.Popen(_comando("trabajador", self.carpeta), bufsize=0, cwd=_RAIZ,
                                            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self.errores,
                                            creationflags=_SIN_VENTANA)
        except (OSError, ValueError) as e:
            self.cerrar()
            raise TareaAislada(f"no pudo arrancar el proceso aparte ({e})") from e

    def _avisar(self, tarea):
        try:
            self.proceso.stdin.write(tarea.encode("ascii") + b"\n")
        except OSError:                  # ya cayó: lo informa la espera
            pass

    def enviar(self, tarea, datos):
        (self.carpeta / "args.json").write_text(json.dumps(datos, default=_a_json), encoding="utf-8", newline="\n")
        self._avisar(tarea)

    def termino(self):
        return (self.carpeta / "listo").is_file() or self.proceso.poll() is not None

    def pedir(self, tarea, datos, tope, esperar):
        self.enviar(tarea, datos)
        inicio = aviso = time.monotonic()
        while not self.termino():
            ahora = time.monotonic()
            if ahora - inicio > tope:
                self.cerrar()
                raise TiempoAgotado(f"pasó de {tope:.3g} s y se cortó".replace(".", ","))
            if esperar is not None and ahora - aviso >= 0.05:
                aviso = ahora
                esperar(ahora - inicio)
            time.sleep(0.001)
        if esperar is not None:
            esperar(time.monotonic() - inicio)
        resultado = self.recoger()
        if "_fallo" in resultado:
            raise TareaAislada(f"el proceso aparte falló ({resultado['_fallo']})")
        return resultado

    def recoger(self):
        """La respuesta del pedido que ya terminó."""
        listo, salida = self.carpeta / "listo", self.carpeta / "salida.json"
        if not listo.is_file() and (self.proceso.returncode != 0 or not salida.is_file()):
            codigo = self.proceso.returncode
            self.errores.close()
            ultima = (self.carpeta / "errores.txt").read_bytes()
            self.cerrar()
            raise _caida(codigo, ultima)
        try:
            resultado = json.loads(salida.read_text(encoding="utf-8"))
            salida.unlink()
            listo.unlink(missing_ok=True)
        except (OSError, ValueError) as e:
            self.cerrar()
            raise TareaAislada(f"el proceso aparte dejó un resultado ilegible ({e})") from e
        if resultado.get("_cerrar"):
            self.cerrar()
        return resultado

    def cerrar(self):
        if self.proceso is not None and self.proceso.poll() is None:
            self.proceso.kill()
            self.proceso.wait()
        if self.proceso is not None:
            self.proceso.stdin.close()
        if hasattr(self, "errores"):
            self.errores.close()
        self.temporal.cleanup()


_trabajador = None
_ocupado = threading.Lock()
_previa_en_curso = None             # la CalculoPendiente que el trabajador está atendiendo


def cerrar_trabajador():
    """Cierra el trabajador y suelta lo que este proceso guardaba de sus respuestas."""
    global _trabajador, formas_recibidas, estados_recibidos, marca_recibida, _previa_en_curso
    _previa_en_curso = None
    if _trabajador is not None:
        _trabajador.cerrar()
        _trabajador = None
    formas_recibidas, estados_recibidos, marca_recibida = {}, [], None


atexit.register(cerrar_trabajador)


def _trabajador_vivo():
    global _trabajador
    if _trabajador is None or _trabajador.proceso.poll() is not None:
        cerrar_trabajador()
        _trabajador = _Trabajador()
    return _trabajador


def _pedir(tarea, datos, tope, esperar):
    try:
        return _trabajador_vivo().pedir(tarea, datos, tope, esperar)
    except TareaAislada:
        raise
    except BaseException:            # quedó con un pedido a medias: no sirve para el próximo
        cerrar_trabajador()
        raise


def _soltar_previa(matar=False):
    """Con `_ocupado` tomado: si la previa en curso se canceló y terminó, tira su respuesta. Con `matar`, si no terminó,
    cierra al trabajador."""
    global _previa_en_curso
    previa = _previa_en_curso
    if previa is None or previa.limite is None:
        return
    if previa.trabajador.termino():
        _previa_en_curso = None
        try:
            previa.trabajador.recoger()
        except (TareaAislada, OSError):        # el error de una previa cancelada no le importa a nadie
            pass
    elif matar:
        cerrar_trabajador()


def _vencio_previa(previa):
    with _ocupado:
        if _previa_en_curso is previa:
            _soltar_previa(matar=True)


def _esperar_previa_cancelada(esperar):
    """Con `_ocupado` tomado: aceptar en plena previa no pierde el documento vivo, le da tiempo a terminar."""
    inicio = time.monotonic()
    while _previa_en_curso is not None and _previa_en_curso.limite is not None:
        _soltar_previa(matar=time.monotonic() > _previa_en_curso.limite)
        if esperar is not None:
            esperar(time.monotonic() - inicio)
        time.sleep(0.02)


class CalculoPendiente:
    """Una previa en proceso aparte: sondear no espera al kernel. La atiende el trabajador con su documento vivo; si otra
    previa lo ocupa, un hijo de una sola tarea, que cancelar mata. Detrás de una previa cancelada, espera su turno."""

    def __init__(self, tarea, datos, tope=TOPE_PREVUELO_PARAMETROS):
        if tarea not in _TAREAS_JSON:
            raise ValueError(f"Tarea aislada desconocida: {tarea}")
        self.tarea, self.datos = tarea, dict(datos, _cwd=os.getcwd())
        self.inicio, self.tope = time.monotonic(), tope
        self.proceso = self.trabajador = self.temporal = self.limite = None
        try:
            previa = _previa_en_curso
            if not self._al_trabajador() and (previa is None or previa.limite is None):
                self._arrancar_hijo()
        except (OSError, TypeError, ValueError) as e:
            self.cancelar()
            raise TareaAislada(f"No pude iniciar la vista previa aparte ({e}).") from e

    def _al_trabajador(self):
        global _previa_en_curso
        if not _ocupado.acquire(blocking=False):
            return False
        try:
            _soltar_previa()
            if _previa_en_curso is not None:
                return False
            t = _trabajador_vivo()
            t.enviar(self.tarea, dict(self.datos, _marca=marca_recibida, _tope_mb=TOPE_MEMORIA_TRABAJADOR))
            self.trabajador, self.proceso, _previa_en_curso = t, t.proceso, self
            return True
        finally:
            _ocupado.release()

    def _arrancar_hijo(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="omnicad_previa_", ignore_cleanup_errors=True)
        self.carpeta = Path(self.temporal.name)
        (self.carpeta / "args.json").write_text(json.dumps(self.datos, default=_a_json), encoding="utf-8", newline="\n")
        self.errores = (self.carpeta / "errores.txt").open("wb")
        self.proceso = subprocess.Popen(_comando(self.tarea, self.carpeta), cwd=_RAIZ, stdout=subprocess.DEVNULL,
                                        stderr=self.errores, creationflags=_SIN_VENTANA |
                                        getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))

    def _termino(self):
        if self.proceso is None and not self._al_trabajador():
            return False
        return self.proceso.poll() is not None if self.trabajador is None else self.trabajador.termino()

    def sondear(self):
        """None mientras calcula; devuelve el JSON terminado o informa el fallo sin tocar el documento."""
        global _previa_en_curso
        if not self._termino():
            if time.monotonic() - self.inicio > self.tope:
                self.cancelar(ya=True)
                raise TiempoAgotado("La vista previa pasó su plazo y se cortó.")
            return None
        try:
            if self.trabajador is not None:
                if _previa_en_curso is self:
                    _previa_en_curso = None
                resultado = self.trabajador.recoger()
            else:
                self.errores.close()
                if self.proceso.returncode:
                    raise _caida(self.proceso.returncode, (self.carpeta / "errores.txt").read_bytes())
                resultado = json.loads((self.carpeta / "salida.json").read_text(encoding="utf-8"))
        except TareaAislada as e:
            raise TareaAislada(f"No se pudo calcular la vista previa: {e}.") from e
        except (OSError, ValueError) as e:
            raise TareaAislada(f"La vista previa dejó un resultado ilegible ({e}).") from e
        finally:
            self.cancelar()
        if "_fallo" in resultado:
            raise TareaAislada(resultado["_fallo"])
        return resultado

    def cancelar(self, ya=False):
        """Deja de esperarla. En el trabajador sigue corriendo y se le da tiempo a terminar; con `ya`, se lo cierra."""
        if self.trabajador is not None:
            if _previa_en_curso is self and ya:
                cerrar_trabajador()
            elif _previa_en_curso is self and self.limite is None:
                self.limite = time.monotonic() + PACIENCIA_PREVIA
                reloj = threading.Timer(PACIENCIA_PREVIA, _vencio_previa, (self,))
                reloj.daemon = True
                reloj.start()
            return
        if self.proceso is not None and self.proceso.poll() is None:
            self.proceso.kill()
            self.proceso.wait()
        if hasattr(self, "errores"):
            self.errores.close()
        if self.temporal is not None:
            self.temporal.cleanup()


def _ejecutar(comando, tope, esperar):
    """`subprocess.run`; con `esperar` corre en un hilo y el que llama la invoca cada 50 ms (sin Qt acá)."""
    def correr():
        return subprocess.run(comando, cwd=_RAIZ, capture_output=True, timeout=tope,
                              creationflags=_SIN_VENTANA, check=False)

    if esperar is None:
        return correr()
    salida = []

    def trabajo():
        try:
            salida.append(correr())
        except BaseException as e:      # se relanza en el hilo que espera
            salida.append(e)

    hilo, inicio = threading.Thread(target=trabajo, daemon=True), time.monotonic()
    hilo.start()
    while hilo.is_alive():
        hilo.join(0.05)
        esperar(time.monotonic() - inicio)
    if isinstance(salida[0], BaseException):
        raise salida[0]
    return salida[0]


def _caida(codigo, errores):
    """La excepción de un hijo que terminó sin resultado. `errores`: lo que dejó en stderr."""
    if codigo < 0 or codigo >= 0x80000000:
        # B-48: caída nativa del kernel (p. ej. 0xC0000005 en TKernel). Acá llega como error en español
        # y la app sigue viva; sin el proceso aparte mataba a todo el programa.
        return TareaAislada(f"el kernel cayó por un error nativo (código {codigo:#x}) dentro "
                            "del proceso aparte; OmniCAD sigue andando")
    ultima = (errores or b"").decode("utf-8", "replace").strip().splitlines()[-1:] or ["sin detalle"]
    return TareaAislada(f"el proceso aparte falló ({ultima[0][:200]})")


def _correr(tarea, tope, args, forma=None, esperar=None):
    if tope <= 0:
        raise TiempoAgotado("no quedó tiempo para correrla")
    if forma is not None and _motor.motor_activo() == "omnikernel":
        # Sin subproceso ni BREP: cada llamada al kernel nativo lleva su CancelToken con plazo (binding omnikernel_py).
        # Las tareas de hoy son de OpenCascade: su despacho informa MOTOR_SIN_SOPORTE en vez de tapar el error.
        return json.loads(json.dumps(_TAREAS[tarea](forma, **args), default=_a_json))
    with tempfile.TemporaryDirectory(prefix="omnicad_tarea_", ignore_cleanup_errors=True) as tmp:   # en Windows el hijo
        # recién muerto puede tardar en soltar el archivo: borrar la carpeta no tiene que tumbar la revisión
        carpeta = Path(tmp)
        try:
            if forma is not None:
                intercambio.escribir_brep(forma, carpeta / "forma.brep")
            (carpeta / "args.json").write_text(json.dumps(args, default=_a_json), encoding="utf-8", newline="\n")
            hijo = _ejecutar(_comando(tarea, carpeta), tope, esperar)
        except subprocess.TimeoutExpired:         # run() ya mató al hijo
            raise TiempoAgotado(f"pasó de {tope:.3g} s y se cortó".replace(".", ",")) from None
        except (OSError, TypeError, ValueError, intercambio.ErrorGeometria) as e:
            raise TareaAislada(f"no pudo arrancar el proceso aparte ({e})") from e
        salida = carpeta / "salida.json"
        if hijo.returncode != 0 or not salida.is_file():
            raise _caida(hijo.returncode, hijo.stderr)
        try:
            resultado = json.loads(salida.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise TareaAislada(f"el proceso aparte dejó un resultado ilegible ({e})") from e
        if "_fallo" in resultado:
            raise TareaAislada(f"el proceso aparte falló ({resultado['_fallo']})")
        return resultado


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
