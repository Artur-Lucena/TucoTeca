# Git do projeto — acompanhamento (11/10/2026, lote 1.5.10–1.5.13)

Projeto: `D:\Tuco-Compartilhado\Jogos\biblioteca\`
O acesso ativo está em `../projeto/` (junction NTFS para o checkout) e em
`../Git-Projeto.bat` (status/diff/log ao vivo a cada 3s).
Este arquivo guarda o estado observado no encerramento da etapa.

```
log --oneline -n 5 --decorate:
1a8b089 (HEAD -> main) gitattributes: qml/qmldir em LF (politica codigo)
5565750 Desktop Qt Quick + QoL 1.0 + freeze tkinter (272/272)
52951c3 (origin/main, origin/HEAD) Revisao geral: nome canonico Steam + capa padrao, sidebar, sanear, downloads qBittorrent, runtime (259/259)
98dccd1 Catalogo SteamRip: buscar, hosts, baixar p/ Piratas, importar (185/185)
12de8f6 Player async: trocar de faixa sem congelar + runner utf-8 (185/185)

status --short --branch:
## main...origin/main [ahead 2]
 M README.md
 M codigo/bib_nucleo/baixar.py
 M codigo/bib_nucleo/banco.py
 M codigo/bib_nucleo/musicas.py
 M codigo/bib_nucleo/qbit.py
 M codigo/bib_nucleo/repacks.py
 M codigo/bib_nucleo/scans.py
 M codigo/ferramentas/testes/test_qt.py
 M codigo/ferramentas/testes/test_repacks.py
 M codigo/ferramentas/testes/test_runtime.py
 M codigo/frontends/app_qt.py
 M codigo/frontends/app_tui.py
 M codigo/frontends/app_win.py
 M codigo/frontends/qml/ActionButton.qml
 M codigo/frontends/qml/Main.qml
 M codigo/frontends/qml/PosterCard.qml
 M codigo/frontends/qml/Theme.qml
 M codigo/frontends/qt_bridge.py
 M codigo/frontends/servicos_ui.py
 M docs/DESKTOP_QT.md
?? codigo/bib_nucleo/capas.py
?? codigo/bib_nucleo/conquistas.py
?? codigo/bib_nucleo/online.py
?? codigo/bib_nucleo/spotify.py
?? codigo/ferramentas/testes/test_conquistas.py
?? codigo/ferramentas/testes/test_online.py
?? codigo/ferramentas/testes/test_spotify.py
?? codigo/frontends/qml/AchievementsDialog.qml
?? codigo/frontends/qml/CoversDialog.qml
?? codigo/frontends/qml/MusicDownloadsDialog.qml
?? codigo/frontends/qml/NewIntegrationDialog.qml
?? codigo/frontends/qml/ProvidersDialog.qml
?? codigo/frontends/qml/SpotifyDialog.qml
?? codigo/frontends/qml/VolumeControl.qml
?? docs/QOL_1_5.md
```

Novos arquivos ainda untracked (não entram no `diff --stat`).
Verificações: 295 PASS + 6 SKIP, 0 FAIL (301 casos); auditoria 6 seções
sem QML crítico; selftest 26 jogos; banco original intacto por SHA-256.

Snapshot do início da sessão (branch/remote/log 20) arquivado abaixo.
HEAD preservado em `1a8b089`; alterações da etapa permanecem locais.

--- snapshot início QoL 1.5 ---

Projeto: `D:\Tuco-Compartilhado\Jogos\biblioteca\`
`.git` mora lá. Este arquivo é só espelho legível na pasta da sessão.
Atualizar no fim de cada tópico com os dois comandos do `QoL-1.5.md`.

```
remote:
origin  https://github.com/Artur-Lucena/Projeto-Launcher.git (fetch/push)

branch -vv:
* main 1a8b089 [origin/main: ahead 2] gitattributes: qml/qmldir em LF

log --oneline -n 20 --decorate:
1a8b089 (HEAD -> main) gitattributes: qml/qmldir em LF (politica codigo)
5565750 Desktop Qt Quick + QoL 1.0 + freeze tkinter (272/272)
52951c3 (origin/main, origin/HEAD) Revisao geral: nome canonico Steam + capa padrao, sidebar, sanear, downloads qBittorrent, runtime (259/259)
98dccd1 Catalogo SteamRip: buscar, hosts, baixar p/ Piratas, importar (185/185)
12de8f6 Player async: trocar de faixa sem congelar + runner utf-8 (185/185)
ec91622 Hub baixa ffmpeg e yt-dlp sozinho + oferta no TOCAR (180/180)
9603f7f Print Tuco: botoes detalhe por modo + msg ffmpeg de play (177/177)
5e1db25 Revisao musicas: capas automaticas iTunes v15 + modal vira aba (177/177)
c0a18f8 Player interno MCI-wave+ffmpeg (transporte, auto-avancar, externo fallback) (172/172)
89ec94d Fase C: mp3 via ffmpeg BYOB + Importar baixadas GUI/TUI (165/165)
876cfcf Fase B: download yt-dlp BYOB p/ staging + Baixar fila GUI/TUI (163/163)
cc1d28c Fase A UI: fila CSV na aba Musicas GUI+TUI (160/160)
73cc2b8 Fase A core: CSV Exportify vira fila downloads v14 (158/158)
bdbd3f9 Aba Musicas no Hub + helpers Harmoni (155/155)
640d713 Punch list item 23 (revisão Win/Linux): js-Linux, .hub-lixo no SKIP, redist total, eol + endurecimentos do outro chat (153/153)
6080531 Capa Steam automatica no import + minimizar/restaurar ao jogar (150/150)
a37e2c8 Repacks automaticos: extrai p/ Piratas, organiza, acha exe, importa (147/147) + --jogar p/ atalhos
7634f0c Remove Switch/Citron total (menos controles): provider, scans, coluna citron_preset, testes, dist
a2c9f7b Linux: subsistemas novos com paridade (cheats/texturas/controles/mac), dedup cross-OS de ROMs, testes 149/149
b2805c0 Controles no Hub: formato calibrado no boot, higiene anti-flip, UI GUI/TUI, XInput corrigido (145/145)

status:
On branch main
Your branch is ahead of 'origin/main' by 2 commits.
nothing to commit, working tree clean
```
