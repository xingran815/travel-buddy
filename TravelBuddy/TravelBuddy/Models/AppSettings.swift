import Foundation

struct AppSettings: Codable {
    var llm_provider: String
    var llm_model: String
    var llm_base_url: String
    var llm_api_key_set: Bool
    var google_maps_api_key_set: Bool
    var app_lang: String
}

struct SettingsUpdate: Codable {
    var llm_provider: String?
    var llm_api_key: String?
    var llm_model: String?
    var llm_base_url: String?
    var google_maps_api_key: String?
    var app_lang: String?
}

struct CacheStats: Codable {
    var places_size_bytes: Int
    var places_entries: Int
    var pros_cons_entries: Int
    var aspects_entries: Int

    var formattedSize: String {
        let kb = Double(places_size_bytes) / 1024
        if kb < 1024 { return String(format: "%.0f KB", kb) }
        return String(format: "%.1f MB", kb / 1024)
    }
}

struct CacheClearRequest: Codable {
    let target: String
}
