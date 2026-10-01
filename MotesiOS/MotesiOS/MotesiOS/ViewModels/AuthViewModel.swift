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
    var isLoggedIn: Bool { AuthService.isLoggedIn }

    func login() async {
        isLoading = true
        error = nil
        do {
            _ = try await AuthService.login(username: username, password: password)
        } catch {
            self.error = "Login failed. Check credentials and server URL."
        }
        isLoading = false
    }

    func logout() {
        AuthService.logout()
    }
}
