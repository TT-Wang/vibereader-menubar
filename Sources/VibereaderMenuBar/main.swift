import Foundation
import AppKit

// MARK: - Config

enum Config {
    static var apiURL: String {
        ProcessInfo.processInfo.environment["VIBEREADER_API"] ?? "http://43.134.177.69:8888"
    }
}

// MARK: - Data Models

struct Article: Decodable {
    let id: String
    let title: String
    let url: String
    let source: String
    let score: Double
    let categories: [String]
}

struct FeedResponse: Decodable {
    let articles: [Article]
    let fetchedAt: String

    enum CodingKeys: String, CodingKey {
        case articles
        case fetchedAt = "fetched_at"
    }
}

// MARK: - AppDelegate

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var menu: NSMenu!
    var refreshTimer: Timer?
    var lastFetched: Date?
    var articles: [Article] = []

    func applicationDidFinishLaunching(_ notification: Notification) {
        fputs("VibereaderMenuBar: launching...\n", stderr)

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            button.title = "V"
            fputs("VibereaderMenuBar: status item created\n", stderr)
        }

        menu = NSMenu()
        statusItem.menu = menu
        setupMenu()

        fetchArticles()

        let timer = Timer(timeInterval: 60, target: self, selector: #selector(timerFired(_:)), userInfo: nil, repeats: true)
        RunLoop.main.add(timer, forMode: .common)
        refreshTimer = timer
        fputs("VibereaderMenuBar: ready\n", stderr)
    }

    @objc func timerFired(_ timer: Timer) {
        fetchArticles()
    }

    // MARK: - Menu Setup

    func setupMenu() {
        menu.removeAllItems()

        // Fetched time header
        let fetchedLabel: String
        if let lastFetched = lastFetched {
            let minutes = Int(Date().timeIntervalSince(lastFetched) / 60)
            fetchedLabel = "fetched \(minutes) min ago"
        } else {
            fetchedLabel = "fetched: never"
        }
        let headerItem = NSMenuItem(title: fetchedLabel, action: nil, keyEquivalent: "")
        headerItem.isEnabled = false
        menu.addItem(headerItem)

        menu.addItem(NSMenuItem.separator())

        // Articles (up to 15)
        let displayArticles = Array(articles.prefix(15))
        for article in displayArticles {
            var truncatedTitle = article.title
            if truncatedTitle.count > 60 {
                let index = truncatedTitle.index(truncatedTitle.startIndex, offsetBy: 60)
                truncatedTitle = String(truncatedTitle[..<index]) + "..."
            }
            let scoreStr = String(format: "%.1f", article.score)
            let itemTitle = "\(truncatedTitle)  \u{27E8}\(scoreStr)\u{27E9} \(article.source)"

            let menuItem = NSMenuItem(
                title: itemTitle,
                action: #selector(openArticle(_:)),
                keyEquivalent: ""
            )
            menuItem.representedObject = article.url as String
            menuItem.target = self
            menu.addItem(menuItem)
        }

        menu.addItem(NSMenuItem.separator())

        // Refresh Feed
        let refreshItem = NSMenuItem(
            title: "Refresh Feed",
            action: #selector(refreshFeed(_:)),
            keyEquivalent: ""
        )
        refreshItem.target = self
        menu.addItem(refreshItem)

        menu.addItem(NSMenuItem.separator())

        // Quit
        let quitItem = NSMenuItem(
            title: "Quit Vibereader",
            action: #selector(NSApplication.terminate(_:)),
            keyEquivalent: ""
        )
        menu.addItem(quitItem)
    }

    // MARK: - Networking

    func fetchArticles() {
        guard let url = URL(string: "\(Config.apiURL)/api/articles") else {
            fputs("fetchArticles: invalid URL\n", stderr)
            return
        }

        URLSession.shared.dataTask(with: url) { [weak self] data, response, error in
            guard let self = self else { return }

            if let error = error {
                fputs("fetchArticles error: \(error.localizedDescription)\n", stderr)
                return
            }

            guard let data = data else {
                fputs("fetchArticles: no data\n", stderr)
                return
            }

            do {
                let feedResponse = try JSONDecoder().decode(FeedResponse.self, from: data)
                let serverDate = ISO8601DateFormatter().date(from: feedResponse.fetchedAt) ?? Date()
                DispatchQueue.main.async {
                    self.articles = feedResponse.articles
                    self.lastFetched = serverDate
                    self.setupMenu()
                }
            } catch {
                fputs("fetchArticles decode error: \(error)\n", stderr)
            }
        }.resume()
    }

    @objc func refreshFeed(_ sender: Any?) {
        fputs("refreshFeed: triggered\n", stderr)
        guard let url = URL(string: "\(Config.apiURL)/refresh") else {
            fputs("refreshFeed: invalid URL\n", stderr)
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            if let error = error {
                fputs("refreshFeed error: \(error.localizedDescription)\n", stderr)
                return
            }
            if let http = response as? HTTPURLResponse {
                fputs("refreshFeed: \(http.statusCode)\n", stderr)
            }
            self?.fetchArticles()
        }.resume()
    }

    @objc func openArticle(_ sender: NSMenuItem) {
        guard let urlString = sender.representedObject as? String,
              let url = URL(string: urlString) else {
            fputs("openArticle: invalid URL\n", stderr)
            return
        }
        NSWorkspace.shared.open(url)
    }
}

// MARK: - Entry Point

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let delegate = AppDelegate()
app.delegate = delegate
app.activate(ignoringOtherApps: true)
app.run()
