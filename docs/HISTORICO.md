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


## INDICE.md

# Ãndice da documentaÃ§Ã£o

Mapa por tema dos documentos em `docs/`. Comece por `ARQUITETURA.md` para
se localizar; o fluxo de colaboraÃ§Ã£o estÃ¡ em `docs/CONTRIBUTING.md`.

## Mapa e interface

- [ARQUITETURA.md](ARQUITETURA.md) â€” mapa de pastas, responsabilidade por
  mÃ³dulo, modelo de dados, fluxos, concorrÃªncia e variÃ¡veis de ambiente.
- [DESKTOP_QT.md](DESKTOP_QT.md) â€” decisÃ£o Qt Quick, cobertura por fluxo,
  contratos de integraÃ§Ã£o, concorrÃªncia e limites da etapa (A1).
- [DESKTOP_ELECTRON.md](DESKTOP_ELECTRON.md) â€” desktop Electron em construÃ§Ã£o
  (fatia F0): ponte NDJSON, contrato de mÃ³dulos, seguranÃ§a e provas.
- [INTEGRACOES.md](INTEGRACOES.md) â€” como adicionar uma integraÃ§Ã£o ao hub
  (contrato, template e testes).
- [VISAO_OS.md](VISAO_OS.md) â€” visÃ£o TucoOS: o Hub como shell pessoal,
  sem reescrita do domÃ­nio.

## Releases e legal

- [RELEASES.md](RELEASES.md) â€” como congelar, gerar bundles, preparar
  anexos e publicar uma release privada (coordenador).
- [LEGAL.md](LEGAL.md) â€” aviso legal e responsabilidades de uso.
- [RECONCILIACAO_GITHUB.md](RECONCILIACAO_GITHUB.md) â€” proveniÃªncia do
  histÃ³rico reconciliado com o remoto e o que nunca vai ao GitHub.

## RevisÃµes tÃ©cnicas (registro histÃ³rico)

- [REVISAO_TECNICA.md](REVISAO_TECNICA.md) â€” auditoria de cÃ³digo de
  06â€“07/10/2026: 20 erros comprovados e corrigidos.
- [REVISAO_LINUX_W11.md](REVISAO_LINUX_W11.md) â€” revisÃ£o Linux feita no
  Windows 11: correÃ§Ãµes verificadas e matriz de compatibilidade por SO.
- [PARTE1_VISUAL_E_AUDITORIA.md](PARTE1_VISUAL_E_AUDITORIA.md) â€” acabamento
  visual Tk e auditoria de 09/10/2026.
- [PARTE2_RUNTIME_E_INTEGRACOES.md](PARTE2_RUNTIME_E_INTEGRACOES.md) â€” runtime
  independente, otimizaÃ§Ã£o e tamanhos medidos dos artefatos.
- [QOL_1_5.md](QOL_1_5.md) â€” qualidade de vida 1.5 do desktop Qt (10/10/2026).
- [INTEGRACAO_FINAL_QOL_MIDIAS.md](INTEGRACAO_FINAL_QOL_MIDIAS.md) â€”
  consolidaÃ§Ã£o de 11/10/2026 das frentes QoL 1.5 e mÃ­dias 2.0 no Qt.

## Dados

- [organizacao-local.json](organizacao-local.json) â€” registro histÃ³rico de
  09/10/2026 dos movimentos de artefatos em `dist/`; nÃ£o Ã© substituto de
  `organizacao_local.py`.


---

## INTEGRACAO_FINAL_QOL_MIDIAS.md

# IntegraÃ§Ã£o final â€” QoL 1.5 e mÃ­dias 2.0

11/10/2026. IntegraÃ§Ã£o das duas frentes depois de pausar a Ã¡rvore compartilhada.
Novas telas e aÃ§Ãµes foram implementadas somente no desktop Qt. O cÃ³digo legado
tkinter foi preservado como recebido da etapa anterior.

## Entregas consolidadas

- MÃºsica: Deezer, iTunes e MusicBrainz sem credencial; Spotify no mesmo modelo
  de resultados, inclusive playlists/curtidas e paginaÃ§Ã£o. Erro de pesquisa
  aparece inline e deixa de ficar eternamente em â€œBuscandoâ€.
- OAuth Spotify: uma Ãºnica funÃ§Ã£o de extraÃ§Ã£o; aceita retorno completo do
  callback ou cÃ³digo puro inteiro. NÃ£o aceita prefixo de texto invÃ¡lido.
- Conquistas: IDs oficiais e referÃªncia pÃºblica em listas separadas. Percentuais
  globais jamais sÃ£o identificadores. CorrespondÃªncia usa definiÃ§Ã£o local
  verificÃ¡vel; save e regras do Hub determinam o desbloqueio offline.
- Videoteca Qt: importaÃ§Ã£o local, busca/download YouTube, reprodutor
  automÃ¡tico/VLC/MPV/MPC-HC e Ctrl+7. HUD adaptativo mantÃ©m as sete categorias.
- MÃ­dias: painel de detecÃ§Ã£o/abertura de imagem, Ã¡udio e vÃ­deo; EQ produz uma
  cÃ³pia importada como mÃºsica, com backup e original preservado.
- Downloads: publicaÃ§Ã£o atÃ´mica, tratamento de fragmentos, deadline de processo,
  reaproveitamento de vÃ­deos existentes e retomada de conversÃ£o sem rebaixar Ã¡udio.
- Jogos: `Piratas/` como diretÃ³rio do runtime portÃ¡til; qBittorrent recebe
  savepath explÃ­cito e autoTMM desligado. O cliente nÃ£o Ã© considerado bem-sucedido
  se recusar a adiÃ§Ã£o. ConfiguraÃ§Ã£o prÃ©-migraÃ§Ã£o ganha backup.
- Hell Clock: instalaÃ§Ã£o movida de `D:\Games\Hell Clock` para
  `D:\Games\Piratas\Hell Clock`; entrada 51 atualizada; 372 arquivos conferidos
  por SHA-256. Junction no caminho antigo mantÃ©m referÃªncias externas.
- Frente Linux preservada: descoberta por SO/permissÃ£o, programas exclusivos
  Windows, DeSmuME, AppImage, Wine, players, progresso e instalador/shell.

## VerificaÃ§Ãµes

- **358 casos: 352 PASS, 6 SKIP por ambiente, 0 FAIL**.
- Inclui carga de 1.000 arquivos/128 conteÃºdos, 20.000 linhas de progresso,
  filhos sem stdout, timeout/recolhimento, falha de banco/disco, GUI e cache.
- Auditoria visual: sete seÃ§Ãµes em 1440Ã—920 e 960Ã—640; diÃ¡logos de mÃºsica,
  YouTube, ferramentas e integraÃ§Ã£o; zero erro QML crÃ­tico.
- Selftest Qt: **26 jogos**. Banco da coleÃ§Ã£o preservado durante a auditoria,
  conferido por SHA-256; organizaÃ§Ã£o do Hell Clock foi uma aÃ§Ã£o separada com backup.
- Testes do novo painel de mÃ­dia simulam a abertura dos programas; nÃ£o lanÃ§am
  jogos ou Ã¡udio. Os adaptadores nÃ£o instalam automaticamente os nove programas.
- O login de conta Spotify requer configuraÃ§Ã£o/consentimento reais. Testes de
  protocolo e catÃ¡logo autenticado sÃ£o simulados; bibliotecas pÃºblicas funcionam
  sem esse login. NÃ£o se trata de extrair streams Spotify.
- Linux nativo/macOS ainda dependem de validaÃ§Ã£o no sistema real; ver
  [revisÃ£o Linux/W11](REVISAO_LINUX_W11.md).

RelatÃ³rios de mÃ¡quina ficam em `IA/TucoTeca/validacao/`; dados pessoais,
credenciais, saves e arquivos baixados permanecem fora do Git.

## Git

O checkout canÃ´nico Ã© `Jogos/biblioteca/`, remoto
`https://github.com/Artur-Lucena/Projeto-Launcher.git`. A pasta de sessÃ£o
`IA/TucoTeca/` tem outro Git local sem remoto; `projeto/` e `Git-Projeto.bat`
dÃ£o acesso ao checkout canÃ´nico. O atraso observado era de commits/alteraÃ§Ãµes
nÃ£o publicados, e nÃ£o perda do repositÃ³rio por mudanÃ§a de pastas.


---

## QOL_1_5.md

# QoL 1.5

ContinuaÃ§Ã£o do desktop Qt/QoL 1.0. SessÃ£o de 10/10/2026; cada tÃ³pico tem
seu decimal. A coleÃ§Ã£o usada na validaÃ§Ã£o visual foi copiada para uma casa
temporÃ¡ria: 25 jogos, 51 mÃºsicas e 4 desejos.

## Entregas

| TÃ³pico | Resultado |
|---|---|
| **1.5.1 â€” Git acessÃ­vel** | Na raiz da sessÃ£o, `projeto/` liga ao checkout real, incluindo `.git`. `Git-Projeto.bat` mostra branch, alteraÃ§Ãµes e commits a cada 3s. |
| **1.5.2 â€” Pesquisa de integraÃ§Ãµes** | Fontes oficiais conferidas; prioridades e limitaÃ§Ãµes abaixo. |
| **1.5.3 â€” Legibilidade** | InformaÃ§Ãµes secundÃ¡rias de 13â€“14px, badges de 12px e tÃ­tulos de cards de 15px. Tokens no tema. |
| **1.5.4 â€” Varredura** | Achados e sugestÃµes priorizados; os ajustes imediatos geraram os tÃ³picos seguintes. |
| **1.5.5 â€” SaÃºde real da coleÃ§Ã£o** | DiagnÃ³stico de todos os jogos; resumo limitado sem distorcer os totais. `+N outros` e filtro de pendÃªncias. Resultado antigo de worker nÃ£o substitui a saÃºde da recarga mais recente. |
| **1.5.6 â€” Busca e filtros** | `N de total Â· filtro Â· busca`, Limpar filtros, seleÃ§Ã£o correta pela paleta em jogos/desejos/downloads, ordenaÃ§Ã£o sincronizada e Ctrl+F funcionando nas telas iniciais. Primeira faixa marcada corretamente na fila de Ã¡udio. |
| **1.5.7 â€” Avisos em fila** | FIFO: cada aviso mantÃ©m texto e severidade, permanece 7s e pode ser fechado pelo botÃ£o Ã—. |
| **1.5.8 â€” InformaÃ§Ãµes e layout** | Idade/estado do backup separados; cor Ã¢mbar para backup ausente ou com â‰¥7 dias. CabeÃ§alho cabe nas larguras 960/1200/1440; cards compactos preservam status/horas. Selftest imprime o total de jogos da coleÃ§Ã£o. |
| **1.5.9 â€” Horas e sessÃµes** | Registrar horas no drawer; decimal com vÃ­rgula ou ponto. SessÃ£o pendente usa o banco correto, faz backup do banco e do marcador, soma as horas e encerra a pendÃªncia. Tentativa repetida nÃ£o soma novamente. |
| **1.5.10 â€” Conquistas sem login** | CatÃ¡logo pÃºblico de nomes/descriÃ§Ãµes/Ã­cones salvo separadamente dos IDs. Metadados vinculados somente por tÃ­tulo/Ã­cone declarado em definiÃ§Ã£o local; percentuais nunca identificam conquistas. Chave Steam opcional para o schema completo. Desbloqueios calculados no save local. |
| **1.5.11 â€” Spotify funcional** | Busca pÃºblica (faixas/Ã¡lbuns/playlists) com Client ID + Secret, sem login; conta sÃ³ p/ playlists e curtidas. Colar cÃ³digo manual quando o loopback falha; erros orientam (redirect/secret/porta). ConteÃºdo continua via downloader local. |
| **1.5.12 â€” Adicionar integraÃ§Ã£o** | BotÃ£o + Adicionar nas IntegraÃ§Ãµes: atalho https persistido na coleÃ§Ã£o (tipos link/catÃ¡logo/emulador/download, `{q}` p/ busca). PadrÃµes protegidos; sem plugins arbitrÃ¡rios. |
| **1.5.13 â€” Piratas padrÃ£o** | Magnets vÃ£o ao qBittorrent do Hub (savepath Piratas/, categoria tucoteca) em Qt/clÃ¡ssico/TUI; perfil antigo migra o DefaultSavePath; import clÃ¡ssico e botÃ£o Organizar movem o que caiu fora (caso Hell Clock). |
| **1.5.14 â€” Bibliotecas sem credencial** | Busca de faixas em Deezer, iTunes e MusicBrainz, seleÃ§Ã£o e envio Ã  fila; cache e erro inline. Spotify integrado no mesmo modelo, inclusive playlists, com OAuth para dados da conta. |
| **1.5.15 â€” IntegraÃ§Ã£o de mÃ­dias Qt** | Aba VÃ­deos, importaÃ§Ã£o local, pesquisa/download YouTube, seleÃ§Ã£o VLC/MPV/MPC-HC e painel para Krita/GIMP/PhotoDemon, Audacity/APO/Peace. EQ gera cÃ³pia importada. Integra a frente 2.0 e a revisÃ£o de portabilidade do outro chat. |

O Hell Clock instalado foi efetivamente organizado em `D:\Games\Piratas\Hell Clock`;
entrada 51 atualizada, backup do banco e 372 arquivos conferidos por SHA-256.
Uma junction no caminho anterior preserva atalhos/configuraÃ§Ãµes existentes.
No runtime portÃ¡til, a pasta padrÃ£o de jogos passa a ser `Piratas/` dentro da casa.

## IntegraÃ§Ãµes pesquisadas

MusicBrainz/CAA, SteamGridDB e os adaptadores de mÃ­dia foram integrados;
os programas externos devem estar instalados/configurados. As demais linhas
abaixo registram a pesquisa e o backlog.

| Prioridade | IntegraÃ§Ã£o e fonte oficial | BenefÃ­cio / encaixe |
|---|---|---|
| Alta | [Ludusavi](https://github.com/mtkennerly/ludusavi) â€” MIT | Preview/backup de saves PC e registro Windows; CLI com JSON. Complementa o backup do catÃ¡logo. |
| Alta | [MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_API) + [Cover Art Archive](https://musicbrainz.org/doc/Cover_Art_Archive/API) | Identificar Ã¡lbuns e complementar capas; consultas pÃºblicas sem chave, com cache e limite de 1 chamada/s ao MusicBrainz. |
| Alta | [SDL GameControllerDB](https://github.com/mdqinc/SDL_GameControllerDB) â€” zlib | Base comunitÃ¡ria de mapas, a usar junto de um backend de entrada para navegaÃ§Ã£o por controle. |
| MÃ©dia | [SteamGridDB](https://github.com/SteamGridDB/node-steamgriddb) | Galeria de pÃ´steres e arte por AppID/tÃ­tulo; API com chave. Clientes abertos, serviÃ§o/arte com condiÃ§Ãµes prÃ³prias. |
| MÃ©dia | [PCGamingWiki](https://github.com/PCGamingWiki/api) / [ProtonDB](https://www.protondb.com/) | Links de suporte/compatibilidade por AppID. Um primeiro passo simples antes de cachear metadados. |
| MÃ©dia | [Heroic](https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher) / [Lutris](https://github.com/lutris/lutris) | ImportaÃ§Ã£o dos instalados e lanÃ§amento por runner externo. |
| Opcional | [pypresence](https://github.com/qwertyquerty/pypresence) | Rich Presence; requer cliente Discord e App ID. |
| Condicional | [RetroAchievements](https://docs.retroachievements.org/general/emulator-support-and-issues.html) | A documentaÃ§Ã£o lista DeSmuME **core libretro**, nÃ£o o standalone atual; nÃ£o confirma Azahar/3DS. Exige compatibilidade do emulador para desbloquear conquistas. |

HowLongToBeat ficou em prioridade menor: wrappers comunitÃ¡rios nÃ£o comprovam
uma API oficial estÃ¡vel. A licenÃ§a MIT anteriormente atribuÃ­da ao redirect
PCGamingWiki nÃ£o foi confirmada (`license: null` nos metadados consultados).

## PrÃ³ximas sugestÃµes de QoL

1. **Escala de texto configurÃ¡vel**, com reflow e validaÃ§Ã£o das trÃªs larguras.
2. **Arrastar pasta/arquivo para importar**, com preview e confirmaÃ§Ã£o dos itens.
3. **DuraÃ§Ã£o das mÃºsicas e progresso do player**, com metadados cacheados.
4. **PreÃ§os/descontos nos Desejos**, com paÃ­s/moeda e consulta sob demanda.
5. **Downloads: recebido/total e espaÃ§o restante**, mantendo clara a origem do progresso.
6. **Gamepad no Big Picture**, incluindo hotplug e repetiÃ§Ã£o do direcional.
7. **Lixeira/desfazer**, cobrindo banco, capas e arquivos gerenciados.

## ValidaÃ§Ã£o

- SuÃ­te integrada: **352 PASS, 6 SKIP, 0 FAIL â€” 358 casos** no Windows.
- `py_compile` dos Python alterados; `git diff --check` sem problemas.
- Auditoria em **1440Ã—920 e 960Ã—640** nas sete seÃ§Ãµes, incluindo VÃ­deos,
  mais mÃºsica/YouTube/ferramentas/integraÃ§Ãµes; nenhum erro QML crÃ­tico.
- Selftest Qt: **26 jogos**. Banco original preservado, comprovado por SHA-256.
- As estatÃ­sticas globais nÃ£o comprovam vÃ­nculo de metadados: a afirmaÃ§Ã£o
  anterior â€œ49/49 vinculados por percentualâ€ foi corrigida. Lista pÃºblica
  disponÃ­vel sem login; vÃ­nculo com ID exige definiÃ§Ã£o verificÃ¡vel.
- Testes de carga incluÃ­dos: 1.000 arquivos/128 conteÃºdos distintos,
  20.000 linhas de progresso, processos sem stdout e timeout, falhas de banco,
  callbacks, cache offline, dados invÃ¡lidos, UI e imports entre as duas frentes.
- Testes usam dados/Ã¡udio/processos simulados; capturas usam a cÃ³pia temporÃ¡ria.
- Login real Spotify requer Client ID/autorizar a conta; protocolo e catÃ¡logo
  autenticado foram testados em sandbox. Busca das bibliotecas pÃºblicas foi
  comprovada sem credenciais. Linux nativo/macOS ainda exigem prova no SO real.

RelatÃ³rios locais: `IA/TucoTeca/validacao/integracao-final-testes.json`,
`hell-clock-organizacao.json` e `qol-1.5-visual.json`. Pesquisa detalhada e notas de sessÃ£o
em `IA/TucoTeca/sessao/`. As capturas ficam no diretÃ³rio temporÃ¡rio indicado
no relatÃ³rio visual.


---

## REVISAO_LINUX_W11.md

# RevisÃ£o Linux feita no Windows 11

Data: 10/10/2026. Python oficial 3.14, Git Bash e FFmpeg local.

Esta revisÃ£o combina inspeÃ§Ã£o dos ramos Linux, testes hermÃ©ticos com SO,
PATH e sinais simulados, execuÃ§Ã£o real dos scripts shell em uma sandbox e
processamento real de Ã¡udio sintÃ©tico. O WSL nÃ£o estÃ¡ instalado nesta mÃ¡quina:
nenhum resultado abaixo Ã© apresentado como validaÃ§Ã£o de kernel, GPU, Ã¡udio
ou sessÃ£o grÃ¡fica Linux.

## CorreÃ§Ãµes verificadas

| Ãrea | Problema confirmado | CorreÃ§Ã£o |
|---|---|---|
| Ferramentas | Override/manifesto podiam escolher `.exe` no Linux; arquivo sem permissÃ£o de execuÃ§Ã£o aparecia disponÃ­vel | Descoberta comum verifica SO e `X_OK`; `.py/.pyz` usam Python, sem exigir chmod |
| IntegraÃ§Ãµes 2.0 | Buscas locais percorriam Program Files inteiro e podiam ignorar o isolamento do portÃ¡til | Caminhos conhecidos, sem busca recursiva; portÃ¡til usa apenas componentes locais e overrides explÃ­citos |
| Players de vÃ­deo | Pedido de MPC-HC no Linux devolvia o executÃ¡vel do MPV | Identidade preservada; MPC-HC indicado como exclusivo do Windows |
| Equalizadores | APO/Peace eram tratados como editores de MP3 e como programas nativos de outros SOs | Abrem painÃ©is de saÃ­da no Windows; ediÃ§Ã£o de arquivos usa Audacity/Tenacity |
| EQ por arquivo | Erro de permissÃ£o ao criar o destino podia escapar; capas de Ã¡lbum podiam entrar no mapeamento FFmpeg | Retorno de erro orientado, publicaÃ§Ã£o atÃ´mica e mapeamento apenas do primeiro fluxo de Ã¡udio |
| DeSmuME | `--windowed-fullscreen` do Windows tambÃ©m era passado Ã  build Linux | Sem flags por padrÃ£o no Linux/macOS; override explÃ­cito preservado |
| DeSmuME | `/usr/games` nem sempre estÃ¡ no PATH | Busca explÃ­cita de `desmume` e `desmume-cli` nessa pasta |
| Azahar | Descoberta dependia da caixa do nome/extensÃ£o do AppImage | Busca sem depender de caixa, inclusive em filesystem case-sensitive |
| Player Linux/macOS | Pausar duas vezes alterava a contagem; parar um processo suspenso podia depender de kill e nÃ£o o recolhia | Pausa idempotente; retoma antes de terminar e executa wait apÃ³s kill |
| Downloads | Leitura de stdout podia bloquear antes do `wait(timeout)` | Leitor dedicado, fila limitada e prazo total; encerra/recolhe o filho e, no Linux, o grupo com FFmpeg |
| VÃ­deos | Falhas deixavam fragmentos; falha de banco podia deixar arquivo Ã³rfÃ£o | Staging descartÃ¡vel, publicaÃ§Ã£o apÃ³s sucesso e limpeza do arquivo novo em falha |
| ImportaÃ§Ã£o local | Origem podia mudar entre o hash e a cÃ³pia | Confere SHA-256 da cÃ³pia antes de publicar; falha nÃ£o gera registro/arquivo parcial |
| Torrents | `.fastresume` gravado no Windows mantinha destino Windows no dual boot | Traduz o destino para o SO atual antes de medir arquivos no disco |
| Launcher | Script Linux sobrescrevia `BIBLIOTECA_HOME` informado pelo desenvolvedor | Override preservado, argumentos com espaÃ§os mantidos |
| Instalador | Ajuda dizia `--destino DIR`, mas sÃ³ `--destino=DIR` era aceito | Aceita ambos, rejeita opÃ§Ã£o desconhecida e argumento ausente |
| Atalho | Caminhos com espaÃ§os, `%`, `$`, `&` ou aspas nÃ£o eram escapados corretamente | GeraÃ§Ã£o conforme Desktop Entry, sem interpolaÃ§Ã£o por sed |
| DesinstalaÃ§Ã£o | Atalho root/usuÃ¡rio era removido do lugar errado | Grava o caminho do atalho criado; preserva dados salvo com `--tudo` |
| Bundle gerado no Windows | Arquivos de controle poderiam sair em CRLF, inclusive o caminho usado na remoÃ§Ã£o do atalho | GeraÃ§Ã£o explÃ­cita com LF |
| TUI | InstruÃ§Ãµes listavam atalhos antigos; selftest dependia de curses real; menu vazio/terminal fechado nÃ£o tinham saÃ­da adequada | Ajuda descreve menus atuais; selftest simulado sem curses; casos vazios/fechamento retornam normalmente |

## Compatibilidade das integraÃ§Ãµes

â€œIntegradoâ€ significa localizar/configurar/abrir a ferramenta externa; nÃ£o
significa que seu binÃ¡rio estÃ¡ instalado ou incluÃ­do automaticamente.

| Programa/recurso | Windows | Linux | macOS |
|---|---|---|---|
| Krita / GIMP | Nativo | Nativo | Nativo |
| PhotoDemon | Nativo | Sem integraÃ§Ã£o nativa | Sem integraÃ§Ã£o nativa |
| Audacity / Tenacity | Nativo | Nativo | Nativo |
| Equalizer APO / Peace | EQ da saÃ­da do sistema | Sem integraÃ§Ã£o nativa | Sem integraÃ§Ã£o nativa |
| Presets FFmpeg do Hub | Exigem FFmpeg | Exigem FFmpeg | Exigem FFmpeg |
| VLC / MPV | Nativo | Nativo | Nativo |
| MPC-HC | Nativo | Sem integraÃ§Ã£o nativa | Sem integraÃ§Ã£o nativa |
| Busca/download YouTube | Exige yt-dlp | Exige yt-dlp | Exige yt-dlp |

PhotoDemon Ã© um projeto independente; nÃ£o Ã© Photoshop descompilado.
Peace usa **GPL-2.0**, conforme a [pÃ¡gina oficial no SourceForge](https://sourceforge.net/projects/peace-equalizer-apo-extension/).
O endereÃ§o de referÃªncia do APO Ã© [SourceForge](https://sourceforge.net/projects/equalizerapo/).
As flags comuns do DeSmuME Linux sÃ£o documentadas nas manpages
[desmume](https://manpages.debian.org/bookworm/desmume/desmume.1.en.html) e
[desmume-cli](https://manpages.debian.org/bookworm/desmume/desmume-cli.1.en.html).

## ConfiguraÃ§Ã£o Linux

`BIBLIOTECA_HOME` aponta para a **pasta-mÃ£e de `dados/`**. Os overrides de
ferramenta apontam para um arquivo executÃ¡vel, nÃ£o para uma pasta nem para
uma sequÃªncia de comandos. Para AppImage, aponte o arquivo e habilite execuÃ§Ã£o:

```sh
chmod +x "$HOME/Aplicativos/Krita.AppImage"
export BIBLIOTECA_KRITA="$HOME/Aplicativos/Krita.AppImage"
export BIBLIOTECA_VLC="/usr/bin/vlc"
```

No checkout, ferramentas instaladas no PATH podem ser usadas. No runtime
portÃ¡til, coloque-as em `ferramentas/<programa>/` ou configure o override.
Scripts/zipapps Python sÃ£o iniciados com o Python do Hub. Ferramentas sem
suporte nativo informam `suportado=false` nos contratos de status.

No Debian/Ubuntu, ferramentas comuns podem ser instaladas pelo gerenciador
da distribuiÃ§Ã£o, por exemplo:

```sh
sudo apt install python3 python3-tk ffmpeg mpv vlc krita gimp audacity desmume
```

`yt-dlp` e emuladores variam de versÃ£o entre distribuiÃ§Ãµes. O Hub usa a
instalaÃ§Ã£o localizada ou o override, e informa a dependÃªncia ausente.
DeSmuME Linux nÃ£o tem updater automÃ¡tico neste Hub. O EQ por arquivo exige
FFmpeg e produz uma cÃ³pia; nÃ£o altera o equalizador da saÃ­da do sistema.

## Como repetir as verificaÃ§Ãµes

Resultado final no W11: **355 casos, 349 aprovados, 6 pulados por ambiente,
0 falhas**. A suÃ­te percorreu banco/backup, scanners/ROMs, mods/texturas,
controles, mÃºsica/Spotify, vÃ­deo, torrents, conquistas, Qt, ferramentas
clÃ¡ssicas, TUI e instaladores. Os selftests TUI e clÃ¡ssico tambÃ©m passaram
numa casa temporÃ¡ria; o diagnÃ³stico somente-leitura confirmou integridade
SQLite, exports e sintaxe compatÃ­vel com Python 3.10.

Durante a execuÃ§Ã£o, quatro expectativas antigas foram corrigidas: trÃªs
associavam IDs de conquistas a percentuais globais, e uma confundia a URI
estÃ¡vel da mÃºsica com sua URL. As regressÃµes agora exigem vÃ­nculo local
verificÃ¡vel nas conquistas e preservaÃ§Ã£o da identidade do catÃ¡logo na fila.

RelatÃ³rio estruturado desta execuÃ§Ã£o:
`%TEMP%/opencode/suite-auditoria-linux-w11.json`.

Windows, na raiz do projeto:

```powershell
py -3.14 -B codigo/ferramentas/testes/executar.py --modulo test_linux_portabilidade
py -3.14 -B codigo/ferramentas/provar_linux_shell.py --ffmpeg
py -3.14 -B codigo/ferramentas/diagnosticar.py --json
```

No Linux, troque `py -3.14` por `python3`. A prova shell usa Bash nativo se
ele estiver no PATH. Sem `--ffmpeg`, testa apenas launchers/instalador.
A CI inclui a prova shell nos jobs Ubuntu, alÃ©m da suÃ­te principal.

Para testar o selftest numa coleÃ§Ã£o descartÃ¡vel:

```sh
export BIBLIOTECA_HOME="$(mktemp -d)"
python3 codigo/frontends/app_tui.py --selftest
```

`diagnosticar.py` abre SQLite em modo somente-leitura e nÃ£o migra o banco.
Os testes usam sandboxes prÃ³prias. A prova shell gera e instala um pacote
mÃ­nimo descartÃ¡vel; a prova FFmpeg usa WAV sintÃ©tico e nÃ£o reproduz Ã¡udio.

### Cobertura adicional

- 26 regressÃµes em `test_linux_portabilidade.py`, executÃ¡veis tambÃ©m no W11.
- ImportaÃ§Ã£o de 1.000 arquivos, 128 conteÃºdos distintos: SHA-256, dedup,
  reimportaÃ§Ã£o e integridade SQLite verificados.
- 20.000 linhas de progresso com callback falhando periodicamente.
- Filho sem stdout, timeout, terminate/kill/wait e grupo de processos Linux.
- Falhas de banco, disco/permissÃ£o e arquivo de origem modificado.
- ExecutÃ¡veis, zipapps, Wine, AppImage, terminal fechado e TUI sem curses.
- Prova real: sintaxe de 4 scripts, 2 launchers, dois formatos de destino,
  instalaÃ§Ã£o/desinstalaÃ§Ã£o com caracteres especiais e 6 presets FFmpeg.

## ValidaÃ§Ã£o ainda necessÃ¡ria num Linux real

Executar a suÃ­te e a prova shell em Linux; abrir Qt/TUI em sessÃ£o grÃ¡fica e
terminal reais; testar Ã¡udio com PulseAudio/PipeWire, pausa/retomada e fim
natural; executar um jogo Wine e uma ROM prÃ³pria no Azahar/DeSmuME; conferir
saves, GPU, FUSE/AppImage e permissÃµes do volume compartilhado; abrir os
programas de mÃ­dia nativos e verificar o atalho pelo menu do desktop.

Esses pontos dependem do sistema anfitriÃ£o e nÃ£o sÃ£o comprovados pela
simulaÃ§Ã£o Windows nem pelo Git Bash.


---

## REVISAO_TECNICA.md

# RevisÃ£o tÃ©cnica â€” TucoTeca (06â€“07/10/2026)

Auditoria de cÃ³digo, estrutura e empacotamento para trabalho em conjunto.
Base: Ã¡rvore de trabalho em `98dccd1` + alteraÃ§Ãµes desta revisÃ£o (nÃ£o
commitadas â€” ver `git status`). ValidaÃ§Ã£o: suÃ­te **221/221** + selftest.

## 1. MÃ©todo e evidÃªncia

- Varredura `ast` de 48 arquivos Python (~22 mil linhas, 288 exports):
  sem definiÃ§Ãµes duplicadas, sem `__all__` duplicado, sem chamada
  `self.*` sem mÃ©todo correspondente nas classes `App`/`Tui`, sem
  colisÃ£o de exports entre mÃ³dulos (sÃ³ `titulo_ok`, mesmo objeto).
- Rede, subprocessos e escrita fora da sandbox sÃ£o bloqueados pelo
  audit-hook de `executar.py`; cada `teste_*` roda em subprocesso
  e diretÃ³rio prÃ³prios. Pulos por SO/display aparecem como `SKIP`.
- `diagnosticar.py` (somente-leitura) confere sintaxe, exports,
  dependÃªncias, mapa de pastas e integridade do SQLite sem migrar o banco.
- `empacotar_fontes.py` gera `dist/tucoteca-fontes-revisadas.zip` com a
  Ã¡rvore atual + manifesto SHA-256, excluindo coleÃ§Ã£o, caches e builds.

## 2. Erros comprovados e corrigidos

| # | Achado | Prova | CorreÃ§Ã£o |
|---|---|---|---|
| 1 | `importar_musicas` retornava `ignorados`, mas o contrato documentado e lido pela GUI/TUI Ã© `ignoradas` (`res['ignoradas']` em `app_win.py`, `app_tui.py`, `test_baixar.py`) â€” `KeyError` em qualquer importaÃ§Ã£o de mÃºsica | leitura dos 3 consumidores + teste de contrato novo | chave unificada em `ignoradas` |
| 2 | Callbacks de worker chamavam `root.after` direto; sem mainloop (testes, fechar janela) levantavam `RuntimeError` e o erro morria na thread | reproduÃ§Ã£o com App real sem mainloop | `frontends/despacho.py`: `DespachanteUi` com fila drenada pelo `after` da UI; erro de callback vai para `erros.log` + barra, sem derrubar a fila |
| 3 | `higienizar_controles` removia chaves duplicadas em **qualquer** seÃ§Ã£o do INI (ex.: `profile=7` do Renderer sumia) | teste com `[Renderer]` + `profile` duplicado | dedup restrito a `[Controls]`, comentÃ¡rios e outras seÃ§Ãµes preservados |
| 4 | `aplicar_preset_controle` reordenava chaves e lia a seleÃ§Ã£o de perfil antes da higiene, podendo mirar o slot errado | teste que envenena `profile\default` e confere posiÃ§Ã£o | cirurgia sÃ³ dentro de `[Controls]`, releitura apÃ³s higienizar |
| 5 | `encerrar_sessao_manual` gravava horas no banco padrÃ£o mesmo quando a sessÃ£o vinha de outro banco, e apagava o marcador mesmo com valor invÃ¡lido | teste com banco dedicado + `nan` | `db_path` explÃ­cito; invÃ¡lido preserva o marcador e retorna erro |
| 6 | `baixar_steamrip` retornava no **primeiro** host resolvido sem tentar os demais; `tentados` sempre vazio no erro | teste com FileDitch falhando + CDN ok | tenta todos na ordem, acumula `tentados`, sÃ³ entÃ£o falha |
| 7 | `_descer` publicava download parcial/incompleto no destino e nÃ£o checava `Content-Length` | teste com `Content-Length` maior que o corpo | escrita em temporÃ¡rio no mesmo disco + publicaÃ§Ã£o atÃ´mica; incompleto nÃ£o publica |
| 8 | `recuperar`/`_aplicar` ignoravam o parÃ¢metro `links` no caminho de erro do macOS (rollback vetava `.app` vÃ¡lido) | teste com falha simulada + `links=True` | propaga `links` em todos os caminhos |
| 9 | ExtraÃ§Ã£o de `.zip` no Mac seguia symlinks sem validar e ativava bits arbitrÃ¡rios de modo | zip com symlink externo | validaÃ§Ã£o prÃ©via + recriaÃ§Ã£o manual com modos filtrados |
| 10 | `.dmg` baixado sem extensÃ£o quebrava a extraÃ§Ã£o Mac | teste com asset `.dmg` | nome do download preserva o sufixo do asset |
| 11 | Pacote de mÃºsicas restaurava arquivo **antes** de conferir o SHA e ignorava duplicata jÃ¡ existente | teste com ZIP adulterado | confere SHA antes de publicar; duplicata com arquivo ausente tem o path religado |
| 12 | `resolver_musica` quebrava com caminho Windows em checkout Linux/macOS (`Path(p).name` nÃ£o separa `\`) | teste com `Z:\...\faixa.mp3` | `nome_arquivo_portatil` + traduÃ§Ã£o de prefixo |
| 13 | Restore de jogos (`importar_lista` por uuid) nÃ£o restaurava `save_path`, mods, `game_code` e `regiao` | teste de restore dedicado | campos preservados no `UPDATE` de restore |
| 14 | `remover_link` chamava `os.rmdir` em symlink POSIX (falha/risco) e `mods_titulo_dir` aceitava TID invÃ¡lido criando pasta `..` | testes de TID invÃ¡lido | `unlink` para symlink, `rmdir` sÃ³ para junction; TID validado antes de montar caminho |
| 15 | Overlay de mods copiava por cima de arquivo local e revalidava sÃ³ por lista de nomes (ediÃ§Ã£o na fonte passava batida) | teste de colisÃ£o + ediÃ§Ã£o de fonte | manifesto com fingerprint (tamanho+mtime) por arquivo; destino ocupado fora do Hub Ã© preservado com aviso |
| 16 | Instalador Mac apagava `emuladores/` com `rm -rf` antes de extrair (perdia `user/` em reinstalaÃ§Ã£o) e exigia o `.pkg` mesmo no pacote leve | teste do instalador leve | `ditto` por cima, sem apagar; leve pula Python/emuladores com aviso |
| 17 | `BibliotecaHub.sh`/`.command`/`.bat` exportavam `BIBLIOTECA_HOME` apontando para `dados/` em vez da raiz, quebrando `resolve_home` + instaladores | leitura dos launchers + teste de layout | raiz por padrÃ£o, com fallback que reconhece a coleÃ§Ã£o legada `dados/dados/` sem movÃª-la |
| 18 | `montar_linux.py --gui` nÃ£o repassava argumentos; builders copiavam `app/` com listas divergentes (novo `despacho.py` ficaria de fora) | teste de layout dos 3 builders | `shift` no launcher, `copiar_app` Ãºnico usado pelos 3 builders |
| 19 | DeSmuME do bundle Windows usava caminho fixo em vez dos overrides do app | teste com `BIBLIOTECA_EMULADOR_NDS` | `desmume_instalado_dir` resolve como o app |
| 20 | `importar_repack` apagava o archive mesmo quando `importar_lista` retornava erros | leitura do fluxo + contrato | erro na importaÃ§Ã£o preserva o archive e a pasta extraÃ­da |

## 3. DecisÃµes de estrutura

- `bib_nucleo/arquivos.py`: publicaÃ§Ã£o atÃ´mica (`destino_temporario`,
  `gravar_atomico`) usada em downloads, cache WAV, instaladores e pacote
  de fontes. NÃ£o substitui backups versionados.
- `frontends/despacho.py`: Ãºnico ponto de entrega workerâ†’UI, com ciclo
  de vida prÃ³prio (cancela timers e descarta fila ao fechar).
- `ferramentas/diagnosticar.py` e `empacotar_fontes.py`: operaÃ§Ã£o e
  entrega sem tocar na coleÃ§Ã£o (banco aberto `mode=ro` + `query_only`).
- `.github/workflows/testes.yml`: matriz Windows/Linux Ã— Python 3.10/3.14,
  com relatÃ³rio JSON por combinaÃ§Ã£o.
- Removidos sem uso: `_verificar_sessoes_pendentes`,
  `_verificar_backup_antigo` (GUI), `_musica_ja_tem` (banco),
  `AZAHAR_USER_EXCLUIR` (builder Linux), imports nÃ£o usados em
  `test_fase_a`/`test_fase_b`/`test_varredura`, `_emu_fake` local em
  `test_mods` (usa o helper do runner).

## 4. O que falta validar (real, nÃ£o simulado)

- Linux real: TUI, Wine, DeSmuME, traduÃ§Ã£o de caminhos e `.run`.
- macOS real: `.command`, `.app` Azahar/DeSmuME, `afplay`, quarentena.
- Rede real: iTunes, SteamRip/hosts, yt-dlp, FFmpeg, releases GitHub.
- Ãudio real: MCI/WAV/ffmpeg no Windows da coleÃ§Ã£o; avanÃ§o no fim.
- Instaladores completos (Inno/`--setup`, `.run`, pacote Mac cheio).
- ConcorrÃªncia Win+Linux na mesma casa continua vetada pelo lock.

## 5. Como reproduzir

```powershell
py -3.14 codigo/ferramentas/testes/executar.py --json "$env:TEMP\tucoteca-testes.json"
py -3.14 codigo/ferramentas/diagnosticar.py --json
py -3.14 codigo/ferramentas/empacotar_fontes.py
```

## 6. RevisÃ£o e modo Big Picture â€” 10/10/2026

- Base de trabalho limpa; diagnÃ³stico geral dos 62 fontes Python, exports,
  dependÃªncias e integridade do banco. ColeÃ§Ã£o encontrada: 25 jogos,
  51 mÃºsicas, 4 desejos. O diagnÃ³stico indicou yt-dlp ausente no ambiente
  consultado; as outras dependÃªncias verificadas estavam disponÃ­veis.
- Tema azul-noite/ciano, seleÃ§Ã£o com borda contrastante e cores alinhadas
  entre cards, botÃµes, tabelas e navegaÃ§Ã£o lateral.
- F11/botÃ£o Tela cheia abre a biblioteca imersiva: capas 216Ã—288,
  destaque com tÃ­tulo e Jogar, sidebar e filtros recolhidos. Esc restaura
  o layout de janela. Mouse/teclado; gamepad nÃ£o foi implementado.
- Setas e Home/End navegam na grade, com rolagem para manter o card
  visÃ­vel. Enter usa o lanÃ§amento existente. Ctrl+F focaliza a busca.
- CorreÃ§Ã£o: recarga preserva seleÃ§Ã£o pelo ID em vez do Ã­ndice; adicionar
  ou renomear jogos nÃ£o seleciona silenciosamente outro tÃ­tulo. SeleÃ§Ã£o
  limitada aos cards renderizados; busca vazia desabilita Jogar do destaque.
- CorreÃ§Ã£o visual: repintura limpa cores residuais de hover nos tÃ­tulos.
- Dois testes de regressÃ£o adicionados: entrada/saÃ­da de tela cheia e
  navegaÃ§Ã£o; preservaÃ§Ã£o da seleÃ§Ã£o apÃ³s inserÃ§Ã£o e busca sem resultados.
- ValidaÃ§Ã£o Windows/Python 3.14: **261 casos, 255 PASS, 6 SKIP, 0 FAIL**;
  `py_compile` dos fontes alterados e `git diff --check` sem erros.
  `--selftest` passou com uma casa temporÃ¡ria vazia; a suÃ­te visual usa
  uma coleÃ§Ã£o de 15 jogos em sandbox. Jogos e Ã¡udio reais nÃ£o foram
  disparados. Linux/macOS continuam cobertos por casos simulados, sem
  validaÃ§Ã£o presencial nesses sistemas nesta revisÃ£o.

## 7. FundaÃ§Ãµes TucoOS â€” 10/10/2026

- Corrigido `Binding loop` no `GridView`/`ListView` (modelo agora Ã© `hub.itens`
  incondicional; visibilidade controla a tela). Guarda anti-eco no `onMudou`
  (`currentIndex` sÃ³ atribui se diferente). QML usa blocos multilinha apÃ³s
  grupo `font {}` em vez de `};`.
- HUD com 6 categorias (InÃ­cio incluso) em janela e tela cheia. SeÃ§Ã£o inicial
  vira o padrÃ£o do Qt. Atalhos Ctrl+1â€¦6; busca local Ctrl+F; paleta global Ctrl+K.
- `servicos_ui.py`: `resumo_sistema()` (contagens, recentes, pendentes, backup,
  disco via stdlib) + `busca_global()` (filtro em memÃ³ria, DTOs sem callable).
  `snapshot()` agora inclui `sistema`; `panorama()` cobre teste de busca.
- `qt_bridge.py`: `sistema`/`recentes`/`paleta`/`paletaQuantidade`,
  `buscarPaleta`/`abrirPaleta`/`abrirPrimeiraPaleta`; `atualizar()` recarrega
  sistema e reemite paleta. Sem I/O na paleta; sem rede.
- QML: InÃ­cio com Continuar/ColeÃ§Ã£o/Acesso rÃ¡pido/Recentes; paleta com Enter
  abrindo o primeiro resultado; `Theme.qml` intacto como fonte de tokens.
- Teste novo `teste_qt_inicio_paleta_e_sistema_local`; HUD cobre `inicio`.
  Suite Qt 10/10; Qt+visual 20/20. Captura validada em cÃ³pia isolada
  (25 jogos, 51 mÃºsicas), sem executar jogo/Ã¡udio. Docs: `VISAO_OS.md` novo,
  `DESKTOP_QT.md`/`ARQUITETURA.md`/`README.md` atualizados.

## 8. QoL 1.0 â€” 10/10/2026 (4 tÃ³picos)

- T1 Biblioteca Pro: `salvarJogo` com nota/etiquetas (`qt_bridge.py`,
  `servicos_ui.py`), diÃ¡logo com Nota 0â€“10 + etiquetas, detalhe com nota,
  `saude_colecao()` (exe/ROM por jogo) com card no InÃ­cio.
- T2 Player/Downloads: fila (`filaAudio`), modos sequÃªncia/aleatÃ³rio/repetir
  (`modoAudio`), volume no rodapÃ©, velocidade MB/s + ETA min nos downloads.
- T3 Visual: tokens `Theme.qml`, paleta com â†‘â†“/Enter (`paletaItem`),
  foco/seleÃ§Ã£o preservados, sem `Binding loop`/`};` apÃ³s grupo `font`.
- T4 Sistema: diÃ¡logo com backups (10), sessÃµes pendentes (+1h) e `erros.log`;
  atalho em ConfiguraÃ§Ãµes e no card de saÃºde. Slots `listarBackups`,
  `listarSessoes`, `verLog`, `registrarSessao`.
- Teste `teste_qt_qol_biblioteca_player_sistema`. Suite Qt 11/11 no mÃ³dulo.

## 9. Congelamento do tkinter â€” 10/10/2026

- RevisÃ£o final do clÃ¡ssico: Big Picture preserva a aba (sem reset p/ Biblioteca),
  `nav_superior` centralizada em `_atualizar_contexto`, toggle com `try` em
  fullscreen/foco, `_navegar_grade` ignora tecla desconhecida e largura zero.
- TÃ­tulo `TucoTeca â€” clÃ¡ssico (congelado)` + docstring de congelamento.
- RegressÃ£o em `test_visual.py` (preservar aba + tecla desconhecida).
- Visual/tkinter: 10/10; diÃ¡logo/despacho/volume: 27/27. Foco agora Ã© o Qt.


---

## VISAO_OS.md

# VisÃ£o TucoOS â€” do Hub ao OS pessoal

TucoTeca Ã© um hub pessoal local-first de Tuco e Isa (jogos + mÃºsicas + vÃ­deos).
TucoOS Ã© a
ambiÃ§Ã£o: o mesmo nÃºcleo confiÃ¡vel virando um shell pessoal â€” InÃ­cio,
busca global, serviÃ§os e integraÃ§Ãµes â€” sem virar spyware, sem nuvem
obrigatÃ³ria, sem reescrita exÃ³tica.

Python continua no domÃ­nio. Qt Quick continua na apresentaÃ§Ã£o. O que muda
Ã© organizaÃ§Ã£o: tudo vira mÃ³dulo com contrato, aÃ§Ã£o explÃ­cita e teste.

## Onde estamos (11/10/2026)

- Desktop Qt Ã© o frontend no Windows (`desktop.py` â†’ Qt Quick); a TUI curses atende Linux/macOS.
- HUD superior: InÃ­cio, Jogos, MÃºsicas, Desejos, Downloads, IntegraÃ§Ãµes, VÃ­deos e YouTube.
  Big Picture (F11) preserva categoria; modo simples reduz a navegaÃ§Ã£o.
- InÃ­cio: continuar jogando, resumo da coleÃ§Ã£o (backup/sessÃµes/disco), acesso rÃ¡pido, recentes.
- Paleta global Ctrl+K: busca local em jogos/mÃºsicas/desejos/downloads, com
  FTS5 para jogos e fallback tolerante a acentos; Enter seleciona o resultado certo.
- ServiÃ§os em `servicos_ui.py`: `snapshot()` + `resumo_sistema()` + `busca_global()` + `RegistroIntegracoes`.
- Bridge Qt (`qt_bridge.py`): modelos, workers em `QThreadPool`, geraÃ§Ãµes anti-resposta-obsoleta, player com token.
- `qml/secoes/` separa as telas; desejos, Hydra, sessÃµes manuais e adaptadores
  remotos foram extraÃ­dos para domÃ­nios. MÃ³dulos grandes ainda requerem evoluÃ§Ã£o.
- Desejo â†’ fonte â†’ importaÃ§Ã£o â†’ obtido preserva histÃ³rico. Saves explÃ­citos tÃªm
  snapshots/restauraÃ§Ã£o SHA-256 com backup anterior; screenshots sÃ£o locais.
- Tuco/Isa compartilham coleÃ§Ã£o/saves, mas tÃªm favoritos e filtros prÃ³prios.
  Atalhos, histÃ³rico anual, disco por jogo, IPS/BPS e cÃ³pia/hardlinks sÃ£o locais.
- Vigia, extraÃ§Ã£o automÃ¡tica, SponsorBlock e API loopback de leitura sÃ£o opt-in.
- Bundles locais essencial/completo: o completo inclui Chromium privado e
  QtMultimedia com retomada. Ãudio MCI/LRC tambÃ©m cobre caminhos longos.
- Provas separadas: suÃ­te hermÃ©tica, runtime nativo com mÃ­dias sintÃ©ticas,
  capturas 1440Ã—920/960Ã—640 e smokes remotos. Resultado exato acompanha a entrega,
  nÃ£o Ã© inferido da suÃ­te antiga. Nenhum jogo real Ã© aberto nos testes.

## PrincÃ­pios inegociÃ¡veis

1. Local-first: coleÃ§Ã£o em SQLite + arquivos. Rede sÃ³ sob aÃ§Ã£o, com timeout e erro virando aviso.
2. Uma coleÃ§Ã£o, um lock. Qt e TUI nunca escrevem juntos.
3. Backup antes de mutaÃ§Ã£o. PublicaÃ§Ã£o atÃ´mica. ConexÃ£o SQLite por operaÃ§Ã£o.
4. UI nunca bloqueia: I/O em worker, resultado via sinal, resposta obsoleta descartada.
5. IntegraÃ§Ã£o = adaptador registrado, nÃ£o plugin arbitrÃ¡rio. Sem execuÃ§Ã£o de cÃ³digo de terceiros.
6. Teste hermÃ©tico: sandbox, sem rede/processo/escrita externa, sem jogo/Ã¡udio real na suite.

## Escopo aprovado e limites

Steam fornece apenas catÃ¡logo/wishlist/referÃªncia: nada de lanÃ§amento pela
Steam, overlay ou sincronizaÃ§Ã£o de conquistas. Sem conta obrigatÃ³ria,
telemetria, interop Playnite/RomM/ITAD ou publicaÃ§Ã£o pÃºblica de bundles.
Tudo remoto respeita `BIBLIOTECA_REDE`; a flag nÃ£o Ã© firewall de apps externos.
Gamepad, assinatura Windows e entrega macOS permanecem adiados.

## Roadmap de referÃªncia (nÃ£o autorizaÃ§Ã£o de novas features)

### Fase 1 â€” Hub sÃ³lido (atual â†’ prÃ³xima)
- [x] InÃ­cio + paleta + sistema local
- [x] QoL 1.0: Biblioteca Pro (nota/etiquetas/saÃºde), player (fila/modos/volume),
  downloads (vel/ETA), sistema (backups/sessÃµes/logs), polimento (tema, paleta â†‘â†“)
- [x] Biblioteca com conquistas locais baseadas em saves/regras compatÃ­veis
- [ ] Tempo estimado de jogo (adiado)
- [ ] Desejos com preÃ§o/histÃ³rico local (cache, nÃ£o scraping agressivo)
- [x] Downloads com ETA/velocidade na lista + importaÃ§Ã£o explÃ­cita de concluÃ­dos
- [x] Player com fila visÃ­vel, capa do Ã¡lbum e atalhos internos configurÃ¡veis

### Fase 2 â€” TucoHub (mÃ©dio prazo)
- MÃ³dulos novos, cada um com serviÃ§o + QML + teste:
  - **Arquivos**: navegar `Games/`, abrir com app padrÃ£o, sanear repacks (reuso de `repacks.py`).
  - **Apps**: launcher de executÃ¡veis locais (atalhos `.lnk`, Steam manifests `appmanifest_*.acf`).
  - **EmulaÃ§Ã£o**: Azahar/DeSmuME com cards de preset/mod/textura/cheat por jogo.
  - **MÃ­dia**: fila CSV â†’ Ã¡udio com progresso real (traz `baixar.py` â†’ QML).
  - **Sistema**: saÃºde (CPU/RAM/GPU/disco), volume, sessÃµes, backups, logs â€” tudo stdlib + WinAPI isolada.
- Busca global vira launcher: `> comando`, `jogo:`, `musica:`, `? ajuda`.
- Temas + densidade (compacto/conforto/Big Picture) via `Theme.qml`: implementados.
- Gamepad: adiado; presets de controles dos emuladores nÃ£o sÃ£o navegaÃ§Ã£o por gamepad.

### Fase 3 â€” TucoOS shell (ambiÃ§Ã£o)
- Boot opcional em tela cheia como shell de HTPC: Big Picture vira modo padrÃ£o, Esc pede confirmaÃ§Ã£o.
- Tela de bloqueio local (PIN) e controle parental: apenas ideias; perfis leves Tuco/Isa jÃ¡ existem.
- ServiÃ§os de fundo opt-in: vigia de saves, vigia de ROMs, servidor DLNA/Jellyfin local, sync Syncthing.
- Loja local de integraÃ§Ãµes: cada integraÃ§Ã£o declara permissÃµes (rede/disco/processo) e o usuÃ¡rio liga/desliga.
- Empacotamento: SuperHub inclui Qt + manifestos; atualizaÃ§Ã£o transacional como emuladores.

## IntegraÃ§Ãµes eficazes (sugestÃµes concretas)

| IntegraÃ§Ã£o | Tipo | Por que | Forma segura |
|---|---|---|---|
| Steam local (`appmanifest`, `libraryfolders.vdf`, `shortcuts.vdf`) | catÃ¡logo | Importa biblioteca sem login | SÃ³ leitura de arquivos locais, preview antes de gravar |
| GOG/Epic manifests locais | catÃ¡logo | Mesma razÃ£o | Mesmo padrÃ£o Steam, um adaptador por loja |
| HowLongToBeat / IGDB via chave do usuÃ¡rio | metadados | Tempo estimado, capa fallback | Timeout curto, falha = aviso |
| Jellyfin/Plex local | mÃ­dia | Filmes/sÃ©ries no mesmo shell | Cliente loopback, sem exposiÃ§Ã£o externa |
| Syncthing / rclone (BYOB) | sync | Saves/mÃºsicas entre mÃ¡quinas | Perfil prÃ³prio, como qBittorrent; nunca pasta do SO |
| qBittorrent (jÃ¡) + RSS local | download | SÃ©ries/mods | Filtros explÃ­citos, destino em `Meus Jogos Locais/` |
| Voice/Gamepad (SDL) | entrada | Controle total no sofÃ¡ | Mapeamento visÃ­vel, sem hook global |
| IA local (Whisper/llama.cpp BYOB) | assistÃªncia | â€œAche RPG <20hâ€, organizar etiquetas | Modelo baixado sob aÃ§Ã£o, inferÃªncia em worker |

Estas sugestÃµes nÃ£o fazem parte da entrega atual; conquistas continuam
100% locais, sem RetroAchievements/sync social. O que NÃƒO fazer: store prÃ³pria
com pagamento, conta online obrigatÃ³ria, telemetria, plugin com `eval`/DLL
arbitrÃ¡ria, scraper que martela site, auto-update silencioso.

## Contrato de mÃ³dulo OS (para nÃ£o virar bola de lama)

```text
codigo/bib_nucleo/<modulo>.py   regra + I/O, sem Qt
codigo/bib_nucleo/rede/<adaptador>.py   integraÃ§Ã£o remota explÃ­cita
codigo/frontends/qml/secoes/<Modulo>.qml   apresentaÃ§Ã£o
qt_bridge: <modulo>_modelo + Slot aÃ§Ã£o + Property estado
test_<modulo>.py: 3-8 casos hermÃ©ticos
docs/VISAO_OS.md: linha na matriz de cobertura
```

- DTOs simples (dict/list/str). Nada de callable no QML.
- Erro vira `{ok: False, erro: str}` ou aviso, nunca exceÃ§Ã£o na UI.
- AÃ§Ã£o destrutiva pede confirmaÃ§Ã£o e faz backup.
- Novo serviÃ§o registra em `RegistroIntegracoes` com `tipo` e `permissÃµes`.

## MÃ©tricas de pronto

- Suite verde + `git diff --check` limpo + selftest Qt e TUI.
- Captura 1440Ã—920 e 960Ã—640 sem HUD engolindo conteÃºdo, sem `Binding loop`/`ReferenceError`.
- AÃ§Ã£o longa mostra atividade, permite fechar sÃ³ apÃ³s concluir, e nÃ£o deixa Ã¡udio/jogo Ã³rfÃ£o.
- Docs atualizadas: cobertura Qt Quick, permissÃµes da integraÃ§Ã£o, como reproduzir.

## EvoluÃ§Ã£o posterior

Novas trilhas precisam de decisÃ£o especÃ­fica; nÃ£o expandir o escopo durante
o fechamento dos bundles. EmulaÃ§Ã£o avanÃ§ada permanece acessÃ­vel no desktop.
Everything tem fallback testado, mas o Ã­ndice nativo nÃ£o foi comprovado neste
ambiente; No-Intro/matching exato e provedores externos nÃ£o sÃ£o garantidos.


---

