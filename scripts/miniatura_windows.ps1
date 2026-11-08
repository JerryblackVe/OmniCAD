# Pide a Windows la miniatura de un archivo (IShellItemImageFactory, solo miniatura: sin caer al ícono) y la guarda
# como PNG. Sirve para comprobar el lector de miniaturas de los .omnicad (H-112) sin abrir el Explorador.
# Uso: powershell -ExecutionPolicy Bypass -File scripts/miniatura_windows.ps1 <archivo> <salida.png> [tamaño]
param([Parameter(Mandatory)][string]$Archivo, [Parameter(Mandatory)][string]$Salida, [int]$Tam = 256)
$ErrorActionPreference = "Stop"
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System; using System.Drawing; using System.Runtime.InteropServices;
public static class Miniatura {
    [StructLayout(LayoutKind.Sequential)] public struct SIZE { public int cx, cy; }
    [ComImport, Guid("bcc18b79-ba16-442f-80c4-8a59c30c463b"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IShellItemImageFactory { [PreserveSig] int GetImage(SIZE size, int flags, out IntPtr phbm); }
    [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
    static extern void SHCreateItemFromParsingName(string path, IntPtr pbc, [MarshalAs(UnmanagedType.LPStruct)] Guid riid,
        [MarshalAs(UnmanagedType.Interface)] out IShellItemImageFactory item);
    [DllImport("gdi32.dll")] static extern bool DeleteObject(IntPtr h);
    public static void Guardar(string archivo, string salida, int tam) {
        IShellItemImageFactory f;
        SHCreateItemFromParsingName(archivo, IntPtr.Zero, typeof(IShellItemImageFactory).GUID, out f);
        IntPtr hbm;
        int hr = f.GetImage(new SIZE { cx = tam, cy = tam }, 0x8, out hbm);   // SIIGBF_THUMBNAILONLY
        if (hr != 0) throw new Exception("Windows no generó miniatura (HRESULT 0x" + hr.ToString("X8") + ")");
        try { using (var b = Image.FromHbitmap(hbm)) { b.Save(salida); Console.WriteLine("miniatura " + b.Width + "x" + b.Height + " -> " + salida); } }
        finally { DeleteObject(hbm); }
    }
}
"@
[Miniatura]::Guardar((Resolve-Path $Archivo).Path, [IO.Path]::GetFullPath($Salida), $Tam)
