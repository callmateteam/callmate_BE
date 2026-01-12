"""S3 file storage service"""

import os
import uuid
from datetime import datetime
from typing import Optional, Tuple
import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class S3Service:
    """S3 파일 업로드/다운로드 서비스"""

    def __init__(self):
        if settings.use_s3:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self.bucket_name = settings.S3_BUCKET_NAME
        else:
            self.s3_client = None
            self.bucket_name = None

    def _generate_key(self, folder: str, filename: str) -> str:
        """고유한 S3 키 생성"""
        ext = os.path.splitext(filename)[1]
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"{folder}/{timestamp}/{unique_id}{ext}"

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        folder: str = "uploads",
        content_type: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        파일 업로드 (S3 또는 로컬)

        Args:
            file_content: 파일 바이트 데이터
            filename: 원본 파일명
            folder: S3 폴더 (audio, pdf, etc.)
            content_type: MIME 타입

        Returns:
            (file_key, file_url): 파일 키와 URL
        """
        if settings.use_s3:
            return await self._upload_to_s3(file_content, filename, folder, content_type)
        else:
            return await self._upload_to_local(file_content, filename, folder)

    async def _upload_to_s3(
        self,
        file_content: bytes,
        filename: str,
        folder: str,
        content_type: Optional[str]
    ) -> Tuple[str, str]:
        """S3에 파일 업로드"""
        key = self._generate_key(folder, filename)

        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                **extra_args
            )

            url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
            return key, url

        except ClientError as e:
            raise Exception(f"S3 업로드 실패: {e}")

    async def _upload_to_local(
        self,
        file_content: bytes,
        filename: str,
        folder: str
    ) -> Tuple[str, str]:
        """로컬에 파일 저장 (개발용)"""
        # 폴더 생성
        upload_dir = os.path.join(settings.UPLOAD_DIR, folder)
        os.makedirs(upload_dir, exist_ok=True)

        # 고유 파일명 생성
        ext = os.path.splitext(filename)[1]
        unique_id = uuid.uuid4().hex[:8]
        new_filename = f"{unique_id}{ext}"
        file_path = os.path.join(upload_dir, new_filename)

        # 파일 저장
        with open(file_path, 'wb') as f:
            f.write(file_content)

        return file_path, file_path

    async def get_file(self, key: str) -> bytes:
        """
        파일 다운로드

        Args:
            key: 파일 키 (S3 키 또는 로컬 경로)

        Returns:
            파일 바이트 데이터
        """
        if settings.use_s3:
            return await self._get_from_s3(key)
        else:
            return await self._get_from_local(key)

    async def _get_from_s3(self, key: str) -> bytes:
        """S3에서 파일 다운로드"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response['Body'].read()
        except ClientError as e:
            raise Exception(f"S3 다운로드 실패: {e}")

    async def _get_from_local(self, path: str) -> bytes:
        """로컬에서 파일 읽기"""
        with open(path, 'rb') as f:
            return f.read()

    async def delete_file(self, key: str) -> bool:
        """
        파일 삭제

        Args:
            key: 파일 키

        Returns:
            성공 여부
        """
        if settings.use_s3:
            try:
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=key
                )
                return True
            except ClientError:
                return False
        else:
            try:
                os.remove(key)
                return True
            except OSError:
                return False

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """
        S3 Presigned URL 생성 (다운로드용)

        Args:
            key: S3 파일 키
            expiration: URL 만료 시간 (초)

        Returns:
            Presigned URL 또는 None
        """
        if not settings.use_s3:
            return None

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError:
            return None


# 싱글톤 인스턴스
s3_service = S3Service()
