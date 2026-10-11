import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import "."

Item {
    id: root
    property var video: ({url: "", sha: "", posicao: 0})
    property bool retomou: false
    readonly property int posicao: player.position
    readonly property int duracao: player.duration
    function parar() { hub.guardarVideoPosicao(video.sha || "", player.position); player.stop() }
    onVideoChanged: { retomou = false; if (player) Qt.callLater(function() { player.play() }) }
    Component.onCompleted: player.play()
    MediaPlayer {
        id: player
        source: root.video.url || ""
        audioOutput: AudioOutput {}
        videoOutput: output
        onMediaStatusChanged: {
            if (!root.retomou && mediaStatus === MediaPlayer.LoadedMedia) {
                root.retomou = true
                if (root.video.posicao) player.position = root.video.posicao
            }
        }
        onErrorOccurred: function(error, errorString) { hub.aviso("Player interno: " + errorString + ". Use VLC/MPV como alternativa.", true) }
    }
    ColumnLayout {
        anchors.fill: parent
        VideoOutput { id: output; Layout.fillWidth: true; Layout.fillHeight: true; fillMode: VideoOutput.PreserveAspectFit }
        Slider { Layout.fillWidth: true; from: 0; to: Math.max(1, player.duration); value: player.position; onMoved: player.position = value }
        RowLayout {
            ActionButton { text: player.playbackState === MediaPlayer.PlayingState ? "Pausar" : "Tocar"; onClicked: player.playbackState === MediaPlayer.PlayingState ? player.pause() : player.play() }
            ActionButton { text: "Parar"; onClicked: root.parar() }
            ComboBox { model: ["0.5×", "1×", "1.5×", "2×"]; currentIndex: 1; onActivated: player.playbackRate = [0.5, 1, 1.5, 2][currentIndex] }
            Label { text: Math.floor(player.position / 60000) + " / " + Math.floor(player.duration / 60000) + " min"; color: Theme.muted }
        }
    }
}
