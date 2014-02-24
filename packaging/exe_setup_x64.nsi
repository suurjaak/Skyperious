; Script for NullSoft Scriptable Install System, producing a 64-bit setup.
;
; @created   13.01.2013
; @modified  12.02.2014

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "Skyperious"
!ifndef PRODUCT_VERSION
  ; PRODUCT_VERSION should come from command-line parameter
  !define PRODUCT_VERSION "1.0"
!endif
!define PRODUCT_PUBLISHER "Erki Suurjaak"
!define PRODUCT_WEB_SITE "http://suurjaak.github.com/Skyperious"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\skyperious.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; MUI 1.67 compatible ------
!include "MUI.nsh"
!include x64.nsh
!include FileAssociation.nsh

!define MUI_TEXT_WELCOME_INFO_TEXT "This wizard will guide you through the installation of $(^NameDA).$\r$\n$\r$\n$_CLICK"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "installer.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!define MUI_PAGE_CUSTOMFUNCTION_PRE FinishPage_Pre
!define MUI_PAGE_CUSTOMFUNCTION_SHOW FinishPage_Show
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE FinishPage_Leave
!define MUI_FINISHPAGE_RUN "$INSTDIR\skyperious.exe"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.txt"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "English"

; MUI end ------

RequestExecutionLevel admin

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "skyperious_${PRODUCT_VERSION}_x64_setup.exe"
InstallDir "$PROGRAMFILES64\Skyperious"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

Section "MainSection" SEC01
  ; Fixes potential problems with uninstalling shortcuts in Windows 7
  SetShellVarContext all
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  File "skyperious.exe"
  CreateDirectory "$SMPROGRAMS\Skyperious"
  CreateShortCut "$SMPROGRAMS\Skyperious\Skyperious.lnk" "$INSTDIR\skyperious.exe"
  SetOverwrite off
  File "skyperious.ini"
  SetOverwrite ifnewer
  File /oname=README.txt "README for Windows.txt"
  CreateShortCut "$SMPROGRAMS\Skyperious\README.lnk" "$INSTDIR\README.txt"
  File "3rd-party licenses.txt"
SectionEnd

Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\Skyperious\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  CreateShortCut "$SMPROGRAMS\Skyperious\Uninstall Skyperious.lnk" "$INSTDIR\uninst.exe"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\skyperious.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\skyperious.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd


Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to uninstall $(^Name)?" IDYES +2
  Abort
FunctionEnd

Section Uninstall
  ; Fixes potential problems with uninstalling shortcuts in Windows 7
  SetShellVarContext all
  Delete "$INSTDIR\${PRODUCT_NAME}.url"
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\README.txt"
  Delete "$INSTDIR\3rd-party licenses.txt"
  Delete "$INSTDIR\skyperious.ini"
  Delete "$INSTDIR\skyperious.exe"

  Delete "$SMPROGRAMS\Skyperious\Skyperious.lnk"
  Delete "$SMPROGRAMS\Skyperious\README.lnk"
  Delete "$SMPROGRAMS\Skyperious\Website.lnk"
  Delete "$SMPROGRAMS\Skyperious\Uninstall Skyperious.lnk"

  RMDir "$SMPROGRAMS\Skyperious"
  RMDir "$INSTDIR"

  ${UnregisterExtension} ".db" "SQLite3 database file"

  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  SetAutoClose true
SectionEnd

Function FinishPage_Show
ReadINIStr $0 "$PLUGINSDIR\iospecial.ini" "Field 6" "HWND"
SetCtlColors $0 0x000000 0xFFFFFF
FunctionEnd

Function FinishPage_Pre
WriteINIStr "$PLUGINSDIR\iospecial.ini" "Settings" "NumFields" "6"
WriteINIStr "$PLUGINSDIR\iospecial.ini" "Field 6" "Type" "CheckBox"
WriteINIStr "$PLUGINSDIR\iospecial.ini" "Field 6" "Text" "&Associate Skyperious with *.db files"
WriteINIStr "$PLUGINSDIR\iospecial.ini" "Field 6" "Left" "120"
WriteINIStr "$PLUGINSDIR\iospecial.ini" "Field 6" "Right" "315"
WriteINIStr "$PLUGINSDIR\iospecial.ini" "Field 6" "Top" "130"
WriteINIStr "$PLUGINSDIR\iospecial.ini" "Field 6" "Bottom" "140"
WriteINIStr "$PLUGINSDIR\iospecial.ini" "Field 6" "State" "0"
FunctionEnd

Function FinishPage_Leave
ReadINIStr $0 "$PLUGINSDIR\iospecial.ini" "Field 6" "State"
StrCmp $0 "0" end
${RegisterExtension} "$INSTDIR\skyperious.exe" ".db" "SQLite3 database file"
end:
FunctionEnd
