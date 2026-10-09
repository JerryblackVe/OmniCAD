# -*- coding: utf-8 -*-
"""Archivo › Abrir de archivos de otros programas (STEP, IGES, mallas, DXF, .f3d/.f3z por el puente con Fusion)."""
import importlib.util
import json
import math
from pathlib import Path

import pytest
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Trsf, gp_Vec
from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopLoc import TopLoc_Location
from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool

from omnicad import api
from omnicad.io_archivos import dxf, puente_fusion
from omnicad.io_archivos import exportar as ex
from omnicad.io_archivos.abrir_externo import (ErrorAbrir, comparar_con_fusion, documento_desde_archivo,
                                               parametros_desde_fusion)
from omnicad.nucleo import geometria as g
from omnicad.timeline.parametros import ANGULO, ESCALAR, LONGITUD

COMPLEMENTO = Path(__file__).resolve().parents[1] / "omnicad" / "integraciones" / "fusion" / "OmniCADPuente"


class _Cuerpo:
    def __init__(self, forma):
        self.forma, self.tipo, self.nombre, self.id = forma, "solido", "c", "c1"


def _volumen_total(doc):
    return sum(c.forma.volumen() if c.tipo == "malla" else g.volumen(c.forma) for c in doc.estado_final.cuerpos.values())


def _step_con_estructura(ruta):
    """Diseño «Conjunto» con un componente «Soporte» (Placa roja 10×20×30) y un Perno (r 5, alto 10) suelto en
    la raíz, corrido 100 mm en X: lo que hace Fusion al exportar STEP."""
    doc = TDocStd_Document(TCollection_ExtendedString("XmlXCAF"))
    formas = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    colores = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

    def nombre(etiqueta, texto):
        TDataStd_Name.Set_s(etiqueta, TCollection_ExtendedString(texto))
        return etiqueta
    raiz = nombre(formas.NewShape(), "Conjunto")
    soporte = nombre(formas.NewShape(), "Soporte")
    placa = nombre(formas.AddShape(BRepPrimAPI_MakeBox(10, 20, 30).Shape(), False), "Placa")
    colores.SetColor(placa, Quantity_Color(0.8, 0.1, 0.2, Quantity_TypeOfColor.Quantity_TOC_RGB),
                     XCAFDoc_ColorType.XCAFDoc_ColorSurf)
    perno = nombre(formas.AddShape(BRepPrimAPI_MakeCylinder(5, 10).Shape(), False), "Perno")
    formas.AddComponent(soporte, placa, TopLoc_Location())
    formas.AddComponent(raiz, soporte, TopLoc_Location())
    corrido = gp_Trsf()
    corrido.SetTranslation(gp_Vec(100, 0, 0))
    formas.AddComponent(raiz, perno, TopLoc_Location(corrido))
    formas.UpdateAssemblies()
    w = STEPCAFControl_Writer()
    w.SetNameMode(True)
    w.SetColorMode(True)
    assert w.Transfer(doc, STEPControl_AsIs)
    w.Write(str(ruta))
    return ruta


# ---------------------------------------------------------------- formatos de intercambio
def test_step_conserva_nombres_colores_y_componentes(tmp_path):
    doc, avisos = documento_desde_archivo(_step_con_estructura(tmp_path / "conjunto.step"))
    assert avisos == [] and doc.nombre == "conjunto" and doc.ruta is None and not doc.modificado
    assert [o.TIPO for o in doc.operaciones] == ["importar_step"] and doc.operaciones[0].p["estructura"]
    estado = doc.estado_final
    assert [c["nombre"] for c in estado.componentes.values()] == ["Soporte"]
    cuerpos = {c.nombre: c for c in estado.cuerpos.values()}
    assert set(cuerpos) == {"Placa", "Perno"}
    assert cuerpos["Placa"].apariencia == pytest.approx([0.8, 0.1, 0.2])
    assert cuerpos["Placa"].componente == next(iter(estado.componentes))
    assert cuerpos["Perno"].componente == ""
    assert g.volumen(cuerpos["Placa"].forma) == pytest.approx(6000, rel=1e-9)
    assert g.volumen(cuerpos["Perno"].forma) == pytest.approx(math.pi * 25 * 10, rel=1e-6)
    (x0, _, _), (x1, _, _) = g.caja_envolvente(cuerpos["Perno"].forma)
    assert (x0, x1) == pytest.approx((95, 105), abs=1e-6)          # la ubicación del ensamblaje se aplica
    assert all(g.es_valida(c.forma) for c in cuerpos.values())


def test_insertar_step_viejo_sigue_igual(tmp_path):
    """Las recetas viejas (sin `estructura`) siguen cargando todo como cuerpos sueltos."""
    from omnicad.timeline.documento import Documento
    from omnicad.timeline.operaciones import OpImportarSTEP
    texto = _step_con_estructura(tmp_path / "a.step").read_text(encoding="utf-8")
    doc = Documento.desde_dict({"operaciones": [OpImportarSTEP("op1", "Importar", contenido=texto).a_dict()]})
    assert doc.resultados[0].estado == "ok" and not doc.estado_final.componentes
    assert _volumen_total(doc) == pytest.approx(6000 + math.pi * 250, rel=1e-6)


@pytest.mark.parametrize("ext", ["iges", "stl", "obj", "3mf", "ply"])
def test_formatos_abren_con_el_volumen_exacto(tmp_path, ext):
    ruta = tmp_path / f"caja.{ext}"
    ex.exportar([_Cuerpo(g.caja(10, 20, 30, (5, 0, 0)))], ruta)
    doc, _ = documento_desde_archivo(ruta)
    assert doc.resultados[0].estado == "ok" and len(doc.estado_final.cuerpos) == 1
    assert _volumen_total(doc) == pytest.approx(6000, rel=1e-6)
    c = next(iter(doc.estado_final.cuerpos.values()))
    caja = c.forma.caja() if c.tipo == "malla" else g.caja_envolvente(c.forma)
    assert [list(p) for p in caja] == [pytest.approx([5, 0, 0], abs=1e-4), pytest.approx([15, 20, 30], abs=1e-4)]


def test_malla_en_centimetros(tmp_path):
    ruta = tmp_path / "caja.stl"
    ex.exportar([_Cuerpo(g.caja(1, 2, 3, (0, 0, 0)))], ruta)
    doc, _ = documento_desde_archivo(ruta, "cm")
    assert _volumen_total(doc) == pytest.approx(6000, rel=1e-6)


def test_dxf_abre_como_boceto_con_perfiles(tmp_path):
    ruta = tmp_path / "placa.dxf"
    dxf.escribir_dxf(ruta, [("polilinea", [(0, 0), (40, 0), (40, 25), (0, 25)], True), ("circulo", (20, 12), 5)])
    doc, _ = documento_desde_archivo(ruta)
    assert [o.TIPO for o in doc.operaciones] == ["boceto"] and doc.operaciones[0].p["plano"] == "XY"
    areas = sorted(p.area for p in doc.estado_final.bocetos["op1"].perfiles)
    assert areas == pytest.approx([math.pi * 25, 40 * 25 - math.pi * 25], rel=1e-3)


def test_errores_claros(tmp_path):
    with pytest.raises(ErrorAbrir, match="Formato no soportado"):
        documento_desde_archivo(tmp_path / "x.dwg")
    with pytest.raises(ErrorAbrir, match="No existe el archivo"):
        documento_desde_archivo(tmp_path / "x.step")
    roto = tmp_path / "roto.step"
    roto.write_text("esto no es un STEP", encoding="utf-8")
    with pytest.raises(ErrorAbrir, match="No se pudo leer roto.step"):
        documento_desde_archivo(roto)


def test_api_open_document_formatos_nuevos(tmp_path):
    s = api.Sesion()
    r = api.llamar(s, "open_document", {"path": str(_step_con_estructura(tmp_path / "c.step"))})
    assert r["ok"] and sorted(b["name"] for b in r["result"]["bodies"]) == ["Perno", "Placa"]
    ruta = tmp_path / "caja.stl"
    ex.exportar([_Cuerpo(g.caja(1, 2, 3, (0, 0, 0)))], ruta)
    r = api.llamar(s, "open_document", {"path": str(ruta), "mesh_units": "cm"})
    assert r["ok"] and r["result"]["bodies"][0]["volume"] == pytest.approx(6000, rel=1e-6)
    r = api.llamar(s, "open_document", {"path": str(tmp_path / "x.dwg")})
    assert not r["ok"] and r["error_kind"] == "FILE_NOT_FOUND"
    (tmp_path / "x.dwg").write_text("x")
    r = api.llamar(s, "open_document", {"path": str(tmp_path / "x.dwg")})
    assert not r["ok"] and r["error_kind"] == "UNSUPPORTED_FILE_TYPE"


# ---------------------------------------------------------------- parámetros de Fusion
def test_parametros_de_fusion():
    lista = [
        {"nombre": "alto", "expresion": "ancho * 2", "unidad": "mm", "valor": 12.0, "comentario": "doble"},
        {"nombre": "ancho", "expresion": "60 mm", "unidad": "mm", "valor": 6.0, "comentario": ""},
        {"nombre": "lado", "expresion": "2", "unidad": "in", "valor": 5.08, "comentario": ""},   # «2» = 2 in
        {"nombre": "giro", "expresion": "30 deg", "unidad": "deg", "valor": math.radians(30), "comentario": ""},
        {"nombre": "n", "expresion": "4", "unidad": "", "valor": 4.0, "comentario": ""},
        {"nombre": "raro", "expresion": "ancho * fn(1)", "unidad": "mm", "valor": 6.0, "comentario": ""},
        {"nombre": "masa", "expresion": "2 kg", "unidad": "kg", "valor": 2.0, "comentario": ""},
    ]
    tabla, avisos = parametros_desde_fusion(lista)
    v = tabla.valores()
    assert v == pytest.approx({"alto": 120, "ancho": 60, "lado": 50.8, "giro": 30, "n": 4, "raro": 60})
    assert tabla.obtener("alto").expresion == "ancho * 2" and tabla.obtener("alto").comentario == "doble"
    assert tabla.obtener("lado").expresion == "50.8 mm"
    assert [tabla.obtener(n).tipo for n in ("giro", "n")] == [ANGULO, ESCALAR]
    assert tabla.obtener("ancho").tipo == LONGITUD
    assert "masa" not in tabla and any("masa" in a for a in avisos)
    assert any("«lado»" in a for a in avisos) and any("«raro»" in a for a in avisos)


def test_comparar_con_fusion(tmp_path):
    doc, _ = documento_desde_archivo(_step_con_estructura(tmp_path / "c.step"))
    total = 6000 + math.pi * 250
    assert comparar_con_fusion(doc, [{"volumen_mm3": total, "visible": True}]) == []
    assert comparar_con_fusion(doc, [{"volumen_mm3": total, "visible": True},
                                     {"volumen_mm3": 99.0, "visible": False}]) == []
    assert "no coincide" in comparar_con_fusion(doc, [{"volumen_mm3": 6000.0, "visible": True}])[0]


# ---------------------------------------------------------------- puente con Fusion (sin Fusion: servidor del complemento)
def _complemento():
    spec = importlib.util.spec_from_file_location("omnicad_puente_prueba", COMPLEMENTO / "OmniCADPuente.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def puente(tmp_path, monkeypatch):
    """El servidor REAL del complemento, con la conversión simulada (Fusion no está en las pruebas)."""
    monkeypatch.setenv(puente_fusion.VARIABLE_CARPETA, str(tmp_path / "info"))
    comp = _complemento()
    pedidos = []

    def atender(pedido):
        pedidos.append(pedido)
        if pedido["accion"] == "estado":
            return {"ok": True, "version": comp.VERSION, "fusion": "prueba"}
        problema = comp.validar_ruta(pedido["ruta"])
        if problema:
            return {"ok": False, "mensaje": problema}
        carpeta = tmp_path / "omnicad_fusion_x"
        carpeta.mkdir()
        _step_con_estructura(carpeta / "modelo.step")
        return {"ok": True, "step": str(carpeta / "modelo.step"), "documento": "pieza",
                "parametros": [{"nombre": "ancho", "expresion": "10 mm", "unidad": "mm", "valor": 1.0, "comentario": ""}],
                "cuerpos": [{"nombre": "Placa", "componente": "Soporte:1", "visible": True, "volumen_mm3": 6000.0},
                            {"nombre": "Perno", "componente": "", "visible": True, "volumen_mm3": math.pi * 250}],
                "componentes": ["Soporte:1"]}
    servidor = comp.Servidor(atender)
    servidor.iniciar()
    yield comp, servidor, pedidos
    servidor.detener()


def test_puente_convierte_f3d(tmp_path, puente):
    comp, servidor, pedidos = puente
    assert json.loads(puente_fusion.ruta_info().read_text())["puerto"] == servidor.puerto
    assert puente_fusion.estado()["fusion"] == "prueba"
    f3d = tmp_path / "pieza.f3d"
    f3d.write_bytes(b"PK")
    doc, avisos = documento_desde_archivo(f3d)
    assert doc.nombre == "pieza" and doc.parametros.valores() == {"ancho": 10.0}
    assert sorted(c.nombre for c in doc.estado_final.cuerpos.values()) == ["Perno", "Placa"]
    assert _volumen_total(doc) == pytest.approx(6000 + math.pi * 250, rel=1e-6)
    assert any("historial" in a for a in avisos) and not any("no coincide" in a for a in avisos)
    assert not (tmp_path / "omnicad_fusion_x").exists()                # el STEP temporal se borra
    assert pedidos[-1] == {"accion": "convertir", "ruta": str(f3d.resolve())}


def test_puente_clave_y_ruta(tmp_path, puente):
    comp, servidor, _ = puente
    info = dict(puente_fusion.leer_info(), token="otra")
    r = puente_fusion._pedir(info, "GET", "/estado")
    assert r == {"ok": False, "mensaje": "Clave del puente inválida."}
    texto = tmp_path / "x.txt"
    texto.write_text("x")
    assert "Solo se convierten" in comp.validar_ruta(str(texto))
    with pytest.raises(puente_fusion.ErrorPuenteFusion, match="No existe el archivo"):
        puente_fusion.convertir(tmp_path / "falta.f3d")


def test_sin_fusion_aviso_claro_con_pasos_a_mano(tmp_path, monkeypatch):
    monkeypatch.setenv(puente_fusion.VARIABLE_CARPETA, str(tmp_path / "vacia"))
    f3d = tmp_path / "pieza.f3d"
    f3d.write_bytes(b"PK")
    with pytest.raises(puente_fusion.ErrorPuenteFusion) as e:
        documento_desde_archivo(f3d)
    assert e.value.motivo == "sin_puente" and "Archivo › Exportar" in str(e.value) and "omnicad setup" in str(e.value)
    r = api.llamar(api.Sesion(), "open_document", {"path": str(f3d)})
    assert not r["ok"] and r["error_kind"] == "FUSION_NOT_AVAILABLE" and "STEP" in " ".join(r["pistas"])
    # Un puente anotado pero caído (Fusion se cerró sin borrar el archivo) da el mismo aviso, no un error crudo.
    (tmp_path / "vacia").mkdir()
    puente_fusion.ruta_info().write_text(json.dumps({"puerto": 9, "token": "x"}))
    with pytest.raises(puente_fusion.ErrorPuenteFusion) as e:
        puente_fusion.convertir(f3d, tiempo=2)
    assert e.value.motivo == "sin_puente"


# ---------------------------------------------------------------- nombres de cuerpos, .f3z y medición en forma libre
STEP_FUSION = """ISO-10303-21;
DATA;
#1=PRODUCT('Asa (1)','Asa (1)','',(#2));
#3=PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE('','',#1,.NOT_KNOWN.);
#4=PRODUCT_DEFINITION('design','',#3,#5);
#6=PRODUCT_DEFINITION_SHAPE('','',#4);
#7=SHAPE_DEFINITION_REPRESENTATION(#6,#8);
#8=SHAPE_REPRESENTATION('Asa (1)',(#9),#10);
#11=SHAPE_REPRESENTATION_RELATIONSHIP('','',#8,#12);
#12=ADVANCED_BREP_SHAPE_REPRESENTATION('brep (a)',(#13,#14,#15),#10);
#13=MANIFOLD_SOLID_BREP('asa_mitad_B',#20);
#14=MANIFOLD_SOLID_BREP('cuer
no (1)',#21);
#15=BREP_WITH_VOIDS('aro de Ana''s',#22,(#23));
ENDSEC;
END-ISO-10303-21;
"""


def test_nombres_de_cuerpos_desde_el_step():
    from omnicad.nucleo.intercambio import nombres_solidos_step
    assert nombres_solidos_step(STEP_FUSION) == {"Asa (1)": ["asa_mitad_B", "cuerno (1)", "aro de Ana's"]}
    assert nombres_solidos_step("ISO-10303-21; DATA; ENDSEC;") == {}


def test_f3z_elige_el_diseno_de_arriba(tmp_path):
    import zipfile
    comp = _complemento()
    f3z = tmp_path / "paquete.f3z"
    descripcion = {"designDescription": {"designGraphs": [{"designObjects": [
        {"id": 1, "contentType": "f3d", "relativePath": "pieza.f3d", "references": []},
        {"id": 2, "contentType": "f3d", "relativePath": "conjunto.f3d", "references": [{"ids": [1]}]},
        {"id": 3, "contentType": "f2d", "relativePath": "plano.f2d", "references": [{"ids": [2]}]}]}]}}
    with zipfile.ZipFile(f3z, "w") as z:
        z.writestr("pieza.f3d", b"x" * 500)          # la más grande, pero la referencia el conjunto
        z.writestr("conjunto.f3d", b"y" * 10)
        z.writestr("plano.f2d", b"z")
        z.writestr("DesignDescription.json", json.dumps(descripcion))
    elegido = Path(comp.f3d_principal(str(f3z), str(tmp_path / "x")))
    assert elegido.name == "conjunto.f3d" and elegido.read_bytes() == b"y" * 10
    assert not (tmp_path / "x" / "plano.f2d").exists()
    with zipfile.ZipFile(tmp_path / "vacio.f3z", "w") as z:
        z.writestr("plano.f2d", b"z")
    with pytest.raises(ValueError, match="no trae"):
        comp.f3d_principal(str(tmp_path / "vacio.f3z"), str(tmp_path / "y"))


def test_volumen_y_area_en_forma_libre():
    """Una esfera pasada a NURBS va por el control con malla y se queda con la integración de OpenCascade (que en
    NURBS ya difería del valor exacto: volumen −0,04 %, área +0,37 %: el control solo la descarta si se aleja más de 1 %)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_NurbsConvert
    esfera = g.esfera(10, (0, 0, 0))
    nurbs = BRepBuilderAPI_NurbsConvert(esfera, True).Shape()
    assert not g.es_forma_libre(esfera) and g.es_forma_libre(nurbs)
    assert g.volumen(nurbs) == pytest.approx(4 / 3 * math.pi * 1000, rel=1e-3)
    assert g.area(nurbs) == pytest.approx(4 * math.pi * 100, rel=5e-3)          # área: +0,37 % (igual que antes)
