import XCTest
@testable import TravelBuddyKit

final class BreakdownFactorsTests: XCTestCase {

    private func breakdown(
        quality: Double? = nil, volume: Double? = nil, distance: Double? = nil,
        cost: Double? = nil, recency: Double? = nil, sentiment: Double? = nil,
        audience: Double? = nil, cuisine: Double? = nil, aspects: Double? = nil,
        history: Double? = nil
    ) -> ScoreBreakdown {
        ScoreBreakdown(
            quality: quality, volume: volume, distance: distance, cost: cost,
            recency: recency, sentiment: sentiment, audience: audience,
            cuisine: cuisine, aspects: aspects, history: history
        )
    }

    func test_empty_breakdown_returns_no_factors() {
        let result = breakdownFactors(from: breakdown())
        XCTAssertTrue(result.isEmpty)
    }

    func test_zero_values_are_filtered_out() {
        let result = breakdownFactors(from: breakdown(
            quality: 1.2,
            volume: 0,
            distance: 0.0,
            cost: 0.5
        ))
        XCTAssertEqual(result.map { $0.id }, ["Quality", "Cost"])
    }

    func test_negative_values_are_filtered_out() {
        let result = breakdownFactors(from: breakdown(
            quality: 1.0, recency: -0.5
        ))
        XCTAssertEqual(result.map { $0.id }, ["Quality"])
    }

    func test_factors_sorted_descending_by_value() {
        let result = breakdownFactors(from: breakdown(
            quality: 0.3, volume: 0.5, sentiment: 0.8, cuisine: 1.2
        ))
        XCTAssertEqual(result.map { $0.id }, ["Cuisine", "Sentiment", "Volume", "Quality"])
        XCTAssertEqual(result.map { $0.value }, [1.2, 0.8, 0.5, 0.3])
    }

    func test_all_ten_fields_produce_ten_factors() {
        let result = breakdownFactors(from: breakdown(
            quality: 1.0, volume: 1.0, distance: 1.0, cost: 1.0, recency: 1.0,
            sentiment: 1.0, audience: 1.0, cuisine: 1.0, aspects: 1.0, history: 1.0
        ))
        XCTAssertEqual(result.count, 10)
        XCTAssertEqual(
            Set(result.map { $0.id }),
            Set(["Quality", "Volume", "Distance", "Cost", "Recency",
                 "Sentiment", "Audience", "Cuisine", "Aspects", "History"])
        )
    }

    func test_regression_only_recency_should_not_be_the_default() throws {
        // Regression guard: this is the exact bug we fixed. A real server response
        // populates many factors; if only `recency` survives decoding, we have
        // regressed to the old broken field-name mapping.
        let json = """
        {
          "place_id": "p", "name": "X",
          "score_breakdown": {
            "quality": 1.0, "volume": 0.4, "distance": 0.3,
            "cost": 0.2, "recency": 0.1, "sentiment": 0.6,
            "audience": 0.0, "cuisine": 0.8, "aspects": 0.0, "history": 0.0
          }
        }
        """.data(using: .utf8)!
        let place = try JSONDecoder().decode(Place.self, from: json)
        let b = try XCTUnwrap(place.score_breakdown)
        let factors = breakdownFactors(from: b)
        XCTAssertGreaterThan(factors.count, 1,
            "Only one factor visible — score_breakdown field names likely diverged from server again")
        XCTAssertEqual(factors.count, 7)
        XCTAssertEqual(factors.first?.id, "Quality")
    }
}
