import re


def fts_query(text: str) -> str:
    if not text or not text.strip():
        return "1"

    raw = text.strip()

    raw = raw.replace('"', '""')

    escaped = re.sub(r'([*?()\[\]:^])', r'"\1"', raw)

    tokens = escaped.split()
    processed_tokens = []
    for token in tokens:
        if token.endswith("*"):
            processed_tokens.append(f'"{token[:-1]}"*')
        else:
            processed_tokens.append(f'"{token}"*')

    return " OR ".join(processed_tokens)
