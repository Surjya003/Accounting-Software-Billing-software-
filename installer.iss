; BillFlow Suite - Inno Setup 6 Installer Script
; Packages standalone PyInstaller distribution into an enterprise Windows setup executable.

#define MyAppName "BillFlow Suite"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Vyapar Software Solutions"
#define MyAppURL "https://billflow.vyaparsoftware.com"
#define MyAppExeName "BillFlow.exe"

[Setup]
; Unique GUID for BillFlow Suite
AppId={{9F2D8E3A-7C1B-4A5D-8E2F-1A3C5B7D9E0F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\BillFlow
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=docs\COMPLIANCE.md
OutputDir=dist_installer
OutputBaseFilename=BillFlow_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableDirPage=no
DisableProgramGroupPage=no
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
; Ensure user financial data folders are created in %APPDATA%\BillFlow with uninsneveruninstall protection
Name: "{userappdata}\BillFlow\data"; Flags: uninsneveruninstall
Name: "{userappdata}\BillFlow\backups"; Flags: uninsneveruninstall
Name: "{userappdata}\BillFlow\logs"; Flags: uninsneveruninstall
Name: "{userappdata}\BillFlow\exports"; Flags: uninsneveruninstall

[Files]
; Standalone application bundle produced by PyInstaller (dist\BillFlow\*)
Source: "dist\BillFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Indian B2B GST Billing & Accounting Software"
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autoprograms}\{#MyAppName}\Open Financial Data Folder"; Filename: "{win}\explorer.exe"; Parameters: """{userappdata}\BillFlow"""
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Inform the user that financial databases and backups are preserved upon uninstallation
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    MsgBox('BillFlow Suite binaries have been removed successfully.' + #13#10 + #13#10 +
           'NOTE: To protect your business books, your accounting databases and backups in:' + #13#10 +
           ExpandConstant('{userappdata}\BillFlow') + #13#10 +
           'have been safely PRESERVED and NOT deleted.', mbInformation, MB_OK);
  end;
end;
