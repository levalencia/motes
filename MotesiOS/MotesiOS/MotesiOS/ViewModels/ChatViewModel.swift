import Foundation

@Observable
class ChatViewModel {
    var messages: [ChatMessage] = []
    var input = ""
    var isStreaming = false
    var error: String?
    var scrollTrigger = 0
    var conversationId: String?
    var agentId = ""
    var agents: [Agent] = []
    var pendingApprovals: [Approval] = []
    let eventStream = EventStreamService()
    let speechRecognizer = SpeechRecognizerService()
    private var approvalPollingTask: Task<Void, Never>?

    func startDictation() {
        speechRecognizer.startListening()
        // Poll transcript into input field
        Task { @MainActor in
            while speechRecognizer.isListening {
                if !speechRecognizer.transcript.isEmpty {
                    input = speechRecognizer.transcript
                }
                try? await Task.sleep(for: .milliseconds(200))
            }
        }
    }

    func stopDictation() {
        speechRecognizer.stopListening()
        if !speechRecognizer.transcript.isEmpty {
            input = speechRecognizer.transcript
        }
    }

    func loadData() async {
        do {
            agents = try await APIClient.shared.get("/api/agents")
            if let first = agents.first {
                agentId = first.id
                // Load the single thread
                messages = try await ChatService.loadThread(agentId: first.id)
            }
        } catch { /* ignore */ }
        eventStream.start()
        startApprovalPolling()
    }

    func refreshThread() async {
        guard !agentId.isEmpty else { return }
        do {
            messages = try await ChatService.loadThread(agentId: agentId)
        } catch { /* ignore */ }
    }

    // MARK: - Approval Polling

    func startApprovalPolling() {
        approvalPollingTask?.cancel()
        approvalPollingTask = Task {
            while !Task.isCancelled {
                await fetchApprovals()
                try? await Task.sleep(for: .seconds(5))
            }
        }
    }

    func fetchApprovals() async {
        guard !agentId.isEmpty else { return }
        do {
            let all: [Approval] = try await APIClient.shared.get("/api/agents/\(agentId)/approvals")
            pendingApprovals = all.filter { $0.isPending }
        } catch { /* ignore */ }
    }

    func approveItem(_ approval: Approval) async {
        do {
            let body = ResolveBody(approved: true)
            let _: [String: String] = try await APIClient.shared.post(
                "/api/approvals/\(approval.id)/resolve",
                body: body
            )
            if let idx = pendingApprovals.firstIndex(where: { $0.id == approval.id }) {
                pendingApprovals[idx].status = "approved"
                // Remove from pending after a brief delay so user sees the result
                Task {
                    try? await Task.sleep(for: .seconds(1.5))
                    pendingApprovals.removeAll { $0.id == approval.id }
                }
            }
        } catch {
            self.error = "Failed to approve"
        }
    }

    func denyItem(_ approval: Approval) async {
        do {
            let body = ResolveBody(approved: false)
            let _: [String: String] = try await APIClient.shared.post(
                "/api/approvals/\(approval.id)/resolve",
                body: body
            )
            if let idx = pendingApprovals.firstIndex(where: { $0.id == approval.id }) {
                pendingApprovals[idx].status = "denied"
                Task {
                    try? await Task.sleep(for: .seconds(1.5))
                    pendingApprovals.removeAll { $0.id == approval.id }
                }
            }
        } catch {
            self.error = "Failed to deny"
        }
    }

    func sendMessage() async {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isStreaming else { return }
        input = ""
        messages.append(ChatMessage(id: UUID().uuidString, role: "user", content: text, tool_name: nil, message_type: "chat"))
        isStreaming = true
        error = nil

        var assistantContent = ""
        messages.append(ChatMessage(id: UUID().uuidString, role: "assistant", content: "", tool_name: nil, message_type: "chat"))

        for await event in ChatService.sendMessage(agentId: agentId, message: text, conversationId: conversationId) {
            switch event {
            case .token(let t):
                assistantContent += t
                messages[messages.count - 1] = ChatMessage(id: messages[messages.count - 1].id, role: "assistant", content: assistantContent, tool_name: nil, message_type: "chat")
            case .toolCall(let name, let result):
                messages.insert(ChatMessage(id: UUID().uuidString, role: "tool", content: result, tool_name: name, message_type: "chat"), at: messages.count - 1)
            case .done(let content, let convId):
                messages[messages.count - 1] = ChatMessage(id: messages[messages.count - 1].id, role: "assistant", content: content, tool_name: nil, message_type: "chat")
                if let cid = convId { conversationId = cid }
            case .error(let msg):
                self.error = msg
            }
        }
        isStreaming = false
    }

    func clearThread() async {
        guard !agentId.isEmpty else { return }
        do {
            try await ChatService.clearThread(agentId: agentId)
            messages = []
            conversationId = nil
        } catch {
            self.error = "Failed to clear thread"
        }
    }

    func handleProactiveEvent(_ event: ProactiveEvent) {
        messages.append(ChatMessage(id: UUID().uuidString, role: "assistant", content: "**\(event.title)**\n\n\(event.body)", tool_name: nil, message_type: "proactive"))
    }
}
