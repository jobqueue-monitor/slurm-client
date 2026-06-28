class Error(Exception):
    pass


class ConnectionError(Error):
    pass


class NetworkError(Error):
    pass


class TokenError(Error):
    pass
