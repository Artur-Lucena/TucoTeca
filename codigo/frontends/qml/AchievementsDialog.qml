import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "achievementsDialog"
    property int gid: 0
    property string gameTitle: ""
    property bool showReference: false
    signal configureProviders()
    title: "Conquistas do Hub — " + gameTitle
    anchors.centerIn: parent
    width: Math.min(850, ApplicationWindow.window ? ApplicationWindow.window.width - 60 : parent.width - 60)
    height: Math.min(750, ApplicationWindow.window ? ApplicationWindow.window.height - 40 : parent.height - 40)
    modal: true; standardButtons: Dialog.Close
    onOpened: { appid.clear(); save.clear(); hub.monitorarConquistas(gid) }
    onClosed: hub.monitorarConquistas(0)
    Connections {
        target: hub
        function onConquistasMudou() {
            if (!appid.activeFocus && !appid.text) appid.text = hub.conquistas.appid || ""
            if (!save.activeFocus && !save.text) save.text = hub.conquistas.save || ""
        }
    }
    contentItem: ColumnLayout {
        spacing: 10
        Label { text: "Steam é somente a referência. Seu save local e as regras do Hub determinam os desbloqueios."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
        RowLayout {
            Layout.fillWidth: true
            TextField { id: appid; objectName: "achievementAppidField"; Layout.fillWidth: true; placeholderText: "App ID de referência (detectado automaticamente)" }
            ActionButton { text: "Sincronizar referência"; enabled: !hub.ocupado; onClicked: hub.sincronizarConquistas(dialog.gid, appid.text, save.text) }
            ActionButton { text: "Chaves…"; onClicked: dialog.configureProviders() }
        }
        RowLayout {
            Layout.fillWidth: true
            TextField { id: save; objectName: "achievementSaveField"; Layout.fillWidth: true; placeholderText: "Arquivo/pasta do save nativo (opcional)"; selectByMouse: true }
            ActionButton { text: "Escolher save…"; onClicked: saveFile.open() }
        }
        RowLayout {
            Layout.fillWidth: true
            Label { text: hub.conquistas.desbloqueadas + " / " + hub.conquistas.total + " desbloqueadas"; font.bold: true; color: Theme.accent; Layout.fillWidth: true }
            ActionButton { text: "Ler save agora"; enabled: !hub.ocupado; onClicked: hub.monitorarConquistas(dialog.gid) }
            ActionButton { text: "Regras locais…"; onClicked: rules.open() }
        }
        CheckBox { text: "Ver catálogo público de nomes e requisitos"; checked: dialog.showReference; onToggled: dialog.showReference = checked }
        Label { text: hub.conquistas.status; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8
            model: dialog.showReference ? (hub.conquistas.referencias_publicas || []) : hub.conquistas.itens
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width - 12
                height: info.implicitHeight + 28
                radius: 10; color: Theme.surface
                border.color: modelData.desbloqueada ? Theme.positive : Theme.line
                RowLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 14
                    Rectangle {
                        width: 44; height: 44; radius: 8; color: Theme.raised
                        Text { anchors.centerIn: parent; text: modelData.desbloqueada ? "★" : "☆"; font.pixelSize: 30; color: modelData.desbloqueada ? Theme.positive : Theme.muted }
                        Image { anchors.fill: parent; source: modelData.icon_url || ""; fillMode: Image.PreserveAspectFit }
                    }
                    ColumnLayout {
                        id: info
                        Layout.fillWidth: true; spacing: 5
                        Label { text: modelData.titulo; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Label { text: modelData.requisito; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
                        Label { text: dialog.showReference ? "Referência pública; não representa desbloqueio de usuário." : modelData.status + (modelData.quando ? " · " + modelData.quando : ""); color: modelData.desbloqueada ? Theme.positive : Theme.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    }
                }
            }
        }
    }
    FileDialog {
        id: saveFile
        title: "Selecione o save nativo do usuário"
        onAccepted: save.text = decodeURIComponent(selectedFile.toString().replace(Qt.platform.os === "windows" ? /^file:\/\/\// : /^file:\/\//, ""))
    }
    Dialog {
        id: rules
        title: "Regras locais do save (JSON)"
        anchors.centerIn: parent; width: Math.min(700, dialog.width - 40); height: Math.min(520, dialog.height - 40)
        modal: true; standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: hub.salvarRegrasConquistas(dialog.gid, ruleText.text)
        contentItem: ColumnLayout {
            Label { text: "Regras relacionam IDs de referência a campos do save. Operadores: eq, gte, contains e exists. Nenhum código é executado."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true
                TextArea { id: ruleText; selectByMouse: true; wrapMode: Text.Wrap; text: '{\n  "ID_DA_REFERENCIA": {"path": ["campo", "contador"], "op": "gte", "value": 10}\n}' }
            }
        }
    }
}
