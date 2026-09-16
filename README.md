# 🎮 Minha Biblioteca de Jogos

Biblioteca pessoal para não depender do Hydra. **Zero dependências** (só Python 3.10+), mesmo banco e mesmas regras em dois frontends nativos (sem navegador, sem rede).

## Casa canônica

Banco, código, backups e capas moram na mesma pasta física NTFS, visível nos dois sistemas:

- Windows: `D:\Tuco-Compartilhado\Jogos\biblioteca\`
- Linux: `/run/media/tuco/Games/Tuco-Compartilhado/Jogos/biblioteca/`

Nunca abra nos dois sistemas ao mesmo tempo; encerre/desmonte antes de trocar de SO.

## Entradas

| Frontend | Onde | Roda como |
|---|---|---|
| `app_win.py` | Windows | aplicativo local (tkinter): `python app_win.py` |
| `app_tui.py` | Linux | aplicativo de terminal (curses): `python app_tui.py` |

Núcleo compartilhado: `bib_core.py` (caminhos, banco, scans, backup, execução).
Versão web antiga removida (histórico em `historico/`).

Opções comuns: `--db outro.db` (padrão: `biblioteca.db` na casa), `--selftest` (só GUI: monta oculta e sai).

## O que faz (nos dois)

- ➕ Cadastrar / editar / excluir: **título + executável** + status (`backlog`, `jogando`, `zerado`, `pausado`, `abandonado`), nota 0–10, favorito, horas, wine prefix, opções, observações, **capa local** (png/jpg/webp até 2 MB).
- 🔎 Buscar + filtrar por status / favoritos; selo **● exe ok / ○ exe?**.
- ▶️ **Executar**: traduz o caminho para o SO atual antes de abrir. Se o jogo exigir administrador (WinError 740), oferece relançar com elevação (UAC).
- ⏱️ **Horas automáticas**: ao jogar, o tempo do processo é somado sozinho (sessões ≥ 30 s). Limite honesto: fechar o launcher antes do jogo perde a sessão; com UAC/startfile as horas seguem manuais.
- 🖥️ **Executável por SO**: `exe_win` / `exe_linux` vencem o caminho único (útil p/ emulador `.exe` no Win e `.AppImage` no Linux).
- 🎮 **Scan de ROMs 3DS** (`.cci/.cxi/.3ds/.3dsx/.elf/.app/.axf`): já liga cada ROM no emulador via opções de lançamento, com preview + confiança.
- 📥 **Importar unificado**: um botão só — pasta (varre jogos de PC + ROMs juntos), arquivo (exe, ROM, JSON ou pacote `.zip`) ou **ler do disco** (Hydra + Steam + Epic + GOG + Riot + programas instalados, cada achado marcado com a fonte). A ROM é ligada no emulador sozinha; sem emulador, importa mesmo assim e o play orienta.

## Emulação 3DS (Azahar)

- Emulador (zip portátil): `D:\Games\Emuladores\Azahar\` (a pasta `user\` dentro dele guarda tudo — portátil na partilha).
- ROMs: `D:\Games\Roms\3DS\`. Mesma versão do Azahar nos dois SOs (save states travam à versão).
- O app **baixa e atualiza o Azahar sozinho** (⬇ na GUI, `A` no TUI: consulta o release, confere sha256 e instala preservando `user\`).
- O scan **lê título, código e região de dentro da ROM** e **cola o ícone da ROM como capa** automaticamente.
- Boot direto em tela cheia (`-f`; desligue com `BIBLIOTECA_AZAHAR_FLAGS=` vazio). Status do Azahar (instalado/user/chaves) na barra da GUI e do TUI.
- **Backup de saves 3DS** (`sdmc/` + `states/`) em botão próprio, separado do backup do banco.
- 🎛️ **Preset por jogo**: cada ROM pode ter um preset (foto da config atual do Azahar em `presets/*.ini`); o launcher mescla no `qt-config.ini` antes de abrir e avisa se falhar (nunca bloqueia o play). Backup pré-preset em `qt-config.ini.bak`.
- No Linux, prefira o AppImage; `sdmc/` (saves) pode ser linkado pra partilha, `config/` fica local.
- Chaves AES + arquivos de sistema: dumpe do seu próprio 3DS (ver wiki do Azahar).
- 🔁 **Tradução determinística**: `D:\…` ↔ `/run/media/tuco/Games/…`. Overrides: `BIBLIOTECA_WIN_ROOT`, `BIBLIOTECA_LINUX_ROOT`, `BIBLIOTECA_HOME`.
- 🔍 **Preview Hydra com confiança** (score 0–1 + motivos; pré-marca ≥ 0.3) — incluído no "ler do disco".
- 💽 **Scan disco com confiança** (`.exe` menos instaladores + manifests Steam; raízes padrão `D:\Games`, `D:\SteamLibrary`, `D:\Riot Games` no Win; override `BIBLIOTECA_SCAN_ROOTS` com `;`; avisa se a lista for parcial pelo teto de varredura). Jogos do Xbox/MS Store não são detectados (loja fechada) — cadastre o exe à mão.
- 💾 **Backup versionado** (`backups/biblioteca-AAAAmmdd-HHMMSS.db` + `.json`, mantém 10).
- 📦 Exportar / importar JSON (GUI e TUI; no TUI o importar aceita `.zip`).
- 📦 **Pacote portátil** (`P` no TUI, 📦/📥 na GUI): um `.zip` com banco + capas (remapeadas p/ os ids novos na volta) + presets + saves 3DS (`sdmc/`). Importação valida todos os nomes antes de aplicar qualquer coisa (anti path-traversal).

Onde o Hydra guarda os dados:

- Windows: `%APPDATA%/hydralauncher/hydra-db` (ou `%APPDATA%/hydra/hydra-db`, antigo)
- Linux: `~/.config/hydralauncher/hydra-db` (ou `~/.config/hydra/hydra-db`, antigo)

## HUB de emulação (provedores)

O núcleo tem um **registro de emuladores** (`provedores()` em `bib_core.py`): cada provider diz que origens atende, onde está o exe, onde ficam config/saves, como montar o launch e como aplicar preset. Lançamento, horas automáticas, pacote e backup de saves falam com o registro — **o Azahar é só o provider nº 1**. O próximo sistema (NDS, GBA…) entra como provider novo sem tocar em lançamento ou frontends.

## Portátil Windows

`python ferramentas/montar_portatil.py` gera `dist/BibliotecaHub-portatil-AAAAmmdd.zip` (~18 MB): Python embutido + tkinter transplantado + scripts Tcl/Tk do fonte oficial + app + launchers. É só extrair e abrir `BibliotecaHub.bat` (a casa vai em `dados/` dentro do pacote).

Modelo **net-install de propósito**: o zip não leva emulador (binário GPL de terceiros + chaves/sysdata, que são dump pessoal e intransferíveis). Na primeira execução, use ⬇ Atualizar Azahar — ele baixa o build oficial e instala sozinho.

## Backup

1. **💾 Backup** na interface (vai para `backups/` na casa canônica), ou
2. **📦 Pacote portátil** (banco + capas + presets + saves — o jeito de levar pra outra máquina), ou
3. **Exportar JSON** (GUI ou TUI), ou
4. Copie `biblioteca.db` com tudo fechado.

## Estrutura

- `bib_core.py` — regras (banco, tradução, scans, backup, execução).
- `app_win.py` / `app_tui.py` — frontends GUI (Windows) / terminal (Linux).
- `biblioteca.db` — criado no primeiro run (SQLite, journal `DELETE`, sem sidecars).
- `backups/` — backups versionados. `capas/` — capas locais. `presets/` — presets do Azahar (`*.ini`).
