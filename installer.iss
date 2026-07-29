; Script generated for CipherDNS Modern Windows Installer
#define MyAppName "CipherDNS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CipherDNS Team"
#define MyAppURL "https://github.com/HeadTDev/cipherdns"
#define MyAppExeName "CipherDNS.exe"

[Setup]
AppId={{D9534F26-8870-4649-86BF-1DCDC1488706}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=dist
OutputBaseFilename=CipherDNS_Setup
SetupIconFile=assets\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=no
PrivilegesRequired=admin
ArchitecturesAllowed=x64 arm64
ArchitecturesInstallIn64BitMode=x64 arm64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostarticon"; Description: "Run CipherDNS automatically on Windows startup"; GroupDescription: "Options:"; Flags: unchecked

[Files]
Source: "dist\CipherDNS_Portable.exe"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "CipherDNS"; ValueData: """{app}\{#MyAppExeName}"" --autostart"; Tasks: autostarticon; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function IsWindowsDarkMode(): Boolean;
var
  AppsUseLightTheme: Cardinal;
begin
  Result := False;
  if RegQueryDWordValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize', 'AppsUseLightTheme', AppsUseLightTheme) then
  begin
    Result := (AppsUseLightTheme = 0);
  end;
end;

procedure InitializeWizard();
begin
  if IsWindowsDarkMode() then
  begin
    WizardForm.MainPanel.Color := $121212;
    WizardForm.PageNameLabel.Font.Color := $4F53D9;
    WizardForm.PageDescriptionLabel.Font.Color := $A0A0A0;
    WizardForm.WelcomeLabel1.Font.Color := $FFFFFF;
    WizardForm.WelcomeLabel2.Font.Color := $D0D0D0;
    WizardForm.FinishedHeadingLabel.Font.Color := $FFFFFF;
    WizardForm.FinishedLabel.Font.Color := $D0D0D0;
  end;
end;
