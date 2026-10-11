# QoL 1.5

Continuação do desktop Qt/QoL 1.0. Sessão de 10/10/2026; cada tópico tem
seu decimal. A coleção usada na validação visual foi copiada para uma casa
temporária: 25 jogos, 51 músicas e 4 desejos.

## Entregas

| Tópico | Resultado |
|---|---|
| **1.5.1 — Git acessível** | Na raiz da sessão, `projeto/` liga ao checkout real, incluindo `.git`. `Git-Projeto.bat` mostra branch, alterações e commits a cada 3s. |
| **1.5.2 — Pesquisa de integrações** | Fontes oficiais conferidas; prioridades e limitações abaixo. |
| **1.5.3 — Legibilidade** | Informações secundárias de 13–14px, badges de 12px e títulos de cards de 15px. Tokens no tema. |
| **1.5.4 — Varredura** | Achados e sugestões priorizados; os ajustes imediatos geraram os tópicos seguintes. |
| **1.5.5 — Saúde real da coleção** | Diagnóstico de todos os jogos; resumo limitado sem distorcer os totais. `+N outros` e filtro de pendências. Resultado antigo de worker não substitui a saúde da recarga mais recente. |
| **1.5.6 — Busca e filtros** | `N de total · filtro · busca`, Limpar filtros, seleção correta pela paleta em jogos/desejos/downloads, ordenação sincronizada e Ctrl+F funcionando nas telas iniciais. Primeira faixa marcada corretamente na fila de áudio. |
| **1.5.7 — Avisos em fila** | FIFO: cada aviso mantém texto e severidade, permanece 7s e pode ser fechado pelo botão ×. |
| **1.5.8 — Informações e layout** | Idade/estado do backup separados; cor âmbar para backup ausente ou com ≥7 dias. Cabeçalho cabe nas larguras 960/1200/1440; cards compactos preservam status/horas. Selftest imprime o total de jogos da coleção. |
| **1.5.9 — Horas e sessões** | Registrar horas no drawer; decimal com vírgula ou ponto. Sessão pendente usa o banco correto, faz backup do banco e do marcador, soma as horas e encerra a pendência. Tentativa repetida não soma novamente. |
| **1.5.10 — Conquistas sem login** | Catálogo público de nomes/descrições/ícones salvo separadamente dos IDs. Metadados vinculados somente por título/ícone declarado em definição local; percentuais nunca identificam conquistas. Chave Steam opcional para o schema completo. Desbloqueios calculados no save local. |
| **1.5.11 — Spotify funcional** | Busca pública (faixas/álbuns/playlists) com Client ID + Secret, sem login; conta só p/ playlists e curtidas. Colar código manual quando o loopback falha; erros orientam (redirect/secret/porta). Conteúdo continua via downloader local. |
| **1.5.12 — Adicionar integração** | Botão + Adicionar nas Integrações: atalho https persistido na coleção (tipos link/catálogo/emulador/download, `{q}` p/ busca). Padrões protegidos; sem plugins arbitrários. |
| **1.5.13 — Piratas padrão** | Magnets vão ao qBittorrent do Hub (savepath Piratas/, categoria tucoteca) em Qt/clássico/TUI; perfil antigo migra o DefaultSavePath; import clássico e botão Organizar movem o que caiu fora (caso Hell Clock). |
| **1.5.14 — Bibliotecas sem credencial** | Busca de faixas em Deezer, iTunes e MusicBrainz, seleção e envio à fila; cache e erro inline. Spotify integrado no mesmo modelo, inclusive playlists, com OAuth para dados da conta. |
| **1.5.15 — Integração de mídias Qt** | Aba Vídeos, importação local, pesquisa/download YouTube, seleção VLC/MPV/MPC-HC e painel para Krita/GIMP/PhotoDemon, Audacity/APO/Peace. EQ gera cópia importada. Integra a frente 2.0 e a revisão de portabilidade do outro chat. |

O Hell Clock instalado foi efetivamente organizado em `D:\Games\Piratas\Hell Clock`;
entrada 51 atualizada, backup do banco e 372 arquivos conferidos por SHA-256.
Uma junction no caminho anterior preserva atalhos/configurações existentes.
No runtime portátil, a pasta padrão de jogos passa a ser `Piratas/` dentro da casa.

## Integrações pesquisadas

MusicBrainz/CAA, SteamGridDB e os adaptadores de mídia foram integrados;
os programas externos devem estar instalados/configurados. As demais linhas
abaixo registram a pesquisa e o backlog.

| Prioridade | Integração e fonte oficial | Benefício / encaixe |
|---|---|---|
| Alta | [Ludusavi](https://github.com/mtkennerly/ludusavi) — MIT | Preview/backup de saves PC e registro Windows; CLI com JSON. Complementa o backup do catálogo. |
| Alta | [MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_API) + [Cover Art Archive](https://musicbrainz.org/doc/Cover_Art_Archive/API) | Identificar álbuns e complementar capas; consultas públicas sem chave, com cache e limite de 1 chamada/s ao MusicBrainz. |
| Alta | [SDL GameControllerDB](https://github.com/mdqinc/SDL_GameControllerDB) — zlib | Base comunitária de mapas, a usar junto de um backend de entrada para navegação por controle. |
| Média | [SteamGridDB](https://github.com/SteamGridDB/node-steamgriddb) | Galeria de pôsteres e arte por AppID/título; API com chave. Clientes abertos, serviço/arte com condições próprias. |
| Média | [PCGamingWiki](https://github.com/PCGamingWiki/api) / [ProtonDB](https://www.protondb.com/) | Links de suporte/compatibilidade por AppID. Um primeiro passo simples antes de cachear metadados. |
| Média | [Heroic](https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher) / [Lutris](https://github.com/lutris/lutris) | Importação dos instalados e lançamento por runner externo. |
| Opcional | [pypresence](https://github.com/qwertyquerty/pypresence) | Rich Presence; requer cliente Discord e App ID. |
| Condicional | [RetroAchievements](https://docs.retroachievements.org/general/emulator-support-and-issues.html) | A documentação lista DeSmuME **core libretro**, não o standalone atual; não confirma Azahar/3DS. Exige compatibilidade do emulador para desbloquear conquistas. |

HowLongToBeat ficou em prioridade menor: wrappers comunitários não comprovam
uma API oficial estável. A licença MIT anteriormente atribuída ao redirect
PCGamingWiki não foi confirmada (`license: null` nos metadados consultados).

## Próximas sugestões de QoL

1. **Escala de texto configurável**, com reflow e validação das três larguras.
2. **Arrastar pasta/arquivo para importar**, com preview e confirmação dos itens.
3. **Duração das músicas e progresso do player**, com metadados cacheados.
4. **Preços/descontos nos Desejos**, com país/moeda e consulta sob demanda.
5. **Downloads: recebido/total e espaço restante**, mantendo clara a origem do progresso.
6. **Gamepad no Big Picture**, incluindo hotplug e repetição do direcional.
7. **Lixeira/desfazer**, cobrindo banco, capas e arquivos gerenciados.

## Validação

- Suíte integrada: **352 PASS, 6 SKIP, 0 FAIL — 358 casos** no Windows.
- `py_compile` dos Python alterados; `git diff --check` sem problemas.
- Auditoria em **1440×920 e 960×640** nas sete seções, incluindo Vídeos,
  mais música/YouTube/ferramentas/integrações; nenhum erro QML crítico.
- Selftest Qt: **26 jogos**. Banco original preservado, comprovado por SHA-256.
- As estatísticas globais não comprovam vínculo de metadados: a afirmação
  anterior “49/49 vinculados por percentual” foi corrigida. Lista pública
  disponível sem login; vínculo com ID exige definição verificável.
- Testes de carga incluídos: 1.000 arquivos/128 conteúdos distintos,
  20.000 linhas de progresso, processos sem stdout e timeout, falhas de banco,
  callbacks, cache offline, dados inválidos, UI e imports entre as duas frentes.
- Testes usam dados/áudio/processos simulados; capturas usam a cópia temporária.
- Login real Spotify requer Client ID/autorizar a conta; protocolo e catálogo
  autenticado foram testados em sandbox. Busca das bibliotecas públicas foi
  comprovada sem credenciais. Linux nativo/macOS ainda exigem prova no SO real.

Relatórios locais: `IA/TucoTeca/validacao/integracao-final-testes.json`,
`hell-clock-organizacao.json` e `qol-1.5-visual.json`. Pesquisa detalhada e notas de sessão
em `IA/TucoTeca/sessao/`. As capturas ficam no diretório temporário indicado
no relatório visual.
