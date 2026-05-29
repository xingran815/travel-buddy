import SwiftUI

struct ProfileView: View {
    @StateObject private var vm = ProfileViewModel()
    @State private var saved = false

    var body: some View {
        Form {
            switch vm.state {
            case .loading:
                ProgressView("Loading profile…")
            case .error(let msg):
                ErrorBannerView(message: msg) { Task { await vm.load() } }
            default:
                Section("Cuisine Preferences") {
                    cuisineChips
                }
                Section("Defaults") {
                    HStack {
                        Text("Language")
                        Spacer()
                        Picker("Language", selection: $vm.defaultLanguage) {
                            ForEach(vm.languageOptions, id: \.0) { code, label in
                                Text(label).tag(code)
                            }
                        }
                        .frame(width: 140)
                    }
                    HStack {
                        Text("Budget (USD)")
                        Spacer()
                        TextField("500", text: $vm.defaultBudget)
                            .textFieldStyle(.roundedBorder)
                            .frame(width: 100)
                    }
                    HStack {
                        Text("Disliked keywords")
                        Spacer()
                        TextField("e.g. smoky, loud", text: $vm.dislikedKeywords)
                            .textFieldStyle(.roundedBorder)
                            .frame(width: 200)
                    }
                }
                Section {
                    HStack {
                        Spacer()
                        Button {
                            Task {
                                await vm.save()
                                saved = true
                                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                                    saved = false
                                }
                            }
                        } label: {
                            Label(saved ? "Saved!" : "Save Profile",
                                  systemImage: saved ? "checkmark" : "square.and.arrow.down")
                        }
                        .buttonStyle(.borderedProminent)
                        Spacer()
                    }
                }
            }
        }
        .navigationTitle("Profile")
        .task { await vm.load() }
    }

    private var cuisineChips: some View {
        LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 4), spacing: 8) {
            ForEach(vm.cuisineOptions, id: \.self) { cuisine in
                ChipView(
                    label: cuisine,
                    isSelected: vm.cuisinePrefs.contains(cuisine)
                ) {
                    if vm.cuisinePrefs.contains(cuisine) {
                        vm.cuisinePrefs.remove(cuisine)
                    } else {
                        vm.cuisinePrefs.insert(cuisine)
                    }
                }
            }
        }
        .padding(.vertical, 4)
    }
}
