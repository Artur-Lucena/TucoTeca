# Desktop Qt Quick

## Decisão de arquitetura

O frontend do checkout Windows é PySide6 + Qt Quick/QML, e é o único desktop.
Python permanece no domínio: substituir banco, emulação e áudio por outra
linguagem acrescentaria uma reescrita sem benefício necessário para a UI.
Qt entrega controles, cena acelerada, foco, imagens assíncronas e layouts.

```text
BibliotecaHub.bat → abrir_hub.py → desktop.py → app_qt.py (PySide6 instalado)
                                                   ├── qml/ (apresentação e componentes)
                                                   └── qt_bridge.py (modelos, estado, workers)
                                                         └── servicos_ui.py (casos de uso/adaptadores)
                                                               └── bib_core / bib_nucleo / SQLite
```

Não há troca de interface dentro do mesmo processo: o Qt Quick é o único
desktop. Sem PySide6 instalado, `desktop.py` encerra com uma mensagem clara
orientando a instalar `codigo/ferramentas/requirements-ui.txt` (ou usar o
pacote pronto). Em Linux/macOS, o hub TUI curses continua disponível pelo
`./BibliotecaHub.sh`. Não há migração nova de schema.

## Interface

- HUD permanente com **Início / Jogos / Músicas / Desejos / Downloads / Integrações / Vídeos**.
- Início OS: continuar, resumo local (backup/sessões/disco), acesso rápido, recentes.
- Paleta global Ctrl+K: busca local unificada, Enter abre o primeiro resultado.
- Tela cheia preserva a categoria e continua permitindo a troca entre telas.
- Biblioteca com arte local em destaque, capas em grade virtualizada, filtros
  por plataforma/favoritos/status, busca e ordenação por nome/horas/recência.
- Drawer de detalhes, formulários e confirmação de exclusão.
- Listas de músicas/desejos/downloads; player persistente no rodapé.
- `Theme.qml` centraliza tokens; `ActionButton.qml` e `PosterCard.qml` são
  componentes reaproveitáveis. Botões seguem pílula (raio = altura/2) com
  altura/texto dos tokens `btnAlto`/`btnTexto` e variante `compact` para
  chips e ações secundárias; combos e campos usam a mesma altura —
  sem número mágico por tela. Hover/foco/seleção têm estados explícitos.
- Layout compacto validado em 960×640; destaque recolhe em telas baixas para
  reservar espaço para a coleção. Renderização sem GPU pode usar
  `QT_QUICK_BACKEND=software` (útil em testes e diagnóstico).
- QoL 1.5: textos auxiliares de 13–14px, cabeçalho adaptativo, primeira linha
  de cards com status/horas visíveis no compacto, resumo dos filtros e botão
  Limpar filtros. Ctrl+F no Início/Integrações abre a busca global.
- Saúde da coleção contabiliza todos os jogos e permite filtrar pendências;
  avisos são mostrados em fila, com botão para fechar. Registro de horas aceita
  decimais e encerra o marcador de sessão pendente após backup.

## Cobertura

| Fluxo | Qt Quick |
|---|---|
| Coleção, busca, filtros, favorito, adicionar/editar/excluir jogo | Sim |
| Aparência: tema claro/escuro, densidade e escala de texto 80–150% | Sim |
| Editar nota 0–10 e etiquetas; saúde exe/ROM no Início | Sim |
| Jogar com provider, presets/mods já configurados e sessão rastreada | Sim |
| Músicas locais: importar pasta, tocar, pausar, anterior/próxima, parar | Sim |
| Fila visível, modos sequência/aleatório/repetir, volume no rodapé | Sim |
| Progresso do player no rodapé (tempo decorrido / duração) | Sim |
| Desejos: listar, adicionar por appid, remover, abrir Steam | Sim |
| Desejos: preço/desconto sob demanda com cache local de 24h | Sim |
| Torrents: progresso com recebido/total, velocidade/ETA, espaço livre, iniciar, pausar/retomar, abrir pasta | Sim |
| SteamRip/FitGirl: pesquisar e abrir página do resultado | Sim |
| Backup da coleção / volume global Windows | Sim |
| Sistema: backups, registro/encerramento de sessões pendentes, últimos erros | Sim |
| Mods, texturas HD, cheats e presets do Azahar no detalhe de cada jogo 3DS | Sim |
| Controles: aplicar e salvar perfis; gerar mapa padrão e testar botões | Sim (leitura ao vivo; sem hardware mostra a ausência, prova física com o usuário) |
| Atualizar emuladores | Sim, com consulta do release e confirmação expressa antes de baixar |
| Importação avançada de jogos/ROMs, sanar/religar executáveis, UAC | Sim |
| Arrastar pasta/arquivo para a janela abre o mesmo preview antes de importar | Sim |
| CSV → áudio, fila de downloads de músicas, buscar capas | Sim |
| Wishlist por JSON salvo; leitura Steam com erro explícito se endpoint indisponível | Sim |
| Importar torrent concluído | Sim |
| Desejo → SteamRip → baixar/importar → obtido | Sim |
| Registrar horas manualmente nos detalhes e encerrar sessão pendente no Sistema | Sim |
| Bibliotecas sem credencial, catálogo Spotify, download/conversão/importação de músicas | Sim |
| Videoteca, YouTube (embutido na variante completa; link externo na essencial), reprodutores, editores e EQ por cópia | Sim |
| Atalhos personalizados em Integrações | Sim |
| Exportar/importar pacotes | Sim, com confirmação para restaurar saves |
| Remoções com desfazer (jogos com capa, desejos, vídeos) via lixeira local | Sim |
| Saves de jogo: configurar, snapshot, restaurar; screenshots | Sim |
| Perfis Tuco/Isa, atalhos, vigia e API de leitura | Sim, em Ferramentas pessoais |
| Letras LRCLIB, LibRetro, SponsorBlock e MP3 por URL | Sim |
| IPS/BPS, cópia/hardlinks e uso de disco | Sim, em ferramentas do jogo |
| Navegação por controle XInput: setas/analógico, A, B, LB/RB e Start | Sim, sem hardware validado ainda |

A cobertura descreve o desktop Qt Quick atual. Distribuições anteriores em
`dist/` não são atualizadas ao editar os fontes.

### Everything opcional no Windows

O scanner usa `es.exe` do PATH ou de `programa/ferramentas/everything/cli/`.
O cliente local consulta a instância `TucoTeca`; uma configuração externa pode
usar `BIBLIOTECA_EVERYTHING` e `BIBLIOTECA_EVERYTHING_INSTANCIA`.
Everything deve estar aberto e com o volume/pasta indexado. Erro, timeout ou
índice vazio mantêm o scanner normal como fallback; o Hub não instala o serviço
automaticamente nem envia o índice ao GitHub. A exportação temporária usa UTF-8
com BOM, é removida após a consulta e restringe os resultados às raízes pedidas.

## Contratos e integrações

`RegistroIntegracoes` recebe descritores `Integracao` com chave estável,
nome, descrição, tipo e um adaptador de busca opcional. O contrato de busca
é `buscar(termo) -> {itens: [{titulo, url}], erros: [str]}`. O frontend não
precisa saber como a fonte consulta/normaliza dados. Chaves duplicadas falham
explicitamente; DTOs enviados ao QML não contêm callables.

Para incluir uma fonte:

1. Implemente o adaptador de domínio (timeouts, normalização, erros).
2. Registre o descritor em `integracoes_padrao()` ou injete um registro em
   `ServicoBiblioteca`. O catálogo aparece no mesmo componente da UI.
3. Teste o adaptador sem rede real e o contrato do registro.

É uma API interna de adaptadores, não um carregador de plugins de terceiros.
Atalhos https do usuário (botão + Adicionar, com `{q}` p/ busca) são
persistidos na coleção; padrões não saem. Downloads e instalações continuam
ações explícitas do usuário.

## Concorrência e persistência

- SQLite: cada caso de uso abre/fecha sua conexão; mutações usam lock de
  escrita e backup antes de alterar a coleção.
- `QThreadPool` executa I/O; `Signal` com `QueuedConnection` entrega os
  resultados à thread Qt. Nenhum worker altera widgets/modelos.
- Refresh e busca remota usam gerações para descartar respostas obsoletas.
- MCI: preparo/conversão de áudio no worker; open/play/pause/close na
  thread dona do dispositivo. Token impede áudio tardio após Parar.
- A UI mantém o processo aberto enquanto conclui operações em andamento.
- Snapshot usa IDs estáveis; filtro/ordenação não selecionam outra entrada
  apenas porque sua posição mudou. Nenhum limite artificial de 150 cards.

## Desenvolvimento e verificação

```powershell
py -3.14 -m pip install -r codigo/ferramentas/requirements-ui.txt
py -3.14 codigo/frontends/desktop.py
py -3.14 codigo/frontends/desktop.py --big-picture
py -3.14 codigo/ferramentas/testes/executar.py --modulo test_qt
```

Use `BIBLIOTECA_HOME` separado para provas. `app_qt.py --selftest` carrega
QML e dados, encerra o player e libera o lock. `--screenshot caminho.png`
grava uma captura no selftest. A suíte Qt usa plataforma offscreen e backend
software, com rede/processos/escrita externa vetados pelo runner.

No checkout atual, as wheels estão instaladas no Python oficial de
desenvolvimento e no runtime `programa/windows-x64/python/Lib`. A CI inclui
um job Qt separado para Windows e Linux. Os testes stdlib continuam podendo
rodar sem Qt (casos de GUI Qt são marcados como pulados).

## Empacotamento e licenças

`copiar_app()` inclui Python, QML e `qmldir`. O pacote de fontes inclui
`codigo/ferramentas/requirements-ui.txt`. `montar_superhub.py` inclui PySide6-Essentials e
shiboken6 6.10.2, recursos/plugins e metadados/licenças das distribuições,
e executa o selftest do dispatcher no runtime montado. O builder exige
essas versões no ambiente de build. Sem PySide6, o desktop orienta a instalar `requirements-ui.txt` ou usar um pacote pronto.

PySide6/Qt possuem licenças próprias (LGPL/GPL/comercial conforme componente);
a licença MIT do Hub não relicencia Qt. Preserve os avisos/licenças e as
bibliotecas dinâmicas substituíveis ao redistribuir. O bundle completo novo
é gerado apenas localmente, para uso pessoal. As árvores de cada variante
são isoladas; a prova também roda no ZIP extraído e confere SHA-256.

## Limites e decisões desta etapa

- `qml/secoes/` contém as telas; `Main.qml` mantém o shell/diálogos comuns.
- Mods, cheats, controles, ROMs/importação avançada, atualização de emuladores,
  sincronização da wishlist e recuperação de executáveis têm fluxo próprio no
  desktop Qt.
- Estatísticas usam barras Qt Quick, sem exigir QtCharts na variante essencial.
  Histórico começa nas sessões novas; não são inventadas datas antigas.
- Hardlinks compartilham mudanças com a origem; a organização não apaga a
  origem. Junctions automáticas não são usadas.
- WebEngine não implica gamepad. A API de leitura não tem rotas de lançamento.
- Provas herméticas não comprovam disponibilidade de serviços externos, matching
  No-Intro ou download de jogos reais. macOS permanece adiado.
