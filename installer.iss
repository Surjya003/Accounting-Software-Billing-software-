; =====================================================================
; BillFlow Suite - Professional Inno Setup 6 / 7 Installer Script
; Publisher: Binapani Automation | Author: Surjyakamal Saha
; AppId GUID: {B111F10A-7C1B-4A5D-8E2F-1A3C5B7D9E0F}
; =====================================================================

#define MyAppName "BillFlow Suite"
#define MyAppPublisher "Binapani Automation"
#define MyAppPublisherURL ""
#define MyAppExeName "BillFlow.exe"
#define MyAppId "{B111F10A-7C1B-4A5D-8E2F-1A3C5B7D9E0F}"

; Derive version from compiled executable if present, else fallback
#ifndef AppVersion
  #if FileExists("dist\BillFlow.exe")
    #define AppVersion GetVersionNumbersString("dist\BillFlow.exe")
  #elif FileExists("dist\BillFlow\BillFlow.exe")
    #define AppVersion GetVersionNumbersString("dist\BillFlow\BillFlow.exe")
  #else
    #define AppVersion "1.0.0"
  #endif
#endif

[Setup]
AppId={{#MyAppId}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} v{#AppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppPublisherURL}
AppSupportURL={#MyAppPublisherURL}
AppUpdatesURL={#MyAppPublisherURL}
AppCopyright=Copyright (C) 2024-2026 Binapani Automation. Made by Surjyakamal Saha
DefaultDirName={autopf}\BillFlow Suite
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=release
OutputBaseFilename=BillFlow_Setup_v{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; Installation Scope: Default per-user (no admin required), let user choose in wizard
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; 64-bit Architecture enforcement
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; Application Process & Mutex detection
AppMutex=BillFlowSuite_SingleInstance_Mutex
CloseApplications=yes
RestartApplications=no

; Icons and Visual Branding
SetupIconFile=assets\branding\app.ico
WizardImageFile=assets\branding\wizard.bmp
WizardSmallImageFile=assets\branding\wizard_small.bmp
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

DisableProgramGroupPage=auto
DisableDirPage=auto
ShowLanguageDialog=no

; Conditional EULA Page (only if docs\EULA.txt exists)
#if FileExists("docs\EULA.txt")
LicenseFile=docs\EULA.txt
#endif

; Code Signing Configuration Placeholder:
; To sign with an EV/OV code signing certificate or Azure Trusted Signing:
; SignTool=signtool sign /fd SHA256 /a /tr http://timestamp.digicert.com /td SHA256 $f

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
ClickFinish=Click Finish to exit Setup.%n%nMade by Surjyakamal Saha

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Dirs]
; Writable enterprise financial data folders in %APPDATA%\BillFlow with uninsneveruninstall flag
Name: "{userappdata}\BillFlow\data"; Flags: uninsneveruninstall; Permissions: users-modify
Name: "{userappdata}\BillFlow\backups"; Flags: uninsneveruninstall; Permissions: users-modify
Name: "{userappdata}\BillFlow\logs"; Flags: uninsneveruninstall; Permissions: users-modify
Name: "{userappdata}\BillFlow\exports"; Flags: uninsneveruninstall; Permissions: users-modify
Name: "{userappdata}\BillFlow\themes"; Flags: uninsneveruninstall; Permissions: users-modify

[Files]
#if FileExists("dist\BillFlow.exe")
; Standalone single-file PyInstaller executable (portable, zero external DLL dependencies)
Source: "dist\BillFlow.exe"; DestDir: "{app}"; Flags: ignoreversion
#else
; Standalone PyInstaller onedir output bundle
Source: "dist\BillFlow\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "BillFlow Suite - Offline Accounting & Billing"
Name: "{autoprograms}\{#MyAppName}\Open BillFlow Data Folder"; Filename: "{win}\explorer.exe"; Parameters: """{userappdata}\BillFlow"""
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// =====================================================================
// Helper: Parse version string 'X.Y.Z' or 'X.Y.Z.W' into 4-part integers
// =====================================================================
procedure ParseVersion(VStr: String; var V1, V2, V3, V4: Integer);
var
  P, N: Integer;
  Part: String;
begin
  V1 := 0; V2 := 0; V3 := 0; V4 := 0;
  N := 1;
  while Length(VStr) > 0 do
  begin
    P := Pos('.', VStr);
    if P > 0 then
    begin
      Part := Copy(VStr, 1, P - 1);
      Delete(VStr, 1, P);
    end
    else
    begin
      Part := VStr;
      VStr := '';
    end;
    case N of
      1: V1 := StrToIntDef(Part, 0);
      2: V2 := StrToIntDef(Part, 0);
      3: V3 := StrToIntDef(Part, 0);
      4: V4 := StrToIntDef(Part, 0);
    end;
    Inc(N);
  end;
end;

function CompareVersions(V1Str, V2Str: String): Integer;
var
  A1, A2, A3, A4: Integer;
  B1, B2, B3, B4: Integer;
begin
  ParseVersion(V1Str, A1, A2, A3, A4);
  ParseVersion(V2Str, B1, B2, B3, B4);

  if A1 > B1 then Result := 1
  else if A1 < B1 then Result := -1
  else if A2 > B2 then Result := 1
  else if A2 < B2 then Result := -1
  else if A3 > B3 then Result := 1
  else if A3 < B3 then Result := -1
  else if A4 > B4 then Result := 1
  else if A4 < B4 then Result := -1
  else Result := 0;
end;

// =====================================================================
// InitializeSetup: Downgrade Protection & Prerequisite Checking
// =====================================================================
function InitializeSetup(): Boolean;
var
  InstalledVer: String;
  RegKey: String;
begin
  Result := True;
  RegKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + ExpandConstant('{#MyAppId}') + '_is1';

  // Check 64-bit and 32-bit registry view across HKLM and HKCU
  if not RegQueryStringValue(HKLM64, RegKey, 'DisplayVersion', InstalledVer) then
    if not RegQueryStringValue(HKCU64, RegKey, 'DisplayVersion', InstalledVer) then
      if not RegQueryStringValue(HKLM32, RegKey, 'DisplayVersion', InstalledVer) then
        RegQueryStringValue(HKCU32, RegKey, 'DisplayVersion', InstalledVer);

  if Length(InstalledVer) > 0 then
  begin
    // Check if installed version is newer than current setup version
    if CompareVersions(InstalledVer, '{#AppVersion}') > 0 then
    begin
      MsgBox('A newer version of BillFlow Suite (' + InstalledVer + ') is already installed.' + #13#10 + #13#10 +
             'Downgrading to version {#AppVersion} is not supported to protect your database schema.' + #13#10 +
             'Setup will now exit.', mbCriticalError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

// =====================================================================
// InitializeUninstall: Check if application is running before uninstall
// =====================================================================
function InitializeUninstall(): Boolean;
begin
  Result := True;
  if CheckForMutexes('BillFlowSuite_SingleInstance_Mutex') then
  begin
    MsgBox('BillFlow Suite is currently running.' + #13#10 + #13#10 +
           'Please save your work and close BillFlow Suite before continuing uninstallation.', mbError, MB_OK);
    Result := False;
  end;
end;

// =====================================================================
// CurUninstallStepChanged: Preserving or Safely Deleting User Data
// =====================================================================
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
  PromptMsg: String;
  ShouldDelete: Boolean;
  Idx: Integer;
  Param: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\BillFlow');
    ShouldDelete := False;

    // Check command-line silent parameter /DELETEDATA=1
    for Idx := 1 to ParamCount do
    begin
      Param := UpperCase(ParamStr(Idx));
      if (Param = '/DELETEDATA=1') or (Param = '-DELETEDATA=1') then
        ShouldDelete := True;
    end;

    // If interactive uninstall, ask explicitly (defaulting to NO)
    if not WizardSilent then
    begin
      PromptMsg := 'Do you also want to delete your BillFlow financial data, company profile, and backups in:' + #13#10 +
                   DataDir + #13#10 + #13#10 +
                   '(Choose No to safely KEEP your accounting books and backups).';
      if MsgBox(PromptMsg, mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        ShouldDelete := True;
    end;

    if ShouldDelete then
    begin
      if DirExists(DataDir) then
        DelTree(DataDir, True, True, True);
    end
    else
    begin
      if not WizardSilent then
      begin
        MsgBox('BillFlow Suite binaries have been uninstalled successfully.' + #13#10 + #13#10 +
               'NOTE: To protect your business books, your accounting databases and backups in:' + #13#10 +
               DataDir + #13#10 +
               'have been safely PRESERVED.', mbInformation, MB_OK);
      end;
    end;
  end;
end;
