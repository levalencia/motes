import Foundation

@Observable
class DashboardViewModel {
    var agents: [Agent] = []
    var conversations: [Conversation] = []
    var isLoading = true

    func loadData() async {
        do {
            agents = try await APIClient.shared.get("/api/agents")
            if let first = agents.first {
                conversations = try await ChatService.loadConversations(agentId: first.id)
            }
        } catch { /* ignore */ }
        isLoading = false
    }
}
