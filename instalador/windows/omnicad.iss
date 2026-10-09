; Instalador de OmniCAD para Windows (Inno Setup 6). Lo arma `instalador/armar.py` después de PyInstaller:
;   ISCC.exe /DVersion=0.1.0 instalador\windows\omnicad.iss
; Instala para el usuario actual sin pedir administrador (o para todos, si se elige en el primer diálogo),
; con acceso directo, asociación de los .omnicad y desinstalador. No toca nada fuera de su carpeta salvo lo que
; se elige en «Tareas adicionales».

#ifndef Version
  #define Version "0.0.0"
#endif

[Setup]
AppId={{52D85DCE-E7B9-47FE-AAC7-7612341EAFF0}
AppName=OmniCAD
AppVersion={#Version}
AppVerName=OmniCAD {#Version}
AppPublisher=Proyecto OmniCAD (software libre, GPL-3.0)
AppPublisherURL=https://github.com/JerryblackVe/OmniCAD
AppSupportURL=https://github.com/JerryblackVe/OmniCAD/issues
AppUpdatesURL=https://github.com/JerryblackVe/OmniCAD/releases
DefaultDirName={autopf}\OmniCAD
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\LICENSE
OutputDir=..\dist
OutputBaseFilename=OmniCAD-{#Version}-windows-instalador
SetupIconFile=..\..\clon\omnicad\recursos\omnicad.ico
UninstallDisplayIcon={app}\OmniCAD.exe
UninstallDisplayName=OmniCAD {#Version}
WizardStyle=modern
; La bienvenida muestra la imagen grande (recorte de la portada); Inno Setup 6 la trae apagada.
DisableWelcomePage=no
; El idioma sale del de Windows; solo pregunta si no es ninguno de los dos.
ShowLanguageDialog=auto
; Imágenes del asistente: las arma armar.py desde la portada y el ícono (100 %, 150 % y 200 % de escala).
WizardImageFile=..\build\asistente\grande_100.bmp,..\build\asistente\grande_150.bmp,..\build\asistente\grande_200.bmp
WizardSmallImageFile=..\build\asistente\chica_100.bmp,..\build\asistente\chica_150.bmp,..\build\asistente\chica_200.bmp
Compression=lzma2
SolidCompression=yes
ChangesAssociations=yes
CloseApplications=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
es.Asociar=Abrir los archivos .omnicad con OmniCAD
en.Asociar=Open .omnicad files with OmniCAD
es.Agentes=Conectar los agentes de IA instalados (Claude Code y OpenCode, con copia .bak de cada archivo)
en.Agentes=Connect the installed AI agents (Claude Code and OpenCode, with a .bak copy of each file)
es.ConectandoAgentes=Conectando los agentes de IA…
en.ConectandoAgentes=Connecting the AI agents…
es.TipoProyecto=Proyecto de OmniCAD
en.TipoProyecto=OmniCAD project

[Tasks]
Name: "escritorio"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "asociar"; Description: "{cm:Asociar}"
Name: "agentes"; Description: "{cm:Agentes}"; Flags: unchecked

[Files]
Source: "..\dist\OmniCAD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\OmniCAD"; Filename: "{app}\OmniCAD.exe"
Name: "{autodesktop}\OmniCAD"; Filename: "{app}\OmniCAD.exe"; Tasks: escritorio

[Registry]
; HKA = el usuario actual (o todos, si se instaló para todos).
Root: HKA; Subkey: "Software\Classes\.omnicad"; ValueType: string; ValueName: ""; ValueData: "OmniCAD.Proyecto"; Flags: uninsdeletevalue uninsdeletekeyifempty; Tasks: asociar
Root: HKA; Subkey: "Software\Classes\OmniCAD.Proyecto"; ValueType: string; ValueName: ""; ValueData: "{cm:TipoProyecto}"; Flags: uninsdeletekey; Tasks: asociar
Root: HKA; Subkey: "Software\Classes\OmniCAD.Proyecto\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\OmniCAD.exe,0"; Tasks: asociar
Root: HKA; Subkey: "Software\Classes\OmniCAD.Proyecto\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\OmniCAD.exe"" ""%1"""; Tasks: asociar

[Run]
Filename: "{app}\omnicad-cli.exe"; Parameters: "setup --cliente todos --aplicar"; StatusMsg: "{cm:ConectandoAgentes}"; Flags: runhidden; Tasks: agentes
Filename: "{app}\OmniCAD.exe"; Description: "{cm:LaunchProgram,OmniCAD}"; Flags: nowait postinstall skipifsilent
