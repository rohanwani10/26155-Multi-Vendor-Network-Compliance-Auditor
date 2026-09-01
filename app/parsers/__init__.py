from app.parsers.arista import normalize_arista
from app.parsers.cisco import normalize_cisco
from app.parsers.fortinet import normalize_fortinet
from app.parsers.ios_style import DECLARED_COVERAGE as IOS_STYLE_COVERAGE
from app.parsers.juniper import DECLARED_COVERAGE as JUNIPER_COVERAGE
from app.parsers.juniper import normalize_juniper
from app.parsers.paloalto import DECLARED_COVERAGE as PALOALTO_COVERAGE
from app.parsers.paloalto import normalize_paloalto
from app.parsers.fortinet import DECLARED_COVERAGE as FORTINET_COVERAGE
from app.parsers.unknown import DECLARED_COVERAGE as UNKNOWN_COVERAGE
from app.parsers.unknown import normalize_unknown

NORMALIZERS = {
    "cisco": normalize_cisco,
    "arista": normalize_arista,
    "juniper": normalize_juniper,
    "paloalto": normalize_paloalto,
    "fortinet": normalize_fortinet,
}

#: Per-vendor declared field coverage (Correction 3). Cisco and Arista share
#: ios_style's adapter and so share its declared coverage.
DECLARED_COVERAGE = {
    "cisco": IOS_STYLE_COVERAGE,
    "arista": IOS_STYLE_COVERAGE,
    "juniper": JUNIPER_COVERAGE,
    "paloalto": PALOALTO_COVERAGE,
    "fortinet": FORTINET_COVERAGE,
    "unknown": UNKNOWN_COVERAGE,
}


def normalize(vendor: str, raw_text: str) -> dict:
    """Tier-1 normalize: raw config text -> vendor-neutral schema dict.
    Falls back to normalize_unknown (everything unrecognized) for any
    vendor we have no Tier-1 normalizer for."""
    normalizer = NORMALIZERS.get(vendor, normalize_unknown)
    return normalizer(raw_text)


def declared_coverage(vendor: str) -> frozenset:
    """This adapter's declared field coverage, or empty for a vendor with
    no adapter at all (falls through to normalize_unknown)."""
    return DECLARED_COVERAGE.get(vendor, UNKNOWN_COVERAGE)
