import Foundation

enum ServerStatus {
    case idle, starting, running, failed(String)
}

@MainActor
class BackendManager: ObservableObject {
    static let shared = BackendManager()

    @Published var status: ServerStatus = .idle

    private var process: Process?
    private var healthTask: Task<Void, Never>?
    private var monitorTask: Task<Void, Never>?

    nonisolated static let port = 8745
    nonisolated static let baseURL = "http://127.0.0.1:\(port)"
    nonisolated private static let healthURL = URL(string: "\(baseURL)/api/health")!

    nonisolated private static let projectRoot: URL = {
        let fm = FileManager.default
        // 0. Bundled backend inside the .app (distribution builds)
        if let resourceURL = Bundle.main.resourceURL {
            let bundled = resourceURL.appendingPathComponent("backend")
            if fm.fileExists(atPath: bundled.appendingPathComponent("venv/bin/python").path) {
                return bundled
            }
        }
        // 1. UserDefaults override wins
        if let stored = UserDefaults.standard.string(forKey: "projectRoot"),
           fm.fileExists(atPath: stored) {
            return URL(fileURLWithPath: stored)
        }
        // 2. Embedded path via Info.plist key (for shipping builds)
        if let plistPath = Bundle.main.object(forInfoDictionaryKey: "TBProjectRoot") as? String,
           fm.fileExists(atPath: plistPath) {
            return URL(fileURLWithPath: plistPath)
        }
        // 3. Well-known dev locations relative to the user's home dir
        let home = fm.homeDirectoryForCurrentUser
        let candidates = [
            home.appendingPathComponent("Documents/Projects/youtube_summary"),
            home.appendingPathComponent("Projects/youtube_summary"),
            home.appendingPathComponent("youtube_summary"),
        ]
        for c in candidates where fm.fileExists(atPath: c.appendingPathComponent("venv/bin/python").path) {
            return c
        }
        // 4. Last resort: the first candidate even if it doesn't exist (caller surfaces an error)
        return candidates[0]
    }()

    func startServer() {
        guard case .idle = status else { return }
        status = .starting

        let root = Self.projectRoot
        let python = root.appendingPathComponent("venv/bin/python").path
        guard FileManager.default.fileExists(atPath: python) else {
            status = .failed("Python not found at \(python)")
            return
        }

        let p = Process()
        p.executableURL = URL(fileURLWithPath: python)
        p.arguments = ["-m", "uvicorn", "app.server.main:app",
                       "--host", "127.0.0.1", "--port", "\(Self.port)"]
        p.currentDirectoryURL = root
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        do {
            try p.run()
        } catch {
            status = .failed("Launch failed: \(error.localizedDescription)")
            return
        }
        process = p

        healthTask = Task {
            for attempt in 0..<60 {
                try? await Task.sleep(nanoseconds: 500_000_000)
                if await isHealthy() {
                    self.status = .running
                    self.startMonitor()
                    return
                }
                if attempt == 59 {
                    self.status = .failed("Server did not respond after 30 s")
                }
            }
        }
    }

    func stopServer() {
        healthTask?.cancel()
        monitorTask?.cancel()
        process?.terminate()
        process?.waitUntilExit()
        process = nil
        status = .idle
    }

    private func startMonitor() {
        monitorTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 10_000_000_000)
                if !(await isHealthy()) {
                    self.status = .failed("Server went away — restarting…")
                    self.process?.terminate()
                    self.process = nil
                    self.status = .idle
                    self.startServer()
                    return
                }
            }
        }
    }

    private func isHealthy() async -> Bool {
        guard let (_, resp) = try? await URLSession.shared.data(from: Self.healthURL),
              let http = resp as? HTTPURLResponse else { return false }
        return http.statusCode == 200
    }
}
