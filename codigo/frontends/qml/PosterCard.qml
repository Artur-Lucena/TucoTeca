import QtQuick
import QtQuick.Controls

Item {
    id: card
    required property var game
    property bool selected: false
    signal chosen()
    signal activated()
    signal details()
    property bool hovered: pointer.containsMouse
    Accessible.role: Accessible.Button
    Accessible.name: game.titulo || "Jogo"
    Accessible.onPressAction: card.chosen()
    Rectangle {
        id: art
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 7 }
        height: parent.height - 66
        radius: 12
        color: Theme.raised
        border.color: card.selected ? Theme.accent : card.hovered ? "#64849c" : Theme.line
        border.width: card.selected ? 3 : 1
        scale: card.hovered ? 1.018 : 1
        Behavior on scale { NumberAnimation { duration: Theme.motion; easing.type: Easing.OutCubic } }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 4
            radius: 9
            gradient: Gradient {
                GradientStop { position: 0; color: "#28435c" }
                GradientStop { position: 1; color: "#182034" }
            }
        }
        Text {
            anchors.centerIn: parent
            width: parent.width - 30
            text: (card.game.titulo || "?").substring(0, 2).toUpperCase()
            font { family: Theme.family; pixelSize: 50; weight: Font.Light }
            color: "#6a8aa7"
            horizontalAlignment: Text.AlignHCenter
        }
        Image {
            anchors.fill: parent
            anchors.margins: 4
            source: card.game.capa_url || ""
            asynchronous: true
            fillMode: Image.PreserveAspectCrop
            sourceSize: Qt.size(420, 560)
            visible: status === Image.Ready
        }
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 4 }
            height: 68
            gradient: Gradient {
                GradientStop { position: 0; color: "transparent" }
                GradientStop { position: 1; color: "#d9091220" }
            }
        }
        Rectangle {
            x: 13; y: 13
            width: platform.implicitWidth + 18; height: 27; radius: 7
            color: "#e0101a29"
            Text {
                id: platform
                anchors.centerIn: parent
                text: card.game.plataforma || "PC"
                color: Theme.text
                font { family: Theme.family; pixelSize: 12; weight: Font.Bold }
            }
        }
        Text {
            anchors { right: parent.right; top: parent.top; margins: 14 }
            text: card.game.favorito ? "★" : ""
            font.pixelSize: 21
            color: "#f5d587"
        }
        Text {
            anchors { left: parent.left; bottom: parent.bottom; margins: 15 }
            text: card.selected ? "PRONTO PARA JOGAR" : ""
            color: Theme.accent
            font { family: Theme.family; pixelSize: Theme.kicker; weight: Font.Bold; letterSpacing: 0.5 }
        }
    }
    Text {
        anchors { left: parent.left; right: parent.right; top: art.bottom; margins: 9 }
        text: card.game.titulo || ""
        color: Theme.text
        font { family: Theme.family; pixelSize: Theme.card; weight: Font.DemiBold }
        elide: Text.ElideRight
    }
    Text {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 9 }
        text: (card.game.status || "backlog") + "  ·  " + Number(card.game.horas || 0).toFixed(1) + " h"
        color: Theme.muted
        font { family: Theme.family; pixelSize: Theme.meta }
        elide: Text.ElideRight
    }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(mouse) { card.chosen(); if (mouse.button === Qt.RightButton) card.details() }
        onDoubleClicked: card.activated()
    }
}
