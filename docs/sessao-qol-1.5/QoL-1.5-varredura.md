# QoL 1.5.4 — Varredura QoL do Desktop Qt (10/10/2026, sem commit)

Base inicial: `Main.qml` + `PosterCard.qml` + `qt_bridge.py` + `servicos_ui.py`,
auditoria verde pós-1.5.3 (6 seções, 0 QML crítico, 25 jogos/51 músicas/4 desejos,
saúde 25/25). Sem TODOs no código (higiene item 50 mantida).
Atualização da continuação: os cinco ajustes imediatos abaixo foram implementados
nos tópicos 1.5.5–1.5.9. Os itens seguintes continuam como sugestões.

## Ajustes imediatos entregues nesta continuação

1. **1.5.6 — Contagem com contexto:** `N de total jogos · filtro · busca`, ação
   Limpar filtros e busca global selecionando o resultado correto em todas as listas.
2. **1.5.5 — Saúde completa:** corrige a interrupção após oito erros, contabiliza
   todos os problemas, mostra `+N outros` e oferece filtro de pendências.
3. **1.5.8 — Backup legível:** estado e idade separados; backup ausente ou com
   sete dias ou mais aparece em âmbar no Início, junto da ação Backup agora.
4. **1.5.7 — Avisos em fila:** ordem FIFO, 7 segundos por aviso e botão para fechar.
5. **1.5.9 — Registrar horas:** diálogo com quantidade informada, inclusive decimal
   com vírgula. Encerrar pendência usa o marcador correto, faz backup e remove
   a sessão da lista. A sugestão de somar automaticamente +1h foi substituída.

## Próximos ajustes sugeridos — esforço médio

6. **Preço/desconto nos Desejos** — linha hoje é `Steam · appid`. Consulta sob
    demanda (`store.steampowered.com/api/appdetails`) com cache 24h em
    `dados/cache-loja/`. Tratar país/moeda, indisponibilidade e jogos gratuitos.
7. **Drag-and-drop de pasta no Jogos** — `DropArea` no GridView → `preview_pasta`
   em worker. Hoje adicionar é manual (diálogo) ou clássico. Qt suporta nativo.
8. **Duração na lista de Músicas** — linha hoje é `artista · álbum`. Duração exige
    leitura de metadados (biblioteca opcional ou FFprobe, se disponível). Fazer lazy: só
   p/ visíveis, cache em memória, fallback "—" sem ffmpeg.
9. **Tamanho restante nos Downloads históricos** — API mostra vel/ETA; fallback
   em disco mostra só `estimativa em disco`. Adicionar `X de Y GB` via peças
   do fast-resume (molde `torrents.py` da Parte 1).
10. **Escala de texto no Config** — 1.5.3 fixou tamanhos legíveis, mas sem
    preferência. Slider 100/112/125% usando tokens do tema, com reflow e
    validação de botões, diálogos e cabeçalho em cada escala.

## Mudanças maiores

11. **Navegação por gamepad no Big Picture** — `DESKTOP_QT.md` admite "Ainda não".
    Caminho: backend de entrada SDL + GameControllerDB, eventos despachados
    para foco/ações QML, hotplug e tratamento de repetição do direcional.
12. **Lixeira com desfazer (7 dias)** — excluir hoje é definitivo (com confirmação,
    sem undo). Mover linha + capa p/ `dados/lixeira/` com restore. Exige poda
    + UI "Desfazer" no toast (liga com item 4).
13. **Volume no Linux** — `volume.py` atualmente fornece Core Audio no Windows.
    `afplay` pertence ao backend de reprodução no Mac, não ao controle de volume.
    Avaliar `wpctl`/`pactl` como adaptadores opcionais no Linux, com o contrato
    existente de leitura/ajuste e validação em uma sessão Linux real.

## Integração sugerida com maior benefício adicional

**Ludusavi:** preview e backup de saves por jogo, incluindo registro Windows e
prefixos Proton. Complementa o backup de SQLite e os saves já centralizados.
Detalhes e fontes oficiais em `QoL-1.5-integracoes.md`.
