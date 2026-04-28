from typing import Any

from slurm_client.rest_api.request import request


@request.get("/openapi/v3")
def api_version(api_paths: dict[str, Any]) -> str:
    versions = {
        path.lstrip("/").split("/")[1]
        for path in api_paths["paths"]
        if path.startswith("/slurm")
    }

    return max(versions)
