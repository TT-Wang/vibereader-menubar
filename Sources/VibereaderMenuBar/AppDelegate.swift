import AppKit
import SwiftUI
import os.log

@MainActor
class AppDelegate: NSObject, NSApplicationDelegate {
    private let logger = Logger(subsystem: "com.vibereader.menubar", category: "AppDelegate")
    var statusItem: NSStatusItem!
    var popover: NSPopover!
    var appState = AppState()
    var refreshTimer: Timer?
    var statusTimer: Timer?
    var backendProcess: Process?

    func applicationDidFinishLaunching(_ notification: Notification) {
        logger.info("launching...")
        startBackend()

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            button.title = "V"
            button.action = #selector(togglePopover(_:))
            button.target = self
        }

        popover = NSPopover()
        popover.contentSize = NSSize(width: 380, height: 500)
        popover.behavior = .transient
        popover.contentViewController = NSHostingController(
            rootView: PopoverContentView(state: appState)
        )

        Task { await appState.fetchArticles() }
        Task { await appState.fetchStatus() }

        // Block-based timers to avoid retain cycles
        let rTimer = Timer(timeInterval: 60, repeats: true) { [weak self] _ in
            guard let self else { return }
            Task { await self.appState.fetchArticles() }
        }
        RunLoop.main.add(rTimer, forMode: .common)
        refreshTimer = rTimer

        let sTimer = Timer(timeInterval: 10, repeats: true) { [weak self] _ in
            guard let self else { return }
            Task { await self.appState.fetchStatus() }
            self.updateIcon()
        }
        RunLoop.main.add(sTimer, forMode: .common)
        statusTimer = sTimer

        logger.info("ready")
    }

    @objc func togglePopover(_ sender: Any?) {
        guard let button = statusItem.button else { return }
        if popover.isShown {
            popover.performClose(sender)
        } else {
            popover.show(relativeTo: button.bounds, of: button, preferredEdge: .minY)
            popover.contentViewController?.view.window?.makeKey()
        }
    }

    func updateIcon() {
        guard let button = statusItem.button else { return }
        button.contentTintColor = appState.claudeActive ? .systemGreen : nil
    }

    // MARK: - Backend lifecycle

    func startBackend() {
        // Find vibereader_web.py next to the built binary or in the repo
        let candidates = [
            Bundle.main.bundlePath + "/../vibereader_web.py",
            Bundle.main.bundlePath + "/../../vibereader_web.py",
            NSHomeDirectory() + "/vibereader-menubar/vibereader_web.py",
        ]
        guard let script = candidates.first(where: { FileManager.default.fileExists(atPath: $0) }) else {
            logger.warning("vibereader_web.py not found — backend not started. Run it manually: python3 vibereader_web.py")
            return
        }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["python3", script]
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice
        do {
            try process.run()
            backendProcess = process
            logger.info("Backend started (pid \(process.processIdentifier))")
        } catch {
            logger.error("Failed to start backend: \(error.localizedDescription)")
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        if let proc = backendProcess, proc.isRunning {
            proc.terminate()
            logger.info("Backend stopped")
        }
    }
}
