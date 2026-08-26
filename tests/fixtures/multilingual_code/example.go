package main
import "fmt"
func parseValue(input string) int { var value int; fmt.Sscanf(input, "%d", &value); return value }
func doubleValue(value int) int { return value * 2 }
func renderValue(value int) string { return fmt.Sprint(value) }
func limitRange(input int) int { if input < 0 { return 0 }; if input > 100 { return 100 }; return input }
func main() { fmt.Println(renderValue(doubleValue(parseValue("21")))) }
