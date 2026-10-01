import Foundation

@Observable
class ServicesViewModel {
    var catalog: [CatalogEntry] = []
    var serviceStatuses: [String: Bool] = [:]
    var isLoading = true
    var error: String?
    var successMessage: String?

    func loadData() async {
        do { catalog = try await APIClient.shared.get("/api/mcp/catalog") } catch {}
        do {
            let statuses: [ServiceKeyStatus] = try await APIClient.shared.get("/api/service-keys")
            for s in statuses { serviceStatuses[s.service] = s.configured }
        } catch {}
        isLoading = false
    }

    func saveKey(service: String, keys: [String: String]) async {
        do {
            let _: [String: String] = try await APIClient.shared.post("/api/service-keys", body: ServiceKeyRequest(service: service, keys: keys))
            serviceStatuses[service] = true
            successMessage = "✅ Connected!"
        } catch {
            self.error = "Failed to save"
        }
    }

    func disconnect(service: String) async {
        try? await APIClient.shared.delete("/api/service-keys/\(service)")
        serviceStatuses[service] = false
    }
}
