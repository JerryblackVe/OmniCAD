//! Descompresor Zstandard del `.f3d` (RS-R1): misma salida y mismos errores que `io_archivos/zstd_puro.py`, que queda
//! como referencia y respaldo. Datos puros: bytes dentro, bytes fuera, sin soltar nada al intérprete salvo el GIL.
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use ruzstd::decoding::{BlockDecodingStrategy, FrameDecoder};

const MAGICO: u32 = 0xFD2F_B528;
const TRUNCADA: &str = "Trama Zstandard truncada.";

fn descomprimir(datos: &[u8], tope: Option<usize>) -> Result<Vec<u8>, String> {
    let mut decodificador = FrameDecoder::new();
    let mut entrada = datos;
    let mut salida: Vec<u8> = Vec::new();
    let mut trozo = vec![0u8; 1 << 20];
    while !entrada.is_empty() {
        let cabecera: [u8; 4] = entrada.get(..4).and_then(|b| b.try_into().ok()).ok_or(TRUNCADA)?;
        let magico = u32::from_le_bytes(cabecera);
        if magico & 0xFFFF_FFF0 == 0x184D_2A50 {
            // trama salteable (metadatos): se ignora
            let largo: [u8; 4] = entrada.get(4..8).and_then(|b| b.try_into().ok()).ok_or(TRUNCADA)?;
            entrada = entrada.get(8usize.saturating_add(u32::from_le_bytes(largo) as usize)..).ok_or(TRUNCADA)?;
            continue;
        }
        if magico != MAGICO {
            return Err("No es Zstandard (número mágico incorrecto).".into());
        }
        decodificador.init(&mut entrada).map_err(|e| format!("Zstandard inválido: {e}"))?;
        loop {
            decodificador
                .decode_blocks(&mut entrada, BlockDecodingStrategy::UptoBytes(1 << 20))
                .map_err(|e| format!("Zstandard inválido: {e}"))?;
            while decodificador.can_collect() > 0 {
                let n = std::io::Read::read(&mut decodificador, &mut trozo).map_err(|e| format!("Zstandard inválido: {e}"))?;
                if n == 0 {
                    break;
                }
                if tope.is_some_and(|t| salida.len() + n > t) {
                    return Err(format!(
                        "La salida Zstandard pasa el tope de {} bytes: el archivo parece dañado o hostil.",
                        tope.unwrap_or(0)
                    ));
                }
                salida.extend_from_slice(&trozo[..n]);
            }
            if decodificador.is_finished() {
                break;
            }
        }
    }
    Ok(salida)
}

/// Descomprime una o varias tramas Zstandard seguidas. `tope`: falla apenas la salida pasa esa cantidad de bytes.
#[pyfunction]
#[pyo3(signature = (datos, tope=None))]
pub fn zstd_descomprimir<'py>(py: Python<'py>, datos: &[u8], tope: Option<usize>) -> PyResult<Bound<'py, PyBytes>> {
    let salida = py.allow_threads(|| descomprimir(datos, tope)).map_err(PyValueError::new_err)?;
    Ok(PyBytes::new(py, &salida))
}

#[cfg(test)]
mod pruebas {
    use super::*;

    fn cruda(datos: &[u8]) -> Vec<u8> {
        // Trama de un solo bloque crudo y último, sin checksum: FHD con tamaño de contenido de 4 bytes.
        let mut t = MAGICO.to_le_bytes().to_vec();
        t.push(0x80 | 0x20);
        t.extend((datos.len() as u32).to_le_bytes());
        let cab = (datos.len() as u32) << 3 | 1; // último bloque, tipo crudo
        t.extend(&cab.to_le_bytes()[..3]);
        t.extend(datos);
        t
    }

    #[test]
    fn dos_tramas_y_una_salteable() {
        let mut t = cruda(b"hola ");
        t.extend(0x184D_2A50u32.to_le_bytes());
        t.extend(3u32.to_le_bytes());
        t.extend(b"xyz");
        t.extend(cruda(b"mundo"));
        assert_eq!(descomprimir(&t, None).unwrap(), b"hola mundo");
    }

    #[test]
    fn errores_y_tope() {
        assert!(descomprimir(b"no es zstd", None).unwrap_err().contains("mágico"));
        assert_eq!(descomprimir(&MAGICO.to_le_bytes()[..3], None).unwrap_err(), TRUNCADA);
        assert!(descomprimir(&cruda(b"0123456789"), Some(9)).unwrap_err().contains("tope"));
        assert_eq!(descomprimir(&cruda(b"0123456789"), Some(10)).unwrap().len(), 10);
        assert!(descomprimir(&cruda(b"0123456789")[..14], None).is_err());
    }
}
