# TucoTeca

Hub local para sua coleção de jogos, músicas e vídeos. Sem conta, sem nuvem.

## Instalação

### Windows 10/11 (64 bits)
1. Baixe `TucoTeca-Setup-<versão>-x64.exe` na release mais recente em
   https://github.com/Artur-Lucena/TucoTeca/releases (confira o SHA-256 em
   `SHA256SUMS.txt`).
2. Execute o instalador (instala só para o seu usuário, sem admin). O
   instalador não é assinado: se o SmartScreen avisar, clique em
   "Mais informações" → "Executar assim mesmo".
3. Abra o TucoTeca pelo Menu Iniciar ou pela Área de Trabalho.

A coleção fica em `Documentos\TucoTeca` (ou na pasta de `BIBLIOTECA_HOME`)
e não é apagada ao atualizar ou desinstalar.

### macOS 13 Ventura ou mais novo (Apple Silicon ou Intel)
1. Baixe a imagem do seu Mac na mesma página: `TucoTeca-<versão>-mac-arm64.dmg`
   (M1, M2, M3…) ou `TucoTeca-<versão>-mac-x64.dmg` (Intel).
2. Abra a `.dmg` e arraste o TucoTeca para **Aplicativos**.
3. Na primeira vez, clique com o botão direito no app → **Abrir** → **Abrir**
   (o app não é notarizado pela Apple). Se o macOS disser que ele "está
   danificado": `xattr -dr com.apple.quarantine /Applications/TucoTeca.app`.

A coleção fica em `Documentos/TucoTeca`. FFmpeg, yt-dlp e 7-Zip (opcionais)
vêm do Homebrew: `brew install ffmpeg yt-dlp sevenzip`.

### Linux
Sem instalador: rode pelos fontes (abaixo), com `python3` 3.10+ no PATH.

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
