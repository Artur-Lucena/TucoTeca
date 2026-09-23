# 🎮 TucoTeca

Biblioteca pessoal para não depender do Hydra. **Zero dependências** (só Python 3.10+), mesmo banco e mesmas regras em dois frontends nativos (sem navegador, sem rede).

## Casa canônica

Banco, código, backups e capas moram na mesma pasta física NTFS, visível nos dois sistemas:

- Windows: `D:\Tuco-Compartilhado\Jogos\biblioteca\`
- Linux: `/run/media/tuco/Games/Tuco-Compartilhado/Jogos/biblioteca/`

Nunca abra nos dois sistemas ao mesmo tempo; encerre/desmonte antes de trocar de SO. O app grava `.biblioteca.lock` na casa e recusa segunda instância (`--ignorar-lock` só após crash; lock com +24h é considerado obsoleto).

## Entradas

No terminal, digite **`tucoteca`** (abre a GUI). Ou duplo-clique em **`TucoTeca.lnk`** (raiz do projeto) — abre só o app, sem janela preta (`BibliotecaHub.bat` faz o mesmo com console, pra debug).

| Frontend | Onde | Roda como |
|---|---|---|
| `codigo/frontends/app_win.py` | Windows | aplicativo local (tkinter): `python codigo/frontends/app_win.py` |
| `codigo/frontends/app_tui.py` | Linux | aplicativo de terminal (curses): `./BibliotecaHub.sh` ou `python3 codigo/frontends/app_tui.py` |

Núcleo compartilhado: `codigo/bib_core.py` (compat; código em `codigo/bib_nucleo/`).
Versão web antiga removida (histórico em `codigo/historico/`).

Opções comuns: `--db outro.db` (padrão: `biblioteca.db` na casa), `--ignorar-lock` (após crash), `--selftest` (só GUI: monta oculta e sai). TUI: `V` provider, `Y` plataforma, `T` etiquetas, `S` sessão manual, preview com `PgUp/PgDn`.

## O que faz (nos dois)

- ➕ Cadastrar / editar / excluir: **título + executável** + horas, etiquetas livres, preset do emulador, observações, **capa local** (png/jpg/webp até 2 MB). O diálogo de edição é sintetizado (status, nota, favorito e caminhos por SO ficam preservados). Filtros cobrem status (`backlog`, `jogando`, `zerado`, `pausado`, `abandonado`), nota 0–10 e favorito gravados.
- 🔎 Buscar + filtrar por status / favoritos / provider (GUI: clique; TUI: `V`) / plataforma / etiquetas; selo **● exe ok / ○ exe?** + **◎confiança** do import.
- 🏷️ **Etiquetas livres**: qualquer jogo aceita tags separadas por vírgula (ex.: `rpg, souls-like`) — aparecem no canto do card (roxo p/ plataforma `PC`/`3DS`/`NDS` derivada da origem + `🏷 tags`) e no detalhe. Filtros: GUI chips `PC`/`3DS`/`NDS` + combo de tags (✕ limpa tudo); TUI `Y` plataforma, `T` tags. Viajam no JSON/pacote e sobrevivem ao restore.
- ▶️ **Executar**: traduz o caminho para o SO atual antes de abrir. Se o jogo exigir administrador (WinError 740), oferece relançar com elevação (UAC). Se o emulador gravado sumiu mas há outro instalado, pergunta (usar+gravar, só desta vez, cancelar); se a ROM sumiu, procura pelo nome nas raízes e oferece religar.
- ⏱️ **Horas automáticas**: ao jogar, o tempo do processo é somado sozinho (sessões ≥ 30 s). UAC/startfile abrem sessão manual em `dados/sessoes/` — reconcilie com ⏱ Registrar sessão (`S` no TUI); ela sobrevive a fechar o launcher.
- 🖥️ **Executável por SO**: `exe_win` / `exe_linux` vencem o caminho único (útil p/ emulador `.exe` no Win e `.AppImage` no Linux).
- 🎮 **Scan de ROMs 3DS** (`.cci/.cxi/.3ds/.3dsx/.elf/.app/.axf`): já liga cada ROM no emulador via opções de lançamento, com preview + confiança.
- 📥 **Importar unificado**: um botão só — pasta (varre jogos de PC + ROMs juntos), arquivo (exe, ROM, JSON ou pacote `.zip`) ou **ler do disco** (Hydra + Steam + Epic + GOG + Riot + programas instalados, cada achado marcado com a fonte). Re-scan não duplica (dedup por exe, ignora barra invertida e renomeios). Jogos Steam ganham a capa oficial sozinhos; a ROM é ligada no emulador sozinha; sem emulador, importa mesmo assim e o play orienta.

## Emulação 3DS (Azahar)

- Emulador (zip portátil): `D:\Games\Emuladores\Azahar\` (a pasta `user\` dentro dele guarda tudo — portátil na partilha).
- ROMs: `D:\Games\Roms\3DS\`. Mesma versão do Azahar nos dois SOs (save states travam à versão).
- O app **baixa e atualiza o Azahar sozinho** (⬇ na GUI, `A` no TUI: consulta o release, confere sha256 e instala preservando `user\`).
- O scan **lê título, código e região de dentro da ROM** e **cola o ícone da ROM como capa** automaticamente.
- Boot direto em tela cheia (`-f`; desligue com `BIBLIOTECA_AZAHAR_FLAGS=` vazio). Status do Azahar (instalado/user/chaves) na barra da GUI e do TUI.
- **Backup de saves 3DS** (`sdmc/` + `states/`) em botão próprio, separado do backup do banco.
- 🎛️ **Preset por jogo**: cada ROM pode ter um preset (foto da config atual em `presets/<emulador>/*.ini`); o launcher mescla no `qt-config.ini` antes de abrir e avisa se falhar (nunca bloqueia o play). Backup pré-preset em `qt-config.ini.bak`.
- No Linux, prefira o AppImage; `sdmc/` (saves) pode ser linkado pra partilha, `config/` fica local.
- Chaves AES + arquivos de sistema: dumpe do seu próprio 3DS (ver wiki do Azahar).
- 🔁 **Tradução determinística**: `D:\…` ↔ `/run/media/tuco/Games/…`. Overrides: `BIBLIOTECA_WIN_ROOT`, `BIBLIOTECA_LINUX_ROOT`, `BIBLIOTECA_HOME`.
- 🔍 **Preview Hydra com confiança** (score 0–1 + motivos; pré-marca ≥ 0.3) — incluído no "ler do disco".
- 💽 **Scan disco com confiança** (`.exe` menos instaladores + manifests Steam; raízes padrão `D:\Games`, `D:\SteamLibrary`, `D:\Riot Games` no Win; override `BIBLIOTECA_SCAN_ROOTS` com `;`; avisa se a lista for parcial pelo teto de varredura). Jogos do Xbox/MS Store não são detectados (loja fechada) — cadastre o exe à mão.
- 💾 **Backup versionado** (`backups/biblioteca-AAAAmmdd-HHMMSS.db` + `.json`, mantém 10).
- 📦 Exportar / importar JSON (GUI e TUI; no TUI o importar aceita `.zip`).
- 📦 **Pacote portátil** (`P` no TUI, 📦/📥 na GUI): um `.zip` com banco + capas (casadas por uuid) + presets + saves 3DS (`sdmc/`). Restaurar preserva horas e última execução; relatório diz novos/atualizados/ignorados/erros. Importação valida todos os nomes antes de aplicar qualquer coisa (anti path-traversal).

Onde o Hydra guarda os dados:

- Windows: `%APPDATA%/hydralauncher/hydra-db` (ou `%APPDATA%/hydra/hydra-db`, antigo)
- Linux: `~/.config/hydralauncher/hydra-db` (ou `~/.config/hydra/hydra-db`, antigo)

## HUB de emulação (provedores)

O núcleo tem um **registro de emuladores** (`provedores()` em `codigo/bib_nucleo/emuladores.py`): cada provider diz que origens atende, onde está o exe, onde ficam config/saves, como montar o launch e como aplicar preset. Lançamento, horas automáticas, pacote e backup de saves falam com o registro — **o Azahar é só o provider nº 1**. O próximo sistema (NDS, GBA…) entra como provider novo sem tocar em lançamento ou frontends. Na GUI, provedores ficam numa seção própria (recurso de fundo, com nº de jogos e ✓ de instalado) — clicar filtra os jogos que ele roda; o emulador não entra na lista de jogos.

## Emulação NDS (DeSmuME)

- Emulador: `D:\Games\Emuladores\DeSmuME\desmume.exe` (release oficial 0.9.13, renomeado p/ nome estável; `desmume.ini` portátil ao lado do exe).
- ROMs: `D:\Games\Roms\NDS\` (`.nds/.dsi`). O scan lê título/código/região do header + banner e cola o ícone como capa, igual ao 3DS.
- O app **baixa e atualiza o DeSmuME sozinho no Windows** (⬇ na GUI, `G` no TUI — mesmo instalador transacional do Azahar). No Linux, use AppImage manual (update automático só Win) ou o DeSmuME do sistema (`desmume` no PATH, flatpak ou snap — detectado sozinho, ou `BIBLIOTECA_EMULADOR_NDS`).

## Primeiro boot no Linux

1. `python3 --version` (precisa 3.10+ com `curses`, que vem junto).
2. `./BibliotecaHub.sh` na raiz (se disser permissão negada: `chmod +x BibliotecaHub.sh`).
3. `chmod +x /run/media/tuco/Games/Games/Emuladores/Azahar/azahar.AppImage` (NTFS não guarda o bit executável).
4. DeSmuME: AppImage na mesma pasta, ou pacote do sistema.
5. O resto (banco, capas, presets, saves, lock) é a mesma partilha do Windows.
- Boot em tela cheia em janela (`--windowed-fullscreen`; `BIBLIOTECA_DESMUME_FLAGS=` desliga). Saves `.dsv` ficam ao lado da ROM (viajam com ela).
- Override: `BIBLIOTECA_EMULADOR_NDS` (exe) ou `BIBLIOTECA_DESMUME_DIR` (pasta, ex.: dentro do portátil).

## Portátil Windows

Extraia `dist/tucoteca-portatil-AAAAmmdd.zip`, duplo-clique em `BibliotecaHub.bat` (ou rode `Criar-Atalho.bat` uma vez e use o atalho da Área de Trabalho) — sem VS Code, sem console, sem Python instalado. A casa vai em `dados/` dentro do pacote.

O Azahar instalado vai junto, 100% das vezes (`emuladores/Azahar/`, com `COPYING.txt` + `FONTE.txt` da GPL e só `user/` essencial: config + saves + mods — nunca nand, chaves, log ou shaders). O DeSmuME vai junto no mesmo esquema (`emuladores/DeSmuME/`). Os `.bat` apontam `BIBLIOTECA_AZAHAR_DIR` pro embutido (override honesto: pasta ausente = ignora e usa o padrão), e o botão ⬇ atualiza o emulador dentro do pacote. Com `--sem-azahar`, o pacote sai magro (net-install: na primeira execução, use ⬇ Atualizar Azahar — ele baixa o build oficial e instala sozinho). O repo git nunca recebe binários (`dist/` ignorado).

## Backup

1. **💾 Backup** na interface (vai para `backups/` na casa canônica), ou
2. **📦 Pacote portátil** (banco + capas + presets `presets/<prov>/` + saves — o jeito de levar pra outra máquina), ou
3. **Exportar JSON** (GUI ou TUI, limpo sem derivados), ou
4. Copie `biblioteca.db` com tudo fechado.

Auto-proteções: backup silencioso antes de todo import (preview/JSON/arquivo), aviso se backup tem +7 dias, lock `.biblioteca.lock` impede abrir nos 2 SOs juntos (`--ignorar-lock` após crash), sessões manuais `dados/sessoes/` reconciliam UAC/startfile via ⏱ Registrar sessão (S no TUI).

## Estrutura

Pastas principais (raiz só tem launchers, este README e git):

- `TucoTeca.lnk` (atalho p/ GUI) / `BibliotecaHub.bat` — **o executável**: duplo-clique abre a GUI (produção/dev).
- `codigo/` — tudo que é programa: `bib_core.py` (compat), `bib_nucleo/` (`base`, `banco`, `scans`, `emuladores`, `pacotes`, `atualizacao`), `frontends/` (GUI Windows / terminal Linux), `ferramentas/` (portátil, testes), `historico/` (arquivo).
- `dados/` — tudo que é seu: `biblioteca.db`, `backups/`, `capas/`, `presets/`, `sessoes/`, `erros.log` (nunca vai pro git).
- `midia/fontes-capas/` — imagens-fonte das capas (já aplicadas; reserva).
- `dist/` — portáteis gerados (ignorado no git).
