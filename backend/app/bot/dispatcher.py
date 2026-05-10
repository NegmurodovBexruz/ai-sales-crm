from aiogram import Dispatcher

from app.bot.handlers import admin_orders, messages, start

dp = Dispatcher()
dp.include_router(start.router)
dp.include_router(admin_orders.router)
dp.include_router(messages.router)
