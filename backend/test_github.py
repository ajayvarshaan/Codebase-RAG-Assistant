import asyncio

from services.github_service import download_github_repository


async def main():
    result = await download_github_repository(
        "https://github.com/facebook/react"
    )

    print("Owner:", result["owner"])
    print("Repository:", result["repo"])
    print("Default branch:", result["default_branch"])
    print("ZIP size:", len(result["zip_data"]), "bytes")


asyncio.run(main())