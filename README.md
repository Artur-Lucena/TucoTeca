# TucoTeca

[![Testes](https://github.com/Artur-Lucena/Projeto-Launcher/actions/workflows/testes.yml/badge.svg)](https://github.com/Artur-Lucena/Projeto-Launcher/actions/workflows/testes.yml)
[![Licença: MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Versão](https://img.shields.io/badge/vers%C3%A3o-1.0.0-informational)](VERSION)

Aplicativo local de biblioteca de jogos e músicas. Desktop moderno em
**PySide6 / Qt Quick** (frontend principal), ferramentas clássicas em tkinter
(**congeladas**: só correções críticas) e TUI curses no Linux.
Núcleo em **Python 3.10+ com biblioteca padrão**, SQLite e arquivos locais.
Qt é uma dependência da interface desktop, não do núcleo.

O catálogo, a importação local e a reprodução local funcionam offline.
Busca de capas, atualização de ferramentas/emuladores, CSV → áudio e
catálogo SteamRip usam rede **sob ação do usuário**. Pillow é opcional
para conversão/preview de imagens; ferramentas externas são descritas abaixo.

## Comece por aqui

| Objetivo | Documento/comando |
|---|---|
| Entender a arquitetura e as pastas | [docs/ARQUITETURA.md](docs/ARQUITETURA.md) |
| Ver o que foi auditado, corrigido e o que falta validar | [docs/REVISAO_TECNICA.md](docs/REVISAO_TECNICA.md) |
| Acabamento visual e revisão atual; prioridades da Parte 2 | [docs/PARTE1_VISUAL_E_AUDITORIA.md](docs/PARTE1_VISUAL_E_AUDITORIA.md) |
| Runtime completo, compactação e ferramentas independentes | [docs/PARTE2_RUNTIME_E_INTEGRACOES.md](docs/PARTE2_RUNTIME_E_INTEGRACOES.md) |
| Trabalhar em conjunto | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Desktop Qt, arquitetura e cobertura da migração | [docs/DESKTOP_QT.md](docs/DESKTOP_QT.md) |
| Visão TucoOS, roadmap e integrações | [docs/VISAO_OS.md](docs/VISAO_OS.md) |
| QoL 1.5: melhorias entregues, pesquisa e próximos ajustes | [docs/QOL_1_5.md](docs/QOL_1_5.md) |
| Diagnosticar a instalação sem alterar a coleção | `python codigo/ferramentas/diagnosticar.py` |
| Gerar a entrega de código para outro desenvolvedor | `python codigo/ferramentas/empacotar_fontes.py` |

## Executar

- **Windows:** `BibliotecaHub.bat` (Qt neste checkout) ou `py -3.14 codigo/frontends/desktop.py`.
- **Clássico (congelado):** `BibliotecaHub.bat --classico` ou Configurações → Abrir ferramentas clássicas.
  Recebe só correções críticas; novidades vão para o Qt.
- **Linux:** `./BibliotecaHub.sh` ou `python3 codigo/frontends/app_tui.py`.
- **macOS:** `BibliotecaHubMac.command` (experimental; requer Python com Tk).

Nesta instalação, `BibliotecaHub.bat` usa o Python e as ferramentas de
`programa/windows-x64/`, os fontes atuais de `codigo/` e sua coleção em
`dados/`. Os atalhos TucoTeca apontam para esse launcher.

Em um ambiente de desenvolvimento novo, instale a camada visual:

```powershell
py -3.14 -m pip install -r requirements-ui.txt
py -3.14 codigo/frontends/desktop.py
```

Sem PySide6, o dispatcher usa tkinter. `--big-picture` inicia Qt em tela cheia.
O launcher respeita `BIBLIOTECA_HOME` explícito em desenvolvimento.

Para uma coleção de desenvolvimento separada, na raiz do checkout:

```powershell
$env:BIBLIOTECA_HOME = Join-Path $env:TEMP "tucoteca-dev"
py -3.14 codigo/frontends/app_win.py --selftest
```

`BIBLIOTECA_HOME` é a **pasta-mãe de `dados/`**. A coleção contém banco,
capas, backups, saves, mods e músicas; permanece fora do Git. A trava
`.biblioteca.lock` impede abertura simultânea da mesma casa.

## Funcionalidades

- **Desktop Qt:** tema azul-noite/ciano, componentes QML, transições de hover,
  capas assíncronas, grade virtualizada, busca, favoritos, ordenação e painel
  de detalhes. Estados vazios, atividade em segundo plano e mensagens de erro.
- **HUD superior:** Início, Jogos, Músicas, Desejos, Downloads e Integrações ficam
  acessíveis também em tela cheia, junto da nova aba Vídeos. Player e volume do PC persistentes no rodapé.
- **Busca global:** **Ctrl+K** acha jogo/música/desejo/download na coleção local.
- **Big Picture:** botão **Big Picture** ou **F11**; **Esc** retorna à janela.
  **Ctrl+1…6** troca de categoria, **Ctrl+F** busca, **setas** navegam pela
  grade, **Enter** joga e **Espaço** abre detalhes. Teclado e mouse;
  navegação por gamepad ainda não implementada.
- **Jogos:** título, capa, horas, nota/status, etiquetas, favoritos e filtros.
- **QoL 1.5:** saúde completa da coleção com filtro de pendências, contagem
  contextual e Limpar filtros, busca global que seleciona o resultado certo,
  avisos em fila e registro manual de horas nos detalhes/Sistema.
- **Lançamento:** executável/provider por SO, minimização da GUI e registro
  de sessão; `--jogar "Título"` atende atalhos de Desktop.
- **Importação:** arquivo/pasta, ROMs com metadados, manifestos de lojas,
  Hydra e repacks. Archives são removidos após importação confirmada.
- **Emulação:** Azahar/3DS e DeSmuME/NDS, presets e backup de saves.
- **Mods/HD/cheats/controles:** gerenciamento local por jogo e presets.
- **Músicas:** importa uma pasta do Harmoni/áudio local, enfileira CSV do
  Exportify, baixa/converte áudio, busca capas de álbum e toca no Hub.
  A música continua enquanto o jogo está aberto. Player externo é opcional.
- **Bibliotecas de música:** Deezer, iTunes e MusicBrainz buscam faixas sem
  chave/login; escolha resultados e envie à fila para baixar/importar. Spotify
  usa configuração OAuth para playlists/curtidas e exibe o resultado na mesma lista.
- **Conquistas do Hub:** Steam fornece referência; o save nativo e regras locais
  determinam desbloqueios persistentes/offline. Saves sem leitor ficam pendentes.
- **Vídeos:** importa arquivos locais, pesquisa/baixa YouTube via yt-dlp,
  e abre com VLC/MPV/MPC-HC. Ferramentas de mídia reúne editores de imagem,
  editores/EQ de áudio e reprodutores; presets FFmpeg geram cópias importadas.
- **Integrações:** + Adicionar registra atalhos HTTPS próprios, incluindo busca
  por `{q}`; cartões personalizados são persistentes e podem ser removidos.
- **Volume do PC (Windows):** slider no rodapé Qt ou na barra lateral clássica;
  controla a saída padrão inteira. A interface clássica inclui −/+5 e mute.
- **SteamRip:** catálogo pesquisável, página do jogo, hosts e fluxo de
  download/importação. A disponibilidade é a do serviço remoto.
- **Desejos:** lista local, inclusão pela busca da Steam e importação de JSON.
  A sincronização remota pode ficar indisponível; falha ou resposta parcial
  preserva a lista anterior.
- **Torrents:** histórico local do qBittorrent, peças recebidas no último
  `.fastresume`, progresso e importação explícita dos concluídos. A aba consulta
  atualizações a cada 3 segundos; o cliente grava o histórico em seu próprio
  intervalo. Sem peças registradas, ocupação em disco é apenas uma estimativa.
  **Iniciar cliente** usa um perfil da coleção; API local mostra velocidade,
  ETA, pausa/retomada. Magnets do Hub vão ao cliente do Hub com destino
  Piratas/ (nunca ao cliente do SO); o que caiu fora pode voltar com Organizar.
- **Sanear pasta:** localiza o jogo antes da limpeza, preserva instaladores
  ainda necessários e compara redistribuíveis por conteúdo. Na GUI, roda em
  segundo plano; setups redundantes vão para `.hub-lixo/`.
- **Coleção portátil:** JSON/ZIP com identidade estável, capas, presets,
  músicas e saves opcionais. Backup versionado guarda os últimos 10 pares.

## Dependências por funcionalidade

As funcionalidades abaixo pertencem ao conjunto Qt + ferramentas clássicas.
A [matriz de migração](docs/DESKTOP_QT.md#cobertura) explicita onde cada fluxo está.

| Recurso | Requisito |
|---|---|
| Núcleo, banco, scanners e ZIP | Python 3.10+ stdlib |
| Desktop Qt | PySide6-Essentials 6.10.2 (`requirements-ui.txt`) |
| GUI clássica | tkinter/Tcl/Tk (em algumas distribuições Linux, `python3-tk`) |
| TUI | curses; no Windows prefira a GUI |
| Imagens JPG/WebP/conversão | Pillow opcional; PNG/GIF têm suporte Tk |
| RAR/7z/ISO | 7-Zip (`BIBLIOTECA_7Z` ou descoberta local) |
| CSV → áudio | yt-dlp; FFmpeg para MP3/conversão |
| Player interno Windows | MCI waveaudio; FFmpeg para formatos comprimidos |
| Player interno Linux/macOS | mpv/ffplay/mpg123/play ou afplay, respectivamente |
| Jogos 3DS/NDS | Emulador e ROMs próprios; Wine para executáveis Windows no Linux |

Ferramentas de áudio podem ser instaladas pelo botão de dependências no
Windows. `BIBLIOTECA_FFMPEG` e `BIBLIOTECA_YTDLP` permitem caminhos explícitos.
O mapa completo de configuração fica em [ARQUITETURA](docs/ARQUITETURA.md).

### SuperHub portátil Windows x64

`codigo/ferramentas/montar_superhub.py` monta Python/Tk/Pillow, Azahar,
DeSmuME, qBittorrent, 7-Zip completo, FFmpeg e yt-dlp com QuickJS-NG em
uma árvore independente. O yt-dlp oficial em zipapp reutiliza o Python
do pacote. Ferramentas e dados usam caminhos locais; o manifesto JSON é editável.

```powershell
py -3.14 codigo/ferramentas/montar_superhub.py --formato todos
```

Extraia o arquivo distribuído e abra `BibliotecaHub.bat`. A coleção é
mantida em `dados/`; o runtime novo inicia com perfis vazios. Coleções podem
ser transferidas pelo pacote de coleção do Hub. Preserve `dados/` em atualizações.

As entregas atuais ficam em `dist/windows/`; os ZIPs de código, em
`dist/fontes/`; versões anteriores, em `dist/historico/`.

## Estrutura resumida

```text
codigo/
  bib_core.py          fachada de compatibilidade para o núcleo
  bib_nucleo/         regras, persistência e adaptadores do sistema
  frontends/          GUI/TUI e dispatcher de callbacks
  ferramentas/        diagnóstico, entrega de fontes, builders e testes
docs/                 mapa técnico e relatório da revisão
.github/workflows/    testes automatizados Windows/Linux
midia/fontes-capas/   artes-fonte de referência, não consumidas pelo runtime
dados/                coleção e estado local (ignorado)
dist/                 entregas geradas (ignorado)
```

## Verificação

```powershell
py -3.14 codigo/ferramentas/testes/executar.py
py -3.14 codigo/ferramentas/testes/executar.py --modulo test_baixar
py -3.14 codigo/ferramentas/testes/executar.py --caso test_player.py teste_player_transporte
py -3.14 codigo/ferramentas/diagnosticar.py --json
```

Cada caso roda em subprocesso/sandbox próprio; escrita fora dela, rede e
processos externos são bloqueados. Os pulos por SO/display/privilégio
aparecem como `SKIP`. `--json arquivo.json` grava um relatório da suíte.

## Entrega ao engenheiro

```powershell
py -3.14 codigo/ferramentas/empacotar_fontes.py
```

Gera **`dist/tucoteca-fontes-revisadas.zip`** com a árvore de trabalho atual,
documentação, testes e manifesto SHA-256. Inclui módulos ainda não
commitados; exclui coleção, caches, histórico local, atalhos e outros
artefatos de build. O engenheiro pode extrair, seguir `CONTRIBUTING.md` e
executar a suíte sem receber seus dados pessoais.

Os installers de usuário continuam em `montar_portatil.py`,
`montar_linux.py`, `montar_mac.py` e `montar_universal.py`. Gerar um bundle
completo pode baixar componentes; instalar o bundle completo é offline.
Os instaladores e o porte macOS exigem também validação em seus SOs reais.

## Licença

Código do Hub: MIT, [LICENSE](LICENSE). Emuladores/ferramentas distribuídos
separadamente mantêm suas licenças e notas de origem nos bundles.
