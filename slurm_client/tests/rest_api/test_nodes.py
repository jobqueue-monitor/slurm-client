import json
import pathlib

import pytest

from slurm_client.rest_api.nodes import NodeDetails, parse_node_details

root = pathlib.Path(__file__).parent / "responses"


@pytest.fixture(scope="session")
def nodes():
    path = root / "nodes.json"

    return json.loads(path.read_text())


def test_parse_node_details(nodes) -> None:
    actual = parse_node_details(nodes[0])

    assert isinstance(actual, NodeDetails)
