import Foundation

// MARK: - Place

struct Place: Codable, Identifiable, Hashable {
    var id: String { place_id }
    let place_id: String
    let name: String
    let address: String?
    let rating: Double?
    let user_ratings_total: Int?
    let price_level: Int?
    let score: Double?
    let types: [String]?
    let lat: Double?
    let lng: Double?
    let website: String?
    let phone: String?
    let opening_hours: OpeningHours?
    let photos: [PhotoRef]?
    let summary: String?
    let pros: [String]?
    let cons: [String]?
    let aspects: [String: String]?
    let llm_rationale: String?
    let score_breakdown: ScoreBreakdown?
    let estimated_price: Int?

    func hash(into hasher: inout Hasher) { hasher.combine(place_id) }
    static func == (lhs: Place, rhs: Place) -> Bool { lhs.place_id == rhs.place_id }
}

struct OpeningHours: Codable {
    let open_now: Bool?
    let weekday_text: [String]?
}

struct PhotoRef: Codable {
    let photo_reference: String?
}

struct ScoreBreakdown: Codable, Equatable {
    let quality: Double?
    let volume: Double?
    let distance: Double?
    let cost: Double?
    let recency: Double?
    let sentiment: Double?
    let audience: Double?
    let cuisine: Double?
    let aspects: Double?
    let history: Double?
}

// MARK: - Recommend Request / Response

struct RecommendRequest: Codable {
    var region: String
    var place_type: String = "restaurant"
    var place_types: [String]? = nil
    var top_n: Int = 5
    var max_pages: Int = 1
    var min_price: Int? = nil
    var max_price: Int? = nil
    var budget: Double? = nil
    var include_details: Bool = true
    var profile: String = "balanced"
    var cuisine: String? = nil
    var audience: String? = nil
    var people: Int = 2
    var query: String? = nil
    var aspects: [String]? = nil
    var indoor_outdoor: String? = nil
    var vibe: String? = nil
    var estimate_missing_price: Bool = false
    var llm_parse: Bool = false
    var llm_rerank: Bool = false
    var llm_summarize: Bool = false
    var llm_aspects: Bool = false
    var lang: String = "en"
}

struct CategoryRecommendRequest: Codable {
    var region: String
    var category_ids: [String]
    var top_n_per: Int = 5
    var max_price: Int? = nil
    var budget: Double? = nil
    var profile: String = "balanced"
    var cuisine: String? = nil
    var audience: String? = nil
    var people: Int = 2
    var indoor_outdoor: String? = nil
    var vibe: String? = nil
    var estimate_missing_price: Bool = false
    var llm_rerank: Bool = false
    var llm_summarize: Bool = false
    var llm_aspects: Bool = false
    var lang: String = "en"
}

struct RecommendResponse: Codable {
    let places: [Place]?
    let results: [String: [Place]]?
    let region: String
    let profile: String?
}
