#define MyAppName "SoundByte"
#define MyAppVersion "1.0"
#define MyAppPublisher "Philip Ayo"
#define MyAppExe "SoundByte.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExe}
OutputBaseFilename=SoundByte-Installer
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\SoundByte.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "logo.png"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\SoundByte"; Filename: "{app}\{#MyAppExe}"
Name: "{commondesktop}\SoundByte"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon
Name: "{userstartup}\SoundByte"; Filename: "{app}\{#MyAppExe}"; Tasks: startupicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "startupicon"; Description: "Run SoundByte at startup"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch SoundByte"; Flags: nowait postinstall skipifsilent