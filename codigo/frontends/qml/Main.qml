import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Window
import "secoes" as Secoes

ApplicationWindow {
    id: window
    objectName: "hubWindow"
    width: 1440; height: 920
    minimumWidth: 960; minimumHeight: 640
    visible: true
    title: "TucoTeca"
    color: Theme.bg
    font.family: Theme.family
    font.pixelSize: Theme.subtitle
    Component.onCompleted: { Theme.tema = hub.aparencia.tema; Theme.densidade = hub.aparencia.densidade }
    palette {
        window: Theme.bg; windowText: Theme.text; base: Theme.surface
        text: Theme.text; button: Theme.raised; buttonText: Theme.text
        highlight: Theme.accent; highlightedText: Theme.ink
        placeholderText: Theme.muted; mid: Theme.line; dark: Theme.surface
    }
    property bool immersive: false
    readonly property var games: hub.secao === "jogos" ? sectionLoader.item : null
    readonly property var collection: ["musicas", "videos", "desejos", "downloads"].indexOf(hub.secao) >= 0 ? sectionLoader.item : null
    readonly property var youtubeLoader: sectionLoader
    property string previousVisibility: "window"
    property string currentSection: hub.secao
    property var notificationQueue: []
    property bool showingNotification: false
    property var sections: [
        {key: "inicio", title: "Início"}, {key: "jogos", title: "Jogos"},
        {key: "musicas", title: "Músicas"}, {key: "desejos", title: "Desejos"},
        {key: "downloads", title: "Downloads"}, {key: "integracoes", title: "Integrações"},
        {key: "videos", title: "Vídeos"}, {key: "youtube", title: "YouTube"}
    ]
    // Modo simples (Isa): só as telas do dia a dia no menu; atalhos continuam válidos.
    readonly property var navSections: hub.aparencia.modo_simples
        ? sections.filter(function(s) { return s.key === "inicio" || s.key === "jogos" || s.key === "musicas" })
        : sections
    property var titles: ({inicio: "Boas-vindas ao seu hub.", jogos: "Sua próxima aventura.",
                          musicas: "Dê o play no seu mundo.", desejos: "O que vem a seguir.",
                          downloads: "A caminho da sua coleção.", integracoes: "Seu hub, conectado.",
                          videos: "Sua videoteca, no mesmo lugar.",
                          youtube: "Assista e baixe sem sair do Hub."})
    property var subtitles: ({inicio: "Continuar, buscar e cuidar da coleção — sem sair do lugar.",
        jogos: "Todos os seus jogos. Um lugar para começar.",
        musicas: "Sua coleção local, com música em todas as telas.",
        desejos: "Guarde os títulos que você quer jogar.",
        downloads: "Progresso do qBittorrent, sem sair do Hub.",
        integracoes: "Catálogos, emuladores e serviços com responsabilidades independentes.",
        videos: "Importe arquivos locais, pesquise YouTube e abra no reprodutor escolhido.",
        youtube: "Navegue no YouTube aqui dentro; baixar é sempre ação sua."})

    function toggleImmersive() {
        if (!immersive) {
            previousVisibility = visibility === Window.Maximized ? "maximized" : "window"
            immersive = true
            showFullScreen()
        } else {
            immersive = false
            if (previousVisibility === "maximized") showMaximized(); else showNormal()
        }
        if (games) games.forceActiveFocus()
        else if (collection) collection.forceActiveFocus()
    }
    function notify(message, error) {
        notificationQueue = notificationQueue.concat([{message: message, error: error}])
        if (!showingNotification) showNextNotification()
    }
    function showNextNotification() {
        if (notificationQueue.length === 0) return
        let next = notificationQueue[0]
        notificationQueue = notificationQueue.slice(1)
        showingNotification = true
        toast.message = next.message
        toast.error = next.error
        toast.open()
        toastTimer.restart()
    }
    function openPalette() {
        paletteQuery.clear()
        hub.buscarPaleta("")
        palette.open()
        paletteQuery.forceActiveFocus()
    }
    function registerHours(game, file) {
        sessionDialog.gid = game.id || game.gid || 0
        sessionDialog.file = file || ""
        sessionDialog.gameTitle = game.titulo || "Jogo"
        sessionHours.clear()
        sessionDialog.open()
        sessionHours.forceActiveFocus()
    }
    function openCovers(category, item) {
        covers.category = category
        covers.ident = item.id
        covers.itemTitle = item.titulo
        covers.open()
    }
    function openAchievements(game) {
        achievements.gid = game.id
        achievements.gameTitle = game.titulo
        achievements.open()
    }
    function editGame(game) {
        gameDialog.gid = game.id || 0
        gameTitle.text = game.titulo || ""
        gameExe.text = game.executable_path || ""
        gameArgs.text = game.launch_options || ""
        gameStatus.currentIndex = Math.max(0, gameStatus.model.indexOf(game.status || "backlog"))
        gameNota.text = (game.nota === null || game.nota === undefined) ? "" : String(game.nota)
        gameTags.text = game.etiquetas || ""
        gameDialog.open()
    }
    function deleteItem(category, item) {
        deleteDialog.category = category
        deleteDialog.ident = item.id
        deleteDialog.itemTitle = item.titulo
        deleteDialog.open()
    }
    function playVideo(id) {
        if (videoPlayer.currentText === "Interno") hub.prepararVideoInterno(id)
        else hub.reproduzirVideo(id, ({"Automático": "auto", "VLC": "vlc", "MPV": "mpv", "MPC-HC": "mpchc"})[videoPlayer.currentText] || "auto")
    }
    function showDetails() { details.open() }
    function showSystem() { sistema.open() }
    function showYoutubeSearch() { youtube.open() }
    function showLyrics(item) {
        hub.buscarLetras(item.artista || "", item.titulo || "", item.album || "", item.duracao_s || Math.floor((item.duracao_ms || 0) / 1000))
        letrasDialog.open()
    }
    function findSources(item) { hub.buscarFontesDesejo(item.titulo); fontesDialog.abrir(item.id, item.titulo) }
    function useIntegration(item) {
        if (item.url && item.url.indexOf("{q}") >= 0) { integrationQuery.chave = item.chave; integrationQuery.title = item.nome; customQuery.clear(); integrationQuery.open() }
        else if (item.url) hub.abrirIntegracao(item.chave, "")
        else if (item.tipo === "catalogo") { catalogDialog.provider = item.chave; catalogDialog.title = item.nome; catalogQuery.clear(); catalogDialog.open() }
        else if (item.tipo === "download") hub.navegar("downloads")
        else if (item.tipo === "musicas_online") spotifyCatalog.open()
        else if (item.tipo === "provedores") providers.open()
        else settings.open()
    }
    onClosing: function(close) {
        if (hub.ocupado) {
            close.accepted = false
            notify("Concluindo a operação atual. Aguarde para fechar.", false)
        }
    }
    FolderDialog {
        id: exportFolder
        title: "Escolha a pasta de destino (ex.: pendrive)"
        onAccepted: hub.exportarColecao(selectedFolder)
    }
    Dialog {
        id: letrasDialog
        objectName: "letrasDialog"
        title: "Letra"
        anchors.centerIn: parent
        width: Math.min(640, window.width - 80)
        height: Math.min(560, window.height - 80)
        modal: true; standardButtons: Dialog.Close
        contentItem: ColumnLayout {
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true
                visible: hub.letras.sincronizadas
                model: hub.letras.linhas || []; clip: true; spacing: 10
                currentIndex: hub.letraIndice
                onCurrentIndexChanged: { if (currentIndex >= 0) positionViewAtIndex(currentIndex, ListView.Center) }
                ScrollBar.vertical: ScrollBar {}
                delegate: Text {
                    required property var modelData
                    required property int index
                    width: ListView.view.width - 16
                    text: modelData.texto; wrapMode: Text.WordWrap
                    color: index === hub.letraIndice ? Theme.accent : Theme.text
                    font.bold: index === hub.letraIndice; font.pixelSize: 18
                }
            }
            ScrollView {
                visible: !hub.letras.sincronizadas
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true; contentWidth: availableWidth
                TextArea { readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; color: Theme.text; text: hub.letras.ok ? hub.letras.texto : (hub.letras.erro || "Buscando letra…") }
            }
        }
    }

    Dialog {
        id: fontesDialog
        objectName: "fontesDialog"
        property int did: 0
        property string titulo: ""
        function abrir(id, t) { did = id; titulo = t; open() }
        title: "Fontes para: " + titulo
        anchors.centerIn: parent
        width: Math.min(720, window.width - 80)
        height: Math.min(600, window.height - 80)
        modal: true; standardButtons: Dialog.Close
        contentItem: ScrollView {
            clip: true; contentWidth: availableWidth
            ColumnLayout {
                width: parent.width; spacing: 10
                Text { text: "SteamRip — download direto (host automático)"; color: Theme.accent; font.pixelSize: 13; visible: hub.fontesDesejo.steamrip.length > 0 }
                Repeater {
                    model: hub.fontesDesejo.steamrip
                    RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Text { text: modelData.titulo; color: Theme.text; Layout.fillWidth: true; elide: Text.ElideRight }
                        ActionButton { text: "Baixar e importar"; primary: true; enabled: !hub.ocupado; onClicked: hub.baixarDesejoSteamRip(modelData.url, fontesDialog.did) }
                        ActionButton { text: "Abrir ↗"; onClicked: hub.abrirUrl(modelData.url) }
                    }
                }
                Text { text: "FitGirl — abre a página para escolher os links"; color: Theme.accent; font.pixelSize: 13; visible: hub.fontesDesejo.fitgirl.length > 0 }
                Repeater {
                    model: hub.fontesDesejo.fitgirl
                    RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Text { text: modelData.titulo; color: Theme.text; Layout.fillWidth: true; elide: Text.ElideRight }
                        ActionButton { text: "Abrir página ↗"; onClicked: hub.abrirUrl(modelData.url) }
                    }
                }
                Text { text: hub.fontesDesejo.erros.join("; "); color: Theme.warning; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 13; visible: hub.fontesDesejo.erros.length > 0 }
            }
        }
    }

    Shortcut { sequence: hub.preferencias.atalhos.tela_cheia; onActivated: window.toggleImmersive() }
    Shortcut { sequence: "Escape"; onActivated: { if (window.immersive) window.toggleImmersive() } }
    Shortcut { sequence: hub.preferencias.atalhos.buscar; onActivated: { if (search.visible) { search.forceActiveFocus(); search.selectAll() } else window.openPalette() } }
    Shortcut { sequence: hub.preferencias.atalhos.paleta; onActivated: window.openPalette() }
    Shortcut { sequence: hub.preferencias.atalhos.inicio; onActivated: hub.navegar("inicio") }
    Shortcut { sequence: hub.preferencias.atalhos.jogos; onActivated: hub.navegar("jogos") }
    Shortcut { sequence: hub.preferencias.atalhos.musicas; onActivated: hub.navegar("musicas") }
    Shortcut { sequence: hub.preferencias.atalhos.desejos; onActivated: hub.navegar("desejos") }
    Shortcut { sequence: hub.preferencias.atalhos.downloads; onActivated: hub.navegar("downloads") }
    Shortcut { sequence: hub.preferencias.atalhos.integracoes; onActivated: hub.navegar("integracoes") }
    Shortcut { sequence: hub.preferencias.atalhos.videos; onActivated: hub.navegar("videos") }
    Shortcut { sequence: hub.preferencias.atalhos.youtube; onActivated: hub.navegar("youtube") }
    Connections {
        target: hub
        function onAviso(message, error) { window.notify(message, error) }
        function onControleAcao(acao) { if (acao === "menu") window.openPalette() }
        function onMudou() {
            if (search.text !== hub.busca) search.text = hub.busca
            if (sistema.visible && !hub.ocupado) sistema.refresh()
            Theme.tema = hub.aparencia.tema
            Theme.densidade = hub.aparencia.densidade
            if (hub.secao === "jogos") {
                if (games && games.currentIndex !== hub.indiceSelecionado) games.currentIndex = hub.indiceSelecionado
            } else if (hub.secao !== "integracoes" && hub.secao !== "inicio") {
                if (collection && collection.currentIndex !== hub.indiceSelecionado) collection.currentIndex = hub.indiceSelecionado
            }
        }
        function onJogoIniciado() { window.showMinimized() }
        function onVideoLocalPronto(video) { internalVideo.video = video; internalVideo.open() }
        function onJogoTerminou() {
            if (window.immersive) window.showFullScreen(); else window.showNormal()
            window.requestActivate()
        }
    }

    header: Rectangle {
        height: 88
        color: Theme.bg
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.line }
        RowLayout {
            id: headerRow
            readonly property real navigationWidth: Math.max(54, (width - 38 -
                (headerBrand.visible ? headerBrand.implicitWidth + 28 + spacing : 0) -
                Math.min(headerSearchButton.implicitWidth, window.width < 1100 ? 70 : 160) -
                Math.min(headerImmersiveButton.implicitWidth, window.width < 1100 ? 56 : 120) -
                50 - spacing * (window.sections.length + 4)) / window.sections.length)
            anchors.fill: parent
            anchors.leftMargin: window.width < 1100 ? 20 : 30
            anchors.rightMargin: window.width < 1100 ? 20 : 30
            spacing: window.width < 1100 ? 8 : 12
            Rectangle {
                width: 38; height: 38; radius: 12
                gradient: Gradient {
                    GradientStop { position: 0; color: "#91e6ee" }
                    GradientStop { position: 1; color: "#638bff" }
                }
                Text { anchors.centerIn: parent; text: "T"; font { pixelSize: 24; weight: Font.Black } color: Theme.ink }
            }
            Text {
                id: headerBrand
                visible: window.width >= 1360
                text: "TUCOTECA"; color: Theme.text
                font { pixelSize: 16; weight: Font.Bold; letterSpacing: 2 }
                Layout.rightMargin: 28
            }
            Repeater {
                model: window.navSections
                ActionButton {
                    required property var modelData
                    objectName: "nav_" + modelData.key
                    text: modelData.title
                    selected: hub.secao === modelData.key
                    quiet: true
                    font.pixelSize: window.immersive ? 16 : 14
                    Layout.maximumWidth: headerRow.navigationWidth
                    onClicked: { hub.navegar(modelData.key); search.text = "" }
                    ToolTip.visible: hovered
                    ToolTip.text: "Abrir " + modelData.title
                    Rectangle {
                        anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
                        width: parent.width - 26; height: 2; radius: 1
                        color: Theme.accent
                        visible: parent.selected
                    }
                }
            }
            Item { Layout.fillWidth: true }
            ActionButton {
                id: headerSearchButton
                objectName: "globalSearchButton"
                text: window.width < 1100 ? "Buscar" : "⌘ Buscar · Ctrl+K"; quiet: true
                Layout.maximumWidth: window.width < 1100 ? 70 : 160
                onClicked: window.openPalette()
                ToolTip.visible: hovered; ToolTip.text: "Busca global · Ctrl+K"
            }
            ActionButton {
                id: headerImmersiveButton
                objectName: "immersiveButton"
                text: window.width < 1100 ? "F11" : window.immersive ? "Sair · F11" : "Big Picture"
                Layout.maximumWidth: window.width < 1100 ? 56 : 120
                onClicked: window.toggleImmersive()
                ToolTip.visible: hovered; ToolTip.text: "Tela cheia · F11"
            }
            ActionButton { objectName: "settingsButton"; text: "⚙"; font.pixelSize: 20; Layout.maximumWidth: 50; onClicked: settings.open(); Accessible.name: "Configurações" }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 30
        spacing: 18
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Text {
                    text: window.titles[hub.secao]
                    color: Theme.text
                    font { pixelSize: window.width < 1100 ? Theme.headline : Theme.display; weight: Font.Bold }
                }
                Text {
                    text: window.subtitles[hub.secao]
                    color: Theme.muted; font.pixelSize: Theme.subtitle
                    Layout.fillWidth: true; elide: Text.ElideRight
                }
            }
            TextField {
                id: search
                objectName: "searchField"
                visible: hub.secao !== "integracoes" && hub.secao !== "inicio"
                Layout.preferredWidth: window.width < 1150 ? 230 : 300
                implicitHeight: 44
                placeholderText: "Buscar nesta categoria  ·  Ctrl+F"
                color: Theme.text
                font.pixelSize: 13
                leftPadding: 15; rightPadding: 35
                background: Rectangle { radius: 12; color: Theme.surface; border.color: search.activeFocus ? Theme.accent : Theme.line }
                onTextEdited: hub.pesquisar(text)
                onAccepted: {
                    if (games) games.forceActiveFocus(); else if (collection) collection.forceActiveFocus()
                }
                ToolButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; text: "×"; visible: search.text.length > 0; onClicked: { search.clear(); hub.pesquisar("") } }
            }
        }

        // Hero usa somente arte local. Trocar de categoria não interrompe o player.
        Rectangle {
            id: hero
            visible: hub.secao === "jogos" && hub.quantidade > 0 && window.height >= 740
            Layout.fillWidth: true
            Layout.preferredHeight: window.height < 800 ? 136 : 182
            radius: Theme.radius
            color: Theme.surface
            clip: true
            Image {
                anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                width: parent.width * 0.54
                source: hub.selecionado.capa_url || ""
                fillMode: Image.PreserveAspectCrop
                asynchronous: true; opacity: 0.56
                sourceSize: Qt.size(850, 400)
            }
            Rectangle {
                anchors.fill: parent
                radius: Theme.radius
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: "#192e46" }
                    GradientStop { position: 0.5; color: "#f0162538" }
                    GradientStop { position: 1; color: "#20132132" }
                }
            }
            RowLayout {
                anchors.fill: parent; anchors.margins: 24; spacing: 18
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 8
                    Text { text: "DA SUA COLEÇÃO"; color: Theme.accent; font { pixelSize: 12; weight: Font.Bold; letterSpacing: 2 } }
                    Text {
                        text: hub.selecionado.titulo || "Escolha seu próximo jogo"
                        color: Theme.text; font { pixelSize: window.immersive ? Theme.display : Theme.headline; weight: Font.Bold }
                        Layout.fillWidth: true; elide: Text.ElideRight; maximumLineCount: 1
                    }
                    Text {
                        text: (hub.selecionado.plataforma || "PC") + "   /   " + (hub.selecionado.status || "backlog") +
                              "   /   " + Number(hub.selecionado.horas || 0).toFixed(1) + " horas jogadas"
                        color: Theme.muted; font.pixelSize: 14
                    }
                }
                ActionButton {
                    text: hub.emJogo ? "Em execução" : "▶  Jogar agora"
                    primary: true; implicitHeight: 50; implicitWidth: 155
                    enabled: !hub.ocupado && !hub.emJogo
                    onClicked: hub.jogar(hub.selecionado.id)
                }
                ActionButton { text: "Detalhes"; onClicked: details.open() }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: hub.secao !== "inicio"
            spacing: 8
            Text {
                visible: hub.secao === "integracoes"
                text: "Suas fontes e atalhos no mesmo lugar."; color: Theme.muted; font.pixelSize: 13
                Layout.fillWidth: true; elide: Text.ElideRight
            }
            ActionButton {
                objectName: "addIntegrationButton"
                visible: hub.secao === "integracoes"
                text: "+ Adicionar"; implicitHeight: 36
                onClicked: novaIntegracao.open()
            }
            Repeater {
                model: hub.secao === "jogos" ? [
                    {key: "todos", text: "Todos"}, {key: "favoritos", text: "★ Favoritos"},
                    {key: "jogando", text: "Jogando"}, {key: "PC", text: "PC"},
                    {key: "3DS", text: "3DS"}, {key: "NDS", text: "NDS"}] : []
                ActionButton {
                    required property var modelData
                    text: modelData.text; selected: hub.filtro === modelData.key; quiet: true
                    implicitHeight: 36
                    onClicked: hub.filtrar(modelData.key)
                }
            }
            Item { Layout.fillWidth: true }
            ComboBox {
                visible: hub.secao === "jogos"
                model: ["Nome", "Recentes", "Mais jogados"]
                currentIndex: ["titulo", "recentes", "horas"].indexOf(hub.ordem)
                implicitWidth: 130; implicitHeight: 36
                onActivated: hub.ordenar(["titulo", "recentes", "horas"][currentIndex])
            }
            ActionButton {
                objectName: "spotifyCatalogButton"
                visible: hub.secao === "musicas"
                text: "Spotify…"; implicitHeight: 36
                onClicked: spotifyCatalog.open()
            }
            ActionButton {
                objectName: "musicDownloadsButton"
                visible: hub.secao === "musicas"
                text: "Fila de downloads"; implicitHeight: 36
                onClicked: musicDownloads.open()
            }
            ActionButton {
                objectName: "pacotesButton"
                visible: hub.secao === "downloads"
                text: "Pacotes locais…"; implicitHeight: 36
                onClicked: pacotes.open()
            }
            ActionButton {
                objectName: "concluidosButton"
                visible: hub.secao === "downloads"
                text: "Importar concluídos…"; implicitHeight: 36
                onClicked: { hub.consultarTorrentsProntos(); concluidos.open() }
            }
            ActionButton { visible: hub.secao === "videos"; text: "Pesquisar YouTube…"; implicitHeight: 36; onClicked: youtube.open() }
            TextField {
                id: youtubeQuery
                objectName: "youtubeNavQuery"
                visible: hub.secao === "youtube" && hub.webDisponivel
                placeholderText: "Pesquisar no YouTube"; implicitWidth: 240; implicitHeight: 36
                color: Theme.text
                onAccepted: youtubeLoader.item ? youtubeLoader.item.irPara(text) : youtube.open()
            }
            ActionButton {
                visible: hub.secao === "youtube" && hub.webDisponivel
                text: "Ir"; implicitHeight: 36
                onClicked: youtubeLoader.item ? youtubeLoader.item.irPara(youtubeQuery.text) : youtube.open()
            }
            ActionButton {
                visible: hub.secao === "youtube" && hub.webDisponivel
                text: "⬇ Baixar este"; primary: true; implicitHeight: 36
                enabled: !hub.ocupado
                onClicked: {
                    youtubeLoader.item.urlAtualAsync(function(u) { hub.youtubeBaixarUrl(u) })
                }
            }
            ActionButton {
                visible: hub.secao === "youtube" && hub.webDisponivel
                text: "MP3 deste"; implicitHeight: 36; enabled: !hub.ocupado
                onClicked: { if (youtubeLoader.item) youtubeLoader.item.urlAtualAsync(function(u) { hub.baixarMp3Url(u) }) }
            }
            ComboBox { id: videoPlayer; visible: hub.secao === "videos"; model: hub.multimediaDisponivel ? ["Interno", "Automático", "VLC", "MPV", "MPC-HC"] : ["Automático", "VLC", "MPV", "MPC-HC"]; implicitWidth: 130; implicitHeight: 36 }
            ActionButton { visible: hub.secao === "videos"; text: "Ferramentas…"; implicitHeight: 36; onClicked: mediaTools.open() }
            ActionButton {
                objectName: "collectionAddButton"
                visible: hub.secao !== "integracoes" && hub.secao !== "youtube"
                text: hub.secao === "jogos" ? "+ Adicionar" : hub.secao === "musicas" ? "+ Importar pasta" :
                      hub.secao === "desejos" ? "+ Adicionar desejo" : hub.secao === "videos" ? "+ Importar vídeos" : "Iniciar cliente"
                implicitHeight: 36; enabled: !hub.ocupado
                onClicked: {
                    if (hub.secao === "jogos") window.editGame({})
                    else if (hub.secao === "musicas") musicFolder.open()
                    else if (hub.secao === "desejos") wishDialog.open()
                    else if (hub.secao === "videos") videoFolder.open()
                    else hub.iniciarDownloads()
                }
            }
            ActionButton { visible: hub.secao === "desejos"; text: "Sincronizar Steam"; implicitHeight: 36; enabled: !hub.ocupado; onClicked: hub.sincronizarDesejosSteam() }
            ActionButton { visible: hub.secao === "desejos"; text: "Importar wishlist…"; implicitHeight: 36; enabled: !hub.ocupado; onClicked: wishlistFile.open() }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: hub.secao !== "integracoes" && hub.secao !== "inicio"
            Text {
                objectName: "collectionSummary"
                text: hub.resumoLista; color: Theme.muted; font.pixelSize: Theme.meta
                Layout.fillWidth: true; elide: Text.ElideRight
            }
            ActionButton {
                objectName: "filterProblemsButton"
                visible: hub.secao === "jogos" && hub.saude.pendentes > 0
                text: "Pendências (" + hub.saude.pendentes + ")"
                selected: hub.filtro === "pendencias"; implicitHeight: 32
                onClicked: hub.verPendencias()
            }
            ActionButton {
                objectName: "clearFiltersButton"
                visible: hub.busca.length > 0 || (hub.secao === "jogos" && hub.filtro !== "todos")
                text: "Limpar filtros"; implicitHeight: 32
                onClicked: hub.limparFiltros()
            }
        }

        Item {
            Layout.fillWidth: true; Layout.fillHeight: true
            Loader {
                id: sectionLoader
                anchors.fill: parent
                sourceComponent: hub.secao === "inicio" ? inicioComponent : hub.secao === "jogos" ? jogosComponent :
                    hub.secao === "musicas" ? musicasComponent : hub.secao === "videos" ? videosComponent :
                    hub.secao === "youtube" ? youtubeComponent : hub.secao === "integracoes" ? integracoesComponent : colecaoComponent
                onLoaded: { if (item && (hub.secao === "jogos" || item.objectName === "collectionList")) item.currentIndex = hub.indiceSelecionado }
            }

            ColumnLayout {
                anchors.centerIn: parent
                visible: hub.secao !== "integracoes" && hub.secao !== "inicio" && hub.secao !== "youtube" && hub.quantidade === 0
                spacing: 14
                Text { text: hub.ocupado ? "◌" : "◇"; color: Theme.accent; font.pixelSize: 54; Layout.alignment: Qt.AlignHCenter }
                Text { text: hub.ocupado ? "Preparando sua coleção…" : hub.busca ? "Nenhum resultado por aqui." : "Este espaço está esperando por você."; color: Theme.text; font.pixelSize: Theme.headline; Layout.alignment: Qt.AlignHCenter }
                Text { text: hub.busca ? "Experimente outro nome ou limpe os filtros." : "Use a ação abaixo para começar."; color: Theme.muted; font.pixelSize: 13; Layout.alignment: Qt.AlignHCenter }
                ActionButton {
                    objectName: "emptyStateAction"
                    visible: !hub.ocupado && !hub.busca && (hub.secao === "jogos" || hub.secao === "musicas" || hub.secao === "desejos" || hub.secao === "videos" || hub.secao === "downloads")
                    text: hub.secao === "jogos" ? "+ Adicionar jogo" : hub.secao === "musicas" ? "+ Importar pasta" :
                          hub.secao === "desejos" ? "+ Adicionar desejo" : hub.secao === "videos" ? "+ Importar vídeos" : "Iniciar cliente"
                    primary: true; Layout.alignment: Qt.AlignHCenter
                    onClicked: {
                        if (hub.secao === "jogos") window.editGame({})
                        else if (hub.secao === "musicas") musicFolder.open()
                        else if (hub.secao === "desejos") wishDialog.open()
                        else if (hub.secao === "videos") videoFolder.open()
                        else hub.iniciarDownloads()
                    }
                }
            }
        }
    }

    Component { id: inicioComponent; Secoes.Inicio { shell: window } }
    Component { id: jogosComponent; Secoes.Jogos { shell: window } }
    Component { id: musicasComponent; Secoes.Musicas { shell: window } }
    Component { id: videosComponent; Secoes.Videos { shell: window } }
    Component { id: youtubeComponent; Secoes.YouTube { shell: window } }
    Component { id: integracoesComponent; Secoes.Integracoes { shell: window } }
    Component { id: colecaoComponent; Secoes.Colecao { shell: window } }

    footer: Rectangle {
        height: 90
        color: Theme.surface
        Rectangle { width: parent.width; height: 1; color: Theme.line }
        RowLayout {
            anchors.fill: parent; anchors.margins: 20; spacing: window.width < 1150 ? 8 : 14
            Rectangle {
                width: 46; height: 46; radius: 12; color: Theme.raised
                Text { anchors.centerIn: parent; text: "♫"; color: Theme.accent; font.pixelSize: 25 }
                Image { anchors.fill: parent; source: hub.audio.capa_url; fillMode: Image.PreserveAspectCrop; asynchronous: true; sourceSize: Qt.size(96, 96) }
            }
            ColumnLayout {
                Layout.preferredWidth: window.width < 1150 ? 140 : 220; spacing: 5
                Text { text: hub.audio.titulo; color: Theme.text; font { pixelSize: 13; weight: Font.DemiBold } Layout.fillWidth: true; elide: Text.ElideRight }
                Text { text: hub.audio.artista; color: Theme.muted; font.pixelSize: 13; Layout.fillWidth: true; elide: Text.ElideRight }
            }
            ActionButton { text: "❮"; Accessible.name: "Faixa anterior"; onClicked: hub.transporte("anterior") }
            ActionButton { text: hub.audio.estado === "tocando" ? "Ⅱ" : hub.audio.estado === "carregando" ? "…" : "▶"; primary: true; Accessible.name: "Reproduzir ou pausar"; onClicked: hub.transporte("alternar") }
            ActionButton { text: "❯"; Accessible.name: "Próxima faixa"; onClicked: hub.transporte("proxima") }
            ActionButton { text: "■"; Accessible.name: "Parar reprodução"; onClicked: hub.transporte("parar") }
            ActionButton {
                text: hub.modoAudioAtual === "aleatorio" ? "⤨" : hub.modoAudioAtual === "repetir" ? "⤾" : "→"
                Accessible.name: "Modo de reprodução"; ToolTip.visible: hovered
                ToolTip.text: hub.modoAudioAtual === "aleatorio" ? "Aleatório" : hub.modoAudioAtual === "repetir" ? "Repetir faixa" : "Em sequência"
                onClicked: hub.modoAudio(hub.modoAudioAtual === "sequencia" ? "aleatorio" : hub.modoAudioAtual === "aleatorio" ? "repetir" : "sequencia")
            }
            ActionButton { text: "☰"; Accessible.name: "Fila de reprodução"; onClicked: fila.open() }
            VolumeControl {
                objectName: "footerPcVolume"
                Layout.preferredWidth: window.width < 1150 ? 210 : 260
                Layout.minimumWidth: 190
            }
            Item { Layout.fillWidth: true }
            BusyIndicator { running: hub.ocupado; visible: running; implicitWidth: 28; implicitHeight: 28 }
            Text { visible: window.width >= 1150; text: hub.atividade; color: Theme.muted; font.pixelSize: 13; Layout.maximumWidth: 170; elide: Text.ElideRight }
            ActionButton { text: "↻"; enabled: !hub.ocupado; Accessible.name: "Atualizar coleção"; onClicked: hub.atualizar() }
        }
    }

    Dialog {
        id: diagnostico
        objectName: "diagnosticoDialog"
        title: "Diagnóstico da instalação"
        anchors.centerIn: parent
        width: Math.min(760, ApplicationWindow.window.width - 60)
        height: Math.min(620, ApplicationWindow.window.height - 40)
        modal: true; standardButtons: Dialog.Close
        contentItem: ColumnLayout {
            spacing: 12
            Connections {
                target: hub
                function onDiagnosticoPronto(texto) { relatorio.text = texto }
            }
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                TextArea {
                    id: relatorio
                    objectName: "diagnosticoTexto"
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.WrapAnywhere
                    color: Theme.text
                    font.family: "Consolas"
                    font.pixelSize: 12
                    text: "Gerando…"
                    background: Rectangle { radius: Theme.radiusSmall; color: Theme.bg }
                }
            }
            RowLayout {
                ActionButton {
                    text: "Copiar relatório"; Layout.fillWidth: true
                    onClicked: { relatorio.selectAll(); relatorio.copy(); relatorio.deselect() }
                }
            }
        }
    }

    Drawer {
        id: details
        objectName: "gameDetails"
        width: Math.min(430, window.width * 0.5); height: window.height
        edge: Qt.RightEdge; modal: true
        onClosed: { if (!achievements.visible) hub.monitorarConquistas(0) }
        background: Rectangle { color: Theme.surface; border.color: Theme.line }
        Flickable {
            anchors.fill: parent; anchors.margins: 28
            contentHeight: detailsColumn.implicitHeight
            clip: true
            ScrollBar.vertical: ScrollBar {}
        ColumnLayout {
            id: detailsColumn
            width: parent.width; spacing: 18
            RowLayout { Layout.fillWidth: true; Text { text: "SOBRE O JOGO"; color: Theme.muted; font { pixelSize: 13; letterSpacing: 2 } } Item { Layout.fillWidth: true } ActionButton { text: "×"; onClicked: details.close() } }
            Image { Layout.fillWidth: true; Layout.preferredHeight: Math.min(280, window.height * 0.28); source: hub.selecionado.capa_url || ""; fillMode: Image.PreserveAspectFit; asynchronous: true }
            Text { text: hub.selecionado.titulo || ""; color: Theme.text; font { pixelSize: 27; weight: Font.Bold } Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Text { text: (hub.selecionado.plataforma || "PC") + "  ·  " + (hub.selecionado.status || "backlog"); color: Theme.accent; font.pixelSize: 13 }
            Text { text: Number(hub.selecionado.horas || 0).toFixed(1) + " horas jogadas" + (hub.selecionado.nota !== null && hub.selecionado.nota !== undefined ? "  ·  nota " + hub.selecionado.nota + "/10" : ""); color: Theme.muted; font.pixelSize: 14 }
            Text { text: hub.selecionado.etiquetas || "Sem etiquetas — edite para organizar."; color: Theme.muted; font.pixelSize: 14; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            ActionButton { Layout.fillWidth: true; text: "▶  Jogar"; primary: true; enabled: !hub.ocupado && !hub.emJogo; onClicked: { hub.jogar(hub.selecionado.id); details.close() } }
            ActionButton { Layout.fillWidth: true; text: hub.selecionado.favorito ? "★  Remover dos favoritos" : "☆  Adicionar aos favoritos"; enabled: !hub.ocupado; onClicked: hub.favorito(hub.selecionado.id) }
            ActionButton { Layout.fillWidth: true; text: "Editar jogo"; enabled: !hub.ocupado; onClicked: window.editGame(hub.selecionado) }
            ActionButton { objectName: "gameCoversButton"; Layout.fillWidth: true; text: "Buscar capas nas bibliotecas…"; enabled: !hub.ocupado; onClicked: window.openCovers("jogos", hub.selecionado) }
            ActionButton { objectName: "gameLibretroButton"; Layout.fillWidth: true; text: "Capa offline (LibRetro)"; enabled: !hub.ocupado && (hub.selecionado.plataforma === "3DS" || hub.selecionado.plataforma === "NDS"); onClicked: hub.buscarCapaLibretro(hub.selecionado.id) }
            ActionButton { objectName: "gameAchievementsButton"; Layout.fillWidth: true; text: "Conquistas do Hub…"; enabled: !!hub.selecionado.id; onClicked: window.openAchievements(hub.selecionado) }
            ActionButton { objectName: "registerGameHoursButton"; Layout.fillWidth: true; text: "Registrar horas…"; enabled: !hub.ocupado && !hub.emJogo && !!hub.selecionado.id; onClicked: window.registerHours(hub.selecionado, "") }
            ActionButton { objectName: "gameToolsButton"; Layout.fillWidth: true; text: "Saves, screenshots e organização…"; enabled: !hub.ocupado; onClicked: { gameTools.gid = hub.selecionado.id; gameTools.open() } }
            ActionButton { visible: (hub.selecionado.origem || "") === "rom-3ds"; Layout.fillWidth: true; text: "Mods, texturas, cheats e presets…"; enabled: !hub.ocupado; onClicked: { emulacaoDialog.gid = hub.selecionado.id; emulacaoDialog.open() } }
            ActionButton { objectName: "gameDiagnosticButton"; Layout.fillWidth: true; text: "Diagnosticar e religar exe/ROM…"; enabled: !hub.ocupado && !!hub.selecionado.id; onClicked: { hub.diagnosticarJogo(hub.selecionado.id); manutencaoDialog.open() } }
            ActionButton { objectName: "gameElevateButton"; Layout.fillWidth: true; text: "▶  Jogar como administrador (UAC)"; enabled: !hub.ocupado && !hub.emJogo && !!hub.selecionado.id; onClicked: { uacConfirm.gid = hub.selecionado.id; uacConfirm.jogo = hub.selecionado.titulo || ""; uacConfirm.open() } }
            ActionButton { text: "Remover da biblioteca"; enabled: !hub.ocupado; onClicked: { window.deleteItem("jogos", hub.selecionado); details.close() } }
            Item { Layout.fillHeight: true }
            Text { text: "Notas pessoais"; color: Theme.muted; font { pixelSize: 13; letterSpacing: 2 } }
            TextArea {
                id: notasJogo
                objectName: "gameNotesArea"
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                wrapMode: TextEdit.Wrap
                placeholderText: "Diário, impressões, onde parei…"
                color: Theme.text
                text: hub.selecionado.observacoes || ""
                background: Rectangle { radius: Theme.radiusSmall; color: Theme.bg; border.color: Theme.line }
            }
            ActionButton {
                objectName: "gameNotesSave"
                Layout.fillWidth: true
                text: "Salvar notas"; enabled: !hub.ocupado && !!hub.selecionado.id
                onClicked: hub.salvarObservacoes(hub.selecionado.id, notasJogo.text)
            }
            Text { text: "Saneamento, reparo e atualização de emuladores ficam em Configurações › Manutenção; importar pacotes e pastas está em Configurações › Coleção."; color: Theme.muted; font.pixelSize: 14; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
        }
    }

    Dialog {
        id: settings
        objectName: "settingsDialog"
        title: "Seu espaço, do seu jeito"
        anchors.centerIn: parent
        width: Math.min(560, window.width - 80)
        height: Math.min(690, window.height - 60)
        modal: true; standardButtons: Dialog.Close
        onOpened: hub.consultarVolume()
        contentItem: ScrollView {
            clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: 16
            Text { text: "TUCOTECA  /  DESKTOP QT"; color: Theme.accent; font { pixelSize: 12; letterSpacing: 2 } }
            Text { text: "Interface Qt Quick, biblioteca local e integrações independentes."; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            ActionButton { text: window.immersive ? "Sair do Big Picture" : "Entrar no Big Picture"; Layout.fillWidth: true; onClicked: { settings.close(); window.toggleImmersive() } }
            ActionButton { text: "Criar backup da coleção"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: hub.backup() }
            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
            Text { text: "APARÊNCIA"; color: Theme.accent; font { pixelSize: 12; letterSpacing: 2 } }
            Text { text: "Tema e densidade ficam salvos nesta coleção."; color: Theme.muted; font.pixelSize: Theme.subtitle; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true
                Text { text: "Tema"; color: Theme.muted; font.pixelSize: 14; Layout.preferredWidth: 90 }
                Repeater {
                    model: [{k: "escuro", t: "Escuro"}, {k: "claro", t: "Claro"}]
                    ActionButton {
                        required property var modelData
                        text: modelData.t; selected: hub.aparencia.tema === modelData.k; quiet: true
                        onClicked: hub.definirAparencia(modelData.k, hub.aparencia.densidade, hub.aparencia.auto_backup, hub.aparencia.modo_simples)
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: "Densidade"; color: Theme.muted; font.pixelSize: 14; Layout.preferredWidth: 90 }
                Repeater {
                    model: [{k: "compacto", t: "Compacto"}, {k: "conforto", t: "Conforto"}, {k: "bigpicture", t: "Big Picture"}]
                    ActionButton {
                        required property var modelData
                        text: modelData.t; selected: hub.aparencia.densidade === modelData.k; quiet: true
                        onClicked: hub.definirAparencia(hub.aparencia.tema, modelData.k, hub.aparencia.auto_backup, hub.aparencia.modo_simples)
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: "Backup"; color: Theme.muted; font.pixelSize: 14; Layout.preferredWidth: 90 }
                ActionButton {
                    text: hub.aparencia.auto_backup ? "Automático ao fim da sessão" : "Somente manual"
                    selected: hub.aparencia.auto_backup; quiet: true
                    onClicked: hub.definirAparencia(hub.aparencia.tema, hub.aparencia.densidade, !hub.aparencia.auto_backup, hub.aparencia.modo_simples)
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: "Modo"; color: Theme.muted; font.pixelSize: 14; Layout.preferredWidth: 90 }
                ActionButton {
                    objectName: "modoSimplesButton"
                    text: hub.aparencia.modo_simples ? "Simples (Isa) — ligado" : "Completo — ligado"
                    selected: hub.aparencia.modo_simples; quiet: true
                    onClicked: hub.definirAparencia(hub.aparencia.tema, hub.aparencia.densidade, hub.aparencia.auto_backup, !hub.aparencia.modo_simples)
                }
            }
            ActionButton {
                objectName: "exportarColecaoButton"
                text: "Exportar coleção para pasta ou pendrive…"; Layout.fillWidth: true; enabled: !hub.ocupado
                onClicked: exportFolder.open()
            }
            ActionButton { objectName: "importarColecaoButton"; text: "Importar pacote de coleção…"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: packageFile.open() }
            ActionButton { text: "Importar pasta de jogos locais…"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: gamesFolder.open() }
            ActionButton { text: "Importar arquivo (exe/ROM) com preview…"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: singleGameFile.open() }
            ActionButton { text: "Importar pacote de jogo (.zip/.rar/.7z)…"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: repackFile.open() }
            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
            Text { text: "MANUTENÇÃO"; color: Theme.accent; font { pixelSize: 12; letterSpacing: 2 } }
            Text { text: "Sanear organiza sobras de instalação e leva instaladores para .hub-lixo, sempre reversível. Mostra o plano antes de aplicar."; color: Theme.muted; font.pixelSize: Theme.subtitle; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            ActionButton { objectName: "sanearButton"; text: "Sanear pasta de jogo…"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: sanearFolder.open() }
            ActionButton { objectName: "personalToolsButton"; text: "Perfis, atalhos, vigia, estatísticas e API local…"; Layout.fillWidth: true; onClicked: personalTools.open() }
            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
            Text { text: "DIAGNÓSTICO"; color: Theme.accent; font { pixelSize: 12; letterSpacing: 2 } }
            Text { text: "Relatório somente-leitura da instalação. Útil para anexar em um issue."; color: Theme.muted; font.pixelSize: Theme.subtitle; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            ActionButton { text: "Gerar diagnóstico"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: { hub.rodarDiagnostico(); diagnostico.open() } }
            ActionButton { text: "Sistema: backups, sessões e logs"; Layout.fillWidth: true; onClicked: { settings.close(); sistema.open() } }
            ActionButton { text: "Provedores online: capas, conquistas e Spotify"; Layout.fillWidth: true; onClicked: providers.open() }
            ActionButton { text: "Ferramentas de mídia: imagem, áudio e vídeo"; Layout.fillWidth: true; onClicked: mediaTools.open() }
            VolumeControl { Layout.fillWidth: true }
            ActionButton { text: "Abrir ferramentas clássicas"; Layout.fillWidth: true; enabled: !hub.ocupado && !hub.emJogo; onClicked: hub.classico() }
            Text { text: "A interface clássica reúne importação avançada, mods, emuladores, CSV, pacotes e manutenção. A troca encerra esta interface e mantém a mesma coleção."; color: Theme.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: Theme.subtitle }
            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
            Text { text: "F11  Tela cheia     Ctrl+1…7  Categorias\nCtrl+F  Buscar     Ctrl+K  Busca global     Setas  Navegar\nEnter  Jogar/Tocar/Assistir     Espaço  Detalhes"; color: Theme.muted; lineHeight: 1.5; font.pixelSize: 13 }
            Text { text: hub.controlesConectados.length ? "Controle conectado: " + hub.controlesConectados.join(", ") : "Nenhum controle XInput detectado. Conecte-o; ele é reconhecido sem reiniciar."; color: Theme.muted; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Text { text: "Controle XInput: setas ou analógico navegam · A confirma · B volta · LB/RB trocam de seção · Start abre a busca global."; color: Theme.muted; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
        }
    }

    Dialog {
        id: gameDialog
        objectName: "gameEditorDialog"
        property int gid: 0
        anchors.centerIn: parent; width: 580; modal: true
        height: Math.min(680, window.height - 60)
        title: gid ? "Editar jogo" : "Adicionar jogo"
        standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: hub.salvarJogo(gid, gameTitle.text, gameExe.text, gameArgs.text, gameStatus.currentText, gameNota.text, gameTags.text, syncReference.checked && gid === 0)
        contentItem: ScrollView {
            clip: true; contentWidth: availableWidth
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { text: "Título" }
            TextField { id: gameTitle; Layout.fillWidth: true; placeholderText: "Nome do jogo"; selectByMouse: true }
            Label { text: "Executável" }
            RowLayout { Layout.fillWidth: true; TextField { id: gameExe; Layout.fillWidth: true; selectByMouse: true } ActionButton { text: "Escolher…"; onClicked: executableDialog.open() } }
            Label { text: "Argumentos / caminho da ROM" }
            TextField { id: gameArgs; Layout.fillWidth: true; selectByMouse: true }
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: "Status" }
                    ComboBox { id: gameStatus; Layout.fillWidth: true; model: ["backlog", "jogando", "zerado", "pausado", "abandonado"] }
                }
                ColumnLayout {
                    Layout.preferredWidth: 110
                    Label { text: "Nota 0–10" }
                    TextField {
                        id: gameNota; placeholderText: "—"; selectByMouse: true
                        validator: RegularExpressionValidator { regularExpression: /[0-9]|10/ }
                    }
                }
            }
            Label { text: "Etiquetas (vírgula separa)" }
            TextField { id: gameTags; Layout.fillWidth: true; placeholderText: "rpg, favorito, coop"; selectByMouse: true }
            CheckBox { id: syncReference; visible: gameDialog.gid === 0; checked: true; text: "Consultar Steam como referência de conquistas ao adicionar"; Layout.fillWidth: true }
        }
        }
    }
    FileDialog { id: executableDialog; title: "Escolha o executável"; onAccepted: gameExe.text = decodeURIComponent(selectedFile.toString().replace(Qt.platform.os === "windows" ? /^file:\/\/\// : /^file:\/\//, "")) }
    FolderDialog { id: musicFolder; title: "Importar pasta de músicas"; onAccepted: hub.importarMusicas(selectedFolder) }
    FolderDialog { id: videoFolder; title: "Importar pasta de vídeos"; onAccepted: hub.importarVideos(selectedFolder) }
    FolderDialog { id: gamesFolder; title: "Importar jogos locais"; onAccepted: { hub.preverPasta(selectedFolder); importPreview.open() } }
    FileDialog { id: singleGameFile; title: "Arquivo de jogo (exe/ROM)"; nameFilters: ["Jogos (*.exe *.lnk *.bat *.cmd *.3ds *.3dsx *.cci *.cxi *.elf *.app *.axf *.nds *.dsi)", "Todos (*.*)"]; onAccepted: { hub.analisarArquivo(selectedFile); importPreview.open() } }
    FileDialog { id: repackFile; title: "Pacote de jogo"; nameFilters: ["Pacotes (*.zip *.rar *.7z)"]; onAccepted: hub.importarRepack(selectedFile) }
    FileDialog { id: wishlistFile; title: "Wishlist salva (JSON)"; nameFilters: ["JSON (*.json)"]; onAccepted: hub.importarWishlist(selectedFile) }
    FileDialog { id: packageFile; title: "Pacote da coleção"; nameFilters: ["TucoTeca (*.zip)"]; onAccepted: packageConfirm.open() }
    Dialog {
        id: packageConfirm
        anchors.centerIn: parent; width: Math.min(520, window.width - 60)
        modal: true; title: "Importar coleção?"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: hub.importarColecao(packageFile.selectedFile, restoreSaves.checked)
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { text: "A coleção atual recebe um backup antes da importação. Jogos com a mesma identidade podem ter o progresso atualizado."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            CheckBox { id: restoreSaves; checked: false; text: "Também restaurar saves de emuladores (sobrescreve os atuais)"; Layout.fillWidth: true }
        }
    }
    Dialog {
        id: importPreview
        objectName: "importPreviewDialog"
        property var selecao: []
        anchors.centerIn: parent
        width: Math.min(760, window.width - 80); height: Math.min(580, window.height - 100)
        modal: true; title: "Importar — preview"; standardButtons: Dialog.Cancel
        onOpened: recarregarSelecao()
        onRejected: hub.limparPreview()
        function recarregarSelecao() {
            var itens = hub.previewImportacao.itens || [];
            var nova = [];
            for (var i = 0; i < itens.length; i++)
                nova.push((itens[i].score || 0) >= 0.3);
            selecao = nova;
        }
        function indicesMarcados() {
            var out = [];
            for (var i = 0; i < selecao.length; i++)
                if (selecao[i]) out.push(i);
            return out;
        }
        contentItem: ColumnLayout {
            spacing: 12
            Label {
                objectName: "importPreviewResumo"
                Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted
                text: {
                    var n = (hub.previewImportacao.itens || []).length;
                    var t = n + " achado(s). Pré-marcados: score ≥ 0.3.";
                    if (hub.previewImportacao.info && hub.previewImportacao.info.truncado)
                        t += " LISTA PARCIAL — refine a pasta.";
                    if (hub.previewImportacao.info && !hub.previewImportacao.info.emu)
                        t += " ROMs importam sem executável (emulador ausente).";
                    return t;
                }
            }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
                model: hub.previewImportacao.itens
                ScrollBar.vertical: ScrollBar {}
                delegate: RowLayout {
                    required property var modelData
                    required property int index
                    width: ListView.view.width - 12; spacing: 10
                    CheckBox {
                        checked: importPreview.selecao.length > index ? importPreview.selecao[index] : false
                        onToggled: {
                            var s = importPreview.selecao.slice();
                            s[index] = checked;
                            importPreview.selecao = s;
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 2
                        Text { text: modelData.titulo || "(sem título)"; color: Theme.text; font.pixelSize: 14; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text { text: (modelData.fonte || modelData.origem || "") + " · " + (modelData.score || 0).toFixed(2); color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                ActionButton { text: "Marcar todos"; enabled: !hub.ocupado; onClicked: { var s = []; for (var i = 0; i < (hub.previewImportacao.itens || []).length; i++) s.push(true); importPreview.selecao = s; } }
                ActionButton { text: "Limpar"; enabled: !hub.ocupado; onClicked: { var s = []; for (var i = 0; i < (hub.previewImportacao.itens || []).length; i++) s.push(false); importPreview.selecao = s; } }
                Item { Layout.fillWidth: true }
                ActionButton { objectName: "importPreviewConfirm"; text: "Importar selecionados"; primary: true; enabled: !hub.ocupado && importPreview.indicesMarcados().length > 0; onClicked: { hub.importarSelecionados(importPreview.indicesMarcados()); importPreview.close(); } }
            }
            Label { visible: (hub.previewImportacao.itens || []).length === 0; text: "Nada por aqui ainda — escolha uma pasta ou arquivo para ver o preview antes de importar."; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
        Connections { target: hub; function onPreviewMudou() { importPreview.recarregarSelecao(); } }
    }
    Dialog {
        id: manutencaoDialog
        objectName: "manutencaoDialog"
        property string campo: ""
        property int gid: 0
        anchors.centerIn: parent
        width: Math.min(620, window.width - 80); height: Math.min(520, window.height - 100)
        modal: true; title: "Manutenção do jogo"; standardButtons: Dialog.Close
        onOpened: { campo = ""; gid = hub.selecionado.id }
        contentItem: ColumnLayout {
            spacing: 12
            Text { text: (hub.manutencao.titulo || hub.selecionado.titulo || "") + " — plano do que será religado"; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Label {
                objectName: "manutencaoExe"
                Layout.fillWidth: true; wrapMode: Text.WordWrap
                text: {
                    var d = hub.manutencao.exe || {};
                    if (d.estado === "ok") return "Executável: ok (" + (d.atual || d.gravado || "?") + ")";
                    if (d.estado === "trocou-emulador")
                        return "Emulador trocado: " + (d.atual || "?") + " pode substituir " + (d.gravado || "?");
                    return "Executável: " + (d.estado || "?") + " — " + (d.gravado || d.atual || "sem caminho");
                }
            }
            Label {
                objectName: "manutencaoRom"
                Layout.fillWidth: true; wrapMode: Text.WordWrap
                visible: { var e = (hub.manutencao.rom || {}).estado; return !!e && e !== "ok"; }
                text: "ROM ausente: " + ((hub.manutencao.rom || {}).gravado || "?")
            }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 6
                model: ((hub.manutencao.rom || {}).candidatos || [])
                ScrollBar.vertical: ScrollBar {}
                delegate: RowLayout {
                    required property var modelData
                    width: ListView.view.width - 12
                    ActionButton { text: "Religar para este"; Layout.fillWidth: true; enabled: !hub.ocupado && hub.manutencao.gid > 0; onClicked: { manutencaoDialog.campo = "launch_options"; manutencaoDialog.gid = hub.manutencao.gid || hub.selecionado.id; hub.religarJogo(manutencaoDialog.gid, "launch_options", modelData) } }
                }
            }
            Text { visible: (((hub.manutencao.rom || {}).candidatos || []).length === 0) && (hub.manutencao.rom || {}).estado === "rom-ausente"; text: "Nenhum candidato encontrado nas pastas de ROM. Use “Religar à mão” e informe o caminho novo."; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout {
                Layout.fillWidth: true; spacing: 10
                TextField { id: romManual; objectName: "manutencaoCaminho"; Layout.fillWidth: true; placeholderText: "Novo caminho (ROM ou executável)" }
                ActionButton { objectName: "manutencaoReligar"; text: "Religar à mão"; enabled: !hub.ocupado && hub.manutencao.gid > 0 && romManual.text.length > 0; onClicked: hub.religarJogo(hub.manutencao.gid, (hub.selecionado.origem || "").indexOf("rom-") === 0 ? "launch_options" : "executable_path", romManual.text) }
            }
            Text { text: "Religar só troca o caminho gravado e preserva horas, notas, saves e etiquetas."; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
    }
    Dialog {
        id: uacConfirm
        property int gid: 0
        property string jogo: ""
        anchors.centerIn: parent; width: Math.min(520, window.width - 60)
        modal: true; title: "Elevar privilégios (UAC)?"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: hub.jogarElevado(uacConfirm.gid)
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { text: "O Windows pedirá confirmação do Controle de Conta de Usuário para abrir “" + uacConfirm.jogo + "” como administrador. Use só se o jogo exigir; com elevação o Hub não rastreia as horas sozinho — registre a sessão ao terminar."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            CheckBox { id: uacEntendi; checked: false; text: "Entendi e quero elevar só este jogo"; Layout.fillWidth: true }
        }
        footer: RowLayout { Item { Layout.fillWidth: true } ActionButton { text: "Cancelar"; onClicked: uacConfirm.reject() } ActionButton { text: "Elevar e jogar"; primary: true; enabled: uacEntendi.checked; onClicked: uacConfirm.accept() } }
    }
    Dialog {
        id: sanearPlanoDialog
        objectName: "sanearPlanoDialog"
        anchors.centerIn: parent; width: Math.min(600, window.width - 60)
        modal: true; title: "Sanear pasta — plano"; standardButtons: Dialog.Cancel
        contentItem: ColumnLayout {
            spacing: 12
            Label {
                objectName: "sanearPlanoResumo"
                Layout.fillWidth: true; wrapMode: Text.WordWrap
                text: {
                    var s = hub.saneamento;
                    if (s.erro && !s.ok) return s.erro;
                    var t = "Pasta: " + (s.pasta || "?") + "\nExecutável: " + (s.exe || (s.precisa_instalar ? "só instalador" : "nenhum"));
                    if (s.quarentenaveis) t += "\n" + s.quarentenaveis + " instalador(es) vão para .hub-lixo (reversível)";
                    if (s.avisos && s.avisos.length) t += "\n" + s.avisos.join("\n");
                    return t;
                }
            }
            RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } ActionButton { objectName: "sanearPlanoAplicar"; text: "Aplicar"; primary: true; enabled: !hub.ocupado && hub.saneamento.ok === true; onClicked: { hub.aplicarSaneamento(hub.saneamento.pasta); sanearPlanoDialog.close() } } }
        }
    }
    FolderDialog { id: sanearFolder; title: "Pasta do jogo para sanear"; onAccepted: { hub.planejarSaneamento(selectedFolder); sanearPlanoDialog.open() } }
    Dialog {
        id: wishDialog
        anchors.centerIn: parent; width: 470; modal: true; title: "Adicionar desejo"
        standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: hub.adicionarDesejo(wishAppid.text, wishTitle.text)
        ColumnLayout {
            width: parent.width; spacing: 14
            Label { text: "Nome do jogo" }
            TextField { id: wishTitle; Layout.fillWidth: true }
            Label { text: "App ID da Steam (número na URL do jogo)" }
            TextField { id: wishAppid; Layout.fillWidth: true; validator: RegularExpressionValidator { regularExpression: /[0-9]+/ } }
        }
    }
    Dialog {
        id: deleteDialog
        property string category: ""
        property int ident: 0
        property string itemTitle: ""
        anchors.centerIn: parent; width: 480; modal: true
        title: "Remover da coleção?"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: hub.excluir(category, ident)
        Label { width: parent.width; text: "Remover “" + deleteDialog.itemTitle + "”?" + (deleteDialog.category === "musicas" ? " O arquivo de áudio e a capa gerenciados pelo Hub também serão removidos." : ""); wrapMode: Text.WordWrap }
    }
    Dialog {
        id: catalogDialog
        objectName: "catalogDialog"
        property string provider: ""
        anchors.centerIn: parent; width: Math.min(760, window.width - 80); height: Math.min(580, window.height - 100)
        modal: true; standardButtons: Dialog.Close
        ColumnLayout {
            anchors.fill: parent; spacing: 16
            RowLayout {
                Layout.fillWidth: true
                TextField { id: catalogQuery; Layout.fillWidth: true; placeholderText: "Nome do jogo"; onAccepted: hub.buscarIntegracao(catalogDialog.provider, text) }
                ActionButton { text: "Pesquisar"; enabled: !hub.ocupado; onClicked: hub.buscarIntegracao(catalogDialog.provider, catalogQuery.text) }
            }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true
                model: hub.catalogo; clip: true; spacing: 8
                ScrollBar.vertical: ScrollBar {}
                delegate: RowLayout {
                    required property var item
                    width: ListView.view.width - 12
                    spacing: 8
                    ActionButton {
                        objectName: "hubDownloadButton"
                        visible: (item.url || "").indexOf("magnet:?") === 0
                        text: "Baixar no Hub"; primary: true; enabled: !hub.ocupado
                        onClicked: hub.baixarTorrent(item.url)
                    }
                    ActionButton {
                        Layout.fillWidth: true
                        text: item.titulo + "  ↗"
                        onClicked: hub.abrirUrl(item.url)
                    }
                }
            }
            Text { text: "A pesquisa acessa a fonte somente quando solicitada. Magnets vão ao qBittorrent do Hub (Meus Jogos Locais/); o resto abre no navegador."; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 14 }
        }
    }
    Dialog {
        id: palette
        objectName: "globalPalette"
        anchors.centerIn: parent
        width: Math.min(680, window.width - 80); height: Math.min(520, window.height - 120)
        modal: true; standardButtons: Dialog.Close
        title: "Busca global · Ctrl+K"
        ColumnLayout {
            anchors.fill: parent; spacing: 12
            TextField {
                id: paletteQuery
                objectName: "paletteField"
                Layout.fillWidth: true
                placeholderText: "Jogo, música, desejo ou download…"
                onTextEdited: hub.buscarPaleta(text)
                onAccepted: { if (hub.paletaQuantidade > 0) { hub.abrirPrimeiraPaleta(); palette.close() } }
                Keys.onDownPressed: { if (hub.paletaQuantidade > 0) { paletteList.currentIndex = 0; paletteList.forceActiveFocus() } }
            }
            ListView {
                id: paletteList
                Layout.fillWidth: true; Layout.fillHeight: true
                model: hub.paleta; clip: true; spacing: 6
                keyNavigationEnabled: true
                ScrollBar.vertical: ScrollBar {}
                Keys.onUpPressed: paletteList.decrementCurrentIndex()
                Keys.onDownPressed: paletteList.incrementCurrentIndex()
                Keys.onReturnPressed: {
                    if (currentIndex >= 0 && currentIndex < hub.paletaQuantidade) {
                        hub.abrirPaleta(hub.paletaItem(currentIndex)); palette.close()
                    }
                }
                delegate: ActionButton {
                    required property var item
                    required property int index
                    width: ListView.view.width - 12
                    selected: ListView.view.currentIndex === index
                    text: "[" + item.tipo + "]  " + item.titulo + "  ·  " + item.sub
                    onClicked: { hub.abrirPaleta(item); palette.close() }
                }
            }
            Text { text: "Somente coleção local. ↑↓ navega, Enter abre."; color: Theme.muted; font.pixelSize: 13 }
        }
    }

    Popup {
        id: fila
        width: Math.min(520, window.width - 80); height: Math.min(480, window.height - 160)
        x: window.width - width - 30
        y: window.height - height - 120
        modal: true; closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { radius: 14; color: Theme.surface; border.color: Theme.line }
        contentItem: ColumnLayout {
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                Text { text: "FILA DE REPRODUÇÃO"; color: Theme.muted; font { pixelSize: 13; letterSpacing: 2 } }
                Item { Layout.fillWidth: true }
                RowLayout {
                    ActionButton { text: "→"; Accessible.name: "Sequência"; selected: hub.modoAudioAtual === "sequencia"; onClicked: hub.modoAudio("sequencia") }
                    ActionButton { text: "⤨"; Accessible.name: "Aleatório"; selected: hub.modoAudioAtual === "aleatorio"; onClicked: hub.modoAudio("aleatorio") }
                    ActionButton { text: "⤾"; Accessible.name: "Repetir"; selected: hub.modoAudioAtual === "repetir"; onClicked: hub.modoAudio("repetir") }
                }
            }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true
                model: hub.filaAudio; clip: true; spacing: 6
                ScrollBar.vertical: ScrollBar {}
                delegate: ActionButton {
                    required property var modelData
                    required property int index
                    width: ListView.view.width - 12
                    selected: modelData.atual
                    text: (modelData.atual ? "▶ " : "") + modelData.titulo + " — " + modelData.artista
                    onClicked: hub.tocar(modelData.id)
                }
            }
            Text { text: "Repetir toca a faixa atual; aleatório sorteia sem repetir a atual."; color: Theme.muted; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
    }

    Dialog {
        id: sistema
        objectName: "systemDialog"
        function refresh() {
            backupList.model = hub.listarBackups()
            sessaoList.model = hub.listarSessoes()
            logView.text = hub.verLog()
        }
        anchors.centerIn: parent
        width: Math.min(640, window.width - 80); height: Math.min(560, window.height - 100)
        modal: true; standardButtons: Dialog.Close
        title: "Sistema e manutenção"
        ColumnLayout {
            anchors.fill: parent; spacing: 12
            RowLayout {
                Layout.fillWidth: true
                ActionButton { text: "↻ Atualizar"; onClicked: sistema.refresh() }
                ActionButton { text: "Backup agora"; enabled: !hub.ocupado; onClicked: hub.backup() }
            }
            Label { text: "Backups (mantém 10)" }
            ListView {
                id: backupList
                Layout.fillWidth: true; Layout.preferredHeight: 110
                model: hub.listarBackups(); clip: true; spacing: 4
                ScrollBar.vertical: ScrollBar {}
                delegate: Label {
                    required property var modelData
                    width: ListView.view.width - 12
                    text: modelData.nome + "  ·  " + (modelData.bytes / 1048576).toFixed(1) + " MB"
                }
            }
            Label { text: "Sessões manuais pendentes" }
            ListView {
                id: sessaoList
                Layout.fillWidth: true; Layout.preferredHeight: 90
                model: hub.listarSessoes(); clip: true; spacing: 4
                ScrollBar.vertical: ScrollBar {}
                delegate: RowLayout {
                    required property var modelData
                    width: ListView.view.width - 12
                    Label { text: (modelData.titulo || modelData.gid) + "  ·  " + (modelData.inicio || ""); Layout.fillWidth: true; elide: Text.ElideRight }
                    ActionButton {
                        objectName: "registerPendingSessionButton"
                        text: "Registrar…"; enabled: !hub.ocupado && !hub.emJogo
                        onClicked: window.registerHours(modelData, modelData._arquivo)
                    }
                }
            }
            Label { text: "Últimos erros" }
            ScrollView {
                Layout.fillWidth: true; Layout.fillHeight: true
                TextArea {
                    id: logView
                    readOnly: true; wrapMode: Text.WordWrap; selectByMouse: true
                    text: hub.verLog()
                }
            }
        }
        onOpened: refresh()
    }

    Dialog {
        id: sessionDialog
        objectName: "sessionDialog"
        property int gid: 0
        property string file: ""
        property string gameTitle: ""
        anchors.centerIn: parent; width: Math.min(460, window.width - 80)
        modal: true
        title: file ? "Encerrar sessão pendente" : "Registrar horas"
        onAccepted: {
            let hours = Number(sessionHours.text.replace(",", "."))
            if (file) hub.encerrarSessao(file, hours)
            else hub.registrarSessao(gid, hours)
        }
        ColumnLayout {
            width: parent.width; spacing: 14
            Label { text: sessionDialog.gameTitle; Layout.fillWidth: true; wrapMode: Text.WordWrap; font.bold: true }
            Label { text: "Quantas horas você jogou?" }
            TextField {
                id: sessionHours
                objectName: "sessionHoursField"
                Layout.fillWidth: true; placeholderText: "Ex.: 1,5"; selectByMouse: true
                validator: RegularExpressionValidator { regularExpression: /[0-9]+([.,][0-9]{1,2})?/ }
            }
            Label {
                text: sessionDialog.file ? "As horas serão somadas e esta sessão sairá da lista de pendências." : "As horas serão somadas ao total do jogo."
                Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted
            }
        }
        footer: DialogButtonBox {
            Button {
                objectName: "saveSessionButton"
                text: "Registrar"; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                enabled: sessionHours.acceptableInput && Number(sessionHours.text.replace(",", ".")) > 0 && !hub.ocupado && !hub.emJogo
            }
            Button { text: "Cancelar"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
            onAccepted: sessionDialog.accept()
            onRejected: sessionDialog.reject()
        }
    }

    Popup {
        id: toast
        objectName: "notificationToast"
        property string message: ""
        property bool error: false
        x: (window.width - width) / 2
        y: window.height - height - 125
        width: Math.min(680, window.width - 70)
        padding: 18
        closePolicy: Popup.CloseOnEscape
        onClosed: {
            toastTimer.stop()
            window.showingNotification = false
            window.showNextNotification()
        }
        background: Rectangle { radius: 12; color: Theme.raised; border.color: toast.error ? Theme.danger : Theme.accent }
        contentItem: RowLayout {
            spacing: 12
            Text {
                objectName: "notificationMessage"
                text: toast.message; color: Theme.text; wrapMode: Text.WordWrap
                font { family: Theme.family; pixelSize: Theme.subtitle }
                Layout.fillWidth: true
            }
            ActionButton { objectName: "dismissNotificationButton"; text: "×"; Accessible.name: "Fechar aviso"; onClicked: toast.close() }
        }
    }
    Timer { id: toastTimer; interval: 7000; onTriggered: toast.close() }
    ProvidersDialog { id: providers }
    NewIntegrationDialog { id: novaIntegracao }
    CoversDialog { id: covers; onConfigureProviders: providers.open() }
    AchievementsDialog { id: achievements; onConfigureProviders: providers.open() }
    SpotifyDialog { id: spotifyCatalog; onConfigureProviders: providers.open(); onShowDownloads: { close(); musicDownloads.open() } }
    MusicDownloadsDialog { id: musicDownloads }
    PiratasDialog { id: pacotes }
    Dialog {
        id: concluidos
        objectName: "concluidosDialog"
        title: "Torrents concluídos · importar para a coleção"
        anchors.centerIn: parent
        width: Math.min(720, window.width - 80); height: Math.min(560, window.height - 100)
        modal: true; standardButtons: Dialog.Close
        onOpened: hub.consultarTorrentsProntos()
        contentItem: ColumnLayout {
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "Só entra aqui o que chegou a 100%. Download incompleto não importa pela metade."
                    color: Theme.muted
                    Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: Theme.subtitle
                }
                ActionButton { text: "↻ Atualizar"; enabled: !hub.ocupado; onClicked: hub.consultarTorrentsProntos() }
            }
            ListView {
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 10
                model: (hub.torrentsProntos.itens || [])
                ScrollBar.vertical: ScrollBar {}
                delegate: Rectangle {
                    required property var modelData
                    width: ListView.view.width - 12
                    implicitHeight: 76; radius: 10; color: Theme.surface
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 14
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 4
                            Text {
                                objectName: "concluidoNome"
                                text: modelData.nome || ""
                                color: Theme.text; font { pixelSize: 15; weight: Font.DemiBold }
                                Layout.fillWidth: true; elide: Text.ElideRight
                            }
                            Text {
                                text: modelData.estado === "pasta" ? "Pasta pronta · organiza e importa" :
                                      modelData.estado === "arquivo" ? "Arquivo pronto · extrai e importa" :
                                      modelData.estado === "sumiu" ? "Sumiu do disco · nada a importar" :
                                      "Formato não suportado · nada a importar"
                                color: modelData.estado === "sumiu" || modelData.estado === "nao-suportado" ? Theme.warning : Theme.muted
                                font.pixelSize: Theme.subtitle; Layout.fillWidth: true; elide: Text.ElideRight
                            }
                        }
                        ActionButton {
                            objectName: "concluidoImportarButton"
                            visible: modelData.estado === "pasta" || modelData.estado === "arquivo"
                            text: "Importar"; primary: true; enabled: !hub.ocupado
                            onClicked: hub.importarTorrent(modelData.save_path)
                        }
                    }
                }
            }
            Text {
                visible: (hub.torrentsProntos.itens || []).length === 0
                text: "Nada 100% ainda. Concluídos aparecem aqui; a origem do download é preservada."
                color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true
            }
        }
    }
    YouTubeDialog { id: youtube }
    MediaToolsDialog { id: mediaTools }
    GameToolsDialog { id: gameTools }
    EmulacaoDialog { id: emulacaoDialog }
    PersonalToolsDialog { id: personalTools }
    Dialog {
        id: internalVideo
        property var video: ({url: "", sha: "", posicao: 0})
        title: video.titulo || "Vídeo interno"
        anchors.centerIn: parent; modal: true
        width: Math.min(960, window.width - 60); height: Math.min(700, window.height - 60)
        standardButtons: Dialog.Close
        onClosed: { if (videoContent.item) videoContent.item.parar(); video = {url: "", sha: "", posicao: 0} }
        contentItem: Loader {
            id: videoContent
            active: !!internalVideo.video.url && hub.multimediaDisponivel
            source: "PlayerVideo.qml"
            onLoaded: item.video = internalVideo.video
        }
    }
    Dialog {
        id: integrationQuery
        property string chave: ""
        anchors.centerIn: parent; width: Math.min(480, window.width - 60)
        modal: true; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: hub.abrirIntegracao(chave, customQuery.text)
        TextField { id: customQuery; width: parent.width; placeholderText: "O que deseja pesquisar?"; selectByMouse: true; onAccepted: integrationQuery.accept() }
    }
}
