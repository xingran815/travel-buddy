import SwiftUI

struct CategoryBrowseView: View {
    @ObservedObject var vm: RecommendViewModel

    private let columns = Array(repeating: GridItem(.flexible(), spacing: 12), count: 3)

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                // Category grid
                Text("Select categories")
                    .font(.headline)
                    .padding(.horizontal)

                LazyVGrid(columns: columns, spacing: 12) {
                    ForEach(vm.categories) { cat in
                        CategoryTileView(
                            category: cat,
                            isSelected: vm.selectedCategories.contains(cat.id)
                        ) {
                            if vm.selectedCategories.contains(cat.id) {
                                vm.selectedCategories.remove(cat.id)
                            } else {
                                vm.selectedCategories.insert(cat.id)
                            }
                        }
                    }
                }
                .padding(.horizontal)

                if !vm.categoryResults.isEmpty {
                    Divider()
                    ForEach(vm.categories.filter { vm.categoryResults[$0.id] != nil }) { cat in
                        if let places = vm.categoryResults[cat.id], !places.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                Label(cat.displayName, systemImage: cat.sfSymbol)
                                    .font(.title3.bold())
                                    .padding(.horizontal)
                                ForEach(places) { place in
                                    PlaceCardView(place: place,
                                        onLike:  { Task { await vm.like(place)  } },
                                        onVisit: { Task { await vm.markVisited(place) } })
                                    .padding(.horizontal)
                                }
                            }
                        }
                    }
                }
            }
            .padding(.vertical)
        }
    }
}

private struct CategoryTileView: View {
    let category: AppCategory
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: category.sfSymbol)
                    .font(.title)
                    .foregroundStyle(isSelected ? .white : accentColor)
                Text(category.displayName)
                    .font(.caption)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(isSelected ? .white : .primary)
            }
            .frame(maxWidth: .infinity, minHeight: 80)
            .background(isSelected ? accentColor : accentColor.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
    }

    private var accentColor: Color {
        switch category.accentColor {
        case "orange": return .orange
        case "blue":   return .blue
        case "purple": return .purple
        case "green":  return .green
        case "pink":   return .pink
        case "indigo": return .indigo
        case "yellow": return .yellow
        case "teal":   return .teal
        case "mint":   return .mint
        default:       return .accentColor
        }
    }
}
