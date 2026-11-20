# Roadmap — TucoTeca

Estado: **2.3** — Linux (AppImage), verificar atualização no app, downloads
unificados, notificações que ficam e biblioteca por gênero. O app desktop é a
única interface, no Windows, no macOS (Apple Silicon e Intel) e no Linux. A
2.2 trouxe baixar dentro do app pelas fontes de download do usuário (formato
do Hydra). A 2.1 trouxe descobrir jogos por gênero, "Onde
baixar", galeria de capas, YouTube ↔ Spotify (clipe ou MP3 com os dados da
música), limpezas e testes rápidos e localizados. Antes: 2.0.x (sem TUI, porte
para o macOS, instalador de um clique), 1.4.x (hub em três pilares), 1.3.x
(primeiro instalador Electron), 1.0.x e 1.2.0.

## 2.0 (entregue)

1. ~~TUI curses e fachada `bib_core` removidas; código que só a TUI usava fora.~~
2. ~~App desktop no macOS: `.dmg` por arquitetura com Python embutido,
   menu e atalhos do Mac (⌘), caminhos sem diferença de caixa/Unicode,
   Steam/Hydra/DeSmuME nas pastas do Mac, jogos `.app`.~~
3. ~~Versão do esquema no banco: um app mais velho recusa a coleção que um
   mais novo já migrou (a mesma coleção pode ir do Windows ao Mac).~~
4. ~~CI público: suíte em Windows, Linux e macOS; `.dmg` e instalador gerados
   e testados (selftest do app empacotado) a cada push.~~

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

Provado ao vivo em 18/11/2026 (`provar_runtime.py rede --provedores
--catalogos`, coleção temporária): Steam (detalhes, nome canônico e preço em
BRL), Cinemeta (busca, ficha e catálogo), SteamRIP e FitGirl (busca), LRCLIB,
LibRetro e SponsorBlock.

Ainda só por simulação, respostas falsas ou em ambiente de desenvolvimento:

- SteamGridDB e RetroAchievements de verdade (exigem a chave do usuário).
- Reprodução real de vídeo no player interno (retomada e legendas na tela).
- Controle físico (mapeamento padrão Xbox/PlayStation),
  UAC real ("Abrir como administrador"), equalização com FFmpeg instalado e
  atualização real de emulador.
- Instalar e abrir o instalador numa máquina Windows limpa.
- macOS num Mac de verdade: abrir a `.dmg` baixada (Gatekeeper com
  quarentena), controle, emuladores (Azahar/DeSmuME `.app`), vídeo e música.
  O CI prova suíte, build e selftest do app nas duas arquiteturas.

## 2.2 (entregue)

- Fontes de download no formato do Hydra, adicionadas pelo usuário (o app não traz nenhuma);
  "Baixar" na loja e nos Desejos, torrent pelo qBittorrent integrado e link direto pelo app.

## 2.1 (entregue)

- Descobrir jogos por gênero, "Onde baixar" na loja e galeria de capas.
- YouTube ↔ Spotify: escolher clipe (MP4) ou música (MP3 com os dados do Spotify).
- Limpar notificações, fila de músicas baixadas e torrents concluídos.
- HowLongToBeat removido (o site passou a exigir token).

## Depois da 2.0

- Validadores restantes da ponte para `ponte_params` e `estado/formato.ts` nos
  cartões antigos.
- "Adicionar à coleção" pelo menu de contexto dos cartões (hoje na página do jogo).
- Assinatura de código do instalador e notarização no macOS (hoje decisão:
  sem; exigem certificados pagos).
- Pacote para Linux (AppImage); hoje o Linux roda pelos fontes.
- Atualização automática (hoje desligada: `publish: null`).
