fn parse_value(input: &str) -> i32 { input.parse().unwrap_or(0) }
fn double_value(value: i32) -> i32 { value * 2 }
fn render_value(value: i32) -> String { value.to_string() }
fn main() { println!("{}", render_value(double_value(parse_value("21")))); }
