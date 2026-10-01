import Foundation

enum AuthService {
    static var isLoggedIn: Bool {
        KeychainHelper.readString(key: "motes_token") != nil
    }

    static var username: String {
        UserDefaults.standard.string(forKey: "motes_username") ?? ""
    }

    static func login(username: String, password: String) async throws -> TokenResponse {
        let body = LoginRequest(username: username, password: password)
        let response: TokenResponse = try await APIClient.shared.post("/api/auth/login", body: body)
        KeychainHelper.saveString(key: "motes_token", value: response.token)
        UserDefaults.standard.set(response.username, forKey: "motes_username")
        return response
    }

    static func logout() {
        KeychainHelper.delete(key: "motes_token")
        UserDefaults.standard.removeObject(forKey: "motes_username")
    }
}
