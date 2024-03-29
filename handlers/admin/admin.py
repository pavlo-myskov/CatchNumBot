from aiogram import Dispatcher, types
from loader import bot, dp, db
from keyboards.user_markup.inline_markup import start_inline_markup
from filters import IsAdmin


async def send_update(message: types.Message):
    users = db.get_users()
    for user in users:
        if user[1]:
            name = user[1]
        elif user[2]:
            name = user[2]
        else:
            name = "друже"
        await bot.send_message(user[0], f'Привіт {name}! Вийшла нова версія гри. Зіграємо⁉️',
                               reply_markup=start_inline_markup())
    # await bot.send_message()


# async def get_static(message: types.Message):
#     await bot.send_message(message.from_user.id, f'<pre>{db.get_static()}</pre>', parse_mode=types.ParseMode.HTML)

async def get_statistic(message: types.Message):
    await message.answer(f'админ хендлер')
    # await message.answer(f'<pre>{db.get_stat()}</pre>', parse_mode=types.ParseMode.HTML)

'''
@dp.message_handler(is_admin=True, commands=['admin'])
async def test_state(message: types.Message):
    log.info(f'`{message.from_user.id}` asked the admin commands list')
    await message.answer("Это список секретных команд, которые доступны только админам канала.
                        По мере развития бота их список будет пополнятся.
                        /admin - покажет это сообщение")
'''


def register_handlers_admin(dp: Dispatcher):
    dp.register_message_handler(send_update, IsAdmin(), commands="send", state="*")
    dp.register_message_handler(get_statistic, IsAdmin(), commands="get", state="*")
