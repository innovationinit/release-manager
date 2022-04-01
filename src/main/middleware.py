from allow_cidr.middleware import AllowCIDRMiddleware as BaseAllowCIDRMiddleware


class AllowCIDRMiddleware(BaseAllowCIDRMiddleware):

    """Subclass adding storing of get_response."""

    def __init__(self, get_response=None):
        """Store get_response, because base middleware forgot about it."""
        super().__init__(get_response=get_response)
        self.get_response = get_response
