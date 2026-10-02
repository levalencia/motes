import Foundation

struct MCPServer: Codable, Identifiable {
    let id: String
    let name: String
    let type: String // "stdio" or "http"
    var command: String?
    var url: String?
    var tool_count: Int?
    var status: String?
}

struct CreateMCPServerRequest: Codable {
    let name: String
    let type: String
    var command: String?
    var url: String?
}

struct MCPTestResult: Codable {
    let success: Bool
    let message: String?
}
