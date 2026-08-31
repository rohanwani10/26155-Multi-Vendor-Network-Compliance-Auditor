from app.parsers import ios_style


def normalize_arista(text: str) -> dict:
    # Arista EOS syntax is IOS-derived and close enough that the same
    # extraction rules apply; kept as a separate module so vendor-specific
    # divergence can be added here later without touching Cisco's path.
    return ios_style.normalize(text)
