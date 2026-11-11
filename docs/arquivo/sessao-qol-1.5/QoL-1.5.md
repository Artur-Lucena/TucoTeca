# QoL 1.5 — acompanhamento da sessão (10/10/2026)

Continuidade de QoL 1.0 (`5565750` — Desktop Qt Quick + freeze tkinter).
Cada tópico abaixo é um decimal de QoL 1.5.

- [x] 1.5.1 — Git do projeto acessível por `projeto/` + `Git-Projeto.bat` ao vivo
- [x] 1.5.2 — Pesquisa integrações open source (`QoL-1.5-integracoes.md`)
- [x] 1.5.3 — Textos pequenos no Hub Qt (Theme/Main/PosterCard, verificado abaixo)
- [x] 1.5.4 — Varredura QoL (`QoL-1.5-varredura.md`, com estado das entregas e próximos ajustes)
- [x] 1.5.5 — Saúde completa e filtro de pendências
- [x] 1.5.6 — Busca global, contagem contextual, limpar filtros e seleção
- [x] 1.5.7 — Avisos em fila, com fechamento individual
- [x] 1.5.8 — Estado do backup e layout compacto legível
- [x] 1.5.9 — Registrar horas e encerrar sessões pendentes corretamente
- [x] 1.5.10 — Conquistas sem login (Comunidade pública + percentuais)
- [x] 1.5.11 — Spotify funcional (busca pública, colar código, erros claros)
- [x] 1.5.12 — Adicionar integração personalizada (botão + persistência)
- [x] 1.5.13 — Piratas como destino padrão de todos os downloads

Projeto canônico: `D:\Tuco-Compartilhado\Jogos\biblioteca\`
Workspace sessão: `D:\Tuco-Compartilhado\IA\TucoTeca\`
`projeto/` é uma junction NTFS para o checkout canônico e inclui o acesso ao
`.git` real. Abrir `projeto/` no editor permite acompanhar o repositório.

## 1.5.1 — Git na pasta raiz (10/10/2026)

A primeira passagem criou apenas `sessao/git-projeto.md`, um snapshot.
Na continuação, o acesso ativo foi concluído:

- `projeto/` — ligação para o checkout real, conferida com `rev-parse`.
- `Git-Projeto.bat` — painel que atualiza status/diff/últimos commits a cada 3s.
- `Git-Projeto.bat --uma-vez` — imprime uma vez (verificado).
- Comandos na raiz desta sessão:

```powershell
git -C projeto status --short --branch
git -C projeto diff
git -C projeto log --oneline -n 20 --decorate
```

Estado no início da sessão QoL 1.5:

- branch `main`, `ahead 2` de `origin/main` (não publicado):
  - `1a8b089` gitattributes: qml/qmldir em LF
  - `5565750` Desktop Qt Quick + QoL 1.0 + freeze tkinter (272/272)
- `origin/main` = `52951c3`
- working tree: limpo (nada a commitar)
- remote: `https://github.com/Artur-Lucena/Projeto-Launcher.git`

Regra da sessão: todo fim de tópico atualiza `sessao/git-projeto.md`
com `log -5` + `status --short`. Sem commit sem pedido (regra item 22 do `TucoTeca.md`).

## 1.5.2 — Integrações open source (10/10/2026)

Pesquisa revisada em `sessao/QoL-1.5-integracoes.md`, com links para as fontes
oficiais. Prioridades: Ludusavi (saves), MusicBrainz/CAA (álbuns/capas),
SDL GameControllerDB + backend de entrada, SteamGridDB e links de suporte.
RetroAchievements não foi confirmado para o Azahar/DeSmuME standalone atual;
o arquivo de implementação citado inicialmente era de um fork. PCGamingWiki
não teve licença MIT confirmada. HLTB ficou em prioridade menor.

## 1.5.3 — Textos pequenos (10/10/2026, sem commit)

`Theme.subtitle` 12→14; `PosterCard` badge 10→12 (altura 25→27), PRONTO 9→11,
status 11→13; `Main.qml`: subtítulos/herói/coleção/saúde/descrições 12→14,
rótulos 11→13, kickers/badges 9–10→12–13, atalho F11 12→13. Eyebrows com
letterSpacing ficam no mínimo 11–12 de propósito.
Verificado: `test_qt` 11/11 + `test_visual` 10/10; auditoria isolada 6 seções,
0 QML crítico, 25 jogos/51 músicas/4 desejos, saúde 25/25; capturas
`aud-jogos/integracoes/compacto` conferidas (badge SOB DEMANDA legível,
compacto 960×640 íntegro). Arquivos sujos (não commitar sem pedido):
`qml/Main.qml`, `qml/PosterCard.qml`, `qml/Theme.qml` (34+/34−, só apresentação).

## 1.5.4 — Varredura (10/10/2026, só sugestões)

Backlog em `sessao/QoL-1.5-varredura.md`: 5 quick wins (contagem com filtro,
"+N outros" na saúde, chip backup ≥7d, fila de toasts, +1h no drawer),
5 médios (preço em Desejos, DnD de pasta, duração em Músicas, restante em
Downloads, escala de texto), 3 grandes (gamepad no Big Picture, lixeira com
desfazer, volume no Linux).

Na continuação, os ajustes imediatos deram origem às entregas seguintes;
o documento de varredura foi atualizado para refletir o que está pronto.

## 1.5.5 — Saúde completa

`saude_colecao` agora examina todos os jogos, mesmo que o resumo mostre apenas
oito problemas. O Início mostra cinco e informa `+N outros`. O botão
"Ver pendências" e o filtro na biblioteca incluem todos os jogos afetados.
Resultados de uma recarga antiga não substituem o diagnóstico novo.

## 1.5.6 — Busca e filtros

Resumo `N de total · filtro · busca` e botão Limpar filtros. A paleta limpa
filtros que escondiam o resultado e seleciona o jogo/desejo/download correto.
Ctrl+F no Início/Integrações abre a busca global; ordenação acompanha o estado
do bridge. Corrigida a marcação da primeira faixa na fila (índice zero).

## 1.5.7 — Avisos em fila

Mensagens sucessivas não se sobrescrevem: FIFO com texto/severidade preservados,
7 segundos por aviso e botão × para fechar individualmente.

## 1.5.8 — Informações e compacto

Estado e idade do backup separados; âmbar para ausência ou idade ≥7 dias.
Textos auxiliares/botões ampliados e tokens no tema. Cabeçalho sem corte em
960/1200/1440px; a primeira linha de cards mantém status/horas visíveis em
960×640. Selftest Qt informa os 25 jogos do snapshot, em vez da quantidade
de itens da tela Início.

## 1.5.9 — Registro de horas e sessões

Drawer oferece Registrar horas, com quantidade explícita e vírgula/ponto decimal.
Sistema substitui +1h por Registrar: usa o marcador da sessão, faz backup do
banco e do marcador, soma no banco do serviço e encerra a pendência. Nova
tentativa para marcador já encerrado não soma as horas novamente.

## 1.5.10 — Conquistas sem login (11/10)

SteamDB bloqueia bots (403). Fonte viável: Comunidade Steam pública
(título/descrição/ícone/% sem chave) + percentuais globais (nome interno sem
chave), cruzados pelo percentual. Empate de % = item parcial honesto
(`sem_vinculo`), nunca adivinhação. Chave segue opcional p/ catálogo completo.
Prova viva: Stardew 413150, 49 linhas em PT-BR, 49/49 vinculados.
Desbloqueios continuam calculados só do save local, offline.

## 1.5.11 — Spotify funcional (11/10)

Client ID agora aceita 32 alnum (era só hex). Client Secret opcional libera
busca pública (faixas/álbuns/playlists públicas) sem login; conta só p/
playlists e curtidas. Colar código manual quando o loopback falha; erros
orientam (redirect não registrado, secret ausente, porta ocupada). Áudio
continua vindo do downloader local, nunca stream.

## 1.5.12 — Adicionar integração (11/10)

Botão + Adicionar nas Integrações com diálogo (chave/nome/descrição/tipo/URL,
`{q}` p/ busca). Atalho https persistido em `dados/integracoes-usuario.json`;
cartão próprio com selo SUA + botão Remover. Padrões protegidos contra remoção
e colisão; URLs só https; sem plugins arbitrários (só abre página).

## 1.5.13 — Piratas padrão (11/10, caso Hell Clock)

Causa: magnets iam ao cliente torrent do SO (pasta dele), não ao perfil do
Hub. Agora: `qbit_adicionar` via API do Hub com savepath Piratas/ + categoria
tucoteca (Qt com botão Baixar no Hub; clássico e TUI idem); perfil antigo migra
o DefaultSavePath; import clássico + botão Organizar movem o que caiu fora
(com aviso de reaponte no cliente). SteamRip direto já caía em Piratas.

## Verificação final da continuação

- Suíte: **295 PASS, 6 SKIP, 0 FAIL (301 casos)**.
- `py_compile` e `git diff --check` OK (`repacks.py` segue CRLF; normaliza no commit).
- Seis seções em 1440×920 e 960×640; capturas de drawer, horas, Configurações
  e Integrações (+ Adicionar); nenhum erro QML crítico. Selftest: **26 jogos**.
- Banco original intacto, conferido por SHA-256; testes de escrita em sandbox.
- Prova viva sem chave: Stardew 49/49; erros claros sem credencial/cliente.
- Relatórios: `validacao/qol-1.5-testes.json`, `qol-1.5-qt.json`, `qol-1.5-visual.json`.
- Documento versionável no projeto: `projeto/docs/QOL_1_5.md`.
- Alterações locais; HEAD continua `1a8b089`, `main` ahead 2 de `origin/main`.
