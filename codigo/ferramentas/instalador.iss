; TucoTeca — instalador Windows (Inno Setup 6).
;
; Compilado pelo builder, que passa as pastas via /D:
;   iscc /DBuildDir="...\hub" /DVersao="20260924" /O"...\dist" instalador.iss
;
; Clássico: wizard, atalho no Menu Iniciar (+Desktop opcional), desinstalador
; em Adicionar/Remover. Sem admin (instala em %LOCALAPPDATA%\TucoTeca).
; Compressão interna LZMA2/ultra — o .exe final É o pacote (100% offline:
; Python embutido + Azahar + DeSmuME + Citron + app).
; Dados do usuário (dados\) nunca são apagados na desinstalação.

#define AppNome "TucoTeca"
#define AppId "TucoTeca.Hub"

[Setup]
AppId={#AppId}
AppName={#AppNome}
AppVersion={#Versao}
AppPublisher=Tuco
DefaultDirName={localappdata}\TucoTeca
DefaultGroupName={#AppNome}
PrivilegesRequired=lowest
Compression=lzma2/ultra
SolidCompression=yes
LZMANumBlockThreads=2
OutputBaseFilename=TucoTeca-Setup-{#Versao}
WizardStyle=modern
UninstallDisplayIcon={app}\python\pythonw.exe
; dados\ é do usuário: desinstalar remove o app, preserva a coleção
DirExistsWarning=no

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "dados\*"

[Dirs]
Name: "{app}\dados"; Permissions: users-modify
Name: "{app}\dados\backups"
Name: "{app}\dados\capas"
Name: "{app}\dados\presets"
Name: "{app}\dados\sessoes"

[Icons]
Name: "{group}\TucoTeca"; Filename: "{app}\BibliotecaHub.bat"; WorkingDir: "{app}"; IconFilename: "{app}\python\pythonw.exe"
Name: "{group}\TucoTeca (debug, com console)"; Filename: "{app}\Debug-Console.bat"; WorkingDir: "{app}"
Name: "{group}\Desinstalar TucoTeca"; Filename: "{uninstallexe}"
Name: "{autodesktop}\TucoTeca"; Filename: "{app}\BibliotecaHub.bat"; WorkingDir: "{app}"; IconFilename: "{app}\python\pythonw.exe"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Atalho na Área de Trabalho"; Flags: unchecked

[Run]
Filename: "{app}\BibliotecaHub.bat"; Description: "Abrir a TucoTeca agora"; Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
; remove sobras do app, nunca a coleção
Type: files; Name: "{app}\VERSAO.txt"
Type: dirifempty; Name: "{app}\app"
Type: dirifempty; Name: "{app}\python"
Type: dirifempty; Name: "{app}\emuladores"
