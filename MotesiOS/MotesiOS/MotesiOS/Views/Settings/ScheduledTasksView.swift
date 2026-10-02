import SwiftUI

struct ScheduledTasksView: View {
    let agentId: String
    @State private var tasks: [ScheduledTask] = []
    @State private var showAddSheet = false
    @State private var isLoading = true

    var body: some View {
        Group {
            if isLoading {
                ProgressView()
            } else if tasks.isEmpty {
                ContentUnavailableView(
                    "No Scheduled Tasks",
                    systemImage: "clock.badge.questionmark",
                    description: Text("Add a task to run on a schedule")
                )
            } else {
                List {
                    ForEach(tasks) { task in
                        taskRow(task)
                    }
                    .onDelete(perform: deleteTasks)
                }
            }
        }
        .navigationTitle("Scheduled Tasks")
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
            AddTaskSheet { name, prompt, cron in
                await createTask(name: name, prompt: prompt, cron: cron)
            }
        }
        .task { await loadTasks() }
    }

    @ViewBuilder
    private func taskRow(_ task: ScheduledTask) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(task.name)
                    .font(.subheadline.bold())
                Text(task.prompt)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
                Text(formatCron(task.cron_expression))
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
            Spacer()
            Toggle("", isOn: Binding(
                get: { task.enabled },
                set: { newValue in
                    Task { await toggleTask(task, enabled: newValue) }
                }
            ))
            .labelsHidden()
        }
    }

    private func formatCron(_ cron: String) -> String {
        let map: [String: String] = [
            "0 7 * * *": "🌅 Every morning 7am",
            "0 8 * * *": "⏰ Every morning 8am",
            "0 19 * * *": "🌆 Daily 7pm",
            "0 * * * *": "🕐 Every hour",
            "*/30 * * * *": "⏱ Every 30 min",
            "0 9 * * 1-5": "📅 Weekdays 9am",
            "0 10 * * 0,6": "🛋 Weekends 10am",
            "0 23 * * *": "🌙 Every night 11pm",
            "0 9 * * 1": "📆 Monday 9am",
            "0 17 * * 5": "📆 Friday 5pm",
        ]
        return map[cron] ?? cron
    }

    private func loadTasks() async {
        do {
            tasks = try await APIClient.shared.get("/api/agents/\(agentId)/tasks")
        } catch { /* ignore */ }
        isLoading = false
    }

    private func createTask(name: String, prompt: String, cron: String) async {
        struct Body: Codable { let name: String; let prompt: String; let cron_expression: String }
        do {
            let newTask: ScheduledTask = try await APIClient.shared.post(
                "/api/agents/\(agentId)/tasks",
                body: Body(name: name, prompt: prompt, cron_expression: cron)
            )
            tasks.append(newTask)
        } catch { /* ignore */ }
    }

    private func toggleTask(_ task: ScheduledTask, enabled: Bool) async {
        let action = enabled ? "resume" : "pause"
        struct Empty: Codable {}
        do {
            let _: ScheduledTask = try await APIClient.shared.post(
                "/api/agents/\(agentId)/tasks/\(task.id)/\(action)",
                body: Empty()
            )
            if let idx = tasks.firstIndex(where: { $0.id == task.id }) {
                tasks[idx].enabled = enabled
            }
        } catch { /* ignore */ }
    }

    private func deleteTasks(at offsets: IndexSet) {
        let toDelete = offsets.map { tasks[$0] }
        tasks.remove(atOffsets: offsets)
        for task in toDelete {
            Task { try? await APIClient.shared.delete("/api/agents/\(agentId)/tasks/\(task.id)") }
        }
    }
}

struct AddTaskSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var prompt = ""
    @State private var selectedCron = "0 8 * * *"
    @State private var customCron = ""

    let scheduleOptions: [(label: String, cron: String)] = [
        ("⏰ Every morning 8am", "0 8 * * *"),
        ("🌅 Every morning 7am", "0 7 * * *"),
        ("🌆 Daily 7pm", "0 19 * * *"),
        ("🕐 Every hour", "0 * * * *"),
        ("⏱ Every 30 min", "*/30 * * * *"),
        ("📅 Weekdays 9am", "0 9 * * 1-5"),
        ("🛋 Weekends 10am", "0 10 * * 0,6"),
        ("🌙 Every night 11pm", "0 23 * * *"),
        ("📆 Monday 9am", "0 9 * * 1"),
        ("📆 Friday 5pm", "0 17 * * 5"),
        ("🔧 Custom cron", "custom"),
    ]

    let onCreate: (String, String, String) async -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section("Task Name") {
                    TextField("e.g., Morning briefing", text: $name)
                }

                Section("Prompt") {
                    TextField("What should Motes do?", text: $prompt, axis: .vertical)
                        .lineLimit(3...6)
                }

                Section("Schedule") {
                    Picker("Frequency", selection: $selectedCron) {
                        ForEach(scheduleOptions, id: \.cron) { option in
                            Text(option.label).tag(option.cron)
                        }
                    }

                    if selectedCron == "custom" {
                        TextField("Cron expression (e.g., 0 9 * * 1-5)", text: $customCron)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("New Task")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        let cron = selectedCron == "custom" ? customCron : selectedCron
                        let taskName = name.trimmingCharacters(in: .whitespaces).isEmpty
                            ? String(prompt.prefix(50))
                            : name
                        Task {
                            await onCreate(taskName, prompt, cron)
                            dismiss()
                        }
                    }
                    .disabled(prompt.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}
