from slurm_client.rest_api.api_version import api_version


def test_api_version():
    assert api_version.path == "/openapi/v3"

    response = {
        "paths": dict.fromkeys(
            [
                "/slurm/v0.0.41/nodes",
                "/slurm/v0.0.44/nodes",
                "/slurmdb/v0.0.41/jobs",
                "/slurmdb/v0.0.44/jobs",
            ]
        )
    }

    expected = "v0.0.44"
    actual = api_version.response_parser(response)

    assert actual == expected
