import Foundation

enum HistoryFilter: String, CaseIterable {
    case all = "All"
    case liked = "Liked"
    case visited = "Visited"
    case disliked = "Disliked"
}

@MainActor
class HistoryViewModel: ObservableObject {
    @Published var events: [HistoryEvent] = []
    @Published var filter: HistoryFilter = .all
    @Published var state: LoadState = .idle

    var filtered: [HistoryEvent] {
        let sorted = events.sorted { $0.ts > $1.ts }
        switch filter {
        case .all:      return sorted
        case .liked:    return sorted.filter { $0.action == "liked" }
        case .visited:  return sorted.filter { $0.action == "visited" }
        case .disliked: return sorted.filter { $0.action == "disliked" }
        }
    }

    func load() async {
        state = .loading
        do {
            let profile = try await APIClient.shared.getProfile()
            events = profile.history
            state = .loaded
        } catch {
            state = .error(error.localizedDescription)
        }
    }
}
