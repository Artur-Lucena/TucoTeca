# TucoTeca — Memória de continuidade (para o OpenCode no Linux)

> Lido ao entrar no Linux. Escrito pelo agente do Windows em 23/09/2026,
> atualizado após revisão geral + 8 melhorias + commit `7e09996`.
> Sessão Linux 24/09: paridade TUI + saves (`d0847e7`), visual + menus
> (`f5b9f5c`), revisão anti-regressão Win (71/71). Detalhes no item 3b.
> Siga os fluxos abaixo do mesmo jeito.
> Sessão Win 24/09 (pós-Linux): Fase 0 do porte Mac pronta e congelada
> (ver item 11). Nada do Win/Linux mudou em comportamento (80/80 + selftest 22).

## 1. O que é o projeto

**TucoTeca** (antes "Minha Biblioteca de Jogos" / "Biblioteca Hub"): biblioteca
pessoal de jogos, **zero dependências** (só Python 3.10+ stdlib), sem navegador
e sem rede. Mesmo banco e mesmas regras em dois frontends nativos:
- **Windows:** GUI tkinter → `codigo/frontends/app_win.py` (comando `tucoteca`)
- **Linux:** TUI curses → comando `tucoteca` (`~/.local/bin/tucoteca` →
  `./BibliotecaHub.sh` → `codigo/frontends/app_tui.py`). Só menus:
  `↑↓/jk` move, `Enter` abre o menu (do jogo ou principal), `ESC` volta,
  digitação só dentro dos prompts. Sem teclas de letras.

Núcleo compartilhado em `codigo/bib_nucleo/` (`base`, `banco`, `scans`,
`emuladores`, `pacotes`, `atualizacao`); `codigo/bib_core.py` é só shim de
compat (`import bib_core as core`). Versão web antiga removida.

## 2. Tradução de caminhos Win ↔ Linux (determinística, ver `base.py`)

| Windows | Linux |
|---|---|
| `D:\` (WIN_ROOT) | `/run/media/tuco/Games` (LINUX_ROOT) |
| `D:\Tuco-Compartilhado\Jogos\biblioteca\` | `.../Tuco-Compartilhado/Jogos/biblioteca/` (casa, `BIBLIOTECA_HOME`) |
| `D:\Games\Piratas` | `/run/media/tuco/Games/Games/Piratas` |
| `D:\Games\Emuladores\Azahar\` | `.../Games/Emuladores/Azahar/` (+ `azahar.AppImage` 2126.1.1) |
| `D:\Games\Roms 3Ds`, `D:\Games\Roms NDs` | mesmos nomes com espaço, mesma tradução |
| `D:\Games\trocar-nome-jogador.py` etc. | `.../Games/trocar-nome-jogador.py` |

Overrides: `BIBLIOTECA_WIN_ROOT`, `BIBLIOTECA_LINUX_ROOT`, `BIBLIOTECA_HOME`,
`BIBLIOTECA_AZAHAR_DIR`, `BIBLIOTECA_EMULADOR_NDS`, `BIBLIOTECA_SCAN_ROOTS`.
**Nunca abra o Hub nos dois SOs ao mesmo tempo** (lock `.biblioteca.lock`;
se obsoleto e o processo morreu, apague o arquivo).

## 3. Estado em 23/09/2026, fim do dia (confirme com os comandos do item 6)

- Hub: **22 jogos**, 100% com capa (padrão 600×800 PNG; ícones NDS 96px intactos),
  0 exes ausentes, 0 duplicatas. Backups em `dados/backups/` (mantém 10).
- Git **limpo e commitado** (`7e09996`): rebrand TucoTeca, etiquetas, dedup,
  capas 600×800, lock, presets v3, TUI com filtros, suite fase D. `.vbs`
  apagado (morto sob SAC); `.build/` de 619 MB podado; `dist/` atual.
- Antivírus Windows: Smart App Control **Off** + exclusões `D:\Games` e repo
  (EICAR sobrevive em `D:\Games` = prova).
- Interpretador Windows: Python 3.14.7 oficial + Pillow; comando `tucoteca`;
  atalho `TucoTeca.lnk`. **Nunca use o Python do uv** (`~/.local/share/uv`,
  binários `NotSigned`, quebra sob SAC).
- Suíte: **74/74 verde** (`test_linux.py` tem 14; fase D 13 com `save_path`).
- Pendências: **Temtem Swarm** estava em 8% e a pasta sumiu do disco (fila do
  Hydra pausada — retomar baixa do zero); **Shroom and Gloom** e
  **How Many Dudes** instalados, com nome `Tuco` e capa. How Many Dudes é
  **Free To Play na Steam** (repack desnecessário; manter ou migrar, a gosto).
- `dist/` tem `tucoteca-portatil-20260923.zip` + `-slim.zip` (atuais).
- Vigília de fontes (`monitor-fontes.py`, domingos 10h): lista vazia,
  mecanismo intacto. Hydra já tem as 7 fontes (DODI, Xatab, onlinefix,
  SteamRip, TinyRepacks, GOG, FitGirl) — nada a adicionar lá.

## 3b. Estado em 24/09/2026, sessão Linux (vale sobre o item 3)

- Git: `d0847e7` (paridade Linux: testes, Wine, DeSmuME, lock, capas) +
  `f5b9f5c` (visual TUI + painel lateral). **Não commitado**: `base.py`
  (fallback `resolver_exe` + lock antigo), `emuladores.py`, `test_linux.py`,
  `app_tui.py` (menus Enter/ESC) — commitar no próximo boot com disco.
- Suíte: **71/71** (`59 + 6 test_linux.py + 4 menus + 2 blindagens Win`).
  `tucoteca --selftest` → 22 jogos. Diagnóstico: 22/22 com exe.
- Banco (com backup `biblioteca-20260923-175115.db` antes): `exe_linux`
  preenchido nos 15 ROMs (AppImage / `/usr/games/desmume-cli`); 4 launches
  `C:\Users\Tuco\Desktop\Roms 3Ds\...` religados aos `.cci` em
  `D:\Games\Roms 3Ds`. `executable_path` do Windows intacto.
- Saves: 3DS compartilha `user/sdmc` (6 títulos com `main`); NDS via
  symlinks `~/.config/desmume/*.dsv` → `DeSmuME/Battery/` (achado com
  `strace`: `desmume-cli` só lê `~/.config/desmume/`); nomes `Tuco` nos
  6 inis intactos.
- Sistema: `python3-tk` 8.6, `wine` 10.0, `desmume` 0.9.13 (binário é
  `desmume-cli`), Pillow 12.1.1 presente, `tucoteca` no PATH, cron dom 10h
  (`monitor-fontes.py` → `~/.cache/tucoteca-monitor.log`).
- Wine: DXVK 2.6 oficial instalado na mão em `~/.wine` (o `dxvk-setup` do
  Debian não faz nada; DLLs antigas eram cópias das internas). Overrides
  `d3d11/dxgi/d3d10core/d3d9/d3d8=native`; lançador força NVIDIA
  (`emuladores.py`, PRIME + filtro DXVK). `d3d12` voltou a builtin (sem vkd3d).
- Saves nativos do HUB (`dados/saves/`, 24/09): prefixo Wine único migrado
  de `~/.wine` (1.2 GB, com DXVK + progresso) para `dados/saves/wine`
  (`~/.wine.antes-hub` guardado até confirmação); `_lancar` usa o prefixo
  do HUB quando o jogo não tem `wine_prefix`. Comandos `wine`/`reg` exigem
  `WINEPREFIX=dados/saves/wine`.
- Pendente do item 3: Temtem Swarm, `dist/`, How Many Dudes (inalterados).

## 4. Como eu trabalho (mantenha o padrão)

- Respostas curtas, em português, sem bajulação; código citado como
  `arquivo:linha`. Pergunte antes de decidir entre opções (sem "Outro").
- **Toda mudança em DB/disco começa com backup** (`core.fazer_backup`).
- **Verifique executando**: `py_compile` + `--selftest` + casos-alvo da suíte
  após qualquer mudança. Não crie arquivos sem necessidade (prefira editar).
- Testes: cada `teste_*` roda em subprocesso sandbox; `test_dialogo_*`
  precisa de display (pulam sem Tk; sem `tkinter` pulam por
  `ModuleNotFoundError`). Menus do TUI têm regressão com `getch` enlatado
  (`test_linux.py`); nunca dispare `Jogar` em teste (abre o jogo de verdade).
  Nunca deixe modal travando teste
  (verificações de startup são não-modais na barra de status).
- Imports: stdlib alfabético → local; `__all__` só com nomes públicos;
  sem Pillow obrigatório (tudo `try/except`, TUI não usa capa).
- CRLF/LF: `.gitattributes` fixa `*.sh` e `*.py` em LF; `*.bat/*.vbs` em CRLF.

## 5. Procedimento padrão (Piratas → Hub)

1. Listar `Games/Piratas`: archives (`.rar/.zip`) → extrair com
   `Games/ferramentas/7z.exe`, verificar o `.exe`, apagar o archive.
2. Apagar sobras: `Read_Me*`, `*.url`, `_redist_readme*`, `_CommonRedist`
   duplicado da raiz, instaladores `setup_*` redundantes.
   **Manter**: `_CommonRedist` de cada jogo, OSTs, `.bak`s, saves.
3. `trocar-nome-jogador.py <Usuario> --aplicar` (motor `sincronizar_nomes()`
   é o que o boot do Hub chama; saves só na troca manual de usuário).
4. No Hub: `core.fazer_backup(db)` → `preview_pasta([Piratas])` →
   `importar_lista` (dedup automático por exe: barra, caixa e renomeios;
   `cgef`/`F10`/`stockfish` já filtrados; títulos de exe colados são
   separados sozinhos) → capa Steam automática p/ jogos `shop=steam`
   com appid; capa manual via API (`header_image`) se faltar.
5. `python3 codigo/frontends/app_win.py --selftest` (ou TUI equivalente).

## 6. Comandos de verificação (Linux)

```
udisksctl mount -b /dev/nvme0n1p3   # se /run/media/tuco/Games sumir
python3 --version                                   # 3.10+
tucoteca --selftest                                 # TUI fake: 22 jogos
tucoteca                                            # abre o TUI (lock único)
python3 codigo/ferramentas/testes/executar.py       # suíte 74/74
python3 -c "import sys; sys.path.insert(0,'codigo'); import bib_core"
```

## 6b. Saves centralizados em `dados/saves/` (Win, 24/09)

Tudo que o Hub lança e tem save em disco mora no Hub; o lugar original
virou **junction NTFS** (transparente p/ jogos e AV; sem admin p/ criar):
`azahar-sdmc`, `desmume-battery`, `how-many-dudes`, `mewgenics`,
`megabonk` (+`.reg` do PlayerPrefs), `chants-of-sennaar` (+`.reg`),
`shroom-and-gloom`, `ultrakill-saves`, `ultrakill-prefs`, `hades-ii`
(junction futura, pasta vazia). Mapa legível em `dados/saves/saves-map.json`;
Wine já era `saves/wine`. Coluna `save_path` (migração v7) aparece no
detalhe (GUI) e no formulário (TUI).
**Não mexer nas junctions pelo Windows como pasta comum** (apagar o link
não apaga os dados, mas recriar exige o rito copiar→hash→junction).
No Linux, junctions aparecem como symlinks (Azahar/DeSmuME seguem);
os links `~/.config/desmume/*.dsv → Battery/` continuam válidos
(`Battery/` segue no mesmo lugar, agora como junction).

## 7. Especificidades do Linux (não quebre)

- Disco `Games` é `nvme0n1p3` NTFS; se desmontar, `udisksctl mount -b
  /dev/nvme0n1p3` (ou clique no drive no Arquivos). Sem ele nada abre.
- `./BibliotecaHub.sh` e `app_tui.py` têm `100755` no git — confira após clone.
- `azahar.AppImage` precisa de `chmod +x` (NTFS não guarda o bit).
- DeSmuME: apt instala como **`desmume-cli`** em `/usr/games` (código já
  detecta); saves em `~/.config/desmume/` linkados ao `Battery/` (refazer
  links se o `Battery/` mudar de lugar); update automático é só Win.
- Wine: DXVK real em `~/.wine` + overrides `native` + PRIME/NVIDIA no
  `_lancar` (`emuladores.py`); `.exe` sem wine dá erro claro. `d3d12` fica
  builtin (sem vkd3d).
- `sincronizar_nomes_boot` e chip 👤 são só da GUI; o TUI não usa.
- Vigília de fontes: cron dom 10h → `~/.cache/tucoteca-monitor.log`
  (equivale à tarefa `MonitorFontesHydra` do Windows).
- `trocar-nome-jogador.py` traduz `D:\...` sozinho no Linux (ver `_casa()`);
  `carregar_estado` traduz antes de podar (sem isso apagava registro válido).
- Pillow 12.1.1 instalado — capas convertem normal.
- TUI é dirigido por menus (`Enter`/`ESC`); `teclas de letras` removidas do
  `rodar`. Painel lateral só em terminal ≥100 col.
- Saves PC vivem em `dados/saves/wine` (prefixo do HUB); nunca em `~/.wine`.
- Transferir save do Windows p/ o HUB: copiar no Windows para
  `D:\Games\Jogadores\Tuco\saves-pc\<Jogo>\`, bootar no Linux e pedir ao
  agente para plantar em `dados/saves/wine/drive_c/users/tuco/...`
  (com backup do atual). Ver item 9.

## 8. Incidente SAC 23/09 (contexto, não ação)

No meio da sessão o Smart App Control endureceu sozinho (modo avaliação →
enforcement): bloqueou `.vbs` (800711C7), DLLs do Python-uv (`NotSigned`) e
até o instalador oficial no modo per-user. Resolução: SAC **Off** pelo Tuco
+ Python 3.14.7 oficial per-user + exclusões. Se algo "não abre" de novo no
Windows, cheque `SmartAppControlState` antes de culpar o código.

## 9. Checklist ao bootar no Windows (pós-sessão Linux 24/09)

Windows não mudou funcionalmente (`app_win.py` só LF; `.bat` só `+%*`;
ramo `nt` intacto), mas confirme:

```
python codigo/ferramentas/testes/executar.py   # espera 71/71 (GUI roda com display)
python codigo/frontends/app_win.py --selftest  # espera [ok] selftest
```

- `exe_linux` novo no banco é ignorado no Windows; `executable_path`
  continua valendo. `launch_options` dos 4 ROMs `C:\...` agora apontam
  para `D:\Games\Roms 3Ds` (arquivos existem nos dois SOs).
- Lock antigo (sem `host`/`so`) ainda libera normal (compat mantida).
- Se algum `FAIL` aparecer só lá, traga o log que corrijo no Linux.

## 10. Resgate de saves do Windows (How Many Dudes, Mewgenics — FEITO 24/09)

Saves de perfil ficam em `C:` (inacessível no Linux). Rito, no PowerShell
do Windows (uma vez por jogo) — **executado em 24/09, staging pronto**:

```
# How Many Dudes (GameMaker): 6 arqs, 43 KB — FEITO
LOCALAPPDATA\HowManyDudes\* -> saves-pc\HowManyDudes\
# Mewgenics (Glaiel Games, %APPDATA%): 9 arqs, 442 KB — FEITO
APPDATA\Glaiel Games\Mewgenics\76561197960271872\* -> saves-pc\Mewgenics\
(inclui saves\steamcampaign01.sav + test00.sav + backups 16-20/09)
```

No Linux, o agente planta em
`dados/saves/wine/drive_c/users/tuco/AppData/...` (How Many Dudes:
`.../Local/HowManyDudes/<steam-id>/`; Mewgenics: conforme o achado),
com backup do atual, e confere o continue no jogo.
Staging: `Games/Jogadores/Tuco/saves-pc/<Jogo>/` (criado 24/09).

## 11. Porte Mac — Fase 0 pronta e CONGELADA (Win, 24/09; sem acesso ao Mac ainda)

Decisões travadas (sem "Outro", valem p/ Fase 2): Mac universal
Intel+ARM (`sys.platform == "darwin"`, via `eh_mac()` em `base.py`);
disco no caminho seguro `/Volumes/Games` (`MAC_ROOT`, override
`BIBLIOTECA_MAC_ROOT`); escopo v1 só ROMs 3DS/NDS (sem Wine no Mac,
`.exe` = só catálogo); frontend GUI tkinter (`app_win.py` é
multiplataforma; `BibliotecaHubMac.command` novo na raiz, LF, duplo-clique
abre a GUI com `BIBLIOTECA_HOME` na pasta do projeto).

Fase 0 aplicada (darwin-safe, Win/Linux com comportamento idêntico):
- `codigo/bib_nucleo/base.py`: `MAC_ROOT`, `eh_mac()`, `win_para_mac`,
  `mac_para_win`, `linux_para_mac`, `mac_para_linux`, helper `_sob`
  (fora do `__all__`); `traduzir_para_atual` virou 3 vias (no Linux,
  prefixo Mac resolve p/ `LINUX_ROOT`); `resolver_exe` com `exe_mac`
  (vence no Mac; nos outros SOs só fallback se existir em disco).
- `codigo/bib_nucleo/banco.py`: migração **v8 `exe_mac`** (auto-migra com
  backup `pre-migracao-*`; `CAMPOS_EDITAVEIS`, CRUD, unique-triplo e
  `importar_lista` em `scans.py` levam `exe_mac`; export JSON/pacote já
  viajam por `SELECT *`).
- `codigo/bib_nucleo/emuladores.py`: importa `eh_mac`; erros do `_lancar`
  SO-aware ("...não executa no Mac..." + dica `exe_mac`; ramo Linux
  byte a byte igual) e modo `popen-mac` no Mac.
- `codigo/ferramentas/testes/test_mac.py` (novo, 6 testes, descoberta
  automática): ida-e-volta Win↔Mac e Linux↔Mac, `traduzir_para_atual`
  cobrindo Mac, `exe_mac` como fallback + prioridade do campo do SO,
  migração v8 em banco legado + CRUD, `importar_lista` com `exe_mac`,
  mensagem Mac no `_lancar` (pula no Windows).
- `.gitattributes`: `*.command text eol=lf`.

Verificado no Windows (nada quebrado): backup `biblioteca-20260924-031237`
(22 jogos) antes de tudo; suíte **80/80** (74 + 6 novos, sandbox);
`app_win.py --selftest` 22 jogos; tradução `D:\` ↔ `/Volumes/Games`
conferida; `dados/` arrumado (backups: 9 pares ≤ 10 + 3 `pre-migracao-*` +
  1 zip emu + 1 dir; junctions `dados/saves/` todas válidas; `capas/` 22
  arqs; `erros.log` limpo). Guards Mac ok: `ctypes`/`winreg`/`startfile`
  só sob `os.name == "nt"` (`app_win.py:107`, `scans.py:570`,
  `emuladores.py:409`); Pillow/curses em `try/except`.
- NÃO commitado (commite junto com o resto quando for): `base.py`,
  `banco.py`, `emuladores.py`, `scans.py`, `.gitattributes`,
  `BibliotecaHubMac.command`, `test_mac.py`. Intactos e pré-existentes os
  diffs `save_path` (`test_fase_d.py`, `app_tui.py`, `app_win.py`).
- Anomalia sem impacto (só observar se repetir): `backups/`
  tem `pre-migracao-20260924-070244-001697.db` (22 jogos, com etiquetas,
  sem `save_path`, Shroom 0.04h@00:22) — snapshot coerente porém mais
  antigo que o banco atual (Shroom 0.52h@02:30); `biblioteca.db` intacto
  (22 jogos, schema v8, LastWrite 03:12) e suíte/selftest verdes.
  Hipótese: `get_db` sob relógio dessincronizado do dual-boot. 32 KB,
  inofensivo.

Notas p/ a Fase 1/2 (quando houver Mac — NÃO fazer antes):
- Lock `.biblioteca.lock`: no Mac `os.name` é `posix` (campo `so` =
  `"posix"`, igual ao Linux) — o lock impede Mac+Linux juntos do mesmo
  jeito que Win+Linux. Nunca abra em 2 SOs juntos do mesmo jeito.
- NTFS no Mac é só-leitura sem driver: se o disco `Games` estiver NTFS,
  a casa canônica NÃO pode morar lá (use casa local no Mac +
  pacote portátil `.zip` p/ levar os 22 jogos; `exe_mac` + ROMs via
  `BIBLIOTECA_MAC_ROOT`). Se for APFS/exFAT, tradução direta vale.
- Fase 1 (coleta no Mac, trazer a saída):
  ```
  sw_vers; uname -m; python3 --version; python3 -c "import tkinter; print('tk ok')"
  ls /Volumes/; ls /Volumes/Games/Tuco-Compartilhado/Jogos/biblioteca/ 2>&1
  ls /Applications/ | grep -i -E "azahar|desmume"; ls ~/Applications 2>/dev/null | grep -i -E "azahar|desmume"
  ```
  + formato do disco + builds (Azahar macOS `.app`/dmg oficial; DeSmuME
  Mac `.app` ou brew) + `chmod +x BibliotecaHubMac.command` na 1ª vez
  (quarentena: `xattr -d com.apple.quarantine` se o Gatekeeper implicar).
- Fase 2 (código, com os dados acima): `default_emu_3ds/nds` achando
  `.app` (Intel+ARM) + `azahar_user_dir` Mac (`~/Library/Application
  Support/...` — confirmar path real); `_lancar` darwin abrindo `.app`
  (sem Wine); `default_scan/roots` Mac + Steam
  `~/Library/Application Support/Steam`; campo `exe_mac` no diálogo da
  GUI; `BIBLIOTECA_AZAHAR_DIR`/`BIBLIOTECA_EMULADOR_NDS` como overrides.

## 12. 3DS: perf Pokémon + GPU (Win, 24/09)

6 ROMs Pokémon (`rom-3ds`, todas com exe/ROM ok e descriptografadas;
`aes_keys.txt` ausente mas irrelevante). Causa do engasgo (X/Y
testados, vale pros 6): `resolution_factor=2` + `async_shader_compilation
=false` no `qt-config.ini` do Azahar portátil. Corrigido em 24/09 (backup
do banco `biblioteca-20260924-042648` + `qt-config.ini.bak` antes):
resolução 1x + shaders assíncronos no config global, preset
`performance` fotografado em `dados/presets/azahar/` e atribuído aos 6
(`azahar_preset`). GPU checada e OK: híbrido RTX 3050 6GB Laptop +
Intel UHD, e o log do Azahar de 23/09 prova `GL_RENDERER: NVIDIA
GeForce RTX 3050` (OpenGL; `graphics_api=1` = OpenGL neste build) —
nada a forçar no Windows. Se ainda engasgar após teste: atualizar
driver NVIDIA ou experimentar Vulkan; suíte 80/80 + selftest 22
continuam verdes.

## 13. Mods 3DS no Hub (Win, 24/09 — suíte 88/88, selftest 22)

Achado no disco: 6 mods LayeredFS já aplicados em
`Emuladores/Azahar/user/load/mods/<title-id>/` (flat, sempre-ativos;
`code.ips` + `romfs/`), e os 6 packs-fonte em `Roms 3Ds/Patches/`
(Repolished 1.7.6, Rebirth 2.2.3, Penumbra/Supernova Lite v1.0.5, com
variantes como `level nerf patch` e layout `luma/titles/<id>/`).
Title IDs lidos do header NCCH das ROMs (não adivinhe: AS=…11C500,
OR=…11C400, UM=…1B5100, US=…1B5000, X=…55D00, Y=…55E00).

Modelo (decisões do Tuco): biblioteca em `dados/mods/azahar/<tid>/<mod>/`
(extraído+normalizado); ativação por **junction NTFS** em
`load/mods/<tid>/` só dos ativos (sem cópia, sem admin); pacote
portátil NÃO inclui mods. Campo `azahar_mods` (JSON, migração **v9**;
`normalizar_mods`/`mods_de` em `banco.py`, `mods_lista` derivado).
`preparar_lancamento` aplica preset + mods (chave nova
`mods_aplicados`; frontends só leem `aviso`, contrato intacto).
GUI: linha 🎨 no detalhe + linha Mods (botão …) no diálogo com janela
(check alternar, Adicionar de arquivo/pasta, Remover, OK/Cancelar).
TUI: `menu_jogo` ganhou `Mods` → `menu_mods` (toggle imediato,
adicionar/remover). Migração dos 6 atuais feita com backup
(`biblioteca-20260924-044104`): árvores movidas p/ biblioteca com os
nomes dos packs e `azahar_mods` gravado por jogo (estado efetivo
idêntico, agora via junction — verificado legível pelo Azahar).

Lições de junction via `DeviceIoControl` (sem admin, sem subprocesso,
testável sob o audit da suíte — `criar_link`/`remover_link`/`_eh_reparse`
em `emuladores.py`, com `_k32()` de assinaturas explícitas):
- SEMPRE `ctypes.WinDLL("kernel32", use_last_error=True)` +
  `ctypes.get_last_error()` — `ctypes.windll` NÃO preserva o erro
  (o "4392" inicial era fantasma e custou horas).
- SEMPRE declare `argtypes`/`restype` (ponteiro truncado = erro esquisito).
- Buffer MOUNT_POINT exato do `mklink` (validado byte a byte via
  `FSCTL_GET_REPARSE_POINT=0x900A8`): strings COM NUL no buffer mas
  `sl`/`pl`/`dl` SEM contar os NULs; `po = sl + 2`; `dl = sl + pl + 12`.
- Cuidado com escapes de `\` e `\0` ao editar via ferramenta/powershell
  (use `chr(0)` e `"?" * 2` — barra-zero literal de 2 chars quebra tudo
  em silêncio).
- `aplicar_mods` remove SÓ reparse points (pastas reais nunca tocadas);
  links órfãos de tentativas falhas são dirs vazios comuns (apagar à mão).
- NÃO commitado (com o resto): `base.py` (MODS_DIR), `banco.py` (v9),
  `emuladores.py` (seção mods), `scans.py` (azahar_mods no import),
  `pacotes.py` (poda `mods_lista`), `app_win.py`, `app_tui.py`,
  `test_mods.py` (9 testes). `python` no shell cai no uv (proibido) —
  usar `py -3.14` (oficial).
- Alinhamento Linux (revisado sem bootar lá): `criar_link`
  vira symlink no posix e `aplicar_mods` reconstrói os links a cada play,
  então junctions do Windows viram symlinks no 1º play Linux e vice-versa
  (ntfs-3g mapeia os dois; biblioteca `dados/mods/` é a mesma partilha).
  Se um nome de mod ativo estiver ocupado por PASTA REAL (junction do
  outro SO ilegível, ou resto de árvore flat): vazia o Hub remove
  sozinho, com conteúdo avisa e nunca apaga. Migração v9 é automática
  via `get_db` nos dois SOs. Import `.7z` no Linux exige p7zip do
  sistema (mensagem orienta); `.zip`/pasta vão só de stdlib. TUI `Mods`
   e `title_id_da_rom` são puros (só leitura) — funcionam lá sem mudança.

## 14. Revisão geral + poda (Win, 24/09 — suíte 90/90, selftest 22)

Erros achados e corrigidos: `importar_mod` enterrava `code.ips` dentro
de `romfs/` quando o pack tinha conteúdo nu + `.ips` juntos (com
regressão); dups em `__all__` do `emuladores.py` (`presets_prov_dir`,
`config_atual_emu`); import local redundante em `pacotes.py`
(`presets_prov_dir` já vinha no topo). Verificados e íntegros:
contagem colunas×placeholders dos INSERTs (`banco` 24/24, `scans`
25/25), `.bat` pega `pythonw` oficial (uv sem `pythonw`, sem risco),
`dist/` com os 2 zips de 23/09 (ignorado, anterior aos mods — restore
dele em código novo funciona: campos ausentes viram padrão), guards
`nt`-only, contrato `preparar_lancamento` (só `aviso` lido).
Mantido de propósito: `codigo/historico/`, `midia/fontes-capas/`,
`dist/`, `.cache/` (ignorados ou reserva), `monitor-fontes.py` e
`trocar-nome-jogador.py` (fora do repo, ativos via cron/procedimento).
Nada morto no código (flags do checker eram métodos/closures).
Scripts temporários de debug apagados de `Temp/opencode`.

## 15. Chave liga/desliga de mods por jogo (Win, 24/09 — 91/91)

Campo `azahar_mods_off` (0/1, migração **v10**, default ligado;
`mods_off` derivado): desligado, o play remove os junctions e roda a
ROM limpa, com a lista preservada p/ religar. GUI: botão
Desligar/Ligar na linha Mods + `🎨 OFF · …` no detalhe (+ estado no
título da janela); TUI: 1ª opção do menu Mods alterna a chave.
`importar_lista`/pacote carregam o flag; `_jogo_limpo` poda só o
derivado. Testado ponta a ponta no X (off some o link, on recria).
Backup `biblioteca-20260924-053110` antes da v10.

## 16. WinError 193 no Jogar 3DS (Win, 24/09 — 92/92)

Sintoma (print do Tuco): `Jogar` no Alpha Sapphire com mods OFF →
`OSError: [WinError 193] %1 não é um aplicativo Win32 válido`. Causa:
`resolver_exe` no Windows preferia o fallback `exe_linux`
(`.../azahar.AppImage`, que EXISTE no disco) ao legado válido
(`azahar.exe`). Corrigido em `base.py`: no `nt`, legado existente
vence; fallback de outro SO só vale com sufixo executável Win
(`_WIN_EXEC`: exe/bat/cmd/lnk/com). Com regressão
(`teste_resolver_legado_vence_appimage_no_windows`) e ajuste no teste
antigo (usava `.bin` como fallback válido — era o bug). Sem escrita
no banco (só código). 6 ROMs diagnosticadas `ok → azahar.exe`;
pode jogar.

## 17. Mods não carregavam — layout aninhado ignorado (Win, 24/09 — 93/93)

Sintoma: com junctions `<tid>/<mod>/` íntegros, o Azahar ignorava os
mods. Causa: a doc oficial (citra.azahar-emu.org/help/feature/
game-modding) manda `romfs`/`code.ips` DIRETO em `load/mods/<title-id>/`
— o nível `<mod>/` nunca é lido. Correção: `aplicar_mods` agora COPIA
com overlay (ordem da lista, último vence) p/ flat `<tid>/`, com
manifesto `.hub-mods.json` (pula cópia se igual; limpa só o que o Hub
pôs; arquivos do usuário e pastas reais nunca tocados; OFF/desligado
limpa tudo). Tamanhos 45–106 MB: cópia local de ~1–2 s só quando muda.
Builders de junction (`criar_link`, `_junction_nt`) podados — viraram
código morto (ficam `_eh_reparse`/`remover_link` p/ limpar as junctions
legadas, já convertidas nos 6 jogos). Testes reescritos p/ cópia
(overlay, preservação, idempotência). Confirmado no jogo pelo Tuco em
24/09 — mods carregando.

## 18. Instaladores clássicos 100% offline (Win+Linux, 24/09 — 108/108)

`montar_portatil.py` refatorado: `montar_base` (BUILD + provas reais) +
`podar_dieta` (__pycache__/*.pyc) + `empacotar_zip` (portátil clássico,
como antes) + `empacotar_tarxz` (LZMA2 stdlib — base dos instaladores;
tar.xz abre nativo em Linux/Win-7Zip/Mac) + `compilar_setup` (chama o
ISCC; override `ISCC_EXE`; `.iss` recebe BUILD/Versão via /D).
`instalador.iss` (Inno 6): wizard moderno, `PrivilegesRequired=lowest`
(%LOCALAPPDATA%, sem admin), atalhos Menu Iniciar (+Desktop opcional),
`dados\` FORA do setup e preservado na desinstalação. Compilação
provada com ISCC portátil 6.7.3 (Inno NÃO está instalado — montar o
`.exe` real exige instalar; `ISCC_EXE` aponta p/ ele).
`montar_linux.py` (novo): monta a árvore `tucoteca/` (app + Azahar
AppImage + user essencial + `.sh`/`.desktop`/`desinstalar.sh`) e gruda
stub POSIX + payload → `dist/tucoteca-setup-<data>.run` (235 MB c/
Azahar 2126.1.1; offset do stub validado byte a byte; `tail -c +N |
tar -xJf`). DeSmuME/Citron Linux ausentes aqui → ficam p/ pacote do
sistema/AppImage próprio (stub avisa; ⬇ do app resolve depois).
Citron entrou no bundle Win (opcional: ausente = aviso, não falha).
`test_instalador.py`: dieta, roundtrip tarxz, offset+payload do .run,
conteúdo do .iss. Commits 9dd458c + 86c64e2 já no GitHub; artefatos em
`dist/` (ignorado no git, mesma máquina). PENDENTE (outro chat): rodar
o `.run` num Linux real. (Setup.exe cheio feito no item 19.)

## DONO DO MAC (vínculo permanente)

O **porte p/ macOS é deste chat** (sessão Mac). Todo o código com `eh_mac`,
`MAC_ROOT`, `exe_mac`, `BibliotecaHubMac.command`, `montar_mac.py` e
`test_mac.py` nasce e é revisado aqui; o `.md` é atualizado a cada passo
p/ leitura retroativa dos outros.

**Contrato p/ os outros chats (Win/Linux):** ao mexer em `base.py`
(tradução de caminhos, `resolver_exe`), `banco.py` (migrações/CAMPOS),
`emuladores.py` (providers, presets, mods) e frontends, pensem no Mac:
toda origem nova precisa de `exe_mac` + tradução `win/mac/linux` + teste
em `test_mac.py` (ou aviso explícito aqui no `.md` de que o Mac ficou
p/ trás). Quebrou a suíte no Mac = avisar este chat pelo `.md`.

## 20. Sessão Mac: núcleo .app + updater darwin + pacote offline (28/09 — 114/114)

**Revisão do código Mac achou buraco real:** só o Citron resolvia `.app`;
Azahar/DeSmuME caíam em caminho Linux (AppImage inútil no Mac) e o ⬇
negava o Mac. Corrigido em `emuladores.py`: `_app_macos()` genérico
(prefere binário homônimo, senão o maior) usado por
`default_emu_3ds`, `default_emu_nds`, `default_emu_switch` (+ `_emu_dir`,
`desmume_dir` apontando p/ `MAC_ROOT`); `azahar_user_dir` no Mac = `user/`
ao lado do bundle (até 3 níveis acima do binário); matchers de asset
extraídos p/ `_asset_azahar_ok` (universal zip) e `_asset_desmume_ok`
(dmg) — testáveis sem rede; `azahar/desmume/citron_instalar` com
`plataforma="darwin"`. REGRA: `eh_mac()` sempre antes de `os.name`
(ele lê `sys.platform` ao vivo; os testes simulam darwin no Windows).
Em `atualizacao.py`: ramo darwin (`_extrair_app_mac`: .zip stdlib c/
trava `__MACOSX`+user, .dmg via hdiutil) + transacional aceita symlinks
INTERNOS no darwin (`.app` exige; externos seguem vetados; Win/Linux
intactos). Testes: `.app` fake, override+default do 3DS, matchers
(atenção: sandbox fixa `BIBLIOTECA_AZAHAR_DIR`, e `MAC_ROOT` é importado
por valor no EMU — ver testes). Commit 88a907c.

**Downloads oficiais em `codigo/ferramentas/.cache/mac/` (415 MB, fora do
git, via `garantir_mac()` em `montar_mac.py`):** python-3.14.7-macos11.pkg
(74 MB, novo) + python-3.10.11-macos11.pkg (39 MB, antigo/mínimo 3.10) +
azahar-macos-universal-2126.1.2.zip (109 MB, novo, sha256 conferido) +
azahar-macos-universal-2126.1.1.zip (109 MB, antigo/fallback, fica no
cache) + Citron-macOS-nightly-0237a9b88.dmg (70 MB) + desmume-0.9.13-macOS.dmg
(14 MB). Zip do Azahar validado: `Azahar.app/Contents/MacOS/azahar`.
`dist/mac/` profissional (308 MB): payload + 5 oficiais +
`Instalar-Mac.command` (checa/abre pkg do Python, extrai app, deszipa
Azahar, monta dmgs via hdiutil, limpa quarantine, grava versao-*.txt) +
`LEIA-ME-MAC.txt`. `INSTALAR.html` atualizado. README idem.

**PENDENTE (só testável num Mac real):** rodar `Instalar-Mac.command`,
abrir o Hub, jogar 3DS/NDS/Switch, testar o ⬇. Nada mais a fazer aqui
sem o Mac. (Nota: vi o commit 105ae9f do outro chat — MUSICAS_DIR — Mac
não afetado, suíte verde.)

## 19. Pacote universal 3 SOs + Setup.exe cheio real (24/09 — 110/110)

Build Win cheio rodado aqui: Azahar 2126.1.1 (544 MB) + DeSmuME 0.9.13
(40 MB) + **Citron 2026-04-27 (98 MB, estava instalado e entrou)** +
provas reais ok → `dist/TucoTeca-Setup-20260924.exe` (**210,8 MB**,
LZMA2/ultra — ~30% menor que os 298 MB do .zip deflate).
`montar_mac.py` (novo): payload `tucoteca-mac-<data>.tar.xz` (68 KB, só
código — Fase 0 honesta) + `Instalar-Mac.command` (extrai p/
~/Applications/TucoTeca; dmg de verdade só num Mac).
`montar_universal.py` (novo): `dist/tucoteca-universal-<data>/` com
`windows/` + `linux/` + `mac/` + `INSTALAR.html` (detecta o SO via
navigator.platform e mostra o passo a passo) + `LEIA-ME.txt`; artefatos
Win/Linux reaproveitados de dist/ (avisa se faltar), Mac gerado na hora.
Testes: payload Mac + montagem universal (sandbox exigiu `trab` param no
`montar_base_mac` + mock do `montar_mac` — suíte veta escrita fora do
tmp). Pendente (outro chat): instalar o .exe/`.run`/Mac em máquina real.

## 18. Provider Citron/Switch + Pokémon Brilliant Diamond (Win, 24/09)

Integração máxima no padrão Azahar/DeSmuME (BYOB, stdlib só, GPL-safe):
`ROM_EXTS_SWITCH` (`.nsp/.xci/.nca/.nro/.nso`), provider `citron`
(`rom-switch`), migração **v11 `citron_preset`**, scan/preview/pacote,
GUI+TUI (filtro Switch, `Atualizar Citron`, `Saves Switch`), suíte
`test_citron.py` (11 testes, 104/104). Citron `2026-04-27` msvc instalado
em `Games/Emuladores/Citron/` (SHA ok; `citron.exe` Qt + `citron-cmd.exe`
padrão do Hub + `citron-room.exe`).
Brilliant Diamond: `Roms Switch/Pokemon Brilliant Diamond.nsp` (4,3 GB,
v0 eShop, tid `0100000011D90000`, FW base 11.0) importado como id 45
(23 jogos, capa 600×800, diag exe/rom ok, selftest 23/23).
**Falta (exige o Switch do Tuco)**: `prod.keys` em
`Emuladores/Citron/user/keys/` + firmware em `user/nand/` (play avisa
sem eles) e 1º play real. Backups `biblioteca-20260924-063216` (22 j.),
`-063437` (23 j.). Não commitado: `test_citron.py`.
**24/09 depois**: Tuco sem Switch → sem dump possível; entrada 45
removida do banco + capa apagada (backup `-063818`, 22 j., selftest
22/23→22 ok). `.nsp` (4,3 GB) mantido em `Roms Switch/`; Citron
instalado fica (serve p/ futuro).

## 19. FireRed/LeafGreen Switch eShop dumps (Win, 24/09)

Achado em `Roms Switch/`: rar NXBrew (386 MB) com os relançamentos
oficiais eShop 2026 (GBA+wrapper, dumps por idioma, 27/02/2026).
Extraído com `Games/ferramentas/7z.exe` (12/12 `PFS0` ok) e rar apagado.
Importados só os 2 em inglês, renomeados limpo: ids 46/47 (24 jogos,
backup `-065044`). Capas 600×800 recortadas da key art oficial
(pokemon.com: Charizard→FireRed, Venusaur→LeafGreen). Demais idiomas no
disco, importáveis sob pedido. Selftest 24/24 ok.
**Mesmo bloqueio do Shield**: sem Switch não há `prod.keys`/firmware —
play avisa, single-player local quando houver chaves.

## 20. Divisão de frentes + refino Win/Linux + base MP3 (Win, 28/09 — 110/110)

**Donos (vale p/ os dois chats, leitura retroativa):**
- **Este chat = W11/Linux.** Dono do núcleo Win/Linux, suíte e instaladores
  Win/Linux. Não mexe no porte Mac além de manter `darwin-safe`.
- **Outro chat = Mac.** Dono do porte Mac (Fase 1/2, `.app`, dmg,
  `~/Applications/TucoTeca`). É ele quem atualiza este MD pelo lado Mac.
- **Regra de integração:** toda mudança Win/Linux tem que manter os ramos
  `eh_mac()` + `exe_mac`/v8 + `resolver_exe` + `_WIN_EXEC` intactos e rodar
  `test_mac.py` (7 testes) junto. Nada de `posix == Linux`; nada de exigir
  `MZ/ELF` de binário p/ áudio. `montar_mac.py` Fase 0 não é tocado aqui.

**Refino aplicado (commit `105ae9f`, push ok, suíte 110/110 + selftest 24):**
- `base.py`: 6 `win/linux/mac_para_*` viraram 1 helper `_trocar_prefixo`
  (comportamento idêntico, conferido ida-e-volta nos 6 sentidos).
- `scans.py:pontuar`: removia 1 stat duplicado por item (`traduzido == exe`
  decide o 0.5, sem `Path(exe).exists()` extra).
- `scans.py:SKIP_DIRS`: + `saves`, `mods`, `musicas` (scanner nunca importa
  prefixo Wine, LayeredFS ou trilha como jogo).
- Melhoria `jogos_do_provedor` (1 build em vez de N) revertida aqui:
  `emuladores.py` estava com edição concorrente do chat Mac no mesmo
  arquivo — deixei o arquivo dele intacto, reaplico depois do commit dele.

**Base MP3 (só FS, sem schema — pronto p/ integrar, sem quebrar nada):**
- `base.py`: `MUSICAS_DIR = dados/musicas/` (+ `garantir_dirs`, `__all__`) e
  `MUSICA_EXTS = {.mp3,.ogg,.m4a,.flac,.wav}`. `dados/` segue ignorado;
  nada no git, nada no scanner, nada nos pacotes ainda.
- Desenho futuro (não implementado): `bib_nucleo/musicas.py` com
  `musica_release_info()` (molde `_capa_steam`) + `musica_instalar()`
  (molde `atualizacao.instalar`, sem `extractall`, sem checagem `MZ/ELF`);
  migração **v12** (`musica_path/musica_sha`, espelho `save_path`);
  `PACOTE_ESQUEMA 3→4` + categoria `musicas/`; `test_musica.py` com
  `urlopen` mockado (padrão `capa_steam_falha_rede`), só tmp da suíte.
  Download sempre sob ação ⬇, nunca no `recarregar/desenhar`; falha de
  rede vira aviso, nunca trava play/list.

**Árvore no push:** `base.py` + `scans.py` commitados (`105ae9f`); `emuladores.py` +
`atualizacao.py` eram do chat Mac e foram commitados por ele em 28/09
(`88a907c` + `9e14c22`: `.app` Azahar/DeSmuME/Citron, updater darwin,
pacote offline Mac, `Instalar-Mac.command`). Pós-merge: suíte **114/114**
+ selftest 24/24 verdes no HEAD combinado.

## 21. Músicas selfhost + revisão Win/Linux (29/09 — 130/130, commit `12fb8e5`)

Outro chat implementou (eu revisei, corrigi e commitei): `bib_nucleo/musicas.py`
(novo) — importa áudio da pasta `music/` do Harmoni p/ `dados/musicas/`,
lê tags ID3v2 com parser próprio stdlib, dedup por sha, `tracks.json`
opcional p/ álbum; play no player do SO por ação explícita (`startfile` /
`open` / `xdg-open`, darwin-safe). `banco.py`: tabela `musicas` (v12) + CRUD;
`pacotes.py`: `PACOTE_ESQUEMA 3→4` com categoria `musicas/`; GUI seção
Músicas (import em thread, janela tocar/excluir) + TUI `menu_musicas`
(por isso `test_linux.py` 7→8 teclas); `test_musica.py` (5 testes) +
1 teste Mac de fallback. Commits anteriores já no GitHub: texturas HD
como mods (`b068bb6`, 122/122), cheats Gateway como mods (`d5622a5`, 124/124).

**Correções da revisão (minhas, mesmo commit):**
- `tocar_musica`: fallback de path de outra máquina p/ `MUSICAS_DIR/<nome>`
  (espírito `procurar_rom`) — o teste do outro chat patcha `base.MUSICAS_DIR`,
  então a leitura tem que ser **ao vivo** (`from ... import` dentro da
  função, como `importar_musicas`); minha 1ª tentativa com global do módulo
  quebrou o teste — revertida. Sem isso a suíte ficava 129/130.
- `musicas.py:_tracks_index`: `tracks.json` com JSON não-objeto (ex. `42`)
  derrubava com `AttributeError` — guardado + regressão
  (`teste_musica_tracks_json_invalido`).
- `app_tui.py:menu_musicas`: `rotulos.index(escolha)` trocado por `pos = idx`
  (rótulo duplicado `artista — título` abria a faixa errada).
- `app_win.py:_aviso_barra`: aviso anterior é removido antes de anexar o
  novo (cada Jogar empilhava `· …` na barra sem limite).
- Achado sem ação: outro chat editou `test_mac.py`/`musicas.py` no meio da
  minha revisão (árvore compartilhada) — por isso o FAIL pareceu
  "fantasma" (passava isolado, falhava na suíte): o teste e a implementação
  mudaram entre duas execuções. Daqui em diante: avisar antes de rodar a
  suíte final p/ congelar a árvore, ou cada chat commita antes de chamar
  revisão.

## 22. Regra de congelamento + revisão cheats/texturas (29/09 — 130/130)

**REGRA (vale p/ todos os chats, sem exceção):** árvore compartilhada, um
commit por frente antes de pedir ou fazer revisão. Procedimento:
1. `git status --short --branch` limpo + `main` em dia com `origin/main`;
2. só então `executar.py` + `--selftest`;
3. commit pequeno + push a cada etapa.
Revisão em árvore suja com outro chat editando junto causa FAIL fantasma
(ver item 21) e commit com autoria misturada. Se a árvore estiver suja de
outro chat, NÃO commite por ele: revise só leitura e peça o commit dele.

**Revisão aplicada nesta sessão (commit `d13771a`, árvore congelada em
`12fb8e5`, suíte 130/130 + selftest 24/24 antes e depois):**
- `texturas.py` tinha `titulo_ok` próprio idêntico ao de `cheats.py`, e o
  `bib_core` (`import *` dos dois) exportava o de texturas por ordem de
  import — divergência silenciosa futura. Agora `texturas` reusa
  `cheats.titulo_ok` (mesmo objeto, `__all__` intacto p/ compat).
- `cheats.py:_ler_blocos` compilava o regex de `[bloco]` a cada linha —
  pré-compilado (`_BLOCO_RE`).
- Verificados e deixados como estão (decisão consciente): `cheats_path` /
  `load_textures_dir` criam a pasta como efeito colateral do getter (dito
  no teste); TUI conta PNGs do submenu de forma síncrona (TUI é síncrono
  por desenho — igual a `atualizar_emu`); `instalar_textura` via
  `shutil.move` (cross-partition cai p/ cópia, stdlib resolve);
  `TEXTURAS_DIR` + SKIP `texturas` + poda dos 3 instaladores já existiam
  (cobrados por `test_texturas.py`); `emuladores.py:1541` avisa no
  play se falta o flag global com pasta ativa.

## 23. Auditoria funda Win/Linux — punch list RESOLVIDO (commit `640d713`)

Auditado sobre HEAD `6080531` + diff sujo (outro chat, parado há 5h).
Suíte na árvore suja: **152/152** + selftest 24/24; após fixes: **153/153**.
Remoção Citron: completa (restos só legítimos: migração v13 DROP,
comentário SCHEMA, schema legado em `test_musica.py:110` p/ cobrir o DROP,
"Switch Pro" = controle). Resolvido de uma vez (checks = feito):

- [x] **P0 — `_listar_linux` cego (`controles.py`):** extraído
  `_parse_devices()` puro + `_eh_js()` (`js0`/`js1`/… casam, `jsfoo` não),
  flush final e entre entradas, `_familia_por_nome` ignora hífen
  (`X-Box 360 pad` → `xbox360`, achado extra no caminho) + regressão
  `teste_parse_devices_js_realista` (última entrada sem linha em branco
  cobre o flush). Detecção Linux volta a funcionar.
- [x] **P1 — `.hub-lixo` passeia no scan:** entrada no `SKIP_DIRS`
  (`scans.py`) + poda em `_iter_reais` (`repacks.py`, cobre achar/
  quarentenar/limpar de uma vez).
- [x] **P1 — `_CommonRedist` parcial (`repacks.py`):** `break` removido —
  remove todos os rasos, não só o primeiro.
- [x] **P2 — `.gitattributes`:** + `.gitignore` e `LICENSE` em LF
  (silencia o warning CRLF).
- [x] **P2 — `capturar` sem caller:** fora do `__all__` de controles
  (segue importável/testável via módulo; `core.capturar` não tinha caller).

Commit `640d713` levou junto o trabalho parado do outro chat (idle 5h+,
suite-green): endurecimento banco (merge de triplos/uuid, backup
best-effort, erros limpos), quarentena `.hub-lixo`, testes de ataque
traversal/symlink, README reescrito sem Switch, `LICENSE` MIT,
`.gitignore` endurecido. Verificado OK e mantido: `detectar_sdl["perfil"]`
é contrato testado; bits XInput/SDL corretos; `winreg`/`ctypes` com
guards; `--jogar` com lock + `finally`; archive consumido mesmo com
`novos==0` (decisão em teste).

## 23. Revisão Mac do lote Win (cheats+texturas+música, 28/09 — 130/130, SEM COMMIT)

Outro chat entregou: `cheats.py`+`texturas.py` (commits b068bb6/d5622a5) e
`musicas.py`+`test_musica.py`+banco v12+pacote v4 (sujos na árvore).
Revisão Mac: **tudo darwin-safe** — cheats/texturas usam `azahar_user_dir()`
(que resolve `.app`+`user/` no Mac), música toca via `open` no darwin, sem
`MZ/ELF` em áudio, `SKIP_DIRS` e builders OS-agnósticos (poda de textures
só Win/Linux porque o Mac não embarca `user/` — nada a espelhar).
Seed de cheats em `user/cheats` viaja no volume compartilhado p/ o Mac.

**Aprimoro meu (2 arquivos, NÃO commitado — aguardando ordem):**
- `musicas.py:tocar_musica` ganhou fallback `MUSICAS_DIR/<nome>` quando o
  path absoluto da máquina que importou não existe (banco compartilhado
  toca no Mac/Linux; alinha com o pacote v4, que já casa por basename).
- `test_mac.py:teste_tocar_musica_cai_no_dados_local` (player mockado —
  nunca abre de verdade).
Suíte 130/130 na árvore combinada. **Commitado 29/09 pelo outro chat em
`12fb8e5`** (lote música + meu fallback + meu teste; refinamentos Win/Linux
deles por cima) e `d13771a` (TID canônico texturas→cheats). Tudo no GitHub,
suíte segue 130/130.

## 22. QC 21 resolvido pelo chat Mac (28/09 — 117/117)

1. **sha nos 6:** digests GitHub p/ Citron dmg
   (`4813ad4…79a2d9`) e Azahar 1.1 (`46839e22…a1a1a`); DeSmuME sem digest
   no release + 2 pkgs Python com pin local do baixado (`70c5239a…`,
   `767ed35a…`, `d42e4bbf…`). `garantir_mac()` revalida sha no cache hit
   (apaga e aborta se divergir).
2. **montar_dmg:** sem glob sem quoting (`find` em `$APP`, `[ -d "$APP" ]`),
   falha de attach/cp/detach propaga `return 1`, mnt limpo no erro.
3. **tamanho:** `montar_universal.py --mac-leve` (mac/ só payload+instalador,
   resto via ⬇) + aviso de MB do mac/ no build cheio.
4. **.dmg coberto:** `teste_extrair_app_mac_dmg_com_hdiutil_mockado` +
   `teste_extrair_app_mac_zip_rejeita_macosx` (sem macOS, sem rede).
5. **links:** `except (OSError, RuntimeError)` (loop!) +
   `teste_links_darwin_internos_e_vetos` (interno/externo/quebrado/loop/
   veto sem flag). Nota: Windows sem privilégio de symlink pula o teste
   (WinError 1314, padrão da suíte).
6. **_app_macos:** exato > prefixo da família > maior (helper solto não
   vence mais).
7. **docs:** não editei o texto do outro chat; correções aqui: item 20
   deles vale com **117/117** (era 110/110) e `test_mac.py` com **14
   testes** (eram 7); numeração duplicada 18/19/20 (minha + deles) fica p/
   renumerar numa integração futura com disco. Commit `9e14c22` já tinha os
   `montar_*.py` "sujos" do QC.

## 21. QC 28/09 — pendências p/ o chat Mac (leitura retroativa, sem commit)

QC rodado no Win em 28/09 (modo Plan, sem editar código, sem commit):
suíte **114/114** + `app_win.py --selftest` 24 jogos. `HEAD 88a907c` + sujos
`montar_mac.py` + `montar_universal.py` intactos aqui.

**P/ o dono Mac decidir/aplicar (nada feito aqui):**
- `montar_mac.py:33-57`: só Azahar 2126.1.2 tem sha; outros 5 só tamanho
  mínimo em `garantir_mac()`. Sugestão: fixar sha256 de todos ou documentar
  fallback. Cache atual em `codigo/ferramentas/.cache/mac/` já tem os 6.
- `montar_mac.py:125-135`: `montar_dmg()` sem `set -e`, `detach` silencioso,
  teste `[ -d "$2"/*.app ]` quebra com espaço. Revisar quoting + falha real.
- `montar_universal.py:118`: `copytree(mac)` agora leva ~400MB+ (2 pkgs +
  1 zip + 2 dmgs) p/ o universal. Sugestão: variante leve ou aviso de tamanho.
- `atualizacao.py:187-204`: ramo `.dmg` (`hdiutil`) sem cobertura — suíte veta
  `subprocess` (`executar.py:95`). Cobrir com mock ou teste só no Mac real.
- `atualizacao.py:36-58`: `links=True` aceita symlink interno. Falta teste de
  link quebrado/loop + externo vetado.
- `emuladores.py:_app_macos`: fallback "maior binário" pode pegar helper.
  Sugestão: lista fechada `azahar/citron/desmume*` após nome exato.
- Docs: itens 18/19 duplicados neste MD; item 20 diz 110/110 e `test_mac.py`
  7 testes — atual é 114/114 e 11 testes. Atualizar na integração.

## 23. QC 28/09 2ª varredura — p/ Mac e Win (117/117, sem commit, sem código)

Baseline Win (só leitura): `py_compile` ok 12 arqs, suíte **117/117**,
`app_win.py --selftest` 24 jogos, árvore limpa em `8f32a11`. Nada editado.

**P/ o dono Mac (não mexi):**
- `atualizacao.py:172`: `_aplicar(..., links)` chama `recuperar(dest)` sem
  `links` no `except` — rollback darwin veta symlink interno `.app` em vez
  de restaurar. Trocar p/ `recuperar(dest, links)`.
- `atualizacao.py:214`: `extractall` não restaura symlink `Frameworks/...`
  — `.app` Qt quebra no update. Extrair preservando link ou revalidar pós.
- `atualizacao.py:254-257`: `sha256` opcional — asset sem `digest` passa só
  com size. Exigir sha ou avisar fraco (DeSmuME/Citron).
- `base.py:268,309`: lock `so=os.name` = `posix` p/ Mac+Linux — Linux apaga
  lock do Mac e vice-versa; sem pid vivo, crash bloqueia 24h. Sugestão:
  `so=sys.platform` (`darwin` vs `linux`) + checar host/pid.
- `emuladores.py:1519`: `_limpar_hub` só limpa mod conhecido — mod renomeado
  vira órfão em `load/mods/<tid>/`. Varredura de órfãos.
- `montar_mac.py:INSTALADOR`: `cp -R` em vez de `ditto`, sem `chmod +x
  MacOS/*`, sem validação zip-slip.

**P/ o dono Win/Linux (vale após commit Mac, não fiz):**
- `banco.py:536-556`: `atualizar_jogo` sem `try IntegrityError` — colisão no
  triplo estoura `sqlite3` cru (criar trata em `:531`). Envolver em ValueError.
- `banco.py:249-267`: `_garantir_uuid` não dedup duplicata existente —
  `CREATE UNIQUE INDEX` quebra `get_db` em banco sujo. Dedup antes do índice.
- `scans.py:1381-1398`: restore por `uuid` não volta `save_path/mods/
  mods_off/game_code/regiao` — perda silenciosa. Espelhar `pacotes.py:44-47`.
- `app_tui.py:490`: `escolher()` ignora `ch==-1` com `timeout(500)` —
  busy-spin. Tratar `-1` como idle.
- Ideias: `base.py:192` `resolver_exe` assimétrico (nt checa existência,
  mac/linux não); `preview_pasta` 4 walks + `_capa_steam` síncrona trava
  import offline; docs aqui: vale **117/117** e `test_mac.py` **14 testes`.

## 24. Texturas HD 3DS — aplicado parcial, retomável (Win, 28/09 — 120/120)

Pedido do Tuco: 6 packs HD com liga/desliga. Fonte: `PokeTex-3DS`
(Gray-Rice, arquivo do fórum Citra): ORAS Donel, USUM Volya, X/Y WIP.
Tamanhos: USUM 119MB, XY 1.75GB, ORAS 2×~1.4GB (total ~4.6GB).

**Feito (sem commit — Plan; suíte 120/120 + selftest 24):**
- `base.py`: `TEXTURAS_DIR` + `garantir_dirs` + `__all__` (molde MUSICAS).
- `scans.py:SKIP_DIRS`: + `texturas` (scanner nunca importa PNG como jogo).
- `bib_nucleo/texturas.py` (novo, sem banco, darwin-safe): toggle por rename
  `<tid>/` <-> `<tid>.off` em `user/load/textures/` (sem admin, sem cópia);
  `listar/alternar/definir/tem/instalar` + `TITULOS` dos 6. `test_texturas.py`
  (3 testes). `montar_portatil.py:incluir_azahar` + `montar_linux.py`: poda
  `load/textures` do instalador (GBs não viajam — trato dos mods).
- Presets (dados/, fora do git): `hd2x` (2x + custom/preload on, limite 100),
  `turbo150` e `performance` intactos. Live em `hd2x`.
- USUM instalado e ligado: `.../load/textures/00040000001B5000/` e `...1B5100/`
  (1226 PNGs, 338MB cada, via `instalar_textura`; toggle provado off/on).
- Cache: `codigo/ferramentas/.cache/texturas/` (ignorado, fora do scanner).

**Pendente (máquina desligou no meio do XY — nada perdido):**
- `XY.7z` com 0 bytes (interrompido no início; `curl -C -` retoma do zero
  limpo). `USUM.7z` completo + extraído (reuso, sem rebaixar).
- Retomar (raiz do repo, jogo fechado):
  `curl.exe -L -C - --retry 3 -o codigo\ferramentas\.cache\texturas\XY.7z
  https://github.com/Gray-Rice/PokeTex-3DS/releases/download/xy/XY.7z`
  depois ORAS Part-1/Part-2 (mesmo padrão, tag `ORAS`), extrair com
  `Games/ferramentas/7z.exe x`, instalar um TID por vez com
  `instalar_textura` (USUM serviu o mesmo conteúdo pros 2 TIDs do par;
  checar layout do XY/ORAS antes — pode vir pasta única ou por jogo).
- Não commitei: `base.py`, `scans.py`, `montar_*.py` sujos + `texturas.py` e
  `test_texturas.py` novos. Frontend (menu Texturas espelho do Mods) ficou
  p/ depois — toggle hoje via `definir/alternar_textura`.

## 24b. Texturas HD — 6/6 ativos (Win, 28/09 — 120/120, sem commit)

- XY.7z retomeu de 1.69GB e fechou em 1834769856 (confere); 7634 PNGs
  (1.77GB) instalado em X `...55D00` + Y `...55E00` (pasta única serve os 2).
- ORAS: Part-1 (12366) + Part-2 (3447) complementares, merge 15813 PNGs
  (3.13GB) em OR `...11C400` + AS `...11C500`. Cuidado: `Copy-Item` falhou
  em silêncio no merge — usar `robocopy /E` (vale p/ próximos packs).
- USUM: 1226 PNGs (338MB) em US `...1B5000` + UM `...1B5100` (piloto).
- Total ativo ~10.5GB em `user/load/textures/`; toggle off/on provado no OR
  (rename instantâneo). Live em preset `hd2x` (2x + custom/preload on).
  Suíte 120/120 + selftest 24 verdes. Cache `.cache/texturas/` mantido
  (reinstalo sem rebaixar). Sem commit (Plan).

## 24c. HD tal qual Mods + verificação + barras (Win, 28/09 — 122/122)

Achado chave: live estava em `performance` (custom OFF) — HD instalado mas
NÃO carregava nesta sessão. `preparar_lancamento` aplica o preset do jogo
a cada play, e os 6 estavam em `performance`.

**1. HD interno como Mods (código, sem commit, 122/122 + selftest 24):**
- `texturas.py`: + `estado_textura()` (1 TID) e `flag_custom_textures()`
  (lê `Utility/custom_textures` do ini live; None se ilegível).
- `bib_core.py`: reexporta `texturas` (frontends usam `core.*`).
- `emuladores.py:preparar_lancamento`: aviso se HD ativo + flag off
  ("...troque p/ hd2x"); `try/except`, lazy import, sandbox-neutro.
- TUI `menu_jogo` + `Texturas` → `menu_texturas` (liga/desliga imediato +
  instalar de pasta; sem banco).
- GUI: linha `🖼️ HD ligado/desligado` no detalhe (`tem_textura`, barato) +
  linha `Texturas HD` no diálogo com botão Ligar/Desligar imediato.
- `test_texturas.py`: + estado/flag + preparar-aviso (5 testes).
- `montar_*.py`: `load/textures` podado do instalador (GBs não viajam).

**2. Verificação dos 6 (só leitura + backup `biblioteca-20260928-220456`):**
ROMs ok, TIDs batem com as pastas, PNGs íntegros (amostra 20/TID, 0 ruins),
6 pastas ativas. Correção aplicada: `azahar_preset=hd2x` nos ids 6–11
(antes `performance` = HD invisível). Hub aberto na hora: só UPDATE breve,
vale no próximo `recarregar`.

**3. Barras pretas (print OR):** `layout_option=0` (Padrão empilha as telas
na vertical = retrato; em 16:9 fullscreen vira pilarbox gigante) + 16.6ms
cravado = vsync. Fix em `hd2x.ini`: `layout_option=2` (Tela Grande: topo
grande + AreaNav no canto, preenche 16:9 sem esticar). Aplica no próximo
  play sozinho (preset). Se ainda sobrar borda fina lateral: normal (3DS é
  4:3/5:3, sem stretch não some 100%). 100% da barra de status = correto.

## 24d. Commit `b068bb6` (Win, 28/09 — 122/122, push ok)

Commitado + push (pedido do Tuco p/ testar): `bib_core.py`, `base.py`
(TEXTURAS_DIR), `emuladores.py` (aviso HD), `scans.py` (SKIP texturas),
`texturas.py` + `test_texturas.py` (novos), `montar_linux/portatil.py`
(poda textures), `app_tui.py` (menu Texturas), `app_win.py` (🖼️ + botão).
Fora do git (dados/): presets `hd2x/turbo150`, 6 pastas HD ativas (~10.5GB),
DB com `hd2x` nos ids 6–11 (backup `biblioteca-20260928-220456`), cache
`.cache/texturas/`. Árvore limpa.

## 25. Estudo Azahar extenso (Win, 28/09 — só pesquisa, nada aplicado)

Fontes: `citra.azahar-emu.org/help+wiki`, wiki `azahar-emu/azahar` (8 pgs),
`azahar-emu.org/faq+compatibility`, releases (18x res, `.vkch`, `-c/-x`),
comunidade (Joey Retro, GBAtemp 60fps/NoOutlines, PokeCoders, Reshiban).

**Mecânicas que o Hub não usava:** per-game `config/custom/<TID>.ini`
(`use_global=false` por chave — persiste sem merge no play); `cheats/
<TID>.txt` Gateway (`*citra_enabled`, reboot); `load/textures` com
`pack.json` new-hash + `preload` vs `async_custom_loading`; `disable_right_
eye`, `cpu_clock%` (5–400), `accurate_mul`, `skip_duplicate_frames`,
`simulate_gpu_timings`; CLI `-f/-w/-g/-i/-c/-x`; shader cache `transferable/
precompiled` (apagar só pós-driver); updates em `0004000E` (ausentes aqui).

**Achados locais:** 8GB RAM (preload ORAS 3GB = risco de swap!);
sem updates (jogos em versão base); sem `aes_keys` (ROMs descriptografadas,
ok); shader cache por TID existe; driver NVIDIA 32.0.16.1692 (Vulkan ok).

**Plano proposto (não implementado):** `hd2x-oras` (audio stretching OFF) +
`hd2x-xy` (ON) por jogo; `preload=false + async_custom_loading=true` nos
packs grandes; testar Vulkan (`graphics_api=2`) num jogo; gerenciador de
cheats no Hub (molde texturas: `cheats/<TID>.txt` + toggle `*citra_enabled`)
p/ 60FPS + No Outlines (casar versão base!); per-game `custom/<TID>.ini`
como alternativa ao merge global. Detalhe e códigos no chat.

## 26. Gerenciador de cheats tal qual Mods (Win, 28/09 — 124/124, sem commit)

Escolha do Tuco no plano do item 25. `bib_nucleo/cheats.py` (novo, sem
banco, darwin-safe): `user/cheats/<TID>.txt` Gateway, toggle por
`*citra_enabled` (preserva resto byte a byte), `listar/ativos/definir/
alternar/adicionar` (novo nasce OFF, valida par hex, caps 64/1024)
`/remover` (apaga arquivo vazio). `bib_core.py` reexporta.
TUI `menu_jogo` + `Cheats` (toggle + adicionar multi-linha + remover).
GUI: `💥 N/M cheats` no detalhe + linha `Cheats` no diálogo com `…` →
`_janela_cheats` (alternar imediato + adicionar com caixa de código +
remover; aviso "vale após reiniciar"). `test_cheats.py` (2 testes).
Semeados OFF nos 6 TIDs (códigos GBAtemp/Reshiban p/ versão base, sem
updates aqui): 60FPS (`08C61A84` XY, `08C650C0` ORAS, `33F67FE8` USUM) +
Sem contorno (`00361D34/38` XY, `00379EB4/B8` ORAS, `0042E2B8` USUM).
Risco: endereço de região/versão errada trava — testar 1 por vez, saves no
Hub. Suíte 124/124 + selftest 24. Sem commit.

## 27. Commit `d5622a5` (Win, 28/09 — 124/124, push ok)

Commitado + push (pedido do Tuco, testes refeitos antes): `cheats.py` +
`test_cheats.py` (novos), `bib_core.py`, `app_tui.py`, `app_win.py`.
Fora do git: 6 `.txt` em `user/cheats/` (OFF). Árvore limpa.

## 28. Controles + commit `89ee6b1` (Win, 29/09 — 136/136, push ok)

Controle do Tuco: Xbox 360 USB (VID 045E/PID 028E, XInput slot 0).
`controles.py` (novo): detectar winmm+XInput+OEM (Linux `/proc`, resto []),
`fotografar/aplicar/listar` presets `[Controls]` em
`dados/presets/controles/`, viewer `ler_estado/resumir/capturar`, mapas
padrão Xbox/PS/Switch (GUIDs verificados no gamecontrollerdb) e `bib_core`.
`test_controles.py` (6 testes).
**Ressalva honesta:** `gerar_perfil()` marcado experimental — Azahar 2126
resetou binds `engine:sdl` p/ teclado em 5 boots controlados (até 1 bind
só, nos 2 estilos; nulo preserva). Fluxo confiável: mapear 1x no Azahar →
`fotografar`. Live restaurado do backup (teclado intacto).
Pendente: menu Controles na GUI/TUI + calibragem do gerador com amostra
real. Músicas (item 29) seguem em aguardo sem commit.

## 30. Controles no Hub validados no boot (Win, 29/09 — 140/140, sem commit)

Tuco mapeou no Azahar (perfil `Switch PRO`, ativo). Amostra real revelou o
formato exato: `api:controller,...,maptype:guid+port,name:...,port:0`,
DPad = botões 11–14 (SDL enum), ZL/ZR = eixos 4/5, sticks planos
`axis_x/axis_y + deadzone`, guid SDL real `0300b969...7200` (≠ tabela!).
Causas dos resets achadas por bisseção: estilo nativo (`chave="v"` +
`chave\default=false`) + chaves DENTRO da seção `[Controls]` (append no
EOF caía em `[Utility]`).
`controles.py`: gerador recalibrado, `detectar_sdl()` (guid real),
`nomes_sdl()`, `perfil_ativo()` (foto/aplica miram o ativo), `aplicar`
por cirurgia de linhas. Boot-verificado: perfil posicional completo (17
binds) sobreviveu; live restaurado (Switch PRO intacto). Presets em
`dados/presets/controles/`: `switch-pro` (foto real) + `xbox-360-posicional`.
GUI: seção Controles + `_janela_controles` (listar/fotografar/aplicar/
gerar/testar ao vivo). TUI: menu Controles idem. Testes 140/140 (7
controles + menu TUI). Sem commit.

## 32. Revisão detalhada pré-volta (Win, 29/09 — 143/143, sem commit)

Achados e correções (tudo com teste):
- Viewer rotulava bits XInput errado (A=bit 12, não 0): `XINPUT_NOMES`
  corrigido + `XINPUT_PARA_SDL`/`xinput_para_sdl()` p/ futuro wizard.
- `_xinput_slots` levantava `AttributeError` fora do Win: guarda `os.name`.
- Preset fotografado levava `name`/`input_maptype` (renomeava slot alheio):
  `fotografar` só captura binds.
- `switch-pro.ini` + `xbox-360-posicional.ini` limpos e válidos.
- Live final: `profile=1`, `size=2`, binds Switch PRO intactos (boot-provado).
Suíte 143/143 (9 controles) + selftest 24. Sem commit. Pode voltar.

## 33. Preset sumido: restaurado via Hub (Win, 29/09 — 144/144, sem commit)

Live estava `profile=0/size=1` com o Switch PRO órfão (Azahar lista só até
`size`): dropdown só Default + pad morto. Causa provável: Apagar/explorar
no diálogo do Azahar (ou boot com seleção perdida).
Recuperação em 1 comando (Azahar fechado): `aplicar_preset_controle(
'switch-pro', perfil=1)` — recriou os 29 binds + `profile=1`/`size=2`;
boot-provado estável. Preset Hub estava intacto (fotografia salva).
Novo: `aplicar_preset_controle(nome, perfil=None)` (None = ativo) com
teste de slot explícito. Suíte 144/144 + selftest. Sem commit.

## 35. Pad funcionando independente do flip (Win, 29/09 — sem commit)

Causa do "não funciona" isolada por eliminação (reproduzido 3×): boot COM
jogo volta `profile` p/ 0 (GUI preserva); binds intactos, TBD o motivo no
Azahar (perfil lido ok, seleção não persiste no game-boot).
Solução robusta (boot-provada): mapa Switch PRO espelhado também no
`profiles\1` via `aplicar_preset_controle('switch-pro', perfil=0)` —
qualquer perfil ativo tem o pad. Binds sdl sobrevivem reescritas do
Azahar e merges do Hub (só seleção era volátil).
Falta o teste humano: abrir o jogo e mover/atacar com o controle.

## 36. Causa final: perfil "Default" é regenerado (Win, 29/09 — 144/144)

Bisseção completa (8 boots): o Azahar REGENERA no game-boot todo perfil
chamado `Default` p/ teclado de fábrica (GUI preserva; jogo não).
`aplicar_preset_controle` agora renomeia `Default`→slug do preset (com
teste). Estado final boot-provado: `profiles\1` = Hub Pad + `profiles\2` =
Switch PRO (ambos sdl, sobrevivem); `profile=0` tanto faz.
Suíte 144/144 + selftest. Sem commit.

## 37. Blindagem final: pad nos 2 slots (Win, 29/09 — sem commit)

Azahar seguia colapsando `size`→1 (dropdown só Default, pad morto mesmo
com binds órfãos intactos). Estratégia à prova de flip: `profiles\1` =
Hub Pad com o mapa Switch PRO completo (29 binds via Hub) — qualquer
perfil ativo tem controle. Pedido ao Tuco: jogar SEM abrir o config
(o diálogo pode fazer parte do gatilho).

## 38. Raiz do flip: sujeira no ini (Win, 29/09 — 145/145, sem commit)

Bisseção final (arquivo mínimo limpo preserva; completo com crud flipa):
linhas `X\default\default` + duplicatas que o próprio Azahar grava ao
re-salvar QUEBRAM a leitura dos perfis no game-boot (GUI preserva).
`higienizar_controles()` embutido no `aplicar` (só texto, com teste);
boot com jogo pós-higiene 100% estável (`profile=1/size=2`, Hub Pad +
Switch PRO intactos). Estado live final confirmado.
Suíte 145/145 + selftest. Sem commit. Falta o teste humano no jogo.

## 39. Perfil único = imune (Win, 29/09 — sem commit)

Multi-perfil no Azahar é instável (flips e colapsos recorrentes mesmo com
higiene). Consolidado em 1 perfil só ("Switch PRO", mapa completo sdl):
boot GUI e boot com jogo preservam tudo (`profile=0/size=1` estáveis).
Bônus: o Azahar parece batizar o perfil pelo controle conectado.
Se o pad não responder AGORA, o problema não é mais config — é runtime
(SDL do Azahar × controle) e o próximo passo é testar outro controle/cabo.

## 40. Apagar no diálogo destrói perfis (Win, 29/09 — sem commit)

Achado final: `beginWriteArray` do Qt APAGA as chaves do array e reescreve
do vetor em memória — o Switch PRO sumiu porque algo reduziu a lista a 1
(botão Apagar no diálogo do Azahar é o caminho). Restaurado via preset Hub
(`aplicar switch-pro → perfil 1`, 29 binds + nome arrumado).
REGRA: não mexer em Apagar/Restaurar/Limpar no config do Azahar;
configurar controle SÓ pelo Hub.

## 41. Perfil único estável (Win, 29/09 — sem commit)

Após ~20 boots de bisseção: multi-perfil + crud do próprio Azahar quebram
a leitura no game-boot (flip/colapso); arquivo mínimo preserva. Fix final:
1 perfil só ("Hub Pad", mapa sdl completo), sem `\default\default`, sem
duplicatas — boot com jogo 100% estável (`profile=0/size=1` fixos, binds
intactos). Sem código novo (só cirurgia via Hub). Falta teste humano.

## 42. Hub escreve bytes idênticos ao Azahar (Win, 29/09 — sem commit)

Tuco criou "pp" na mão em 30s e funcionou. Fotografei e diff contra o
preset do Hub: **0 diferenças** — formato nunca foi o problema. O que
quebra é mexer em perfis (Apagar/renomear/criar) no diálogo + flips de
seleção no game-boot. Regra mantida: configurar controle SÓ pelo Hub,
que tem a fotografia guardada (`switch-pro.ini` = backup exato).

## 43. Commit `b2805c0` (Win, 29/09 — 145/145, push ok, temp limpo)

Commitado com permissão total: controles calibrados no boot real,
higiene anti-flip embutida, UI GUI/TUI, XInput com bits certos (A=bit 12)
+ `xinput_para_sdl`. Temp de debug apagado (só restou o de outros chats).
Árvore limpa. Pad com perfil único estável — teste no jogo vale.

## 44. Atalhos do Desktop via Hub (Win, 29/09 — 139/139, sem commit)

Megabonk/Mewgenics/ULTRAKILL abriam o Hydra. Novo `app_win.py --jogar
BUSCA` (id/título, exato vence; erro claro se 0/ambíguo; conta horas ao
fechar; sem janela). Desktop: 3 atalhos recriados p/ `pythonw app_win.py
--jogar "<Jogo>"` (ícones mantidos); originais Hydra guardados em
`Desktop/Atalhos-Hydra-antigos/`. PokeXGames intocado (não é Hydra).
Cuidado: outros chats mexeram junto (Linux paridade + REMOVE Citron total;
meu UI sweep foi absorvido). Suíte 139/139 + selftest.

## 45. Repacks automáticos (Win, 29/09 — 145/145, sem commit)

`bib_nucleo/repacks.py` (novo): `.zip` stdlib / `.rar/.7z/.iso` via 7z
(`BIBLIOTECA_7Z`, erro claro sem extrator) → `Piratas/<slug>` → desembrulha
pasta única → limpa `Read_Me/.url/_redist` + `_CommonRedist` raiz duplicado
+ `setup_*` redundante (só com exe jogável; sem exe, preserva e avisa
"precisa instalar") → acha exe (SKIP + nome/tamanho) → importa dedup →
apaga archive. `.zip` com `biblioteca.json` segue pacote do Hub.
`analisar_arquivo` ganha `arquivo-jogo`; GUI (thread+progresso) e TUI;
`importar_json` TUI não manda mais todo `.zip` p/ pacote. `test_repacks.py`
(6). Suíte 145/145 + selftest. Sem commit.

## 46. Sephiria + Wanderburg reais + commit `a37e2c8` (01/10 — 147/147)

Teste real com 2 rars achou bug de verdade: `Path("D:")/"Games"` vira
relativo (`pasta_piratas` + `ferramenta_7z`) — corrigido + regressão.
Títulos com sufixo (`-SteamRIP.com`, `-DODI`…) agora limpam (`_REP_TAGS`).
Importados ids 48/49 (backup `biblioteca-20261001-050157`), archives
apagados, títulos arrumados. Commit + push com permissão total.
Pendente: capas dos 2 (manuais no diálogo).

## 47. Capas Sephiria + Wanderburg (01/10 — 148/148, sem commit)

AppIDs Steam (2436940, 3624140) + `header_image` oficial via `_capa_steam`
+ `salvar_capa_bytes` (backup `biblioteca-20261001-052058` antes).
600×800 PNG padrão nos 2 (`48-2436940.png`, `49-3624140.png`).
Nenhum outro jogo sem capa. Suíte 148/148 + selftest 24/24.

## 48. Capa automática padrão (01/10 — 150/150, sem commit)

`_appid_steam_por_titulo()` (storesearch, nome exato, nunca levanta) +
`importar_repack` tenta capa sozinho após importar (falha de rede vira
`capa_pendente`, nunca trava). GUI/TUI mostram "capa ✓".
Sephiria/Wanderburg ganharam `shop=steam` + appid (backup `...-052603`).
Testes com `urlopen`/saves mockados. Suíte 150/150 + selftest.

## 49. Commit `6080531` (01/10 — 150/150, push ok)

Commitado a pedido: capa automática + minimizar/restaurar + testes.
Árvore limpa.

## 50. Higiene pré-público (01/10 — 150/150, sem commit)

Sem segredos/vazamentos no git; `dados/dist/cache/build/lock/lnk`
ignorados. Corrigido p/ revisão: README fiel (sem Switch/Citron, com
repacks/cheats/HD/controles/músicas/--jogar/testes/estrutura), filtro
TUI sem "Switch" morto, comentário `.iss` sem Citron, `LICENSE` MIT,
`.gitignore` + `*.db/*.bak`, nome do zip no `.bat`. Sem TODOs no código.
Suíte 150/150 + selftest. Sem commit.

## 47. Minimizar/restaurar + revisão geral (01/10 — 148/148, sem commit)

GUI minimiza ao abrir jogo (`iconify`) e volta ao fechar (`deiconify`+
foco, com guarda p/ janela fechada); TUI redesenha em loop (sem suspender).
Health: todas as APIs usadas existem pós-refactors dos outros chats;
música do outro chat absorvida sem conflito; tocar_musica deles com mock.
Suíte 148/148 + selftest. Sem commit.

## 34. Auditoria total pré-volta (Win, 29/09 — 144/144, sem commit)

Só certezas verificadas:
- Suíte 144/144 + selftest 24/24 verdes; `main` inclui música do outro
  chat (12fb8e5) e TID único (d13771a) sem conflito (meu diff: só controles).
- Live: `profile=1/size=2`, 17 binds Switch PRO intactos; `profile\default`
  existe mas é `false` (o próprio Azahar mantém; inofensivo).
- DB: 24 jogos (6× `hd2x`), tabela `musicas` existe vazia; 6 texturas HD
  ativas; 60FPS on nos 6 + contorno on no OR; presets `switch-pro` e
  `xbox-360-posicional` válidos.
- Revisão achou e corrigiu: viewer com bits trocados, crash fora do Win,
  preset com identidade junto, `fotografar` gerando `X\default\default`.
- Sem commit. Pode voltar.

## 31. Treco do controle resolvido 1-por-1 (Win, 29/09 — 142/142, sem commit)

Culpa minha em 2 dos 3 (igate; desculpa). Causas raiz, todas provadas:
1. **Preset sumiu**: `profile\default=true` travava o perfil 0 p/ sempre
   (fonte: `config.cpp` ReadSetting — meu teste com `profile=0` cunhou a
   linha e meus restores a preservaram). Removida + `profile=1` + `size=2`.
2. **Pad morto no jogo**: consequência do (1) — boot caía no Default
   teclado. Com o perfil fixo em 1, binds intactos após boot (provado).
3. **Duas abas**: `_janela_controles` agora é instância única (foco em vez
   de duplicar) + filhas (Testar) morrem junto.
Endurecido no Hub: `aplicar` garante `profiles\size`, remove o veneno
`profile\default` e confirma `profile=`; `fotografar` pula flags `\default`
(antes gerava `X\default\default` + `"false"` com aspas). Preset
`switch-pro` refotografado limpo (31→0 flags). Testes 142/142 + selftest.
Sem commit.

## 28. Integração Harmoni → Músicas (PLAN, Win, 28/09 — nada implementado)

Fonte: `Ssenseii/harmoni` (MIT, GUI+CLI, Spotify OAuth/Exportify → baixa
via YouTube/yt-dlp, ID3, formatos mp3/m4a). Local:
`Downloads/Harmoni-Windows/` (config mp3, saída `music/`, manifestos
`data/tracks.json+playlists.json`; `spotify_client_id` vazio = fluxo
Exportify CSV). Decisões do Tuco: mp3, tabela própria, copiar, player do SO.

**Desenho (molde texturas/cheats, stdlib, darwin-safe, sem `MZ/ELF`):**
1. `bib_nucleo/musicas.py`: `MUSICA_DIR` override (`BIBLIOTECA_MUSICA_DIR`
   → Harmoni `music/`); `varrer_harmoni()` (exts `MUSICA_EXTS`, lê ID3v2
   manual p/ artista/título + casa com `tracks.json`); `importar_musicas()`
   (copia p/ `dados/musicas/<artista>-<titulo>.mp3`, dedup `musica_sha`).
2. `banco.py` migração **v12**: tabela `musicas` (id, titulo, artista, album,
   musica_path, musica_sha, origem, criado_em) — jogos intactos.
3. `scans.py`: SKIP `music`/`data` do Harmoni; `pacotes.py` ESQUEMA 3→4 +
   categoria `musicas/` (opcional, avisa tamanho).
4. Play: `startfile`/`xdg-open`/`open` (player do SO). GUI/TUI: seção
   Músicas (buscar, tocar, importar). `test_musica.py` (mp3 fake + tmp).
5. Linux: Harmoni é exe — lá vale .py/docker ou pasta `music/` via partilha;
   Mac: `BIBLIOTECA_MUSICA_DIR` aponta p/ onde estiver.
Pré-requisito do Tuco: baixar 1 playlist no Harmoni (Exportify) p/ validar
o piloto com arquivos reais.

## 29. Build Músicas integrado (Win, 28/09 — 128/128, sem commit)

Harmoni nunca rodou (sem `music/`); piloto com fixtures fiéis (ID3v2.3).
`musicas.py` (novo): `harmoni_dir()` (env ou `Downloads/Harmoni-Windows/
music`), `ler_tags()` ID3 manual + fallback `Artista - Titulo`,
`tracks.json` opcional, `varrer/importar` (cópia slug + dedup sha),
`tocar_musica()` (player do SO, nunca em teste). `banco.py` v12: tabela
`musicas` + CRUD (+ `__all__`). `pacotes.py` v4: `musicas/` por nome de
arquivo + restore casando linha (com checagem sha anti-colisão); `esquema
(2,3,4)` no filtro de capas (regressão pega em teste). `bib_core` reexporta.
GUI: seção Músicas (lista, tocar, importar em thread, excluir) + TUI menu
Músicas (buscar/tocar/importar/excluir). `test_musica.py` (4) + ajuste
`test_linux.py` (índice do Sair). Revisão: 0 dups em 222 exports, tocar
fora da suíte, sem SKIP global (scanner não alcança mp3), sem commit.

## 28. 60FPS padrão + Editar sem trava + sem popups (Win, 28/09 — 124/124)

- 60FPS ligado nos outros 5 (OR já estava): 6/6 ativos (`definir_cheat`,
  Azahar fechado). Efeito no próximo boot de cada jogo.
- Trava 1–2s no Editar: era `estado_textura()` contando 15k PNGs do OR
  (medido 1.84s) na abertura do diálogo. `_ler_tex` agora mostra on/off
  barato (`is_dir`, 0.0s) e conta em thread como a capa.
- Popups abrir/fechar: `jogar()` e `_sessao_fim()` usavam `showinfo`.
  Novo `_aviso_barra()` (texto no `lbl_cont`, não-modal); erros seguem
  `showerror`. TUI já era `msg` (sem popup).
- Revisão: detalhe usa `tem_textura`/`listar_cheats` (baratos); resto do
  abrir-diálogo (capa 200px, presets, TID 512B) é ms. Suíte 124/124 +
  selftest 24. Sem commit.

## 44. Paridade Linux dos subsistemas novos + dedup cross-OS (Linux, 29/09 — 149/149)

Suíte estava 132/148 aqui (16 falhas só-Linux; baseline no commit limpo
confirmou — não era sujeira local):
- 14 falhas (cheats/texturas/controles): fakes `azahar.exe` invisíveis no
  Linux → `azahar_user_dir()` vazio em cascata. Helper `azahar_fake()` em
  `executar.py` (exe no Win, AppImage no Linux).
- 1 falha: `_arquivos(links=True)` aceitava symlink quebrado — `resolve()`
  não-estrito nunca falha no Linux (no Win o teste pulava por privilégio,
  mascarando). Veto explícito com `os.path.exists`.
- 1 falha: teste mac↔win comparava `Path()` com separadores mistos (raiz
  sandbox é posix) — comparação normalizada (vale nos 2 SOs).
- Dedup cross-OS (bug real, achado importando): `chave_dedup` agora
  canonicaliza via `win_para_linux` + `importar_lista` dedupa ROMs por
  (título, ROM) ignorando o exe do emulador (azahar.exe × AppImage).
  Import cego 24→108 revertido (backup `biblioteca-20260929-213843.db`).
  PENDENTE decisão do Tuco: 10 variantes FR/DE/IT/JA/ES de FireRed/LeafGreen
  (só EN no banco) + 50 exes scan-disco p/ revisão no TUI (I → Pasta).

## 45. Remoção total do Switch (Linux, 29/09 — 138/138)

Emulação não vingou: removido TUDO (controles e Mac intactos).
Banco (backup `biblioteca-20260929-222821.db`): 2 linhas rom-switch
apagadas (22 jogos), capas e `Roms Switch/` (386M) apagados,
`dados/presets/citron/` vazio removido, coluna `citron_preset` dropada
via migração v13 (`_garantir_sem_citron`, bancos legados incluídos).
Código: provider Citron + `ROM_EXTS_SWITCH` + `default_roms_switch_roots`
+ `default_emu_switch` + `citron_*` + `backup_saves_citron` + preset nas
duas UIs + filetypes + botões ⬇/saves + `test_citron.py` + Citron nos
4 montar_*; `dist/`: 2 `.dmg` apagados. Trocados: `?`-counts dos
INSERTs (banco/scans) após tirar a coluna. Pacotes .zip antigos com
rom-switch restauram como origem crua (sem provider).

## 51. Aba Músicas no Hub + revisão Harmoni (Win, 06/10 — 155/155, sem commit)

Pedido do Tuco: Hub com jogos + aba Músicas; tocar segue com jogo aberto
(player externo, processo independente — `tocar_musica` + `Popen`
não-bloqueante do `jogar`, nada a mudar no launch).
Revisão F0: suíte 153/153 + selftest 24 no `640d713` do outro chat
(punch-list 23: nada em músicas, sem conflito) + fumaça isolada
(varrer/import-dedup/busca/tocar-mock/excluir OK). Achados: `harmoni_dir`
None (sem `music/` real) e tags `.m4a/.ogg/.flac` mudas (fallback nome).
Feito (sem commit): `musicas.py` +`texto_musica`/`sugestao_harmoni_dir`;
GUI 5º NAV `🎵 Músicas` (lista embutida, Tocar/Importar/Excluir, detalhe
♪ + botão vira TOCAR, busca filtra, `jogar`/`excluir`/`editar` com guarda,
aviso `Tocando:` na barra); TUI rótulo único + sugestão + msg com faixa;
`test_musica` helpers + `test_dialogo` aba (com display). Suíte 155/155 +
selftest 24. Não commitado: `musicas.py`, `app_win.py`, `app_tui.py`,
`test_musica.py`, `test_dialogo.py`. Falta humano: abrir Hub, importar
pasta real, tocar + abrir jogo juntos.

## 52. CSV → mp3 tal qual Harmoni, Fase A pronta (Win, 06/10 — 160/160)

Levantamento real: Exportify (`Track/Album/Artist Name(s)` com `;`),
mp3s Harmoni com ID3 válido (`ler_tags` lê tudo), `music/` 51 = `Musicas`
21 por sha, yt-dlp/ffmpeg fora do PATH (bins do Harmoni em `Temp\_MEI*`,
efêmeros). Travado com Tuco: BYOB + 1º resultado + nativo-sem-ffmpeg.
Commits: aba `bdbd3f9`, core `73cc2b8`, UI `cc1d28c` (árvore limpa).
Fase A core: `baixar.py` (`ler_csv_exportify` utf-8-sig, nunca levanta;
`primeiro_artista`) + tabela `downloads` **v14** (`enfileirar` dedup
uri/par/catálogo, `listar/marcar/limpar`, `marcar` valida estado) +
`test_baixar.py` (3). Validado nos 3 CSVs reais (23+22+6, re-fila zera).
Fase A UI: aba ganha modo fila (toggle `Fila (N)`, `⬇ CSV…`, limpar
prontas/falhas, detalhe estado/erro/uri, JOGAR desabilitado na fila) +
TUI `Baixar de CSV…`/`Fila (N)…`/`menu_fila`. 2 FAILs meus no caminho
(`cget state` ttk devolve `Tcl_Obj`; limpar não tira pendente — Clear
Done). Suíte 160/160 + selftest 24. Segue Fase B (yt-dlp BYOB mockado).

## 53. Fases B+C: fila baixa e vira mp3 no Hub (Win, 06/10 — 165/165)

Commits `876cfcf` (B) + `89ec94d` (C), push ok, árvore limpa.
Fase B: `localizar_ytdlp` (env→PATH, molde 7z), `casar_video`
(ytsearch1 1º resultado + video_id auditável), `baixar_faixa`
(Popen com progresso `--newline`, staging `dados/baixados/` novo em
`BAIXAR_DIR` + SKIP + `garantir_dirs`; estado novo `baixado` nos
`ESTADOS_DOWNLOAD`), botões `⬇ Baixar fila` (GUI thread + TUI
síncrono; sem binário = aviso orientando).
Fase C: `localizar_ffmpeg`, `converter_faixa` (mp3 lame q2 + ID3v2.3
da fila; sem ffmpeg copia nativo `MUSICA_EXTS` + aviso, outro ext =
falha honesta; staging apagado no sucesso, fica p/ retry na falha),
`importar_fila_pronta` + botões `Importar baixadas` (GUI thread + TUI).
Testes tudo mockado (run/Popen/ffmpeg enlatados; `localizar` via env —
hermético mesmo se a máquina ganhar os bins). 2 correções no caminho:
`Tcl_Obj` do `cget state` e limpar-não-tira-pendente. Suíte 165/165 +
selftest 24. Falta real: instalar yt-dlp (+ffmpeg p/ mp3) e rodar a
fila Terra de verdade.

## 54. Player interno no Hub (Win, 06/10 — 172/172, commit `c0a18f8`)

Pedido do Tuco: tocar sem app externo. Travado: interno padrão +
externo como fallback + auto-avançar.
`player.py` (novo): `Player` (transporte + playlist, backend injetável)
+ backends `MciBackend`/`AfplayBackend`/`LinuxBackend`/`NuloBackend`.
Achado provado por bisseção: MCI-`mpegvideo` quebra aqui (rc=277,
driver interno; `mciqtz32.dll` presente) mas `waveaudio` é sólido
(rc=0) — então mp3/m4a decodificam via ffmpeg em `dados/cache-wav/`
(teto LRU 1GB; `BAIXAR_DIR`/`CACHE_WAV_DIR` + SKIP, sem schema);
`.wav` vai direto, sem ffmpeg. Sem ffmpeg: mp3 interno nega honesto
(aponta `BIBLIOTECA_FFMPEG` + sugere Externo…).
GUI: transporte ⏮ ▶/⏸ ⏹ ⏭ + `Externo…` + `♪ atual` na aba, poll 1s p/
auto-avançar, detalhe TOCAR= interno, excluir para o que toca; TUI:
submenu Tocar/Pausar/Próxima/Parar/Externo/Excluir + título `♪` +
vigia por loop. Prova real (ffmpeg portátil no Temp, apagado depois):
Cotidiano tocou — `playing`, pos andando, dur 168373 (= CSV!), pause/
resume ok, `terminou` falso durante. Suíte 172/172 (7 player, todos
mockados) + selftest 24. Linux (`mpv/mpg123/ffplay/play`) e Mac
(`afplay`) só valem em máquina real — avisar chats pelo `.md` se
falhar. Fora de escopo: volume/seek.

## 55. Revisão geral músicas + capas automáticas (Win, 06/10 — 177/177)

Commit `5e1db25` (push ok, +488/−124, árvore limpa). Sem TODOs no código.
Botões: modal `_janela_musicas` podado (duplicava a aba; config `Músicas…`
agora abre a aba; teste migrou p/ aba); detalhe da aba mostra a arte
(`carregar_miniatura` 216×280, tile ♪ se sem); TUI ganhou `Baixar
capas…` (com guarda de rótulo, igual `Fila (`).
Capas automáticas (iTunes Search, sem chave, molde `_capa_steam`):
`capa_album_url` (artista+álbum, cai p/ artista+título, 600px),
`baixar_capa_album` (rede vira pendente, nunca trava), coluna
`musica_capa` **v15** (CREATE + ALTER aditivo em pré-capa),
`salvar_capa_musica_bytes` (`mus-<id>-<slug>.jpg`, 2MB),
`baixar_capas_faltantes` (botões GUI thread + TUI).
Parâmetros: env `BIBLIOTECA_CAPA_MUSICA_AUTO` (default on; `0` desliga),
auto no `importar_musicas`/`converter`/`importar_fila_pronta`
(`capa_auto=` explícito p/ hermeticidade), estado visível no config.
Pacote: arte viaja no manifesto (`mus:<sha>`) e restaura por sha.
Prova real: iTunes devolveu 600x600 de Construção e Flor de Lis.
Suíte 177/177 (5 capa, mocks) + selftest 24 (migrou o banco real p/
v15 sem escrita além da coluna).

## 56. Print do Tuco: botões por modo + msg certa (Win, 06/10 — 177/177)

Commit `9603f7f`. Print mostrava 51 faixas reais no Hub com botões de
jogo ativos na aba + popup ffmpeg com texto de conversão no play.
`_botoes_detalhe(modo)`: jogo tudo normal; música só TOCAR+Excluir
(Editar/Novo travam); fila tudo travado. Msg de play sem ffmpeg agora
é de play (aponta `BIBLIOTECA_FFMPEG` + sugere Externo…, sem o texto
de `.m4a` da Fase C); barra da aba diz player interno. Testes cobrem
os 3 modos. Próximo real: instalar ffmpeg p/ interno + `⬇ Baixar
capas faltantes` p/ tirar os `sem capa`.

## 57. Hub baixa ffmpeg/yt-dlp sozinho (Win, 06/10 — 180/180)

Popup do Tuco resolvido na raiz: `instalar_ffmpeg`/`instalar_ytdlp`
(oficiais gyan.dev/GitHub, checagem MZ + tamanho, sem `extractall`,
só Windows; fora dele orienta gerenciador) plantam em
`Games/ferramentas/` (casa do 7z); `localizar_*` agora: env →
ferramentas → PATH; `ffmpeg_pronto`/`ytdlp_pronto` com piso 1MB.
UI: TOCAR sem ffmpeg oferece baixar (~80MB) em thread e retoma
sozinho; `Baixar fila` sem yt-dlp oferece (~30MB); config mostra
`áudio: ffmpeg ✓/✗ · yt-dlp ✓/✗` + botão `⬇ Dependências de áudio`;
TUI tem a opção equivalente (bloqueante, explícita).
Prova real: ffmpeg 105MB instalado de verdade + Flor de Lis no
interno (`tocando`, pos andando, dur 223190 ≈ CSV). Suíte 180/180
(3 installer, mocks) + selftest 24. Commit `ec91622`.

## 58. Freeze ao trocar faixa + catálogo SteamRip (Win, 06/10 — 185/185)

Commits `12de8f6` (player) + `98dccd1` (steamrip), push ok, limpa.
Freeze: causa era decode+sha na thread da UI (cada troca 1–3s); agora
`_tocar_faixa_async` (corte imediato + `Carregando…` + token que mata
thread velha; auto-avançar/⏭⏮ pelo mesmo caminho, falha silenciosa
vira aviso, sem popup em loop). Bônus: runner aguenta traceback com
`♪` (utf-8 fallback).
SteamRip (`fontes.py`, fonte já conhecida da vigília): `?s=` acha
posts, post lista hosts (`GOFILE/MegaDB/FileDitch…` via
`<strong>+DOWNLOAD HERE</strong>`); FileDitch direto, Gofile via API
guest (token+server+contents, pega o maior), MegaDB via HEAD
(html = protegido, manda abrir a página); `.rar` cai em `Piratas/`
com progresso e o repack existente importa (`Importar último`).
Ordem por `BIBLIOTECA_STEAMRIP_HOSTS` (default diretas 1º).
UI: `⬇ SteamRip…` no IMPORTAR (busca/resultados/hosts/Baixar/Abrir/
Importar) + TUI `menu_steamrip` (URL mostrada p/ abrir fora).
Provas reais: busca `megabonk` → post → 3 hosts verdadeiros
(403 inicial era só UA; headers de navegador resolvem; `urljoin`
corrige href relativo). Suíte 185/185 (5 fontes, mocks) + selftest.

## 62. Ball x Pit: links mortos nos hosts (08/10 — 222/222, sem commit)

Print do Tuco: `fileditch: veio HTML` + `gofile: 404`. Reprodução ao
vivo provou que não é bug de parse: o fileditch redirecionou para a
homepage do SteamRip (arquivo expirado lá) e o conteúdo gofile
`rYYCIOpF` devolve 404 na API (upload removido). Ambos os links do
post estão mortos; o Hub tentou os 2 e relatou certo.
Melhorias no `fontes.py`: HTML com redirect para fora do host agora
diz `arquivo expirado ou removido no host` (`_mesmo_host` tolera
subdomínio/CDN, então CDN legítimo não é acusado); 404 em gofile e
megadb vira `conteúdo expirado ou removido (404)` em vez de erro
genérico. Nada publicado em nenhum caminho de falha (temporário +
chepotência mantidos). Regressão `teste_steamrip_expirado_e_404`
+ suíte 222/222 e selftest 24. Sem commit.
## 63. Catálogo FitGirl no Hub (08/10 — 225/225, sem commit)

Ball x Pit morto no SteamRip mas vivo na FitGirl (280 MB + OST).
Mapeado ao vivo: busca `?s=` (`h1.entry-title`), post com espelhos
`Filehoster:` (DataNodes/FuckingFast/MultiUpload) + magnets + 1337x.
Download direto impossível: os 3 espelhos exigem JS/sessão/CF e o
`.torrent` é JS-renderizado — o Hub cataloga e entrega ao SO
(`abrir_url`: navegador p/ espelhos, cliente torrent p/ magnet).
`fontes.py`: `buscar_fitgirl`/`detalhes_fitgirl`/`nome_magnet`/
`abrir_url`; diálogo virou `dlg_catalogo(fonte)` (SteamRip mantém
Baixar/Importar; FitGirl tem Abrir selecionado/página +
Importar arquivo…); TUI ganhou `menu_fitgirl` + `Catálogo FitGirl`.
Prova real: `ball x pit` → post → 3 espelhos + 2 magnets com nome.
Suíte 225/225 + selftest 24. Sem commit.
Para Ball x Pit: jogo morto nos 2 hosts — usar `Abrir página`,
tentar outro jogo ou o Hydra; quando o post trocar os links, o
catálogo baixa sem mudar código.

## 59. Player pulando faixas: causa real e correção (Win, 06/10 — 189/189)

Causa reproduzida no Windows: aliases MCI são locais à thread de abertura.
`_tocar_faixa_async` abria/tocava no worker; a thread Tk consultava o alias
e recebia **rc=263** (nome de dispositivo inválido), interpretado como fim.
A tentativa anterior de esperar 3s só adiava os pulos; foi removida.

Correção em `player.py` + `app_win.py`: `preparar()` faz hash/conversão
no worker; `open_preparado`/play/pause/status/close ficam na thread Tk.
Resultados chegam por `SimpleQueue`, drenada por `after` da própria UI
(worker não chama Tk). Preparações serializadas; resultados com token
antigo são descartados sem parar a faixa atual; Stop/fechar invalidam
carregamentos e fecham o dispositivo. Próxima/anterior usam a playlist
capturada, mesmo após buscar ou trocar para Jogos.

Fim natural MCI exige `stopped` + posição/duração válidas no final;
status desconhecido/erro não avança. Backends de processo só terminam
automaticamente com código de saída 0. Não há espera artificial de 3s.

Verificado: `py_compile`, **189/189** (regressões de afinidade MCI,
consulta falha, troca rápida, Stop/fechar no carregamento e avanço real),
selftest 24 jogos/24 cards em snapshot temporário do banco (origem aberta
só-leitura). Prova real com Tk `mainloop` + ffmpeg instalado: Flor de Lis
ficou na mesma faixa >7s com posição andando; pausa/continuar corretos;
troca A→B→A→B respeitou a última escolha; WAV de 300ms avançou exatamente
uma vez para o seguinte. Banco e cache da prova ficaram no Temp.

Ainda sem commit: `player.py`, `app_win.py`, `test_player.py`,
`test_dialogo.py`. Fechar/reabrir o Hub carrega a correção.

## 60. Volume geral do PC pelo Hub (Win, 06/10 — 193/193, sem commit)

`volume.py` (novo, stdlib): Windows Core Audio (`IAudioEndpointVolume`)
via ctypes/COM, não usa volume do MCI nem abre outro app. APIs públicas:
`ler_volume_pc`, `definir_volume_pc`, `ajustar_volume_pc`, `alternar_mudo_pc`;
porcentagem limitada a 0–100 e valores NaN/infinito/inválidos rejeitados.
Cada operação consulta a saída padrão novamente (fones/HDMI), cria/libera
interfaces na mesma thread e equilibra CoInitializeEx/CoUninitialize.
Guard darwin antes de nt; imports nativos só dentro do backend Windows.

GUI: rodapé fixo na barra lateral `VOLUME DO PC`, slider 0–100%, botões
−/+ de 5 pontos e Silenciar/Ativar som. Funciona em Jogos e Músicas.
Polling de 1s reflete teclas/mixer externos; sincronização é só-leitura,
não sobrescreve o volume ao abrir o Hub. Slider com debounce de 80ms;
polling respeita arrasto/ajuste pendente; fechar cancela timers. Sem saída
de áudio, controles ficam desabilitados e recuperam no próximo poll.
Botões compactos; regressão GUI verifica que cabem nos 180px do rodapé.

Verificado: py_compile, **193/193** (3 testes de volume + integração GUI;
inclui regressões do player), selftest 24 jogos/24 cards em snapshot.
Prova real pela GUI: − mudou 100→95%, + voltou a 100%, slider a 99%,
silenciar/ativar funcionaram e MCI permaneceu `playing`. Volume e mute
originais foram restaurados no fim da prova. `README.md` atualizado.

Além dos arquivos pendentes do item 59: `volume.py`, `bib_core.py`,
`test_volume.py`, `README.md` (e os ajustes em `app_win.py`/`test_dialogo.py`).

## 61. Revisão técnica p/ engenheiro (07/10 — 221/221, sem commit)

Auditoria `ast` de 48 arquivos (~22 mil linhas, 288 exports): sem
definições/`__all__` duplicados, sem `self.*` sem método, sem colisão
de exports. 20 erros comprovados corrigidos, os principais:
`importar_musicas` devolvia `ignorados` e a GUI/TUI lia `ignoradas`
(`KeyError` em todo import de música); callbacks de worker chamavam
Tk direto (novo `frontends/despacho.py` com fila + ciclo de vida);
higiene de controles apagava `profile` de outras seções do INI;
`encerrar_sessao_manual` gravava no banco errado e apagava marcador
inválido; restore não voltava `save_path`/mods/código/região;
`baixar_steamrip` parava no 1º host e publicava download parcial;
rollback Mac ignorava `links`; pacote de música validava SHA depois
de publicar; overlay de mods copiava por cima de arquivo local.
Novos: `arquivos.py` (publicação atômica), `diagnosticar.py`
(somente-leitura), `empacotar_fontes.py` (ZIP da árvore + SHA-256),
`CONTRIBUTING.md`, `docs/ARQUITETURA.md`, `docs/REVISAO_TECNICA.md`
e CI Windows/Linux × 3.10/3.14. Launchers corrigidos p/ casa raiz
(com fallback `dados/dados/`); `copiar_app` único nos 3 builders.
Verificado: 221/221 + selftest em snapshot + entrega de fontes
(74 arquivos, 1.99 MB, sem coleção). Falta validação real em Linux,
Mac, rede, áudio, instaladores completos e outro SO da casa.

## 64. Parte 1 — acabamento Tk e revisão (09/10/2026, sem commit)

Projeto: `D:\Tuco-Compartilhado\Jogos\biblioteca`. Pedido ativo: polir o
Tk atual, auditar e preparar recomendações; Parte 2 ainda não iniciada.
Relatório atual: `docs/PARTE1_VISUAL_E_AUDITORIA.md`.

- Novo `frontends/aparencia.py`: tema local sem pip, botões nine-slice,
  ícone, `BarraAcoes` com quebra de linha e `PainelRolavel`. Já incluído
  em `montar_portatil.py:APP_ARQS`, usado pelos três builders.
- GUI: tabelas Treeview nas quatro listas, sidebar rolável, filtros por
  contexto, detalhes separados no compacto (<1120 px), capas uniformes,
  ícones vetoriais e resize sem reentrada (`update_idletasks` retirado da
  reorganização). Cache de capa distingue interpretadores Tk.
- qBittorrent estava em **LOCALAPPDATA**, não APPDATA. Torrent real ainda
  existe em `Local/qBittorrent/BT_backup` (o relato anterior de que saiu
  do cliente era incorreto). `torrents.py` agora calcula pelas peças do
  fast-resume v1/v2; disco pré-alocado nunca prova conclusão; single-file
  corrigido. GUI consulta mudanças a cada 3s, mas isso é o último estado
  salvo pelo cliente, NÃO velocidade/ETA da Web API. Importar ainda é uma
  ação explícita, não um pipeline automático persistente.
- Desejos: erro/retorno parcial preserva a lista; flag manual não se perde
  ao aparecer em sync. Parser JSON ruim não quebra. Endpoint antigo volta
  HTML; **não afirmar que login resolve ou que sync anônimo é impossível**.
  API moderna consultada retornou `{"response":{}}` para esta conta, sem
  distinção suficiente entre privacidade/vazio/indisponível.
- Sanear GUI em worker com backup; localiza o jogo antes de limpar e só
  remove `_CommonRedist` da raiz com igualdade de conteúdo SHA-256.
- Verificação final: **243 PASS, 6 SKIP, 0 FAIL (249 descobertos)**;
  selftest em snapshot/casa temporários: **25 jogos/25 cards**; sintaxe
  mínima 3.10 em 56 fontes; geometria visível 1280×800/960×600/860×560 e
  escala Tk 125%. Pyflakes sem nomes indefinidos, AST sem defs duplicadas.
- Banco real só-leitura: 25 jogos, 51 músicas, 4 desejos, nenhum exe ausente.
  Entrada `Balls` em `Piratas/BALL x PIT/Balls.exe` sem capa (metadados p/
  melhorar); torrent FitGirl 100% em `Piratas/BALL x PIT [FitGirl Repack]`.
  Coleção não foi editada nem limpa nesta Parte 1.
- Entrega de fontes atual: `dist/tucoteca-fontes-parte1-20261009.zip`
  (80 arquivos + manifesto, 2.03 MB, integridade ZIP validada).
- Árvore continua com trabalho acumulado não commitado. Não usar `stash`
  para provar regressão (mistura outros trabalhos); não commitar sem pedido.

## 65. Parte 2 — runtime/sidecars/compactação (09/10/2026, sem commit)

Usuário aprovou o visual e pediu otimização, integração e compactação. Primeira
entrega concluída; relatório: `docs/PARTE2_RUNTIME_E_INTEGRACOES.md`.

- `bib_nucleo/ferramentas.py`: manifesto editável, paths locais, zipapps e
  overrides. Pacote identificado por `manifesto-runtime.json` não usa PATH/
  instalação canônica do PC como fallback. `base.resolve_home` reconhece pacote.
- `qbit.py`: cliente com `--profile/--configuration=tucoteca/--relative-fastresume`,
  API loopback e perfil em `dados/perfis/qBittorrent_tucoteca`. Magnets do Hub
  vão ao exe direto. **GUI qBittorrent exige Password_PBKDF2 mesmo com LocalHostAuth=false**:
  conferido nos fontes 5.2.4; bootstrap PBKDF2-SHA512 gera hash válido. Provas
  nativas de API/torrent local artificial/100%/pausa/retomada passaram e cliente
  de prova é encerrado sem mexer no perfil instalado.
- GUI Downloads: consultas só em worker, snapshot para renderizar, API mostra
  velocidade/ETA e controles. Histórico permanece fallback. API ainda não é
  pipeline persistente de instalação/importação automática.
- Banco cacheia inicialização por inode/mtime/schema_version; invalida para
  edição/migração, backfill UUID preservado. Benchmark 100 conexões mediana
  91,74→54,10 ms (~41% menos tempo, não confundir com velocidade de todo app).
- `montar_superhub.py`: runtime Win x64 completo. Python/Tk/Pillow, Azahar,
  DeSmuME, qBit, **7z + 7z.dll**, FFmpeg, yt-dlp zipapp oficial + QuickJS-NG.
  Sem estados pessoais/mods/HD/debug `.pdb`; terceiros originais sem UPX.
  Scripts Tcl/Tk em cache usados antes de tentar download.
- **Bug crítico descoberto/corrigido:** `podar_dieta` usava `*.py[cod]` e
  apagava `.pyd` (SQLite/Tk!) depois do selftest. Agora remove só pyc/pyo;
  teste protege pyd e novas provas rodam depois de extrair ZIP e 7z.
- `dist/tucoteca-superhub-windows-x64-20261009.zip`: **144,22 MiB**.
  `.7z`: **97,16 MiB** (antes ZIP 298,10 MiB); árvore ~370,42 MiB. Provas,
  hashes e versões em `dist/superhub-verificacao.json`. Runtime começa vazio;
  coleção original (25 jogos/51 músicas/4 desejos) não migrou para ele.
- Testes: **251 PASS + 6 SKIP, 0 FAIL (257 descobertos)**. Sintaxe 3.10 e
  Pyflakes (nomes definidos) nos 61 fontes. Core Mac/Linux em testes; novos
  artefatos são Windows x64, outros SOs ainda precisam de bundle nativo.
- Fontes atuais e helpers de build são locais e editáveis. Não commitar sem
  pedido; considerar a árvore toda ainda com alterações de várias sessões.

## 66. Organização local e launcher aberto (09/10/2026)

- `dist/` agora tem `windows/` (SuperHub ZIP/7z + verificação), `fontes/`
  (ZIPs de código), `historico/windows|linux|universal/` e `mac/` preservado.
  `montar_superhub.DIST` e default de `empacotar_fontes` seguem a organização.
- Runtime extraído/verificado em `programa/windows-x64/`. Dados existentes
  continuam em `dados/`; código em `codigo/`. Pasta `Games/Piratas` vazia
  do antigo bug de caminho relativo removida. Operações registradas em
  `docs/organizacao-local.json`.
- Backup antes: `biblioteca-20261009-091636.db` (+JSON). Atalhos anteriores
  copiados para `dados/backups/atalhos-antes-launcher-local/`.
- `BibliotecaHub.bat` prefere o Python embutido; chama `codigo/ferramentas/abrir_hub.py`,
  que configura Tcl/Tk e sidecars do runtime, e carrega fontes atuais com a
  coleção original. Perfis/caminhos de emulação existentes mantidos.
- Atalhos do repo/Desktop agora apontam ao BAT. Selftest com esse launcher:
  **25 jogos/25 cards**. Launcher aberto: processo pythonw embutido,
  janela `TucoTeca`, respondendo; log sem erro de startup.

## 67. Nome canônico + capa padrão no import (09/10/2026, sem commit)

- `scans.py:canonizar_steam()` novo: match exato normalizado na storesearch
  (até 3 requisições, nunca levanta); `_appid_steam_por_titulo` virou
  delegação (comportamento idêntico).
- `importar_repack` resolve nome da loja + appid antes do `pontuar` e grava
  `shop/object_id` no item → capa Steam automática passa a ser o padrão;
  offline preserva o título local.
- Corrigido ao vivo id 50: `Balls` → `BALL x PIT`, shop steam, object_id
  2062430, capa `50-2062430.png` (backup `biblioteca-20261009-210335` antes).
- Testes novos: `teste_canonizar_steam_exato`,
  `teste_repack_nome_canonico_e_capa` (o fixture inicial provou a regra:
  pasta fora do padrão real não casa — exact-match é o contrato).
- Verificado: **259/259 + selftest 25/25**. Preview manual (pasta/disco)
  mantém o título local — canonizar na UI-thread travharia a tela.

## 68. SteamRip morto, Downloads ok, Hell Clock pendente (09/10, sem commit)

- Ball x PIT no SteamRip: links genuinamente mortos nos hosts (gofile 404,
  fileditch devolve HTML de expirado — conferido ao vivo). NÃO é bug de
  automação: `baixar_steamrip`/`_descer` validam HTML/tamanho/redirect e o
  `fim_baixar` já oferece "Tentar no FitGirl?". Sem lixo salvo em disco.
- Aba Downloads verificada ao vivo com UI oculta: 2 torrents, API local,
  poll 3s, Pausar/Retomar/Verificar funcionando. Se o usuário não vê, é Hub
  desatualizado aberto (pedir restart pelo launcher).
- Hell Clock [FitGirl Repack]: 5/5 MD5 ok, 100% em
  `D:\Games\Piratas\Hell Clock [FitGirl Repack]`, fora do banco. É
  setup+bins (instalador): usuário roda setup como admin e importa a pasta
  instalada. Erro de extração dele: sem log no Hub, sem pasta parcial,
  57GB livres, bins íntegros → suspeito RAM (8GB total, 1,5GB livre, típico
  unarc/ISDone). Aguardando texto exato do erro.
- Atalho Ball x Pit recriado no Desktop (padrão `--jogar`, ícone Balls.exe;
  resolver confere id 50). Não existia nem em Atalhos-Hydra-antigos.
- `programa/` (build local com dados) entrou no `.gitignore` — nunca commitar.

## 69. Pasta dedicada do Hub (10/10/2026, Win)

- Workspace do agente saiu de `IA/Opencode Memory/` (agora vazia) para
  `IA/TucoTeca/`: `continuidade/TucoTeca.md` (este arquivo),
  `validacao/` (scripts + capturas), `sessao/` (notas de sessão).
  Código/coleção continuam canônicos em `Jogos/biblioteca/` (`REL_HOME`
  intacto). No Linux, ler aqui:
  `/run/media/tuco/Games/Tuco-Compartilhado/IA/TucoTeca/continuidade/TucoTeca.md`.

## 70. QoL 1.5 — git visível + integrações + textos + varredura (10/10, sem commit)

Sessão Win, continuidade de QoL 1.0 (`5565750`). Cada tópico um decimal.
Detalhes em `sessao/QoL-1.5.md` (+ `git-projeto.md`, `QoL-1.5-integracoes.md`,
`QoL-1.5-varredura.md`).

- **1.5.1 — git na pasta da sessão:** `.git` continua em `Jogos/biblioteca/`
  (não movido/duplicado). Espelho legível em `sessao/git-projeto.md`
  (atualizado no fim; comandos `--git-dir/--work-tree` p/ acompanhar sem sair
  daqui). Início: `main` ahead 2 (`1a8b089`, `5565750`), árvore limpa.
- **1.5.2 — integrações open source (só pesquisa):** curto prazo GameControllerDB
  (risco zero) → MusicBrainz/CAA sem chave → SteamGridDB por key → PCGamingWiki
  "Correções ↗" → HLTB sob demanda com cache; 2ª fase RetroAchievements +
  ProtonDB. GPL (Lutris/Heroic/SRM) só via CLI/BYOB, nunca embutido. Playnite
  como referência UX.
- **1.5.3 — textos pequenos (código, sem commit):** `Theme.subtitle` 12→14;
  `PosterCard` badge 10→12, PRONTO 9→11, status 11→13; `Main.qml` 12→14
  (subtítulos/herói/coleção/saúde/descrições), 11→13 (rótulos), 9–10→12–13
  (kickers/badge SOB DEMANDA). Só apresentação (34+/34−). Verificado:
  `test_qt` 11/11 + `test_visual` 10/10 + auditoria isolada 6 seções sem QML
  crítico (25 jogos/51 músicas/4 desejos, saúde 25/25; compacto 960×640 ok).
  Sujos: `qml/Main.qml`, `qml/PosterCard.qml`, `qml/Theme.qml`.
- **1.5.4 — varredura (só sugestões):** 5 quick wins (contagem com filtro, "+N
  outros", chip backup ≥7d, fila toasts, +1h no drawer), 5 médios (preço
  Desejos, DnD pasta, duração Músicas, restante Downloads, escala texto),
  3 grandes (gamepad Big Picture, lixeira desfazer, volume Linux). Não-fazer:
  sem repaginação, sem rede no recarregar, sem auto-import, sem GPL embutido.
- Coleção/banco não tocados (auditoria em cópia isolada no Temp). Sem commit
  (regra item 22); `main` segue ahead 2 + 3 sujos do 1.5.3.

## 71. QoL 1.5 — continuação e entregas 1.5.5–1.5.9 (10/10, sem commit)

Vale sobre o resumo inicial do item 70. Documento versionável no checkout:
`docs/QOL_1_5.md`; notas completas em `IA/TucoTeca/sessao/QoL-1.5.md`.

- **1.5.1 completado:** `IA/TucoTeca/projeto/` é junction NTFS para o checkout
  `Jogos/biblioteca/`, com `.git` real. `Git-Projeto.bat` na raiz da sessão
  mostra status/diff/log a cada 3s; `--uma-vez` conferido. No Linux usar o
  caminho canônico diretamente.
- **1.5.2 revisado com fontes oficiais:** Ludusavi (MIT, CLI JSON para saves)
  ganhou prioridade; MusicBrainz/CAA, SDL GameControllerDB e SteamGridDB seguem
  candidatos. Atualizar o txt SDL exige backend de entrada; não é navegação
  Qt automática. RetroAchievements: fonte oficial lista DeSmuME core libretro,
  não standalone; não confirma 3DS/Azahar. O documento citado anteriormente
  era de um fork. PCGamingWiki redirect não teve licença MIT confirmada
  (`license: null`). HLTB em prioridade menor.
- **1.5.5:** saúde verifica toda a coleção (antes parava no oitavo problema
  e distorcia `ok`); IDs completos, `+N outros` e filtro de pendências.
- **1.5.6:** contagem contextual, Limpar filtros, paleta selecionando o resultado
  correto apesar de filtros antigos; Ctrl+F no Início abre paleta, ordenação
  sincronizada. Primeira faixa da fila passa a estar marcada (índice zero).
- **1.5.7:** avisos FIFO, 7s e fechamento ×, sem sobrescrever texto/severidade.
- **1.5.8:** estado/idade de backup claros, texto ampliado, cabeçalho adaptativo
  e primeira linha de cards inteira no compacto. Selftest Qt conta coleção,
  não itens da tela Início (agora imprime 25 em vez de 0).
- **1.5.9:** Registrar horas no drawer e no Sistema, decimal com vírgula/ponto;
  encerrar pendência usa marcador e banco corretos. Backup de DB + marcador
  antes, pendência removida no sucesso e rejeição de registro duplicado.
- Verificado: **270 PASS + 6 SKIP, 0 FAIL (276)**; **15/15 Qt** após o último
  ajuste compacto; `py_compile` e `diff --check` OK. Auditoria 6 seções ×
  1440×920/960×640 + drawer/horas/config, sem QML crítico; selftest 25 jogos.
  Banco real preservado (SHA-256). Snapshot com 25 jogos/51 músicas/4 desejos
  em `%TEMP%/opencode/tucoteca-auditoria`; o "sem backup" nas capturas é da
  casa temporária, que não copia os backups reais.
- Relatórios em `IA/TucoTeca/validacao/qol-1.5-{testes,qt,visual}.json`.
  HEAD `1a8b089`, ahead 2; arquivos alterados: `app_qt.py`, `qt_bridge.py`,
  `servicos_ui.py`, 4 QMLs, `test_qt.py`, README e docs; não commitados.

## 72. QoL 1.5 — lote 1.5.10–1.5.13: conquistas sem login, Spotify, +integração, Piratas (11/10, sem commit)

Vale sobre o item 71. Detalhes versionáveis em `docs/QOL_1_5.md`.

- **1.5.10 — conquistas sem login:** SteamDB bloqueia bots (403); fonte viável é
  Comunidade Steam pública (título/descrição/ícone/% sem chave) + percentuais
  globais (nome interno sem chave), cruzados pelo %. % empatado = item parcial
  honesto (`sem_vinculo`), nunca adivinhação. Chave segue opcional p/ catálogo
  completo. Prova viva: Stardew 413150, 49 linhas PT-BR, 49/49 vinculados.
  Desbloqueios continuam só do save local, offline.
- **1.5.11 — Spotify funcional:** Client ID agora aceita 32 alnum (era só hex);
  Client Secret opcional libera busca pública (faixas/álbuns/playlists públicas)
  sem login; conta só p/ playlists e curtidas. Colar código manual quando o
  loopback falha; erros orientam (redirect/secret/porta). Sem credencial, a
  busca falha com mensagem clara em vez de silêncio.
- **1.5.12 — adicionar integração:** botão + Adicionar nas Integrações; atalho
  https persistido em `dados/integracoes-usuario.json` (tipos link/catálogo/
  emulador/download, `{q}` p/ busca). Padrões protegidos contra remoção e
  colisão de chave; sem plugins arbitrários (só URL).
- **1.5.13 — Piratas padrão (caso Hell Clock):** causa era o magnet ir ao
  cliente do SO (pasta dele) em vez do perfil do Hub. Agora magnets vão ao
  qBittorrent do Hub com savepath Piratas/ + categoria tucoteca (Qt/clássico/
  TUI); perfil antigo migra o DefaultSavePath; import clássico + botão
  Organizar movem o que caiu fora (com aviso de reaponte no cliente).
- Verificado: **295 PASS + 6 SKIP, 0 FAIL (301)**; auditoria 6 seções sem QML
  crítico; selftest 26 jogos; banco real preservado (SHA-256). Captura da tela
  Integrações com + Adicionar conferida.
- `repacks.py` segue CRLF na cópia de trabalho (normaliza p/ LF no commit).
  HEAD `1a8b089`, ahead 2, sem commit (regra item 22).

## 73. Ajustes seguros pós-CI: janelas ocultas, exe em subpasta, capas Qt (11/10/2026, commit local, sem push)

Detalhes versionados em `docs/AJUSTES_SEGUROS_2026-10-11.md`.

- Run CI `38107900310`: Qt verde; stdlib vermelho (Windows e Ubuntu, 3.10 e 3.14).
  Falhas: `test_mac` (loop de symlink), `test_repacks.symlink_nao_vaza`, e três testes
  tkinter de layout/tela cheia. Correção anterior no relato dizia "quase verde": errado.
- Feito: `opcoes_sem_janela()` em processos de fundo (yt-dlp, ffmpeg, 7z,
  nvidia-smi, player); exe em subpasta não é mais descartado em `achar_exe`;
  harness trata loop de symlink; miniaturas Qt com `Layout.*` fixo (aba Músicas,
  rodapé, recentes, Bibliotecas de música).
- Não feito por risco: fluxo Qt de pacotes RAR em Piratas (Slots-and-Daggers segue
  compactado), redesenho de Seu espaço/Provedores/Bibliotecas, mudanças no tkinter.
- Verificado localmente: suíte 358/358 sem falha (6 SKIP por ambiente); py_compile
  nos 8 arquivos; auditoria visual 7 seções sem QML crítico; banco real intacto.
- Limite: symlink é negado neste Windows (WinError 1314); os dois testes de symlink
  não exercitam as asserções localmente. Ubuntu e shell Linux ficam para o CI.

## 74. União de pastas: TucoTeca dentro da biblioteca (11/10/2026)

- Estrutura nova: o workspace de IA (continuidade, sessao, validacao, Git-Projeto.bat,
  README) agora fica em `D:\Tuco-Compartilhado\Jogos\biblioteca\workspace\`.
- `D:\Tuco-Compartilhado\IA\TucoTeca` virou **junction** para `...\biblioteca\workspace`:
  caminhos antigos em notas e atalhos continuam válidos.
- A junction `projeto\` (que apontava para a biblioteca) foi removida. O `.git` próprio
  da TucoTeca não foi trazido: não tinha commits, branch nem remoto. Backup completo
  (com `.git`) em `C:\Users\Tuco\Backups\TucoTeca-antes-da-uniao-20261011`.
- 24 arquivos copiados e conferidos por SHA-256. `Git-Projeto.bat` ajustado: repositório
  = pasta pai do workspace, com fallback absoluto; testado pelos dois caminhos.
- Repositório da biblioteca: um só `.git`. `workspace/` aparece como não rastreado e
  ainda não foi commitado (decisão pendente). Alterações pendentes preservadas.
- `sessao/git-projeto.md` ainda cita a junction `projeto` antiga: texto histórico.
