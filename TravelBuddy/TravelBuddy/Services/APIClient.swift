import Foundation

enum APIError: LocalizedError {
    case badURL, httpError(Int), decodingError(Error), noData

    var errorDescription: String? {
        switch self {
        case .badURL:              return "Invalid URL"
        case .httpError(let c):   return "HTTP \(c)"
        case .decodingError(let e): return "Decode error: \(e.localizedDescription)"
        case .noData:             return "No data received"
        }
    }
}

struct APIClient {
    static let shared = APIClient()
    private let base = URL(string: BackendManager.baseURL)!
    private let session = URLSession.shared

    private func get<T: Decodable>(_ path: String) async throws -> T {
        let url = base.appendingPathComponent(path)
        let (data, resp) = try await session.data(from: url)
        if let http = resp as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw APIError.httpError(http.statusCode)
        }
        do { return try JSONDecoder().decode(T.self, from: data) }
        catch { throw APIError.decodingError(error) }
    }

    private func post<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        var req = URLRequest(url: base.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(body)
        let (data, resp) = try await session.data(for: req)
        if let http = resp as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw APIError.httpError(http.statusCode)
        }
        do { return try JSONDecoder().decode(T.self, from: data) }
        catch { throw APIError.decodingError(error) }
    }

    private func put<B: Encodable, T: Decodable>(_ path: String, body: B) async throws -> T {
        var req = URLRequest(url: base.appendingPathComponent(path))
        req.httpMethod = "PUT"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(body)
        let (data, resp) = try await session.data(for: req)
        if let http = resp as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            throw APIError.httpError(http.statusCode)
        }
        do { return try JSONDecoder().decode(T.self, from: data) }
        catch { throw APIError.decodingError(error) }
    }

    // MARK: - Health

    func health() async throws -> Bool {
        struct H: Decodable { let status: String }
        let h: H = try await get("/api/health")
        return h.status == "ok"
    }

    // MARK: - Profile

    func getProfile() async throws -> UserProfile {
        try await get("/api/profile")
    }

    func updateProfile(_ update: ProfileUpdate) async throws -> UserProfile {
        try await put("/api/profile", body: update)
    }

    func recordFeedback(_ feedback: FeedbackRequest) async throws {
        struct Ok: Decodable { let status: String }
        let _: Ok = try await post("/api/profile/feedback", body: feedback)
    }

    // MARK: - Recommend

    func recommend(_ req: RecommendRequest) async throws -> RecommendResponse {
        try await post("/api/recommend", body: req)
    }

    func recommendCategories(_ req: CategoryRecommendRequest) async throws -> RecommendResponse {
        try await post("/api/recommend/categories", body: req)
    }

    func categories() async throws -> [AppCategory] {
        try await get("/api/categories")
    }

    func profiles() async throws -> [String] {
        try await get("/api/profiles")
    }

    // MARK: - Planner

    func plan(destination: String, budget: Double, days: Int,
              preferences: String, lang: String) async throws -> String {
        struct PlanReq: Encodable {
            let destination: String; let budget: Double; let days: Int
            let preferences: String; let lang: String
        }
        struct PlanResp: Decodable { let itinerary: String }
        let resp: PlanResp = try await post("/api/plan", body: PlanReq(
            destination: destination, budget: budget, days: days,
            preferences: preferences, lang: lang))
        return resp.itinerary
    }

    // MARK: - Settings

    func getSettings() async throws -> AppSettings {
        try await get("/api/settings")
    }

    func updateSettings(_ update: SettingsUpdate) async throws -> AppSettings {
        try await put("/api/settings", body: update)
    }

    func cacheStats() async throws -> CacheStats {
        try await get("/api/cache/stats")
    }

    func clearCache(target: String) async throws {
        struct Ok: Decodable { let cleared: [String] }
        let _: Ok = try await post("/api/cache/clear",
                                   body: CacheClearRequest(target: target))
    }
}
