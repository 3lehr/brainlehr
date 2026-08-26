def parse_value(input_value: str) -> int:
    return int(input_value)
def double_value(value: int) -> int:
    return value * 2
def render_value(value: int) -> str:
    return str(value)
print(render_value(double_value(parse_value("21"))))
