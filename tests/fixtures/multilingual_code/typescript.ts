function parseValue(input: string): number { return Number(input); }
function doubleValue(value: number): number { return value * 2; }
function renderValue(value: number): string { return String(value); }
const result = renderValue(doubleValue(parseValue("21")));
console.log(result);
