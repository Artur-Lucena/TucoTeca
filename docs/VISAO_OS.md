# Visão TucoOS — do Hub ao OS pessoal

TucoTeca é um hub pessoal local-first de Tuco e Isa (jogos + músicas + vídeos).
TucoOS é a
ambição: o mesmo núcleo confiável virando um shell pessoal — Início,
busca global, serviços e integrações — sem virar spyware, sem nuvem
obrigatória, sem reescrita exótica.

Python continua no domínio. Qt Quick continua na apresentação. O que muda
é organização: tudo vira módulo com contrato, ação explícita e teste.

## Onde estamos (11/10/2026)

- Desktop Qt é o frontend no Windows (`desktop.py` → Qt Quick); a TUI curses atende Linux/macOS.
- HUD superior: Início, Jogos, Músicas, Desejos, Downloads, Integrações, Vídeos e YouTube.
  Big Picture (F11) preserva categoria; modo simples reduz a navegação.
- Início: continuar jogando, resumo da coleção (backup/sessões/disco), acesso rápido, recentes.
- Paleta global Ctrl+K: busca local em jogos/músicas/desejos/downloads, com
  FTS5 para jogos e fallback tolerante a acentos; Enter seleciona o resultado certo.
- Serviços em `servicos_ui.py`: `snapshot()` + `resumo_sistema()` + `busca_global()` + `RegistroIntegracoes`.
- Bridge Qt (`qt_bridge.py`): modelos, workers em `QThreadPool`, gerações anti-resposta-obsoleta, player com token.
- `qml/secoes/` separa as telas; desejos, Hydra, sessões manuais e adaptadores
  remotos foram extraídos para domínios. Módulos grandes ainda requerem evolução.
- Desejo → fonte → importação → obtido preserva histórico. Saves explícitos têm
  snapshots/restauração SHA-256 com backup anterior; screenshots são locais.
- Tuco/Isa compartilham coleção/saves, mas têm favoritos e filtros próprios.
  Atalhos, histórico anual, disco por jogo, IPS/BPS e cópia/hardlinks são locais.
- Vigia, extração automática, SponsorBlock e API loopback de leitura são opt-in.
- Bundles locais essencial/completo: o completo inclui Chromium privado e
  QtMultimedia com retomada. Áudio MCI/LRC também cobre caminhos longos.
- Provas separadas: suíte hermética, runtime nativo com mídias sintéticas,
  capturas 1440×920/960×640 e smokes remotos. Resultado exato acompanha a entrega,
  não é inferido da suíte antiga. Nenhum jogo real é aberto nos testes.

## Princípios inegociáveis

1. Local-first: coleção em SQLite + arquivos. Rede só sob ação, com timeout e erro virando aviso.
2. Uma coleção, um lock. Qt e TUI nunca escrevem juntos.
3. Backup antes de mutação. Publicação atômica. Conexão SQLite por operação.
4. UI nunca bloqueia: I/O em worker, resultado via sinal, resposta obsoleta descartada.
5. Integração = adaptador registrado, não plugin arbitrário. Sem execução de código de terceiros.
6. Teste hermético: sandbox, sem rede/processo/escrita externa, sem jogo/áudio real na suite.

## Escopo aprovado e limites

Steam fornece apenas catálogo/wishlist/referência: nada de lançamento pela
Steam, overlay ou sincronização de conquistas. Sem conta obrigatória,
telemetria, interop Playnite/RomM/ITAD ou publicação pública de bundles.
Tudo remoto respeita `BIBLIOTECA_REDE`; a flag não é firewall de apps externos.
Gamepad, assinatura Windows e entrega macOS permanecem adiados.

## Roadmap de referência (não autorização de novas features)

### Fase 1 — Hub sólido (atual → próxima)
- [x] Início + paleta + sistema local
- [x] QoL 1.0: Biblioteca Pro (nota/etiquetas/saúde), player (fila/modos/volume),
  downloads (vel/ETA), sistema (backups/sessões/logs), polimento (tema, paleta ↑↓)
- [x] Biblioteca com conquistas locais baseadas em saves/regras compatíveis
- [ ] Tempo estimado de jogo (adiado)
- [ ] Desejos com preço/histórico local (cache, não scraping agressivo)
- [x] Downloads com ETA/velocidade na lista + importação explícita de concluídos
- [x] Player com fila visível, capa do álbum e atalhos internos configuráveis

### Fase 2 — TucoHub (médio prazo)
- Módulos novos, cada um com serviço + QML + teste:
  - **Arquivos**: navegar `Games/`, abrir com app padrão, sanear repacks (reuso de `repacks.py`).
  - **Apps**: launcher de executáveis locais (atalhos `.lnk`, Steam manifests `appmanifest_*.acf`).
  - **Emulação**: Azahar/DeSmuME com cards de preset/mod/textura/cheat por jogo.
  - **Mídia**: fila CSV → áudio com progresso real (traz `baixar.py` → QML).
  - **Sistema**: saúde (CPU/RAM/GPU/disco), volume, sessões, backups, logs — tudo stdlib + WinAPI isolada.
- Busca global vira launcher: `> comando`, `jogo:`, `musica:`, `? ajuda`.
- Temas + densidade (compacto/conforto/Big Picture) via `Theme.qml`: implementados.
- Gamepad: adiado; presets de controles dos emuladores não são navegação por gamepad.

### Fase 3 — TucoOS shell (ambição)
- Boot opcional em tela cheia como shell de HTPC: Big Picture vira modo padrão, Esc pede confirmação.
- Tela de bloqueio local (PIN) e controle parental: apenas ideias; perfis leves Tuco/Isa já existem.
- Serviços de fundo opt-in: vigia de saves, vigia de ROMs, servidor DLNA/Jellyfin local, sync Syncthing.
- Loja local de integrações: cada integração declara permissões (rede/disco/processo) e o usuário liga/desliga.
- Empacotamento: SuperHub inclui Qt + manifestos; atualização transacional como emuladores.

## Integrações eficazes (sugestões concretas)

| Integração | Tipo | Por que | Forma segura |
|---|---|---|---|
| Steam local (`appmanifest`, `libraryfolders.vdf`, `shortcuts.vdf`) | catálogo | Importa biblioteca sem login | Só leitura de arquivos locais, preview antes de gravar |
| GOG/Epic manifests locais | catálogo | Mesma razão | Mesmo padrão Steam, um adaptador por loja |
| HowLongToBeat / IGDB via chave do usuário | metadados | Tempo estimado, capa fallback | Timeout curto, falha = aviso |
| Jellyfin/Plex local | mídia | Filmes/séries no mesmo shell | Cliente loopback, sem exposição externa |
| Syncthing / rclone (BYOB) | sync | Saves/músicas entre máquinas | Perfil próprio, como qBittorrent; nunca pasta do SO |
| qBittorrent (já) + RSS local | download | Séries/mods | Filtros explícitos, destino em `Meus Jogos Locais/` |
| Voice/Gamepad (SDL) | entrada | Controle total no sofá | Mapeamento visível, sem hook global |
| IA local (Whisper/llama.cpp BYOB) | assistência | “Ache RPG <20h”, organizar etiquetas | Modelo baixado sob ação, inferência em worker |

Estas sugestões não fazem parte da entrega atual; conquistas continuam
100% locais, sem RetroAchievements/sync social. O que NÃO fazer: store própria
com pagamento, conta online obrigatória, telemetria, plugin com `eval`/DLL
arbitrária, scraper que martela site, auto-update silencioso.

## Contrato de módulo OS (para não virar bola de lama)

```text
codigo/bib_nucleo/<modulo>.py   regra + I/O, sem Qt
codigo/bib_nucleo/rede/<adaptador>.py   integração remota explícita
codigo/frontends/qml/secoes/<Modulo>.qml   apresentação
qt_bridge: <modulo>_modelo + Slot ação + Property estado
test_<modulo>.py: 3-8 casos herméticos
docs/VISAO_OS.md: linha na matriz de cobertura
```

- DTOs simples (dict/list/str). Nada de callable no QML.
- Erro vira `{ok: False, erro: str}` ou aviso, nunca exceção na UI.
- Ação destrutiva pede confirmação e faz backup.
- Novo serviço registra em `RegistroIntegracoes` com `tipo` e `permissões`.

## Métricas de pronto

- Suite verde + `git diff --check` limpo + selftest Qt e TUI.
- Captura 1440×920 e 960×640 sem HUD engolindo conteúdo, sem `Binding loop`/`ReferenceError`.
- Ação longa mostra atividade, permite fechar só após concluir, e não deixa áudio/jogo órfão.
- Docs atualizadas: cobertura Qt Quick, permissões da integração, como reproduzir.

## Evolução posterior

Novas trilhas precisam de decisão específica; não expandir o escopo durante
o fechamento dos bundles. Emulação avançada permanece acessível no desktop.
Everything tem fallback testado, mas o índice nativo não foi comprovado neste
ambiente; No-Intro/matching exato e provedores externos não são garantidos.
