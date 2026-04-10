"""Скрипт для инициализации MinIO buckets."""
from src.storage.minio_service import minio_service


def main():
    minio_service.ensure_buckets()
    print("MinIO buckets initialized successfully")


if __name__ == "__main__":
    main()
