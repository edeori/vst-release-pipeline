// Local setup helper. Call "read" only through a process that captures stdout.
import Foundation
import Security
let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: "moth-vst-release-ci", kSecAttrAccount as String: "edeori"]
if CommandLine.arguments.last == "store" {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    _ = try JSONSerialization.jsonObject(with: data)
    let attributes = [kSecValueData as String: data]
    var status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
    if status == errSecItemNotFound {
        var item = query
        item[kSecValueData as String] = data
        status = SecItemAdd(item as CFDictionary, nil)
    }
    guard status == errSecSuccess else { fputs("Keychain save failed: \(status)\n", stderr); exit(1) }
} else if CommandLine.arguments.last == "read" {
    var readQuery = query
    readQuery[kSecReturnData as String] = true
    var result: CFTypeRef?
    let status = SecItemCopyMatching(readQuery as CFDictionary, &result)
    guard status == errSecSuccess, let data = result as? Data else {
        fputs("Shared Apple credentials unavailable in local Keychain: \(status)\n", stderr); exit(1)
    }
    FileHandle.standardOutput.write(data)
} else { fputs("Expected store or read\n", stderr); exit(1) }
