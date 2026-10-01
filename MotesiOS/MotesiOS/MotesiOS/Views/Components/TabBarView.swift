import SwiftUI

struct TabBarView: View {
    @State var chatVM = ChatViewModel()
    @State var authVM = AuthViewModel()
    @State var agentId = ""
    @State var loadError = ""

    var body: some View {
        TabView {
            Tab("Chat", systemImage: "bubble.left.and.bubble.right.fill") {
                ChatView(vm: chatVM)
            }
            Tab("Call", systemImage: "phone.fill") {
                if !agentId.isEmpty {
                    CallView(agentId: agentId)
                } else if !loadError.isEmpty {
                    VStack(spacing: 12) {
                        MascotView(size: 80)
                        Text("Could not load agent")
                            .font(.headline)
                        Text(loadError)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 32)
                        Button("Retry") {
                            Task { await loadAgent() }
                        }
                        .tint(MotesTheme.accent)
                    }
                } else {
                    VStack {
                        MascotView(size: 80)
                        ProgressView()
                            .padding(.top, 8)
                    }
                }
            }
            Tab("Services", systemImage: "link") {
                ServicesView()
            }
            Tab("Settings", systemImage: "gearshape.fill") {
                SettingsView(authVM: authVM)
            }
        }
        .tint(MotesTheme.accent)
        .task { await loadAgent() }
    }

    func loadAgent() async {
        loadError = ""
        do {
            let agents: [Agent] = try await APIClient.shared.get("/api/agents")
            if let first = agents.first {
                agentId = first.id
            } else {
                loadError = "No agents configured"
            }
        } catch {
            loadError = error.localizedDescription
        }
    }
}
