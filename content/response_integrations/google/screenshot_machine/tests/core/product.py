import abc


class ScreenshotMachine(abc.ABC):

    @staticmethod
    def take_screenshot(
        api_key: str,
        url: str,
        image_format: str,
        device: str,
        dimension: str,
        cache_limit: int,
        delay: int
    ) -> str:
        """Return screenshot"""
        return (
            f"Created Screenshot: {api_key}, {url}, {image_format}, {device}, "
            f"{dimension}, {cache_limit}, {delay}"
        )
