"""Bounded evaluators for Phase 17 expression practice.

These parsers intentionally implement documented subsets. They never call eval,
execute submitted source, import workbooks, or expose private expected values.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


class ExpressionError(ValueError):
    pass


EXCEL_FUNCTIONS = {
    "SUM", "AVERAGE", "MIN", "MAX", "COUNT", "COUNTA", "IF", "SUMIF", "SUMIFS",
    "COUNTIF", "COUNTIFS", "VLOOKUP", "HLOOKUP", "XLOOKUP", "INDEX", "MATCH", "IFERROR",
    "ABS", "ROUND", "LEN", "LEFT", "RIGHT", "MID", "CONCAT", "UPPER", "LOWER", "TRIM",
    "DATE", "YEAR", "MONTH", "DAY", "AND", "OR", "NOT",
}

_excel_token = re.compile(
    r'\s*(?:(?P<number>\d+(?:\.\d+)?)|(?P<string>"(?:[^"]|"")*")|'
    r'(?P<cell>\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?)|'
    r'(?P<name>[A-Za-z_][A-Za-z0-9_.]*)|(?P<op><>|<=|>=|[+\-*/^&=<>(),]))'
)


def _cell_key(value: str) -> str:
    return value.replace("$", "").upper()


def _column_number(value: str) -> int:
    result = 0
    for character in value:
        result = result * 26 + ord(character.upper()) - 64
    return result


def _column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _range_values(reference: str, cells: dict[str, Any]) -> list[Any]:
    start, end = (_cell_key(part) for part in reference.split(":", 1))
    pattern = re.compile(r"([A-Z]+)(\d+)")
    start_match, end_match = pattern.fullmatch(start), pattern.fullmatch(end)
    if not start_match or not end_match:
        raise ExpressionError("Invalid range reference")
    c1, r1 = _column_number(start_match[1]), int(start_match[2])
    c2, r2 = _column_number(end_match[1]), int(end_match[2])
    if c2 < c1 or r2 < r1 or (c2 - c1 + 1) * (r2 - r1 + 1) > 10_000:
        raise ExpressionError("Range is reversed or exceeds the 10,000-cell limit")
    return [cells.get(f"{_column_name(column)}{row}") for row in range(r1, r2 + 1) for column in range(c1, c2 + 1)]


@dataclass
class ExcelParser:
    formula: str
    cells: dict[str, Any]

    def __post_init__(self):
        source = self.formula.strip()
        if not source.startswith("="):
            raise ExpressionError("Excel formulas must start with =")
        if len(source) > 2_000:
            raise ExpressionError("Formula exceeds the 2,000-character limit")
        self.tokens: list[tuple[str, str]] = []
        position = 1
        while position < len(source):
            match = _excel_token.match(source, position)
            if not match:
                raise ExpressionError(f"Unsupported token near character {position + 1}")
            kind = next(key for key, value in match.groupdict().items() if value is not None)
            self.tokens.append((kind, match.group(kind)))
            position = match.end()
        self.position = 0
        self.cells = {_cell_key(key): value for key, value in self.cells.items()}

    def parse(self) -> Any:
        value = self.comparison()
        if self.position != len(self.tokens):
            raise ExpressionError("Unexpected content after formula")
        return value

    def peek(self, value: str | None = None) -> bool:
        if self.position >= len(self.tokens):
            return False
        return value is None or self.tokens[self.position][1].upper() == value

    def take(self, value: str | None = None) -> tuple[str, str]:
        if not self.peek(value):
            raise ExpressionError(f"Expected {value or 'expression'}")
        token = self.tokens[self.position]
        self.position += 1
        return token

    def comparison(self) -> Any:
        left = self.concat()
        while self.peek() and self.tokens[self.position][1] in {"=", "<>", "<", ">", "<=", ">="}:
            operator = self.take()[1]
            right = self.concat()
            left = {"=": left == right, "<>": left != right, "<": left < right, ">": left > right,
                    "<=": left <= right, ">=": left >= right}[operator]
        return left

    def concat(self) -> Any:
        value = self.term()
        while self.peek("&"):
            self.take("&")
            value = f"{value}{self.term()}"
        return value

    def term(self) -> Any:
        value = self.factor()
        while self.peek() and self.tokens[self.position][1] in {"+", "-"}:
            operator = self.take()[1]
            right = self.factor()
            value = _number(value) + _number(right) if operator == "+" else _number(value) - _number(right)
        return value

    def factor(self) -> Any:
        value = self.power()
        while self.peek() and self.tokens[self.position][1] in {"*", "/"}:
            operator = self.take()[1]
            right = _number(self.power())
            if operator == "/" and right == 0:
                raise ExpressionError("Division by zero")
            value = _number(value) * right if operator == "*" else _number(value) / right
        return value

    def power(self) -> Any:
        value = self.atom()
        if self.peek("^"):
            self.take("^")
            value = _number(value) ** _number(self.power())
        return value

    def atom(self) -> Any:
        if self.peek("+") or self.peek("-"):
            sign = self.take()[1]
            value = _number(self.atom())
            return value if sign == "+" else -value
        kind, value = self.take()
        if kind == "number":
            return float(value) if "." in value else int(value)
        if kind == "string":
            return value[1:-1].replace('""', '"')
        if kind == "cell":
            return _range_values(value, self.cells) if ":" in value else self.cells.get(_cell_key(value))
        if value == "(":
            result = self.comparison()
            self.take(")")
            return result
        if kind == "name":
            name = value.upper()
            if name in {"TRUE", "FALSE"}:
                return name == "TRUE"
            if not self.peek("("):
                raise ExpressionError(f"Unknown name {value}")
            if name not in EXCEL_FUNCTIONS:
                raise ExpressionError(f"Unsupported Excel function {name}")
            self.take("(")
            arguments: list[Any] = []
            if not self.peek(")"):
                while True:
                    try:
                        arguments.append(self.comparison())
                    except ExpressionError as error:
                        if name != "IFERROR":
                            raise
                        arguments.append(error)
                    if not self.peek(","):
                        break
                    self.take(",")
            self.take(")")
            return _excel_function(name, arguments)
        raise ExpressionError(f"Unexpected token {value}")


def _flatten(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        result.extend(value if isinstance(value, list) else [value])
    return result


def _number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ExpressionError(f"{value!r} is not numeric") from error


def _matches(value: Any, criterion: Any) -> bool:
    if not isinstance(criterion, str):
        return value == criterion
    match = re.fullmatch(r"(<=|>=|<>|=|<|>)?(.*)", criterion)
    assert match
    operator, expected = match.group(1) or "=", match.group(2)
    try:
        actual_value, expected_value = float(value), float(expected)
    except (TypeError, ValueError):
        actual_value, expected_value = str(value), expected
    return {"=": actual_value == expected_value, "<>": actual_value != expected_value,
            "<": actual_value < expected_value, ">": actual_value > expected_value,
            "<=": actual_value <= expected_value, ">=": actual_value >= expected_value}[operator]


def _excel_function(name: str, arguments: list[Any]) -> Any:
    values = _flatten(arguments)
    numeric = [_number(value) for value in values if value not in (None, "") and not isinstance(value, str) or isinstance(value, str) and _is_number(value)]
    if name == "SUM": return sum(numeric)
    if name == "AVERAGE": return sum(numeric) / len(numeric) if numeric else 0
    if name == "MIN": return min(numeric) if numeric else 0
    if name == "MAX": return max(numeric) if numeric else 0
    if name == "COUNT": return len(numeric)
    if name == "COUNTA": return sum(value not in (None, "") for value in values)
    if name == "IF":
        if len(arguments) not in {2, 3}: raise ExpressionError("IF expects two or three arguments")
        return arguments[1] if bool(arguments[0]) else (arguments[2] if len(arguments) == 3 else False)
    if name in {"SUMIF", "COUNTIF"}:
        if len(arguments) not in {2, 3}: raise ExpressionError(f"{name} expects two or three arguments")
        criteria_range = _flatten([arguments[0]])
        selected = [index for index, value in enumerate(criteria_range) if _matches(value, arguments[1])]
        if name == "COUNTIF": return len(selected)
        sum_range = _flatten([arguments[2] if len(arguments) == 3 else arguments[0]])
        return sum(_number(sum_range[index]) for index in selected if index < len(sum_range))
    if name in {"SUMIFS", "COUNTIFS"}:
        sum_range = _flatten([arguments[0]]) if name == "SUMIFS" else None
        pairs = arguments[1:] if name == "SUMIFS" else arguments
        if len(pairs) < 2 or len(pairs) % 2: raise ExpressionError(f"{name} expects range/criteria pairs")
        ranges = [_flatten([pairs[index]]) for index in range(0, len(pairs), 2)]
        length = min(map(len, ranges))
        selected = [index for index in range(length) if all(_matches(ranges[pair][index], pairs[pair * 2 + 1]) for pair in range(len(ranges)))]
        return len(selected) if name == "COUNTIFS" else sum(_number(sum_range[index]) for index in selected if sum_range and index < len(sum_range))
    if name == "IFERROR":
        if len(arguments) != 2: raise ExpressionError("IFERROR expects two arguments")
        return arguments[1] if isinstance(arguments[0], ExpressionError) else arguments[0]
    if name == "ABS": return abs(_number(_one(name, arguments)))
    if name == "ROUND": return round(_number(arguments[0]), int(_number(arguments[1])))
    if name == "LEN": return len(str(_one(name, arguments)))
    if name in {"UPPER", "LOWER", "TRIM"}:
        text = str(_one(name, arguments))
        return text.upper() if name == "UPPER" else text.lower() if name == "LOWER" else text.strip()
    if name in {"LEFT", "RIGHT"}:
        text, length = str(arguments[0]), int(_number(arguments[1] if len(arguments) > 1 else 1))
        return text[:length] if name == "LEFT" else text[-length:]
    if name == "MID": return str(arguments[0])[int(_number(arguments[1])) - 1:int(_number(arguments[1])) - 1 + int(_number(arguments[2]))]
    if name == "CONCAT": return "".join(str(value) for value in values)
    if name == "AND": return all(map(bool, values))
    if name == "OR": return any(map(bool, values))
    if name == "NOT": return not bool(_one(name, arguments))
    if name == "DATE": return date(int(_number(arguments[0])), int(_number(arguments[1])), int(_number(arguments[2]))).isoformat()
    if name in {"YEAR", "MONTH", "DAY"}:
        value = datetime.fromisoformat(str(_one(name, arguments))).date()
        return {"YEAR": value.year, "MONTH": value.month, "DAY": value.day}[name]
    if name == "MATCH":
        needle, haystack = arguments[0], _flatten([arguments[1]])
        try: return haystack.index(needle) + 1
        except ValueError as error: raise ExpressionError("MATCH did not find a value") from error
    if name == "INDEX":
        matrix, row = arguments[0], int(_number(arguments[1]))
        flat = _flatten([matrix])
        if row < 1 or row > len(flat): raise ExpressionError("INDEX row is out of range")
        return flat[row - 1]
    if name == "XLOOKUP":
        needle, lookup, results = arguments[0], _flatten([arguments[1]]), _flatten([arguments[2]])
        try: index = lookup.index(needle)
        except ValueError:
            if len(arguments) > 3: return arguments[3]
            raise ExpressionError("XLOOKUP did not find a value")
        return results[index]
    if name in {"VLOOKUP", "HLOOKUP"}:
        raise ExpressionError(f"{name} requires a two-dimensional workbook range and is accepted only in workbook grading")
    raise ExpressionError(f"Unsupported Excel function {name}")


def _one(name: str, arguments: list[Any]) -> Any:
    if len(arguments) != 1: raise ExpressionError(f"{name} expects one argument")
    return arguments[0]


def _is_number(value: str) -> bool:
    try: float(value); return True
    except ValueError: return False


def evaluate_excel(formula: str, cells: dict[str, Any]) -> Any:
    return ExcelParser(formula, cells).parse()


TABLEAU_FUNCTIONS = {
    "SUM", "AVG", "MIN", "MAX", "COUNT", "COUNTD", "IF", "THEN", "ELSEIF", "ELSE", "END", "CASE", "WHEN",
    "ISNULL", "IFNULL", "ZN", "STR", "INT", "FLOAT", "DATE", "DATETRUNC", "DATEDIFF",
    "UPPER", "LOWER", "TRIM", "LEN", "CONTAINS", "STARTSWITH", "ENDSWITH",
    "RUNNING_SUM", "WINDOW_SUM", "WINDOW_AVG", "RANK", "LOOKUP", "INDEX", "FIRST", "LAST",
    "FIXED", "INCLUDE", "EXCLUDE", "AND", "OR", "NOT",
}


def validate_tableau(expression: str, fields: list[str]) -> dict[str, Any]:
    if not expression.strip() or len(expression) > 2_000:
        raise ExpressionError("Expression is empty or exceeds 2,000 characters")
    if re.search(r"[^A-Za-z0-9_\s\[\]{}():,.'\"+*/%<>=!-]", expression):
        raise ExpressionError("Expression contains an unsupported token")
    referenced = re.findall(r"\[([^\]]+)\]", expression)
    unknown = sorted(set(referenced) - set(fields))
    if unknown:
        raise ExpressionError(f"Unknown field(s): {', '.join(unknown)}")
    words = re.findall(r"\b([A-Z][A-Z_]*)\s*\(", expression.upper())
    unsupported = sorted(set(words) - TABLEAU_FUNCTIONS)
    if unsupported:
        raise ExpressionError(f"Unsupported Tableau function(s): {', '.join(unsupported)}")
    if expression.count("(") != expression.count(")") or expression.count("{") != expression.count("}"):
        raise ExpressionError("Parentheses or LOD braces are unbalanced")
    return {"valid": True, "fields": referenced, "functions": sorted(set(words))}


def evaluate_tableau(expression: str, rows: list[dict[str, Any]], fields: list[str] | None = None,
                     partition_by: list[str] | None = None, order_by: str | None = None) -> Any:
    fields = fields or sorted({key for row in rows for key in row})
    validate_tableau(expression, fields)
    partition_by = partition_by or []
    unknown_context = sorted((set(partition_by) | ({order_by} if order_by else set())) - set(fields))
    if unknown_context: raise ExpressionError(f"Unknown partition/order field(s): {', '.join(unknown_context)}")
    source = " ".join(expression.strip().split())
    lod = re.fullmatch(r"\{\s*FIXED\s+(.+?)\s*:\s*(SUM|AVG|MIN|MAX)\s*\(\s*\[([^]]+)]\s*\)\s*}", source, re.I)
    if lod:
        dimensions = re.findall(r"\[([^]]+)]", lod.group(1))
        if not dimensions: raise ExpressionError("FIXED requires at least one dimension")
        groups: dict[tuple[Any, ...], list[float]] = {}
        for row in rows:
            groups.setdefault(tuple(row.get(item) for item in dimensions), []).append(_number(row.get(lod.group(3))))
        return {"|".join(map(str, key)): _aggregate(lod.group(2), values) for key, values in groups.items()}
    running = re.fullmatch(r"RUNNING_SUM\s*\(\s*SUM\s*\(\s*\[([^]]+)]\s*\)\s*\)", source, re.I)
    if running:
        ordered_rows = sorted(rows, key=lambda row: tuple(str(row.get(field)) for field in partition_by) + ((str(row.get(order_by)),) if order_by else ()))
        totals: dict[tuple[Any, ...], float] = {}; result = []
        for row in ordered_rows:
            partition = tuple(row.get(field) for field in partition_by)
            totals[partition] = totals.get(partition, 0) + _number(row.get(running.group(1)))
            result.append(totals[partition])
        return result
    window = re.fullmatch(r"WINDOW_(SUM|AVG)\s*\(\s*SUM\s*\(\s*\[([^]]+)]\s*\)\s*\)", source, re.I)
    if window:
        partitions: dict[tuple[Any, ...], list[float]] = {}
        for row in rows: partitions.setdefault(tuple(row.get(field) for field in partition_by), []).append(_number(row.get(window.group(2))))
        aggregates = {key: sum(values) if window.group(1).upper() == "SUM" else sum(values) / len(values) for key, values in partitions.items()}
        return [aggregates[tuple(row.get(field) for field in partition_by)] for row in rows]
    ratio = re.fullmatch(r"(SUM|AVG|MIN|MAX)\s*\(\s*\[([^]]+)]\s*\)\s*([+*/-])\s*(SUM|AVG|MIN|MAX)\s*\(\s*\[([^]]+)]\s*\)", source, re.I)
    if ratio:
        left = _aggregate(ratio.group(1), [_number(row.get(ratio.group(2))) for row in rows])
        right = _aggregate(ratio.group(4), [_number(row.get(ratio.group(5))) for row in rows])
        if ratio.group(3) == "/" and right == 0: raise ExpressionError("Division by zero")
        return {"+": left + right, "-": left - right, "*": left * right, "/": left / right}[ratio.group(3)]
    aggregate = re.fullmatch(r"(SUM|AVG|MIN|MAX|COUNT|COUNTD)\s*\(\s*\[([^]]+)]\s*\)", source, re.I)
    if aggregate:
        values = [row.get(aggregate.group(2)) for row in rows]
        return _aggregate(aggregate.group(1), values)
    raise ExpressionError("This valid expression requires Tableau runtime semantics outside the supported grader subset")


def _aggregate(name: str, values: list[Any]) -> Any:
    name = name.upper()
    present = [value for value in values if value is not None]
    if name == "COUNT": return len(present)
    if name == "COUNTD": return len(set(present))
    numeric = [_number(value) for value in present]
    if name == "SUM": return sum(numeric)
    if name == "AVG": return sum(numeric) / len(numeric) if numeric else 0
    if name == "MIN": return min(numeric) if numeric else None
    if name == "MAX": return max(numeric) if numeric else None
    raise ExpressionError(f"Unsupported aggregate {name}")


def equivalent(actual: Any, expected: Any, tolerance: float = 1e-9) -> bool:
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=tolerance, abs_tol=tolerance)
    return actual == expected
