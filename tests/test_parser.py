from src.egm_interface import EGM4Serial


def _parser() -> EGM4Serial:
    return EGM4Serial()


def _build_type11_record() -> str:
    """Build a synthetic CPY/CFX record that exercises signed SR parsing."""
    chars = ["0"] * 63
    chars[0] = "M"
    chars[1:3] = list("01")      # plot
    chars[3:7] = list("0001")    # record
    chars[7:9] = list("15")      # day
    chars[9:11] = list("01")     # month
    chars[11:13] = list("12")    # hour
    chars[13:15] = list("30")    # minute
    chars[15:20] = list("00420") # co2
    chars[20:25] = list("00050") # h2o
    chars[25:30] = list("00123") # rht 12.3
    chars[30:34] = list("0123")  # par
    chars[34:38] = list("0042")  # evap
    chars[38:42] = list("0234")  # temp 23.4
    chars[42:46] = list("0015")  # dc
    chars[46:50] = list("0123")  # flow 12.3
    chars[50:54] = list("0456")  # sr_mag 4.56
    chars[54] = "2"              # flow_mult
    chars[56:58] = list("-9")    # sr_sign (negative)
    chars[57:61] = list("9876")  # atmp parsed from [-6:-2]
    chars[61:63] = list("11")    # probe_type
    return "".join(chars)


def test_parse_src_record_extracts_expected_fields() -> None:
    parser = _parser()
    line = "R000001180313170042900000000000000000000000000000000000096508"
    parsed = parser._parse_data(line)

    assert parsed["type"] == "R"
    assert parsed["probe_type"] == 8
    assert parsed["co2_ppm"] == 429
    assert parsed["atmp"] == 965
    assert parsed["dt"] == 0
    assert parsed["dc"] == 0


def test_parse_non_src_record_retains_atmp() -> None:
    parser = _parser()
    line = "M080028260113060047600000000000000000000000000000000000099500"
    parsed = parser._parse_data(line)

    assert parsed["type"] == "M"
    assert parsed["probe_type"] == 0
    assert parsed["atmp"] == 995


def test_parse_type11_builds_signed_sr() -> None:
    parser = _parser()
    parsed = parser._parse_data(_build_type11_record())

    assert parsed["probe_type"] == 11
    assert parsed["sr_mag"] == 4.56
    assert parsed["sr"] == -4.56
    assert parsed["atmp"] == 9876


def test_parse_warmup_and_zero_records() -> None:
    parser = _parser()

    warmup = parser._parse_data("W,+54")
    assert warmup["type"] == "W"
    assert warmup["warmup_temp"] == 54.0

    zero = parser._parse_data("Z,+10")
    assert zero["type"] == "Z"
    assert zero["zero_countdown"] == 10.0

    zero_end = parser._parse_data("Z")
    assert zero_end["type"] == "Z_END"
