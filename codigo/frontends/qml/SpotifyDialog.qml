import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "spotifyDialog"
    signal configureProviders()
    signal showDownloads()
    title: "Bibliotecas de música · catálogo para sua coleção local"
    anchors.centerIn: parent
    width: Math.min(950, ApplicationWindow.window ? ApplicationWindow.window.width - 60 : parent.width - 60)
    height: Math.min(750, ApplicationWindow.window ? ApplicationWindow.window.height - 40 : parent.height - 40)
    modal: true; standardButtons: Dialog.Close
    contentItem: ColumnLayout {
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            Label { text: hub.spotifyEstado.conectado ? "Spotify conectado" : hub.spotifyEstado.aguardando ? "Autorize no navegador e cole o código abaixo se a volta falhar…" : "Busque grátis nas bibliotecas públicas ou conecte sua conta"; color: Theme.accent; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            ActionButton { text: "Configurar…"; onClicked: dialog.configureProviders() }
            ActionButton { text: hub.spotifyEstado.conectado ? "Desconectar" : hub.spotifyEstado.configurado ? "Conectar Spotify" : "Configurar Spotify"; enabled: !hub.spotifyEstado.aguardando; onClicked: { if (!hub.spotifyEstado.configurado) dialog.configureProviders(); else if (hub.spotifyEstado.conectado) hub.desconectarSpotify(); else hub.conectarSpotify() } }
        }
        RowLayout {
            visible: hub.spotifyEstado.aguardando && !hub.spotifyEstado.conectado
            Layout.fillWidth: true
            TextField { id: authCode; objectName: "spotifyAuthCodeField"; Layout.fillWidth: true; placeholderText: "Código 'code=…' da URL de retorno (se o navegador não voltar sozinho)"; onAccepted: hub.colarCodigoSpotify(text) }
            ActionButton { text: "Usar código"; enabled: !hub.ocupado && authCode.text.length > 0; onClicked: hub.colarCodigoSpotify(authCode.text) }
        }
        Rectangle {
            visible: !hub.spotifyEstado.configurado && !hub.spotifyEstado.conectado
            Layout.fillWidth: true; radius: 10; color: Theme.surface; border.color: Theme.line
            implicitHeight: guide.implicitHeight + 24
            ColumnLayout {
                id: guide
                anchors.fill: parent; anchors.margins: 12; spacing: 6
                Label { text: "Sem conta, sem problema — a busca abaixo já funciona."; font.bold: true; color: Theme.text }
                Label { text: "1. Digite artista/faixa e Buscar · 2. Marque e envie à fila · 3. Conta Spotify só libera playlists e curtidas (Configurar…)."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            TextField { id: query; objectName: "spotifySearchField"; Layout.fillWidth: true; placeholderText: "Artista/faixa (grátis) ou link Spotify"; onAccepted: dialog.pesquisar() }
            ComboBox {
                id: fonteBox; objectName: "musicSourceBox"; implicitWidth: 150
                model: ["Todas", "Deezer", "iTunes", "MusicBrainz", "Spotify"]
                ToolTip.visible: hovered; ToolTip.text: "Spotify exige conta ou Client Secret"
            }
            ActionButton { text: "Buscar"; enabled: !hub.ocupado; onClicked: dialog.pesquisar() }
            ActionButton { text: "Atualizar"; enabled: !hub.ocupado && query.text.length >= 2; ToolTip.visible: hovered; ToolTip.text: "Ignora o cache local"; onClicked: hub.pesquisarMusicas(query.text, dialog.fonteChave(), true) }
        }
        RowLayout {
            Layout.fillWidth: true
            ActionButton { text: "Minhas playlists"; enabled: !hub.ocupado && hub.spotifyEstado.conectado; onClicked: hub.consultarSpotify("playlists", "", false); ToolTip.visible: hovered && !hub.spotifyEstado.conectado; ToolTip.text: "Exige conta conectada" }
            ActionButton { text: "Curtidas"; enabled: !hub.ocupado && hub.spotifyEstado.conectado; onClicked: hub.consultarSpotify("salvas", "", false); ToolTip.visible: hovered && !hub.spotifyEstado.conectado; ToolTip.text: "Exige conta conectada" }
        }
        Label { objectName: "musicSearchStatus"; text: hub.musicaOnlineMensagem; color: Theme.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap; maximumLineCount: 3 }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8
            model: hub.musicaOnlineItens
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var item
                width: ListView.view.width - 12; height: 94; radius: 10; color: Theme.surface
                RowLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 12
                    CheckBox { visible: !!item.uri; checked: hub.musicaOnlineSelecionados.indexOf(item.uri || "") >= 0; onToggled: hub.alternarMusicaOnline(item.uri, checked) }
                    Image { source: item.capa_url || ""; asynchronous: true; width: 54; height: 54; fillMode: Image.PreserveAspectFit }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Label { text: item.titulo; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: (item.artista || "") + (item.album ? " · " + item.album : "") + (item.duracao_ms ? " · " + dialog.duracao(item.duracao_ms) : ""); color: Theme.muted; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                    Rectangle { radius: 6; color: Theme.raised; width: badge.implicitWidth + 14; height: 24
                        Label { id: badge; anchors.centerIn: parent; text: item.nome_fonte || item.fonte; font.pixelSize: Theme.fs(11); color: Theme.accent } }
                    ActionButton { visible: item.tipo === "playlist"; text: "Ver faixas"; enabled: !hub.ocupado; onClicked: hub.consultarSpotify("playlist", item.id, false) }
                    ActionButton { text: "Abrir ↗"; enabled: !!item.url; onClicked: hub.abrirUrl(item.url) }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            ActionButton { text: "Selecionar todas"; onClicked: hub.selecionarTodasMusicasOnline(true) }
            ActionButton { text: "Limpar seleção"; onClicked: hub.selecionarTodasMusicasOnline(false) }
            Label { text: hub.musicaOnlineSelecionados.length + " selecionada(s)"; color: Theme.muted; Layout.fillWidth: true }
            ActionButton { visible: hub.spotifyTemMais; text: "Mais resultados"; enabled: !hub.ocupado; onClicked: hub.consultarSpotify("", "", true) }
        }
        RowLayout {
            Layout.fillWidth: true
            ActionButton { text: "Enviar à fila"; Layout.fillWidth: true; enabled: hub.musicaOnlineSelecionados.length > 0 && !hub.ocupado; onClicked: { hub.enfileirarMusicasOnline(false); dialog.showDownloads() } }
            ActionButton { text: "Baixar e importar"; primary: true; Layout.fillWidth: true; enabled: hub.musicaOnlineSelecionados.length > 0 && !hub.ocupado; onClicked: { hub.enfileirarMusicasOnline(true); dialog.showDownloads() } }
        }
        Label { text: "As bibliotecas dão seleção e metadados. O downloader busca o áudio na fonte configurada e salva/importa o arquivo local, com tags e capa."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
    }
    function fonteChave() {
        return ["todas", "deezer", "itunes", "musicbrainz", "spotify"][fonteBox.currentIndex]
    }
    function pesquisar() {
        hub.pesquisarMusicas(query.text, fonteChave(), false)
    }
    function duracao(ms) {
        var s = Math.floor(ms / 1000)
        return Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2)
    }
}
