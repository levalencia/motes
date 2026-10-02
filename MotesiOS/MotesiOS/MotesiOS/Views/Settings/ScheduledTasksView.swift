import SwiftUI

struct ScheduledTasksView: View {
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
            AddTaskSheet { prompt, schedule in
                await createTask(prompt: prompt, schedule: schedule)
            }
        }
        .task { await loadTasks() }
    }

    @ViewBuilder
    private func taskRow(_ task: ScheduledTask) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(task.prompt)
                    .font(.subheadline)
                    .lineLimit(2)
                Text(task.schedule)
                    .font(.caption)
                    .foregroundStyle(.secondary)
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

    private func loadTasks() async {
        do {
            tasks = try await APIClient.shared.get("/api/tasks")
        } catch { /* ignore */ }
        isLoading = false
    }

    private func createTask(prompt: String, schedule: String) async {
        do {
            let newTask: ScheduledTask = try await APIClient.shared.post(
                "/api/tasks",
                body: CreateTaskRequest(prompt: prompt, schedule: schedule)
            )
            tasks.append(newTask)
        } catch { /* ignore */ }
    }

    private func toggleTask(_ task: ScheduledTask, enabled: Bool) async {
        let action = enabled ? "resume" : "pause"
        do {
            let _: ScheduledTask = try await APIClient.shared.post(
                "/api/tasks/\(task.id)/\(action)",
                body: EmptyBody()
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
            Task { try? await APIClient.shared.delete("/api/tasks/\(task.id)") }
        }
    }
}

struct AddTaskSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var prompt = ""
    @State private var selectedSchedule = "Every morning 8am"
    @State private var customSchedule = ""

    let scheduleOptions = ["Every morning 8am", "Every hour", "Daily 7pm", "Custom"]

    let onCreate: (String, String) async -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section("Task Prompt") {
                    TextField("What should Motes do?", text: $prompt, axis: .vertical)
                        .lineLimit(3...6)
                }

                Section("Schedule") {
                    Picker("Frequency", selection: $selectedSchedule) {
                        ForEach(scheduleOptions, id: \.self) { option in
                            Text(option).tag(option)
                        }
                    }

                    if selectedSchedule == "Custom" {
                        TextField("Cron expression or description", text: $customSchedule)
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
                        let schedule = selectedSchedule == "Custom" ? customSchedule : selectedSchedule
                        Task {
                            await onCreate(prompt, schedule)
                            dismiss()
                        }
                    }
                    .disabled(prompt.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
    }
}

private struct EmptyBody: Codable {}
