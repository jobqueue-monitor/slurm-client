import datetime as dt

import pytest

from slurm_client.rest_api.token import Token


class TestToken:
    @pytest.mark.parametrize(
        "valid_until",
        (
            dt.datetime(2026, 5, 20, 21, 0, 0, tzinfo=dt.UTC),
            dt.datetime(2025, 7, 31, 6, 53, 32, tzinfo=dt.UTC),
        ),
    )
    @pytest.mark.parametrize("token", ("abcde", "fghijkl"))
    def test_from_expr(self, token, valid_until):
        actual = Token.from_expr(f"SLURM_JWT={token}", valid_until)

        assert actual.token == token
        assert actual.valid_until == valid_until

    def test_from_expr_failing(self):
        with pytest.raises(ValueError):
            Token.from_expr("abcde", dt.datetime(2026, 5, 20))

    @pytest.mark.parametrize(
        "now",
        (
            dt.datetime(2026, 5, 20, 21, 10, 54, tzinfo=dt.UTC),
            dt.datetime(2026, 5, 20, 22, 10, 0, tzinfo=dt.UTC),
        ),
    )
    def test_is_valid(self, monkeypatch, now):
        class DateTime:
            @classmethod
            def now(self, tz=None):
                return now

        valid_until = dt.datetime(2026, 5, 20, 21, 15, 0, tzinfo=dt.UTC)
        monkeypatch.setattr(dt, "datetime", DateTime)

        token = Token("abcdef", valid_until)

        actual = token.is_valid()
        expected = valid_until >= now

        assert actual == expected

    def test_str(self):
        token = Token("abcdef", dt.datetime(2025, 7, 5, 0, 0, 0, tzinfo=dt.UTC))

        assert str(token) == token.token
