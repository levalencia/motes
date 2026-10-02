import Foundation

struct ScheduledTask: Codable, Identifiable {
    let id: String
    let prompt: String
    let schedule: String
    var enabled: Bool

    enum CodingKeys: String, CodingKey {
        case id, prompt, schedule, enabled
    }
}

struct CreateTaskRequest: Codable {
    let prompt: String
    let schedule: String
}
