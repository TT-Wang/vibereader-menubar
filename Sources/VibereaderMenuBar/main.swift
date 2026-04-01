import Foundation
import AppKit
import SwiftUI

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

// MARK: - AppState

class AppState: ObservableObject {
    @Published var articles: [Article] = []
    @Published var lastFetched: Date? = nil
    @Published var isRefreshing: Bool = false
    @Published var searchText: String = ""

    var filteredArticles: [Article] {
        let sorted = articles.sorted { $0.score > $1.score }
        let top = Array(sorted.prefix(15))
        if searchText.isEmpty { return top }
        return top.filter { a in
            a.title.localizedCaseInsensitiveContains(searchText) ||
            a.source.localizedCaseInsensitiveContains(searchText) ||
            a.categories.contains { $0.localizedCaseInsensitiveContains(searchText) }
        }
    }

    func fetchArticles() {
        guard let url = URL(string: "\(Config.apiURL)/api/articles") else {
            fputs("fetchArticles: invalid URL\n", stderr)
            return
        }

        URLSession.shared.dataTask(with: url) { [weak self] data, _, error in
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
                    withAnimation {
                        self.articles = feedResponse.articles
                    }
                    self.lastFetched = serverDate
                }
            } catch {
                fputs("fetchArticles decode error: \(error)\n", stderr)
            }
        }.resume()
    }

    func refreshFeed() {
        guard let url = URL(string: "\(Config.apiURL)/refresh") else {
            fputs("refreshFeed: invalid URL\n", stderr)
            return
        }

        let oldFetchedAt = lastFetched

        DispatchQueue.main.async {
            self.isRefreshing = true
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        URLSession.shared.dataTask(with: request) { [weak self] _, response, error in
            if let error = error {
                fputs("refreshFeed error: \(error.localizedDescription)\n", stderr)
                DispatchQueue.main.async { self?.isRefreshing = false }
                return
            }
            if let http = response as? HTTPURLResponse {
                fputs("refreshFeed: \(http.statusCode)\n", stderr)
            }
            // Poll until fetched_at changes or timeout after 15s
            self?.pollForUpdate(oldFetchedAt: oldFetchedAt, attempt: 0)
        }.resume()
    }

    func pollForUpdate(oldFetchedAt: Date?, attempt: Int) {
        guard attempt < 8 else {
            fputs("refreshFeed: timed out waiting for update\n", stderr)
            DispatchQueue.main.async { self.isRefreshing = false }
            return
        }

        DispatchQueue.global().asyncAfter(deadline: .now() + 2.0) { [weak self] in
            guard let self = self,
                  let url = URL(string: "\(Config.apiURL)/api/articles") else { return }

            URLSession.shared.dataTask(with: url) { data, _, error in
                guard let data = data else {
                    self.pollForUpdate(oldFetchedAt: oldFetchedAt, attempt: attempt + 1)
                    return
                }

                if let feed = try? JSONDecoder().decode(FeedResponse.self, from: data) {
                    let serverDate = ISO8601DateFormatter().date(from: feed.fetchedAt)
                    let changed = (serverDate != nil && serverDate != oldFetchedAt)

                    if changed {
                        fputs("refreshFeed: articles updated\n", stderr)
                        DispatchQueue.main.async {
                            withAnimation {
                                self.articles = feed.articles
                            }
                            self.lastFetched = serverDate
                            self.isRefreshing = false
                        }
                    } else {
                        self.pollForUpdate(oldFetchedAt: oldFetchedAt, attempt: attempt + 1)
                    }
                } else {
                    self.pollForUpdate(oldFetchedAt: oldFetchedAt, attempt: attempt + 1)
                }
            }.resume()
        }
    }
}

// MARK: - PopoverContentView

struct PopoverContentView: View {
    @ObservedObject var state: AppState

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Vibereader")
                    .font(.headline)
                    .fontWeight(.bold)
                Spacer()
                Text(timeAgoText)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Button {
                    state.refreshFeed()
                } label: {
                    if state.isRefreshing {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 12))
                    }
                }
                .buttonStyle(.borderless)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)

            Divider()

            // Search bar
            TextField("Search articles...", text: $state.searchText)
                .textFieldStyle(.roundedBorder)
                .padding(.horizontal, 16)
                .padding(.vertical, 8)

            Divider()

            // Article list
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(state.filteredArticles, id: \.id) { article in
                        ArticleRowView(article: article)
                        Divider()
                    }
                }
            }

            Divider()

            // Footer
            Button("Quit Vibereader") {
                NSApplication.shared.terminate(nil)
            }
            .buttonStyle(.borderless)
            .font(.caption)
            .foregroundColor(.secondary)
            .padding(.vertical, 8)
        }
        .frame(width: 380, height: 500)
        .background(Color(nsColor: .windowBackgroundColor))
    }

    var timeAgoText: String {
        guard let date = state.lastFetched else { return "never" }
        let minutes = Int(Date().timeIntervalSince(date) / 60)
        if minutes < 1 { return "just now" }
        if minutes < 60 { return "\(minutes)m ago" }
        return "\(minutes / 60)h ago"
    }
}

// MARK: - ArticleRowView

struct ArticleRowView: View {
    let article: Article
    @State private var isHovered = false

    var body: some View {
        Button {
            if let url = URL(string: article.url) {
                NSWorkspace.shared.open(url)
            }
        } label: {
            VStack(alignment: .leading, spacing: 6) {
                // Title
                Text(article.title)
                    .font(.system(size: 13, weight: .semibold))
                    .lineLimit(2)
                    .foregroundColor(.primary)

                // Score badge + categories + source
                HStack(spacing: 6) {
                    // Score badge — colored
                    Text(String(format: "%.1f", article.score))
                        .font(.system(size: 10, weight: .bold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(scoreColor.opacity(0.2))
                        .foregroundColor(scoreColor)
                        .clipShape(RoundedRectangle(cornerRadius: 4))

                    // Category pills
                    ForEach(article.categories.prefix(3), id: \.self) { cat in
                        Text(cat)
                            .font(.system(size: 9))
                            .padding(.horizontal, 5)
                            .padding(.vertical, 2)
                            .background(Color.purple.opacity(0.15))
                            .foregroundColor(.purple)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                    }

                    Spacer()

                    // Source
                    Text(article.source)
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(isHovered ? Color.primary.opacity(0.06) : Color.clear)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }

    var scoreColor: Color {
        if article.score > 2.0 { return .green }
        if article.score > 1.0 { return .yellow }
        return .gray
    }
}

// MARK: - AppDelegate

class AppDelegate: NSObject, NSApplicationDelegate, NSPopoverDelegate {
    var statusItem: NSStatusItem!
    var popover: NSPopover!
    var appState = AppState()
    var refreshTimer: Timer?

    func applicationDidFinishLaunching(_ notification: Notification) {
        fputs("VibereaderMenuBar: launching...\n", stderr)

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            button.title = "V"
            button.action = #selector(togglePopover(_:))
            button.target = self
            fputs("VibereaderMenuBar: status item created\n", stderr)
        }

        popover = NSPopover()
        popover.contentSize = NSSize(width: 380, height: 500)
        popover.behavior = .transient
        popover.delegate = self
        popover.contentViewController = NSHostingController(rootView: PopoverContentView(state: appState))

        appState.fetchArticles()

        let timer = Timer(timeInterval: 60, target: self, selector: #selector(timerFired(_:)), userInfo: nil, repeats: true)
        RunLoop.main.add(timer, forMode: .common)
        refreshTimer = timer
        fputs("VibereaderMenuBar: ready\n", stderr)
    }

    @objc func togglePopover(_ sender: Any?) {
        guard let button = statusItem.button else { return }
        if popover.isShown {
            popover.performClose(sender)
        } else {
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            // Ensure popover window becomes key for keyboard input (search field)
            popover.contentViewController?.view.window?.makeKey()
        }
    }

    @objc func timerFired(_ timer: Timer) {
        appState.fetchArticles()
    }
}

// MARK: - Entry Point

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let delegate = AppDelegate()
app.delegate = delegate
app.activate(ignoringOtherApps: true)
app.run()
