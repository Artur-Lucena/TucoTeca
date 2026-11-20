; Pasta fixa do TucoTeca no Windows: %LOCALAPPDATA%\Programs\TucoTeca.
;
; O instalador de um clique por usuário só reaproveita a pasta anterior se ela
; estiver no registro (HKCU\Software\<APP_GUID>\InstallLocation); sem isso ele
; usa o nome do pacote (tucoteca-electron) e a atualização vira uma segunda
; cópia, com os atalhos numa pasta e o desinstalador na outra. Quem já tem uma
; pasta registrada continua nela.
!macro preInit
  !ifndef BUILD_UNINSTALLER
    ReadRegStr $0 HKCU "Software\${APP_GUID}" InstallLocation
    StrCmp $0 "" 0 +2
      WriteRegExpandStr HKCU "Software\${APP_GUID}" InstallLocation "$LOCALAPPDATA\Programs\TucoTeca"
  !endif
!macroend
