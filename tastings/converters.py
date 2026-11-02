class ObjectIdConverter:
    """Matches a 24-character hex MongoDB ObjectId in URLs."""

    regex = "[0-9a-f]{24}"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return str(value)
