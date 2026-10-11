import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "youtubeDialog"
    title: "YouTube · baixar para a videoteca"
    anchors.centerIn: parent
    width: Math.min(850, ApplicationWindow.window.width - 60)
    height: Math.min(700, ApplicationWindow.window.height - 40)
    modal: true; standardButtons: Dialog.Close
    contentItem: ColumnLayout {
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            TextField { id: query; objectName: "youtubeSearchField"; Layout.fillWidth: true; placeholderText: "Título, canal ou link YouTube"; onAccepted: hub.buscarVideos(text, false) }
            ActionButton { text: "Buscar"; enabled: !hub.ocupado; onClicked: hub.buscarVideos(query.text, false) }
            ActionButton { text: "Atualizar"; enabled: !hub.ocupado; onClicked: hub.buscarVideos(query.text, true) }
        }
        Label { text: hub.videosMensagem; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
        Label { visible: hub.videoProgresso.rotulo.length > 0; text: "Baixando " + hub.videoProgresso.rotulo; color: Theme.accent }
        ProgressBar { visible: hub.videoProgresso.rotulo.length > 0; Layout.fillWidth: true; from: 0; to: 100; value: hub.videoProgresso.pct }
        ListView {
            objectName: "youtubeResults"
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8
            model: hub.videosResultados
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var item
                width: ListView.view.width - 12; height: 112; radius: 12; color: Theme.surface
                RowLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 12
                    Image { source: item.thumb || ""; Layout.preferredWidth: 110; Layout.preferredHeight: 76; fillMode: Image.PreserveAspectFit; asynchronous: true }
                    ColumnLayout {
                        Layout.fillWidth: true
                        Label { text: item.titulo; Layout.fillWidth: true; elide: Text.ElideRight; font.bold: true }
                        Label { text: item.canal + " · " + Math.floor((item.duracao_s || 0) / 60) + " min"; Layout.fillWidth: true; elide: Text.ElideRight; color: Theme.muted }
                    }
                    ActionButton { text: "Página ↗"; onClicked: hub.abrirUrl(item.url) }
                    ActionButton { text: "Baixar"; primary: true; enabled: !hub.ocupado; onClicked: hub.baixarVideo(item.video_id) }
                }
            }
        }
        Label { text: "MP4 até 720p; mesclagem de áudio/vídeo usa o FFmpeg configurado. Após baixar, o vídeo aparece na videoteca local."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
    }
}
