# -*- coding: utf-8 -*-
"""Adjuntos del chat del Asistente (IA-9, asistente/adjuntos.py): validación, bloques por tipo, cómo los mandan los
proveedores (urlopen parcheado), el modo suscripción (Popen parcheado), el historial sin contenido pesado y archivos
hostiles que no tiran la app. Sin red ni gasto."""
import base64
import io
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

import pytest
from PIL import Image

from omnicad.asistente import adjuntos, config, historial  # noqa: F401 — config primero: evita el ciclo con agente_local
from omnicad.asistente.adjuntos import ErrorAdjunto, preparar
from omnicad.asistente.proveedores import agente_local, anthropic, openai_compat
from omnicad.asistente.proveedores.agente_local import AgenteLocal
from omnicad.asistente.proveedores.base import ErrorProveedor
from omnicad.io_archivos.dxf import escribir_dxf

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" viewBox="0 0 100 50">'
       '<rect x="10" y="10" width="80" height="30"/><circle cx="50" cy="25" r="10"/></svg>')


def _archivo(tmp_path, nombre, datos):
    ruta = tmp_path / nombre
    ruta.write_bytes(datos if isinstance(datos, bytes) else datos.encode("utf-8"))
    return ruta


def _foto(tmp_path, nombre="foto.jpg", tam=(4000, 3000)):
    ruta = tmp_path / nombre
    Image.new("RGB", tam, (200, 30, 30)).save(ruta)
    return ruta


# ---------------------------------------------------------------- validación
@pytest.mark.parametrize("nombre", ["virus.exe", "notas.txt", "pieza.step", "sin_extension"])
def test_solo_extensiones_permitidas(tmp_path, nombre):
    with pytest.raises(ErrorAdjunto, match="solo PDF, PNG, JPG, SVG y DXF"):
        preparar(_archivo(tmp_path, nombre, b"MZ cualquier cosa"))


def test_tope_de_tamano_vacio_inexistente_y_pdf_falso(tmp_path, monkeypatch):
    monkeypatch.setattr(adjuntos, "TOPE_OTROS", 100)
    with pytest.raises(ErrorAdjunto, match="pesa más de"):
        preparar(_archivo(tmp_path, "grande.svg", "<svg>" + " " * 200 + "</svg>"))
    with pytest.raises(ErrorAdjunto, match="vacío"):
        preparar(_archivo(tmp_path, "vacio.png", b""))
    with pytest.raises(ErrorAdjunto, match="No se pudo leer"):
        preparar(tmp_path / "no_existe.pdf")
    with pytest.raises(ErrorAdjunto, match="No se pudo leer"):
        carpeta = tmp_path / "carpeta.pdf"
        carpeta.mkdir()
        preparar(carpeta)                                     # una carpeta no es un archivo
    with pytest.raises(ErrorAdjunto, match="no es un PDF válido"):
        preparar(_archivo(tmp_path, "trucho.pdf", b"<html>no soy un pdf</html>"))
    assert adjuntos.TOPE_PDF == 20 * 2**20 and adjuntos.MAXIMO == 10


def test_el_undecimo_se_rechaza(tmp_path):
    ruta = _archivo(tmp_path, "plano.pdf", PDF)
    assert preparar(ruta, 9).clase == "pdf"
    with pytest.raises(ErrorAdjunto, match="Máximo 10 adjuntos por mensaje: «plano.pdf» no se agregó"):
        preparar(ruta, 10)


# ---------------------------------------------------------------- bloques por tipo
def test_pdf_va_como_documento_con_su_ruta(tmp_path):
    a = preparar(_archivo(tmp_path, "Plano.PDF", PDF))
    assert [b["tipo"] for b in a.bloques] == ["texto", "documento"]
    assert str(tmp_path / "Plano.PDF") in a.bloques[0]["texto"] and "PDF" in a.bloques[0]["texto"]
    assert a.bloques[1]["pdf"] == PDF and a.bloques[1]["nombre"] == "Plano.PDF" and a.miniatura is None


def test_foto_grande_se_achica_a_png(tmp_path):
    a = preparar(_foto(tmp_path))
    imagen = a.bloques[1]
    assert a.clase == "imagen" and imagen["tipo"] == "imagen" and imagen["png"][:4] == b"\x89PNG"
    assert (imagen["ancho"], imagen["alto"]) == (1568, 1176) and len(imagen["png"]) <= adjuntos.TOPE_PNG
    assert "4000×3000 px (va achicada a 1568×1176)" in a.bloques[0]["texto"] and a.miniatura == imagen["png"]


def test_imagen_rota_y_bomba_de_pixeles(tmp_path, monkeypatch):
    with pytest.raises(ErrorAdjunto, match="no es una imagen PNG o JPG válida"):
        preparar(_archivo(tmp_path, "rota.png", b"\x89PNG\r\n\x1a\n" + b"\0" * 50))
    monkeypatch.setattr(adjuntos, "TOPE_PIXELES", 1000)
    with pytest.raises(ErrorAdjunto, match="megapíxeles"):
        preparar(_foto(tmp_path, "enorme.png", (100, 100)))


def test_svg_y_dxf_llevan_vista_previa_y_como_insertarlos(tmp_path):
    svg = preparar(_archivo(tmp_path, "logo.svg", SVG))
    texto = svg.bloques[0]["texto"]
    assert "SVG con 2 primitivas, 80.0 × 30.0 mm" in texto
    assert f"insert_svg(path={json.dumps(str(tmp_path / 'logo.svg'))})" in texto
    vista = Image.open(io.BytesIO(svg.miniatura))
    assert vista.size[0] == adjuntos.LADO_VISTA and vista.getpixel((10, vista.size[1] // 2)) != (255, 255, 255)
    ruta = tmp_path / "pieza.dxf"
    escribir_dxf(ruta, [("linea", (0, 0), (10, 0)), ("circulo", (5, 5), 3)])
    dxf = preparar(ruta)
    assert "DXF con 2 primitivas, 10.0 × 8.0 mm" in dxf.bloques[0]["texto"] and "insert_dxf(path=" in dxf.bloques[0]["texto"]
    assert dxf.bloques[1]["tipo"] == "imagen" and dxf.bloques[1]["adjunto"] == "pieza.dxf"


def test_svg_y_dxf_hostiles_no_tiran_la_app(tmp_path):
    roto = preparar(_archivo(tmp_path, "roto.svg", "<svg><g><path d='M0 0 L"))
    assert [b["tipo"] for b in roto.bloques] == ["texto"] and "No se pudo leer su geometría" in roto.bloques[0]["texto"]
    assert "Texto del archivo (recortado):\n<svg><g>" in roto.bloques[0]["texto"]
    basura = preparar(_archivo(tmp_path, "basura.dxf", bytes(range(256)) * 100))
    assert "No se pudo leer su geometría" in basura.bloques[0]["texto"]
    binario = preparar(_archivo(tmp_path, "bin.dxf", b"AutoCAD Binary DXF\r\n\x1a\0" + b"\0" * 100))
    assert "binario" in binario.bloques[0]["texto"]
    # «mil millones de risas»: expat (2.4 o más nueva, la de Python 3.12) corta la expansión de entidades
    entidades = '<!ENTITY a0 "xxxxxxxxxx">' + "".join(f'<!ENTITY a{i} "' + f"&a{i - 1};" * 10 + '">' for i in range(1, 9))
    bomba = preparar(_archivo(tmp_path, "bomba.svg", f"<!DOCTYPE svg [{entidades}]><svg>&a8;</svg>"))
    assert "No se pudo leer" in bomba.bloques[0]["texto"]
    lineas = "".join(f'<line x1="0" y1="{i}" x2="10" y2="{i}"/>' for i in range(adjuntos.TOPE_PRIMITIVAS + 50))
    enorme = preparar(_archivo(tmp_path, "enorme.svg", f'<svg xmlns="http://www.w3.org/2000/svg">{lineas}</svg>'))
    assert f"la vista previa dibuja las primeras {adjuntos.TOPE_PRIMITIVAS}" in enorme.bloques[0]["texto"]
    assert enorme.miniatura is not None


# ---------------------------------------------------------------- proveedores (urlopen parcheado)
class _Respuesta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture
def red(monkeypatch):
    pedidos, respuestas = [], []

    def urlopen(pedido, timeout=None):
        pedidos.append(json.loads(pedido.data))
        r = respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return _Respuesta(json.dumps(r).encode())

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return pedidos, respuestas


def _chat(tmp_path):
    a, b = preparar(_archivo(tmp_path, "plano.pdf", PDF)), preparar(_foto(tmp_path, "f.png", (40, 30)))
    return [{"rol": "usuario", "contenido": [{"tipo": "texto", "texto": "Mirá esto."}, *a.bloques, *b.bloques]}]


def test_anthropic_manda_el_pdf_como_document_y_la_imagen(tmp_path, red):
    pedidos, respuestas = red
    respuestas.append({"content": [{"type": "text", "text": "Lo vi."}], "usage": {}})
    r = anthropic.ProveedorAnthropic(clave="sk-x").responder("", _chat(tmp_path), [])
    contenido = pedidos[0]["messages"][0]["content"]
    assert r.texto == "Lo vi." and [c["type"] for c in contenido] == ["text", "text", "document", "text", "image"]
    assert contenido[2] == {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                           "data": base64.b64encode(PDF).decode()}}
    assert base64.b64decode(contenido[4]["source"]["data"])[:4] == b"\x89PNG"


def test_openai_manda_el_pdf_como_file_y_explica_si_lo_rechaza(tmp_path, red):
    pedidos, respuestas = red
    respuestas.append({"choices": [{"message": {"content": "Ok."}}], "usage": {}})
    p = openai_compat.ProveedorOpenAI("gpt-x", clave="sk-x")
    assert p.responder("", _chat(tmp_path), []).texto == "Ok."
    partes = pedidos[0]["messages"][0]["content"]
    assert [c["type"] for c in partes] == ["text", "text", "file", "text", "image_url"]
    assert partes[2] == {"type": "file", "file": {"filename": "plano.pdf",
                                                  "file_data": "data:application/pdf;base64," + base64.b64encode(PDF).decode()}}
    cuerpo = io.BytesIO(json.dumps({"error": {"message": "file parts not supported"}}).encode())
    respuestas.append(urllib.error.HTTPError("u", 400, "Bad", {}, cuerpo))
    with pytest.raises(ErrorProveedor, match="HTTP 400.*file parts not supported.*PDF adjunto"):
        p.responder("", _chat(tmp_path), [])


# ---------------------------------------------------------------- modo suscripción (Popen parcheado)
class _Proceso:
    pid, returncode = 4242, 0

    def __init__(self):
        self.stdin = io.BytesIO()
        self.stdin.close = lambda: None
        self.stdout, self.stderr = iter([]), iter([])

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0


@pytest.fixture
def lanzar(monkeypatch, tmp_path):
    """Popen parcheado: guarda argv, stdin y los archivos que había en la carpeta del pedido (en bytes)."""
    monkeypatch.setattr(agente_local.shutil, "which", lambda nombre: f"C:/bin/{nombre}.cmd")
    monkeypatch.setenv("OMNICAD_PUENTE_DIR", str(tmp_path))
    lanzados = []

    def popen(argv, **kw):
        proceso = _Proceso()
        lanzados.append({"argv": argv, "cwd": kw["cwd"], "proceso": proceso, "archivos": {
            n: Path(kw["cwd"], n).read_bytes() for n in os.listdir(kw["cwd"])}})
        return proceso

    monkeypatch.setattr(agente_local.subprocess, "Popen", popen)
    return lanzados


def _correr(tipo, lanzar, bloques):
    eventos = []
    pesados = [b for b in bloques if b["tipo"] in ("imagen", "documento")]
    texto = "Mirá esto.\n\n" + "\n\n".join(b["texto"] for b in bloques if b["tipo"] == "texto")
    AgenteLocal(tipo).correr(texto, "SISTEMA", "explicar", lambda t, d: eventos.append((t, d)), None, pesados)
    return lanzar[-1], eventos


def test_agentes_locales_reciben_rutas_imagenes_y_pdf(tmp_path, lanzar):
    bloques = _chat(tmp_path)[0]["contenido"][1:]
    # Claude Code: los adjuntos van como bloques por stdin (stream-json); la ruta, en el texto.
    corrida, eventos = _correr("claude_code", lanzar, bloques)
    assert corrida["argv"][-2:] == ["--input-format", "stream-json"] and not eventos
    mensaje = json.loads(corrida["proceso"].stdin.getvalue())
    contenido = mensaje["message"]["content"]
    assert mensaje["type"] == "user" and [c["type"] for c in contenido] == ["text", "document", "image"]
    assert str(tmp_path / "plano.pdf") in contenido[0]["text"]
    # OpenCode: -f con las copias de la carpeta del pedido, con nombre propio (ninguna ruta ajena en argv).
    corrida, eventos = _correr("opencode", lanzar, bloques)
    archivos = [corrida["argv"][i + 1] for i, x in enumerate(corrida["argv"]) if x == "-f"]
    assert [os.path.basename(r) for r in archivos] == ["adjunto_1.pdf", "adjunto_2.png"] and not eventos
    assert all(os.path.dirname(r) == corrida["cwd"] for r in archivos)
    assert corrida["archivos"]["adjunto_1.pdf"] == PDF and corrida["archivos"]["adjunto_2.png"][:4] == b"\x89PNG"
    assert str(tmp_path / "plano.pdf") in corrida["proceso"].stdin.getvalue().decode()
    # Codex: la imagen con --image en un solo argumento (el «-» final sigue siendo stdin); el PDF no: se avisa.
    corrida, eventos = _correr("codex", lanzar, bloques)
    imagen = next(x for x in corrida["argv"] if x.startswith("--image="))
    assert imagen.endswith("adjunto_2.png") and "," not in imagen and corrida["argv"][-1] == "-"
    assert eventos == [("aviso", "Codex no recibe PDF adjuntos: le llega solo la ruta del archivo, no su contenido.")]


def test_agente_sin_adjuntos_no_cambia_la_linea_de_comandos(lanzar):
    AgenteLocal("claude_code").correr("hola", "SISTEMA", "explicar")
    assert "--input-format" not in lanzar[-1]["argv"] and lanzar[-1]["proceso"].stdin.getvalue() == b"hola"


# ---------------------------------------------------------------- historial
def test_historial_guarda_nombre_y_tipo_no_el_contenido(tmp_path, monkeypatch):
    monkeypatch.setenv(historial.VAR_CARPETA, str(tmp_path / "hist"))
    chat = _chat(tmp_path)
    chat[0]["contenido"].append({"tipo": "imagen", "png": b"\x89PNG captura", "ancho": 1, "alto": 1})  # del visor
    id_chat = historial.guardar(chat, "explicar", "anthropic", "")
    crudo = (tmp_path / "hist" / f"{id_chat}.json").read_text(encoding="utf-8")
    assert base64.b64encode(PDF).decode() not in crudo and '"documento"' not in crudo
    guardado = historial.cargar(id_chat)["mensajes"][0]["contenido"]
    assert [b["tipo"] for b in guardado] == ["texto", "texto", "texto", "imagen"]
    assert "«plano.pdf»: PDF" in guardado[1]["texto"] and "«f.png»: imagen" in guardado[2]["texto"]
    assert guardado[3]["png"] == b"\x89PNG captura"           # las capturas que no son adjuntos siguen
