import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Window

ApplicationWindow {
    id: window
    objectName: "hubWindow"
    width: 1440; height: 920
    minimumWidth: 960; minimumHeight: 640
    visible: true
    title: "TucoTeca"
    color: Theme.bg
    font.family: Theme.family
    palette {
        window: Theme.bg; windowText: Theme.text; base: Theme.surface
        text: Theme.text; button: Theme.raised; buttonText: Theme.text
        highlight: Theme.accent; highlightedText: Theme.ink
        placeholderText: Theme.muted; mid: Theme.line; dark: Theme.surface
    }
    property bool immersive: false
    property string previousVisibility: "window"
    property string currentSection: hub.secao
    property var sections: [
        {key: "inicio", title: "Início"}, {key: "jogos", title: "Jogos"},
        {key: "musicas", title: "Músicas"}, {key: "desejos", title: "Desejos"},
        {key: "downloads", title: "Downloads"}, {key: "integracoes", title: "Integrações"}
    ]
    property var titles: ({inicio: "Boas-vindas ao seu hub.", jogos: "Sua próxima aventura.",
                          musicas: "Dê o play no seu mundo.", desejos: "O que vem a seguir.",
                          downloads: "A caminho da sua coleção.", integracoes: "Seu hub, conectado."})
    property var subtitles: ({inicio: "Continuar, buscar e cuidar da coleção — sem sair do lugar.",
        jogos: "Todos os seus jogos. Um lugar para começar.",
        musicas: "Sua coleção local, com música em todas as telas.",
        desejos: "Guarde os títulos que você quer jogar.",
        downloads: "Progresso do qBittorrent, sem sair do Hub.",
        integracoes: "Catálogos, emuladores e serviços com responsabilidades independentes."})

    function toggleImmersive() {
        if (!immersive) {
            previousVisibility = visibility === Window.Maximized ? "maximized" : "window"
            immersive = true
            showFullScreen()
        } else {
            immersive = false
            if (previousVisibility === "maximized") showMaximized(); else showNormal()
        }
        if (hub.secao === "jogos") games.forceActiveFocus()
        else if (hub.secao !== "integracoes" && hub.secao !== "inicio") collection.forceActiveFocus()
    }
    function notify(message, error) {
        toast.message = message
        toast.error = error
        toast.open()
        toastTimer.restart()
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
    onClosing: function(close) {
        if (hub.ocupado) {
            close.accepted = false
            notify("Concluindo a operação atual. Aguarde para fechar.", false)
        }
    }
    Shortcut { sequence: "F11"; onActivated: window.toggleImmersive() }
    Shortcut { sequence: "Escape"; onActivated: { if (window.immersive) window.toggleImmersive() } }
    Shortcut { sequence: "Ctrl+F"; onActivated: { search.forceActiveFocus(); search.selectAll() } }
    Shortcut { sequence: "Ctrl+K"; onActivated: { paletteQuery.clear(); hub.buscarPaleta(""); palette.open(); paletteQuery.forceActiveFocus() } }
    Shortcut { sequence: "Ctrl+1"; onActivated: hub.navegar("inicio") }
    Shortcut { sequence: "Ctrl+2"; onActivated: hub.navegar("jogos") }
    Shortcut { sequence: "Ctrl+3"; onActivated: hub.navegar("musicas") }
    Shortcut { sequence: "Ctrl+4"; onActivated: hub.navegar("desejos") }
    Shortcut { sequence: "Ctrl+5"; onActivated: hub.navegar("downloads") }
    Shortcut { sequence: "Ctrl+6"; onActivated: hub.navegar("integracoes") }
    Connections {
        target: hub
        function onAviso(message, error) { window.notify(message, error) }
        function onMudou() {
            if (!search.activeFocus) search.text = hub.busca
            if (hub.secao === "jogos") {
                if (games.currentIndex !== hub.indiceSelecionado) games.currentIndex = hub.indiceSelecionado
            } else if (hub.secao !== "integracoes" && hub.secao !== "inicio") {
                if (collection.currentIndex !== hub.indiceSelecionado) collection.currentIndex = hub.indiceSelecionado
            }
        }
        function onJogoIniciado() { window.showMinimized() }
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
            anchors.fill: parent
            anchors.leftMargin: 30; anchors.rightMargin: 30
            spacing: 12
            Rectangle {
                width: 38; height: 38; radius: 12
                gradient: Gradient {
                    GradientStop { position: 0; color: "#91e6ee" }
                    GradientStop { position: 1; color: "#638bff" }
                }
                Text { anchors.centerIn: parent; text: "T"; font { pixelSize: 24; weight: Font.Black } color: Theme.ink }
            }
            Text {
                visible: window.width >= 1140
                text: "TUCOTECA"; color: Theme.text
                font { pixelSize: 16; weight: Font.Bold; letterSpacing: 2 }
                Layout.rightMargin: 28
            }
            Repeater {
                model: window.sections
                ActionButton {
                    required property var modelData
                    objectName: "nav_" + modelData.key
                    text: modelData.title
                    selected: hub.secao === modelData.key
                    quiet: true
                    font.pixelSize: window.immersive ? 16 : 14
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
                text: "⌘ Buscar · Ctrl+K"; quiet: true
                onClicked: { paletteQuery.clear(); hub.buscarPaleta(""); palette.open(); paletteQuery.forceActiveFocus() }
            }
            ActionButton {
                objectName: "immersiveButton"
                text: window.immersive ? "Sair · F11" : "Big Picture"
                onClicked: window.toggleImmersive()
                ToolTip.visible: hovered; ToolTip.text: "Tela cheia · F11"
            }
            ActionButton { text: "⚙"; font.pixelSize: 20; onClicked: settings.open(); Accessible.name: "Configurações" }
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
                    font { pixelSize: window.width < 1100 ? 25 : 30; weight: Font.Bold }
                }
                Text {
                    text: window.subtitles[hub.secao]
                    color: Theme.muted; font.pixelSize: 12
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
                    if (hub.secao === "jogos") games.forceActiveFocus(); else collection.forceActiveFocus()
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
                    Text { text: "DA SUA COLEÇÃO"; color: Theme.accent; font { pixelSize: 10; weight: Font.Bold; letterSpacing: 2 } }
                    Text {
                        text: hub.selecionado.titulo || "Escolha seu próximo jogo"
                        color: Theme.text; font { pixelSize: window.immersive ? 30 : 25; weight: Font.Bold }
                        Layout.fillWidth: true; elide: Text.ElideRight; maximumLineCount: 1
                    }
                    Text {
                        text: (hub.selecionado.plataforma || "PC") + "   /   " + (hub.selecionado.status || "backlog") +
                              "   /   " + Number(hub.selecionado.horas || 0).toFixed(1) + " horas jogadas"
                        color: Theme.muted; font.pixelSize: 12
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
            visible: hub.secao !== "integracoes" && hub.secao !== "inicio"
            spacing: 8
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
            Text { text: hub.quantidade + " itens"; color: Theme.muted; font.pixelSize: 12; Layout.leftMargin: 8 }
            Item { Layout.fillWidth: true }
            ComboBox {
                visible: hub.secao === "jogos"
                model: ["Nome", "Recentes", "Mais jogados"]
                implicitWidth: 130; implicitHeight: 36
                onActivated: hub.ordenar(["titulo", "recentes", "horas"][currentIndex])
            }
            ActionButton {
                text: hub.secao === "jogos" ? "+ Adicionar" : hub.secao === "musicas" ? "+ Importar pasta" :
                      hub.secao === "desejos" ? "+ Adicionar desejo" : "Iniciar cliente"
                implicitHeight: 36; enabled: !hub.ocupado
                onClicked: {
                    if (hub.secao === "jogos") window.editGame({})
                    else if (hub.secao === "musicas") musicFolder.open()
                    else if (hub.secao === "desejos") wishDialog.open()
                    else hub.iniciarDownloads()
                }
            }
        }

        Item {
            Layout.fillWidth: true; Layout.fillHeight: true
            GridView {
                id: games
                objectName: "gamesGrid"
                anchors.fill: parent
                visible: hub.secao === "jogos"
                model: hub.itens
                clip: true
                cellWidth: width / Math.max(1, Math.floor(width / (window.immersive ? 235 : 190)))
                cellHeight: Math.min(window.height < 740 ? 265 : 370, cellWidth * 1.32 + 55)
                cacheBuffer: cellHeight * 2
                keyNavigationEnabled: true
                activeFocusOnTab: true
                highlightMoveDuration: 160
                highlightRangeMode: GridView.ApplyRange
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                Keys.onReturnPressed: { if (hub.selecionado.id && !hub.ocupado) hub.jogar(hub.selecionado.id) }
                Keys.onSpacePressed: { if (hub.selecionado.id) details.open() }
                onCurrentIndexChanged: { if (activeFocus) hub.selecionar(currentIndex) }
                delegate: PosterCard {
                    required property var item
                    required property int index
                    width: games.cellWidth - 8; height: games.cellHeight - 10
                    game: item
                    selected: hub.selecionado.id === item.id
                    onChosen: { games.currentIndex = index; games.forceActiveFocus(); hub.selecionar(index) }
                    onActivated: { if (!hub.ocupado) hub.jogar(item.id) }
                    onDetails: details.open()
                }
            }

            ListView {
                id: collection
                objectName: "collectionList"
                anchors.fill: parent
                visible: hub.secao !== "jogos" && hub.secao !== "integracoes" && hub.secao !== "inicio"
                model: hub.itens
                clip: true; spacing: 8
                activeFocusOnTab: true
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                Keys.onReturnPressed: { if (hub.secao === "musicas" && hub.selecionado.id) hub.tocar(hub.selecionado.id) }
                onCurrentIndexChanged: { if (activeFocus) hub.selecionar(currentIndex) }
                delegate: Rectangle {
                    id: row
                    required property var item
                    required property int index
                    width: collection.width - 12
                    height: hub.secao === "downloads" ? 104 : 82
                    radius: 12
                    color: rowHover.hovered ? Theme.raised : Theme.surface
                    border.color: collection.activeFocus && collection.currentIndex === index ? Theme.accent : "transparent"
                    HoverHandler { id: rowHover }
                    TapHandler { onTapped: { collection.currentIndex = index; hub.selecionar(index); collection.forceActiveFocus() } }
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 16
                        Rectangle {
                            width: 50; height: 50; radius: 10; color: Theme.raised
                            Text { anchors.centerIn: parent; text: hub.secao === "musicas" ? "♫" : hub.secao === "desejos" ? "☆" : "↓"; color: Theme.accent; font.pixelSize: 26 }
                            Image { anchors.fill: parent; source: row.item.capa_url || ""; fillMode: Image.PreserveAspectCrop; asynchronous: true; sourceSize: Qt.size(100, 100) }
                        }
                        ColumnLayout {
                            Layout.fillWidth: true; spacing: 6
                            Text {
                                Layout.fillWidth: true; elide: Text.ElideRight
                                text: row.item.titulo || row.item.nome || ""
                                color: Theme.text; font { pixelSize: 15; weight: Font.DemiBold }
                            }
                            Text {
                                Layout.fillWidth: true; elide: Text.ElideRight
                                text: hub.secao === "musicas" ? (row.item.artista || "Artista desconhecido") + "  ·  " + (row.item.album || "Álbum local") :
                                      hub.secao === "desejos" ? "Steam  ·  " + row.item.appid :
                                      Number(row.item.pct || 0).toFixed(1) + "%  ·  " + (row.item.estado || "Histórico local") +
                                      (row.item.fonte_progresso === "estimativa" ? "  ·  estimativa em disco" : "") +
                                      (row.item.velocidade ? "  ·  " + (row.item.velocidade / 1048576).toFixed(1) + " MB/s" : "") +
                                      (row.item.eta ? "  ·  ETA " + Math.floor(row.item.eta / 60) + "min" : "")
                                color: Theme.muted; font.pixelSize: 12
                            }
                            ProgressBar { visible: hub.secao === "downloads"; Layout.fillWidth: true; from: 0; to: 100; value: row.item.pct || 0 }
                        }
                        ActionButton {
                            text: hub.secao === "musicas" ? "▶ Tocar" : hub.secao === "desejos" ? "Abrir na Steam ↗" : "Abrir pasta"
                            onClicked: {
                                if (hub.secao === "musicas") hub.tocar(row.item.id)
                                else if (hub.secao === "desejos") hub.abrirUrl("https://store.steampowered.com/app/" + row.item.appid)
                                else hub.abrirPasta(row.item.save_path || "")
                            }
                        }
                        ActionButton {
                            visible: hub.secao === "downloads" && row.item.fonte_progresso === "api"
                            text: "Pausar"; enabled: !hub.ocupado
                            onClicked: hub.controlarDownload(row.item.hash, "pausar")
                        }
                        ActionButton {
                            visible: hub.secao === "downloads" && row.item.fonte_progresso === "api"
                            text: "Retomar"; enabled: !hub.ocupado
                            onClicked: hub.controlarDownload(row.item.hash, "retomar")
                        }
                        ActionButton {
                            visible: hub.secao !== "downloads"
                            text: "×"; Accessible.name: "Remover da coleção"; enabled: !hub.ocupado
                            onClicked: window.deleteItem(hub.secao, row.item)
                        }
                    }
                }
            }

            ScrollView {
                id: home
                objectName: "homeView"
                anchors.fill: parent
                visible: hub.secao === "inicio"
                clip: true
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 18
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 18
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 170
                            radius: Theme.radius; color: Theme.surface; border.color: Theme.line
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 8
                                Text { text: "CONTINUAR"; color: Theme.accent; font { pixelSize: 10; weight: Font.Bold; letterSpacing: 2 } }
                                Text {
                                    text: hub.recentes.length > 0 ? hub.recentes[0].titulo : "Nada por aqui ainda"
                                    color: Theme.text; font { pixelSize: 22; weight: Font.Bold }
                                    elide: Text.ElideRight; Layout.fillWidth: true
                                }
                                Text { text: hub.recentes.length > 0 ? (hub.recentes[0].plataforma || "PC") + "  ·  " + Number(hub.recentes[0].horas || 0).toFixed(1) + " h" : "Jogue algo e ele aparece aqui."; color: Theme.muted; font.pixelSize: 12 }
                                Item { Layout.fillHeight: true }
                                ActionButton { text: "▶  Continuar jogando"; primary: true; enabled: hub.recentes.length > 0 && !hub.ocupado && !hub.emJogo; onClicked: hub.jogar(hub.recentes[0].id) }
                            }
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 170
                            radius: Theme.radius; color: Theme.surface; border.color: Theme.line
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 22; spacing: 8
                                Text { text: "COLEÇÃO"; color: Theme.accent; font { pixelSize: 10; weight: Font.Bold; letterSpacing: 2 } }
                                Text { text: hub.sistema.jogos + " jogos  ·  " + hub.sistema.musicas + " músicas"; color: Theme.text; font { pixelSize: 20; weight: Font.DemiBold } }
                                Text { text: hub.sistema.backup + "  ·  " + hub.sistema.pendentes + " sessão(ões) pendente(s)  ·  " + hub.sistema.disco_livre_gb + " GB livres"; color: Theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                Item { Layout.fillHeight: true }
                                RowLayout {
                                    ActionButton { text: "Ver jogos  →"; onClicked: hub.navegar("jogos") }
                                    ActionButton { text: "Backup agora"; enabled: !hub.ocupado; onClicked: hub.backup() }
                                }
                            }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: saudeCol.implicitHeight + 44
                        radius: Theme.radius; color: Theme.surface; border.color: Theme.line
                        ColumnLayout {
                            id: saudeCol
                            anchors.fill: parent; anchors.margins: 22; spacing: 10
                            Text { text: "SAÚDE DA COLEÇÃO"; color: Theme.accent; font { pixelSize: 10; weight: Font.Bold; letterSpacing: 2 } }
                            Text {
                                text: hub.saude.total > 0 ? hub.saude.ok + " de " + hub.saude.total + " jogos sem pendência de exe/ROM" : "Verificando coleção…"
                                color: Theme.text; font { pixelSize: 15; weight: Font.DemiBold }
                                wrapMode: Text.WordWrap; Layout.fillWidth: true
                            }
                            Repeater {
                                model: hub.saude.problemas.slice(0, 5)
                                Text {
                                    required property var modelData
                                    text: "• " + modelData.titulo + " — " + modelData.motivo
                                    color: Theme.muted; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true
                                }
                            }
                            RowLayout {
                                ActionButton { text: "Ver biblioteca  →"; onClicked: hub.navegar("jogos") }
                                ActionButton { text: "Abrir sistema"; onClicked: sistema.open() }
                            }
                        }
                    }
                    Text { text: "ACESSO RÁPIDO"; color: Theme.muted; font { pixelSize: 11; letterSpacing: 2 } }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: window.width >= 1250 ? 3 : 2
                        columnSpacing: 18; rowSpacing: 18
                        Repeater {
                            model: [{key: "jogos", nome: "Jogos", desc: "Grade, filtros e detalhes."}, {key: "musicas", nome: "Músicas", desc: "Player que atravessa telas."}, {key: "desejos", nome: "Desejos", desc: "O que entra na coleção."}, {key: "downloads", nome: "Downloads", desc: "qBittorrent local."}, {key: "integracoes", nome: "Integrações", desc: "Catálogos e emuladores."}, {key: "paleta", nome: "Busca global", desc: "Tudo com Ctrl+K."}]
                            Rectangle {
                                required property var modelData
                                Layout.fillWidth: true; Layout.preferredHeight: 118
                                radius: Theme.radius; color: Theme.surface; border.color: Theme.line
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 20; spacing: 14
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 6
                                        Text { text: modelData.nome; color: Theme.text; font { pixelSize: 17; weight: Font.DemiBold } }
                                        Text { text: modelData.desc; color: Theme.muted; font.pixelSize: 12 }
                                    }
                                    ActionButton {
                                        text: "Abrir  →"
                                        onClicked: {
                                            if (modelData.key === "paleta") { paletteQuery.clear(); hub.buscarPaleta(""); palette.open() }
                                            else hub.navegar(modelData.key)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    Text {
                        text: "JOGADOS RECENTEMENTE"; color: Theme.muted; font { pixelSize: 11; letterSpacing: 2 }
                        visible: hub.recentes.length > 0
                    }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: window.width >= 1250 ? 4 : 2
                        columnSpacing: 18; rowSpacing: 18
                        visible: hub.recentes.length > 0
                        Repeater {
                            model: hub.recentes
                            Rectangle {
                                required property var modelData
                                Layout.fillWidth: true; Layout.preferredHeight: 96
                                radius: Theme.radius; color: Theme.surface; border.color: Theme.line
                                RowLayout {
                                    anchors.fill: parent; anchors.margins: 14; spacing: 12
                                    Rectangle {
                                        width: 52; height: 68; radius: 8; color: Theme.raised
                                        Image { anchors.fill: parent; source: modelData.capa_url || ""; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true; spacing: 4
                                        Text {
                                            text: modelData.titulo; color: Theme.text; font { pixelSize: 14; weight: Font.DemiBold }
                                            elide: Text.ElideRight; Layout.fillWidth: true
                                        }
                                        Text { text: (modelData.plataforma || "PC") + "  ·  " + Number(modelData.horas || 0).toFixed(1) + " h"; color: Theme.muted; font.pixelSize: 11 }
                                    }
                                    ActionButton { text: "▶"; Accessible.name: "Jogar recente"; enabled: !hub.ocupado && !hub.emJogo; onClicked: hub.jogar(modelData.id) }
                                }
                            }
                        }
                    }
                }
            }

            ScrollView {
                anchors.fill: parent
                visible: hub.secao === "integracoes"
                clip: true
                contentWidth: availableWidth
                GridLayout {
                    width: parent.width
                    columns: window.width >= 1250 ? 3 : 2
                    columnSpacing: 18; rowSpacing: 18
                    Repeater {
                        model: hub.integracoes
                        Rectangle {
                            required property var modelData
                            Layout.fillWidth: true; Layout.preferredHeight: 238
                            radius: Theme.radius; color: Theme.surface; border.color: Theme.line
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 23; spacing: 12
                                RowLayout {
                                    Rectangle {
                                        width: 44; height: 44; radius: 13; color: Theme.raised
                                        Text { anchors.centerIn: parent; text: modelData.inicial; color: modelData.cor; font { pixelSize: 18; weight: Font.Bold } }
                                    }
                                    Item { Layout.fillWidth: true }
                                    Text { text: modelData.tipo === "catalogo" ? "SOB DEMANDA" : "LOCAL"; color: Theme.muted; font { pixelSize: 9; letterSpacing: 1 } }
                                }
                                Text { text: modelData.nome; color: Theme.text; font { pixelSize: 21; weight: Font.DemiBold } }
                                Text { text: modelData.descricao; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: Theme.muted; font.pixelSize: 12 }
                                Item { Layout.fillHeight: true }
                                ActionButton {
                                    text: modelData.tipo === "catalogo" ? "Explorar catálogo  →" : modelData.tipo === "download" ? "Ver downloads  →" : "Gerenciar emulador  →"
                                    Layout.fillWidth: true
                                    onClicked: {
                                        if (modelData.tipo === "catalogo") {
                                            catalogDialog.provider = modelData.chave
                                            catalogDialog.title = modelData.nome
                                            catalogQuery.clear()
                                            catalogDialog.open()
                                        } else if (modelData.tipo === "download") hub.navegar("downloads")
                                        else settings.open()
                                    }
                                }
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                anchors.centerIn: parent
                visible: hub.secao !== "integracoes" && hub.secao !== "inicio" && hub.quantidade === 0
                spacing: 14
                Text { text: hub.ocupado ? "◌" : "◇"; color: Theme.accent; font.pixelSize: 54; Layout.alignment: Qt.AlignHCenter }
                Text { text: hub.ocupado ? "Preparando sua coleção…" : hub.busca ? "Nenhum resultado por aqui." : "Este espaço está esperando por você."; color: Theme.text; font.pixelSize: 21; Layout.alignment: Qt.AlignHCenter }
                Text { text: hub.busca ? "Experimente outro nome ou limpe os filtros." : "Use as ações acima para começar."; color: Theme.muted; font.pixelSize: 13; Layout.alignment: Qt.AlignHCenter }
            }
        }
    }

    footer: Rectangle {
        height: 90
        color: Theme.surface
        Rectangle { width: parent.width; height: 1; color: Theme.line }
        RowLayout {
            anchors.fill: parent; anchors.margins: 20; spacing: 14
            Rectangle {
                width: 46; height: 46; radius: 12; color: Theme.raised
                Text { anchors.centerIn: parent; text: "♫"; color: Theme.accent; font.pixelSize: 25 }
                Image { anchors.fill: parent; source: hub.audio.capa_url; fillMode: Image.PreserveAspectCrop; asynchronous: true; sourceSize: Qt.size(96, 96) }
            }
            ColumnLayout {
                Layout.preferredWidth: window.width < 1150 ? 170 : 240; spacing: 5
                Text { text: hub.audio.titulo; color: Theme.text; font { pixelSize: 13; weight: Font.DemiBold } Layout.fillWidth: true; elide: Text.ElideRight }
                Text { text: hub.audio.artista; color: Theme.muted; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
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
            ProgressBar { Layout.fillWidth: true; Layout.maximumWidth: 180; from: 0; to: Math.max(1, hub.audio.duracao); value: hub.audio.posicao }
            Slider {
                visible: hub.volume.ok === true
                Layout.maximumWidth: 110; from: 0; to: 100; value: hub.volume.nivel || 0
                Accessible.name: "Volume do PC"
                onPressedChanged: { if (!pressed) hub.definirVolume(value) }
            }
            Item { Layout.fillWidth: true }
            BusyIndicator { running: hub.ocupado; visible: running; implicitWidth: 28; implicitHeight: 28 }
            Text { text: hub.atividade; color: Theme.muted; font.pixelSize: 11; Layout.maximumWidth: 190; elide: Text.ElideRight }
            ActionButton { text: "↻"; enabled: !hub.ocupado; Accessible.name: "Atualizar coleção"; onClicked: hub.atualizar() }
        }
    }

    Drawer {
        id: details
        width: Math.min(430, window.width * 0.5); height: window.height
        edge: Qt.RightEdge; modal: true
        background: Rectangle { color: Theme.surface; border.color: Theme.line }
        Flickable {
            anchors.fill: parent; anchors.margins: 28
            contentHeight: detailsColumn.implicitHeight
            clip: true
            ScrollBar.vertical: ScrollBar {}
        ColumnLayout {
            id: detailsColumn
            width: parent.width; spacing: 18
            RowLayout { Layout.fillWidth: true; Text { text: "SOBRE O JOGO"; color: Theme.muted; font { pixelSize: 11; letterSpacing: 2 } } Item { Layout.fillWidth: true } ActionButton { text: "×"; onClicked: details.close() } }
            Image { Layout.fillWidth: true; Layout.preferredHeight: Math.min(280, window.height * 0.28); source: hub.selecionado.capa_url || ""; fillMode: Image.PreserveAspectFit; asynchronous: true }
            Text { text: hub.selecionado.titulo || ""; color: Theme.text; font { pixelSize: 27; weight: Font.Bold } Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Text { text: (hub.selecionado.plataforma || "PC") + "  ·  " + (hub.selecionado.status || "backlog"); color: Theme.accent; font.pixelSize: 13 }
            Text { text: Number(hub.selecionado.horas || 0).toFixed(1) + " horas jogadas" + (hub.selecionado.nota !== null && hub.selecionado.nota !== undefined ? "  ·  nota " + hub.selecionado.nota + "/10" : ""); color: Theme.muted; font.pixelSize: 14 }
            Text { text: hub.selecionado.etiquetas || "Sem etiquetas — edite para organizar."; color: Theme.muted; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            ActionButton { Layout.fillWidth: true; text: "▶  Jogar"; primary: true; enabled: !hub.ocupado && !hub.emJogo; onClicked: { hub.jogar(hub.selecionado.id); details.close() } }
            ActionButton { Layout.fillWidth: true; text: hub.selecionado.favorito ? "★  Remover dos favoritos" : "☆  Adicionar aos favoritos"; enabled: !hub.ocupado; onClicked: hub.favorito(hub.selecionado.id) }
            ActionButton { Layout.fillWidth: true; text: "Editar jogo"; enabled: !hub.ocupado; onClicked: window.editGame(hub.selecionado) }
            ActionButton { Layout.fillWidth: true; text: "Remover da biblioteca"; enabled: !hub.ocupado; onClicked: { window.deleteItem("jogos", hub.selecionado); details.close() } }
            Item { Layout.fillHeight: true }
            Text { text: "Mods, presets, cheats e saves estão nas ferramentas clássicas, em Configurações."; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        }
        }
    }

    Dialog {
        id: settings
        title: "Seu espaço, do seu jeito"
        anchors.centerIn: parent
        width: Math.min(560, window.width - 80)
        modal: true; standardButtons: Dialog.Close
        onOpened: hub.consultarVolume()
        ColumnLayout {
            width: parent.width; spacing: 16
            Text { text: "TUCOTECA  /  DESKTOP QT"; color: Theme.accent; font { pixelSize: 10; letterSpacing: 2 } }
            Text { text: "Interface Qt Quick, biblioteca local e integrações independentes."; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            ActionButton { text: window.immersive ? "Sair do Big Picture" : "Entrar no Big Picture"; Layout.fillWidth: true; onClicked: { settings.close(); window.toggleImmersive() } }
            ActionButton { text: "Criar backup da coleção"; Layout.fillWidth: true; enabled: !hub.ocupado; onClicked: hub.backup() }
            ActionButton { text: "Sistema: backups, sessões e logs"; Layout.fillWidth: true; onClicked: { settings.close(); sistema.open() } }
            RowLayout {
                visible: hub.volume.ok === true
                Layout.fillWidth: true
                Label { text: "Volume do PC" }
                Slider {
                    Layout.fillWidth: true; from: 0; to: 100; value: hub.volume.nivel || 0
                    onPressedChanged: { if (!pressed) hub.definirVolume(value) }
                }
                ActionButton { text: hub.volume.mudo ? "Ativar som" : "Silenciar"; onClicked: hub.silenciar() }
            }
            ActionButton { text: "Abrir ferramentas clássicas"; Layout.fillWidth: true; enabled: !hub.ocupado && !hub.emJogo; onClicked: hub.classico() }
            Text { text: "A interface clássica reúne importação avançada, mods, emuladores, CSV, pacotes e manutenção. A troca encerra esta interface e mantém a mesma coleção."; color: Theme.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: 12 }
            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
            Text { text: "F11  Tela cheia     Ctrl+1…6  Categorias\nCtrl+F  Buscar     Ctrl+K  Busca global     Setas  Navegar\nEnter  Jogar     Espaço  Detalhes"; color: Theme.muted; lineHeight: 1.5; font.pixelSize: 12 }
        }
    }

    Dialog {
        id: gameDialog
        property int gid: 0
        anchors.centerIn: parent; width: 580; modal: true
        title: gid ? "Editar jogo" : "Adicionar jogo"
        standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: hub.salvarJogo(gid, gameTitle.text, gameExe.text, gameArgs.text, gameStatus.currentText, gameNota.text, gameTags.text)
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
        }
    }
    FileDialog { id: executableDialog; title: "Escolha o executável"; onAccepted: gameExe.text = decodeURIComponent(selectedFile.toString().replace(Qt.platform.os === "windows" ? /^file:\/\/\// : /^file:\/\//, "")) }
    FolderDialog { id: musicFolder; title: "Importar pasta de músicas"; onAccepted: hub.importarMusicas(selectedFolder) }
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
                delegate: ActionButton {
                    required property var item
                    width: ListView.view.width - 12
                    text: item.titulo + "  ↗"
                    onClicked: hub.abrirUrl(item.url)
                }
            }
            Text { text: "A pesquisa acessa a fonte somente quando solicitada. Resultados abrem no navegador."; color: Theme.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true; font.pixelSize: 12 }
        }
    }
    Dialog {
        id: palette
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
            Text { text: "Somente coleção local. ↑↓ navega, Enter abre."; color: Theme.muted; font.pixelSize: 11 }
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
                Text { text: "FILA DE REPRODUÇÃO"; color: Theme.muted; font { pixelSize: 11; letterSpacing: 2 } }
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
            Text { text: "Repetir toca a faixa atual; aleatório sorteia sem repetir a atual."; color: Theme.muted; font.pixelSize: 11; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
    }

    Dialog {
        id: sistema
        anchors.centerIn: parent
        width: Math.min(640, window.width - 80); height: Math.min(560, window.height - 100)
        modal: true; standardButtons: Dialog.Close
        title: "Sistema e manutenção"
        ColumnLayout {
            anchors.fill: parent; spacing: 12
            RowLayout {
                Layout.fillWidth: true
                ActionButton { text: "↻ Atualizar"; onClicked: { backupList.model = hub.listarBackups(); sessaoList.model = hub.listarSessoes(); logView.text = hub.verLog() } }
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
                        text: "+1h"; enabled: !hub.ocupado
                        onClicked: hub.registrarSessao(modelData.gid, 1.0)
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
        onOpened: { backupList.model = hub.listarBackups(); sessaoList.model = hub.listarSessoes(); logView.text = hub.verLog() }
    }

    Popup {
        id: toast
        property string message: ""
        property bool error: false
        x: (window.width - width) / 2
        y: window.height - height - 125
        width: Math.min(680, window.width - 70)
        padding: 18
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { radius: 12; color: Theme.raised; border.color: toast.error ? Theme.danger : Theme.accent }
        contentItem: Text { text: toast.message; color: Theme.text; wrapMode: Text.WordWrap; font { family: Theme.family; pixelSize: 13 } }
    }
    Timer { id: toastTimer; interval: 7000; onTriggered: toast.close() }
}
