import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: volumeControl
    implicitWidth: 240
    spacing: 2
    Text {
        text: "VOLUME DO PC"
        color: Theme.muted
        font { family: Theme.family; pixelSize: Theme.kicker; weight: Font.DemiBold }
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 8
        ActionButton {
            text: hub.volume.mudo ? "×♪" : "♪"
            implicitWidth: 38; implicitHeight: 34
            enabled: hub.volume.ok === true
            Accessible.name: hub.volume.mudo ? "Ativar som do PC" : "Silenciar PC"
            ToolTip.visible: hovered; ToolTip.text: Accessible.name
            onClicked: hub.silenciar()
        }
        Slider {
            id: pcVolume
            objectName: "pcVolumeSlider"
            Layout.fillWidth: true; Layout.minimumWidth: 70; Layout.preferredWidth: 140
            implicitHeight: 34
            from: 0; to: 100; stepSize: 1
            enabled: hub.volume.ok === true
            Accessible.name: "Volume geral do PC"
            onMoved: commitVolume.restart()
            onPressedChanged: {
                if (!pressed && enabled) {
                    commitVolume.stop()
                    hub.definirVolume(value)
                }
            }
            background: Rectangle {
                x: pcVolume.leftPadding
                y: pcVolume.topPadding + (pcVolume.availableHeight - height) / 2
                width: pcVolume.availableWidth; height: 6; radius: 3
                color: Theme.line
                Rectangle {
                    width: pcVolume.visualPosition * parent.width; height: parent.height; radius: 3
                    color: hub.volume.mudo ? Theme.muted : Theme.accent
                }
            }
            handle: Rectangle {
                x: pcVolume.leftPadding + pcVolume.visualPosition * (pcVolume.availableWidth - width)
                y: pcVolume.topPadding + (pcVolume.availableHeight - height) / 2
                width: 18; height: 18; radius: 9
                color: pcVolume.enabled ? Theme.accent : Theme.muted
                border.color: pcVolume.activeFocus ? Theme.text : Theme.line
                border.width: pcVolume.activeFocus ? 2 : 1
            }
        }
        Text {
            objectName: "pcVolumePercent"
            text: hub.volume.ok ? Math.round(pcVolume.value) + "%" : "—"
            color: Theme.text; font { family: Theme.family; pixelSize: Theme.meta }
            Layout.preferredWidth: 40
            horizontalAlignment: Text.AlignRight
        }
    }
    Timer {
        id: commitVolume
        interval: 80
        onTriggered: hub.definirVolume(pcVolume.value)
    }
    Connections {
        target: hub
        function onVolumeMudou() {
            if (!pcVolume.pressed && !commitVolume.running && hub.volume.ok)
                pcVolume.value = hub.volume.nivel
        }
    }
    Component.onCompleted: pcVolume.value = hub.volume.nivel || 0
}
