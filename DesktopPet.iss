; DesktopPet 安装程序脚本
; 需要 Inno Setup 6+ (https://jrsoftware.org/isdl.php)
;
; 使用方式：
;   1. 先用 BUILD.bat 构建 PyInstaller 输出到 dist\DesktopPet\
;   2. 用 Inno Setup 打开此文件 → 编译
;   或直接运行 BUILD_INSTALLER.bat 一键完成

#define MyAppName "DesktopPet"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "goldentrain"
#define MyAppURL "https://github.com/golden-train/DesktopPet"
#define MyAppExeName "DesktopPet.exe"
#define MyAppIcon "data\assets\images\firefly\icon\icon.ico"

[Setup]
; 基本设置
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=.\dist
OutputBaseFilename=DesktopPet_Setup_{#MyAppVersion}
Compression=lzma2/ultra
LZMAUseSeparateProcess=yes
LZMADictionarySize=65536
SolidCompression=yes
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=admin
AllowNoIcons=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile={#MyAppIcon}
CloseApplications=no
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: checkedonce

[Files]
; 主程序 — 递归包含整个 PyInstaller 输出目录
Source: "dist\DesktopPet\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 环境变量示例文件
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
; 安装完成后可选启动
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: postinstall nowait skipifsilent unchecked

[UninstallRun]
; 卸载时清理用户数据目录（询问确认）
Filename: "{cmd}"; Parameters: "/c rmdir /s /q ""{localappdata}\DesktopPet\data"""; Flags: runhidden

[Code]
{ 卸载时弹出确认对话框 }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if MsgBox('是否同时删除所有用户数据（配置、日志、导入的角色模型等）？'#13#13'保留数据可用于下次安装。', mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec('rmdir', '/s /q "' + ExpandConstant('{localappdata}') + '\DesktopPet\data"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    end;
  end;
end;
