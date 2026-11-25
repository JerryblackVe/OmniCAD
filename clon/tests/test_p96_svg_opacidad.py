"""P-96: los rellenos invisibles no crean perfiles extra."""
from omnicad.io_archivos.svg import leer_svg, listar_capas_svg


def test_p96_svg_descarta_rellenos_casi_transparentes(tmp_path):
    ruta = tmp_path / "opacidad.svg"
    ruta.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="20mm" viewBox="0 0 40 20">'
        '<rect id="normal" width="10" height="10"/>'
        '<rect id="pestana" x="10" width="2" height="10" fill-opacity="0.001"/>'
        '<g opacity="0.005"><rect id="grupo" width="30" height="2"/></g>'
        '<rect id="estilo" x="20" width="2" height="10" style="fill-opacity:0.5%"/>'
        '<g fill-opacity="0.001"><rect id="heredado" width="2" height="2"/>'
        '<rect id="trazo" x="30" width="2" height="2" stroke="#000000"/></g>'
        '</svg>', encoding="utf-8")
    prims = leer_svg(ruta)
    assert [f["nombre"] for f in prims.formas] == ["normal", "trazo"]
    assert [f["relleno"] for f in prims.formas] == [True, False]
    assert listar_capas_svg(ruta)["total"] == len(prims)
