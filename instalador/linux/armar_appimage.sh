#!/usr/bin/env bash
# Arma el AppImage de OmniCAD a partir de la carpeta congelada por PyInstaller (instalador/dist/OmniCAD).
# Uso: bash instalador/linux/armar_appimage.sh VERSION   (lo llama instalador/armar.py)
# Baja appimagetool (github.com/AppImage/appimagetool) la primera vez a instalador/build/herramientas/.
set -euo pipefail

VERSION="${1:?falta la versión}"
AQUI="$(cd "$(dirname "$0")" && pwd)"
INSTALADOR="$(dirname "$AQUI")"
REPO="$(dirname "$INSTALADOR")"
DIST="$INSTALADOR/dist"
BUILD="$INSTALADOR/build"
APPDIR="$BUILD/OmniCAD.AppDir"
RECURSOS="$REPO/clon/omnicad/recursos"
HERRAMIENTA="$BUILD/herramientas/appimagetool-x86_64.AppImage"
URL_HERRAMIENTA="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"

[ -d "$DIST/OmniCAD" ] || { echo "Falta $DIST/OmniCAD: corré PyInstaller (instalador/armar.py)." >&2; exit 1; }

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/icons/hicolor/256x256/apps" "$APPDIR/usr/share/icons/hicolor/512x512/apps" \
         "$APPDIR/usr/share/applications" "$APPDIR/usr/share/mime/packages"
cp -a "$DIST/OmniCAD" "$APPDIR/usr/lib/omnicad"
install -m 755 "$AQUI/AppRun" "$APPDIR/AppRun"
install -m 644 "$AQUI/omnicad.desktop" "$APPDIR/omnicad.desktop"
install -m 644 "$AQUI/omnicad.desktop" "$APPDIR/usr/share/applications/omnicad.desktop"
install -m 644 "$AQUI/omnicad-mime.xml" "$APPDIR/usr/share/mime/packages/omnicad.xml"
install -m 644 "$RECURSOS/omnicad_256.png" "$APPDIR/omnicad.png"
install -m 644 "$RECURSOS/omnicad_256.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/omnicad.png"
install -m 644 "$RECURSOS/omnicad_512.png" "$APPDIR/usr/share/icons/hicolor/512x512/apps/omnicad.png"
ln -sf omnicad.png "$APPDIR/.DirIcon"

if [ ! -x "$HERRAMIENTA" ]; then
    mkdir -p "$(dirname "$HERRAMIENTA")"
    echo "» bajando appimagetool de $URL_HERRAMIENTA"
    curl -fL --retry 3 -o "$HERRAMIENTA" "$URL_HERRAMIENTA"
    chmod +x "$HERRAMIENTA"
fi

SALIDA="$DIST/OmniCAD-$VERSION-x86_64.AppImage"
# Sin FUSE (WSL, contenedores de CI) appimagetool se extrae y corre solo.
APPIMAGE_EXTRACT_AND_RUN=1 ARCH=x86_64 "$HERRAMIENTA" --no-appstream "$APPDIR" "$SALIDA"
chmod +x "$SALIDA"
echo "AppImage: $SALIDA"
