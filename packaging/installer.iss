#ifndef PayloadDir
  #error PayloadDir must be supplied by build_windows.py
#endif
#ifndef ReleaseDir
  #error ReleaseDir must be supplied by build_windows.py
#endif
#ifndef AppVersion
  #define AppVersion "0.1.0a1"
#endif

[Setup]
AppId={{2F601791-C674-48F3-A66A-42D84CC0E178}
AppName=Slicer Profile Lab Alpha
AppVersion={#AppVersion}
AppPublisher=WhereIsEggs
AppPublisherURL=https://github.com/WhereIsEggs/slicer-profile-lab
AppSupportURL=https://github.com/WhereIsEggs/slicer-profile-lab/issues
DefaultDirName={localappdata}\Programs\Slicer Profile Lab Alpha
DefaultGroupName=Slicer Profile Lab Alpha
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\SlicerProfileLab.exe
OutputDir={#ReleaseDir}
OutputBaseFilename=SlicerProfileLab-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
InfoBeforeFile=alpha-notice.txt
LicenseFile=..\LICENSE.txt
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked

[Icons]
Name: "{group}\Slicer Profile Lab Alpha"; Filename: "{app}\SlicerProfileLab.exe"
Name: "{group}\Alpha testing guide"; Filename: "{app}\_internal\docs\alpha-testing.md"
Name: "{group}\License"; Filename: "{app}\_internal\LICENSE.txt"
Name: "{autodesktop}\Slicer Profile Lab Alpha"; Filename: "{app}\SlicerProfileLab.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\SlicerProfileLab.exe"; Description: "Open Slicer Profile Lab Alpha"; Flags: nowait postinstall skipifsilent

; No UninstallDelete entries: never remove app data or Orca profiles.
