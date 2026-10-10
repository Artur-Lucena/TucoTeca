# Parte 1 — acabamento visual e auditoria

Data: 09/10/2026. Base: árvore de trabalho sobre `98dccd1`, incluindo as
alterações acumuladas das sessões anteriores. Este documento registra a
implementação atual e o trabalho recomendado para a Parte 2.

## 1. Acabamento aplicado

- Tema próprio em `codigo/frontends/aparencia.py`: paleta azul-escura/violeta,
  botões nine-slice arredondados com estados de foco/hover/desabilitado,
  tipografia consistente e ícone local. Os elementos são gerados com Tk;
  o runtime não precisa baixar tema, instalar pacote ou carregar uma DLL nova.
- Cabeçalhos por seção, descrição do contexto e busca expansível. Filtros de
  plataforma/status/etiquetas aparecem apenas na Biblioteca.
- Barra lateral rolável, volume fixo e grupos só onde há várias ações.
  Biblioteca → Todos os jogos; Músicas → Minhas faixas. Desejos e Downloads
  são destinos diretos.
- Desejos, Downloads, Músicas e Fila usam Treeview: cabeçalhos, colunas,
  zebra, seleção independente e apenas a rolagem da tabela.
- `BarraAcoes` redistribui ações conforme a largura real, inclusive nos
  catálogos. As listas de resultados e hosts têm rolagem em seus próprios
  contêineres.
- Grade de capas com tamanho uniforme, hover/seleção e fallback em gradiente.
  Marcadores de downloads/desejos/música são desenhados como vetores, sem
  depender de uma fonte de emoji.
- Detalhes com rolagem. Abaixo de 1120 px, o espaço é cedido ao conteúdo e
  **Detalhes** abre uma janela sincronizada com a seleção atual.
- O helper visual entra em `copiar_app`, utilizado nos três builders.

### Pesquisa técnica

Foram consultados os projetos [Sun Valley](https://github.com/rdbende/Sun-Valley-ttk-theme),
[Azure ttk](https://github.com/rdbende/Azure-ttk-theme) e a
[documentação de ttk](https://docs.python.org/3/library/tkinter.ttk.html).
Aplicamos a técnica documentada de elementos de imagem/estados e widgets
ttk, com arte gerada localmente. Nenhum código desses temas foi copiado.

## 2. Problemas confirmados e corrigidos nesta etapa

| Problema | Evidência | Correção |
|---|---|---|
| A grade terminava em uma coluna após resize | Interface visível em 1280×800; reorganização chamava `update_idletasks`, permitindo reentrada | Medição e redistribuição sem event loop aninhado |
| Ações cortadas e duas barras nas listas | Janela compacta e barras com vários botões em uma linha fixa | Fluxo por largura medida, tabelas com viewport próprio |
| Imagens de um Tk destruído eram reutilizadas | Cache global não incluía identidade do interpretador | Chave por interpretador e teste com dois roots |
| Tema novo ficaria fora do ZIP | Lista explícita de arquivos em `montar_portatil.py` | Inclusão de `aparencia.py` e teste do layout offline |
| Torrents reais não eram encontrados no Windows | `BT_backup` estava em Local, enquanto o Hub só consultava Roaming | Local primeiro, compatibilidade com Roaming e override |
| Arquivo pré-alocado podia indicar conclusão falsa | Contagem antiga dependia de `stat().st_size`; reprodução com arquivo de zeros | Peças do fast-resume v1/v2; estimativa nunca autoriza conclusão |
| Torrent single-file era procurado em `nome/nome` | Composição antiga aplicava o nome duas vezes | Arquivo e pasta tratados separadamente |
| Metadados bencode ruins podiam provocar exceções não tratadas | Chave de dicionário não-hashable e aninhamento excessivo | Validação de chaves/caminhos e limite de profundidade |
| Sync parcial podia remover desejos já existentes | Worker aceitava itens parciais com erros e chamava o espelho destrutivo | Qualquer erro preserva o estado anterior |
| Desejo manual perdia proteção quando aparecia no espelho | UPDATE definia `manual=0` | Flag manual preservado; teste de duas sincronizações |
| JSON de desejos inválido podia quebrar o parser | Valores não-objeto em dicionário provocavam unpack/strip inválido | Tipos verificados e títulos normalizados |
| Mensagem afirmava que login resolveria endpoint indisponível | Redirecionamento à home ocorria mesmo no navegador do usuário | Erro descreve a resposta observada e orienta inclusão/exportação local |
| Sanear bloqueava a GUI e limpava antes de localizar jogo | Varredura síncrona e organização anterior à detecção | Worker com backup, progresso, retorno pela fila e detecção antes da limpeza |
| Redistribuíveis diferentes eram tratados como duplicados | Igualdade era inferida por nome/profundidade | Só cópia da raiz comprovadamente idêntica por arquivos/tamanho/SHA-256 é removida |

Os testes de higienização usam diretórios artificiais. Esta etapa não
executou limpeza na coleção real, nem modificou seus títulos/capas/saves.

## 3. Verificação

- Suíte completa: **249 casos sem falha**, sendo **243 executados** e **6
  pulados por condições do Windows**. O runner explicita cada pulo; não são
  testes executados com sucesso.
- Testes de interface visível em 1280×800, 960×600 e 860×560, inclusive
  redimensionamento de volta, seleção, janela de detalhes e ações alcançáveis.
- Escala Tk equivalente a 125% verificada em teste adicional.
- Compilação/sintaxe dos fontes também conferida com sintaxe mínima 3.10.
- Pyflakes temporário utilizado na revisão: sem `UndefinedName` ou
  `UndefinedLocal`; AST sem definições duplicadas. Existem avisos de imports
  de reexportação, probes opcionais e variáveis/imports não usados nos testes.
  Esses avisos não foram confundidos com falhas funcionais.
- Banco real aberto somente-leitura: integridade `ok`, 25 jogos, 51 músicas,
  4 desejos, 0 downloads de áudio. Nenhum executável da coleção ausente.
  Uma entrada tem título `Balls`, aponta para a pasta BALL x PIT e não tem capa.
- O histórico real do qBittorrent foi lido: BALL x PIT [FitGirl Repack],
  100% em peças, destino em `D:\Games\Piratas`.
- Capturas de verificação foram feitas a partir de um snapshot temporário
  do banco. Selftest também deve ser reproduzido com snapshot/casa separados
  para evitar conflito com o Hub aberto.

## 4. Melhorias recomendadas para a Parte 2

### Prioridade 1 — integrações completas e contratos

1. **qBittorrent Web API local.** O histórico em arquivo é periódico e não
   informa velocidade/ETA em tempo real. Adicionar adaptador para a API
   oficial, com estado de conexão, pausa/retomada, destino e reconexão. Manter
   arquivos como fallback. Download seletivo, paths remapeados e torrents
   v2-only exigem tratamento adicional.
2. **Pipeline persistente de conclusão.** Atualmente a importação é acionada
   pelo usuário em Verificar concluídos. Falta uma fila persistente que
   registre download → verificação → instalação necessária/pronto → importado,
   sem reimportar a cada poll. Instalador baixado não é jogo instalado.
3. **Wishlist remota moderna.** `ler_wishlist` ainda tenta o endpoint antigo.
   O endpoint público `IWishlistService/GetWishlist/v1` foi consultado para
   esta conta e respondeu `{"response":{}}`, o que não prova sozinho se a
   lista está vazia, privada em detalhes de jogos ou indisponível. Implementar
   o adaptador moderno com metadados, distinção de erro/privacidade/vazio,
   seleção de conta e testes de resposta completa. Inclusão manual e JSON
   são os caminhos locais funcionais atuais.
4. **Gerenciador único de tarefas.** Existem workers específicos espalhados
   pela GUI. Centralizar progresso, cancelamento, timeout, exceções e resultados,
   preservando a afinidade da UI/MCI e uma conexão SQLite por worker.

### Prioridade 2 — metadados, arquivos e distribuição

5. **Resolver metadados por contexto.** Combinar executável, pasta, manifesto
   da loja e AppID da lista de desejos. Isso evita títulos genéricos como
   `Balls` e melhora a busca de capa. A associação deve ter evidência e nível
   de confiança explícitos.
6. **Plano de limpeza por jogo.** `sanear_pasta` é destinado a uma pasta de
   jogo; não é um organizador geral de C:/D:. Acrescentar preview por título,
   manifesto de operações e restauração da quarentena. Comparação de conteúdo
   deve continuar sendo requisito para remover uma duplicata.
7. **Ferramentas em um pacote.** Descoberta relativa à casa do Hub e manifesto
   local de versões/licenças/hashes para qBittorrent, 7-Zip, FFmpeg, yt-dlp e
   emuladores. Os builders hoje não entregam todos esses sidecars juntos.
8. **Decompor frontends por domínio.** Aparência já foi extraída; separar
   páginas, diálogos, tarefas e controladores antes de um porte PySide6. O
   núcleo deve conservar APIs utilizáveis sem interface gráfica.
9. **Coleções grandes.** A grade atual limita o desenho a 150 jogos. Implementar
   paginação/renderização por viewport, seleção por identidade e carregamento
   assíncrono de arte, evitando reconsultas de providers em toda busca.
10. **Validação nativa dos outros SOs.** Testes de caminhos/Mac/Linux nesta
    sessão foram executados ou simulados no Windows. Ainda é necessário testar
    instalação, áudio, DPI e interação com emuladores em máquinas reais.

### Qualidade de engenharia

- Integrar Pyflakes/Ruff no CI com exceções explícitas para reexports/probes.
- Manter testes com a janela realmente dimensionada; selftest oculto não
  substitui teste de geometria.
- Guardar relatório JSON por versão e incluir o helper visual no pacote.
- Entregas atuais: `dist/windows/`; ZIPs dos fontes: `dist/fontes/`;
  versões anteriores: `dist/historico/`.
- A árvore possui alterações acumuladas não commitadas. Entregas para revisão
  devem usar `empacotar_fontes.py`, que inclui o estado atual, e o manifesto
  SHA-256; uma cópia do último commit sozinho não contém todas as mudanças.

## 5. Referências para integrações

- [qBittorrent WebUI API](https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-5.0))
- [libtorrent: fast-resume e pré-alocação](https://www.libtorrent.org/manual-ref.html#fast-resume)
- [ttk: elementos, estados e Treeview](https://docs.python.org/3/library/tkinter.ttk.html)
