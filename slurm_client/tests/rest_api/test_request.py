from slurm_client.rest_api import request


class TestRequest:
    def test_init(self):
        r = request.Request(
            method="get",
            path="/openapi/v3",
            parameters={},
            response_parser=lambda r: "a",
        )

        assert r.method == "get"
        assert r.path == "/openapi/v3"
        assert r.parameters == {}
        assert r.response_parser({}) == "a"

    def test_path_parameters(self):
        r = request.Request(
            method="get",
            path="/slurm/{version}/node/{node_name}",
            parameters={},
            response_parser=lambda r: "a",
        )

        actual = r.path_parameters(node_name="c-1")

        assert actual.path == "/slurm/{version}/node/c-1"

    def test_parser_parameters(self):
        r = request.Request(
            method="get",
            path="/openapi/v3",
            parameters={},
            response_parser=lambda r, c: f"a/{c}",
        )

        actual = r.parser_parameters(c=1)
        assert actual.response_parser({}) == "a/1"


def test_decorator():
    def f(r):  # pragma: no cover
        return "a"

    expected = request.Request(
        method="post", path="/openapi/v3", parameters={}, response_parser=f
    )
    actual = request._decorator(method="post", path="/openapi/v3", parameters={})(f)
    assert actual == expected
    actual = request._decorator(method="post", path="/openapi/v3")(f)
    assert actual == expected

    expected = request.Request(
        method="post", path="/openapi/v3", parameters={"b": 1}, response_parser=f
    )
    actual = request._decorator(method="post", path="/openapi/v3", parameters={"b": 1})(
        f
    )
    assert actual == expected


def test_request_selector():
    def f(r):  # pragma: no cover
        return "a"

    expected = request.Request(
        method="post", path="/openapi/v3", parameters={"a": 3}, response_parser=f
    )

    actual = request.request.post("/openapi/v3", parameters={"a": 3})(f)
    assert actual == expected
