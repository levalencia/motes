import XCTest
@testable import MotesiOS

final class ApprovalModelsTests: XCTestCase {

    // MARK: - Codable

    func testDecodeFull() throws {
        let json = """
        {
            "id": "a1",
            "tool_name": "gmail_send",
            "arguments_json": "{}",
            "status": "pending",
            "created_at": "2025-01-01"
        }
        """.data(using: .utf8)!

        let approval = try JSONDecoder().decode(Approval.self, from: json)
        XCTAssertEqual(approval.id, "a1")
        XCTAssertEqual(approval.tool_name, "gmail_send")
        XCTAssertEqual(approval.arguments_json, "{}")
        XCTAssertEqual(approval.status, "pending")
        XCTAssertEqual(approval.created_at, "2025-01-01")
    }

    func testDecodeNilCreatedAt() throws {
        let json = """
        {
            "id": "a2",
            "tool_name": "outlook_send_email",
            "arguments_json": "{}",
            "status": "approved",
            "created_at": null
        }
        """.data(using: .utf8)!

        let approval = try JSONDecoder().decode(Approval.self, from: json)
        XCTAssertNil(approval.created_at)
    }

    // MARK: - displayName

    func testDisplayNameKnownTools() {
        let knownTools: [(String, String)] = [
            ("gmail_send", "📧 Send an email via Gmail"),
            ("outlook_send_email", "📧 Send an email via Outlook"),
            ("calendar_create", "📅 Create a calendar event"),
            ("reminders_create", "🔔 Create a reminder in Apple Reminders"),
            ("file_download_url", "📁 Generate a file download link"),
            ("pptx_add_slide", "📊 Add a slide to a PowerPoint"),
        ]

        for (toolName, expected) in knownTools {
            let approval = makeApproval(toolName: toolName)
            XCTAssertEqual(approval.displayName, expected, "Failed for tool: \(toolName)")
        }
    }

    func testDisplayNameUnknownToolReplacesUnderscores() {
        let approval = makeApproval(toolName: "some_unknown_tool")
        XCTAssertEqual(approval.displayName, "some unknown tool")
    }

    // MARK: - displayArgs

    func testDisplayArgsEmail() {
        let argsJSON = #"{"to":"alice@example.com","subject":"Hello"}"#
        let approval = makeApproval(toolName: "gmail_send", argsJSON: argsJSON)
        XCTAssertEqual(approval.displayArgs, "To: alice@example.com\nSubject: Hello")
    }

    func testDisplayArgsOutlookEmail() {
        let argsJSON = #"{"to":"bob@example.com","subject":"Meeting"}"#
        let approval = makeApproval(toolName: "outlook_send_email", argsJSON: argsJSON)
        XCTAssertEqual(approval.displayArgs, "To: bob@example.com\nSubject: Meeting")
    }

    func testDisplayArgsReminder() {
        let argsJSON = #"{"title":"Buy groceries"}"#
        let approval = makeApproval(toolName: "reminders_create", argsJSON: argsJSON)
        XCTAssertEqual(approval.displayArgs, "Reminder: Buy groceries")
    }

    func testDisplayArgsCalendar() {
        let argsJSON = #"{"title":"Standup"}"#
        let approval = makeApproval(toolName: "calendar_create", argsJSON: argsJSON)
        XCTAssertEqual(approval.displayArgs, "Event: Standup")
    }

    func testDisplayArgsInvalidJSON() {
        let approval = makeApproval(toolName: "gmail_send", argsJSON: "not json")
        XCTAssertEqual(approval.displayArgs, "not json")
    }

    // MARK: - isPending

    func testIsPendingTrue() {
        let approval = makeApproval(status: "pending")
        XCTAssertTrue(approval.isPending)
    }

    func testIsPendingFalse() {
        let approval = makeApproval(status: "approved")
        XCTAssertFalse(approval.isPending)
    }

    // MARK: - Helpers

    private func makeApproval(
        toolName: String = "gmail_send",
        argsJSON: String = "{}",
        status: String = "pending"
    ) -> Approval {
        Approval(
            id: "test",
            tool_name: toolName,
            arguments_json: argsJSON,
            status: status,
            created_at: nil
        )
    }
}
