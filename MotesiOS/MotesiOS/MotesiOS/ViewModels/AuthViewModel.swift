import Foundation

@Observable
class AuthViewModel {
    var username = ""
    var password = ""
    var serverURL: String {
        get { APIClient.shared.baseURL }
        set { APIClient.shared.baseURL = newValue }
    }
    var isLoading = false
    var error: String?
    var isLoggedIn: Bool

    init() {
        // If no server URL configured, force login
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
