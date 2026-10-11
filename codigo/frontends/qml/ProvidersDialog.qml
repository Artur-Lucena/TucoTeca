import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "providersDialog"
    title: "Provedores online"
    anchors.centerIn: parent
    width: Math.min(600, ApplicationWindow.window ? ApplicationWindow.window.width - 60 : parent.width - 60)
    height: Math.min(590, ApplicationWindow.window ? ApplicationWindow.window.height - 40 : parent.height - 40)
    modal: true; standardButtons: Dialog.Save | Dialog.Cancel
    onAccepted: hub.configurarProvedores(steamKey.text, steamgridKey.text, spotifyId.text, spotifySecret.text)
    contentItem: ScrollView {
        clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { text: "Sem chave: Steam (capas/IDs), Wikipedia, iTunes, MusicBrainz/CAA e Deezer."; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Label { text: "Steam Web API — catálogo completo de referência"; font.bold: true }
            TextField { id: steamKey; objectName: "steamProviderKey"; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: hub.provedoresOnline.steam_key ? "Já configurada; vazio preserva" : "Chave opcional" }
            Label { text: "Fornece nomes, descrições e ícones das conquistas. O Hub calcula os desbloqueios no save local."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
            ActionButton { text: "Obter chave Steam ↗"; onClicked: hub.abrirUrl("https://steamcommunity.com/dev/apikey") }
            Label { text: "SteamGridDB — pôsteres e arte alternativa"; font.bold: true }
            TextField { id: steamgridKey; objectName: "steamgridProviderKey"; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: hub.provedoresOnline.steamgriddb_key ? "Já configurada; vazio preserva" : "Chave opcional SteamGridDB" }
            ActionButton { text: "Configurar SteamGridDB ↗"; onClicked: hub.abrirUrl("https://www.steamgriddb.com/profile/preferences") }
            Label { text: "Spotify — busca pública e playlists da sua conta"; font.bold: true }
            TextField { id: spotifyId; objectName: "spotifyClientIdField"; Layout.fillWidth: true; placeholderText: hub.provedoresOnline.spotify_client_id ? "Client ID já configurado; vazio preserva" : "Client ID do aplicativo Spotify" }
            TextField { id: spotifySecret; objectName: "spotifyClientSecretField"; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: hub.provedoresOnline.spotify_client_secret ? "Client Secret já configurado; vazio preserva" : "Client Secret (busca sem login)" }
            Label { text: "Com ID + Secret, a busca funciona sem conectar a conta. Conectar a conta libera playlists e curtidas."; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
            Label { text: "No aplicativo Spotify, registre o Redirect URI:\n" + hub.spotifyEstado.redirect; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted }
            ActionButton { text: "Abrir painel Spotify ↗"; onClicked: hub.abrirUrl("https://developer.spotify.com/dashboard") }
        }
    }
}
