# -*- coding: utf-8 -*-
"""
Cliente del puente con Fusion 360: abre un .f3d/.f3z pidiéndole a Fusion (instalado en la PC) que lo convierta.

El .f3d guarda los cuerpos en formato ShapeManager de Autodesk, que es cerrado: no se puede leer directo.
El complemento propio `omnicad/integraciones/fusion/OmniCADPuente` (escrito desde cero con la API pública de
Fusion; lo instala `omnicad setup --cliente fusion --aplicar`) corre dentro de Fusion, escucha pedidos en
127.0.0.1 y deja su puerto y una clave en `puente_fusion.json` (la misma carpeta que `puente.json`).

Protocolo (HTTP + JSON, cabecera `X-OmniCAD-Token`):
  GET  /estado     → {"ok", "version", "fusion"}
  POST /convertir  {"ruta"} → {"ok", "step", "documento", "parametros": [{nombre, expresion, unidad, valor,
                   comentario}], "cuerpos": [{nombre, componente, volumen_mm3, caja_mm, visible}],
                   "componentes": [nombres]} o {"ok": false, "mensaje"}.
`step` es un archivo temporal que escribe Fusion: se lee y se borra acá.

Sin Qt: lo usan la ventana, la API, la CLI y el MCP.
"""
import json
import os
import shutil
import urllib.error
import urllib.request
from pathlib import Path

from .. import carpeta_datos

VERSION_PROTOCOLO = 1
EXTENSIONES = (".f3d", ".f3z")
VARIABLE_CARPETA = "OMNICAD_PUENTE_FUSION_DIR"
TIEMPO_ESTADO_S = 5
TIEMPO_CONVERTIR_S = 600        # un ensamblaje grande puede tardar minutos en abrirse en Fusion

PASOS_A_MANO = ("Para abrirlo a mano: 1) abrí el archivo en Fusion; 2) Archivo › Exportar…, tipo «STEP (*.step)»; "
                "3) en OmniCAD, Archivo › Abrir y elegí ese .step (conserva nombres, colores y componentes; los "
                "parámetros no viajan en el STEP).")
COMO_ACTIVAR = ("Para que OmniCAD lo haga solo: instalá el complemento con «omnicad setup --cliente fusion --aplicar», "
                "abrí Fusion y verificá en Utilidades › Complementos (Mayús+S) que «OmniCADPuente» esté en ejecución.")


class ErrorPuenteFusion(RuntimeError):
    """El puente no está disponible o la conversión falló. `motivo`: "sin_puente" | "conversion"."""

    def __init__(self, mensaje, motivo="conversion"):
        super().__init__(mensaje)
        self.motivo = motivo


def carpeta_info():
    """Carpeta de `puente_fusion.json`: OMNICAD_PUENTE_FUSION_DIR o %LOCALAPPDATA%/OmniCAD (la del complemento)."""
    propia = os.environ.get(VARIABLE_CARPETA)
    if propia:
        return Path(propia)
    return carpeta_datos()


def ruta_info():
    return carpeta_info() / "puente_fusion.json"


def leer_info():
    """{puerto, token, pid, version} del complemento en ejecución, o None."""
    try:
        datos = json.loads(ruta_info().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(datos, dict) or not isinstance(datos.get("puerto"), int) or not datos.get("token"):
        return None
    return datos


def _sin_puente(detalle):
    return ErrorPuenteFusion(f"No se pudo hablar con Fusion 360: {detalle}\n\n{COMO_ACTIVAR}\n\n{PASOS_A_MANO}", "sin_puente")


def _pedir(info, metodo, camino, datos=None, tiempo=TIEMPO_ESTADO_S):
    url = f"http://127.0.0.1:{info['puerto']}{camino}"
    cuerpo = None if datos is None else json.dumps(datos).encode("utf-8")
    pedido = urllib.request.Request(url, data=cuerpo, method=metodo,
                                    headers={"Content-Type": "application/json", "X-OmniCAD-Token": info["token"]})
    sin_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # 127.0.0.1 nunca va por un proxy
    try:
        with sin_proxy.open(pedido, timeout=tiempo) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except ValueError:
            raise ErrorPuenteFusion(f"El complemento de Fusion respondió con error {e.code}.") from None
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        if isinstance(getattr(e, "reason", None), TimeoutError) or isinstance(e, TimeoutError):
            raise ErrorPuenteFusion(f"Fusion no respondió en {tiempo} s (puede estar ocupado con un diálogo abierto).",
                                    "sin_puente") from None
        raise _sin_puente("Fusion no está abierto o el complemento OmniCAD no está en ejecución.") from None
    except ValueError:
        raise ErrorPuenteFusion("El complemento de Fusion respondió algo que no es JSON.") from None


def estado():
    """Estado del puente: {"ok": True, "version", "fusion"} si responde. Lanza ErrorPuenteFusion si no."""
    info = leer_info()
    if info is None:
        raise _sin_puente("el complemento OmniCAD no está en ejecución dentro de Fusion.")
    r = _pedir(info, "GET", "/estado")
    if not r.get("ok"):
        raise ErrorPuenteFusion(r.get("mensaje") or "El complemento de Fusion no está listo.", "sin_puente")
    return r


def convertir(ruta, tiempo=TIEMPO_CONVERTIR_S):
    """Le pide a Fusion que abra `ruta` (.f3d/.f3z) y exporte STEP. Devuelve el resultado del protocolo con
    `step_texto` (el STEP leído; el archivo temporal se borra) en lugar de `step`."""
    ruta = Path(ruta).resolve()
    if ruta.suffix.lower() not in EXTENSIONES:
        raise ErrorPuenteFusion(f"No es un archivo de Fusion (.f3d o .f3z): {ruta.name}")
    if not ruta.is_file():
        raise ErrorPuenteFusion(f"No existe el archivo: {ruta}")
    info = leer_info()
    if info is None:
        raise _sin_puente("el complemento OmniCAD no está en ejecución dentro de Fusion.")
    r = _pedir(info, "POST", "/convertir", {"ruta": str(ruta)}, tiempo)
    if not r.get("ok"):
        raise ErrorPuenteFusion(f"Fusion no pudo convertir {ruta.name}: {r.get('mensaje') or 'error desconocido'}"
                                f"\n\n{PASOS_A_MANO}")
    step = Path(r.get("step") or "")
    try:
        texto = step.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise ErrorPuenteFusion(f"No se pudo leer el STEP que exportó Fusion ({step}): {e}") from None
    finally:
        _borrar_temporal(step)
    r = dict(r)
    del r["step"]
    r["step_texto"] = texto
    return r


def _borrar_temporal(step):
    """Borra el STEP temporal y su carpeta, solo si la carpeta es la que crea el complemento."""
    try:
        if step.parent.name.startswith("omnicad_fusion_"):
            shutil.rmtree(step.parent, ignore_errors=True)
        elif step.is_file():
            step.unlink()
    except OSError:
        pass
