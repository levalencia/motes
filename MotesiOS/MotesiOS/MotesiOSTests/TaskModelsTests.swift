import XCTest
@testable import MotesiOS

final class TaskModelsTests: XCTestCase {

    func testDecode() throws {
        let json = """
        {
            "id": "t1",
            "name": "Daily summary",
            "prompt": "Summarise my inbox",
            "cron_expression": "0 8 * * *",
            "status": "active",
            "run_count": 5,
            "last_run_at": "2025-06-01T08:00:00Z"
        }
        """.data(using: .utf8)!

        let task = try JSONDecoder().decode(ScheduledTask.self, from: json)
        XCTAssertEqual(task.id, "t1")
        XCTAssertEqual(task.name, "Daily summary")
        XCTAssertEqual(task.prompt, "Summarise my inbox")
        XCTAssertEqual(task.cron_expression, "0 8 * * *")
        XCTAssertEqual(task.status, "active")
        XCTAssertEqual(task.run_count, 5)
        XCTAssertEqual(task.last_run_at, "2025-06-01T08:00:00Z")
    }

    func testDecodeNilLastRunAt() throws {
        let json = """
        {
            "id": "t2",
            "name": "Test",
            "prompt": "Do something",
            "cron_expression": "0 * * * *",
            "status": "paused",
            "run_count": 0,
            "last_run_at": null
        }
        """.data(using: .utf8)!

        let task = try JSONDecoder().decode(ScheduledTask.self, from: json)
        XCTAssertNil(task.last_run_at)
    }

    func testEnabledGetActive() {
        let task = makeTask(status: "active")
        XCTAssertTrue(task.enabled)
    }

    func testEnabledGetPaused() {
        let task = makeTask(status: "paused")
        XCTAssertFalse(task.enabled)
    }

    func testEnabledSetTrue() {
        var task = makeTask(status: "paused")
        task.enabled = true
        XCTAssertEqual(task.status, "active")
    }

    func testEnabledSetFalse() {
        var task = makeTask(status: "active")
        task.enabled = false
        XCTAssertEqual(task.status, "paused")
    }

    // MARK: - Helpers

    private func makeTask(status: String) -> ScheduledTask {
        ScheduledTask(
            id: "t",
            name: "Test",
            prompt: "prompt",
            cron_expression: "0 * * * *",
            status: status,
            run_count: 0,
            last_run_at: nil
        )
    }
}
