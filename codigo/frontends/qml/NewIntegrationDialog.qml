import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "newIntegrationDialog"
    title: "Adicionar integração"
    anchors.centerIn: parent
    width: Math.min(560, ApplicationWindow.window ? ApplicationWindow.window.width - 60 : parent.width - 60)
    modal: true; standardButtons: Dialog.Save | Dialog.Cancel
    onAccepted: hub.adicionarIntegracao(keyField.text, nameField.text, descField.text,
                                       ["link", "catalogo", "emulador", "download"][typeBox.currentIndex],
                                       urlField.text)
    onOpened: { keyField.clear(); nameField.clear(); descField.clear(); urlField.clear(); typeBox.currentIndex = 0 }
    contentItem: ColumnLayout {
        spacing: 12
        Label { text: "Atalho salvo nesta coleção. Sem plugins: só abre páginas https."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
        Label { text: "Chave (identificador único)" }
        TextField { id: keyField; objectName: "integrationKeyField"; Layout.fillWidth: true; placeholderText: "ex.: meu-site" }
        Label { text: "Nome" }
        TextField { id: nameField; Layout.fillWidth: true; placeholderText: "ex.: Meu site de mods" }
        Label { text: "Descrição" }
        TextField { id: descField; Layout.fillWidth: true; placeholderText: "O que este atalho abre" }
        Label { text: "Tipo" }
        ComboBox { id: typeBox; Layout.fillWidth: true; model: ["Atalho (abre página)", "Catálogo (abre busca)", "Emulador", "Download"] }
        Label { text: "URL https (use {q} onde vai a busca)" }
        TextField { id: urlField; Layout.fillWidth: true; placeholderText: "https://exemplo.com/busca?q={q}"; selectByMouse: true }
    }
    footer: DialogButtonBox {
        Button {
            objectName: "saveIntegrationButton"
            text: "Adicionar"; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            enabled: keyField.acceptableInput && keyField.text.length >= 2 && nameField.text.length >= 2
        }
        Button { text: "Cancelar"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
        onAccepted: dialog.accept()
        onRejected: dialog.reject()
    }
}
