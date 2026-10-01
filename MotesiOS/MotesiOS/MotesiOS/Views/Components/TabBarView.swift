import SwiftUI

struct TabBarView: View {
    @State var chatVM = ChatViewModel()
    @State var authVM = AuthViewModel()

    var body: some View {
        TabView {
            Tab("Chat", systemImage: "bubble.left.and.bubble.right.fill") {
                ChatView(vm: chatVM)
            }
            Tab("Call", systemImage: "phone.fill") {
                if let agentId = chatVM.agents.first?.id {
                    CallView(agentId: agentId)
                } else {
                    VStack {
                        MascotView(size: 80)
                        Text("Loading...")
                            .foregroundStyle(.secondary)
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
    }
}
