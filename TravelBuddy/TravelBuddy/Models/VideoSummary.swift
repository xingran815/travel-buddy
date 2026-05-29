import Foundation

struct SummarizeEvent: Codable {
    let step: String
    let progress: Double
    let data: SummarizeEventData?
}

struct SummarizeEventData: Codable {
    let title: String?
    let video_id: String?
    let language: String?
    let source_language: String?
    let summary: String?
    let translation: String?
    let message: String?
    let skipped: Bool?
}

struct VideoResult: Identifiable {
    let id = UUID()
    let title: String
    let videoId: String
    let summary: String
    let translation: String?
    let sourceLanguage: String
}
