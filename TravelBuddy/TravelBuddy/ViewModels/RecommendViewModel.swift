import Foundation
import MapKit

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

    // Results
    @Published var places: [Place] = []
    @Published var categoryResults: [String: [Place]] = [:]
    @Published var state: LoadState = .idle

    // Map region
    @Published var mapRegion = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 41.0, longitude: 29.0),
        span: MKCoordinateSpan(latitudeDelta: 0.1, longitudeDelta: 0.1)
    )

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
                updateMap()
            } else {
                let req = CategoryRecommendRequest(
                    region: region,
                    category_ids: Array(selectedCategories),
                    top_n_per: topN,
                    profile: selectedProfile,
                    llm_rerank: llmRerank,
                    llm_summarize: llmSummarize,
                    llm_aspects: llmAspects
                )
                let resp = try await APIClient.shared.recommendCategories(req)
                categoryResults = resp.results ?? [:]
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

    private func updateMap() {
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
        mapRegion = MKCoordinateRegion(center: center, span: span)
    }
}
