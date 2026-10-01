import Foundation

struct CatalogEntry: Codable, Identifiable {
    var id: String { name }
    let name: String
    let description: String
    let category: String
    var built_in: Bool?
    var requires_oauth: Bool?
    var macos_only: Bool?
    var env_vars: [String]?
    var coming_soon: Bool?
}

struct ServiceKeyStatus: Codable {
    let service: String
    let configured: Bool
    let keys: [String]
}

struct ServiceKeyRequest: Codable {
    let service: String
    let keys: [String: String]
}
