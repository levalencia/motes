import Foundation

struct ChatRequest: Codable {
    let message: String
    var conversation_id: String?
}

enum ChatService {
    static func sendMessage(agentId: String, message: String, conversationId: String? = nil) -> AsyncStream<SSEEvent> {
        let body = ChatRequest(message: message, conversation_id: conversationId)
        return APIClient.shared.streamSSE(path: "/api/agents/\(agentId)/chat", body: body)
    }

    /// Load all messages in the single thread for an agent
    static func loadThread(agentId: String) async throws -> [ChatMessage] {
        try await APIClient.shared.get("/api/agents/\(agentId)/thread")
    }

    /// Clear the entire thread
    static func clearThread(agentId: String) async throws {
        try await APIClient.shared.delete("/api/agents/\(agentId)/thread")
    }

    // Legacy methods kept for compatibility
    static func loadConversations(agentId: String) async throws -> [Conversation] {
        try await APIClient.shared.get("/api/agents/\(agentId)/conversations")
    }

    static func loadMessages(conversationId: String) async throws -> [ChatMessage] {
        try await APIClient.shared.get("/api/conversations/\(conversationId)/messages")
    }

    static func deleteConversation(id: String) async throws {
        try await APIClient.shared.delete("/api/conversations/\(id)")
    }

    static func renameConversation(id: String, title: String) async throws {
        struct RenameReq: Codable { let title: String }
        let _: [String: String] = try await APIClient.shared.post("/api/conversations/\(id)/rename", body: RenameReq(title: title))
    }
}
