import XCTest
@testable import TravelBuddyKit

final class PlaceDecodingTests: XCTestCase {

    func test_decodes_all_ten_score_breakdown_keys() throws {
        let json = """
        {
          "place_id": "p1",
          "name": "Çiya Sofrası",
          "score": 4.52,
          "score_breakdown": {
            "quality":   1.35,
            "volume":    0.60,
            "distance":  0.55,
            "cost":      0.50,
            "recency":   0.20,
            "sentiment": 0.90,
            "audience":  0.30,
            "cuisine":   1.10,
            "aspects":   0.15,
            "history":   0.05
          }
        }
        """.data(using: .utf8)!

        let place = try JSONDecoder().decode(Place.self, from: json)
        let b = try XCTUnwrap(place.score_breakdown)

        XCTAssertEqual(b.quality,   1.35)
        XCTAssertEqual(b.volume,    0.60)
        XCTAssertEqual(b.distance,  0.55)
        XCTAssertEqual(b.cost,      0.50)
        XCTAssertEqual(b.recency,   0.20)
        XCTAssertEqual(b.sentiment, 0.90)
        XCTAssertEqual(b.audience,  0.30)
        XCTAssertEqual(b.cuisine,   1.10)
        XCTAssertEqual(b.aspects,   0.15)
        XCTAssertEqual(b.history,   0.05)
    }

    func test_decodes_pros_cons_and_llm_rationale() throws {
        let json = """
        {
          "place_id": "p2",
          "name": "Borsam",
          "pros": ["Famous pide", "Affordable"],
          "cons": ["Cash only"],
          "llm_rationale": "Best stone-oven pide nearby; matches a budget profile."
        }
        """.data(using: .utf8)!

        let place = try JSONDecoder().decode(Place.self, from: json)

        XCTAssertEqual(place.pros, ["Famous pide", "Affordable"])
        XCTAssertEqual(place.cons, ["Cash only"])
        XCTAssertEqual(place.llm_rationale, "Best stone-oven pide nearby; matches a budget profile.")
    }

    func test_decodes_when_llm_fields_absent() throws {
        let json = """
        {"place_id": "p3", "name": "Baylan"}
        """.data(using: .utf8)!

        let place = try JSONDecoder().decode(Place.self, from: json)

        XCTAssertNil(place.pros)
        XCTAssertNil(place.cons)
        XCTAssertNil(place.llm_rationale)
        XCTAssertNil(place.score_breakdown)
    }

    func test_decodes_recommend_response_with_places() throws {
        let json = """
        {
          "places": [
            {"place_id": "p1", "name": "A"},
            {"place_id": "p2", "name": "B"}
          ],
          "region": "Kadiköy",
          "profile": "balanced"
        }
        """.data(using: .utf8)!

        let resp = try JSONDecoder().decode(RecommendResponse.self, from: json)

        XCTAssertEqual(resp.region, "Kadiköy")
        XCTAssertEqual(resp.profile, "balanced")
        XCTAssertEqual(resp.places?.count, 2)
        XCTAssertEqual(resp.places?.first?.name, "A")
    }
}
