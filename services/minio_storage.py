"""Работа с хранилищем MinIO: проверка и загрузка фото и видео компонентов.

Имена объектов генерируются на латинице:
    power_component_<id>_image_<8 символов>.png
    power_component_<id>_video_<8 символов>.mp4
"""

import json
import logging
import uuid
from io import BytesIO

from minio import Minio

from core.config import settings

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE = 5 * 1024 * 1024    # 5 МБ
MAX_VIDEO_SIZE = 50 * 1024 * 1024   # 50 МБ


def detect_image(header: bytes) -> tuple[str, str] | None:
    """(content_type, расширение) для PNG/JPEG/GIF/WEBP, иначе None."""
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif", ".gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None


def detect_video(header: bytes) -> tuple[str, str] | None:
    """(content_type, расширение) для MP4/MOV/WEBM, иначе None."""
    if header[4:8] == b"ftyp":
        if header[8:10] == b"qt":
            return "video/quicktime", ".mov"
        return "video/mp4", ".mp4"
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm", ".webm"
    return None


def generate_object_name(power_component_id: int, kind: str, extension: str) -> str:
    """Латинское имя файла в бакете, kind — image или video."""
    return f"power_component_{power_component_id}_{kind}_{uuid.uuid4().hex[:8]}{extension}"


class MinioStorage:
    def __init__(self) -> None:
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self.public_url = settings.MINIO_PUBLIC_URL.rstrip("/")

    def ensure_bucket(self) -> None:
        """Создаёт бакет при отсутствии и открывает его на чтение для всех."""
        if not self.client.bucket_exists(bucket_name=self.bucket):
            self.client.make_bucket(bucket_name=self.bucket)
            logger.info("Создан бакет MinIO %s", self.bucket)

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.bucket}/*"],
                }
            ],
        }
        self.client.set_bucket_policy(bucket_name=self.bucket, policy=json.dumps(policy))

    def url_for(self, object_name: str) -> str:
        return f"{self.public_url}/{self.bucket}/{object_name}"

    def upload(self, object_name: str, data: bytes, content_type: str) -> str:
        """Кладёт файл в бакет и возвращает его публичный URL."""
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return self.url_for(object_name)

    def remove(self, object_name: str) -> None:
        self.client.remove_object(bucket_name=self.bucket, object_name=object_name)


storage = MinioStorage()
