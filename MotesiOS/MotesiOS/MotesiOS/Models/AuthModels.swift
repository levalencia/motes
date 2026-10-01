import Foundation

struct LoginRequest: Codable {
    let username: String
    let password: String
}

struct TokenResponse: Codable {
    let token: String
    let user_id: String
    let username: String
}
