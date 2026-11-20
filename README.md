# TucoTeca

Hub local para sua coleção de jogos, músicas e vídeos. Sem conta, sem nuvem.

## Instalação

Baixe o arquivo do seu sistema na [última release](https://github.com/Artur-Lucena/TucoTeca/releases/latest):

- **Windows 10/11:** `TucoTeca-Setup-<versão>-x64.exe` — abra e pronto: ele
  instala para o seu usuário e abre o TucoTeca. Se o Windows avisar que
  protegeu o computador: *Mais informações → Executar assim mesmo*.
- **macOS 13 ou mais novo:** `…-mac-arm64.dmg` (Apple Silicon) ou
  `…-mac-x64.dmg` (Intel) — abra e arraste o TucoTeca para *Aplicativos*. Na
  primeira vez, botão direito no app → *Abrir* (no macOS 15+: *Ajustes do
  Sistema → Privacidade e Segurança → Abrir Mesmo Assim*).
- **Linux (x64):** `…-linux-x64.AppImage` — marque como executável
  (`chmod +x`) e abra. Se o Ubuntu 24.04+ não abrir, rode com `--no-sandbox`.

A coleção fica em *Documentos/TucoTeca* e continua lá ao atualizar ou
desinstalar. Para atualizar: Configurações → *Verificar atualização* (ou
instale a versão nova por cima). FFmpeg, yt-dlp e 7-Zip são
opcionais; no Mac, `brew install ffmpeg yt-dlp sevenzip`.

## Executar pelos fontes (desenvolvimento)
```
npm --prefix codigo/frontends/electron ci
npm --prefix codigo/frontends/electron run build
TucoTeca.bat                              # Windows
python3 codigo/ferramentas/abrir_hub.py   # macOS/Linux
```
Requer Python 3.14 (`py -3.14` no Windows; no Mac/Linux, o `python3` que
abre o `abrir_hub.py` é o mesmo que a ponte usa) e Node 24.

## Documentação
- [Arquitetura](docs/ARQUITETURA.md) — mapa de pastas, módulos, dados e fluxos.
- [Desktop Electron](docs/DESKTOP_ELECTRON.md) — telas, ponte, controle e segurança.
- [Integrações](docs/INTEGRACOES.md) — como acrescentar um provedor.
- [Colaboração](docs/CONTRIBUTING.md), [Releases](docs/RELEASES.md),
  [Roadmap](docs/ROADMAP.md), [Segurança](docs/SECURITY.md) e
  [Aviso legal](docs/LEGAL.md).
- Mudanças por versão: [CHANGELOG](docs/CHANGELOG.md).

## Licença
MIT. Veja LICENSE.
