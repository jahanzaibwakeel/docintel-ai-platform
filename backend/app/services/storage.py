from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

import boto3
from fastapi.responses import FileResponse, RedirectResponse, Response

from app.core.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.settings.storage_endpoint_url or None,
            region_name=self.settings.storage_region,
            aws_access_key_id=self.settings.storage_access_key_id or None,
            aws_secret_access_key=self.settings.storage_secret_access_key or None,
        )

    def save_pdf(self, workspace_id: int, contents: bytes) -> str:
        if self.settings.storage_provider == "s3":
            if not self.settings.storage_bucket:
                raise ValueError("STORAGE_BUCKET is required for S3 storage")
            key = f"workspaces/{workspace_id}/documents/{uuid4().hex}.pdf"
            self._client().put_object(
                Bucket=self.settings.storage_bucket,
                Key=key,
                Body=contents,
                ContentType="application/pdf",
                ServerSideEncryption="AES256",
            )
            return f"s3://{self.settings.storage_bucket}/{key}"

        user_dir = self.settings.upload_dir / str(workspace_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        storage_path = user_dir / f"{uuid4().hex}.pdf"
        storage_path.write_bytes(contents)
        return str(storage_path)

    def open_local_path(self, storage_path: str) -> str:
        if not storage_path.startswith("s3://"):
            return storage_path
        bucket, key = self._split_s3_uri(storage_path)
        temp = NamedTemporaryFile(delete=False, suffix=".pdf")
        temp.close()
        self._client().download_file(bucket, key, temp.name)
        return temp.name

    def response(self, storage_path: str, filename: str) -> Response:
        if storage_path.startswith("s3://"):
            bucket, key = self._split_s3_uri(storage_path)
            url = self._client().generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key, "ResponseContentDisposition": f'inline; filename="{filename}"'},
                ExpiresIn=self.settings.storage_presign_seconds,
            )
            return RedirectResponse(url)

        path = Path(storage_path)
        if not path.exists():
            raise FileNotFoundError(storage_path)
        return FileResponse(path, media_type="application/pdf", filename=filename)

    def delete(self, storage_path: str) -> None:
        if not storage_path:
            return
        if storage_path.startswith("s3://"):
            bucket, key = self._split_s3_uri(storage_path)
            self._client().delete_object(Bucket=bucket, Key=key)
            return
        Path(storage_path).unlink(missing_ok=True)

    @staticmethod
    def _split_s3_uri(uri: str) -> tuple[str, str]:
        without_scheme = uri.removeprefix("s3://")
        bucket, key = without_scheme.split("/", 1)
        return bucket, key


def get_storage() -> StorageService:
    return StorageService()

