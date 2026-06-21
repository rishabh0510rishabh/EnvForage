; Inno Setup Script for EnvForage

[Setup]
AppId={{5DCE63EF-A39B-4DDF-90A0-B6D7D3193C5F}
AppName=EnvForage
AppVersion=2.0.0
DefaultDirName={autopf}\EnvForage
DefaultGroupName=EnvForage
PrivilegesRequired=none
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=Output
OutputBaseFilename=envforage-v2.0.0-setup
SetupIconFile=logo.ico
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
AppPublisher=EnvForage Contributors
AppSupportURL=https://github.com/rishabh0510rishabh/EnvForage
AppUpdatesURL=https://github.com/rishabh0510rishabh/EnvForage/releases
DisableProgramGroupPage=yes
ChangesEnvironment=yes

[Files]
Source: "..\dist\envforage.exe"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: envpath; Description: "Add EnvForage to your PATH environment variable"; Flags: unchecked
Name: DirectoryContext; Description: "Add 'Diagnose ML Environment Here' to directory right-click context menu"; Flags: unchecked
Name: FileContext; Description: "Add 'Generate Repair Script with EnvForage' to JSON file right-click context menu"; Flags: unchecked
Name: ProtocolHandler; Description: "Register envforage:// custom URL protocol handler"; Flags: unchecked

[Registry]
; Context menu for Directory background
Root: HKA; Subkey: "Software\Classes\Directory\Background\shell\EnvForageDiagnose"; ValueType: string; ValueName: ""; ValueData: "Diagnose ML Environment Here"; Flags: uninsdeletekey; Tasks: DirectoryContext
Root: HKA; Subkey: "Software\Classes\Directory\Background\shell\EnvForageDiagnose"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\envforage.exe"""; Flags: uninsdeletekey; Tasks: DirectoryContext
Root: HKA; Subkey: "Software\Classes\Directory\Background\shell\EnvForageDiagnose\command"; ValueType: string; ValueName: ""; ValueData: "cmd.exe /k """"{app}\envforage.exe"" diagnose"""; Flags: uninsdeletekey; Tasks: DirectoryContext

; Context menu for JSON files
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.json\shell\EnvForageFix"; ValueType: string; ValueName: ""; ValueData: "Generate Repair Script with EnvForage"; Flags: uninsdeletekey; Tasks: FileContext
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.json\shell\EnvForageFix"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\envforage.exe"""; Flags: uninsdeletekey; Tasks: FileContext
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.json\shell\EnvForageFix\command"; ValueType: string; ValueName: ""; ValueData: "cmd.exe /k """"{app}\envforage.exe"" fix --report ""%1"""""; Flags: uninsdeletekey; Tasks: FileContext

; Custom URL protocol handler
Root: HKA; Subkey: "Software\Classes\envforage"; ValueType: string; ValueName: ""; ValueData: "URL:EnvForage Protocol"; Flags: uninsdeletekey; Tasks: ProtocolHandler
Root: HKA; Subkey: "Software\Classes\envforage"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""; Flags: uninsdeletekey; Tasks: ProtocolHandler
Root: HKA; Subkey: "Software\Classes\envforage\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\envforage.exe"",0"; Flags: uninsdeletekey; Tasks: ProtocolHandler
Root: HKA; Subkey: "Software\Classes\envforage\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\envforage.exe"" diagnose --send ""%1"""; Flags: uninsdeletekey; Tasks: ProtocolHandler

[UninstallDelete]
Type: filesandordirs; Name: "{%USERPROFILE}\.envforage"

[Code]
var
  GpuWarningLabel: TNewStaticText;
  ExistingInstallPage: TInputOptionWizardPage;
  ProgressPage: TOutputProgressWizardPage;

function GetInstalledUninstallString(var UninstallString: string): Boolean;
var
  RegPath, RegPathLegacy: string;
begin
  Result := False;
  RegPath := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{5DCE63EF-A39B-4DDF-90A0-B6D7D3193C5F}_is1';
  RegPathLegacy := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{5DCE63EF-A39B-4DDF-90A0-B6D7D3193C5F}}_is1';
  if RegQueryStringValue(HKLM, RegPath, 'UninstallString', UninstallString) or
     RegQueryStringValue(HKLM, RegPathLegacy, 'UninstallString', UninstallString) then
  begin
    Result := True;
    Exit;
  end;
  if RegQueryStringValue(HKCU, RegPath, 'UninstallString', UninstallString) or
     RegQueryStringValue(HKCU, RegPathLegacy, 'UninstallString', UninstallString) then
  begin
    Result := True;
    Exit;
  end;
end;

function CleanQuotes(S: string): string;
begin
  Result := S;
  if Length(Result) > 0 then
  begin
    if Result[1] = '"' then
      Delete(Result, 1, 1);
    if (Length(Result) > 0) and (Result[Length(Result)] = '"') then
      Delete(Result, Length(Result), 1);
  end;
end;

procedure InitializeWizard();
begin
  // Create a custom page right after the welcome page
  ExistingInstallPage := CreateInputOptionPage(
    wpWelcome,
    'Existing Installation Detected',
    'An existing installation of EnvForage was detected on this computer.',
    'Please select what you would like to do and click Next:',
    True, // exclusive (radio buttons)
    False // listbox format (looks cleaner and native)
  );

  // Add the radio options
  ExistingInstallPage.Add('&Reinstall / Repair (Overwrites current files, keeps cache/databases)');
  ExistingInstallPage.Add('&Uninstall (Removes the existing version completely)');

  // Default to Reinstall / Repair
  ExistingInstallPage.Values[0] := True;

  // Create the progress page
  ProgressPage := CreateOutputProgressPage(
    'Checking Installation Health',
    'Analyzing the existing EnvForage installation...'
  );
end;

function ShouldSkipPage(PageID: Integer): Boolean;
var
  UninstallString: string;
begin
  Result := False;
  if PageID = ExistingInstallPage.ID then
  begin
    // Skip this page if a previous installation is NOT found
    Result := not GetInstalledUninstallString(UninstallString);
  end;
end;

function CheckExistingInstallationHealth(var ErrorMsg: string): Boolean;
var
  UninstallString: string;
  AppDir: string;
  ExePath: string;
  ResultCode: Integer;
begin
  Result := True; // Healthy by default
  ErrorMsg := '';

  ProgressPage.Show();
  try
    ProgressPage.SetProgress(10, 100);
    ProgressPage.SetText('Reading installation registry metadata...', '');
    Sleep(400); // Visual feedback pause

    if GetInstalledUninstallString(UninstallString) then
    begin
      ProgressPage.SetProgress(40, 100);
      ProgressPage.SetText('Locating main executable...', '');
      Sleep(400);

      AppDir := ExtractFilePath(CleanQuotes(UninstallString));
      ExePath := AppDir + 'envforage.exe';

      if not FileExists(ExePath) then
      begin
        ProgressPage.SetProgress(100, 100);
        ErrorMsg := 'The main executable "envforage.exe" is missing from the installation directory.';
        Result := False;
        Sleep(200);
      end
      else
      begin
        ProgressPage.SetProgress(70, 100);
        ProgressPage.SetText('Verifying binary integrity and runtime execution...', '');
        Sleep(500);

        // Try executing envforage.exe --version silently
        if Exec(ExePath, '--version', AppDir, SW_HIDE, ewWaitUntilTerminated, ResultCode) then
        begin
          ProgressPage.SetProgress(95, 100);
          Sleep(300);
          if ResultCode <> 0 then
          begin
            ErrorMsg := 'The executable crashed or failed to run correctly (Exit Code: ' + IntToStr(ResultCode) + ').';
            Result := False;
          end;
        end
        else
        begin
          ProgressPage.SetProgress(95, 100);
          Sleep(300);
          ErrorMsg := 'Failed to execute "envforage.exe". The binary may be corrupted or blocked.';
          Result := False;
        end;
        ProgressPage.SetProgress(100, 100);
        Sleep(200);
      end;
    end
    else
    begin
      ProgressPage.SetProgress(100, 100);
      ErrorMsg := 'No existing installation metadata found.';
      Result := False;
      Sleep(200);
    end;
  finally
    ProgressPage.Hide();
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  UninstallString: string;
  ErrorCode: Integer;
  ErrorMsg: string;
  MsgResult: Integer;
begin
  Result := True;
  if CurPageID = ExistingInstallPage.ID then
  begin
    if ExistingInstallPage.SelectedValueIndex = 0 then
    begin
      // User selected "Reinstall / Repair"
      if CheckExistingInstallationHealth(ErrorMsg) then
      begin
        // Current installation is healthy! Ask if they still want to proceed
        MsgResult := MsgBox(
          'No errors were detected in your current EnvForage installation (it is healthy and functional).' + #13#10#13#10 +
          'Do you still want to proceed with reinstalling/repairing it?',
          mbConfirmation,
          MB_YESNO or MB_DEFBUTTON2
        );
        if MsgResult = IDYES then
        begin
          Result := True;
        end
        else
        begin
          // Abort the setup since they don't want to proceed with a healthy app
          WizardForm.Close();
          Result := False;
        end;
      end
      else
      begin
        // Current installation has errors! Inform the user and proceed
        MsgBox(
          'The existing installation has errors/warnings:' + #13#10 +
          ErrorMsg + #13#10#13#10 +
          'Setup will now proceed to reinstall and repair the application.',
          mbInformation,
          MB_OK
        );
        Result := True;
      end;
    end
    else if ExistingInstallPage.SelectedValueIndex = 1 then
    begin
      // User selected "Uninstall"
      if GetInstalledUninstallString(UninstallString) then
      begin
        if ShellExec('open', CleanQuotes(UninstallString), '/SILENT', '', SW_SHOWNORMAL, ewWaitUntilTerminated, ErrorCode) then
        begin
          MsgBox('Existing version uninstalled successfully. Click OK to proceed with the new installation.', mbInformation, MB_OK);
        end
        else
        begin
          MsgBox('Failed to run the uninstaller. Setup will now abort.', mbError, MB_OK);
          Result := False;
        end;
      end;
    end;
  end;
end;

const
  WM_SETTINGCHANGE = $001A;

function SendNotifyMessage(hWnd: HWND; Msg: UINT; wParam: LongInt; lParam: String): Boolean;
  external 'SendNotifyMessageW@user32.dll stdcall';

// NVIDIA GPU Detection logic
function DetectNvidiaGpu(): Boolean;
var
  I: Integer;
  KeyName: string;
  Description: string;
begin
  Result := False;
  for I := 0 to 20 do
  begin
    KeyName := 'SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\' + Format('%.4d', [I]);
    if RegQueryStringValue(HKLM, KeyName, 'DriverDesc', Description) or
       RegQueryStringValue(HKLM, KeyName, 'Device Description', Description) then
    begin
      if Pos('NVIDIA', UpperCase(Description)) > 0 then
      begin
        Result := True;
        Exit;
      end;
    end;
  end;
end;

// Check if nvidia-smi is missing
function IsNvidiaSmiMissing(): Boolean;
begin
  Result := not (FileExists(ExpandConstant('{win}\System32\nvidia-smi.exe')) or
                 FileExists('C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe'));
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpSelectDir then
  begin
    if DetectNvidiaGpu() and IsNvidiaSmiMissing() then
    begin
      if GpuWarningLabel = nil then
      begin
        GpuWarningLabel := TNewStaticText.Create(WizardForm);
        GpuWarningLabel.Parent := WizardForm.SelectDirPage;
        GpuWarningLabel.Top := WizardForm.DirEdit.Top + WizardForm.DirEdit.Height + ScaleY(15);
        GpuWarningLabel.Width := WizardForm.SelectDirPage.Width;
        GpuWarningLabel.Height := ScaleY(50);
        GpuWarningLabel.AutoSize := False;
        GpuWarningLabel.WordWrap := True;
        GpuWarningLabel.Font.Color := clRed;
        GpuWarningLabel.Font.Style := [fsBold];
        GpuWarningLabel.Caption := '[WARNING] NVIDIA GPU detected, but no driver/nvidia-smi was found. Please install NVIDIA drivers to enable CUDA hardware profiling.';
      end;
      GpuWarningLabel.Show();
    end
    else
    begin
      if GpuWarningLabel <> nil then
        GpuWarningLabel.Hide();
    end;
  end;
end;

// PATH manipulation functions
procedure AddToPath(PathToAdd: string; IsAdmin: Boolean);
var
  OldPath: string;
  NewPath: string;
  RootHive: Integer;
  SubKey: string;
begin
  if IsAdmin then
  begin
    RootHive := HKLM;
    SubKey := 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment';
  end
  else
  begin
    RootHive := HKCU;
    SubKey := 'Environment';
  end;

  if RegQueryStringValue(RootHive, SubKey, 'Path', OldPath) then
  begin
    if Pos(UpperCase(PathToAdd), UpperCase(OldPath)) = 0 then
    begin
      if OldPath = '' then
        NewPath := PathToAdd
      else
        NewPath := OldPath + ';' + PathToAdd;
      RegWriteExpandStringValue(RootHive, SubKey, 'Path', NewPath);
      SendNotifyMessage(HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment');
    end;
  end
  else
  begin
    RegWriteExpandStringValue(RootHive, SubKey, 'Path', PathToAdd);
    SendNotifyMessage(HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment');
  end;
end;

procedure RemoveFromPath(PathToRemove: string; IsAdmin: Boolean);
var
  OldPath: string;
  NewPath: string;
  RootHive: Integer;
  SubKey: string;
  P: Integer;
begin
  if IsAdmin then
  begin
    RootHive := HKLM;
    SubKey := 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment';
  end
  else
  begin
    RootHive := HKCU;
    SubKey := 'Environment';
  end;

  if RegQueryStringValue(RootHive, SubKey, 'Path', OldPath) then
  begin
    P := Pos(UpperCase(PathToRemove), UpperCase(OldPath));
    if P > 0 then
    begin
      NewPath := OldPath;
      Delete(NewPath, P, Length(PathToRemove));
      StringChange(NewPath, ';;', ';');
      if (Length(NewPath) > 0) and (NewPath[1] = ';') then
        Delete(NewPath, 1, 1);
      if (Length(NewPath) > 0) and (NewPath[Length(NewPath)] = ';') then
        Delete(NewPath, Length(NewPath), 1);
      RegWriteExpandStringValue(RootHive, SubKey, 'Path', NewPath);
      SendNotifyMessage(HWND_BROADCAST, WM_SETTINGCHANGE, 0, 'Environment');
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('envpath') then
    begin
      AddToPath(ExpandConstant('{app}'), IsAdminInstallMode());
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ErrorCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    RemoveFromPath(ExpandConstant('{app}'), True);
    RemoveFromPath(ExpandConstant('{app}'), False);
    ShellExec('open', 'https://envforage.xyz/uninstall', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
  end;
end;
