"""
baseline.domain.mapping_spec — Pure domain representation of mapping specifications (§6.1).

R7: baseline.mapping_spec is pure: stdlib + pydantic only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SlotType(str, Enum):
    INT = "int"
    IP = "ip"
    CIDR = "cidr"
    IDENT = "ident"
    WORD = "word"
    QUOTED = "quoted"
    REST = "rest"


Fragment = dict[str, Any]


_SLOT_PATTERNS: dict[SlotType, re.Pattern[str]] = {
    SlotType.INT: re.compile(r"^\d+$"),
    SlotType.IP: re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    SlotType.CIDR: re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$"),
    SlotType.IDENT: re.compile(r"^[A-Za-z0-9_.-]+$"),
    SlotType.WORD: re.compile(r"^\S+$"),
    SlotType.QUOTED: re.compile(r'^(".*"|\'.*\')$'),
    SlotType.REST: re.compile(r"^.*$"),
}


@dataclass(frozen=True)
class Token:
    """Either a literal token or a typed extraction slot."""
    literal: str = ""
    is_slot: bool = False
    slot_name: str = ""
    slot_type: SlotType = SlotType.WORD


@dataclass(frozen=True)
class MappingSpec:
    """
    Pure specification defining how to match and render a syntax pattern (§6.1).
    """
    vendor_id: str
    dialect_fingerprint: str
    pattern: tuple[Token, ...]
    target_setting_id: str
    value_bindings: dict[str, Any] = field(default_factory=dict)
    render_template: str = ""


def match(spec: MappingSpec, line_bytes: bytes) -> dict[str, Any] | None:
    """
    Match line_bytes against spec.pattern.
    Returns extracted slot values dict if matches, or None if no match.
    """
    try:
        line_str = line_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        line_str = line_bytes.decode("latin-1").strip()

    if not line_str:
        return None

    # Check for rest slot at end
    has_rest = any(t.is_slot and t.slot_type == SlotType.REST for t in spec.pattern)

    tokens = line_str.split()
    if not has_rest:
        if len(tokens) != len(spec.pattern):
            return None
    elif len(tokens) < len(spec.pattern):
        return None

    bindings: dict[str, Any] = {}

    for i, pat_tok in enumerate(spec.pattern):
        if pat_tok.is_slot and pat_tok.slot_type == SlotType.REST:
            rest_val = " ".join(tokens[i:])
            bindings[pat_tok.slot_name] = rest_val
            return bindings

        curr_token = tokens[i]
        if not pat_tok.is_slot:
            if curr_token.lower() != pat_tok.literal.lower():
                return None
        else:
            matcher = _SLOT_PATTERNS.get(pat_tok.slot_type, _SLOT_PATTERNS[SlotType.WORD])
            if not matcher.match(curr_token):
                return None

            val: Any = curr_token
            if pat_tok.slot_type == SlotType.INT:
                val = int(curr_token)
            elif pat_tok.slot_type == SlotType.QUOTED and len(curr_token) >= 2:
                if (curr_token.startswith('"') and curr_token.endswith('"')) or \
                   (curr_token.startswith("'") and curr_token.endswith("'")):
                    val = curr_token[1:-1]

            bindings[pat_tok.slot_name] = val

    return bindings


def render(spec: MappingSpec, fragment: dict[str, Any]) -> bytes:
    """
    Render fragment back into configuration line bytes.
    """
    if spec.render_template:
        rendered = spec.render_template.format(**fragment)
        return rendered.encode("utf-8")

    # Fallback to reconstructing from pattern tokens
    parts: list[str] = []
    for tok in spec.pattern:
        if not tok.is_slot:
            parts.append(tok.literal)
        else:
            val = fragment.get(tok.slot_name, "")
            parts.append(str(val))

    return " ".join(parts).encode("utf-8")
