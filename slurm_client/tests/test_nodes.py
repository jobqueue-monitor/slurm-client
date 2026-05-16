import pytest

from slurm_client.rest_api import nodes


@pytest.mark.parametrize(
    ["node_string", "expected"],
    (
        pytest.param("c-1,c-2", ["c-1", "c-2"], id="unglobbed"),
        pytest.param(
            "c-1,c-[2,3,4]", ["c-1", "c-2", "c-3", "c-4"], id="partially-globbed"
        ),
        pytest.param("c-[0,1],d-[2,5]", ["c-0", "c-1", "d-2", "d-5"], id="globbed"),
    ),
)
def test_parse_node_list(node_string, expected):
    node_type = {"configured": node_string, "total": len(expected)}
    actual = nodes.parse_node_list(node_type)

    assert actual == expected
