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
- 🖥️ **Executável por SO**: `exe_win` / `exe_linux` vencem o caminho único (útil p/ emulador `.exe` no Win e `.AppImage` no Linux).
- 🎮 **Scan de ROMs 3DS** (`.cci/.cxi/.3ds/.3dsx/.elf/.app/.axf`): já liga cada ROM no emulador via opções de lançamento, com preview + confiança.

## Emulação 3DS (Azahar)

- Emulador (zip portátil): `D:\Games\Emuladores\Azahar\` (a pasta `user\` dentro dele guarda tudo — portátil na partilha).
- ROMs: `D:\Games\Roms\3DS\`. Mesma versão do Azahar nos dois SOs (save states travam à versão).
- O app **baixa e atualiza o Azahar sozinho** (⬇ na GUI, `A` no TUI: consulta o release, confere sha256 e instala preservando `user\`).
- O scan **lê título, código e região de dentro da ROM** e **cola o ícone da ROM como capa** automaticamente.
- Boot direto em tela cheia (`-f`; desligue com `BIBLIOTECA_AZAHAR_FLAGS=` vazio). Status do Azahar (instalado/user/chaves) na barra da GUI e do TUI.
- **Backup de saves 3DS** (`sdmc/` + `states/`) em botão próprio, separado do backup do banco.
- No Linux, prefira o AppImage; `sdmc/` (saves) pode ser linkado pra partilha, `config/` fica local.
- Chaves AES + arquivos de sistema: dumpe do seu próprio 3DS (ver wiki do Azahar).
- 🔁 **Tradução determinística**: `D:\…` ↔ `/run/media/tuco/Games/…`. Overrides: `BIBLIOTECA_WIN_ROOT`, `BIBLIOTECA_LINUX_ROOT`, `BIBLIOTECA_HOME`.
- 🔍 **Preview Hydra com confiança** (score 0–1 + motivos; pré-marca ≥ 0.3).
- 💽 **Scan disco com confiança** (`.exe` menos instaladores + manifests Steam; raízes padrão `D:\Games`, `D:\SteamLibrary`, `D:\Riot Games` no Win; override `BIBLIOTECA_SCAN_ROOTS` com `;`; GUI/TUI aceitam pasta custom; avisa se a lista for parcial pelo teto de varredura).
- 💾 **Backup versionado** (`backups/biblioteca-AAAAmmdd-HHMMSS.db` + `.json`, mantém 10).
- 📦 Exportar / importar JSON (GUI e TUI).

Onde o Hydra guarda os dados:

- Windows: `%APPDATA%/hydralauncher/hydra-db` (ou `%APPDATA%/hydra/hydra-db`, antigo)
- Linux: `~/.config/hydralauncher/hydra-db` (ou `~/.config/hydra/hydra-db`, antigo)

## Backup

1. **💾 Backup** na interface (vai para `backups/` na casa canônica), ou
2. **Exportar JSON** (GUI ou TUI), ou
3. Copie `biblioteca.db` com tudo fechado.

## Estrutura

- `bib_core.py` — regras (banco, tradução, scans, backup, execução).
- `app_win.py` / `app_tui.py` — frontends GUI (Windows) / terminal (Linux).
- `biblioteca.db` — criado no primeiro run (SQLite, journal `DELETE`, sem sidecars).
- `backups/` — backups versionados. `capas/` — capas locais.
