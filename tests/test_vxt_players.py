"""Conformance: the .vxt writer emits all five observer entries.

the generator-fixes audit, task 4. Historical failure: only the NSDF line,
stranding CCA / Black Dog / Cronian / spectator players with no observer craft
(and, once the craft assets shipped, still limiting vehicle choice).
"""

from bzmap.formats.vxt import STANDARD_OBSERVERS, write_standard_vxt
from bzmap.validate.terrain import check_vxt_players


def test_writer_emits_all_five_entries(tmp_path):
    out = write_standard_vxt(tmp_path / "map.vxt")

    text = out.read_text()
    for craft in ("avobserv", "svobserv", "bvobserv", "cvobserv", "observer"):
        assert craft in text
    assert len(STANDARD_OBSERVERS) == 5


def test_the_historical_single_entry_fails_validation():
    problems = check_vxt_players("avobserv avobserv.des\tx\tNSDF\n")

    missing = "\n".join(problems)
    for craft in ("svobserv", "bvobserv", "cvobserv", "observer"):
        assert craft in missing


def test_the_standard_text_passes(tmp_path):
    out = write_standard_vxt(tmp_path / "map.vxt")

    assert check_vxt_players(out.read_text()) == []
