import asyncio
from call import start_call


async def main():
    await start_call("+1234567890","tg",{"voice_id":"yM93hbw8Qtvdma2wCnJG"})


if __name__ == "__main__":
    asyncio.run(main())

