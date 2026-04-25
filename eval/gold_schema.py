from pydantic import BaseModel

from argus_core.schemas import ClaimStatus


class GoldClaim(BaseModel):
    id: str
    source_url: str
    source_text: str
    statement: str
    expected_status: ClaimStatus
    expected_verbatim_span: str
    expected_char_start: int
    expected_char_end: int
    notes: str = ""
