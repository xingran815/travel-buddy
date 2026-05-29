import SwiftUI

@main
struct TravelBuddyApp: App {
    @StateObject private var backend = BackendManager.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(backend)
                .frame(minWidth: 900, minHeight: 600)
        }
        .windowStyle(.automatic)
        .defaultSize(width: 1100, height: 720)
        .commands {
            CommandGroup(after: .appInfo) {
                Button("Restart Backend") {
                    Task { @MainActor in
                        backend.stopServer()
                        backend.startServer()
                    }
                }
                .keyboardShortcut("r", modifiers: [.command, .shift])
            }
        }
    }

    init() {
        Task { @MainActor in
            BackendManager.shared.startServer()
        }
    }
}
