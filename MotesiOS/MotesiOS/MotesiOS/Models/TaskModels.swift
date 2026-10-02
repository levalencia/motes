import Foundation

struct ScheduledTask: Codable, Identifiable {
    let id: String
    let name: String
    let prompt: String
    let cron_expression: String
    var status: String
    let run_count: Int
    let last_run_at: String?

    var enabled: Bool {
        get { status == "active" }
        set { status = newValue ? "active" : "paused" }
    }

    enum CodingKeys: String, CodingKey {
        case id, name, prompt, cron_expression, status, run_count, last_run_at
    }
}
