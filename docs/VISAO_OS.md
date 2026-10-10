# Visão TucoOS — do Hub ao OS pessoal

TucoTeca é um hub local-first (jogos + músicas + downloads). TucoOS é a
ambição: o mesmo núcleo confiável virando um shell pessoal — Início,
busca global, serviços e integrações — sem virar spyware, sem nuvem
obrigatória, sem reescrita exótica.

Python continua no domínio. Qt Quick continua na apresentação. O que muda
é organização: tudo vira módulo com contrato, ação explícita e teste.

## Onde estamos (10/10/2026)

- Desktop Qt é o frontend principal no Windows (`desktop.py` → Qt, `--classico` → tkinter).
- HUD superior: Início, Jogos, Músicas, Desejos, Downloads, Integrações. Big Picture (F11) preserva categoria.
- Início: continuar jogando, resumo da coleção (backup/sessões/disco), acesso rápido, recentes.
- Paleta global Ctrl+K: busca em memória em jogos/músicas/desejos/downloads, Enter abre o primeiro.
- Serviços em `servicos_ui.py`: `snapshot()` + `resumo_sistema()` + `busca_global()` + `RegistroIntegracoes`.
- Bridge Qt (`qt_bridge.py`): modelos, workers em `QThreadPool`, gerações anti-resposta-obsoleta, player com token.
- Suite Qt 10/10 + visual tkinter intacto. Validação visual em cópia isolada (25 jogos, 51 músicas).

## Princípios inegociáveis

1. Local-first: coleção em SQLite + arquivos. Rede só sob ação, com timeout e erro virando aviso.
2. Uma coleção, um lock. Qt e tkinter nunca escrevem juntos.
3. Backup antes de mutação. Publicação atômica. Conexão SQLite por operação.
4. UI nunca bloqueia: I/O em worker, resultado via sinal, resposta obsoleta descartada.
5. Integração = adaptador registrado, não plugin arbitrário. Sem execução de código de terceiros.
6. Teste hermético: sandbox, sem rede/processo/escrita externa, sem jogo/áudio real na suite.

## Roadmap proposto

### Fase 1 — Hub sólido (atual → próxima)
- [x] Início + paleta + sistema local
- [x] QoL 1.0: Biblioteca Pro (nota/etiquetas/saúde), player (fila/modos/volume),
  downloads (vel/ETA), sistema (backups/sessões/logs), polimento (tema, paleta ↑↓)
- [ ] Biblioteca com conquistas locais e tempo estimado
- [ ] Desejos com preço/histórico local (cache, não scraping agressivo)
- [ ] Downloads com ETA/velocidade na lista + importar concluído em 1 clique
- [ ] Player com fila visível, capa do álbum e atalhos de mídia

### Fase 2 — TucoHub (médio prazo)
- Módulos novos, cada um com serviço + QML + teste:
  - **Arquivos**: navegar `Games/`, abrir com app padrão, sanear repacks (reuso de `repacks.py`).
  - **Apps**: launcher de executáveis locais (atalhos `.lnk`, Steam manifests `appmanifest_*.acf`).
  - **Emulação**: Azahar/DeSmuME com cards de preset/mod/textura/cheat por jogo (traz tkinter → QML).
  - **Mídia**: fila CSV → áudio com progresso real (traz `baixar.py` → QML).
  - **Sistema**: saúde (CPU/RAM/GPU/disco), volume, sessões, backups, logs — tudo stdlib + WinAPI isolada.
- Busca global vira launcher: `> comando`, `jogo:`, `musica:`, `? ajuda`.
- Temas + densidade (compacto/conforto/Big Picture) via `Theme.qml`.
- Gamepad: navegação espacial na grade (foco QML) + mapeamento em `controles.py`.

### Fase 3 — TucoOS shell (ambição)
- Boot opcional em tela cheia como shell de HTPC: Big Picture vira modo padrão, Esc pede confirmação.
- Tela de bloqueio local (PIN), perfis (Tuco/visita), controle parental por etiqueta.
- Serviços de fundo opt-in: vigia de saves, vigia de ROMs, servidor DLNA/Jellyfin local, sync Syncthing.
- Loja local de integrações: cada integração declara permissões (rede/disco/processo) e o usuário liga/desliga.
- Empacotamento: SuperHub inclui Qt + manifestos; atualização transacional como emuladores.

## Integrações eficazes (sugestões concretas)

| Integração | Tipo | Por que | Forma segura |
|---|---|---|---|
| Steam local (`appmanifest`, `libraryfolders.vdf`, `shortcuts.vdf`) | catálogo | Importa biblioteca sem login | Só leitura de arquivos locais, preview antes de gravar |
| GOG/Epic manifests locais | catálogo | Mesma razão | Mesmo padrão Steam, um adaptador por loja |
| RetroAchievements (opt-in, token do usuário) | progresso | Conquistas sem spoof | Cache local, polling sob ação, nunca credencial em log |
| HowLongToBeat / IGDB via chave do usuário | metadados | Tempo estimado, capa fallback | Timeout curto, falha = aviso |
| Jellyfin/Plex local | mídia | Filmes/séries no mesmo shell | Cliente loopback, sem exposição externa |
| Syncthing / rclone (BYOB) | sync | Saves/músicas entre máquinas | Perfil próprio, como qBittorrent; nunca pasta do SO |
| qBittorrent (já) + RSS local | download | Séries/mods | Filtros explícitos, destino em `Piratas/` |
| Discord Rich Presence (opt-in) | social | “Jogando X” | Processo lateral, desliga por padrão |
| Voice/Gamepad (SDL) | entrada | Controle total no sofá | Mapeamento visível, sem hook global |
| IA local (Whisper/llama.cpp BYOB) | assistência | “Ache RPG <20h”, organizar etiquetas | Modelo baixado sob ação, inferência em worker |

O que NÃO fazer: store própria com pagamento, conta online obrigatória, telemetria, plugin com `eval`/DLL arbitrária, scraper que martela site, auto-update silencioso.

## Contrato de módulo OS (para não virar bola de lama)

```text
codigo/os_nucleo/<modulo>.py   regra + I/O, sem Qt
codigo/frontends/qml/<Modulo>.qml   apresentação
qt_bridge: <modulo>_modelo + Slot ação + Property estado
test_<modulo>.py: 3-8 casos herméticos
docs/VISAO_OS.md: linha na matriz de cobertura
```

- DTOs simples (dict/list/str). Nada de callable no QML.
- Erro vira `{ok: False, erro: str}` ou aviso, nunca exceção na UI.
- Ação destrutiva pede confirmação e faz backup.
- Novo serviço registra em `RegistroIntegracoes` com `tipo` e `permissões`.

## Métricas de pronto

- Suite verde + `git diff --check` limpo + selftest Qt e tkinter.
- Captura 1440×920 e 960×640 sem HUD engolindo conteúdo, sem `Binding loop`/`ReferenceError`.
- Ação longa mostra atividade, permite fechar só após concluir, e não deixa áudio/jogo órfão.
- Docs atualizadas: cobertura Qt × clássico, permissões da integração, como reproduzir.

## Decisão pedida

Escolha 1 trilha para a próxima sessão (sem “Outro” na hora de implementar):

- **A — Biblioteca Pro**: metadados, fila do player, importar concluído, detalhes ricos.
- **B — Emulação no Qt**: presets/mods/texturas/cheats por jogo em QML (maior valor p/ 3DS/NDS).
- **C — Sistema OS**: Arquivos + Apps + saúde do PC, paleta como launcher.
- **D — Catálogos Pro**: Steam local + RetroAchievements opt-in + cache.
