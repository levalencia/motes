import SwiftUI

struct MCPServersView: View {
    @State private var servers: [MCPServer] = []
    @State private var showAddSheet = false
    @State private var isLoading = true
    @State private var testingId: String?
    @State private var testResult: String?

    var body: some View {
        Group {
            if isLoading {
                ProgressView()
            } else if servers.isEmpty {
                ContentUnavailableView(
                    "No MCP Servers",
                    systemImage: "server.rack",
                    description: Text("Add an MCP server to extend Motes")
                )
            } else {
                List {
                    ForEach(servers) { server in
                        serverRow(server)
                    }
                    .onDelete(perform: deleteServers)
                }
            }
        }
        .navigationTitle("MCP Integrations")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showAddSheet = true
                } label: {
                    Image(systemName: "plus")
                }
            }
        }
        .sheet(isPresented: $showAddSheet) {
            AddMCPServerSheet { name, type, command, url in
                await createServer(name: name, type: type, command: command, url: url)
            }
        }
        .task { await loadServers() }
    }

    @ViewBuilder
    private func serverRow(_ server: MCPServer) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: server.type == "http" ? "globe" : "terminal")
                    .foregroundStyle(MotesTheme.accent)
                    .font(.caption)
                Text(server.name)
                    .font(.subheadline.bold())
                Spacer()
                Text(server.type.uppercased())
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.gray.opacity(0.15))
                    .clipShape(Capsule())
            }

            if let toolCount = server.tool_count {
                Text("\(toolCount) tool\(toolCount == 1 ? "" : "s") available")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            if let result = testResult, testingId == server.id {
                Text(result)
                    .font(.caption)
                    .foregroundStyle(result.hasPrefix("✅") ? .green : .red)
            }

            Button {
                Task { await testServer(server) }
            } label: {
                HStack(spacing: 4) {
                    if testingId == server.id && testResult == nil {
                        ProgressView()
                            .controlSize(.mini)
                    } else {
                        Image(systemName: "play.circle")
                    }
                    Text("Test Connection")
                }
                .font(.caption)
            }
            .tint(MotesTheme.accent)
        }
        .padding(.vertical, 2)
    }

    private func loadServers() async {
        do {
            servers = try await APIClient.shared.get("/api/mcp/servers")
        } catch { /* ignore */ }
        isLoading = false
    }

    private func createServer(name: String, type: String, command: String?, url: String?) async {
        do {
            let req = CreateMCPServerRequest(name: name, type: type, command: command, url: url)
            let newServer: MCPServer = try await APIClient.shared.post("/api/mcp/servers", body: req)
            servers.append(newServer)
        } catch { /* ignore */ }
    }

    private func testServer(_ server: MCPServer) async {
        testingId = server.id
        testResult = nil
        do {
            struct Empty: Codable {}
            let result: MCPTestResult = try await APIClient.shared.post(
                "/api/mcp/servers/\(server.id)/test",
                body: Empty()
            )
            testResult = result.success ? "✅ Connected" : "❌ \(result.message ?? "Failed")"
        } catch {
            testResult = "❌ Connection failed"
        }
    }

    private func deleteServers(at offsets: IndexSet) {
        let toDelete = offsets.map { servers[$0] }
        servers.remove(atOffsets: offsets)
        for server in toDelete {
            Task { try? await APIClient.shared.delete("/api/mcp/servers/\(server.id)") }
        }
    }
}

struct AddMCPServerSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var type = "stdio"
    @State private var command = ""
    @State private var url = ""

    let onCreate: (String, String, String?, String?) async -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section("Server Info") {
                    TextField("Name", text: $name)
                    Picker("Type", selection: $type) {
                        Text("stdio").tag("stdio")
                        Text("HTTP").tag("http")
                    }
                    .pickerStyle(.segmented)
                }

                if type == "stdio" {
                    Section("Command") {
                        TextField("e.g. npx -y @modelcontextprotocol/server-filesystem", text: $command, axis: .vertical)
                            .lineLimit(2...4)
                            .font(.caption)
                    }
                } else {
                    Section("URL") {
                        TextField("https://mcp-server.example.com", text: $url)
                            .textContentType(.URL)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("Add MCP Server")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        Task {
                            await onCreate(
                                name,
                                type,
                                type == "stdio" ? command : nil,
                                type == "http" ? url : nil
                            )
                            dismiss()
                        }
                    }
                    .disabled(name.isEmpty || (type == "stdio" && command.isEmpty) || (type == "http" && url.isEmpty))
                }
            }
        }
    }
}
