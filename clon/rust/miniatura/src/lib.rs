//! Proveedor de miniaturas de Windows para `.omnicad` (H-112): el Explorador muestra la vista del modelo, como
//! hace Fusion con los `.f3d`. Lee `miniatura.png` del ZIP del proyecto sin confiar en el archivo (topes de tamaño,
//! sin `unwrap` ni índices que puedan entrar en pánico: corre dentro del proceso del Explorador o su sustituto) y la
//! entrega como HBITMAP. La registra por usuario `omnicad miniaturas instalar` (HKCU, sin administrador).
#![allow(non_snake_case)]

use std::cell::RefCell;
use std::ffi::c_void;
use std::sync::atomic::{AtomicUsize, Ordering};

use windows::Win32::Foundation::{CLASS_E_CLASSNOTAVAILABLE, CLASS_E_NOAGGREGATION, E_FAIL, E_UNEXPECTED, S_FALSE, S_OK};
use windows::Win32::Graphics::Gdi::{CreateDIBSection, BITMAPINFO, BITMAPINFOHEADER, BI_RGB, DIB_RGB_COLORS, HBITMAP};
use windows::Win32::Graphics::Imaging::{
    CLSID_WICImagingFactory, GUID_WICPixelFormat32bppBGRA, IWICBitmapSource, IWICImagingFactory, WICBitmapInterpolationModeFant,
    WICConvertBitmapSource, WICDecodeMetadataCacheOnDemand,
};
use windows::Win32::System::Com::{
    CoCreateInstance, IClassFactory, IClassFactory_Impl, IStream, CLSCTX_INPROC_SERVER, STREAM_SEEK, STREAM_SEEK_END, STREAM_SEEK_SET,
};
use windows::Win32::UI::Shell::PropertiesSystem::{IInitializeWithStream, IInitializeWithStream_Impl};
use windows::Win32::UI::Shell::{IThumbnailProvider, IThumbnailProvider_Impl, SHCreateMemStream, WTSAT_ARGB, WTS_ALPHATYPE};
use windows_core::{implement, IUnknown, Interface, Ref, BOOL, GUID, HRESULT};

/// CLSID del proveedor; el mismo que escribe `omnicad/cli/cmd_miniaturas.py` en el registro.
pub const CLSID_MINIATURA: GUID = GUID::from_u128(0x179505fe_a2aa_4964_a34d_f0bd6c7531fb);
/// Igual que `TOPE_MINIATURA` de `io_archivos/proyecto.py`.
const TOPE_MINIATURA: usize = 16 * 1024 * 1024;
/// El directorio central de un .omnicad (manifiesto, receta y caché por paso) entra holgado en esto.
const TOPE_DIRECTORIO: usize = 16 * 1024 * 1024;
const NOMBRE: &[u8] = b"miniatura.png";

static OBJETOS: AtomicUsize = AtomicUsize::new(0);

fn u16_en(b: &[u8], i: usize) -> Option<u16> {
    Some(u16::from_le_bytes(b.get(i..i + 2)?.try_into().ok()?))
}

fn u32_en(b: &[u8], i: usize) -> Option<u32> {
    Some(u32::from_le_bytes(b.get(i..i + 4)?.try_into().ok()?))
}

/// Lee exactamente `n` bytes desde `pos` (las lecturas de IStream pueden venir de a pedazos).
fn leer(s: &IStream, pos: u64, n: usize) -> Option<Vec<u8>> {
    unsafe { s.Seek(pos as i64, STREAM_SEEK_SET, None).ok()? };
    let mut buf = vec![0u8; n];
    let mut hecho = 0usize;
    while hecho < n {
        let mut leidos = 0u32;
        let pedido = (n - hecho).min(1 << 20) as u32;
        let hr = unsafe { s.Read(buf.as_mut_ptr().add(hecho) as *mut c_void, pedido, Some(&mut leidos)) };
        if hr.is_err() || leidos == 0 {
            return None;
        }
        hecho += leidos as usize;
    }
    Some(buf)
}

fn largo(s: &IStream) -> Option<u64> {
    let mut fin = 0u64;
    unsafe { s.Seek(0, STREAM_SEEK(STREAM_SEEK_END.0), Some(&mut fin)).ok()? };
    Some(fin)
}

/// `miniatura.png` del ZIP, o None si no está, está rota o pasa los topes. Sin ZIP64: un proyecto de más de 4 GB
/// se queda sin miniatura.
fn miniatura_del_zip(s: &IStream) -> Option<Vec<u8>> {
    let total = largo(s)?;
    let cola = total.min(22 + 65535) as usize;            // fin del directorio central + comentario máximo
    let fin = leer(s, total - cola as u64, cola)?;
    let eocd = (0..=cola.checked_sub(22)?).rev().find(|&i| u32_en(&fin, i) == Some(0x0605_4b50))?;
    let tam_dir = u32_en(&fin, eocd + 12)? as usize;
    let ini_dir = u32_en(&fin, eocd + 16)? as u64;
    if tam_dir > TOPE_DIRECTORIO || ini_dir + tam_dir as u64 > total {
        return None;
    }
    let dir = leer(s, ini_dir, tam_dir)?;
    let mut i = 0usize;
    while u32_en(&dir, i) == Some(0x0201_4b50) {
        let metodo = u16_en(&dir, i + 10)?;
        let comprimido = u32_en(&dir, i + 20)? as usize;
        let original = u32_en(&dir, i + 24)? as usize;
        let (n, e, c) = (u16_en(&dir, i + 28)? as usize, u16_en(&dir, i + 30)? as usize, u16_en(&dir, i + 32)? as usize);
        let local = u32_en(&dir, i + 42)? as u64;
        if dir.get(i + 46..i + 46 + n)? == NOMBRE {
            if comprimido > TOPE_MINIATURA || original > TOPE_MINIATURA {
                return None;
            }
            let cab = leer(s, local, 30)?;
            if u32_en(&cab, 0) != Some(0x0403_4b50) {
                return None;
            }
            let datos = local + 30 + u16_en(&cab, 26)? as u64 + u16_en(&cab, 28)? as u64;
            if datos + comprimido as u64 > total {
                return None;
            }
            let crudo = leer(s, datos, comprimido)?;
            return match metodo {
                0 => Some(crudo),
                8 => miniz_oxide::inflate::decompress_to_vec_with_limit(&crudo, original).ok(),
                _ => None,
            };
        }
        i += 46 + n + e + c;
    }
    None
}

/// PNG → HBITMAP BGRA de arriba hacia abajo, achicado (sin deformar) para que el lado mayor no pase de `cx`.
fn png_a_bitmap(png: &[u8], cx: u32) -> windows_core::Result<HBITMAP> {
    unsafe {
        let wic: IWICImagingFactory = CoCreateInstance(&CLSID_WICImagingFactory, None, CLSCTX_INPROC_SERVER)?;
        let flujo = SHCreateMemStream(Some(png)).ok_or_else(|| windows_core::Error::from(E_FAIL))?;
        let marco = wic.CreateDecoderFromStream(&flujo, std::ptr::null(), WICDecodeMetadataCacheOnDemand)?.GetFrame(0)?;
        let (mut w, mut h) = (0u32, 0u32);
        marco.GetSize(&mut w, &mut h)?;
        if w == 0 || h == 0 {
            return Err(E_FAIL.into());
        }
        let mut fuente: IWICBitmapSource = marco.cast()?;
        let cx = cx.max(1);
        if w.max(h) > cx {
            let (nw, nh) = if w >= h { (cx, (h as u64 * cx as u64 / w as u64).max(1) as u32) } else { ((w as u64 * cx as u64 / h as u64).max(1) as u32, cx) };
            let escala = wic.CreateBitmapScaler()?;
            escala.Initialize(&fuente, nw, nh, WICBitmapInterpolationModeFant)?;
            fuente = escala.cast()?;
            (w, h) = (nw, nh);
        }
        let bgra = WICConvertBitmapSource(&GUID_WICPixelFormat32bppBGRA, &fuente)?;
        let info = BITMAPINFO {
            bmiHeader: BITMAPINFOHEADER {
                biSize: size_of::<BITMAPINFOHEADER>() as u32,
                biWidth: w as i32,
                biHeight: -(h as i32),
                biPlanes: 1,
                biBitCount: 32,
                biCompression: BI_RGB.0,
                ..Default::default()
            },
            ..Default::default()
        };
        let mut bits: *mut c_void = std::ptr::null_mut();
        let bmp = CreateDIBSection(None, &info, DIB_RGB_COLORS, &mut bits, None, 0)?;
        let largo = (w * 4 * h) as usize;
        let destino = std::slice::from_raw_parts_mut(bits as *mut u8, largo);
        if let Err(e) = bgra.CopyPixels(std::ptr::null(), w * 4, destino) {
            let _ = windows::Win32::Graphics::Gdi::DeleteObject(bmp.into());
            return Err(e);
        }
        Ok(bmp)
    }
}

#[implement(IInitializeWithStream, IThumbnailProvider)]
struct Proveedor {
    png: RefCell<Option<Vec<u8>>>,
}

impl Proveedor {
    fn nuevo() -> Self {
        OBJETOS.fetch_add(1, Ordering::SeqCst);
        Proveedor { png: RefCell::new(None) }
    }
}

impl Drop for Proveedor {
    fn drop(&mut self) {
        OBJETOS.fetch_sub(1, Ordering::SeqCst);
    }
}

impl IInitializeWithStream_Impl for Proveedor_Impl {
    fn Initialize(&self, flujo: Ref<IStream>, _modo: u32) -> windows_core::Result<()> {
        let flujo = flujo.ok()?;
        let png = miniatura_del_zip(flujo).ok_or_else(|| windows_core::Error::from(E_FAIL))?;
        *self.png.borrow_mut() = Some(png);
        Ok(())
    }
}

impl IThumbnailProvider_Impl for Proveedor_Impl {
    fn GetThumbnail(&self, cx: u32, phbmp: *mut HBITMAP, alfa: *mut WTS_ALPHATYPE) -> windows_core::Result<()> {
        if phbmp.is_null() || alfa.is_null() {
            return Err(E_UNEXPECTED.into());
        }
        let png = self.png.borrow();
        let png = png.as_deref().ok_or_else(|| windows_core::Error::from(E_UNEXPECTED))?;
        let bmp = png_a_bitmap(png, cx)?;
        unsafe {
            *phbmp = bmp;
            *alfa = WTSAT_ARGB;
        }
        Ok(())
    }
}

#[implement(IClassFactory)]
struct Fabrica;

impl IClassFactory_Impl for Fabrica_Impl {
    fn CreateInstance(&self, externo: Ref<IUnknown>, iid: *const GUID, ppv: *mut *mut c_void) -> windows_core::Result<()> {
        if ppv.is_null() {
            return Err(E_UNEXPECTED.into());
        }
        unsafe { *ppv = std::ptr::null_mut() };
        if externo.is_some() {
            return Err(CLASS_E_NOAGGREGATION.into());
        }
        let objeto: IUnknown = Proveedor::nuevo().into();
        unsafe { objeto.query(iid, ppv).ok() }
    }

    fn LockServer(&self, _bloquear: BOOL) -> windows_core::Result<()> {
        Ok(())
    }
}

#[unsafe(no_mangle)]
extern "system" fn DllGetClassObject(clsid: *const GUID, iid: *const GUID, ppv: *mut *mut c_void) -> HRESULT {
    if clsid.is_null() || iid.is_null() || ppv.is_null() {
        return E_UNEXPECTED;
    }
    unsafe {
        *ppv = std::ptr::null_mut();
        if *clsid != CLSID_MINIATURA {
            return CLASS_E_CLASSNOTAVAILABLE;
        }
        let fabrica: IClassFactory = Fabrica.into();
        fabrica.query(iid, ppv)
    }
}

#[unsafe(no_mangle)]
extern "system" fn DllCanUnloadNow() -> HRESULT {
    if OBJETOS.load(Ordering::SeqCst) == 0 { S_OK } else { S_FALSE }
}

#[cfg(test)]
mod pruebas {
    use super::*;

    /// ZIP de un solo miembro guardado sin comprimir (lo que escribe `proyecto._escribir`).
    fn zip_con(nombre: &[u8], datos: &[u8]) -> Vec<u8> {
        let (n, t) = (nombre.len() as u16, datos.len() as u32);
        let mut z = Vec::new();
        z.extend(0x0403_4b50u32.to_le_bytes());
        z.extend([20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);          // versión, banderas, método 0, hora, CRC
        z.extend(t.to_le_bytes());
        z.extend(t.to_le_bytes());
        z.extend(n.to_le_bytes());
        z.extend(0u16.to_le_bytes());
        z.extend(nombre);
        z.extend(datos);
        let ini_dir = z.len() as u32;
        z.extend(0x0201_4b50u32.to_le_bytes());
        z.extend([20, 0, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);  // versiones, banderas, método 0, hora, CRC
        z.extend(t.to_le_bytes());
        z.extend(t.to_le_bytes());
        z.extend(n.to_le_bytes());
        z.extend([0u8; 12]);                                             // extra, comentario, disco, atributos
        z.extend(0u32.to_le_bytes());                                    // cabecera local en 0
        z.extend(nombre);
        let tam_dir = z.len() as u32 - ini_dir;
        z.extend(0x0605_4b50u32.to_le_bytes());
        z.extend([0, 0, 0, 0, 1, 0, 1, 0]);
        z.extend(tam_dir.to_le_bytes());
        z.extend(ini_dir.to_le_bytes());
        z.extend(0u16.to_le_bytes());
        z
    }

    fn leer_de(bytes: &[u8]) -> Option<Vec<u8>> {
        miniatura_del_zip(&unsafe { SHCreateMemStream(Some(bytes)) }.unwrap())
    }

    #[test]
    fn lee_la_miniatura_y_rechaza_lo_roto() {
        let zip = zip_con(NOMBRE, b"\x89PNG prueba");
        assert_eq!(leer_de(&zip).as_deref(), Some(&b"\x89PNG prueba"[..]));
        assert_eq!(leer_de(&zip_con(b"receta.json", b"{}")), None);     // sin miniatura
        assert_eq!(leer_de(&zip[..zip.len() - 10]), None);              // cortado
        assert_eq!(leer_de(&[0u8; 7]), None);                           // más corto que el fin del ZIP
        assert_eq!(leer_de(&[0x50u8; 3000]), None);                     // basura
    }
}
