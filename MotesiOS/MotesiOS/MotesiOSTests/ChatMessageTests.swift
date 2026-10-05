import XCTest
@testable import MotesiOS

final class ChatMessageTests: XCTestCase {

    func testDecodeAllFields() throws {
        let json = """
        {
            "id": "m1",
            "role": "assistant",
            "content": "Hello!",
            "tool_name": "gmail_send",
            "message_type": "tool_call",
            "created_at": "2025-06-01T12:00:00Z"
        }
        """.data(using: .utf8)!

        let msg = try JSONDecoder().decode(ChatMessage.self, from: json)
        XCTAssertEqual(msg.id, "m1")
        XCTAssertEqual(msg.role, "assistant")
        XCTAssertEqual(msg.content, "Hello!")
        XCTAssertEqual(msg.tool_name, "gmail_send")
        XCTAssertEqual(msg.message_type, "tool_call")
        XCTAssertEqual(msg.created_at, "2025-06-01T12:00:00Z")
    }

    func testDecodeNilOptionalFields() throws {
        let json = """
        {
            "id": "m2",
            "role": "user",
            "content": "Hi"
        }
        """.data(using: .utf8)!

        let msg = try JSONDecoder().decode(ChatMessage.self, from: json)
        XCTAssertNil(msg.tool_name)
        XCTAssertNil(msg.message_type)
        XCTAssertNil(msg.created_at)
    }

    func testResolvedTypeDefaultsToChat() {
        let msg = ChatMessage(
            id: "m3",
            role: "user",
            content: "test",
            tool_name: nil,
            message_type: nil,
            created_at: nil
        )
        XCTAssertEqual(msg.resolvedType, "chat")
    }

    func testResolvedTypeUsesMessageType() {
        let msg = ChatMessage(
            id: "m4",
            role: "assistant",
            content: "test",
            tool_name: nil,
            message_type: "tool_call",
            created_at: nil
        )
        XCTAssertEqual(msg.resolvedType, "tool_call")
    }
}
