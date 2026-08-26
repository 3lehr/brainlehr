import Foundation
func parseValue(_ input: String) -> Int { Int(input) ?? 0 }
func doubleValue(_ value: Int) -> Int { value * 2 }
func renderValue(_ value: Int) -> String { String(value) }
print(renderValue(doubleValue(parseValue("21"))))
