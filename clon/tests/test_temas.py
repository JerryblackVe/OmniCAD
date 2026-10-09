# -*- coding: utf-8 -*-
"""Sistema de temas (ui/temas.py): los cinco temas incluidos, el QSS generado, el contraste del texto, los temas
del usuario (base + colores parciales, archivos inválidos) y su elección en Preferencias."""
import json
import os
import re

import pytest

from omnicad.ui import temas

INCLUIDOS = list(temas.INCLUIDOS)


@pytest.fixture(autouse=True)
def tema_de_fabrica(tmp_path, monkeypatch):
    """Cada prueba arranca con el tema de fábrica y una carpeta de temas propia (nunca la real del usuario)."""
    monkeypatch.setenv(temas.VAR_CARPETA, str(tmp_path / "temas"))
    temas.activar(temas.DEFECTO)
    yield
    temas.activar(temas.DEFECTO)


def escribir(carpeta, nombre, contenido):
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    ruta.write_text(contenido if isinstance(contenido, str) else json.dumps(contenido), encoding="utf-8")
    return ruta


# ---------------------------------------------------------------- los temas incluidos
def test_hay_cinco_temas_y_el_de_fabrica_es_oscuro_moderno():
    assert INCLUIDOS == ["oscuro_moderno", "claro_moderno", "azul_profesional", "minimalista", "clasico"]
    assert temas.DEFECTO == "oscuro_moderno" and temas.clave_activa() == "oscuro_moderno"
    from omnicad.ui.preferencias import DEFECTOS
    assert DEFECTOS["general/tema"] == "oscuro_moderno"


@pytest.mark.parametrize("clave", INCLUIDOS)
def test_cada_tema_tiene_todos_los_colores_validos(clave):
    colores = temas.INCLUIDOS[clave]["colores"]
    assert set(colores) == set(temas.CLAVES_COLOR)
    for token, valor in colores.items():
        assert re.fullmatch(r"#[0-9a-f]{6}", valor), (clave, token, valor)


@pytest.mark.parametrize("clave", INCLUIDOS)
def test_el_qss_de_cada_tema_se_genera_completo_y_bien_formado(clave):
    qss = temas.generar_qss(temas.INCLUIDOS[clave]["colores"])
    assert "$" not in qss, "quedó un token sin reemplazar"
    assert qss.count("{") == qss.count("}")
    # cada regla es «selectores { propiedades }» sin llaves adentro ni llaves sueltas
    assert re.fullmatch(r"(\s*[^{}]+\{[^{}]*\})+\s*", re.sub(r"/\*.*?\*/", "", qss, flags=re.S))
    assert temas.INCLUIDOS[clave]["colores"]["texto"] in qss


def test_la_plantilla_no_tiene_colores_fijos_sueltos():
    fijos = re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|\brgba?\(", temas.PLANTILLA_QSS.template)
    assert fijos == [], f"colores fijos en la plantilla: {fijos}"


def test_falta_un_token_el_qss_falla_en_voz_alta():
    colores = dict(temas.INCLUIDOS["clasico"]["colores"])
    del colores["acento"]
    with pytest.raises(KeyError):
        temas.generar_qss(colores)


def test_la_plantilla_solo_usa_tokens_que_existen():
    usados = set(re.findall(r"\$([a-z_]+)", temas.PLANTILLA_QSS.template))
    assert usados <= set(temas.CLAVES_COLOR), usados - set(temas.CLAVES_COLOR)


# ---------------------------------------------------------------- contraste
def test_razon_de_contraste_conocida():
    assert temas.razon_contraste("#000000", "#ffffff") == pytest.approx(21.0)
    assert temas.razon_contraste("#777777", "#777777") == pytest.approx(1.0)
    assert temas.razon_contraste("#767676", "#ffffff") == pytest.approx(4.54, abs=0.01)    # el gris AA clásico


@pytest.mark.parametrize("clave", INCLUIDOS)
def test_contraste_del_texto_al_menos_4_5_en_cada_tema(clave):
    colores = temas.INCLUIDOS[clave]["colores"]
    asignaciones = [(t, f, round(temas.razon_contraste(colores[t], colores[f]), 2)) for t, f in temas.PARES_CONTRASTE]
    flojos = [a for a in asignaciones if a[2] < temas.MIN_CONTRASTE]
    assert flojos == [], f"{clave}: contraste menor a 4.5 en {flojos}"
    assert temas.contraste_bajo(colores) == []
    # el par principal, medido directo
    assert temas.razon_contraste(colores["texto"], colores["fondo"]) >= 4.5
    assert temas.razon_contraste(colores["texto"], colores["panel"]) >= 4.5


def test_un_tema_con_texto_ilegible_se_detecta():
    colores = dict(temas.INCLUIDOS["claro_moderno"]["colores"], texto="#dddddd")
    assert ("texto", "fondo") in [(t, f) for t, f, _ in temas.contraste_bajo(colores)]


# ---------------------------------------------------------------- temas del usuario
def test_tema_de_usuario_toma_lo_que_falta_de_la_base(tmp_path):
    carpeta = tmp_path / "mis_temas"
    escribir(carpeta, "mio.json", {"nombre": "Mi tema", "base": "claro_moderno",
                                   "colores": {"acento": "#ff00aa", "texto": "#102030"}})
    usuario, avisos = temas.temas_usuario(carpeta)
    assert avisos == [] and list(usuario) == ["usuario:mio"]
    t = usuario["usuario:mio"]
    base = temas.INCLUIDOS["claro_moderno"]["colores"]
    assert t["nombre"] == "Mi tema" and t["base"] == "claro_moderno" and t["usuario"] is True
    assert t["colores"]["acento"] == "#ff00aa" and t["colores"]["texto"] == "#102030"
    resto = [k for k in temas.CLAVES_COLOR if k not in ("acento", "texto")]
    assert all(t["colores"][k] == base[k] for k in resto)
    assert set(t["colores"]) == set(temas.CLAVES_COLOR)
    assert temas.generar_qss(t["colores"])        # se puede generar el QSS con un tema parcial


def test_tema_de_usuario_sin_base_ni_nombre_usa_los_de_fabrica(tmp_path):
    carpeta = tmp_path / "t"
    escribir(carpeta, "solo_colores.json", {"colores": {"fondo": "#abc"}})
    t = temas.temas_usuario(carpeta)[0]["usuario:solo_colores"]
    assert t["base"] == temas.DEFECTO and t["nombre"] == "solo_colores"
    assert t["colores"]["fondo"] == "#aabbcc"                   # '#abc' se normaliza a '#aabbcc'


def test_json_invalido_se_ignora_y_se_avisa_sin_romper_los_demas(tmp_path):
    carpeta = tmp_path / "t"
    escribir(carpeta, "roto.json", "{esto no es json")
    escribir(carpeta, "lista.json", "[1, 2, 3]")
    escribir(carpeta, "vacio.json", "")
    escribir(carpeta, "bueno.json", {"nombre": "Bueno", "colores": {"acento": "#123456"}})
    usuario, avisos = temas.temas_usuario(carpeta)
    assert list(usuario) == ["usuario:bueno"]
    for archivo in ("roto.json", "lista.json", "vacio.json"):
        assert any(archivo in a and "ignorado" in a for a in avisos), (archivo, avisos)
    assert len(avisos) == 3


def test_colores_invalidos_y_claves_desconocidas_se_ignoran_con_aviso(tmp_path):
    carpeta = tmp_path / "t"
    escribir(carpeta, "raro.json", {"base": "no_existe", "colores": {
        "acento": "rojo", "texto": "#102030", "inventado": "#ffffff", "fondo": 12}})
    usuario, avisos = temas.temas_usuario(carpeta)
    t = usuario["usuario:raro"]
    base = temas.INCLUIDOS[temas.DEFECTO]["colores"]
    assert t["base"] == temas.DEFECTO and t["colores"]["texto"] == "#102030"
    assert t["colores"]["acento"] == base["acento"] and t["colores"]["fondo"] == base["fondo"]
    texto = " | ".join(avisos)
    assert "no_existe" in texto and "inventado" in texto and "«acento»" in texto and "«fondo»" in texto


def test_carpeta_inexistente_o_vacia_no_da_temas_ni_avisos(tmp_path):
    assert temas.temas_usuario(tmp_path / "no_existe") == ({}, [])
    (tmp_path / "vacia").mkdir()
    assert temas.temas_usuario(tmp_path / "vacia") == ({}, [])


def test_activar_un_tema_de_usuario_y_volver_al_de_fabrica_si_ya_no_esta(tmp_path):
    carpeta = tmp_path / "temas"                                   # la que apunta OMNICAD_TEMAS_DIR
    escribir(carpeta, "mio.json", {"nombre": "Mío", "base": "azul_profesional", "colores": {"acento": "#ff0000"}})
    assert temas.activar("usuario:mio") == []
    assert temas.clave_activa() == "usuario:mio" and temas.color("acento") == "#ff0000"
    assert temas.nombre_activo() == "Mío"
    assert "usuario:mio" in [c for c, _n, _u in temas.disponibles()[0]]
    (carpeta / "mio.json").unlink()                                 # el archivo desapareció
    avisos = temas.activar("usuario:mio")
    assert temas.clave_activa() == temas.DEFECTO and any("usuario:mio" in a for a in avisos)


def test_disponibles_lista_los_incluidos_primero_y_los_del_usuario_marcados(tmp_path):
    escribir(tmp_path / "temas", "zeta.json", {"nombre": "Zeta"})
    lista, avisos = temas.disponibles()
    assert avisos == []
    assert [c for c, _n, _u in lista[:5]] == INCLUIDOS and not any(u for _c, _n, u in lista[:5])
    assert lista[5] == ("usuario:zeta", "Zeta", True)


def test_exportar_plantilla_es_un_json_con_todos_los_colores_que_se_vuelve_a_leer(tmp_path):
    ruta = temas.exportar_plantilla(tmp_path / "salida" / "plantilla.json", "azul_profesional")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    assert datos["base"] == "azul_profesional" and set(datos["colores"]) == set(temas.CLAVES_COLOR)
    t, avisos = temas.leer_archivo(ruta)
    assert avisos == [] and t["colores"] == temas.INCLUIDOS["azul_profesional"]["colores"]


def test_ruta_de_plantilla_nueva_no_pisa_archivos(tmp_path):
    carpeta = tmp_path / "t"
    assert temas.ruta_plantilla_nueva(carpeta).name == "mi_tema.json"
    escribir(carpeta, "mi_tema.json", {})
    assert temas.ruta_plantilla_nueva(carpeta).name == "mi_tema_2.json"


# ---------------------------------------------------------------- el tema activo llega a lo que pinta a mano
def test_el_fondo_de_la_vista_3d_sigue_al_tema_activo():
    from omnicad.ui.visor3d import ENTORNOS, ConfigVista
    for clave in ("claro_moderno", "azul_profesional", "oscuro_moderno"):
        temas.activar(clave)
        c = temas.activo()
        _n, arriba, abajo, _luz = ENTORNOS["tema"]
        assert arriba == pytest.approx(temas.rgb_f(c["visor_arriba"])) and abajo == pytest.approx(temas.rgb_f(c["visor_abajo"]))
        assert ConfigVista().colores_fondo()[0] == arriba
    temas.activar("claro_moderno")
    assert not ConfigVista().oscuro()
    temas.activar("oscuro_moderno")
    assert ConfigVista().oscuro()


def test_los_observadores_se_avisan_al_cambiar_de_tema():
    llamadas = []
    temas.observar(lambda: llamadas.append(temas.clave_activa()))
    temas.activar("minimalista")
    temas.activar("clasico")
    assert llamadas[-2:] == ["minimalista", "clasico"]


def test_el_navegador_lee_el_tema_activo_y_no_una_copia_vieja():
    import omnicad.ui.navegador as nav
    assert not hasattr(nav, "TEXTO"), "navegador.py no puede guardar el color de texto al importarse"
    assert nav.temas.activo() is temas.activo()


def test_la_paleta_de_qt_sale_de_los_tokens():
    from PySide6.QtGui import QPalette
    for clave in INCLUIDOS:
        c = temas.INCLUIDOS[clave]["colores"]
        p = temas.paleta(c)
        assert p.color(QPalette.Window).name() == c["fondo"] and p.color(QPalette.WindowText).name() == c["texto"]
        assert p.color(QPalette.Base).name() == c["entrada"] and p.color(QPalette.Highlight).name() == c["seleccion"]
        assert p.color(QPalette.Disabled, QPalette.Text).name() == c["texto_inactivo"]


# ---------------------------------------------------------------- Preferencias
@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def prefs(tmp_path):
    from PySide6.QtCore import QSettings
    from omnicad.ui.preferencias import Preferencias
    return Preferencias(QSettings(str(tmp_path / "prefs.ini"), QSettings.IniFormat))


def test_preferencias_guarda_el_tema_elegido(prefs):
    assert prefs["general/tema"] == "oscuro_moderno"
    prefs["general/tema"] = "minimalista"
    assert prefs["general/tema"] == "minimalista"
    prefs.restablecer()
    assert prefs["general/tema"] == "oscuro_moderno"


def test_dialogo_ofrece_todos_los_temas_y_avisa_la_vista_previa(qapp, prefs, tmp_path):
    from omnicad.ui.preferencias import DialogoPreferencias
    escribir(tmp_path / "temas", "mio.json", {"nombre": "Mío"})
    dlg = DialogoPreferencias(prefs)
    combo = dlg.controles["general/tema"]
    claves = [combo.itemData(i) for i in range(combo.count())]
    assert claves == INCLUIDOS + ["usuario:mio"] and "(propio)" in combo.itemText(len(claves) - 1)
    assert combo.currentData() == "oscuro_moderno"
    elegidos = []
    dlg.tema_elegido.connect(elegidos.append)
    combo.setCurrentIndex(combo.findData("claro_moderno"))
    assert elegidos == ["claro_moderno"] and dlg.b_aplicar.isEnabled()
    dlg.b_aplicar.click()
    assert prefs["general/tema"] == "claro_moderno"
    dlg.b_restablecer.click()
    assert prefs["general/tema"] == "oscuro_moderno" and combo.currentData() == "oscuro_moderno"
    assert elegidos[-1] == "oscuro_moderno"


def test_dialogo_exporta_la_plantilla_a_la_carpeta_de_temas_y_la_suma_a_la_lista(qapp, prefs, tmp_path):
    from omnicad.ui.preferencias import DialogoPreferencias
    dlg = DialogoPreferencias(prefs)
    combo = dlg.controles["general/tema"]
    combo.setCurrentIndex(combo.findData("azul_profesional"))
    ruta = dlg._exportar_plantilla()
    assert ruta == tmp_path / "temas" / "mi_tema.json" and ruta.is_file()
    assert json.loads(ruta.read_text(encoding="utf-8"))["base"] == "azul_profesional"
    assert combo.findData("usuario:mi_tema") >= 0 and combo.currentData() == "azul_profesional"
    assert "Plantilla guardada" in dlg.aviso_tema.text()
    assert dlg._exportar_plantilla().name == "mi_tema_2.json"       # la segunda no pisa a la primera


def test_dialogo_avisa_si_un_tema_propio_tiene_poco_contraste(qapp, prefs, tmp_path):
    from omnicad.ui.preferencias import DialogoPreferencias
    escribir(tmp_path / "temas", "gris.json", {"base": "claro_moderno", "colores": {"texto": "#dddddd"}})
    dlg = DialogoPreferencias(prefs)
    combo = dlg.controles["general/tema"]
    combo.setCurrentIndex(combo.findData("usuario:gris"))
    assert "Contraste" in dlg.aviso_tema.text()
    combo.setCurrentIndex(combo.findData("minimalista"))
    assert "Contraste" not in dlg.aviso_tema.text()


# ---------------------------------------------------------------- captura con --tema
def test_captura_rechaza_un_tema_que_no_existe(capsys):
    from omnicad.ui.captura import main
    with pytest.raises(SystemExit) as e:
        main(["x.png", "--tema", "no_existe"])
    assert e.value.code == 2 and "oscuro_moderno" in capsys.readouterr().err
