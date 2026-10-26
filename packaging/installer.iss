; Per-user application installer. Content libraries and DAZ settings are never managed here.
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef BuildRoot
  #define BuildRoot "..\dist\Daz3DProductResolver"
#endif
#ifndef OutputRoot
  #define OutputRoot "..\dist\release"
#endif
[Setup]
AppId={{0473D621-CE06-4A23-BD23-70F310C5440E}
AppName=Daz 3D Product Resolver
AppVersion={#AppVersion}
AppPublisher=enaielei
AppPublisherURL=https://github.com/enaielei/daz-3d-product-resolver
AppSupportURL=https://github.com/enaielei/daz-3d-product-resolver/issues
DefaultDirName={localappdata}\Programs\Daz3DProductResolver
DefaultGroupName=Daz 3D Product Resolver
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
OutputDir={#OutputRoot}
OutputBaseFilename=Daz3DProductResolver-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=110
LicenseFile=..\LICENSE
UninstallDisplayIcon={app}\Daz3DProductResolver.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
UsePreviousAppDir=not IsTestInstall
CreateUninstallRegKey=not IsTestInstall
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "{#BuildRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{userprograms}\Daz 3D Product Resolver"; Filename: "{app}\Daz3DProductResolver.exe"; Check: not IsTestInstall
Name: "{userdesktop}\Daz 3D Product Resolver"; Filename: "{app}\Daz3DProductResolver.exe"; Tasks: desktopicon; Check: not IsTestInstall
[Run]
Filename: "{app}\Daz3DProductResolver.exe"; Description: "Open Daz 3D Product Resolver"; Flags: nowait postinstall skipifsilent
[Code]
function IsTestInstall: Boolean;
begin
  Result := ExpandConstant('{param:PORTABLETEST|0}') = '1';
end;
