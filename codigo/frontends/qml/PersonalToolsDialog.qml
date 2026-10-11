import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: dialog
    objectName: "personalToolsDialog"
    title: "Ferramentas pessoais"
    anchors.centerIn: parent
    width: Math.min(760, ApplicationWindow.window.width - 60)
    height: Math.min(740, ApplicationWindow.window.height - 60)
    modal: true; standardButtons: Dialog.Close
    onOpened: { watchPath.text = hub.preferencias.watch; autoImport.checked = hub.preferencias.watch_auto; hub.consultarEstatisticas() }
    contentItem: ScrollView {
        clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { text: "PERFIL LOCAL"; color: Theme.accent; font.bold: true }
            RowLayout {
                Repeater {
                    model: ["Tuco", "Isa"]
                    ActionButton { required property string modelData; text: modelData; selected: hub.preferencias.ativo === modelData; enabled: !hub.ocupado && !hub.emJogo; onClicked: hub.trocarPerfil(modelData) }
                }
                ActionButton { text: "Guardar filtros atuais"; enabled: !hub.ocupado; onClicked: hub.salvarFiltroPerfil() }
            }
            Label { text: "Favoritos e filtros são independentes; jogos, músicas e saves continuam compartilhados."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Label { text: "SEU ANO EM JOGOS · " + hub.estatisticasAno.ano; color: Theme.accent; font.bold: true }
            Label { text: hub.estatisticasAno.total_horas + " h registradas neste perfil (histórico novo; não inventa sessões antigas)."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 120
                Repeater {
                    model: hub.estatisticasAno.meses
                    ColumnLayout {
                        required property real modelData
                        required property int index
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 3
                        Item { Layout.fillHeight: true }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: Math.max(2, 90 * modelData / Math.max(1, Math.max.apply(null, hub.estatisticasAno.meses))); color: Theme.accent; radius: 3 }
                        Label { text: index + 1; Layout.alignment: Qt.AlignHCenter; font.pixelSize: 12 }
                    }
                }
            }
            Label { text: "ATALHOS (SOMENTE NA JANELA)"; color: Theme.accent; font.bold: true }
            RowLayout {
                Layout.fillWidth: true
                ComboBox { id: shortcutAction; model: Object.keys(hub.preferencias.atalhos); Layout.fillWidth: true; onActivated: shortcutText.text = hub.preferencias.atalhos[currentText] }
                TextField { id: shortcutText; Layout.preferredWidth: 160; placeholderText: "Ctrl+K"; selectByMouse: true }
                ActionButton { text: "Salvar"; onClicked: hub.salvarAtalho(shortcutAction.currentText, shortcutText.text) }
            }
            Label { text: "PASTA VIGIADA"; color: Theme.accent; font.bold: true }
            TextField { id: watchPath; Layout.fillWidth: true; placeholderText: "Pasta de downloads (.zip/.rar/.7z)"; selectByMouse: true }
            CheckBox { id: autoImport; text: "Importar automaticamente os pacotes estáveis"; Layout.fillWidth: true }
            Label { text: "Desligado por padrão. Ao importar com sucesso, o arquivo compactado é removido pelo fluxo existente; falhas preservam o arquivo. Pacotes de coleção nunca entram nesta automação."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.warning }
            RowLayout {
                ActionButton { text: "Escolher pasta…"; onClicked: watchFolder.open() }
                ActionButton { text: "Salvar vigia"; onClicked: hub.configurarWatch(watchPath.text, autoImport.checked) }
                ActionButton { text: "Desligar"; onClicked: { watchPath.clear(); hub.configurarWatch("", false) } }
            }
            Repeater {
                model: hub.watchProntos
                Label { required property var modelData; text: modelData.nome + (modelData.resultado ? (modelData.resultado.ok ? " · importado" : " · " + modelData.resultado.erro) : " · detectado; use Importar pacote de jogo"); Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }
            Label { text: "SPONSORBLOCK"; color: Theme.accent; font.bold: true }
            CheckBox { checked: hub.preferencias.sponsorblock; text: "Pular trechos de patrocínio no YouTube embutido"; onClicked: hub.definirSponsorBlock(checked); Layout.fillWidth: true }
            Label { text: "Opt-in: envia somente o ID do vídeo ao SponsorBlock. Não remove publicidade da plataforma."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Label { text: "API LOCAL (LEITURA)"; color: Theme.accent; font.bold: true }
            ActionButton { text: hub.apiLocal.ativa ? "Desligar API" : "Ligar em 127.0.0.1"; enabled: !hub.ocupado; onClicked: hub.definirApiLocal(!hub.apiLocal.ativa) }
            TextArea { visible: hub.apiLocal.ativa; Layout.fillWidth: true; readOnly: true; selectByMouse: true; wrapMode: TextEdit.WrapAnywhere; text: hub.apiLocal.url + "\nAuthorization: Bearer " + hub.apiLocal.token + "\nGET /status · /jogos · /musicas · /desejos" }
            ActionButton { text: "Atualizar yt-dlp/FFmpeg (SHA-256 fixado)"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: hub.atualizarAudio() }
        }
    }
    FolderDialog { id: watchFolder; title: "Pasta vigiada"; onAccepted: watchPath.text = hub.caminhoLocal(selectedFolder) }
}
