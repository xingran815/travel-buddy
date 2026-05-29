import SwiftUI
import MapKit

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

                if !vm.selectedCategories.isEmpty {
                    refinementSection
                        .padding(.horizontal)
                }

                if vm.categoryResults.isEmpty {
                    emptyState
                } else {
                    Divider()
                    resultsMap
                        .frame(height: 280)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .padding(.horizontal)
                    ForEach(vm.categories.filter { vm.categoryResults[$0.id] != nil }) { cat in
                        if let places = vm.categoryResults[cat.id], !places.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                Label(cat.displayName, systemImage: cat.sfSymbol)
                                    .font(.title3.bold())
                                    .foregroundStyle(cat.color)
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

    @ViewBuilder
    private var refinementSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Divider()
            Text("Refine")
                .font(.headline)

            if vm.showAudience {
                Picker("Audience", selection: $vm.selectedAudience) {
                    Text("Any").tag(String?.none)
                    Text("Family").tag(String?.some("family"))
                    Text("Adult").tag(String?.some("adult"))
                }
                .pickerStyle(.segmented)
            } else if vm.autoFamily {
                Label("Audience: Family", systemImage: "figure.2.and.child.holdinghands")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if vm.showIndoorOutdoor {
                Picker("Setting", selection: $vm.indoorOutdoor) {
                    Text("Any").tag(String?.none)
                    Text("Indoor").tag(String?.some("indoor"))
                    Text("Outdoor").tag(String?.some("outdoor"))
                }
                .pickerStyle(.segmented)
            }

            if vm.showBudget {
                Picker("Budget", selection: $vm.maxPrice) {
                    Text("Any").tag(Int?.none)
                    Text("$").tag(Int?.some(1))
                    Text("$$").tag(Int?.some(2))
                    Text("$$$").tag(Int?.some(3))
                }
                .pickerStyle(.segmented)
            }

            if vm.showVibe {
                TextField("Vibe (e.g. cozy, lively)", text: $vm.vibe)
                    .textFieldStyle(.roundedBorder)
            }

            HStack(spacing: 16) {
                Toggle("Rerank", isOn: $vm.llmRerank)
                Toggle("Summarize", isOn: $vm.llmSummarize)
                Toggle("Aspects", isOn: $vm.llmAspects)
            }
            .font(.caption)
            .toggleStyle(.checkbox)
        }
    }

    private var pins: [CategoryPin] {
        vm.categories.flatMap { cat -> [CategoryPin] in
            (vm.categoryResults[cat.id] ?? []).compactMap { place in
                guard let lat = place.lat, let lng = place.lng else { return nil }
                return CategoryPin(
                    id: place.place_id,
                    coordinate: CLLocationCoordinate2D(latitude: lat, longitude: lng),
                    color: cat.color,
                    symbol: cat.sfSymbol,
                    name: place.name
                )
            }
        }
    }

    private var resultsMap: some View {
        Map(position: $vm.mapRegion) {
            ForEach(pins) { pin in
                Annotation(pin.name, coordinate: pin.coordinate) {
                    Image(systemName: pin.symbol)
                        .font(.system(size: 11, weight: .bold))
                        .foregroundStyle(.white)
                        .padding(6)
                        .background(pin.color, in: Circle())
                        .overlay(Circle().stroke(.white, lineWidth: 1.5))
                }
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Image(systemName: "mappin.slash")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)
            Text("No results yet")
                .foregroundStyle(.secondary)
            Text("Pick categories above and tap Search")
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 40)
    }
}

private struct CategoryPin: Identifiable {
    let id: String
    let coordinate: CLLocationCoordinate2D
    let color: Color
    let symbol: String
    let name: String
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
                    .foregroundStyle(isSelected ? .white : category.color)
                Text(category.displayName)
                    .font(.caption)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(isSelected ? .white : .primary)
            }
            .frame(maxWidth: .infinity, minHeight: 80)
            .background(isSelected ? category.color : category.color.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
    }
}
