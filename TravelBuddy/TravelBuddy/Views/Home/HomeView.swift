import SwiftUI

struct HomeView: View {
    @StateObject private var vm = HomeViewModel()

    var body: some View {
        ScrollView {
            switch vm.state {
            case .idle, .loading:
                LoadingView(message: "Loading…")
                    .frame(height: 300)
            case .error(let msg):
                ErrorBannerView(message: msg) { Task { await vm.load() } }
            case .loaded:
                VStack(alignment: .leading, spacing: 24) {
                    statsGrid
                    recentActivity
                }
                .padding()
            }
        }
        .navigationTitle("TravelBuddy")
        .task { await vm.load() }
    }

    private var statsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            StatCard(title: "Places Liked",    value: "\(vm.totalLiked)",
                     icon: "hand.thumbsup.fill",   color: .green)
            StatCard(title: "Places Visited",  value: "\(vm.totalVisited)",
                     icon: "checkmark.seal.fill",  color: .blue)
            StatCard(title: "History Events",
                     value: "\(vm.profile?.history.count ?? 0)",
                     icon: "clock.fill", color: .orange)
            StatCard(title: "Profile",
                     value: vm.profile?.default_language.uppercased() ?? "—",
                     icon: "person.fill", color: .purple)
        }
    }

    private var recentActivity: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Recent Activity")
                .font(.headline)
            if vm.recentEvents.isEmpty {
                Text("No activity yet — start exploring!")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(vm.recentEvents) { event in
                    HStack {
                        Image(systemName: iconFor(action: event.action))
                            .foregroundStyle(colorFor(action: event.action))
                        Text(event.place_id)
                            .font(.caption)
                            .lineLimit(1)
                        Spacer()
                        Text(Date(timeIntervalSince1970: event.ts),
                             style: .relative)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
    }

    private func iconFor(action: String) -> String {
        switch action {
        case "liked":    return "hand.thumbsup.fill"
        case "disliked": return "hand.thumbsdown.fill"
        case "visited":  return "checkmark.seal.fill"
        default:         return "clock"
        }
    }

    private func colorFor(action: String) -> Color {
        switch action {
        case "liked":    return .green
        case "disliked": return .red
        case "visited":  return .blue
        default:         return .secondary
        }
    }
}

private struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundStyle(color)
                .frame(width: 36)
            VStack(alignment: .leading, spacing: 2) {
                Text(value).font(.title2.bold())
                Text(title).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.quinary)
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}
