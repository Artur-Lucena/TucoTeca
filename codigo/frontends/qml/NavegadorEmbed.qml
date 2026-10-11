import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

// Navegador YouTube embutido, usado pela seção "YouTube".
//
// Regras de segurança/uso (decisão de projeto):
// - navegação restrita a https e hosts YouTube (ver `permitirNavegacao`);
// - perfil off-the-record (sem cookies/persistência de terceiros);
// - download de vídeo é sempre ação explícita do usuário, pelo Hub;
// - sem Addons instalado, o Main.qml usa Loader com sourceComponent vazio
//   e mostra o diálogo clássico (fallback da variante essencial).
Item {
    id: raiz
    property url urlInicial: "https://www.youtube.com/"
    property bool carregando: false
    property string titulo: ""
    property string urlAtual: ""
    signal pedirDownload(string url)
    signal pedirAbrirExterno(string url)

    function irPara(url) {
        const alvo = String(url || "").trim()
        if (!alvo) return
        view.url = alvo.indexOf("http") === 0 ? alvo : "https://www.youtube.com/results?search_query=" + encodeURIComponent(alvo)
    }
    function voltar() { if (view.canGoBack) view.goBack() }
    function recarregar() { view.reload() }

    function permitirNavegacao(url) {
        // Aceita somente https em hosts do YouTube.
        if (String(url.scheme).toLowerCase() !== "https") return false
        const host = String(url.host).toLowerCase()
        return host === "www.youtube.com" || host === "youtube.com"
            || host === "m.youtube.com" || host === "youtu.be"
            || host.endsWith(".youtube.com") || host.endsWith(".youtube-nocookie.com")
    }

    WebEngineView {
        id: view
        objectName: "navegadorEmbed"
        anchors.fill: parent
        url: raiz.urlInicial
        profile: WebEngineProfile {
            offTheRecord: true          // sem cookies/armazenamento persistente
            httpUserAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        }
        onLoadingChanged: function(loadRequest) {
            raiz.carregando = loadRequest.status === WebEngineView.LoadStartedStatus
            if (loadRequest.status === WebEngineView.LoadSucceededStatus
                    || loadRequest.status === WebEngineView.LoadFailedStatus) {
                raiz.urlAtual = view.url.toString()
            }
        }
        onTitleChanged: raiz.titulo = view.title

        // Só deixa navegar dentro do YouTube; o resto abre fora do Hub.
        onNavigationRequested: function(request) {
            if (!raiz.permitirNavegacao(request.url)) {
                request.action = WebEngineNavigationRequest.IgnoreRequest
                raiz.pedirAbrirExterno(request.url.toString())
            }
        }

        // JS não confiável: só lemos a URL da página quando o Hub pedir.
        function urlAtualAsync(callback) {
            view.runJavaScript("window.location.href", function(r) { callback(String(r || "")) })
        }
    }
}
