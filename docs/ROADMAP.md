# Roadmap — TucoTeca

Estado: **1.3.0 em preparação** — primeira entrega do desktop Electron como
instalador Windows. Publicadas antes: 1.0.1, 1.0.2 e 1.0.3 (Mac); a tag
`v1.2.0` marca as fatias Electron F0–F6.

## Até a 1.3.0

1. ~~Empacotamento: instalador NSIS com Python embutido e preparador de release.~~
2. ~~Coerência: versões unificadas, docs/CI/lançadores sem Qt.~~
3. ~~Paridade com o antigo Qt (mapa em `DESKTOP_ELECTRON.md`).~~
4. Acabamento: revisão de textos/acentos e layout, prova do instalador numa
   máquina limpa, congelar, gerar anexos e publicar.

## Depois da 1.3.0

- Assinatura de código do instalador (hoje decisão: sem assinatura).
- Prova física do controle (Xbox 360 XInput) e credenciais vivas (Spotify,
  Steam, SteamGridDB).
- Desktop Electron para macOS/Linux (hoje só TUI).
- Atualização automática (hoje desligada: `publish: null`).
