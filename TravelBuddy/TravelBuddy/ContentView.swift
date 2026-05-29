import SwiftUI

struct ContentView: View {
    @EnvironmentObject var backend: BackendManager
    @State private var selection: NavItem? = .home

    var body: some View {
        switch backend.status {
        case .idle:
            startingView("Waiting for server…")
        case .starting:
            startingView("Starting backend server…")
        case .failed(let msg):
            VStack(spacing: 16) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 56))
                    .foregroundStyle(.red)
                Text("Server failed to start")
                    .font(.title2.bold())
                Text(msg)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Button("Retry") { backend.startServer() }
                    .buttonStyle(.borderedProminent)
            }
            .padding(40)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        case .running:
            NavigationSplitView {
                SidebarView(selection: $selection)
            } detail: {
                NavigationStack {
                    switch selection {
                    case .home, .none: HomeView()
                    case .summarize:   SummarizeView()
                    case .recommend:   RecommendView()
                    case .planner:     PlannerView()
                    case .profile:     ProfileView()
                    case .history:     HistoryView()
                    case .settings:    SettingsView()
                    }
                }
            }
            .navigationSplitViewStyle(.balanced)
        }
    }

    private func startingView(_ msg: String) -> some View {
        VStack(spacing: 16) {
            ProgressView()
                .controlSize(.large)
            Text(msg)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
