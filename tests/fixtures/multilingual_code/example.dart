int parseValue(String input) => int.tryParse(input) ?? 0;
int doubleValue(int value) => value * 2;
String renderValue(int value) => value.toString();
int limitRange(int input) => input < 0 ? 0 : (input > 100 ? 100 : input);
void main() { print(renderValue(doubleValue(parseValue('21')))); }
