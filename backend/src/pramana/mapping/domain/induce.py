"""
mapping.domain.induce — Deterministic mapping specification induction (§6.1).

R3: No framework in domain/.
R7: baseline.mapping_spec is pure: stdlib + pydantic only.
"""
from __future__ import annotations

import re
from pramana.baseline.api import MappingSpec, SlotType, Token
from pramana.shared_kernel.api import sha256_bytes

_IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_INT_RE = re.compile(r"^\d+$")


def induce_spec(line_bytes: bytes, target_setting_id: str, vendor_id: str) -> MappingSpec:
    """
    Deterministically induce a MappingSpec from a line of configuration syntax.
    
    Identifies variable values (integers, IP addresses, quoted strings) as typed slots,
    and command keywords as literals. Generates a reproducible dialect_fingerprint.
    """
    try:
        line_str = line_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        line_str = line_bytes.decode("latin-1").strip()

    tokens_raw = line_str.split()
    pattern_tokens: list[Token] = []
    skeleton_parts: list[str] = []

    slot_counter = 1
    for tok in tokens_raw:
        if _INT_RE.match(tok):
            slot_name = f"slot_{slot_counter}"
            slot_counter += 1
            pattern_tokens.append(Token(is_slot=True, slot_name=slot_name, slot_type=SlotType.INT))
            skeleton_parts.append("<INT>")
        elif _IP_RE.match(tok):
            slot_name = f"slot_{slot_counter}"
            slot_counter += 1
            pattern_tokens.append(Token(is_slot=True, slot_name=slot_name, slot_type=SlotType.IP))
            skeleton_parts.append("<IP>")
        elif (tok.startswith('"') and tok.endswith('"')) or (tok.startswith("'") and tok.endswith("'")):
            slot_name = f"slot_{slot_counter}"
            slot_counter += 1
            pattern_tokens.append(Token(is_slot=True, slot_name=slot_name, slot_type=SlotType.QUOTED))
            skeleton_parts.append("<QUOTED>")
        else:
            pattern_tokens.append(Token(literal=tok, is_slot=False))
            skeleton_parts.append(tok.lower())

    skeleton = f"{vendor_id}:" + " ".join(skeleton_parts)
    dialect_fingerprint = sha256_bytes(skeleton.encode("utf-8"))

    # Render template using slot names
    template_parts: list[str] = []
    for tok in pattern_tokens:
        if not tok.is_slot:
            template_parts.append(tok.literal)
        else:
            template_parts.append(f"{{{tok.slot_name}}}")

    render_template = " ".join(template_parts)

    return MappingSpec(
        vendor_id=vendor_id,
        dialect_fingerprint=dialect_fingerprint,
        pattern=tuple(pattern_tokens),
        target_setting_id=target_setting_id,
        render_template=render_template,
    )
