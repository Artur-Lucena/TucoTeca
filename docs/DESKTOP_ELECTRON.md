# Desktop Electron

O desktop do TucoTeca é um app **Electron** com renderer **Preact +
TypeScript**; o motor continua em Python. Domínio (SQLite, emulação, áudio,
integrações) fica em `bib_nucleo` / `servicos_ui`; o Electron só apresenta.
Entrega: instalador Windows (NSIS). Linux/macOS usam a TUI pelos fontes.

```text
┌────────────────────────── Electron (Node) ────────────────────────────┐
│ main: janela, instância única, IPC, protocolos tucoteca-img/-media,   │
│       menu, diálogos, ciclo de vida da ponte                          │
│   └ preload (contextBridge) → window.tucoteca                         │
│       └ renderer: Preact + TypeScript (só IPC, sem Node)              │
└───────────────────────────────┬───────────────────────────────────────┘
                     spawn + NDJSON em stdin/stdout (sem TCP)
┌───────────────────────────────▼───────────────────────────────────────┐
│ ponte.py (+ _paridade/_meta/_colecoes/_midia) → ServicoBiblioteca     │
└───────────────────────────────────────────────────────────────────────┘
```

## Protocolo (NDJSON)

- Pedido: `{"id": 1, "metodo": "nucleo.ping", "params": {…}}` (`params` opcional).
- Resposta: `{"id": 1, "ok": true, "resultado": …}` ou `{"id": 1, "ok": false, "erro": "…"}`.
- Eventos (sem `id`): `bloqueio` (coleção ocupada; a ponte sai com código 2) e
  `trabalho` (início/progresso/cancelamento/fim de operações longas).
- A ponte nunca morre por erro de chamada: JSON inválido, método desconhecido e
  exceção viram `ok: false`. O main corta cada pedido em **30 s**; o que pode
  demorar mais roda como **trabalho** (`trabalhos.listar/cancelar`) e aparece no
  rodapé (`Atividade`).

## Métodos da ponte (136)

Contrato provado por `test_ponte.py`, `test_paridade.py`, `test_provedores.py`,
`test_colecoes.py` e `test_midia.py`. Ações que mexem em
arquivos do emulador, saves ou coleção recusam com um jogo aberto ("Feche o
jogo aberto antes…"); confirmações de ações destrutivas ficam na interface.

| Domínio | Métodos |
|---|---|
| núcleo e preferências | `nucleo.ping/snapshot/revisao/buscar/saude` (snapshot aceita `partes`), `modulos.listar`, `preferencias.ler/trocar_perfil/filtro/salvar_filtro`, `aparencia.ler/salvar` |
| jogos | `jogo.ler/salvar/favoritar/observacoes/jogar`*, `jogo.registrar_horas`, `jogo.diagnosticar/religar/disco/jogar_elevado`, `jogos.importar`*, `jogos.prever`, `jogos.importar_selecionados` |
| emulação | `emulacao.jogo/mod/cheat/textura/preset`, `emulacao.status/consultar/atualizar`*, `controles.listar/fotografar/aplicar/gerar/estado` |
| saves e capas | `saves.configurar/snapshot/restaurar`, `ferramentas.jogo`, `capas.buscar/aplicar/libretro`, `conquistas.avaliar/sincronizar/regras` |
| músicas | `musicas.importar`*, `musicas.baixar_fila`*, `musicas.buscar_online/enfileirar/letras`, `musicas.eq_presets`, `musicas.eq`* |
| vídeos | `videos.local/salvar_posicao/reproduzir/buscar_online`, `videos.importar/baixar/baixar_mp3`* |
| desejos | `desejos.adicionar/precos/sincronizar_steam/importar_wishlist/buscar_fontes` |
| downloads | `torrents.listar` (com `fora_destino`), `torrents.controlar/organizar`, `torrents.importar`*, `pacotes.importar/abrir_instalador` |
| integrações | `integracoes.listar/adicionar/remover/url/buscar` |
| coleção e sistema | `colecao.backup/exportar/importar`, `backups.listar`, `estatisticas.ler`, `item.excluir/desfazer`, `lixeira.estado`, `sessoes.listar/encerrar`, `sistema.erros/volume/volume_definir/volume_mudo`, `manutencao.plano/sanear`, `ferramentas.listar/abrir`, `provedores.configurar` |
| página do jogo e provedores | `jogo.pagina`, `jogo.enriquecer`*, `jogos.enriquecer_lote`*, `jogo.meta_salvar/artes_buscar/arte_aplicar`, `metadados.provedores/configurar` |
| coleções e loja | `colecoes.criar/renomear/apagar/definir`, `jogo.colecoes`, `loja.destaques/buscar/pagina/desejar`, `jogos.lojas_prever`* |
| filmes e séries | `midia.pastas/pasta_adicionar/pasta_remover`, `midia.varrer`*, `midia.biblioteca/titulo/descobrir/continuar/lista/lista_alternar/seguir/calendario`, `midia.atualizar_seguidas`*, `midia.corrigir/reproduzir/externo/salvar_posicao/marcar/legenda` |
| trabalhos | `trabalhos.listar/cancelar` |

\* roda como trabalho (devolve `{trabalho}`; resultado chega pelo evento).

## Telas

Seis seções na barra lateral; o resto são abas (`#/secao/aba`) ou páginas.

| Seção | Abas / páginas |
|---|---|
| Início | KPIs, **Continuar assistindo**, continuar jogando e **Sessões abertas** |
| Jogos | **Biblioteca** (grade, filtros, importar pasta, arrastar e soltar, importar de lojas instaladas) · **Catálogo** (vitrine e busca da loja Steam) · **Desejos** · **Coleções** |
| Página do jogo `#/jogo/:id[/aba]` | hero com arte e números; Visão geral (descrição, galeria, ficha), Conquistas (RetroAchievements + save), Emulação (3DS), Saves, Manutenção, Editar (dados, horas, capa, arte, correção dos provedores) |
| Página da loja `#/loja/:appid` | ficha da Steam; adicionar aos Desejos ou abrir o jogo se já está na biblioteca |
| Filmes e Séries | **Biblioteca** (pastas escolhidas, varrer, revisar correspondência) · **Continuar** · **Descobrir** (Cinemeta) · **Minha lista** · **Calendário** · **Vídeos** · **YouTube** |
| Página do título `#/titulo/:imdb` | sinopse, temporadas/episódios com progresso, assistir, lista, seguir, marcar visto |
| Músicas | lista, player no rodapé (letra sincronizada, volume do PC), equalizar, busca online e fila |
| Downloads | torrents com progresso, organizar, importar concluídos, pacotes locais |
| Configurações | **Geral** (aparência, provedores, dados dos jogos, emuladores, controles, sanear pasta, ferramentas de mídia, coleção) · **Integrações** |

Notificações ficam no sino do cabeçalho (`#/notificacoes` mostra o histórico).
As chaves antigas (`desejos`, `integracoes`, `videos`, `youtube`) continuam
valendo como apelidos de rota, inclusive nos atalhos pessoais.

## Comportamentos transversais

- **Rotas por hash** (`estado/rota.ts`): voltar/avançar pelos botões do
  cabeçalho, `Alt+←/→` e botões laterais do mouse.
- **Paleta** `Ctrl+K`/`Ctrl+F` (busca global), atalhos pessoais `Ctrl+1..8`,
  `F11` tela cheia.
- **Controle** (Gamepad API, mapeamento padrão): direcional/analógico movem o
  foco pela tela (`navegacao/foco.ts`, navegação espacial), A ativa, B fecha o
  diálogo aberto ou volta, LB/RB trocam de aba (ou de seção), Start abre a
  busca. O anel de foco aparece ao usar o controle e some ao mexer o mouse.
- **Big Picture** (densidade): zoom maior, anel de foco sempre visível, setas
  do teclado andam pelo foco fora de campos de texto e a lista lateral de
  jogos some.
- **Carga leve**: depois de uma ação o renderer pergunta `nucleo.revisao`
  (contadores por categoria mantidos por triggers) e recarrega só as listas
  que mudaram.
- **Aparência**: tema escuro/claro (`:root[data-tema]`, mesmos tokens de cor),
  densidade compacta/confortável/Big Picture e tamanho do texto (80–150%) viram
  o zoom da janela (`webFrame.setZoomFactor`). Aplicada ao abrir e ao salvar.
- **Confirmações**: `confirmar()` (diálogo do app, `componentes/ui/Confirmacao.tsx`)
  — nunca `window.confirm`. Esc/Enter são tratados na captura para não fechar a
  gaveta do detalhe junto.
- **Carregamento por seção**: `Lazy` com `key` por seção e componente nomeado
  (`import(...).then((m) => m.Videos)`).
- **Queda da ponte**: banner com **Reconectar** (single-flight, refaz o snapshot).
- **Lock da coleção**: instância única; lock de processo vivo é recusado. Lock
  órfão (pid morto no mesmo host/SO — crash, queda de energia, encerramento
  forçado) é assumido **ao abrir** e no Reconectar.
- **Arquivos soltos** fora da área de Jogos não fazem nada (`will-navigate`
  bloqueado e drop padrão cancelado); o caminho real vem de
  `webUtils.getPathForFile` (`caminhoDoArquivo`).

## Segurança

- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`; o
  renderer só enxerga `window.tucoteca` (`shared/api.ts`).
- Imagens e mídia locais por `tucoteca-img://` e `tucoteca-media://` (com
  Range); o main valida cada caminho contra a pasta da coleção e, para mídia,
  também contra as pastas de Filmes e Séries escolhidas pelo usuário (lidas do
  núcleo; raiz de disco, caminho relativo e `..` são recusados; fora → 403).
- Rede só por ação do usuário (buscar dados, abrir Catálogo/Descobrir,
  varrer pastas). Exceção aprovada: o Calendário renova as séries seguidas ao
  ser aberto, no máximo a cada 12 h. Tudo respeita `BIBLIOTECA_REDE=0`.
- Links http/https abrem no navegador do sistema; `app:abrir-url` só aceita
  https e respeita `BIBLIOTECA_REDE=0`; `app:abrir-pasta` só dentro da coleção.
- Seletores de arquivo/pasta são do sistema; filtros vindos do renderer são
  validados (extensões alfanuméricas).
- Provas usam `BIBLIOTECA_HOME` e `TUCOTECA_USERDATA` temporários — nunca a
  coleção real nem o `%APPDATA%` padrão.

## Desenvolvimento e verificação

```powershell
npm --prefix codigo/frontends/electron ci
npm --prefix codigo/frontends/electron run dev        # hot reload
npm --prefix codigo/frontends/electron test           # vitest
npm --prefix codigo/frontends/electron run typecheck
py -3.14 -B codigo/ferramentas/validar.py             # todos os gates
```

Selftest: `electron . --selftest [--screenshot x.png] [--db X] [--ignorar-lock]`
— erro → saída 1, lock ocupado → 2, sucesso imprime
`[ok] selftest Electron: N jogos; ponte, módulos e Início carregados`.
Coleção sintética para provas: `semear_prova_electron.py --destino … --limpar`.
Provas de tela usam `--remote-debugging-port` e CDP sobre o app empacotado.

| Variável | Uso |
|---|---|
| `TUCOTECA_RAIZ` | raiz dos fontes Python (checkout: 3 níveis acima do `appPath`; instalado: `resources/tucoteca`) |
| `BIBLIOTECA_HOME` | pasta da coleção (checkout: a raiz; instalado: `Documentos\TucoTeca`, preservada ao atualizar/desinstalar) |
| `TUCOTECA_PYTHON` | intérprete explícito; ordem: env → `programa/windows-x64/python/python.exe` → `py -3.14` / `python3` |
| `TUCOTECA_USERDATA` | userData do Electron fora do padrão (provas) |

## App instalado

`npm run dist` gera `dist/TucoTeca-Setup-<versão>-x64.exe` (NSIS por usuário,
sem admin) com `electron-builder.config.cjs`: núcleo Python, ponte e Python
embutido em `resources/tucoteca/`. A ponte roda com `windowsHide` (sem
console). Build, prova e anexos: `docs/RELEASES.md`. Sem assinatura de código
(decisão do usuário).

## Limites conhecidos

- Download automático de repacks a partir das fontes não está na interface (a
  busca abre a página no navegador). Filmes e Séries não transmitem nada:
  Cinemeta é só catálogo e os vídeos são os arquivos do usuário.
- O player interno toca o que o Chromium toca (MP4/H.264, WebM…); MKV com
  HEVC/DTS/AC3 vai para o reprodutor externo. Textos do Cinemeta vêm em inglês.
- HowLongToBeat usa uma API não oficial (desligado por padrão).
- Controle físico, UAC real, FFmpeg instalado e atualização real de emulador
  foram provados por simulação; a validação no hardware do usuário segue
  pendente (ver `ROADMAP.md`).
- O volume do player é do renderer (HTMLAudio); o volume do PC usa Core Audio
  e só aparece no Windows.
