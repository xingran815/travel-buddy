import SwiftUI

struct RecommendView: View {
    @StateObject private var vm = RecommendViewModel()

    var body: some View {
        VStack(spacing: 0) {
            // Search bar
            HStack(spacing: 8) {
                TextField("Region (e.g. Kadiköy, Istanbul)", text: $vm.region)
                    .textFieldStyle(.roundedBorder)
                Picker("Profile", selection: $vm.selectedProfile) {
                    ForEach(vm.profiles, id: \.self) { Text($0.capitalized).tag($0) }
                }
                .frame(width: 130)
                Stepper("Top \(vm.topN)", value: $vm.topN, in: 3...20)
                    .fixedSize()
                Button {
                    Task { await vm.search() }
                } label: {
                    Label("Search", systemImage: "magnifyingglass")
                }
                .disabled(vm.region.isEmpty)
                .keyboardShortcut(.return, modifiers: [])
            }
            .padding()

            Picker("Mode", selection: $vm.browseMode) {
                ForEach(BrowseMode.allCases, id: \.self) { Text($0.rawValue).tag($0) }
            }
            .pickerStyle(.segmented)
            .padding(.horizontal)
            .padding(.bottom, 8)

            Divider()

            // Content
            ZStack {
                switch vm.state {
                case .loading:
                    LoadingView(message: "Searching…")
                case .error(let msg):
                    ErrorBannerView(message: msg) { Task { await vm.search() } }
                default:
                    if vm.browseMode == .byType {
                        PlaceTypeView(vm: vm)
                    } else {
                        CategoryBrowseView(vm: vm)
                    }
                }
            }
        }
        .navigationTitle("Recommendations")
        .task { await vm.loadMeta() }
    }
}
