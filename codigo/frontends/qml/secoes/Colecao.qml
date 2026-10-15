import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

ListView {
    id: collection
    objectName: "collectionList"
    property var shell
    model: hub.itens
    clip: true; spacing: 8
    activeFocusOnTab: true
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
    Keys.onReturnPressed: { if (hub.secao === "musicas" && hub.selecionado.id) hub.tocar(hub.selecionado.id); else if (hub.secao === "videos" && hub.selecionado.id) shell.playVideo(hub.selecionado.id) }
    onCurrentIndexChanged: { if (activeFocus) hub.selecionar(currentIndex) }
    delegate: Rectangle {
        id: row
        required property var item
        required property int index
        width: collection.width - 12
        height: hub.secao === "downloads" ? 104 : hub.aparencia.modo_simples ? 100 : 82
        radius: 12
        color: rowHover.hovered ? Theme.raised : Theme.surface
        border.color: collection.activeFocus && collection.currentIndex === index ? Theme.accent : "transparent"
        HoverHandler { id: rowHover }
        TapHandler { onTapped: { collection.currentIndex = index; hub.selecionar(index); collection.forceActiveFocus() } }
        RowLayout {
            anchors.fill: parent; anchors.margins: 14; spacing: 12
            Rectangle {
                width: 50; height: 50; radius: 10; color: Theme.raised
                Text { anchors.centerIn: parent; text: hub.secao === "musicas" ? "♫" : hub.secao === "desejos" ? "☆" : hub.secao === "videos" ? "▶" : "↓"; color: Theme.accent; font.pixelSize: Theme.fs(26) }
                Image { anchors.fill: parent; source: row.item.capa_url || ""; fillMode: Image.PreserveAspectCrop; asynchronous: true; sourceSize: Qt.size(100, 100) }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 6
                Text { Layout.fillWidth: true; elide: Text.ElideRight; text: row.item.titulo || row.item.nome || ""; color: Theme.text; font { pixelSize: Theme.card; weight: Font.DemiBold } }
                Text {
                    Layout.fillWidth: true; elide: Text.ElideRight
                    text: hub.secao === "musicas" ? (row.item.artista || "Artista desconhecido") + "  ·  " + (row.item.album || "Álbum local") :
                          hub.secao === "videos" ? (row.item.canal || "Arquivo local") + "  ·  " + Math.floor((row.item.duracao_s || 0) / 60) + " min" :
                          hub.secao === "desejos" ? "Steam  ·  " + row.item.appid :
                          Number(row.item.pct || 0).toFixed(1) + "%  ·  " + (row.item.estado || "Histórico local") +
                          (row.item.fonte_progresso === "estimativa" ? "  ·  estimativa em disco" : "") +
                          (row.item.velocidade ? "  ·  " + (row.item.velocidade / 1048576).toFixed(1) + " MB/s" : "") +
                          (row.item.eta ? "  ·  ETA " + Math.floor(row.item.eta / 60) + "min" : "")
                    color: Theme.muted; font.pixelSize: Theme.subtitle
                }
                ProgressBar { visible: hub.secao === "downloads"; Layout.fillWidth: true; from: 0; to: 100; value: row.item.pct || 0 }
            }
            ActionButton {
                text: hub.secao === "musicas" ? "▶ Tocar" : hub.secao === "desejos" ? "Steam ↗" : hub.secao === "videos" ? "▶ Assistir" : "Abrir pasta"
                onClicked: {
                    if (hub.secao === "musicas") hub.tocar(row.item.id)
                    else if (hub.secao === "desejos") hub.abrirUrl("https://store.steampowered.com/app/" + row.item.appid)
                    else if (hub.secao === "videos") collection.shell.playVideo(row.item.id)
                    else hub.abrirPasta(row.item.save_path || "")
                }
            }
            ActionButton { visible: hub.secao === "musicas" && !hub.aparencia.modo_simples; text: "Capas…"; enabled: !hub.ocupado; onClicked: collection.shell.openCovers("musicas", row.item) }
            ActionButton { visible: hub.secao === "musicas"; text: "Letras"; enabled: !hub.ocupado; onClicked: collection.shell.showLyrics(row.item) }
            ActionButton { visible: hub.secao === "downloads" && row.item.fonte_progresso === "api"; text: "Pausar"; enabled: !hub.ocupado; onClicked: hub.controlarDownload(row.item.hash, "pausar") }
            ActionButton { visible: hub.secao === "downloads" && row.item.fonte_progresso === "api"; text: "Retomar"; enabled: !hub.ocupado; onClicked: hub.controlarDownload(row.item.hash, "retomar") }
            ActionButton { visible: hub.secao === "downloads" && hub.foraDoDestino(row.item.save_path || ""); text: "Organizar"; enabled: !hub.ocupado; ToolTip.visible: hovered; ToolTip.text: "Mover para Meus Jogos Locais"; onClicked: hub.organizarDownload(row.item.save_path) }
            ActionButton { visible: hub.secao !== "downloads" && !hub.aparencia.modo_simples; text: "×"; Accessible.name: "Remover da coleção"; enabled: !hub.ocupado; onClicked: collection.shell.deleteItem(hub.secao, row.item) }
            ActionButton { visible: hub.secao === "desejos"; text: "Buscar fonte"; enabled: !hub.ocupado; onClicked: collection.shell.findSources(row.item) }
        }
    }
}
