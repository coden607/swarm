import SwiftUI
import WebKit

final class Model: ObservableObject {
    @Published var serverURL: String = UserDefaults.standard.string(forKey: "server") ?? ""
    @Published var showSettings = false

    func save(_ raw: String) {
        var v = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if !v.isEmpty && !v.contains("://") { v = "http://" + v }
        serverURL = v
        UserDefaults.standard.set(v, forKey: "server")
    }
}

struct ContentView: View {
    @StateObject private var model = Model()
    @State private var draft = ""

    var body: some View {
        ZStack(alignment: .topTrailing) {
            if model.serverURL.isEmpty {
                VStack(spacing: 12) {
                    Text("Swarm").font(.largeTitle).bold()
                    Text("Enter the address of your Swarm server, e.g. 192.168.1.20:8000 or your remote link.")
                        .multilineTextAlignment(.center)
                    TextField("Server address", text: $draft)
                        .textFieldStyle(.roundedBorder)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                        .keyboardType(.URL)
                    Button("Connect") { model.save(draft) }
                        .buttonStyle(.borderedProminent)
                }
                .padding()
            } else {
                SwarmWebView(url: model.serverURL).ignoresSafeArea(edges: .bottom)
                Button {
                    draft = model.serverURL
                    model.showSettings = true
                } label: {
                    Image(systemName: "gearshape.fill").padding(12)
                }
            }
        }
        .sheet(isPresented: $model.showSettings) {
            NavigationView {
                Form {
                    Section(header: Text("Server address")) {
                        TextField("192.168.1.20:8000", text: $draft)
                            .autocapitalization(.none)
                            .disableAutocorrection(true)
                            .keyboardType(.URL)
                    }
                    Button("Save") { model.save(draft); model.showSettings = false }
                }
                .navigationTitle("Settings")
            }
        }
    }
}

struct SwarmWebView: UIViewRepresentable {
    let url: String

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let cfg = WKWebViewConfiguration()
        cfg.allowsInlineMediaPlayback = true
        cfg.userContentController.add(context.coordinator, name: "swarmCache")
        let web = WKWebView(frame: .zero, configuration: cfg)
        web.navigationDelegate = context.coordinator
        context.coordinator.web = web
        context.coordinator.load(url)
        return web
    }

    func updateUIView(_ web: WKWebView, context: Context) {
        if context.coordinator.server != url { context.coordinator.load(url) }
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {
        weak var web: WKWebView?
        var server = ""
        private var offline = false
        private var timer: Timer?

        override init() {
            super.init()
            // While the offline page is shown, retry the real server every 10 s.
            timer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { [weak self] _ in
                guard let self = self, self.offline else { return }
                self.reload()
            }
        }

        deinit { timer?.invalidate() }

        func load(_ url: String) {
            server = url
            reload()
        }

        private func reload() {
            guard let u = URL(string: server) else { return }
            web?.load(URLRequest(url: u, timeoutInterval: 6))
        }

        // The web UI posts its last known state here after every successful refresh.
        func userContentController(_ c: WKUserContentController, didReceive message: WKScriptMessage) {
            if let s = message.body as? String { UserDefaults.standard.set(s, forKey: "cache") }
        }

        func webView(_ w: WKWebView, didFinish navigation: WKNavigation!) {
            if w.url?.scheme != "about" { offline = false }
        }

        func webView(_ w: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            showOffline(w)
        }

        func webView(_ w: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            showOffline(w)
        }

        private func showOffline(_ w: WKWebView) {
            offline = true
            let cache = UserDefaults.standard.string(forKey: "cache") ?? "{}"
            let b64 = Data(cache.utf8).base64EncodedString()
            let html = """
            <!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">
            <body style="font-family:-apple-system;margin:1rem;background:#f5f5f5">
            <div style="background:#e67700;color:#fff;padding:1rem;border-radius:8px"><b>OFFLINE</b> - server unreachable. Last known state shown; retrying every 10 s.</div>
            <p id="t"></p><div id="l"></div><h3>Recent alerts</h3><div id="e"></div>
            <script>
            var c = {};
            try { c = JSON.parse(atob("\(b64)")); } catch (x) {}
            var s = c.status || {cameras: [], total: 0};
            document.getElementById("t").textContent = c.ts ? "As of " + new Date(c.ts).toLocaleString() + " - " + s.total + " people across " + s.cameras.length + " camera(s)" : "No cached data yet.";
            s.cameras.forEach(function (x) {
              var d = document.createElement("div");
              d.style.cssText = "background:#fff;padding:.8rem;margin:.5rem 0;border-radius:8px";
              d.textContent = x.id + " (" + x.brand + "): " + (x.count === null ? "-" : x.count) + " people - " + x.status;
              document.getElementById("l").appendChild(d);
            });
            (c.events || []).slice(0, 30).forEach(function (x) {
              var d = document.createElement("div");
              d.textContent = new Date(x.ts * 1000).toLocaleString() + " - " + x.label + ": " + x.count;
              document.getElementById("e").appendChild(d);
            });
            </script>
            """
            w.loadHTMLString(html, baseURL: URL(string: "about:blank"))
        }
    }
}
