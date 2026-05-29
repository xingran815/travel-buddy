import SwiftUI
import MapKit

struct PlaceTypeView: View {
    @ObservedObject var vm: RecommendViewModel

    var body: some View {
        VStack(spacing: 0) {
            // Type chip filters
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(vm.commonTypes, id: \.self) { type in
                        ChipView(
                            label: type.replacingOccurrences(of: "_", with: " ").capitalized,
                            isSelected: vm.selectedTypes.contains(type)
                        ) {
                            if vm.selectedTypes.contains(type) {
                                vm.selectedTypes.remove(type)
                            } else {
                                vm.selectedTypes.insert(type)
                            }
                        }
                    }
                }
                .padding(.horizontal)
                .padding(.vertical, 8)
            }

            // AI toggles row
            HStack(spacing: 16) {
                Toggle("Rerank", isOn: $vm.llmRerank)
                Toggle("Summarize", isOn: $vm.llmSummarize)
                Toggle("Aspects", isOn: $vm.llmAspects)
            }
            .font(.caption)
            .toggleStyle(.checkbox)
            .padding(.horizontal)
            .padding(.bottom, 6)

            Divider()

            if vm.places.isEmpty {
                emptyState
            } else {
                // Map + results split
                VSplitView {
                    Map(coordinateRegion: $vm.mapRegion, annotationItems: vm.places) { place in
                        MapAnnotation(coordinate: CLLocationCoordinate2D(
                            latitude: place.lat ?? 0, longitude: place.lng ?? 0)) {
                            if place.lat != nil {
                                VStack(spacing: 2) {
                                    Image(systemName: "mappin.circle.fill")
                                        .foregroundStyle(.red)
                                        .font(.title2)
                                    Text(place.name)
                                        .font(.system(size: 9))
                                        .fixedSize()
                                }
                            }
                        }
                    }
                    .frame(minHeight: 200)

                    ScrollView {
                        LazyVStack(spacing: 10) {
                            ForEach(vm.places) { place in
                                PlaceCardView(place: place,
                                    onLike:  { Task { await vm.like(place)  } },
                                    onVisit: { Task { await vm.markVisited(place) } })
                            }
                        }
                        .padding()
                    }
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
            Text("Enter a region above and tap Search")
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
