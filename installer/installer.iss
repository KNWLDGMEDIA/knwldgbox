; ============================================================================
; KNWLDGBox — Inno Setup installer script
;
; Expects a fully assembled payload in installer\payload\ (produced by
; build_windows.ps1):
;   payload\python\                  standalone CPython runtime
;   payload\backend\                 FastAPI backend source
;   payload\app\dist\                built Vue frontend
;   payload\tools\ffmpeg\            ffmpeg.exe / ffprobe.exe (optional)
;   payload\playwright-browsers\     bundled Chromium (optional)
;   payload\wheels\                  offline Python packages (deleted post-install)
;   payload\icon.ico                 app icon (optional)
;   payload\MicrosoftEdgeWebview2Setup.exe
;
; Compile:  ISCC.exe /DAppVersion=1.0.0 installer.iss
; ============================================================================

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#define AppName "KNWLDGBox"
#define AppPublisher "KNWLDGMEDIA"
#define AppURL "https://github.com/KNWLDGMEDIA/knwldgbox"

[Setup]
AppId={{C4D2E8F1-7A3B-4E5F-9D1C-2B6A8E0F3D47}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=KNWLDGBox-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
CloseApplications=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\icon.ico
#if FileExists("payload\icon.ico")
SetupIconFile=payload\icon.ico
#endif

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
; Python runtime, backend, frontend, tools
Source: "payload\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "payload\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "payload\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "payload\tools\*"; DestDir: "{app}\tools"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "payload\playwright-browsers\*"; DestDir: "{app}\playwright-browsers"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "payload\icon.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; Offline Python packages — only needed during installation
Source: "payload\wheels\*"; DestDir: "{tmp}\wheels"; Flags: ignoreversion recursesubdirs createallsubdirs deleteafterinstall
; WebView2 evergreen bootstrapper — only needed during installation
Source: "payload\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\backend\launcher.py"""; WorkingDir: "{app}\backend"; IconFilename: "{app}\icon.ico"; Comment: "Launch {#AppName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\backend\launcher.py"""; WorkingDir: "{app}\backend"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
; WebView2 runtime is required by pywebview (only installed if missing)
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; \
    Check: not IsWebView2Installed; StatusMsg: "Installing Microsoft Edge WebView2 Runtime..."; Flags: waituntilterminated
; Offer to launch the app when finished (opt-in)
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\backend\launcher.py"""; WorkingDir: "{app}\backend"; \
    Description: "Launch {#AppName}"; Flags: postinstall nowait unchecked

[Code]
{ ---------------------------------------------------------------------------- }

function IsWebView2Installed(): Boolean;
var
  Version: String;
begin
  Result :=
    RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) or
    RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version) or
    RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', Version);
end;

{ Install all Python dependencies offline from the bundled wheels.
  Shims (sherlock.exe, maigret.exe, yt-dlp.exe, holehe.exe, ...) are generated
  here so they embed the *actual* install path chosen by the user. }
function InstallPythonPackages(): Boolean;
var
  ResultCode: Integer;
  PyExe, Wheels, ReqFile, LogFile, Params: String;
begin
  PyExe   := ExpandConstant('{app}\python\python.exe');
  Wheels  := ExpandConstant('{tmp}\wheels');
  ReqFile := ExpandConstant('{app}\backend\requirements.txt');
  LogFile := ExpandConstant('{app}\install-pip.log');

  Params := '/c ""' + PyExe + '" -m pip install --no-index --find-links "' + Wheels + '" --upgrade pip setuptools wheel'
          + ' && "' + PyExe + '" -m pip install --no-index --find-links "' + Wheels + '" --no-build-isolation -r "' + ReqFile + '"'
          + ' > "' + LogFile + '" 2>&1"';

  if not Exec(ExpandConstant('{cmd}'), Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := False;
    exit;
  end;
  Result := (ResultCode = 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    WizardForm.StatusLabel.Caption := 'Installing Python components (this may take a few minutes)...';
    WizardForm.Refresh;
    if not InstallPythonPackages() then
    begin
      if MsgBox('Failed to install the Python components.' #13#10
        + 'See "install-pip.log" in the installation folder for details.' #13#10#13#10
        + 'Abort the installation?', mbCriticalError, MB_YESNO) = IDYES then
      begin
        Abort();
      end;
    end;
  end;
end;
