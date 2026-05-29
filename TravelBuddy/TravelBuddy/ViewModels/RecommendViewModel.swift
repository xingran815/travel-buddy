import Foundation
import MapKit
import SwiftUI

enum BrowseMode: String, CaseIterable {
    case byType = "By Place Type"
    case byCategory = "By Category"
}

@MainActor
class RecommendViewModel: ObservableObject {
    @Published var browseMode: BrowseMode = .byType
    @Published var region: String = ""
    @Published var selectedProfile: String = "balanced"
    @Published var topN: Int = 5
    @Published var profiles: [String] = []
    @Published var categories: [AppCategory] = []
    @Published var selectedCategories: Set<String> = []

    // By-type options
    @Published var selectedTypes: Set<String> = ["restaurant"]
    @Published var llmRerank = false
    @Published var llmSummarize = false
    @Published var llmAspects = false

    // By-category refinements (mirror CLI _ask_category_refinement)
    @Published var selectedAudience: String? = nil   // nil=any, "family", "adult"
    @Published var indoorOutdoor: String? = nil       // nil=any, "indoor", "outdoor"
    @Published var maxPrice: Int? = nil               // nil=any, 1/2/3
    @Published var vibe: String = ""

    // Category sets mirrored from app/ui/prompts.py
    let categoriesWithVibe: Set<String> = ["nightlife", "food"]
    let categoriesWithIndoorOutdoor: Set<String> = ["sights", "museums", "nature", "family", "nightlife"]

    // Conditional-display gates (mirror CLI rules)
    var autoFamily: Bool { selectedCategories.contains("family") }
    var showAudience: Bool { !autoFamily }
    var showIndoorOutdoor: Bool { !selectedCategories.isDisjoint(with: categoriesWithIndoorOutdoor) }
    var showBudget: Bool { selectedProfile != "budget" }
    var showVibe: Bool { !selectedCategories.isDisjoint(with: categoriesWithVibe) }
    var effectiveAudience: String? { autoFamily ? "family" : selectedAudience }

    // Results
    @Published var places: [Place] = []
    @Published var categoryResults: [String: [Place]] = [:]
    @Published var state: LoadState = .idle

    // Map camera position
    @Published var mapRegion: MapCameraPosition = .region(MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 41.0, longitude: 29.0),
        span: MKCoordinateSpan(latitudeDelta: 0.1, longitudeDelta: 0.1)
    ))

    let commonTypes = ["restaurant", "cafe", "bar", "museum", "park",
                       "shopping_mall", "tourist_attraction", "spa", "night_club"]

    func loadMeta() async {
        async let profs = try? APIClient.shared.profiles()
        async let cats  = try? APIClient.shared.categories()
        let (p, c) = await (profs, cats)
        profiles   = p ?? ["balanced", "foodie", "budget", "atmosphere"]
        categories = c ?? []
    }

    func search() async {
        guard !region.isEmpty else { return }
        state = .loading
        do {
            if browseMode == .byType {
                let req = RecommendRequest(
                    region: region,
                    place_types: Array(selectedTypes),
                    top_n: topN,
                    profile: selectedProfile,
                    llm_rerank: llmRerank,
                    llm_summarize: llmSummarize,
                    llm_aspects: llmAspects
                )
                let resp = try await APIClient.shared.recommend(req)
                places = resp.places ?? []
                updateMap(places)
            } else {
                let trimmedVibe = vibe.trimmingCharacters(in: .whitespaces)
                let req = CategoryRecommendRequest(
                    region: region,
                    category_ids: Array(selectedCategories),
                    top_n_per: topN,
                    max_price: showBudget ? maxPrice : nil,
                    profile: selectedProfile,
                    audience: effectiveAudience,
                    indoor_outdoor: showIndoorOutdoor ? indoorOutdoor : nil,
                    vibe: showVibe && !trimmedVibe.isEmpty ? trimmedVibe : nil,
                    estimate_missing_price: true,   // CLI hardcodes True for category mode
                    llm_rerank: llmRerank,
                    llm_summarize: llmSummarize,
                    llm_aspects: llmAspects
                )
                let resp = try await APIClient.shared.recommendCategories(req)
                categoryResults = resp.results ?? [:]
                updateMap(allCategoryPlaces)
            }
            state = .loaded
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    func like(_ place: Place) async {
        try? await APIClient.shared.recordFeedback(
            FeedbackRequest(place_id: place.place_id, action: "liked", rating: nil))
    }

    func markVisited(_ place: Place) async {
        try? await APIClient.shared.recordFeedback(
            FeedbackRequest(place_id: place.place_id, action: "visited", rating: nil))
    }

    /// Flattened category results in `categories` order (stable for pin coloring).
    var allCategoryPlaces: [Place] {
        categories.flatMap { categoryResults[$0.id] ?? [] }
    }

    private func updateMap(_ places: [Place]) {
        let coords = places.compactMap { p -> CLLocationCoordinate2D? in
            guard let lat = p.lat, let lng = p.lng else { return nil }
            return CLLocationCoordinate2D(latitude: lat, longitude: lng)
        }
        guard !coords.isEmpty else { return }
        let lats = coords.map(\.latitude)
        let lngs = coords.map(\.longitude)
        let center = CLLocationCoordinate2D(
            latitude: (lats.min()! + lats.max()!) / 2,
            longitude: (lngs.min()! + lngs.max()!) / 2
        )
        let span = MKCoordinateSpan(
            latitudeDelta: max(0.02, (lats.max()! - lats.min()!) * 1.4),
            longitudeDelta: max(0.02, (lngs.max()! - lngs.min()!) * 1.4)
        )
        mapRegion = .region(MKCoordinateRegion(center: center, span: span))
    }
}
