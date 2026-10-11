import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: section
    objectName: "youtubeSection"
    property var shell
    function irPara(url) { if (browser.item) browser.item.irPara(url) }
    function urlAtualAsync(callback) { if (browser.item) browser.item.urlAtualAsync(callback); else callback("") }
    Loader {
        id: browser
        anchors.fill: parent
        active: hub.webDisponivel
        source: "../NavegadorEmbed.qml"
    }
    Connections {
        target: browser.item
        ignoreUnknownSignals: true
        function onPedirDownload(url) { hub.youtubeBaixarUrl(url) }
        function onPedirAbrirExterno(url) { hub.abrirUrl(url) }
    }
    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(600, parent.width - 40)
        visible: !hub.webDisponivel
        spacing: 14
        Text { text: "◇"; color: Theme.accent; font.pixelSize: 54; Layout.alignment: Qt.AlignHCenter }
        Text { text: "YouTube no navegador"; color: Theme.text; font.pixelSize: 21; Layout.alignment: Qt.AlignHCenter }
        Text { text: "Variante essencial ou rede desligada. A busca e o download continuam disponíveis sob ação sua; para assistir, o vídeo abre no navegador."; color: Theme.muted; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        ActionButton { text: "Pesquisar e baixar…"; primary: true; Layout.alignment: Qt.AlignHCenter; onClicked: section.shell.showYoutubeSearch() }
    }
}
