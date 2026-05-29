import SwiftUI

enum NavItem: String, CaseIterable, Identifiable {
    case home         = "Home"
    case summarize    = "Video Summary"
    case recommend    = "Recommendations"
    case planner      = "Trip Planner"
    case profile      = "Profile"
    case history      = "History"
    case settings     = "Settings"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .home:      return "house.fill"
        case .summarize: return "play.rectangle.fill"
        case .recommend: return "mappin.and.ellipse"
        case .planner:   return "map.fill"
        case .profile:   return "person.fill"
        case .history:   return "clock.fill"
        case .settings:  return "gearshape.fill"
        }
    }
}

struct SidebarView: View {
    @Binding var selection: NavItem?

    var body: some View {
        List(NavItem.allCases, selection: $selection) { item in
            Label(item.rawValue, systemImage: item.icon)
                .tag(item)
        }
        .listStyle(.sidebar)
        .navigationTitle("TravelBuddy")
    }
}
