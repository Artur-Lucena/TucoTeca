# TucoTeca

[![Testes](https://github.com/Artur-Lucena/Projeto-Launcher/actions/workflows/testes.yml/badge.svg)](https://github.com/Artur-Lucena/Projeto-Launcher/actions/workflows/testes.yml)
[![Licença: MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Versão](https://img.shields.io/badge/vers%C3%A3o-1.0.0-informational)](VERSION)

Um hub para a **sua** coleção de jogos, músicas e vídeos — no seu computador,
sem conta, sem nuvem e sem depender de ninguém para abrir a biblioteca.

Ele nasceu de uma necessidade simples: ter tudo o que eu já baixei em um só
lugar, com cara de aplicativo moderno, funcionando offline, e sem entregar
para terceiros a lista do que eu tenho. Hoje é usado por duas pessoas (Tuco e
Isa) e é mantido assim: projeto pessoal, estável, e com os limites ditos em
voz alta em vez de escondidos.

- **A coleção é sua.** Fica em `dados/`, na sua máquina. Nenhum servidor
  próprio, nenhuma telemetria, nenhum login obrigatório.
- **A internet é opcional.** Abrir, jogar, ouvir e ver funcionam sem rede.
  Buscar capas, letras, catálogos ou baixar algo é sempre **você quem pede**.
- **O que é de terceiros é separado do que é seu.** Emuladores e ferramentas
  são programas independentes, agregados como estão, com suas licenças.

## Primeiros passos

**Windows** — duplo-clique em `TucoTeca.bat`
(`BibliotecaHub.bat` continua como alias legado).

**Linux** — `./BibliotecaHub.sh` em um terminal (abre a TUI).

**macOS** — `BibliotecaHubMac.command` (experimental; precisa de Python com Tk).

Se você tem Python e quer desenvolver:

```powershell
py -3.14 -m pip install -r requirements-ui.txt
py -3.14 codigo/frontends/desktop.py
```

Sem PySide6, o hub cai automaticamente para a interface clássica em tkinter.
`--big-picture` abre direto em tela cheia; `--classico` força o modo clássico.

Para testar sem encostar na sua coleção de verdade:

```powershell
$env:BIBLIOTECA_HOME = Join-Path $env:TEMP "tucoteca-dev"
py -3.14 codigo/frontends/app_win.py --selftest
```

`BIBLIOTECA_HOME` é a pasta onde vive o `dados/` do hub. A trava
`.biblioteca.lock` impede que duas cópias abram a mesma coleção ao mesmo tempo.

## O que ele faz

**A biblioteca**
- Grade de capas, busca, favoritos, filtros por plataforma/status e ordenação.
- Detalhes com horas de jogo, nota, etiquetas, observações e conquistas locais.
- Jogar com um clique, escolhendo o executável certo para o seu sistema.
- Capturas de tela por jogo, notas e registro manual de horas.

**Músicas**
- Importa uma pasta inteira sem duplicar faixas.
- Toca enquanto você joga, com player persistente no rodapé.
- Baixa e converte áudio (yt-dlp + FFmpeg), busca capas de álbum e letras
  sincronizadas (LRCLIB), com cache local.
- Busca faixas no Deezer, iTunes e MusicBrainz sem precisar de conta.

**Vídeos e YouTube**
- Videoteca local, com retomada de onde parou e controle de velocidade.
- Na variante completa, o YouTube roda embutido com perfil privado; na
  essencial, abre no navegador do sistema.

**Baixar e organizar**
- Desejos com histórico: você marca o que quer, o hub ajuda a achar a fonte,
  baixa e importa, e só então marca como obtido.
- Catálogo SteamRip pesquisável e histórico local de torrents (qBittorrent).
- Organiza a pasta de downloads com hardlink ou cópia, sem apagar a origem e
  sem sermos "backup" — hardlink não é backup.
- Sanea pastas de instalação com cuidado: acha o jogo antes de limpar.

**Coisas pequenas que ajudam**
- Modo tela cheia (F11) navegável pelo teclado.
- Busca global `Ctrl+K`.
- Volume geral do PC no rodapé.
- Backup da coleção em um clique, exportável para outro computador.
- Perfis separados para Tuco e Isa (favoritos e filtros independentes).
- API local de leitura (desligada por padrão, só loopback, com token).

## O que ele **não** faz

Vale a dizer claramente, porque é a diferença entre um hub honesto e um
promessômetro:

- **Nada de gamepad.** A navegação em tela cheia é teclado e mouse.- **Nada de conquistas online, overlay ou integração com a Steam como
  destino.** A Steam serve só como catálogo e lista de desejos; as conquistas
  do hub são locais e persistidas no seu banco.
- **Nada de conta obrigatória ou sincronização entre máquinas.** O pacote de
  coleção existe para levar sua biblioteca de um PC a outro na mão.
- **Sem assinatura de código.** O Windows pode reclamar do SmartScreen na
  primeira execução.
- **macOS é experimental.** Os fontes e os testes mantêm os caminhos, mas não
  há bundle macOS validado.
- **Everything** (busca instantânea) é opcional; sem ele, a varredura normal
  continua sendo a fonte da verdade.

## Requisitos

| Recurso | O que precisa |
|---|---|
| Núcleo, banco e testes | Python 3.10+ (só biblioteca padrão) |
| Interface principal | PySide6-Essentials 6.10.2 (`requirements-ui.txt`) |
| YouTube embutido e vídeo interno | `requirements-extras.txt` (PySide6-Addons, variante completa) |
| Interface clássica e TUI | tkinter/Tcl/Tk e curses |
| Imagens JPG/WebP | Pillow (opcional; PNG/GIF funcionam sem ele) |
| RAR/7z/ISO | 7-Zip instalado ou no pacote |
| Áudio e vídeo | FFmpeg (conversão) e um player externo como opção |

Os pacotes prontos (veja abaixo) já trazem tudo isso junto — inclusive os
emuladores — e não pedem instalação de Python no Windows.

## Pacotes prontos

A release privada **v1.0.0** traz dois pacotes Windows x64:

| Variante | O que tem | Para quem |
|---|---|---|
| **essencial** | Sem Chromium: o YouTube abre no navegador do sistema | Quer o pacote menor e leve |
| **completo** | Com QtWebEngine e QtMultimedia: YouTube embutido e vídeo interno | Quer tudo dentro do hub |

Os dois incluem Python, Tk, Pillow, PySide6, 7-Zip, FFmpeg, yt-dlp,
QuickJS-NG, qBittorrent, Azahar e DeSmuME. A coleção começa vazia; para
trazer a sua, use **exportar/importar pacote de coleção** dentro do hub.

Para gerar você mesmo (na máquina de build, com os emuladores instalados):

```powershell
py -3.14 codigo/ferramentas/montar_superhub.py --extras essencial --revisao <SHA>
py -3.14 codigo/ferramentas/montar_superhub.py --extras completo  --revisao <SHA>
```

O builder monta o runtime, executa provas reais nele (tkinter, Qt, áudio MCI,
Chromium com rede bloqueada, qBittorrent) e repete as provas no pacote
extraído. Nada disso é simulado: se a prova falha, o pacote não sai.

Para montar a pasta da release (fontes + bundles + notas + checksums):

```powershell
py -3.14 codigo/ferramentas/preparar_release.py --revisao <SHA> --saida dist/release/v1.0.0
```

Esse comando confere hash por hash, garante que nenhum dado pessoal entrou e
escreve as notas da release. **Ele não publica nada** — a publicação no GitHub
é um passo separado e explícito.

O repositório [Projeto-Launcher](https://github.com/Artur-Lucena/Projeto-Launcher)
é privado e guarda apenas fontes, testes, documentação e o necessário para
build. Coleção, jogos, ROMs, saves, perfis pessoais e runtimes não entram no
Git. O histórico está explicado em
[docs/RECONCILIACAO_GITHUB.md](docs/RECONCILIACAO_GITHUB.md).

## Como o código está organizado

```text
codigo/
  bib_nucleo/          regras, persistência e adaptadores do sistema
    rede/              integrações de internet (sempre sob ação do usuário)
  frontends/           interface Qt Quick, clássica (tkinter) e TUI
    qml/secoes/        telas da interface Qt
  ferramentas/         diagnóstico, provas, empacotamento e testes
docs/                  arquitetura, revisões, decisões e responsabilidades
dados/                 sua coleção (nunca vai para o Git)
dist/                  pacotes gerados (também fora do Git)
```

A explicação completa, com o mapa de módulos, está em
[docs/ARQUITETURA.md](docs/ARQUITETURA.md). As decisões de produto e o que
ainda falta estão em [docs/VISAO_OS.md](docs/VISAO_OS.md).

## Testes

```powershell
py -3.14 codigo/ferramentas/testes/executar.py    # suíte completa
py -3.14 -m pytest --cobertura                    # com pytest e cobertura
```

Cada teste roda em processo e pasta temporária próprios, com rede, escrita
fora da sandbox e processos externos bloqueados. Nenhum teste toca a sua
coleção, abre jogo ou acessa a internet. Casos que dependem de Linux, macOS ou
display são marcados como `SKIP`, não como falha.

A mesma suíte roda na CI do GitHub em Windows e Linux, Python 3.10 e 3.14, com
e sem Qt, mais uma verificação de segredos no histórico. O guia de colaboração
é o [CONTRIBUTING.md](CONTRIBUTING.md).

## Privacidade e legal

- O hub é um **gerenciador local**: organiza o que você já tem. Ele não
  distribui, não hospedeia e não incentiva pirataria.
- Toda ação de rede (buscar capa, consultar catálogo, baixar letra) é disparada
  por você, com tempo limite e cache local. Se a rede falhar, você recebe um
  aviso e a biblioteca continua funcionando.
- `BIBLIOTECA_REDE=0` desliga todas as ações remotas do hub.
- A API local de leitura é opt-in, só aceita conexões da própria máquina e
  exige token.
- Capas, letras e metadados de terceiros pertencem a quem os fez; o hub só
  os exibe na sua biblioteca pessoal.
- Nenhuma capa comercial é versionada neste repositório.

O texto completo está em [docs/LEGAL.md](docs/LEGAL.md).

## Licença

O código do hub é [MIT](LICENSE). Emuladores e ferramentas que vêm nos pacotes
mantêm suas próprias licenças, com os textos e as fontes dentro de cada
pacote (`manifesto-runtime.json`, `FONTE.txt`, `COPYING.txt`).
