def parse_floats(values: list[str]) -> list[float]:
    result = []
    for v in values:
        try:
            result.append(float(v))
        except (ValueError, TypeError):
            pass
    return result


def is_float(v: str) -> bool:
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def format_change(current_val: str, prev_val: str) -> str:
    try:
        curr = float(current_val)
        prev = float(prev_val)
    except (ValueError, TypeError):
        return "[dim]—[/dim]"
    diff = curr - prev
    if diff > 0:
        return f"[green]▲ +{diff:.2f}[/green]"
    elif diff < 0:
        return f"[red]▼ {diff:.2f}[/red]"
    else:
        return "[dim]— 0.00[/dim]"
