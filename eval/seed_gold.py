"""Seed eval/gold.jsonl with hand-curated, source-verified claims.

Each entry's source_text is a verbatim excerpt from the cited URL (fetched
2026-04-25). The verbatim_span is a contiguous substring of source_text;
char offsets are computed via str.find and asserted before write.

Rerun any time:  uv run python -m eval.seed_gold
"""

from __future__ import annotations

from pathlib import Path

from argus_core.schemas import ClaimStatus

from eval.gold_schema import GoldClaim

_ENTRIES: list[GoldClaim] = []


def add(
    *,
    id: str,
    source_url: str,
    source_text: str,
    statement: str,
    verbatim_span: str,
    expected_status: ClaimStatus = ClaimStatus.LIKELY_TRUE,
    notes: str = "",
) -> None:
    start = source_text.find(verbatim_span)
    if start == -1:
        raise ValueError(f"{id}: verbatim_span not found in source_text")
    end = start + len(verbatim_span)
    entry = GoldClaim(
        id=id,
        source_url=source_url,
        source_text=source_text,
        statement=statement,
        expected_status=expected_status,
        expected_verbatim_span=verbatim_span,
        expected_char_start=start,
        expected_char_end=end,
        notes=notes,
    )
    assert source_text[entry.expected_char_start : entry.expected_char_end] == verbatim_span
    _ENTRIES.append(entry)


# === FINANCE — FOMC rate decisions, 2024 ============================================

add(
    id="fin-001",
    source_url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20240131a.htm",
    source_text=(
        "In support of its goals, the Committee decided to maintain the target range "
        "for the federal funds rate at 5-1/4 to 5-1/2 percent."
    ),
    statement=(
        "On January 31, 2024 the FOMC held the federal funds rate target range at "
        "5-1/4 to 5-1/2 percent."
    ),
    verbatim_span="the Committee decided to maintain the target range for the federal funds rate at 5-1/4 to 5-1/2 percent",
    notes="First meeting of 2024; rate hold continues the pause that began July 2023.",
)

add(
    id="fin-002",
    source_url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20240731a.htm",
    source_text=(
        "Recent indicators suggest that economic activity has continued to expand at "
        "a solid pace. Job gains have moderated, and the unemployment rate has moved "
        "up but remains low. Inflation has eased over the past year but remains "
        "somewhat elevated. In recent months, there has been some further progress "
        "toward the Committee's 2 percent inflation objective."
    ),
    statement=(
        "As of July 31, 2024 the FOMC characterized US economic activity as continuing "
        "to expand at a solid pace."
    ),
    verbatim_span="economic activity has continued to expand at a solid pace",
    notes="Hedged macro language; useful as a medium-difficulty extraction case.",
)

add(
    id="fin-003",
    source_url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20240731a.htm",
    source_text=(
        "Recent indicators suggest that economic activity has continued to expand at "
        "a solid pace. Job gains have moderated, and the unemployment rate has moved "
        "up but remains low. Inflation has eased over the past year but remains "
        "somewhat elevated."
    ),
    statement=(
        "As of July 31, 2024 the FOMC stated that inflation had eased over the past "
        "year but remained somewhat elevated."
    ),
    verbatim_span="Inflation has eased over the past year but remains somewhat elevated",
    notes="Two-part claim with internal contrast; tests the extractor on hedged language.",
)

add(
    id="fin-004",
    source_url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20240918a.htm",
    source_text=(
        "In support of its goals, the Committee decided to lower the target range for "
        "the federal funds rate by 1/2 percentage point to 4-3/4 to 5 percent."
    ),
    statement=(
        "On September 18, 2024 the FOMC cut the federal funds rate by 50 basis points "
        "to a target range of 4-3/4 to 5 percent."
    ),
    verbatim_span="the Committee decided to lower the target range for the federal funds rate by 1/2 percentage point to 4-3/4 to 5 percent",
    notes="First rate cut of the 2024 easing cycle; large 50bp move.",
)

add(
    id="fin-005",
    source_url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20241107a.htm",
    source_text=(
        "In support of its goals, the Committee decided to lower the target range for "
        "the federal funds rate by 1/4 percentage point to 4-1/2 to 4-3/4 percent."
    ),
    statement=(
        "On November 7, 2024 the FOMC cut the federal funds rate by 25 basis points "
        "to a target range of 4-1/2 to 4-3/4 percent."
    ),
    verbatim_span="the Committee decided to lower the target range for the federal funds rate by 1/4 percentage point to 4-1/2 to 4-3/4 percent",
    notes="Second cut of 2024 easing cycle.",
)

add(
    id="fin-006",
    source_url="https://www.federalreserve.gov/newsevents/pressreleases/monetary20241218a.htm",
    source_text=(
        "In support of its goals, the Committee decided to lower the target range for "
        "the federal funds rate by 1/4 percentage point to 4-1/4 to 4-1/2 percent."
    ),
    statement=(
        "On December 18, 2024 the FOMC cut the federal funds rate by 25 basis points "
        "to a target range of 4-1/4 to 4-1/2 percent."
    ),
    verbatim_span="the Committee decided to lower the target range for the federal funds rate by 1/4 percentage point to 4-1/4 to 4-1/2 percent",
    notes="Third cut of 2024 easing cycle.",
)


# === CLIMATE — NASA 2024 temperature record ==========================================

add(
    id="cli-001",
    source_url="https://www.nasa.gov/news-release/temperatures-rising-nasa-confirms-2024-warmest-year-on-record/",
    source_text=(
        "Earth's average surface temperature in 2024 was the warmest on record, "
        "according to an analysis led by NASA scientists."
    ),
    statement="NASA confirmed 2024 was the warmest year on record for Earth's average surface temperature.",
    verbatim_span="Earth's average surface temperature in 2024 was the warmest on record",
    notes="Possessive apostrophe in 'Earth's' — extractor must preserve it exactly.",
)

add(
    id="cli-002",
    source_url="https://www.nasa.gov/news-release/temperatures-rising-nasa-confirms-2024-warmest-year-on-record/",
    source_text=(
        "Global temperatures in 2024 were 2.30 degrees Fahrenheit (1.28 degrees "
        "Celsius) above the agency's 20th-century baseline (1951-1980), which tops "
        "the record set in 2023."
    ),
    statement=(
        "Global temperatures in 2024 were 1.28°C above NASA's 1951-1980 20th-century "
        "baseline, beating the 2023 record."
    ),
    verbatim_span="2.30 degrees Fahrenheit (1.28 degrees Celsius) above the agency's 20th-century baseline (1951-1980)",
    notes="Dual-unit figure with parenthetical baseline; tests preservation of nested punctuation.",
)

add(
    id="cli-003",
    source_url="https://www.nasa.gov/news-release/temperatures-rising-nasa-confirms-2024-warmest-year-on-record/",
    source_text=(
        "NASA scientists further estimate Earth in 2024 was about 2.65 degrees "
        "Fahrenheit (1.47 degrees Celsius) warmer than the mid-19th century average "
        "(1850-1900)."
    ),
    statement=(
        "NASA estimated Earth in 2024 was about 1.47°C warmer than the 1850-1900 "
        "pre-industrial average."
    ),
    verbatim_span="about 2.65 degrees Fahrenheit (1.47 degrees Celsius) warmer than the mid-19th century average (1850-1900)",
    notes="Hedged ('about'); approaches the 1.5°C Paris threshold and is policy-relevant.",
)


# === CLIMATE — IPCC AR6 Synthesis Report SPM headlines ==============================

add(
    id="cli-004",
    source_url="https://www.ipcc.ch/report/ar6/syr/resources/spm-headline-statements/",
    source_text=(
        "Human activities, principally through emissions of greenhouse gases, have "
        "unequivocally caused global warming, with global surface temperature reaching "
        "1.1°C above 1850-1900 in 2011-2020."
    ),
    statement=(
        "IPCC AR6 SYR concluded human activities, principally GHG emissions, have "
        "unequivocally caused global warming."
    ),
    verbatim_span="Human activities, principally through emissions of greenhouse gases, have unequivocally caused global warming",
    notes="The 'unequivocally' framing is the key attribution claim; multi-clause sentence.",
)

add(
    id="cli-005",
    source_url="https://www.ipcc.ch/report/ar6/syr/resources/spm-headline-statements/",
    source_text=(
        "Widespread and rapid changes in the atmosphere, ocean, cryosphere and "
        "biosphere have occurred."
    ),
    statement="IPCC AR6 stated widespread and rapid changes have occurred across atmosphere, ocean, cryosphere, and biosphere.",
    verbatim_span="Widespread and rapid changes in the atmosphere, ocean, cryosphere and biosphere have occurred",
    notes="Short, complete IPCC headline; easy extraction case.",
)

add(
    id="cli-006",
    source_url="https://www.ipcc.ch/report/ar6/syr/resources/spm-headline-statements/",
    source_text="Climate change is a threat to human well-being and planetary health.",
    statement="IPCC AR6 stated climate change is a threat to human well-being and planetary health.",
    verbatim_span="Climate change is a threat to human well-being and planetary health",
    notes="Single-sentence headline; simplest extraction baseline case.",
)


# === HEALTH — WHO COVID-19 PHEIC end =================================================

add(
    id="hea-001",
    source_url=(
        "https://www.who.int/news/item/05-05-2023-statement-on-the-fifteenth-meeting-"
        "of-the-international-health-regulations-(2005)-emergency-committee-regarding-"
        "the-coronavirus-disease-(covid-19)-pandemic"
    ),
    source_text=(
        "He determines that COVID-19 is now an established and ongoing health issue "
        "which no longer constitutes a public health emergency of international "
        "concern (PHEIC)."
    ),
    statement=(
        "On May 5, 2023 the WHO Director-General determined COVID-19 no longer "
        "constituted a public health emergency of international concern."
    ),
    verbatim_span="COVID-19 is now an established and ongoing health issue which no longer constitutes a public health emergency of international concern",
    notes="Formal IHR language; tests preservation of long multi-clause health-policy phrasing.",
)


def main() -> int:
    out = Path(__file__).parent / "gold.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for entry in _ENTRIES:
            f.write(entry.model_dump_json() + "\n")

    with out.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            roundtrip = GoldClaim.model_validate_json(line)
            assert (
                roundtrip.source_text[
                    roundtrip.expected_char_start : roundtrip.expected_char_end
                ]
                == roundtrip.expected_verbatim_span
            ), f"line {i} ({roundtrip.id}) failed round-trip offset check"

    print(f"Wrote {len(_ENTRIES)} gold claims to {out}")
    print("All entries round-tripped through GoldClaim and offset assertions held.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
