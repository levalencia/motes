import Foundation

@Observable
class ChatViewModel {
    var messages: [ChatMessage] = []
    var input = ""
    var isStreaming = false
    var conversationId: String?
    var conversations: [Conversation] = []
    var agentId = ""
    var agents: [Agent] = []
    var error: String?
    let eventStream = EventStreamService()

    func loadData() async {
        do {
            agents = try await APIClient.shared.get("/api/agents")
            if let first = agents.first {
                agentId = first.id
                conversations = try await ChatService.loadConversations(agentId: first.id)
            }
        } catch { /* ignore */ }
        eventStream.start()
    }

    func sendMessage() async {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isStreaming else { return }
        input = ""
        messages.append(ChatMessage(id: UUID().uuidString, role: "user", content: text, tool_name: nil))
        isStreaming = true
        error = nil

        var assistantContent = ""
        messages.append(ChatMessage(id: UUID().uuidString, role: "assistant", content: "", tool_name: nil))

        for await event in ChatService.sendMessage(agentId: agentId, message: text, conversationId: conversationId) {
            switch event {
            case .token(let t):
                assistantContent += t
                messages[messages.count - 1] = ChatMessage(id: messages[messages.count - 1].id, role: "assistant", content: assistantContent, tool_name: nil)
            case .toolCall(let name, let result):
                messages.insert(ChatMessage(id: UUID().uuidString, role: "tool", content: result, tool_name: name), at: messages.count - 1)
            case .done(let content, let convId):
                messages[messages.count - 1] = ChatMessage(id: messages[messages.count - 1].id, role: "assistant", content: content, tool_name: nil)
                if let cid = convId { conversationId = cid }
            case .error(let msg):
                self.error = msg
            }
        }
        isStreaming = false
        // Refresh conversations
        if let aid = agents.first?.id {
            conversations = (try? await ChatService.loadConversations(agentId: aid)) ?? conversations
        }
    }

    func loadConversation(id: String) async {
        conversationId = id
        do {
            messages = try await ChatService.loadMessages(conversationId: id)
        } catch { /* ignore */ }
    }

    func deleteConversation(id: String) async {
        try? await ChatService.deleteConversation(id: id)
        conversations.removeAll { $0.id == id }
        if conversationId == id {
            messages = []
            conversationId = nil
        }
    }

    func newChat() {
        messages = []
        conversationId = nil
        input = ""
    }

    func handleProactiveEvent(_ event: ProactiveEvent) {
        messages.append(ChatMessage(id: UUID().uuidString, role: "assistant", content: "💡 **\(event.title)**\n\n\(event.body)", tool_name: nil))
    }
}
