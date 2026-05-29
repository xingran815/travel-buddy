import SwiftUI

struct HistoryView: View {
    @StateObject private var vm = HistoryViewModel()

    var body: some View {
        VStack(spacing: 0) {
            Picker("Filter", selection: $vm.filter) {
                ForEach(HistoryFilter.allCases, id: \.self) { f in
                    Text(f.rawValue).tag(f)
                }
            }
            .pickerStyle(.segmented)
            .padding()

            Divider()

            switch vm.state {
            case .loading:
                LoadingView()
            case .error(let msg):
                ErrorBannerView(message: msg) { Task { await vm.load() } }
            default:
                if vm.filtered.isEmpty {
                    VStack(spacing: 12) {
                        Image(systemName: "clock.badge.xmark")
                            .font(.system(size: 48))
                            .foregroundStyle(.secondary)
                        Text("No history yet")
                            .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List(vm.filtered) { event in
                        HistoryRowView(event: event)
                    }
                    .listStyle(.inset)
                }
            }
        }
        .navigationTitle("History")
        .task { await vm.load() }
    }
}
