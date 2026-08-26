package main
import "fmt"
func parseValue(input string) int { var value int; fmt.Sscanf(input, "%d", &value); return value }
func doubleValue(value int) int { return value * 2 }
func renderValue(value int) string { return fmt.Sprint(value) }
func main() { fmt.Println(renderValue(doubleValue(parseValue("21")))) }
