import Foundation

@MainActor
class ProfileViewModel: ObservableObject {
    @Published var profile: UserProfile?
    @Published var state: LoadState = .idle

    // Editable fields
    @Published var cuisinePrefs: Set<String> = []
    @Published var defaultBudget: String = ""
    @Published var defaultLanguage: String = "en"
    @Published var dislikedKeywords: String = ""

    let cuisineOptions = ["Turkish", "Italian", "Seafood", "Asian", "Mexican",
                          "Mediterranean", "American", "French", "Indian", "Japanese"]
    let languageOptions = [("en", "English"), ("tr", "Turkish"), ("de", "German"),
                           ("fr", "French"), ("es", "Spanish")]

    func load() async {
        state = .loading
        do {
            let p = try await APIClient.shared.getProfile()
            profile = p
            cuisinePrefs = Set(p.cuisine_prefs)
            defaultBudget = p.default_budget.map { String(format: "%.0f", $0) } ?? ""
            defaultLanguage = p.default_language
            dislikedKeywords = p.disliked_keywords.joined(separator: ", ")
            state = .loaded
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    func save() async {
        state = .loading
        let update = ProfileUpdate(
            cuisine_prefs: Array(cuisinePrefs),
            default_budget: Double(defaultBudget),
            default_language: defaultLanguage,
            disliked_keywords: dislikedKeywords.split(separator: ",")
                .map { $0.trimmingCharacters(in: .whitespaces) }
                .filter { !$0.isEmpty }
        )
        do {
            profile = try await APIClient.shared.updateProfile(update)
            state = .loaded
        } catch {
            state = .error(error.localizedDescription)
        }
    }
}
