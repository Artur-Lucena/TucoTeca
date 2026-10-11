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
    property alias perfil: view.profile
    property string erro: ""
    signal pedirDownload(string url)
    signal pedirAbrirExterno(string url)

    function irPara(url) {
        const alvo = String(url || "").trim()
        if (!alvo) return
        const validada = alvo.indexOf("http") === 0 ? hub.youtubeIr(alvo, "") : hub.youtubeBuscar(alvo)
        if (validada) view.url = validada
    }
    function urlAtualAsync(callback) { callback(view.url.toString()) }
    function voltar() { if (view.canGoBack) view.goBack() }
    function recarregar() { view.reload() }

    function permitirNavegacao(url) {
        // Aceita somente https em hosts do YouTube.
        if (String(url) === "about:blank") return true
        return hub.youtubeIr(String(url), "") !== ""
    }

    WebEngineView {
        id: view
        objectName: "navegadorEmbed"
        anchors.fill: parent
        url: raiz.urlInicial
        profile: WebEngineProfile {
            offTheRecord: true          // sem cookies/armazenamento persistente
            onDownloadRequested: function(download) { download.cancel() }
        }
        settings.localContentCanAccessFileUrls: false
        settings.localContentCanAccessRemoteUrls: false
        onPermissionRequested: function(permission) { permission.deny() }
        onFileDialogRequested: function(request) { request.reject() }
        onLoadingChanged: function(loadRequest) {
            raiz.carregando = loadRequest.status === WebEngineView.LoadStartedStatus
            if (loadRequest.status === WebEngineView.LoadSucceededStatus
                    || loadRequest.status === WebEngineView.LoadFailedStatus) {
                raiz.urlAtual = view.url.toString()
                raiz.erro = loadRequest.status === WebEngineView.LoadFailedStatus ? loadRequest.errorString : ""
            }
        }
        onTitleChanged: raiz.titulo = view.title
        onUrlChanged: { raiz.urlAtual = view.url.toString(); hub.consultarSponsor(raiz.urlAtual) }

        // Só deixa navegar dentro do YouTube; o resto abre fora do Hub.
        onNavigationRequested: function(request) {
            if (!raiz.permitirNavegacao(request.url)) {
                request.reject()
                // Um redirect/iframe não pode abrir um navegador silenciosamente.
                if (request.isMainFrame && request.navigationType === WebEngineNavigationRequest.LinkClickedNavigation)
                    raiz.pedirAbrirExterno(request.url.toString())
            }
        }
        onNewWindowRequested: function(request) {
            if (request.userInitiated) raiz.pedirAbrirExterno(request.requestedUrl.toString())
        }

        // JS não confiável: só lemos a URL da página quando o Hub pedir.
    }
    Label {
        anchors { left: parent.left; right: parent.right; bottom: parent.bottom; margins: 12 }
        visible: raiz.erro !== ""
        text: "YouTube indisponível aqui: " + raiz.erro + ". Use o navegador externo."
        wrapMode: Text.WordWrap
        color: "#ffffff"
        background: Rectangle { color: "#7b342b"; radius: 8 }
    }
    Timer {
        interval: 1000; repeat: true
        running: hub.preferencias.sponsorblock && hub.sponsor.segmentos.length > 0
        onTriggered: {
            // Somente tempos numéricos validados no Python. Revalida o ID da
            // página em cada tick para não aplicar um trecho a outro vídeo.
            const id = JSON.stringify(hub.sponsor.video)
            const segmentos = JSON.stringify(hub.sponsor.segmentos)
            view.runJavaScript("(function(){const u=new URL(location.href);const id=u.searchParams.get('v')||u.pathname.split('/')[2];if(id!==" + id + ")return;const v=document.querySelector('video');if(!v)return;for(const s of " + segmentos + "){if(v.currentTime>=s[0]&&v.currentTime<s[1]){v.currentTime=s[1];break;}}})()")
        }
    }
}
