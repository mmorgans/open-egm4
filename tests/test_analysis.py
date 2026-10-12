from src.analysis import FluxCalculator


def test_flux_calculator_returns_slope_r2_and_flux_alias() -> None:
    calc = FluxCalculator(window_size=10)
    for time_s, co2 in [(0, 400), (1, 402), (2, 404), (3, 406)]:
        calc.add_point(time_s, co2)

    result = calc.calculate()

    assert result.n == 4
    assert result.slope == 2.0
    assert result.flux == result.slope
    assert result.r_squared == 1.0
    assert result.std_err == 0.0


def test_flux_calculator_reports_standard_error_for_noisy_series() -> None:
    calc = FluxCalculator(window_size=10)
    for time_s, co2 in [(0, 400), (1, 403), (2, 403), (3, 407), (4, 409)]:
        calc.add_point(time_s, co2)

    result = calc.calculate()

    assert result.n == 5
    assert 0.0 <= result.r_squared <= 1.0
    assert result.std_err > 0


def test_flux_calculator_sliding_window_limits_points() -> None:
    calc = FluxCalculator(window_size=3)
    for time_s, co2 in [(0, 400), (1, 401), (2, 402), (3, 403)]:
        calc.add_point(time_s, co2)

    result = calc.calculate()

    assert result.n == 3
    assert calc.times == [1, 2, 3]
    assert calc.co2 == [401, 402, 403]
