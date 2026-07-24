#define MyAppName "Türkmenabat ERP"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Türkmenabat"
#define MyAppExeName "Turkmenabat ERP.exe"

[Setup]
AppId={{B3670E77-89C8-42E6-9BA8-F91E6CBBBA7E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Turkmenabat ERP
DefaultGroupName=Turkmenabat ERP
OutputDir=output
OutputBaseFilename=Turkmenabat-ERP-Setup-v1.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\Turkmenabat ERP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent
