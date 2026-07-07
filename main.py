import asyncio

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from handlers import admin, broadcast, start, user
from scheduler import scheduler_loop

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start.router)
dp.include_router(admin.router)
dp.include_router(broadcast.router)
dp.include_router(user.router)


async def main():
    asyncio.create_task(scheduler_loop(bot))
    print("Bot ishga tushdi")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
