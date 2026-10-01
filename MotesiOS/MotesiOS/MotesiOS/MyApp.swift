import SwiftUI

@main
struct MotesApp: App {
    @State private var authVM = AuthViewModel()

    var body: some Scene {
        WindowGroup {
            if authVM.isLoggedIn {
                TabBarView(authVM: authVM)
            } else {
                LoginView(vm: authVM)
            }
        }
    }
}
