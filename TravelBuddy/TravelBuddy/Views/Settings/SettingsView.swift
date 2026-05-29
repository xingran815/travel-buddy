import SwiftUI

struct SettingsView: View {
    @StateObject private var vm = SettingsViewModel()

    var body: some View {
        Form {
            switch vm.state {
            case .loading:
                ProgressView("Loading settings…")
            case .error(let msg):
                ErrorBannerView(message: msg) { Task { await vm.load() } }
            default:
                llmSection
                mapsSection
                generalSection
                cacheSection
                saveSection
            }
        }
        .navigationTitle("Settings")
        .task { await vm.load() }
    }

    private var llmSection: some View {
        Section("LLM Provider") {
            Picker("Provider", selection: $vm.llmProvider) {
                ForEach(vm.providerOptions, id: \.self) { Text($0.capitalized).tag($0) }
            }
            LabeledContent("Model") {
                TextField("gpt-4o", text: $vm.llmModel)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 200)
            }
            LabeledContent("Base URL") {
                TextField("https://api.openai.com/v1", text: $vm.llmBaseURL)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 280)
            }
            LabeledContent("API Key") {
                SecureField("sk-…", text: $vm.llmApiKey)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 200)
            }
            if let s = vm.settings {
                Label(s.llm_api_key_set ? "Key configured" : "No key set",
                      systemImage: s.llm_api_key_set ? "checkmark.seal.fill" : "xmark.seal.fill")
                    .foregroundStyle(s.llm_api_key_set ? .green : .red)
                    .font(.caption)
            }
        }
    }

    private var mapsSection: some View {
        Section("Google Maps") {
            LabeledContent("API Key") {
                SecureField("AIza…", text: $vm.googleMapsKey)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 200)
            }
            if let s = vm.settings {
                Label(s.google_maps_api_key_set ? "Key configured" : "No key set",
                      systemImage: s.google_maps_api_key_set
                        ? "checkmark.seal.fill" : "xmark.seal.fill")
                    .foregroundStyle(s.google_maps_api_key_set ? .green : .red)
                    .font(.caption)
            }
        }
    }

    private var generalSection: some View {
        Section("General") {
            Picker("Language", selection: $vm.appLang) {
                ForEach(vm.langOptions, id: \.0) { code, label in
                    Text(label).tag(code)
                }
            }
        }
    }

    private var cacheSection: some View {
        Section("Cache") {
            if let stats = vm.cacheStats {
                LabeledContent("Places cache") {
                    Text("\(stats.places_entries) entries · \(stats.formattedSize)")
                        .foregroundStyle(.secondary)
                }
                LabeledContent("Pros/cons cache") {
                    Text("\(stats.pros_cons_entries) entries")
                        .foregroundStyle(.secondary)
                }
            }
            HStack(spacing: 12) {
                Button("Clear Places Cache") {
                    Task { await vm.clearCache(target: "places") }
                }
                .buttonStyle(.bordered)
                Button("Clear LLM Cache") {
                    Task { await vm.clearCache(target: "llm") }
                }
                .buttonStyle(.bordered)
                Button("Clear All", role: .destructive) {
                    Task { await vm.clearCache(target: "all") }
                }
                .buttonStyle(.bordered)
            }
        }
    }

    private var saveSection: some View {
        Section {
            HStack {
                Spacer()
                Button {
                    Task { await vm.save() }
                } label: {
                    Label(vm.saveSuccess ? "Saved!" : "Save Settings",
                          systemImage: vm.saveSuccess ? "checkmark" : "gearshape")
                }
                .buttonStyle(.borderedProminent)
                Spacer()
            }
        }
    }
}
