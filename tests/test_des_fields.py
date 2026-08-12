"""Conformance: human-facing metadata is real, not generator residue.

the generator-fixes audit, task 3. Historical failures: SIZE hardcoded
"Medium" (wrong for 7 of 10 maps), the author line "Map by AI-generated for the
the Expansion Pack", missionName = the raw slug, empty customtags.
"""

import pytest

from bzmap.formats.des import size_band, write_des_text
from bzmap.validate.terrain import check_des_fields


def test_size_band_follows_corpus_majority():
    assert size_band(1280) == "Small"
    assert size_band(2560) == "Small"
    assert size_band(3840) == "Medium"
    assert size_band(5120) == "Large"


def test_author_default_is_skippy_and_grammatical():
    text = write_des_text(
        mission_name="Open Range", world="Elysium", size="Small",
        geysers=6, scrap=146, players=14,
    )
    assert "Made by Skippy" in text
    assert "AI-generated" not in text


def test_the_historical_metadata_fails_validation():
    des = "WORLD: Elysium\tSIZE: Medium\r\nGEYSERS: 6\tSCRAP: 6\r\nPLAYERS: 14\r\n"
    ini = '[DESCRIPTION]\r\nmissionName = "xx01open"\r\ncustomtags = ""\r\n'

    problems = check_des_fields(des, ini, stem="xx01open", width_m=1280)

    text = "\n".join(problems)
    assert "SIZE" in text            # Medium on a 1280 m map
    assert "slug" in text            # missionName == stem
    assert "customtags" in text      # empty


def test_correct_metadata_passes():
    des = "WORLD: Elysium\tSIZE: Small\r\nGEYSERS: 6\tSCRAP: 146\r\nPLAYERS: 14\r\n"
    ini = ('[DESCRIPTION]\r\nmissionName = "Open Range"\r\n'
           'customtags = "strategy, small, elysium"\r\n')

    assert check_des_fields(des, ini, stem="xx01open", width_m=1280) == []
