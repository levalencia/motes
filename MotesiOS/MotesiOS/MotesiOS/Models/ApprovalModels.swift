import Foundation

struct Approval: Codable, Identifiable {
    let id: String
    let action: String
    let description: String
    var status: String // "pending", "approved", "denied"
    let created_at: String?

    var isPending: Bool { status == "pending" }
}

struct ApprovalAction: Codable {
    let status: String
}
