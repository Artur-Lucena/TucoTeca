# TucoTeca

[![Testes](https://github.com/Artur-Lucena/Projeto-Launcher/actions/workflows/testes.yml/badge.svg)](https://github.com/Artur-Lucena/Projeto-Launcher/actions/workflows/testes.yml)
[![Licença: MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Versão](https://img.shields.io/badge/vers%C3%A3o-1.0.2-informational)](VERSION)

Um hub para a **sua** coleção de jogos, músicas e vídeos — no seu computador,
sem conta, sem nuvem e sem depender de ninguém para abrir a biblioteca.

A ideia é simples: reunir a coleção em um lugar agradável de usar, sem
precisar estar online para abri-la. É um projeto pessoal de Tuco e Isa,
feito para o uso do dia a dia — com os limites documentados, não escondidos.

[Baixar a release privada](https://github.com/Artur-Lucena/Projeto-Launcher/releases/tag/v1.0.2)
· [Como começar](#primeiros-passos) · [Desenvolvimento](docs/CONTRIBUTING.md)

- **A coleção é sua.** Fica em `dados/`, na sua máquina. Nenhum servidor
  próprio, nenhuma telemetria, nenhum login obrigatório.
- **A internet é opcional.** Abrir, jogar, ouvir e ver funcionam sem rede.
  Buscar capas, letras, catálogos ou baixar algo é sempre **você quem pede**.
- **O que é de terceiros é separado do que é seu.** Emuladores e ferramentas
  são programas independentes, agregados como estão, com suas licenças.

## Primeiros passos

### Usar no Windows, sem instalar Python

1. Abra a [release v1.0.2](https://github.com/Artur-Lucena/Projeto-Launcher/releases/tag/v1.0.2).
   É preciso ter acesso ao repositório privado.
2. Escolha **essencial** ou **completo** na tabela abaixo. Baixe também
   `SHA256SUMS.txt` para conferir o arquivo antes de abrir.
3. Extraia o ZIP **inteiro** em uma pasta própria. Não rode de dentro do ZIP.
4. Abra `TucoTeca.bat`. `BibliotecaHub.bat` continua como alias legado.
   A biblioteca começa vazia; importe seus arquivos ou um pacote de coleção.

`Criar-Atalho.bat` cria um novo atalho na Área de Trabalho. Não há instalador
que substitua uma instalação existente. Para conferir o download no PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 .\tucoteca-1.0.2-windows-x64-essencial.zip
```

Compare o resultado com a linha correspondente em `SHA256SUMS.txt`.

### Executar pelos fontes

No Windows, com Python instalado:

```powershell
py -3.14 -m pip install -r codigo/ferramentas/requirements-ui.txt
py -3.14 codigo/frontends/desktop.py
```

Sem PySide6, o hub cai automaticamente para a interface clássica em tkinter.
`--big-picture` abre direto em tela cheia; `--classico` força o modo clássico.

**Linux:** `./BibliotecaHub.sh` em um terminal abre a TUI; precisa de Python 3.10+.
**macOS:** `BibliotecaHubMac.command` abre a interface clássica; é experimental
e precisa de Python com Tk. Não há bundle macOS validado nesta release.

Para experimentar os fontes sem encostar na coleção real:

```powershell
$env:BIBLIOTECA_HOME = Join-Path $env:TEMP "tucoteca-dev"
py -3.14 codigo/frontends/app_win.py --selftest
```

`BIBLIOTECA_HOME` aponta para a **pasta-mãe** de `dados/`, não para o banco.
A trava
`.biblioteca.lock` impede que duas cópias abram a mesma coleção ao mesmo tempo.

## Atualizar sem perder seus dados

1. Feche o Hub e faça uma cópia de segurança da pasta antiga.
2. Extraia a versão nova em **outra pasta**. Não descompacte por cima de `dados/`.
3. Exporte/importe um pacote de coleção pelo Hub, ou copie seu `dados/` para
   a nova pasta. O pacote de coleção não leva jogos nem ROMs.
4. Preserve separadamente saves, mods, perfis de emuladores e arquivos externos.
   Confira os caminhos e a coleção antes de abandonar a versão antiga.

Não apague a instalação anterior até confirmar que está tudo certo. Uma cópia
de segurança de verdade é independente; hardlinks não substituem backup.

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
  sem tratar essa organização como backup.
- Saneia pastas de instalação com confirmação e quarentena, preservando o jogo.

**Coisas pequenas que ajudam**
- Modo tela cheia (F11) navegável pelo teclado.
- Busca global `Ctrl+K`.
- Volume geral do PC no rodapé (Windows).
- Backup da coleção em um clique, exportável para outro computador.
- Perfis separados para Tuco e Isa (favoritos e filtros independentes).
- API local de leitura (desligada por padrão, só loopback, com token).

## O que ele **não** faz

Algumas coisas continuam fora do escopo desta versão:

- **Nada de gamepad.** A navegação em tela cheia é teclado e mouse.
- **Nada de conquistas online, overlay ou integração com a Steam como
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
| Interface principal | PySide6-Essentials 6.10.2 (`codigo/ferramentas/requirements-ui.txt`) |
| YouTube embutido e vídeo interno | `codigo/ferramentas/requirements-extras.txt` (PySide6-Addons, variante completa) |
| Interface clássica | tkinter/Tcl/Tk |
| TUI no Linux | curses (biblioteca padrão do Python) |
| Imagens JPG/WebP | Pillow (opcional; PNG/GIF funcionam sem ele) |
| RAR/7z/ISO | 7-Zip instalado ou no pacote |
| Áudio e vídeo | FFmpeg (conversão) e um player externo como opção |

Os bundles Windows já trazem o runtime e as ferramentas usadas pelo Hub,
inclusive os emuladores. Não é preciso instalar Python separadamente.

## Pacotes prontos

A [release privada **v1.0.2**](https://github.com/Artur-Lucena/Projeto-Launcher/releases/tag/v1.0.2)
reúne fontes, dois bundles Windows x64, notas, licenças, proveniência e hashes:

| Variante | O que tem | Para quem |
|---|---|---|
| **essencial** | Sem Chromium: o YouTube abre no navegador do sistema | Prefere o download menor |
| **completo** | Com QtWebEngine e QtMultimedia: YouTube embutido e vídeo interno | Prefere a mídia dentro do hub |

Os dois incluem Python, Tk, Pillow, PySide6, 7-Zip, FFmpeg, yt-dlp,
QuickJS-NG, qBittorrent, Azahar e DeSmuME. A coleção começa vazia; para
trazer a sua, use **exportar/importar pacote de coleção** dentro do hub.

Os arquivos são `tucoteca-1.0.2-windows-x64-essencial.zip`,
`tucoteca-1.0.2-windows-x64-completo.zip` e `tucoteca-1.0.2-fontes.zip`.
A tag `v1.0.0` foi preservada como registro de preparação, sem release publicada.

## Gerar e verificar uma release

Na máquina Windows de build, com dependências e componentes disponíveis,
comece com um checkout **limpo**. O fluxo completo está em [docs/RELEASES.md](docs/RELEASES.md).

```powershell
$sha = git rev-parse HEAD
py -3.14 codigo/ferramentas/montar_superhub.py --extras essencial --formato zip --revisao $sha
py -3.14 codigo/ferramentas/montar_superhub.py --extras completo --formato zip --revisao $sha
```

O builder monta o runtime, executa provas reais nele (tkinter, Qt, áudio MCI,
Chromium com rede bloqueada na variante completa e qBittorrent) e repete as
provas no pacote extraído. Mídias são sintéticas e os perfis são temporários.
Uma falha impede concluir a verificação; não trate um ZIP sem relatório completo
como uma entrega validada.

Para montar a pasta da release (fontes + bundles + notas + checksums):

```powershell
py -3.14 codigo/ferramentas/preparar_release.py --revisao $sha --saida dist/release/v1.0.2
```

Esse comando exige revisão e versão iguais entre fontes e bundles, confere
os manifestos, veta arquivos pessoais no runtime e gera notas, licenças e
hashes. Recusa sobrescrever uma entrega antiga. **Ele não publica nada**:
no GitHub, primeiro crie um rascunho, confira os anexos e só então publique.

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
.provas/               relatórios e caches de ferramentas (fora do Git)
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
é o [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Privacidade e legal

- O hub é um **gerenciador local**: organiza o que você já tem. Ele não
  distribui, não hospedeia e não incentiva pirataria.
- Toda ação de rede (buscar capa, consultar catálogo, baixar letra) é disparada
  por você, com tempo limite e cache local. Se a rede falhar, você recebe um
  aviso e a biblioteca continua funcionando.
- `BIBLIOTECA_REDE=0` bloqueia consultas/downloads remotos do Hub. Não é um
  firewall: navegador, qBittorrent e outros programas externos podem continuar
  usando a rede. Sites acessados também têm seus próprios termos e políticas.
- A API local de leitura é opt-in, só aceita conexões da própria máquina e
  exige token.
- Capas, letras e metadados de terceiros pertencem a quem os fez; o hub só
  os exibe na sua biblioteca pessoal.
- A árvore atual e os pacotes de fontes não incluem capas comerciais. Dez
  capas antigas permanecem no histórico preservado, como explica a documentação.

O texto completo está em [docs/LEGAL.md](docs/LEGAL.md).

## Licença

O código do hub é [MIT](LICENSE). Emuladores e ferramentas que vêm nos pacotes
mantêm suas próprias licenças. Os **textos das licenças e links para os fontes**
acompanham os bundles; o ZIP de fontes da TucoTeca não inclui o código-fonte
dessas ferramentas. Veja `LICENCAS.md` na release e `manifesto-runtime.json`,
`FONTE.txt` e os arquivos de licença dentro do runtime.

## Se algo der errado

Confira se o ZIP foi extraído inteiro e abra `Debug-Console.bat` para ver a
mensagem de erro. Para desenvolvimento, use `codigo/ferramentas/diagnosticar.py`.
Ao relatar um problema, informe a versão, a variante, seu sistema e os passos
para reproduzir — não anexe seu banco, saves ou credenciais. Use os modelos
de issue deste repositório; para informações sensíveis, consulte [SECURITY.md](docs/SECURITY.md).
