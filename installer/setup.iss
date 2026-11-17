; S&W 지출결의서 작성이 — 설치 프로그램 (Inno Setup 6)
; tools/build.py 가 /DAppVersion=... /DSourceDir=... /DOutputDir=... 를 넘겨 컴파일한다.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\지출결의서"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif

#define AppName "S&W 지출결의서 작성이"
#define AppExe "지출결의서.exe"

[Setup]
; AppId 는 바꾸지 말 것 (업데이트 시 같은 프로그램으로 인식하는 기준)
AppId={{6E3A4F7C-2B9D-4C1E-9A57-5D0F3B8C21A4}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=S&W 경영지원부
; 관리자 권한 없이 사용자별 설치 (회사 PC 에서도 바로 설치·자동 업데이트 가능)
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\SnW 지출결의서
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
SetupIconFile=..\app\assets\icon.ico
OutputDir={#OutputDir}
; GitHub 첨부파일 이름은 한글이 지워지므로 영문으로
OutputBaseFilename=SnW_Jichul_Setup_{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
; 데이터(작성이력)는 내 문서\S&W 지출결의서 에 있으므로 제거해도 남는다

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "바로가기:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; 업데이트 시 예전 버전의 남은 라이브러리 정리
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{#AppName} 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; 일반 설치: 마지막 화면에서 '실행' 체크 / 자동 업데이트(/SILENT): 설치 후 바로 다시 실행
Filename: "{app}\{#AppExe}"; Description: "{#AppName} 실행"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: WizardSilent
