def format_multiline_text(text: str, font, max_width: int) -> list[str]:
    words = text.split(' ')
    lines = []
    cur_line = ""
    for w in words:
        tested_line = f"{cur_line} {w}".strip()
        if font.size(tested_line)[0] <= max_width:
            cur_line = tested_line
        else:
            if cur_line:
                lines.append(cur_line)
            cur_line = w

    if cur_line:
        lines.append(cur_line)
    return lines
