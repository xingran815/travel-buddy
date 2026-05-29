import Foundation

enum LoadState {
    case idle, loading, loaded, error(String)
}

@MainActor
class HomeViewModel: ObservableObject {
    @Published var profile: UserProfile?
    @Published var state: LoadState = .idle

    var totalLiked: Int   { profile?.history.filter { $0.action == "liked" }.count ?? 0 }
    var totalVisited: Int { profile?.history.filter { $0.action == "visited" }.count ?? 0 }
    var recentEvents: [HistoryEvent] {
        (profile?.history ?? [])
            .sorted { $0.ts > $1.ts }
            .prefix(10)
            .map { $0 }
    }

    func load() async {
        state = .loading
        do {
            profile = try await APIClient.shared.getProfile()
            state = .loaded
        } catch {
            state = .error(error.localizedDescription)
        }
    }
}
