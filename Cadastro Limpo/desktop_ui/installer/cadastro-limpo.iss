; Cadastro Limpo — Inno Setup 6
; Pré-requisito: https://jrsoftware.org/isinfo.php
; Depois de rodar tools/desktop_ui/build_windows.ps1 a partir de tools/:
;   ISCC cadastro-limpo.iss   (ou abrir no Compiler IDE)
; Gera Output\cadastro-limpo-setup-<versão>.exe relativo a este ficheiro.

#define MyAppName "Cadastro Limpo"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Felipe Raposo"
#define MyAppExeName "cadastro-limpo.exe"

[Setup]
AppId={{B4C8E2A6-9F0D-4C1E-B7A3-8D5E2F1C9A0B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=cadastro-limpo-setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=no
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\cadastro-limpo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
