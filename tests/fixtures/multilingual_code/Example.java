class Example {
  static int parseValue(String input) { return Integer.parseInt(input); }
  static int doubleValue(int value) { return value * 2; }
  static String renderValue(int value) { return Integer.toString(value); }
  static int limitRange(int input) { return Math.min(100, Math.max(0, input)); }
  public static void main(String[] args) { System.out.println(renderValue(doubleValue(parseValue("21")))); }
}
