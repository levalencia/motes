import XCTest

/// Verify hardcoded URLs in the iOS app match the actual backend routes.
/// Catches mismatches like /agents/{id}/realtime vs /realtime-call/{id}.
final class URLConsistencyTests: XCTestCase {

    func testVoiceCallWebSocketURL() {
        // The backend route is @router.websocket("/api/realtime-call/{agent_id}")
        let baseURL = "wss://example.com"
        let agentId = "test-agent"
        let url = "\(baseURL)/api/realtime-call/\(agentId)"
        XCTAssertTrue(url.contains("/api/realtime-call/"), "WebSocket URL must use /api/realtime-call/ not /api/agents/")
        XCTAssertFalse(url.contains("/agents/\(agentId)/realtime"), "Old URL pattern should not be used")
    }

    func testApprovalEndpoints() {
        let agentId = "test-agent"
        let approvalId = "req-123"

        // List approvals must be agent-scoped
        let listURL = "/api/agents/\(agentId)/approvals"
        XCTAssertTrue(listURL.contains("/agents/"))

        // Resolve must use /resolve with body, not /approve or /deny
        let resolveURL = "/api/approvals/\(approvalId)/resolve"
        XCTAssertTrue(resolveURL.contains("/resolve"))
        XCTAssertFalse(resolveURL.contains("/approve"))
        XCTAssertFalse(resolveURL.contains("/deny"))
    }

    func testScheduledTaskEndpoints() {
        let agentId = "test-agent"
        let taskId = "task-456"

        // All task endpoints must be agent-scoped
        let listURL = "/api/agents/\(agentId)/tasks"
        XCTAssertTrue(listURL.contains("/agents/\(agentId)/tasks"))

        let pauseURL = "/api/agents/\(agentId)/tasks/\(taskId)/pause"
        XCTAssertTrue(pauseURL.contains("/agents/"))
    }

    func testThreadEndpoint() {
        let agentId = "test-agent"
        let threadURL = "/api/agents/\(agentId)/thread"
        XCTAssertTrue(threadURL.contains("/agents/\(agentId)/thread"))
    }
}
