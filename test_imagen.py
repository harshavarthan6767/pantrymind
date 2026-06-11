import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from google.genai import Client
from google.genai import types as genai_types

async def main():
    print("Testing image generation directly...")
    client = Client(vertexai=True, project=os.getenv("GCP_PROJECT"), location="us-central1")
    response = await client.aio.models.generate_images(
        model=os.getenv("IMAGEN_MODEL", "imagen-4.0-generate-001"),
        prompt="A simple test image of an apple",
        config=genai_types.GenerateImagesConfig(
            number_of_images=1,
        )
    )
    if response.generated_images and len(response.generated_images) > 0:
        img_obj = response.generated_images[0].image
        print("image object type:", type(img_obj))
        print("image attrs:", dir(img_obj))
        if hasattr(img_obj, 'image_bytes'):
            bytes_data = img_obj.image_bytes
            print("image_bytes type:", type(bytes_data))
            print("image_bytes length:", len(bytes_data))
            print("first 20 bytes:", bytes_data[:20])
        else:
            print("No image_bytes attribute")
    else:
        print("No generated images returned.")

if __name__ == "__main__":
    asyncio.run(main())
