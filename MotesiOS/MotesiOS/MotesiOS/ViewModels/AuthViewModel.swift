import Foundation

@Observable
class AuthViewModel {
    // Hardcoded for dev/testing — remove before release
    var username = "luis"
    var password = "Motes2025!"
    var serverURL: String {
        get {
            let saved = APIClient.shared.baseURL
            if saved == "http://localhost:8001" {
                APIClient.shared.baseURL = "https://luiss-macbook-pro.tailf19efd.ts.net:8001"
                return "https://luiss-macbook-pro.tailf19efd.ts.net:8001"
            }
            return saved
        }
        set { APIClient.shared.baseURL = newValue }
    }
    var isLoading = false
    var error: String?
    var isLoggedIn: Bool

    init() {
        let savedURL = UserDefaults.standard.string(forKey: "motes_server_url") ?? ""
        if savedURL.isEmpty || !savedURL.hasPrefix("https://") {
            AuthService.logout()
            UserDefaults.standard.removeObject(forKey: "motes_server_url")
            isLoggedIn = false
        } else {
            isLoggedIn = AuthService.isLoggedIn
        }
    }

    func login() async {
        isLoading = true
        error = nil
        do {
            _ = try await AuthService.login(username: username.lowercased(), password: password)
            isLoggedIn = true
        } catch {
            self.error = "\(error.localizedDescription)"
        }
        isLoading = false
    }

    func logout() {
        AuthService.logout()
        isLoggedIn = false
    }
}
