import Foundation
func parseValue(_ input: String) -> Int { Int(input) ?? 0 }
func doubleValue(_ value: Int) -> Int { value * 2 }
func renderValue(_ value: Int) -> String { String(value) }
func limitRange(_ input: Int) -> Int { min(100, max(0, input)) }
print(renderValue(doubleValue(parseValue("21"))))
