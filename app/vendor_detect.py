import re

# Ordered most-specific-first: Arista/Fortinet/Palo Alto/Juniper are checked
# before the generic Cisco IOS fallback, since Arista's syntax is otherwise
# nearly identical to Cisco's and would be misdetected if checked last.
VENDOR_SIGNATURES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("arista", ("arista",), (r"! device:.*eos", r"\barista\b")),
    ("fortinet", ("fortinet", "forti"), (r"#config-version=", r"^config system global")),
    ("paloalto", ("paloalto", "panos", "pan-os"), (r"set deviceconfig system", r"set mgt-config")),
    ("juniper", ("juniper", "junos"), (r"## last commit", r"^set system host-name")),
    ("cisco", ("cisco", "ios"), (r"building configuration", r"^version \d+\.\d+")),
)


def detect_vendor(filename: str, text: str) -> str:
    """Detect vendor from filename hints, falling back to content signatures
    in the first N lines. Returns "unknown" if nothing matches."""
    name = filename.lower()
    for vendor, filename_hints, _content_patterns in VENDOR_SIGNATURES:
        if any(hint in name for hint in filename_hints):
            return vendor

    head = "\n".join(text.splitlines()[:40]).lower()
    for vendor, _filename_hints, content_patterns in VENDOR_SIGNATURES:
        if any(re.search(pattern, head, re.MULTILINE) for pattern in content_patterns):
            return vendor

    return "unknown"
