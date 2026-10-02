import Foundation

struct Agent: Codable, Identifiable {
    let id: String
    let name: String
    var system_prompt: String?
}

struct Conversation: Codable, Identifiable {
    let id: String
    let agent_id: String
    var title: String
    var conversation_type: String?
    var updated_at: String?
}

struct ChatMessage: Codable, Identifiable {
    let id: String
    let role: String
    let content: String
    var tool_name: String?
    var message_type: String?
    var created_at: String?

    /// Resolved type: defaults to "chat" if nil
    var resolvedType: String { message_type ?? "chat" }
}
