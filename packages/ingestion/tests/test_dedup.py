from argus_ingestion.dedup import SimHashDedup


def test_near_duplicate_detected_and_unrelated_not():
    dedup = SimHashDedup()
    original = (
        "The central bank announced a quarter-point rate hike on Tuesday, "
        "citing persistent inflation pressures across the housing and energy sectors. "
        "Officials emphasized that further tightening remains on the table for the coming quarter."
    )
    near_dup = (
        "The central bank announced a quarter-point rate hike Tuesday, "
        "citing persistent inflation pressure across housing and energy sectors. "
        "Officials emphasized further tightening remains on the table for the coming quarter."
    )
    unrelated = (
        "A new species of deep-sea octopus was discovered off the coast of Costa Rica, "
        "with researchers documenting unusual nesting behavior near hydrothermal vents."
    )

    dedup.add("hash-original", original)

    assert dedup.is_near_duplicate(near_dup) is True
    assert dedup.is_near_duplicate(unrelated) is False
