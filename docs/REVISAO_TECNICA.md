# Revisão técnica — TucoTeca (06–07/10/2026)

Auditoria de código, estrutura e empacotamento para trabalho em conjunto.
Base: árvore de trabalho em `98dccd1` + alterações desta revisão (não
commitadas — ver `git status`). Validação: suíte **221/221** + selftest.

## 1. Método e evidência

- Varredura `ast` de 48 arquivos Python (~22 mil linhas, 288 exports):
  sem definições duplicadas, sem `__all__` duplicado, sem chamada
  `self.*` sem método correspondente nas classes `App`/`Tui`, sem
  colisão de exports entre módulos (só `titulo_ok`, mesmo objeto).
- Rede, subprocessos e escrita fora da sandbox são bloqueados pelo
  audit-hook de `executar.py`; cada `teste_*` roda em subprocesso
  e diretório próprios. Pulos por SO/display aparecem como `SKIP`.
- `diagnosticar.py` (somente-leitura) confere sintaxe, exports,
  dependências, mapa de pastas e integridade do SQLite sem migrar o banco.
- `empacotar_fontes.py` gera `dist/tucoteca-fontes-revisadas.zip` com a
  árvore atual + manifesto SHA-256, excluindo coleção, caches e builds.

## 2. Erros comprovados e corrigidos

| # | Achado | Prova | Correção |
|---|---|---|---|
| 1 | `importar_musicas` retornava `ignorados`, mas o contrato documentado e lido pela GUI/TUI é `ignoradas` (`res['ignoradas']` em `app_win.py`, `app_tui.py`, `test_baixar.py`) — `KeyError` em qualquer importação de música | leitura dos 3 consumidores + teste de contrato novo | chave unificada em `ignoradas` |
| 2 | Callbacks de worker chamavam `root.after` direto; sem mainloop (testes, fechar janela) levantavam `RuntimeError` e o erro morria na thread | reprodução com App real sem mainloop | `frontends/despacho.py`: `DespachanteUi` com fila drenada pelo `after` da UI; erro de callback vai para `erros.log` + barra, sem derrubar a fila |
| 3 | `higienizar_controles` removia chaves duplicadas em **qualquer** seção do INI (ex.: `profile=7` do Renderer sumia) | teste com `[Renderer]` + `profile` duplicado | dedup restrito a `[Controls]`, comentários e outras seções preservados |
| 4 | `aplicar_preset_controle` reordenava chaves e lia a seleção de perfil antes da higiene, podendo mirar o slot errado | teste que envenena `profile\default` e confere posição | cirurgia só dentro de `[Controls]`, releitura após higienizar |
| 5 | `encerrar_sessao_manual` gravava horas no banco padrão mesmo quando a sessão vinha de outro banco, e apagava o marcador mesmo com valor inválido | teste com banco dedicado + `nan` | `db_path` explícito; inválido preserva o marcador e retorna erro |
| 6 | `baixar_steamrip` retornava no **primeiro** host resolvido sem tentar os demais; `tentados` sempre vazio no erro | teste com FileDitch falhando + CDN ok | tenta todos na ordem, acumula `tentados`, só então falha |
| 7 | `_descer` publicava download parcial/incompleto no destino e não checava `Content-Length` | teste com `Content-Length` maior que o corpo | escrita em temporário no mesmo disco + publicação atômica; incompleto não publica |
| 8 | `recuperar`/`_aplicar` ignoravam o parâmetro `links` no caminho de erro do macOS (rollback vetava `.app` válido) | teste com falha simulada + `links=True` | propaga `links` em todos os caminhos |
| 9 | Extração de `.zip` no Mac seguia symlinks sem validar e ativava bits arbitrários de modo | zip com symlink externo | validação prévia + recriação manual com modos filtrados |
| 10 | `.dmg` baixado sem extensão quebrava a extração Mac | teste com asset `.dmg` | nome do download preserva o sufixo do asset |
| 11 | Pacote de músicas restaurava arquivo **antes** de conferir o SHA e ignorava duplicata já existente | teste com ZIP adulterado | confere SHA antes de publicar; duplicata com arquivo ausente tem o path religado |
| 12 | `resolver_musica` quebrava com caminho Windows em checkout Linux/macOS (`Path(p).name` não separa `\`) | teste com `Z:\...\faixa.mp3` | `nome_arquivo_portatil` + tradução de prefixo |
| 13 | Restore de jogos (`importar_lista` por uuid) não restaurava `save_path`, mods, `game_code` e `regiao` | teste de restore dedicado | campos preservados no `UPDATE` de restore |
| 14 | `remover_link` chamava `os.rmdir` em symlink POSIX (falha/risco) e `mods_titulo_dir` aceitava TID inválido criando pasta `..` | testes de TID inválido | `unlink` para symlink, `rmdir` só para junction; TID validado antes de montar caminho |
| 15 | Overlay de mods copiava por cima de arquivo local e revalidava só por lista de nomes (edição na fonte passava batida) | teste de colisão + edição de fonte | manifesto com fingerprint (tamanho+mtime) por arquivo; destino ocupado fora do Hub é preservado com aviso |
| 16 | Instalador Mac apagava `emuladores/` com `rm -rf` antes de extrair (perdia `user/` em reinstalação) e exigia o `.pkg` mesmo no pacote leve | teste do instalador leve | `ditto` por cima, sem apagar; leve pula Python/emuladores com aviso |
| 17 | `BibliotecaHub.sh`/`.command`/`.bat` exportavam `BIBLIOTECA_HOME` apontando para `dados/` em vez da raiz, quebrando `resolve_home` + instaladores | leitura dos launchers + teste de layout | raiz por padrão, com fallback que reconhece a coleção legada `dados/dados/` sem movê-la |
| 18 | `montar_linux.py --gui` não repassava argumentos; builders copiavam `app/` com listas divergentes (novo `despacho.py` ficaria de fora) | teste de layout dos 3 builders | `shift` no launcher, `copiar_app` único usado pelos 3 builders |
| 19 | DeSmuME do bundle Windows usava caminho fixo em vez dos overrides do app | teste com `BIBLIOTECA_EMULADOR_NDS` | `desmume_instalado_dir` resolve como o app |
| 20 | `importar_repack` apagava o archive mesmo quando `importar_lista` retornava erros | leitura do fluxo + contrato | erro na importação preserva o archive e a pasta extraída |

## 3. Decisões de estrutura

- `bib_nucleo/arquivos.py`: publicação atômica (`destino_temporario`,
  `gravar_atomico`) usada em downloads, cache WAV, instaladores e pacote
  de fontes. Não substitui backups versionados.
- `frontends/despacho.py`: único ponto de entrega worker→UI, com ciclo
  de vida próprio (cancela timers e descarta fila ao fechar).
- `ferramentas/diagnosticar.py` e `empacotar_fontes.py`: operação e
  entrega sem tocar na coleção (banco aberto `mode=ro` + `query_only`).
- `.github/workflows/testes.yml`: matriz Windows/Linux × Python 3.10/3.14,
  com relatório JSON por combinação.
- Removidos sem uso: `_verificar_sessoes_pendentes`,
  `_verificar_backup_antigo` (GUI), `_musica_ja_tem` (banco),
  `AZAHAR_USER_EXCLUIR` (builder Linux), imports não usados em
  `test_fase_a`/`test_fase_b`/`test_varredura`, `_emu_fake` local em
  `test_mods` (usa o helper do runner).

## 4. O que falta validar (real, não simulado)

- Linux real: TUI, Wine, DeSmuME, tradução de caminhos e `.run`.
- macOS real: `.command`, `.app` Azahar/DeSmuME, `afplay`, quarentena.
- Rede real: iTunes, SteamRip/hosts, yt-dlp, FFmpeg, releases GitHub.
- Áudio real: MCI/WAV/ffmpeg no Windows da coleção; avanço no fim.
- Instaladores completos (Inno/`--setup`, `.run`, pacote Mac cheio).
- Concorrência Win+Linux na mesma casa continua vetada pelo lock.

## 5. Como reproduzir

```powershell
py -3.14 codigo/ferramentas/testes/executar.py --json "$env:TEMP\tucoteca-testes.json"
py -3.14 codigo/ferramentas/diagnosticar.py --json
py -3.14 codigo/ferramentas/empacotar_fontes.py
```

## 6. Revisão e modo Big Picture — 10/10/2026

- Base de trabalho limpa; diagnóstico geral dos 62 fontes Python, exports,
  dependências e integridade do banco. Coleção encontrada: 25 jogos,
  51 músicas, 4 desejos. O diagnóstico indicou yt-dlp ausente no ambiente
  consultado; as outras dependências verificadas estavam disponíveis.
- Tema azul-noite/ciano, seleção com borda contrastante e cores alinhadas
  entre cards, botões, tabelas e navegação lateral.
- F11/botão Tela cheia abre a biblioteca imersiva: capas 216×288,
  destaque com título e Jogar, sidebar e filtros recolhidos. Esc restaura
  o layout de janela. Mouse/teclado; gamepad não foi implementado.
- Setas e Home/End navegam na grade, com rolagem para manter o card
  visível. Enter usa o lançamento existente. Ctrl+F focaliza a busca.
- Correção: recarga preserva seleção pelo ID em vez do índice; adicionar
  ou renomear jogos não seleciona silenciosamente outro título. Seleção
  limitada aos cards renderizados; busca vazia desabilita Jogar do destaque.
- Correção visual: repintura limpa cores residuais de hover nos títulos.
- Dois testes de regressão adicionados: entrada/saída de tela cheia e
  navegação; preservação da seleção após inserção e busca sem resultados.
- Validação Windows/Python 3.14: **261 casos, 255 PASS, 6 SKIP, 0 FAIL**;
  `py_compile` dos fontes alterados e `git diff --check` sem erros.
  `--selftest` passou com uma casa temporária vazia; a suíte visual usa
  uma coleção de 15 jogos em sandbox. Jogos e áudio reais não foram
  disparados. Linux/macOS continuam cobertos por casos simulados, sem
  validação presencial nesses sistemas nesta revisão.

## 7. Fundações TucoOS — 10/10/2026

- Corrigido `Binding loop` no `GridView`/`ListView` (modelo agora é `hub.itens`
  incondicional; visibilidade controla a tela). Guarda anti-eco no `onMudou`
  (`currentIndex` só atribui se diferente). QML usa blocos multilinha após
  grupo `font {}` em vez de `};`.
- HUD com 6 categorias (Início incluso) em janela e tela cheia. Seção inicial
  vira o padrão do Qt. Atalhos Ctrl+1…6; busca local Ctrl+F; paleta global Ctrl+K.
- `servicos_ui.py`: `resumo_sistema()` (contagens, recentes, pendentes, backup,
  disco via stdlib) + `busca_global()` (filtro em memória, DTOs sem callable).
  `snapshot()` agora inclui `sistema`; `panorama()` cobre teste de busca.
- `qt_bridge.py`: `sistema`/`recentes`/`paleta`/`paletaQuantidade`,
  `buscarPaleta`/`abrirPaleta`/`abrirPrimeiraPaleta`; `atualizar()` recarrega
  sistema e reemite paleta. Sem I/O na paleta; sem rede.
- QML: Início com Continuar/Coleção/Acesso rápido/Recentes; paleta com Enter
  abrindo o primeiro resultado; `Theme.qml` intacto como fonte de tokens.
- Teste novo `teste_qt_inicio_paleta_e_sistema_local`; HUD cobre `inicio`.
  Suite Qt 10/10; Qt+visual 20/20. Captura validada em cópia isolada
  (25 jogos, 51 músicas), sem executar jogo/áudio. Docs: `VISAO_OS.md` novo,
  `DESKTOP_QT.md`/`ARQUITETURA.md`/`README.md` atualizados.

## 8. QoL 1.0 — 10/10/2026 (4 tópicos)

- T1 Biblioteca Pro: `salvarJogo` com nota/etiquetas (`qt_bridge.py`,
  `servicos_ui.py`), diálogo com Nota 0–10 + etiquetas, detalhe com nota,
  `saude_colecao()` (exe/ROM por jogo) com card no Início.
- T2 Player/Downloads: fila (`filaAudio`), modos sequência/aleatório/repetir
  (`modoAudio`), volume no rodapé, velocidade MB/s + ETA min nos downloads.
- T3 Visual: tokens `Theme.qml`, paleta com ↑↓/Enter (`paletaItem`),
  foco/seleção preservados, sem `Binding loop`/`};` após grupo `font`.
- T4 Sistema: diálogo com backups (10), sessões pendentes (+1h) e `erros.log`;
  atalho em Configurações e no card de saúde. Slots `listarBackups`,
  `listarSessoes`, `verLog`, `registrarSessao`.
- Teste `teste_qt_qol_biblioteca_player_sistema`. Suite Qt 11/11 no módulo.

## 9. Congelamento do tkinter — 10/10/2026

- Revisão final do clássico: Big Picture preserva a aba (sem reset p/ Biblioteca),
  `nav_superior` centralizada em `_atualizar_contexto`, toggle com `try` em
  fullscreen/foco, `_navegar_grade` ignora tecla desconhecida e largura zero.
- Título `TucoTeca — clássico (congelado)` + docstring de congelamento.
- Regressão em `test_visual.py` (preservar aba + tecla desconhecida).
- Visual/tkinter: 10/10; diálogo/despacho/volume: 27/27. Foco agora é o Qt.
