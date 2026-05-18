import pytest

from slurm_client.rest_api import resources


@pytest.mark.parametrize(
    ["spec", "expected"],
    (
        pytest.param(
            "cpu=128,mem=2043570M", {"cpu": "128", "memory": "2043570M"}, id="tres"
        ),
        pytest.param(
            "cpu=12,mem=96000M", {"cpu": "12", "memory": "96000M"}, id="tres_used"
        ),
    ),
)
def test_parse_resource_spec(spec, expected):
    actual = resources.parse_resource_spec(spec)
    assert actual == expected
