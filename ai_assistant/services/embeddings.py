import cohere

from django.conf import settings


co = cohere.ClientV2(
    api_key=settings.COHERE_API_KEY
)


def generate_embeddings(texts):
    response = co.embed(
        texts=texts,
        model="embed-english-v3.0",
        input_type="search_document",
        embedding_types=["float"],
    )

    return response.embeddings.float