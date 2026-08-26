int parseValue(String input) => int.tryParse(input) ?? 0;
int doubleValue(int value) => value * 2;
String renderValue(int value) => value.toString();
void main() { print(renderValue(doubleValue(parseValue('21')))); }
