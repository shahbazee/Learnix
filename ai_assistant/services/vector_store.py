from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from django.conf import settings


client = QdrantClient(
    url=settings.QDRANT_URL
)


def create_collection():
    collection_name = settings.QDRANT_COLLECTION_NAME

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1024,
                distance=Distance.COSINE,
            ),
        )

    return collection_name