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


@pytest.mark.parametrize(
    ["spec", "expected"],
    (
        pytest.param(
            "gpu:nvidia_h200_nvl:8(S:0-1)",
            [
                {
                    "type": "gpu",
                    "name": "nvidia_h200_nvl",
                    "quantity": 8,
                    "socket_affinity": [0, 1],
                }
            ],
        ),
        pytest.param(
            "gpu:nvidia_h200_nvl:8(IDX:0-7)",
            [
                {
                    "type": "gpu",
                    "name": "nvidia_h200_nvl",
                    "quantity": 8,
                    "index": list(range(8)),
                }
            ],
        ),
        pytest.param(
            "gpu:nvidia_a100-sxm4-80gb:0(IDX:N/A)",
            [
                {
                    "type": "gpu",
                    "name": "nvidia_a100-sxm4-80gb",
                    "quantity": 0,
                    "index": [],
                }
            ],
        ),
        pytest.param("N/A", []),
    ),
)
def test_parse_generic_resource_spec(spec, expected):
    actual = resources.parse_generic_resource_spec(spec)

    assert actual == expected
