import XCTest
@testable import MotesiOS

// Duplicate of the private formatCron function from ScheduledTasksView for testing
private func formatCron(_ cron: String) -> String {
    let map: [String: String] = [
        "0 7 * * *": "🌅 Every morning 7am",
        "0 8 * * *": "⏰ Every morning 8am",
        "0 19 * * *": "🌆 Daily 7pm",
        "0 * * * *": "🕐 Every hour",
        "*/30 * * * *": "⏱ Every 30 min",
        "0 9 * * 1-5": "📅 Weekdays 9am",
        "0 10 * * 0,6": "🛋 Weekends 10am",
        "0 23 * * *": "🌙 Every night 11pm",
        "0 9 * * 1": "📆 Monday 9am",
        "0 17 * * 5": "📆 Friday 5pm",
    ]
    return map[cron] ?? cron
}

final class FormatHelpersTests: XCTestCase {

    func testAllPresets() {
        let presets: [(String, String)] = [
            ("0 7 * * *", "🌅 Every morning 7am"),
            ("0 8 * * *", "⏰ Every morning 8am"),
            ("0 19 * * *", "🌆 Daily 7pm"),
            ("0 * * * *", "🕐 Every hour"),
            ("*/30 * * * *", "⏱ Every 30 min"),
            ("0 9 * * 1-5", "📅 Weekdays 9am"),
            ("0 10 * * 0,6", "🛋 Weekends 10am"),
            ("0 23 * * *", "🌙 Every night 11pm"),
            ("0 9 * * 1", "📆 Monday 9am"),
            ("0 17 * * 5", "📆 Friday 5pm"),
        ]

        for (cron, expected) in presets {
            XCTAssertEqual(formatCron(cron), expected, "Failed for cron: \(cron)")
        }
    }

    func testUnknownCronReturnsRaw() {
        let raw = "5 4 * * SUN"
        XCTAssertEqual(formatCron(raw), raw)
    }

    func testEmptyStringReturnsRaw() {
        XCTAssertEqual(formatCron(""), "")
    }
}
