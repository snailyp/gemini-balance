from typing import Union


class ImageMetadata:
    def __init__(self, width: int, height: int, filename: str, size: int, url: str, delete_url: Union[str, None] = None):
        self.width = width
        self.height = height
        self.filename = filename
        self.size = size
        self.url = url
        self.delete_url = delete_url
class UploadResponse:
    def __init__(self, success: bool, code: str, message: str, data: ImageMetadata):
        self.success = success
        self.code = code
        self.message = message
        self.data = data
class ImageUploader:
    def upload(self, file: bytes, filename: str) -> UploadResponse:
        raise NotImplementedError
