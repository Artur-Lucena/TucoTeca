import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "piratasDialog"
    title: "Pacotes em Piratas · extrair, instalar e importar"
    anchors.centerIn: parent
    width: Math.min(860, ApplicationWindow.window ? ApplicationWindow.window.width - 60 : parent.width - 60)
    height: Math.min(680, ApplicationWindow.window ? ApplicationWindow.window.height - 40 : parent.height - 40)
    modal: true; standardButtons: Dialog.Close
    onOpened: hub.atualizarPacotes()
    contentItem: ColumnLayout {
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            Text {
                text: "Tudo aqui acontece dentro do Hub: extrair, instalar e importar."
                color: Theme.muted
                Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: Theme.subtitle
            }
            ActionButton { text: "↻ Atualizar"; enabled: !hub.ocupado; onClicked: hub.atualizarPacotes() }
        }
        Label {
            visible: !hub.tem7z()
            Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.warning
            text: "Sem 7-Zip encontrado: só .zip extrai aqui. Instale o 7-Zip, use D:\\Games\\ferramentas\\7z.exe ou aponte BIBLIOTECA_7Z."
        }
        Label { objectName: "pacotesResumo"; text: hub.pacotesPiratas.length + " pacote(s) pendente(s)"; color: Theme.muted }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 10
            model: hub.pacotesPiratas
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var item
                width: ListView.view.width - 12
                implicitHeight: 92; radius: 10; color: Theme.surface
                RowLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 14
                    Rectangle {
                        Layout.preferredWidth: 40; Layout.minimumWidth: 40; Layout.maximumWidth: 40
                        Layout.preferredHeight: 40; Layout.minimumHeight: 40; Layout.maximumHeight: 40
                        radius: 10; color: Theme.raised
                        Text {
                            anchors.centerIn: parent
                            text: item.tipo === "arquivo" ? "📦" : "📁"
                            color: Theme.accent; font.pixelSize: 18
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 4
                        Text {
                            text: item.nome
                            color: Theme.text; font { pixelSize: 15; weight: Font.DemiBold }
                            Layout.fillWidth: true; elide: Text.ElideRight
                        }
                        Text {
                            text: {
                                if (item.estado === "compactado" || item.estado === "falta-7z")
                                    return "Compactado · " + item.tamanho_mb + " MB"
                                if (item.estado === "pronta")
                                    return "Extraído · executável pronto"
                                if (item.estado === "instalar")
                                    return "Extraído · precisa instalar"
                                return item.estado
                            }
                            color: item.estado === "pronta" ? Theme.positive : Theme.muted
                            font.pixelSize: Theme.subtitle; Layout.fillWidth: true; elide: Text.ElideRight
                        }
                    }
                    Rectangle {
                        radius: 6; color: Theme.raised
                        Layout.preferredWidth: Math.max(96, estadoLbl.implicitWidth + 16)
                        Layout.preferredHeight: 24
                        Label {
                            id: estadoLbl
                            anchors.centerIn: parent
                            text: item.estado === "falta-7z" ? "sem 7-Zip" : item.estado
                            color: item.estado === "pronta" ? Theme.positive :
                                   item.estado === "falta-7z" ? Theme.warning : Theme.muted
                            font.pixelSize: 11
                        }
                    }
                    ActionButton {
                        visible: item.tipo === "arquivo" && item.estado !== "falta-7z"
                        text: item.estado === "compactado" ? "Extrair" : "Preparar de novo"
                        enabled: !hub.ocupado
                        onClicked: hub.prepararPacote(item.caminho)
                    }
                    ActionButton {
                        visible: item.estado === "instalar" && item.setup.length > 0
                        text: "Abrir instalador"
                        enabled: !hub.ocupado
                        onClicked: hub.abrirInstaladorPacote(item.setup)
                    }
                    ActionButton {
                        visible: item.estado === "pronta" || (item.estado === "instalar" && item.setup.length > 0)
                        text: item.estado === "pronta" ? "Importar" : "Já instalei…"
                        primary: true; enabled: !hub.ocupado
                        onClicked: {
                            pacoteAlvo.pasta = item.pasta
                            pacoteAlvo.estado = item.estado
                            pacoteAlvo.nome = item.nome
                            pacoteExeDialog.open()
                        }
                    }
                }
            }
        }
        Text {
            visible: hub.pacotesPiratas.length === 0
            text: "Nada pendente em Piratas/: pacote compacto só aparece aqui depois de baixar, e o que entra na coleção sai da lista."
            color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true
        }
    }

    Dialog {
        id: pacoteExeDialog
        objectName: "pacoteExeDialog"
        title: "Importar " + pacoteAlvo.nome
        anchors.centerIn: parent
        width: Math.min(560, ApplicationWindow.window ? ApplicationWindow.window.width - 60 : parent.width - 60)
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: hub.importarPacote(pacoteAlvo.pasta, pacoteExe.text)
        contentItem: ColumnLayout {
            width: parent.width; spacing: 12
            Label {
                text: pacoteAlvo.estado === "pronta"
                      ? "O Hub achou o executável. Confirme a importação para a coleção."
                      : "Depois de instalar, informe o .exe do jogo (o Hub usa esse caminho)."
                wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
            Label { text: "Executável"; color: Theme.muted }
            RowLayout {
                Layout.fillWidth: true
                TextField {
                    id: pacoteExe; objectName: "pacoteExeField"
                    Layout.fillWidth: true; selectByMouse: true
                    placeholderText: "Caminho do .exe do jogo"
                }
                ActionButton { text: "Escolher…"; onClicked: pacoteExeBrowser.open() }
            }
            FileDialog {
                id: pacoteExeBrowser
                title: "Escolha o executável do jogo"
                nameFilters: ["Executáveis (*.exe)"]
                onAccepted: pacoteExe.text = decodeURIComponent(selectedFile.toString().replace(/^file:\/\/\//, ""))
            }
            Label {
                text: "A importação cria o jogo com o nome canônico e mantém a pasta onde está."
                wrapMode: Text.WordWrap; Layout.fillWidth: true; color: Theme.muted
            }
        }
    }

    QtObject {
        id: pacoteAlvo
        property string pasta: ""
        property string estado: ""
        property string nome: ""
    }
}
