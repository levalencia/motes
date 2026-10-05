import XCTest
@testable import MotesiOS

final class MCPModelsTests: XCTestCase {

    func testMCPServerDecode() throws {
        let json = """
        {
            "id": "s1",
            "name": "Local MCP",
            "type": "stdio",
            "command": "npx mcp-server",
            "url": null,
            "tool_count": 5,
            "status": "connected"
        }
        """.data(using: .utf8)!

        let server = try JSONDecoder().decode(MCPServer.self, from: json)
        XCTAssertEqual(server.id, "s1")
        XCTAssertEqual(server.name, "Local MCP")
        XCTAssertEqual(server.type, "stdio")
        XCTAssertEqual(server.command, "npx mcp-server")
        XCTAssertNil(server.url)
        XCTAssertEqual(server.tool_count, 5)
        XCTAssertEqual(server.status, "connected")
    }

    func testMCPServerDecodeHTTP() throws {
        let json = """
        {
            "id": "s2",
            "name": "Remote MCP",
            "type": "http",
            "command": null,
            "url": "https://mcp.example.com",
            "tool_count": null,
            "status": null
        }
        """.data(using: .utf8)!

        let server = try JSONDecoder().decode(MCPServer.self, from: json)
        XCTAssertEqual(server.type, "http")
        XCTAssertNil(server.command)
        XCTAssertEqual(server.url, "https://mcp.example.com")
        XCTAssertNil(server.tool_count)
        XCTAssertNil(server.status)
    }

    func testMCPTestResultDecode() throws {
        let json = """
        {"success": true, "message": "All tools operational"}
        """.data(using: .utf8)!

        let result = try JSONDecoder().decode(MCPTestResult.self, from: json)
        XCTAssertTrue(result.success)
        XCTAssertEqual(result.message, "All tools operational")
    }

    func testMCPTestResultDecodeNilMessage() throws {
        let json = """
        {"success": false, "message": null}
        """.data(using: .utf8)!

        let result = try JSONDecoder().decode(MCPTestResult.self, from: json)
        XCTAssertFalse(result.success)
        XCTAssertNil(result.message)
    }
}
