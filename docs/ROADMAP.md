# Roadmap — TucoTeca

Estado: **1.3.0 publicada** (14/11/2026) — primeira entrega do desktop
Electron como instalador Windows. Antes: 1.0.1, 1.0.2, 1.0.3 (Mac) e 1.2.0
(fatias Electron F0–F6).

## 1.3.0 (entregue)

1. ~~Empacotamento: instalador NSIS com Python embutido e preparador de release.~~
2. ~~Coerência: versões unificadas, docs/CI/lançadores sem Qt.~~
3. ~~Paridade com o antigo Qt (mapa em `DESKTOP_ELECTRON.md`).~~
4. ~~Acabamento: textos/acentos, layout, correções da auditoria e publicação.~~

## Pendências de validação da 1.3.0

Provadas só por simulação ou em ambiente de desenvolvimento:

- Instalar e abrir o instalador numa máquina Windows limpa.
- Controle físico (Xbox 360 XInput), UAC real ("Abrir como administrador"),
  equalização com FFmpeg instalado e atualização real de emulador.

## Depois da 1.3.0

- Assinatura de código do instalador (hoje decisão: sem assinatura).
- Credenciais vivas (Spotify, Steam, SteamGridDB).
- Desktop Electron para macOS/Linux (hoje só TUI).
- Atualização automática (hoje desligada: `publish: null`).
