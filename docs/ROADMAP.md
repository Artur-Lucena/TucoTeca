# Roadmap — TucoTeca

Estado: **1.4.7 publicada** (17/11/2026) — revisão geral: código repetido
fundido, módulos sem uso fora, Vídeos no player comum e raiz do projeto com 8
arquivos. Antes, a 1.4.6 reagrupou a interface por seção. A 1.4.5 trouxe
o hub em três pilares: Jogos à la
Hydra (navegação nova, biblioteca lateral, página do jogo com provedores,
coleções, catálogo da loja Steam, importação de lojas instaladas), Filmes e
Séries à la Stremio com os arquivos do usuário e o catálogo Cinemeta, e
Músicas; navegação por controle e Big Picture. Antes: 1.3.1 (revisão da 1.3.0),
1.3.0 (primeiro instalador Electron), 1.0.x e 1.2.0.

## 1.4 (entregue)

1. ~~1.4.0 — correções e podas (capas, regras de conquista, CSS por área, formatação).~~
2. ~~1.4.1 — casca: rotas por hash, cabeçalho, seis seções, biblioteca lateral, carga leve.~~
3. ~~1.4.2 — página do jogo e provedores (Steam, SteamGridDB, RetroAchievements, HowLongToBeat).~~
4. ~~1.4.3 — coleções, catálogo Steam, desejos em Jogos, lojas instaladas.~~
5. ~~1.4.4 — Filmes e Séries (pastas, Cinemeta, player, continuar, lista, calendário).~~
6. ~~1.4.5 — controle (foco espacial, LB/RB, Start, B) e Big Picture; docs.~~
7. ~~1.4.6 — arrumação: renderer por seção, poda de arquivos antigos.~~
8. ~~1.4.7 — revisão geral: podas, fusões e raiz enxuta.~~

## Pendências de validação

Provadas só por simulação, respostas falsas ou em ambiente de desenvolvimento:

- Provedores e catálogos de verdade: Steam, SteamGridDB, RetroAchievements,
  HowLongToBeat (API não oficial) e Cinemeta.
- Reprodução real de vídeo no player interno (retomada e legendas na tela).
- Controle físico (mapeamento padrão Xbox/PlayStation),
  UAC real ("Abrir como administrador"), equalização com FFmpeg instalado e
  atualização real de emulador.
- Instalar e abrir o instalador numa máquina Windows limpa.

## Depois da 1.4

- Validadores restantes da ponte para `ponte_params` e `estado/formato.ts` nos
  cartões antigos.
- "Adicionar à coleção" pelo menu de contexto dos cartões (hoje na página do jogo).
- Assinatura de código do instalador (hoje decisão: sem assinatura).
- Desktop Electron para macOS/Linux (hoje só TUI).
- Atualização automática (hoje desligada: `publish: null`).
