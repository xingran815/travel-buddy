import XCTest
@testable import TravelBuddyKit

/// Guards parity between the SwiftUI category refinement gates and the CLI
/// rules in app/ui/prompts.py (_ask_category_refinement / _build_filter_choices).
@MainActor
final class CategoryRefinementTests: XCTestCase {

    private func vm(categories: Set<String>, profile: String = "balanced") -> RecommendViewModel {
        let m = RecommendViewModel()
        m.selectedCategories = categories
        m.selectedProfile = profile
        return m
    }

    func test_vibe_shown_only_for_food_or_nightlife() {
        XCTAssertTrue(vm(categories: ["food"]).showVibe)
        XCTAssertTrue(vm(categories: ["nightlife"]).showVibe)
        XCTAssertFalse(vm(categories: ["shopping"]).showVibe)
    }

    func test_indoor_outdoor_shown_for_relevant_categories_only() {
        for c in ["sights", "museums", "nature", "family", "nightlife"] {
            XCTAssertTrue(vm(categories: [c]).showIndoorOutdoor, "expected \(c) to show setting")
        }
        XCTAssertFalse(vm(categories: ["food"]).showIndoorOutdoor)
        XCTAssertFalse(vm(categories: ["shopping"]).showIndoorOutdoor)
    }

    func test_budget_hidden_for_budget_profile() {
        XCTAssertTrue(vm(categories: ["food"], profile: "balanced").showBudget)
        XCTAssertFalse(vm(categories: ["food"], profile: "budget").showBudget)
    }

    func test_family_category_auto_sets_audience_and_hides_control() {
        let m = vm(categories: ["family", "food"])
        XCTAssertTrue(m.autoFamily)
        XCTAssertFalse(m.showAudience)
        XCTAssertEqual(m.effectiveAudience, "family")
    }

    func test_effective_audience_uses_selection_when_no_family_category() {
        let m = vm(categories: ["food"])
        XCTAssertTrue(m.showAudience)
        XCTAssertNil(m.effectiveAudience)
        m.selectedAudience = "adult"
        XCTAssertEqual(m.effectiveAudience, "adult")
    }

    private func place(_ id: String) -> Place {
        let json = Data(#"{"place_id":"\#(id)","name":"\#(id)"}"#.utf8)
        return try! JSONDecoder().decode(Place.self, from: json)
    }

    private func cat(_ id: String) -> AppCategory {
        AppCategory(id: id, name_en: id, name_tr: id, google_types: [])
    }

    func test_allCategoryPlaces_flattens_in_categories_order() {
        let m = RecommendViewModel()
        m.categories = [cat("food"), cat("nightlife"), cat("museums")]
        m.categoryResults = [
            "nightlife": [place("bar1")],
            "food": [place("rest1"), place("rest2")],
            // "museums" intentionally absent
        ]
        XCTAssertEqual(m.allCategoryPlaces.map(\.place_id), ["rest1", "rest2", "bar1"])
    }
}
