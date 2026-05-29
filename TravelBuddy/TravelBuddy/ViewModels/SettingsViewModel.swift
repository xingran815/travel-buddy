import Foundation

@MainActor
class SettingsViewModel: ObservableObject {
    @Published var settings: AppSettings?
    @Published var cacheStats: CacheStats?
    @Published var state: LoadState = .idle
    @Published var saveSuccess = false

    // Edit fields
    @Published var llmProvider: String = "openai"
    @Published var llmModel: String = "gpt-4o"
    @Published var llmBaseURL: String = "https://api.openai.com/v1"
    @Published var llmApiKey: String = ""
    @Published var googleMapsKey: String = ""
    @Published var appLang: String = "en"

    let providerOptions = ["openai", "anthropic", "local"]
    let langOptions = [("en", "English"), ("tr", "Turkish"), ("de", "German"),
                       ("fr", "French"), ("es", "Spanish")]

    func load() async {
        state = .loading
        async let s = try? APIClient.shared.getSettings()
        async let c = try? APIClient.shared.cacheStats()
        let (settings, stats) = await (s, c)
        self.settings = settings
        self.cacheStats = stats
        if let s = settings {
            llmProvider = s.llm_provider
            llmModel    = s.llm_model
            llmBaseURL  = s.llm_base_url
            appLang     = s.app_lang
        }
        state = .loaded
    }

    func save() async {
        state = .loading
        let update = SettingsUpdate(
            llm_provider:      llmProvider.isEmpty ? nil : llmProvider,
            llm_api_key:       llmApiKey.isEmpty   ? nil : llmApiKey,
            llm_model:         llmModel.isEmpty     ? nil : llmModel,
            llm_base_url:      llmBaseURL.isEmpty   ? nil : llmBaseURL,
            google_maps_api_key: googleMapsKey.isEmpty ? nil : googleMapsKey,
            app_lang:          appLang.isEmpty      ? nil : appLang
        )
        do {
            settings = try await APIClient.shared.updateSettings(update)
            saveSuccess = true
            state = .loaded
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    func clearCache(target: String) async {
        try? await APIClient.shared.clearCache(target: target)
        cacheStats = try? await APIClient.shared.cacheStats()
    }
}
