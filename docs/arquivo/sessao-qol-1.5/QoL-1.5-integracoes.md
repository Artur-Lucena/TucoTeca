# QoL 1.5.2 — Pesquisa integrações open source (10/10/2026)

Pesquisa revisada com fontes primárias em 10/10/2026. O domínio do Hub usa
stdlib; o desktop já usa PySide6/Qt. Integrações propostas devem funcionar
com a biblioteca local, com operações remotas em worker e por ação do usuário.
As variáveis `BIBLIOTECA_*` citadas abaixo são propostas, ainda não implementadas.

Software aberto, dados abertos e serviço com API são coisas diferentes.
Ferramentas GPL podem ser distribuídas com suas próprias condições; chamar
um programa independente por CLI não torna automaticamente o Hub GPL.
Para este projeto, adaptadores próprios e sidecars são o encaixe mais simples.

## Recomendadas (curto prazo, baixo risco)

### 1. SDL GameControllerDB — mapas de controle (zlib)
- O quê: `https://github.com/mdqinc/SDL_GameControllerDB` — `gamecontrollerdb.txt` comunitário p/ SDL2/SDL3.
- Por quê: Hub já tem `controles.py` + mapas Xbox/PS/Switch. O banco comunitário amplia a cobertura de GUIDs e plataformas.
- Como: `BIBLIOTECA_GAMECONTROLLERDB` apontando p/ txt local + botão "Atualizar mapas" (sob demanda, cache em `dados/`). Molde `atualizar_emu`.
- Esforço: médio. É necessário carregar os mapas no backend SDL e validar o controle real. Baixar um txt sozinho não adiciona navegação por gamepad ao Qt Quick. Licença zlib confirmada no arquivo LICENSE oficial.

### 2. MusicBrainz + Cover Art Archive — capas/tags de música sem chave (aberto)
- O quê: `https://musicbrainz.org/ws/2/` (consultas públicas sem chave, exige User-Agent e no máximo 1 chamada/s) + `https://coverartarchive.org` (API de capas por MBID).
- Por quê: hoje capa de música é iTunes (proprietário). MusicBrainz é o fallback aberto natural p/ `baixar_capa_album` quando iTunes volta vazio.
- Como: `musica_capa_mb()` molde `_capa_steam`/`capa_album_url`; tenta MusicBrainz→CAA antes de marcar `sem capa`. Tudo mockado em `test_musica.py`.
- Esforço: médio. Casar artista/álbum, cachear MBIDs e tratar capa ausente/503. Serviço gratuito para uso não comercial conforme a documentação. Capas não herdam automaticamente uma licença de software aberto.

### 3. SteamGridDB — arte alternativa p/ jogo fora do Steam (key gratuita)
- O quê: serviço com API v2 e chave pessoal; wrapper aberto `node-steamgriddb` e ferramentas do ecossistema `SGDBoop`/`Steam ROM Manager`. A existência de clientes abertos não implica que o servidor ou suas artes sejam open source.
- Por quê: capa Steam falha em jogo não-Steam/renomeado (caso `Balls`→`BALL x PIT`, item 67). SGDB cobre non-Steam com `searchGame` + `getGridsBySteamAppId`.
- Como: `BIBLIOTECA_STEAMGRIDDB_KEY` opcional; botão "Buscar arte alternativa" no diálogo; manter a seleção da arte em cache local.
- Risco: médio-baixo (key pessoal, rate limit).

### 4. HowLongToBeat — tempo Main/Extra/100% no detalhe (wrappers MIT/WTFPL, sem API oficial)
- O quê: serviço proprietário com wrappers comunitários. Não foi confirmada uma API pública oficial estável nesta revisão.
- Por quê: estimar o tempo de conclusão pode ajudar na escolha do próximo jogo.
- Como: campo virtual (sem schema) `hltb_main/hltb_extra/hltb_100` com cache em `dados/cache-hltb/`; busca só no drawer ("Ver tempo estimado"); falha vira "indisponível".
- Prioridade baixa entre as opções desta pesquisa: depende de scraping/endpoints internos e manutenção. Um link de pesquisa é um primeiro passo mais simples.

### 5. PCGamingWiki — fixes/mods por AppID (serviço comunitário)
- O quê: `https://www.pcgamingwiki.com/wiki/PCGamingWiki:API` (`action=cargoquery` em `Infobox_game`) + redirect `github.com/PCGamingWiki/api` (appid.php/gog.php).
- Por quê: "como arrumo fullscreen/stutter neste jogo?" direto do drawer, sem Google. Playnite já tem provider disso (`Jeshibu/PlayniteExtensions`).
- Como: botão "Correções ↗" no detalhe (abre página via `abrir_url`); opcional: `cargoquery` p/ `Cover_URL/Developers/Released` como 2º fallback de metadados. Rate 1 req/2s + cache.
- Encaixe inicial: link por AppID, sem copiar código do servidor. A API de metadados GitHub retornou `license: null` para `PCGamingWiki/api`; a afirmação anterior de licença MIT foi removida por falta de confirmação.

## Segunda fase (bom, mas com conta/cache)

### 6. RetroAchievements — consulta de conquistas (compatibilidade a confirmar)
- O quê: API web e bibliotecas de integração abertas; consulta de progresso de conta é diferente de desbloquear conquistas durante a emulação.
- Verificação: a lista oficial consultada inclui DeSmuME como **core libretro**, não o DeSmuME standalone deste Hub. Não lista 3DS/Azahar. O documento `RETROACHIEVEMENTS_IMPLEMENTATION.md` encontrado anteriormente era de um fork, não prova suporte no Azahar instalado.
- Encaixe: mostrar progresso existente da conta, ou acrescentar futuramente um emulador/core compatível com NDS. Não prometer conquistas 3DS no runtime atual.

### 7. ProtonDB — "roda no Linux?" (crowdsourced, sem API oficial estável)
- O quê: `protondb.com` (tiers platinum→borked) + mirrors abertos (`trsnaqe/protondb-api`, `zwsyscall/protonDB` script Python).
- Por quê: Tuco é dual-boot Win/Linux (item 7 do TucoTeca.md). Tier no detalhe responde "jogo no Linux ou só Win?".
- Como: cache local por appid (`dados/cache-protondb/`), refresh manual; badge "Linux: gold · 2000 relatos".
- Esforço: médio. Preferir inicialmente um link por AppID; uma classificação de Proton não garante que o mesmo jogo rode no prefixo Wine configurado pelo Hub.

## Referências de UX (não embutir código)

### 8. Playnite (MIT, C#) — o que copiar em ideia, não em código
- Playnite: biblioteca unificada, playtime, fullscreen com controle, temas e add-ons. Referência de UX; stack desktop diferente da interface Qt do Hub.
- Levar p/ QoL 1.5.4: playtime já existe; faltam fullscreen navegável por controle e import de launchers (Steam/Epic/GOG) como leitura local.

### 9. Lutris (GPL-3.0, Python) — scripts YAML de instalação
- `lutris/lutris`: installers declarativos YAML, `pga.db` SQLite e CLI. Pode servir como runner externo no Linux; avaliar os comandos e formatos realmente suportados na versão instalada.

### 10. Heroic + legendary/gogdl/Nile (GPLv3) — Epic/GOG/Amazon sem cliente
- O README oficial do Heroic documenta Legendary (Epic), gogdl (GOG) e Nile (Amazon).
- Encaixe: importar jogos já instalados e lançar pelo runner externo. Autenticação e downloads ficam no cliente escolhido. Conferir cada sidecar e sua licença separadamente.

### 11. pypresence — Discord Rich Presence (MIT, Python, pip)
- `qwertyquerty/pypresence`: cliente Python aberto para IPC/Rich Presence. Discord é um serviço proprietário. Integração opcional com App ID e o cliente desktop em execução.
- Como: `BIBLIOTECA_DISCORD_RPC=0` default; se lib presente + Discord aberto, atualiza no `jogar`, limpa no fim. Nunca trava play.

### 12. Ludusavi — backups de saves de jogos PC (MIT, prioridade alta)

- [Projeto oficial](https://github.com/mtkennerly/ludusavi) e [licença MIT](https://github.com/mtkennerly/ludusavi/blob/master/LICENSE) conferidos.
- Funciona em Windows/Linux/macOS; identifica arquivos de save e entradas de registro, incluindo Proton e vários launchers.
- A CLI oferece `--api` com JSON e comandos de preview. O Hub já centraliza alguns saves, mas backup do catálogo SQLite não equivale a backup do progresso de todos os jogos.
- Encaixe: sidecar opcional, primeiro "Pré-visualizar saves" e "Backup deste jogo". Mostrar os arquivos reconhecidos antes de integrar a restauração. O manifesto de jogos possui condições próprias, distintas da licença do executável.
- [Contrato CLI oficial](https://github.com/mtkennerly/ludusavi/blob/master/docs/help/command-line.md).

## Ordem sugerida de implementação (revisada)

1. Ludusavi: preview e backup de saves por jogo — alto benefício prático.
2. MusicBrainz/CAA: melhorar identificação de álbuns e fallback de capas.
3. SDL GameControllerDB + backend de entrada: preparar navegação por controle.
4. SteamGridDB: galeria de pôsteres/arte por chave opcional.
5. PCGamingWiki/ProtonDB: atalhos de suporte por AppID.
6. Heroic/Legendary/Lutris: biblioteca de jogos instalados nos clientes.
7. Rich Presence e RetroAchievements: opcionais; HLTB em prioridade menor.

## Fontes primárias conferidas nesta continuação

- [SDL GameControllerDB: uso](https://github.com/mdqinc/SDL_GameControllerDB) e [licença](https://github.com/mdqinc/SDL_GameControllerDB/blob/master/LICENSE).
- [MusicBrainz API: autenticação e limite](https://musicbrainz.org/doc/MusicBrainz_API).
- [Cover Art Archive API: MBIDs e miniaturas](https://musicbrainz.org/doc/Cover_Art_Archive/API).
- [SteamGridDB: cliente oficial e exemplos de API](https://github.com/SteamGridDB/node-steamgriddb).
- [RetroAchievements: emuladores/cores suportados](https://docs.retroachievements.org/general/emulator-support-and-issues.html).
- [PCGamingWiki: contrato de redirecionamento](https://github.com/PCGamingWiki/api) e [metadados de licença](https://api.github.com/repos/PCGamingWiki/api).
- [Heroic: backends e recursos documentados](https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher).
- [pypresence: instalação e requisitos](https://github.com/qwertyquerty/pypresence).
- [Ludusavi: recursos, licença e CLI](https://github.com/mtkennerly/ludusavi).
