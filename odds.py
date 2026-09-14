# Analysis Football Bot — Myanmar Odds
# User-facing format: 2.5 | L-100, -0.5 | L-100

ASIAN_TO_MYANMAR = {
    0.00: "D",
    0.25: "L-50",
    0.50: "L-100",
    0.75: "1+50",
    1.00: "1D",
    1.25: "1-50",
    1.50: "1-100",
    1.75: "2+50",
    2.00: "2D",
    2.25: "2-50",
    2.50: "2-100",
    2.75: "3+50",
    3.00: "3D",
    3.25: "3-50",
    3.50: "3-100",
    3.75: "4+50",
    4.00: "4D",
    4.25: "4-50",
    4.50: "4-100",
    5.00: "5D",
}


def _normalize_line(line):
    if isinstance(line, str):
        line = line.strip().replace("+", "")
        try:
            return float(line)
        except ValueError:
            return None
    if isinstance(line, (int, float)):
        return float(line)
    return None


def asian_to_myanmar(line):
    """Convert a supported Asian quarter/half/full line to Myanmar notation."""
    value = _normalize_line(line)
    if value is None:
        raise ValueError("Invalid Asian line.")

    if value not in ASIAN_TO_MYANMAR:
        raise ValueError(f"Unsupported Asian line: {line}")

    return ASIAN_TO_MYANMAR[value]


def display_line(line):
    """Return the compact user-facing format: Asian line | Myanmar odds."""
    value = _normalize_line(line)
    if value is None:
        raise ValueError("Invalid Asian line.")

    if value.is_integer():
        line_text = str(int(value))
    else:
        line_text = str(value).rstrip("0").rstrip(".")

    return f"{line_text} | {asian_to_myanmar(value)}"
