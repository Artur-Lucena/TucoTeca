# Histórico de auditorias e reconciliações (consolidado)


## PARTE1_VISUAL_E_AUDITORIA.md

# Parte 1 â€” acabamento visual e auditoria

Data: 09/10/2026. Base: Ã¡rvore de trabalho sobre `98dccd1`, incluindo as
alteraÃ§Ãµes acumuladas das sessÃµes anteriores. Este documento registra a
implementaÃ§Ã£o atual e o trabalho recomendado para a Parte 2.

## 1. Acabamento aplicado

- Tema prÃ³prio em `codigo/frontends/aparencia.py`: paleta azul-escura/violeta,
  botÃµes nine-slice arredondados com estados de foco/hover/desabilitado,
  tipografia consistente e Ã­cone local. Os elementos sÃ£o gerados com Tk;
  o runtime nÃ£o precisa baixar tema, instalar pacote ou carregar uma DLL nova.
- CabeÃ§alhos por seÃ§Ã£o, descriÃ§Ã£o do contexto e busca expansÃ­vel. Filtros de
  plataforma/status/etiquetas aparecem apenas na Biblioteca.
- Barra lateral rolÃ¡vel, volume fixo e grupos sÃ³ onde hÃ¡ vÃ¡rias aÃ§Ãµes.
  Biblioteca â†’ Todos os jogos; MÃºsicas â†’ Minhas faixas. Desejos e Downloads
  sÃ£o destinos diretos.
- Desejos, Downloads, MÃºsicas e Fila usam Treeview: cabeÃ§alhos, colunas,
  zebra, seleÃ§Ã£o independente e apenas a rolagem da tabela.
- `BarraAcoes` redistribui aÃ§Ãµes conforme a largura real, inclusive nos
  catÃ¡logos. As listas de resultados e hosts tÃªm rolagem em seus prÃ³prios
  contÃªineres.
- Grade de capas com tamanho uniforme, hover/seleÃ§Ã£o e fallback em gradiente.
  Marcadores de downloads/desejos/mÃºsica sÃ£o desenhados como vetores, sem
  depender de uma fonte de emoji.
- Detalhes com rolagem. Abaixo de 1120 px, o espaÃ§o Ã© cedido ao conteÃºdo e
  **Detalhes** abre uma janela sincronizada com a seleÃ§Ã£o atual.
- O helper visual entra em `copiar_app`, utilizado nos trÃªs builders.

### Pesquisa tÃ©cnica

Foram consultados os projetos [Sun Valley](https://github.com/rdbende/Sun-Valley-ttk-theme),
[Azure ttk](https://github.com/rdbende/Azure-ttk-theme) e a
[documentaÃ§Ã£o de ttk](https://docs.python.org/3/library/tkinter.ttk.html).
Aplicamos a tÃ©cnica documentada de elementos de imagem/estados e widgets
ttk, com arte gerada localmente. Nenhum cÃ³digo desses temas foi copiado.

## 2. Problemas confirmados e corrigidos nesta etapa

| Problema | EvidÃªncia | CorreÃ§Ã£o |
|---|---|---|
| A grade terminava em uma coluna apÃ³s resize | Interface visÃ­vel em 1280Ã—800; reorganizaÃ§Ã£o chamava `update_idletasks`, permitindo reentrada | MediÃ§Ã£o e redistribuiÃ§Ã£o sem event loop aninhado |
| AÃ§Ãµes cortadas e duas barras nas listas | Janela compacta e barras com vÃ¡rios botÃµes em uma linha fixa | Fluxo por largura medida, tabelas com viewport prÃ³prio |
| Imagens de um Tk destruÃ­do eram reutilizadas | Cache global nÃ£o incluÃ­a identidade do interpretador | Chave por interpretador e teste com dois roots |
| Tema novo ficaria fora do ZIP | Lista explÃ­cita de arquivos em `montar_portatil.py` | InclusÃ£o de `aparencia.py` e teste do layout offline |
| Torrents reais nÃ£o eram encontrados no Windows | `BT_backup` estava em Local, enquanto o Hub sÃ³ consultava Roaming | Local primeiro, compatibilidade com Roaming e override |
| Arquivo prÃ©-alocado podia indicar conclusÃ£o falsa | Contagem antiga dependia de `stat().st_size`; reproduÃ§Ã£o com arquivo de zeros | PeÃ§as do fast-resume v1/v2; estimativa nunca autoriza conclusÃ£o |
| Torrent single-file era procurado em `nome/nome` | ComposiÃ§Ã£o antiga aplicava o nome duas vezes | Arquivo e pasta tratados separadamente |
| Metadados bencode ruins podiam provocar exceÃ§Ãµes nÃ£o tratadas | Chave de dicionÃ¡rio nÃ£o-hashable e aninhamento excessivo | ValidaÃ§Ã£o de chaves/caminhos e limite de profundidade |
| Sync parcial podia remover desejos jÃ¡ existentes | Worker aceitava itens parciais com erros e chamava o espelho destrutivo | Qualquer erro preserva o estado anterior |
| Desejo manual perdia proteÃ§Ã£o quando aparecia no espelho | UPDATE definia `manual=0` | Flag manual preservado; teste de duas sincronizaÃ§Ãµes |
| JSON de desejos invÃ¡lido podia quebrar o parser | Valores nÃ£o-objeto em dicionÃ¡rio provocavam unpack/strip invÃ¡lido | Tipos verificados e tÃ­tulos normalizados |
| Mensagem afirmava que login resolveria endpoint indisponÃ­vel | Redirecionamento Ã  home ocorria mesmo no navegador do usuÃ¡rio | Erro descreve a resposta observada e orienta inclusÃ£o/exportaÃ§Ã£o local |
| Sanear bloqueava a GUI e limpava antes de localizar jogo | Varredura sÃ­ncrona e organizaÃ§Ã£o anterior Ã  detecÃ§Ã£o | Worker com backup, progresso, retorno pela fila e detecÃ§Ã£o antes da limpeza |
| RedistribuÃ­veis diferentes eram tratados como duplicados | Igualdade era inferida por nome/profundidade | SÃ³ cÃ³pia da raiz comprovadamente idÃªntica por arquivos/tamanho/SHA-256 Ã© removida |

Os testes de higienizaÃ§Ã£o usam diretÃ³rios artificiais. Esta etapa nÃ£o
executou limpeza na coleÃ§Ã£o real, nem modificou seus tÃ­tulos/capas/saves.

## 3. VerificaÃ§Ã£o

- SuÃ­te completa: **249 casos sem falha**, sendo **243 executados** e **6
  pulados por condiÃ§Ãµes do Windows**. O runner explicita cada pulo; nÃ£o sÃ£o
  testes executados com sucesso.
- Testes de interface visÃ­vel em 1280Ã—800, 960Ã—600 e 860Ã—560, inclusive
  redimensionamento de volta, seleÃ§Ã£o, janela de detalhes e aÃ§Ãµes alcanÃ§Ã¡veis.
- Escala Tk equivalente a 125% verificada em teste adicional.
- CompilaÃ§Ã£o/sintaxe dos fontes tambÃ©m conferida com sintaxe mÃ­nima 3.10.
- Pyflakes temporÃ¡rio utilizado na revisÃ£o: sem `UndefinedName` ou
  `UndefinedLocal`; AST sem definiÃ§Ãµes duplicadas. Existem avisos de imports
  de reexportaÃ§Ã£o, probes opcionais e variÃ¡veis/imports nÃ£o usados nos testes.
  Esses avisos nÃ£o foram confundidos com falhas funcionais.
- Banco real aberto somente-leitura: integridade `ok`, 25 jogos, 51 mÃºsicas,
  4 desejos, 0 downloads de Ã¡udio. Nenhum executÃ¡vel da coleÃ§Ã£o ausente.
  Uma entrada tem tÃ­tulo `Balls`, aponta para a pasta BALL x PIT e nÃ£o tem capa.
- O histÃ³rico real do qBittorrent foi lido: BALL x PIT [FitGirl Repack],
  100% em peÃ§as, destino em `D:\Games\Piratas`.
- Capturas de verificaÃ§Ã£o foram feitas a partir de um snapshot temporÃ¡rio
  do banco. Selftest tambÃ©m deve ser reproduzido com snapshot/casa separados
  para evitar conflito com o Hub aberto.

## 4. Melhorias recomendadas para a Parte 2

### Prioridade 1 â€” integraÃ§Ãµes completas e contratos

1. **qBittorrent Web API local.** O histÃ³rico em arquivo Ã© periÃ³dico e nÃ£o
   informa velocidade/ETA em tempo real. Adicionar adaptador para a API
   oficial, com estado de conexÃ£o, pausa/retomada, destino e reconexÃ£o. Manter
   arquivos como fallback. Download seletivo, paths remapeados e torrents
   v2-only exigem tratamento adicional.
2. **Pipeline persistente de conclusÃ£o.** Atualmente a importaÃ§Ã£o Ã© acionada
   pelo usuÃ¡rio em Verificar concluÃ­dos. Falta uma fila persistente que
   registre download â†’ verificaÃ§Ã£o â†’ instalaÃ§Ã£o necessÃ¡ria/pronto â†’ importado,
   sem reimportar a cada poll. Instalador baixado nÃ£o Ã© jogo instalado.
3. **Wishlist remota moderna.** `ler_wishlist` ainda tenta o endpoint antigo.
   O endpoint pÃºblico `IWishlistService/GetWishlist/v1` foi consultado para
   esta conta e respondeu `{"response":{}}`, o que nÃ£o prova sozinho se a
   lista estÃ¡ vazia, privada em detalhes de jogos ou indisponÃ­vel. Implementar
   o adaptador moderno com metadados, distinÃ§Ã£o de erro/privacidade/vazio,
   seleÃ§Ã£o de conta e testes de resposta completa. InclusÃ£o manual e JSON
   sÃ£o os caminhos locais funcionais atuais.
4. **Gerenciador Ãºnico de tarefas.** Existem workers especÃ­ficos espalhados
   pela GUI. Centralizar progresso, cancelamento, timeout, exceÃ§Ãµes e resultados,
   preservando a afinidade da UI/MCI e uma conexÃ£o SQLite por worker.

### Prioridade 2 â€” metadados, arquivos e distribuiÃ§Ã£o

5. **Resolver metadados por contexto.** Combinar executÃ¡vel, pasta, manifesto
   da loja e AppID da lista de desejos. Isso evita tÃ­tulos genÃ©ricos como
   `Balls` e melhora a busca de capa. A associaÃ§Ã£o deve ter evidÃªncia e nÃ­vel
   de confianÃ§a explÃ­citos.
6. **Plano de limpeza por jogo.** `sanear_pasta` Ã© destinado a uma pasta de
   jogo; nÃ£o Ã© um organizador geral de C:/D:. Acrescentar preview por tÃ­tulo,
   manifesto de operaÃ§Ãµes e restauraÃ§Ã£o da quarentena. ComparaÃ§Ã£o de conteÃºdo
   deve continuar sendo requisito para remover uma duplicata.
7. **Ferramentas em um pacote.** Descoberta relativa Ã  casa do Hub e manifesto
   local de versÃµes/licenÃ§as/hashes para qBittorrent, 7-Zip, FFmpeg, yt-dlp e
   emuladores. Os builders hoje nÃ£o entregam todos esses sidecars juntos.
8. **Decompor frontends por domÃ­nio.** AparÃªncia jÃ¡ foi extraÃ­da; separar
   pÃ¡ginas, diÃ¡logos, tarefas e controladores antes de um porte PySide6. O
   nÃºcleo deve conservar APIs utilizÃ¡veis sem interface grÃ¡fica.
9. **ColeÃ§Ãµes grandes.** A grade atual limita o desenho a 150 jogos. Implementar
   paginaÃ§Ã£o/renderizaÃ§Ã£o por viewport, seleÃ§Ã£o por identidade e carregamento
   assÃ­ncrono de arte, evitando reconsultas de providers em toda busca.
10. **ValidaÃ§Ã£o nativa dos outros SOs.** Testes de caminhos/Mac/Linux nesta
    sessÃ£o foram executados ou simulados no Windows. Ainda Ã© necessÃ¡rio testar
    instalaÃ§Ã£o, Ã¡udio, DPI e interaÃ§Ã£o com emuladores em mÃ¡quinas reais.

### Qualidade de engenharia

- Integrar Pyflakes/Ruff no CI com exceÃ§Ãµes explÃ­citas para reexports/probes.
- Manter testes com a janela realmente dimensionada; selftest oculto nÃ£o
  substitui teste de geometria.
- Guardar relatÃ³rio JSON por versÃ£o e incluir o helper visual no pacote.
- Entregas atuais: `dist/windows/`; ZIPs dos fontes: `dist/fontes/`;
  versÃµes anteriores: `dist/historico/`.
- A Ã¡rvore possui alteraÃ§Ãµes acumuladas nÃ£o commitadas. Entregas para revisÃ£o
  devem usar `empacotar_fontes.py`, que inclui o estado atual, e o manifesto
  SHA-256; uma cÃ³pia do Ãºltimo commit sozinho nÃ£o contÃ©m todas as mudanÃ§as.

## 5. ReferÃªncias para integraÃ§Ãµes

- [qBittorrent WebUI API](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-5.0))
- [libtorrent: fast-resume e prÃ©-alocaÃ§Ã£o](https://www.libtorrent.org/manual-ref.html#fast-resume)
- [ttk: elementos, estados e Treeview](https://docs.python.org/3/library/tkinter.ttk.html)


---

## PARTE2_RUNTIME_E_INTEGRACOES.md

# Parte 2 â€” runtime independente, otimizaÃ§Ã£o e compactaÃ§Ã£o

09/10/2026. Primeira entrega implementada da Parte 2.

## Resultado medido

Tamanhos abaixo em MiB (1.048.576 bytes), arredondados a duas casas.

| Artefato | Tamanho | ComparaÃ§Ã£o com ZIP anterior |
|---|---:|---:|
| PortÃ¡til anterior, 23/09 | 298,10 | referÃªncia |
| SuperHub completo ZIP | 144,22 | 51,6% menor |
| SuperHub completo 7z/LZMA2 sÃ³lido | 97,16 | 67,4% menor |

O runtime novo descompactado ocupa aproximadamente 370,42 MiB. Inclui
mais ferramentas de integraÃ§Ã£o que o anterior; o ganho principal veio
da separaÃ§Ã£o entre programa e estado pessoal, alÃ©m da poda e compactaÃ§Ã£o.
O ZIP anterior continha cerca de 400 MiB de estado/mods do Azahar. O
qBittorrent instalado tambÃ©m tinha aproximadamente 162 MiB de `.pdb`.

Arquivos gerados em `dist/windows/`:

- `tucoteca-superhub-windows-x64-20261009.zip`
- `tucoteca-superhub-windows-x64-20261009.7z`
- `superhub-verificacao.json`: tamanhos exatos, SHA-256 e provas da Ã¡rvore
  e dos dois arquivos extraÃ­dos.

## Estrutura do pacote

```text
BibliotecaHub.bat / Debug-Console.bat
README-PORTATIL.txt / LICENSE-TucoTeca.txt
manifesto-runtime.json
app/                    fontes locais editÃ¡veis
python/                 Python 3.14.7 + Tk + Pillow
ferramentas/
  7zip/                 7z.exe + 7z.dll
  ffmpeg/               FFmpeg 9.0.2
  yt-dlp/               zipapp oficial 2026.08.19, com EJS
  quickjs/              QuickJS-NG 0.17.0
  qbittorrent/          qBittorrent 5.2.4
emuladores/
  Azahar/               2126.1.1, DLLs/plugins e user/ novo
  DeSmuME/              release_0_9_13
dados/                  coleÃ§Ã£o/perfis criados localmente
```

As fontes da TucoTeca permanecem arquivos `.py`. Os componentes de
terceiros sÃ£o executados como processos independentes, com suas licenÃ§as
e links de fonte junto deles. NÃ£o foi aplicado UPX nem alterado um executÃ¡vel
de terceiro. Os codecs de Pillow nÃ£o usados pela UI (AVIF, fontes e CMS)
foram omitidos; PNG/JPEG/WebP/GIF e redimensionamento continuam disponÃ­veis.

## IntegraÃ§Ãµes e portabilidade

### Descoberta local

`bib_nucleo/ferramentas.py` resolve executÃ¡veis pelo manifesto, pastas
relativas e overrides explÃ­citos. No runtime completo nÃ£o hÃ¡ fallback
silencioso para PATH ou instalaÃ§Ãµes deste PC. O checkout conserva os
fallbacks legados para continuar utilizando suas instalaÃ§Ãµes atuais.

O runtime vence a casa canÃ´nica do PC de build, mesmo sem variÃ¡vel
`BIBLIOTECA_HOME`. O manifesto Ã© local/editÃ¡vel e registra caminhos,
plataforma, versÃµes, fontes, licenÃ§as, tamanhos e hashes.

O yt-dlp usa a distribuiÃ§Ã£o zipimport oficial, de aproximadamente 3 MiB,
executada pelo Python incluÃ­do. Isso evita outro interpretador embutido
no downloader. QuickJS-NG, suportado pelo yt-dlp, fornece o runtime JS
em aproximadamente 2 MiB. Deno continua aceito como override opcional.

### qBittorrent

- Magnets abertos no Hub sÃ£o encaminhados diretamente ao cliente, sem
  depender da associaÃ§Ã£o magnet/.torrent do Windows.
- O perfil usa `dados/perfis/qBittorrent_tucoteca/`, independente do
  perfil instalado. Fast-resume usa caminhos relativos ao perfil.
- Web API ligada somente a 127.0.0.1, porta determinÃ­stica por casa.
  Origin/Referer corretos e conexÃ£o sem proxy para o endpoint local.
- O GUI exige um hash de credencial mesmo quando o localhost estÃ¡ dispensado
  de autenticaÃ§Ã£o. O bootstrap gera PBKDF2-SHA512 no formato do projeto;
  a prova nativa confirmou que a API inicia corretamente.
- Downloads mostra progresso, velocidade/ETA e pausar/retomar via API.
  Consultas HTTP sÃ£o feitas fora da thread Tk; a tela usa snapshots e nÃ£o
  repete a consulta no callback de renderizaÃ§Ã£o.
- Se a API estiver indisponÃ­vel, o histÃ³rico em arquivo continua sendo
  fallback. No checkout, o histÃ³rico instalado pode aparecer junto ao cliente
  integrado. Itens histÃ³ricos nÃ£o recebem controles de uma API que nÃ£o os possui.

## OtimizaÃ§Ãµes e correÃ§Ãµes

1. Builder novo monta perfis vazios: nÃ£o incorpora saves, mods, HD, histÃ³rico,
   configuraÃ§Ãµes pessoais, AppImage Linux ou sÃ­mbolos `.pdb` no runtime Windows.
2. 7-Zip completo: o `7z.exe` do PC carregava a DLL de outro diretÃ³rio.
   Agora a DLL acompanha o exe; seu caminho de carregamento foi confirmado.
3. **Bug crÃ­tico na dieta antiga:** `*.py[cod]` tambÃ©m correspondia a `.pyd`.
   Isso apagava SQLite/Tk e outras extensÃµes depois do selftest do builder.
   A poda agora remove apenas `.pyc/.pyo`; teste protege extensÃµes nativas.
4. Scripts oficiais Tcl/Tk jÃ¡ em cache sÃ£o reutilizados antes de tentar rede.
5. Manifesto Ã© cacheado por arquivo/mtime/tamanho, preservando ediÃ§Ã£o local.
6. Banco: evita repetir inicializaÃ§Ã£o completa em conexÃµes de um arquivo/schema
   jÃ¡ verificado. Identidade, mtime e `schema_version` invalidam o cache;
   backfill de UUID e migraÃ§Ãµes continuam sendo verificados em testes.

### Benchmark de conexÃµes

Em snapshot da coleÃ§Ã£o local, 100 conexÃµes + consulta de contagem, 3 rodadas:

- Antes: 91,74 / 96,57 / 91,63 ms.
- Depois: 57,18 / 54,10 / 52,63 ms.
- Mediana: 91,74 â†’ 54,10 ms, aproximadamente 41% menos tempo nesse cenÃ¡rio.

Ã‰ uma mediÃ§Ã£o de operaÃ§Ãµes de banco, nÃ£o uma promessa de acelerar todo o app
por esse percentual.

## VerificaÃ§Ã£o realizada

- SuÃ­te: **251 executados, 6 pulados por condiÃ§Ãµes do Windows, 0 falhas**
  (257 descobertos).
- Sintaxe/diagnÃ³stico: 61 fontes Python, banco real Ã­ntegro, 25 jogos,
  51 mÃºsicas, 4 desejos; diagnÃ³stico da coleÃ§Ã£o em somente-leitura.
- Runtime validado apÃ³s a dieta e **depois da extraÃ§Ã£o do ZIP e do 7z**,
  em diretÃ³rios diferentes, com PATH reduzido ao System32.
- Python/Tk/Pillow, criaÃ§Ã£o/leitura JPEG e PhotoImage nativos.
- FFmpeg local: versÃ£o e conversÃ£o de WAV artificial para MP3.
- yt-dlp local: execuÃ§Ã£o da versÃ£o; QuickJS: execuÃ§Ã£o de JavaScript local.
- qBittorrent local: perfil temporÃ¡rio, API de versÃ£o, torrent artificial
  com dados jÃ¡ existentes, 100%, pausa, retomada e encerramento.
- Integridade dos arquivos comprimidos e manifesto SHA-256.

As provas nÃ£o alteraram os perfis do qBittorrent instalado nem migraram a
coleÃ§Ã£o real para o pacote. O runtime comeÃ§a vazio; os dados sÃ£o transferÃ­veis
pelo pacote de coleÃ§Ã£o da prÃ³pria TucoTeca.

## PrÃ³ximas entregas possÃ­veis

1. Fila persistente de conclusÃ£o/instalaÃ§Ã£o/importaÃ§Ã£o de jogos, com idempotÃªncia
   e identificaÃ§Ã£o da pasta instalada. A importaÃ§Ã£o de concluÃ­dos ainda Ã©
   acionada explicitamente; um setup baixado nÃ£o Ã© um jogo instalado.
2. Atualizador de componentes que mantenha versÃµes/licenÃ§as/manifesto em sincronia,
   com publicaÃ§Ã£o atÃ´mica e rollback.
3. Pacotes nativos completos Linux/macOS. Os caminhos/overrides e testes de
   compatibilidade continuam funcionando, mas este artefato Ã© Windows x64.
4. Fonte FFmpeg com seleÃ§Ã£o de codecs especÃ­ficos de Ã¡udio, apÃ³s provas de
   formatos e reproduÃ§Ã£o, para reduzir ainda mais o maior sidecar.
5. Resolver metadados por pasta/manifesto/AppID e a wishlist pela API moderna.

## Reproduzir

```powershell
py -3.14 codigo/ferramentas/testes/executar.py
py -3.14 codigo/ferramentas/montar_superhub.py --formato todos
# Atualizar fontes no runtime jÃ¡ montado e repetir provas/compactaÃ§Ã£o:
py -3.14 codigo/ferramentas/montar_superhub.py --reutilizar --formato todos
```

Construir pode obter os componentes oficiais ausentes; depois de empacotado,
executar o programa e trabalhar com arquivos locais nÃ£o exige instalaÃ§Ã£o ou rede.


---

## RECONCILIACAO_GITHUB.md

# ReconciliaÃ§Ã£o do Projeto-Launcher com a TucoTeca

## Base e proveniÃªncia

O repositÃ³rio canÃ´nico Ã©
`https://github.com/Artur-Lucena/Projeto-Launcher`, mantido privado.

Na comparaÃ§Ã£o de 11/10/2026:

- `origin/main` estava em `6466dbedfb5162f7a541834ed6030de96934e95e`;
- a revisÃ£o local validada era `b35bac9ec6b31ead3e3ec70b279cf91efd59fc70`;
- os histÃ³ricos tinham raÃ­zes diferentes, sem ancestral comum;
- a contraparte local `598bff1` tinha os mesmos fontes e documentos de
  `6466dbe`, byte a byte por blob Git, exceto pelas dez capas antigas;
- depois dessa base local vieram 20 commits, incluindo os merges S0â€“S8,
  lint R4 e as correÃ§Ãµes e regressÃµes R5.

A reconciliaÃ§Ã£o parte do remoto e incorpora a linha local como segundo
histÃ³rico do merge. Nenhum commit existente Ã© reescrito. Antes dos ajustes
documentais, a Ã¡rvore resultante foi conferida contra a Ã¡rvore de `b35bac9`
(`8c93323f881473664491e68bae5c888cf9efce4d`). No commit de reconciliaÃ§Ã£o
`a50edac`, os fontes em `codigo/` sÃ£o idÃªnticos aos da R5; apenas a documentaÃ§Ã£o
dessa integraÃ§Ã£o foi atualizada.

O merge torna as duas linhas ancestrais da revisÃ£o final. Assim, `main`,
`feat/s7b`, `feat/youtube-embed`, `qa/testes` e `os/windows` podem ser alinhadas
e enviadas por push normal, sem `--force`.

## Ãrvore de fontes

```text
codigo/
  bib_core.py             fachada de compatibilidade
  bib_nucleo/             persistÃªncia, domÃ­nio e adaptadores locais
    rede/                  integraÃ§Ãµes remotas explÃ­citas
  frontends/              Qt Quick, ferramentas clÃ¡ssicas e TUI
    qml/secoes/            telas Qt Quick
  ferramentas/            diagnÃ³stico, provas e empacotamento
    testes/                fixtures sintÃ©ticas e testes em sandbox
docs/                      arquitetura, uso, revisÃµes e responsabilidades
.github/                   testes automatizados e modelos de colaboraÃ§Ã£o
```

Os sete mÃ³dulos antigos de rede nÃ£o voltam Ã  raiz de `bib_nucleo/`: suas
versÃµes atuais estÃ£o em `rede/`, com os aliases de compatibilidade existentes.
`docs/organizacao-local.json` permanece inalterado: registra movimentos antigos
de artefatos locais e nÃ£o define o comportamento do organizador de jogos.

## O que pode ser enviado

Somente o projeto necessÃ¡rio para desenvolver, testar e empacotar o launcher:
fontes Python/QML, documentaÃ§Ã£o, licenÃ§a, launchers, dependÃªncias declaradas,
configuraÃ§Ã£o de testes e empacotadores.

NÃ£o enviar:

- `dados/`, bancos SQLite, saves, perfis pessoais ou marcadores de sessÃµes;
- executÃ¡veis de jogos, ROMs, mÃºsicas ou vÃ­deos da coleÃ§Ã£o;
- `programa/`, runtimes locais, `dist/`, ZIPs ou backups pessoais;
- `.provas/`, `.build/`, `.cache/`, `codigo/historico/` e atalhos `.lnk`;
- credenciais, tokens ou arquivos de configuraÃ§Ã£o de provedores pessoais.

A Ã¡rvore atual e os objetos dos dois histÃ³ricos sÃ£o conferidos antes do push,
alÃ©m da varredura de segredos. Os testes usam arquivos sintÃ©ticos; a integraÃ§Ã£o
nÃ£o executa jogos nem modifica a instalaÃ§Ã£o pessoal, coleÃ§Ã£o ou atalho.

## Imagens histÃ³ricas

As dez capas comerciais do remoto antigo ficam fora da Ã¡rvore final.
Preservar o histÃ³rico significa preservar tambÃ©m seus blobs antigos; este
merge nÃ£o apaga conteÃºdo histÃ³rico. NÃ£o hÃ¡ novas capas comerciais no envio
dos fontes atuais. O gerador de placeholders neutros continua disponÃ­vel
opcionalmente, sem exigir uma pasta `midia/` em um clone limpo.

## ValidaÃ§Ã£o e artefatos de release

A referÃªncia R5 tinha 413 testes aprovados, seis pulos por ambiente e zero
falhas, com 63% de cobertura real dos subprocessos e Ruff configurado limpo.
Os gates sÃ£o repetidos sobre a Ã¡rvore reconciliada antes do envio.

Os empacotadores e instruÃ§Ãµes do [README](../README.md) continuam sendo a
entrada para preparar releases. Fazer push dos fontes nÃ£o anexa runtimes nem
cria uma release automaticamente. A compilaÃ§Ã£o deve comeÃ§ar com dados/perfis
vazios e seguir as licenÃ§as dos componentes de terceiros.

Os ZIPs R5 em `dist/marco-s0-s8/r5/` permanecem apenas locais, associados a
`b35bac9`. NÃ£o devem ser apresentados como builds de um commit posterior
sem nova geraÃ§Ã£o e validaÃ§Ã£o.

## Release privada v1.0.1

A release Ã© montada a partir de uma revisÃ£o congelada por
`codigo/ferramentas/preparar_release.py`, que reÃºne pacote de fontes, bundles
Windows jÃ¡ validados, relatÃ³rios de verificaÃ§Ã£o, notas e checksums. Nada Ã©
publicado automaticamente: criar a release no GitHub Ã© passo explÃ­cito, com o
repositÃ³rio privado, e sem coleÃ§Ã£o, jogos, saves ou perfis pessoais.
Os runtimes de terceiros ficam apenas nos anexos autorizados, com licenÃ§as;
nÃ£o entram na Ã¡rvore Git. A proveniÃªncia de cada bundle fica registrada no
`manifesto-runtime.json` (`versoes.revisao_git`, `versoes.tucoteca`) e conferida por SHA-256
no builder e na preparaÃ§Ã£o da release.

A tag `v1.0.0` aponta para `853c9a0` e permanece intacta; a CI dessa revisÃ£o
passou, mas a preparaÃ§Ã£o revelou falhas antes da publicaÃ§Ã£o dos anexos.
Por autorizaÃ§Ã£o do proprietÃ¡rio, a primeira release publicada passa a ser
`v1.0.1`, com fontes e bundles da revisÃ£o corrigida. NÃ£o houve exclusÃ£o ou
movimentaÃ§Ã£o da tag antiga. Fluxo completo: [RELEASES.md](RELEASES.md).

## Complemento: portabilidade dos testes na CI

A primeira execuÃ§Ã£o da `main` em `a50edac` foi
[38152335953](https://github.com/Artur-Lucena/Projeto-Launcher/actions/runs/38152335953).
Qt Linux e Gitleaks passaram; os quatro jobs stdlib e Qt Windows apontaram
quatro pressupostos dos testes: tamanho mÃ¡ximo do desktop virtual, ausÃªncia
de gerenciador de janelas no Xvfb, largura fixa em vez da largura disponÃ­vel
da sidebar e resoluÃ§Ã£o de symlinks em loop ao removÃª-los no Python 3.10.

O complemento altera apenas o harness, testes e configuraÃ§Ã£o de CI. As
asserÃ§Ãµes de fullscreen/layout sÃ£o mantidas, com espera limitada; Openbox
fornece fullscreen real no Linux. O sandbox verifica os pais resolvidos ao
remover uma entrada, mas continua seguindo o alvo de escritas e SQLite.
Quatro testes adicionais garantem remoÃ§Ã£o segura e veto a escapes, inclusive
por `..` ou links nos pais, sem realizar operaÃ§Ãµes reais fora do sandbox.
Outro teste simula explicitamente o mÃ¡ximo de um desktop de 1024Ã—768 para
garantir que ele nÃ£o limite as geometrias da prova visual.

Os fontes de runtime e os artefatos R5 nÃ£o mudam; a instalaÃ§Ã£o pessoal nÃ£o
recebe esse complemento de infraestrutura de testes.

Gates locais do complemento: runner com 424 casos, zero falhas e seis pulos;
pytest com 418 testes aprovados, seis pulos e 63% de cobertura real. Ruff
configurado, actionlint 1.7.12 e Gitleaks limpos. A conclusÃ£o da execuÃ§Ã£o remota
deve ser conferida no GitHub Actions, nÃ£o presumida a partir desses gates.


---

