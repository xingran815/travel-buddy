import Foundation

struct UserProfile: Codable {
    var cuisine_prefs: [String]
    var default_budget: Double?
    var default_language: String
    var disliked_keywords: [String]
    var history: [HistoryEvent]
}

struct HistoryEvent: Codable, Identifiable {
    var id: String { "\(place_id)_\(action)_\(ts)" }
    let place_id: String
    let action: String
    let ts: Double
    let rating: Int?
}

struct FeedbackRequest: Codable {
    let place_id: String
    let action: String
    let rating: Int?
}

struct ProfileUpdate: Codable {
    var cuisine_prefs: [String]?
    var default_budget: Double?
    var default_language: String?
    var disliked_keywords: [String]?
}
