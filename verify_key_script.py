import httpx
import asyncio

async def verify_key_request(api_key: str):
    url = f"http://localhost:6000/gemini/v1beta/verify-key/{api_key}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url)
            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {response.text}")
        except httpx.RequestError as e:
            print(f"An error occurred while requesting {e.request.url}: {e}")

if __name__ == "__main__":
    # Replace with your actual API key
    api_key = "AIzaSyD0Kjrexz4uLqNvaFiBiNHExhCsnfnovCI"
    asyncio.run(verify_key_request(api_key))
