import SwiftUI

struct ServicesView: View {
    @State private var vm = ServicesViewModel()
    @State private var configuringService = ""
    @State private var keyInputs: [String: String] = [:]

    var body: some View {
        NavigationStack {
            List {
                // Slack & Telegram integration cards
                Section("💬 Messaging Integrations") {
                    MessagingSetupCard(
                        name: "Slack",
                        icon: "bubble.left.and.bubble.right",
                        color: .purple,
                        webhookURL: "\(APIClient.shared.baseURL)/api/webhooks/slack",
                        steps: [
                            "1. Create a Slack App at api.slack.com/apps",
                            "2. Enable Event Subscriptions",
                            "3. Set Request URL to the webhook URL below",
                            "4. Subscribe to message.im events",
                            "5. Install the app to your workspace",
                        ]
                    )

                    MessagingSetupCard(
                        name: "Telegram",
                        icon: "paperplane.fill",
                        color: .blue,
                        webhookURL: "\(APIClient.shared.baseURL)/api/webhooks/telegram",
                        steps: [
                            "1. Message @BotFather on Telegram",
                            "2. Create a new bot with /newbot",
                            "3. Copy the bot token to Services > Telegram",
                            "4. Set the webhook URL below via Telegram API",
                            "5. Send a message to your bot to test",
                        ]
                    )
                }

                ForEach(vm.catalog) { item in
                    let isBuiltIn = item.built_in == true
                    let isComingSoon = item.coming_soon == true
                    let key = item.name.lowercased()
                    let isConfigured = vm.serviceStatuses[key] == true

                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(item.name)
                                .font(.subheadline.bold())
                            Spacer()
                            if isBuiltIn {
                                Text("Active")
                                    .font(.caption2)
                                    .foregroundStyle(MotesTheme.teal)
                            } else if isConfigured {
                                Text("Connected")
                                    .font(.caption2)
                                    .foregroundStyle(.green)
                            } else if isComingSoon {
                                Text("Coming soon")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        Text(item.description)
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        if !isBuiltIn && !isComingSoon {
                            if let envVars = item.env_vars, !envVars.isEmpty {
                                if isConfigured {
                                    Button("Disconnect", role: .destructive) {
                                        Task { await vm.disconnect(service: key) }
                                    }
                                    .font(.caption)
                                } else {
                                    Button("Setup") { configuringService = key }
                                        .font(.caption)
                                        .tint(MotesTheme.accent)
                                }
                            }
                        }
                    }
                    .opacity(isComingSoon ? 0.5 : 1)
                }
            }
            .navigationTitle("Services")
            .task { await vm.loadData() }
        }
    }
}
