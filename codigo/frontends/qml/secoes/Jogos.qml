import QtQuick
import QtQuick.Controls
import ".."

GridView {
    id: games
    objectName: "gamesGrid"
    property var shell
    model: hub.itens
    clip: true
    cellWidth: width / Math.max(1, Math.floor(width / (shell.immersive || hub.aparencia.modo_simples || Theme.densidade === "bigpicture" ? 235 : Theme.densidade === "compacto" ? 170 : 190)))
    cellHeight: Math.min(shell.height < 740 ? Math.max(200, height - 8) : 370, cellWidth * 1.32 + 55)
    cacheBuffer: cellHeight * 2
    keyNavigationEnabled: true; activeFocusOnTab: true
    highlightMoveDuration: 160
    highlightRangeMode: GridView.ApplyRange
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
    Keys.onReturnPressed: { if (hub.selecionado.id && !hub.ocupado) hub.jogar(hub.selecionado.id) }
    Keys.onSpacePressed: { if (hub.selecionado.id) shell.showDetails() }
    onCurrentIndexChanged: { if (activeFocus) hub.selecionar(currentIndex) }
    delegate: PosterCard {
        required property var item
        required property int index
        width: games.cellWidth - 8; height: games.cellHeight - 10
        game: item; selected: hub.selecionado.id === item.id
        onChosen: { games.currentIndex = index; games.forceActiveFocus(); hub.selecionar(index) }
        onActivated: { if (!hub.ocupado) hub.jogar(item.id) }
        onDetails: games.shell.showDetails()
    }
}
