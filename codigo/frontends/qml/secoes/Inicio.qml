import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

ScrollView {
    id: home
    objectName: "homeView"
    property var shell
    clip: true; contentWidth: availableWidth
    ColumnLayout {
        width: parent.width; spacing: 18
        RowLayout {
            Layout.fillWidth: true; spacing: 18
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 190
                radius: Theme.radius; color: Theme.surface; border.color: Theme.line
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 22; spacing: 8
                    Text { text: "CONTINUAR"; color: Theme.accent; font { pixelSize: Theme.fs(12); weight: Font.Bold; letterSpacing: 2 } }
                    Text { text: hub.recentes.length ? hub.recentes[0].titulo : "Nada por aqui ainda"; color: Theme.text; font { pixelSize: Theme.fs(22); weight: Font.Bold } elide: Text.ElideRight; Layout.fillWidth: true }
                    Text { text: hub.recentes.length ? (hub.recentes[0].plataforma || "PC") + "  ·  " + Number(hub.recentes[0].horas || 0).toFixed(1) + " h" : "Jogue algo e ele aparece aqui."; color: Theme.muted; font.pixelSize: Theme.fs(14) }
                    Item { Layout.fillHeight: true }
                    ActionButton { text: "▶  Continuar jogando"; primary: true; enabled: hub.recentes.length > 0 && !hub.ocupado && !hub.emJogo; onClicked: hub.jogar(hub.recentes[0].id) }
                }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 190
                radius: Theme.radius; color: Theme.surface; border.color: Theme.line
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 22; spacing: 8
                    Text { text: "COLEÇÃO · " + hub.preferencias.ativo; color: Theme.accent; font { pixelSize: Theme.fs(12); weight: Font.Bold; letterSpacing: 2 } }
                    Text { text: hub.sistema.jogos + " jogos  ·  " + hub.sistema.musicas + " músicas"; color: Theme.text; font { pixelSize: Theme.fs(20); weight: Font.DemiBold } }
                    Text { objectName: "backupStatus"; text: hub.sistema.backup; color: hub.sistema.backup_estado === "ausente" || hub.sistema.backup_estado === "antigo" ? Theme.warning : Theme.muted; font.pixelSize: Theme.subtitle; Layout.fillWidth: true; elide: Text.ElideRight }
                    Text { text: hub.sistema.pendentes + " sessão(ões) pendente(s)  ·  " + hub.sistema.disco_livre_gb + " GB livres"; color: Theme.muted; font.pixelSize: Theme.subtitle; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Item { Layout.fillHeight: true }
                    RowLayout { ActionButton { text: "Ver jogos →"; onClicked: hub.navegar("jogos") } ActionButton { text: "Backup agora"; enabled: !hub.ocupado; onClicked: hub.backup() } }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: saudeCol.implicitHeight + 44
            radius: Theme.radius; color: Theme.surface; border.color: Theme.line
            ColumnLayout {
                id: saudeCol
                anchors.fill: parent; anchors.margins: 22; spacing: 10
                Text { text: hub.aparencia.modo_simples ? "SUA COLEÇÃO" : "SAÚDE DA COLEÇÃO"; color: Theme.accent; font { pixelSize: Theme.fs(12); weight: Font.Bold; letterSpacing: 2 } }
                Text { objectName: "healthSummary"; text: !hub.saude.verificada ? "Verificando coleção…" : hub.saude.total > 0 ? hub.saude.ok + " de " + hub.saude.total + " jogos sem pendência de exe/ROM" : "Nenhum jogo cadastrado ainda."; color: Theme.text; font { pixelSize: Theme.fs(15); weight: Font.DemiBold } wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Repeater {
                    model: hub.aparencia.modo_simples ? [] : hub.saude.problemas.slice(0, 5)
                    Text { required property var modelData; text: "• " + modelData.titulo + " — " + modelData.motivo; color: Theme.muted; font.pixelSize: Theme.fs(14); elide: Text.ElideRight; Layout.fillWidth: true }
                }
                Text { objectName: "healthMore"; visible: hub.saude.pendentes > 5; text: "+" + Math.max(0, hub.saude.pendentes - 5) + " outros jogos com pendências"; color: Theme.warning; font.pixelSize: Theme.subtitle }
                RowLayout {
                    ActionButton { objectName: "viewProblemsButton"; visible: hub.saude.pendentes > 0 && !hub.aparencia.modo_simples; text: "Ver pendências →"; onClicked: hub.verPendencias() }
                    ActionButton { text: "Ver biblioteca →"; onClicked: hub.navegar("jogos") }
                    ActionButton { visible: !hub.aparencia.modo_simples; text: "Abrir sistema"; onClicked: home.shell.showSystem() }
                }
            }
        }
        Text { text: "ACESSO RÁPIDO"; color: Theme.muted; font { pixelSize: Theme.fs(13); letterSpacing: 2 } }
        GridLayout {
            Layout.fillWidth: true; columns: home.shell.width >= 1250 ? 3 : 2; columnSpacing: 18; rowSpacing: 18
            Repeater {
                model: home.shell.navSections.filter(function(s) { return s.key !== "inicio" }).concat(hub.aparencia.modo_simples ? [] : [{key: "paleta", title: "Busca global"}])
                Rectangle {
                    required property var modelData
                    Layout.fillWidth: true; Layout.preferredHeight: hub.aparencia.modo_simples ? 140 : 118
                    radius: Theme.radius; color: Theme.surface; border.color: Theme.line
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 20
                        Text { text: modelData.title; color: Theme.text; font { pixelSize: Theme.fs(17); weight: Font.DemiBold } Layout.fillWidth: true }
                        ActionButton { text: "Abrir →"; onClicked: modelData.key === "paleta" ? home.shell.openPalette() : hub.navegar(modelData.key) }
                    }
                }
            }
        }
        Label { visible: hub.recentes.length > 0; text: "JOGADOS RECENTEMENTE"; color: Theme.muted; font.pixelSize: Theme.fs(13) }
        GridLayout {
            Layout.fillWidth: true; columns: home.shell.width >= 1250 ? 4 : 2; columnSpacing: 12; rowSpacing: 12
            Repeater {
                model: hub.recentes
                Rectangle {
                    required property var modelData
                    Layout.fillWidth: true; Layout.preferredHeight: 96; color: Theme.surface; radius: Theme.radius
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 12; spacing: 12
                        Image { source: modelData.capa_url || ""; Layout.preferredWidth: 50; Layout.preferredHeight: 68; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: modelData.titulo; elide: Text.ElideRight; Layout.fillWidth: true; color: Theme.text }
                            Label { text: (modelData.plataforma || "PC") + " · " + Number(modelData.horas || 0).toFixed(1) + " h"; color: Theme.muted; font.pixelSize: Theme.fs(13) }
                        }
                        ActionButton { text: "▶"; Accessible.name: "Jogar recente"; enabled: !hub.ocupado && !hub.emJogo; onClicked: hub.jogar(modelData.id) }
                    }
                }
            }
        }
    }
}
