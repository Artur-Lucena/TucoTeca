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

### Linux e macOS (TUI no terminal)
1. Tenha Python 3.10+.
2. Baixe os fontes (`tucoteca-<versão>-fontes.zip`) e extraia.
3. Execute `./BibliotecaHub.sh` (Linux) ou `BibliotecaHubMac.command` (macOS).

## Executar pelos fontes (desenvolvimento)
```
npm --prefix codigo/frontends/electron ci
npm --prefix codigo/frontends/electron run build
TucoTeca.bat
```
Requer Python 3.14 (`py -3.14`) e Node 24.

## Documentação
- [Arquitetura](docs/ARQUITETURA.md) — mapa de pastas, módulos, dados e fluxos.
- [Desktop Electron](docs/DESKTOP_ELECTRON.md) — telas, ponte, controle e segurança.
- [Integrações](docs/INTEGRACOES.md) — como acrescentar um provedor.
- [Colaboração](docs/CONTRIBUTING.md), [Releases](docs/RELEASES.md),
  [Roadmap](docs/ROADMAP.md), [Segurança](docs/SECURITY.md) e
  [Aviso legal](docs/LEGAL.md).
- Mudanças por versão: [CHANGELOG.md](CHANGELOG.md).

## Licença
MIT. Veja LICENSE.
