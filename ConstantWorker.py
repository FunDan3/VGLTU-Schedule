#! /usr/bin/python3
from telebot.async_telebot import AsyncTeleBot as telebot
from vgltu_api import fetcher
import os, asyncio, json, datetime
import secrets

bot = telebot(secrets.telegram_token)

async def send_schedule(chat_id, value, json_data):
	group, day_sent = value
	schedule = await data_fetcher.get_schedule(group) #time, lesson, tutor, location
	message = "\n\n".join([f"""{lesson['time']}
{lesson['lesson']}
{lesson['tutor']}
{lesson['location']}""" for lesson in schedule])
	await bot.send_message(chat_id, message)

async def timer():
	while True:
		if os.path.exists("subscribers.json"):
			with open("subscribers.json", "r") as f:
				json_data = json.load(f)
		else:
			json_data = {}

		tasks = []
		for chat_id, value in json_data.items():
			if value[1]!=datetime.datetime.now().day:
				tasks.append(send_schedule(chat_id, value, json_data))
				json_data[chat_id][1] = datetime.datetime.now().day
		changed_json = len(tasks)>0
		await asyncio.gather(*tasks)
		print(changed_json)
		if changed_json:
			with open("subscribers.json", "w") as f:
				f.write(json.dumps(json_data))
		await asyncio.sleep(60*5)
	return

@bot.message_handler(commands = ["start", "unsubscribe", "subscribe"])
async def command_handler(message):
	command = message.text.split(" ")[0].replace("/", "", 1)
	command = globals()[command] #Dont hack me please!
	await command(message)

async def unsubscribe(message):
	with open("subscribers.json", "r") as f:
		json_data = json.load(f)
	if str(message.chat.id) not in json_data:
		await bot.reply_to(message, "Дак ты не подписан, гений...")
		return
	del json_data[str(message.chat.id)]
	with open("subscribers.json", "w") as f:
		json.dump(json_data, f)
	await bot.reply_to(message, "Ну и иди нафиг! 🖕")


async def subscribe(message):
	group = message.text.replace("/subscribe ", "", 1)
	all_groups = await data_fetcher.get_groups()
	if group not in all_groups:
		await bot.reply_to(message, "Нет такой группы. Пишите как на сайте, включая заглавные буквы.")
		return
	if os.path.exists("subscribers.json"):
		with open("subscribers.json", "r") as f:
			json_data = json.loads(f.read())
	else:
		json_data = {}
	if str(message.chat.id) in json_data:
		await bot.reply_to(message, "Так ты уже на чёт подписан. Отпишись сначала /unsubscribe")
		return
	json_data[str(message.chat.id)] = (group, datetime.datetime.now().day)
	with open("subscribers.json", "w") as f:
		f.write(json.dumps(json_data))
	await bot.reply_to(message, "Спасибо, что использовал меня 🥵. Когда тебя отчислят напиши /unsubscribe, окей?")

async def start(message):
	await bot.reply_to(message, """VGLTU-Schedule - это телеграм бот, который собирает расписание из сайта и отсылает примерно вам в полночь.
Для того, чтобы начать получать расписание напишите /subscribe <ВАША ГРУППА>. Пишите как на сайте, включая заглавные буквы.

VGLTU-Schedule  Copyright (C) 2024  Fun_Dan3
Эта программа не предоставляет АБСОЛЮТНО НИКАКИХ ГАРАНТИЙ.
Лицензия: https://raw.githubusercontent.com/FunDan3/VGLTU-Schedule/refs/heads/main/LICENSE.

Если есть проблемы или предложения пишите @fun_dan3.
""")

async def start_bot():
	global data_fetcher
	data_fetcher = fetcher()
	try:
		await asyncio.gather(bot.polling(), timer())
	except KeyboardInterrupt:
		await data_fetcher.close()
	except asyncio.exceptions.CancelledError:
		await data_fetcher.close()

asyncio.run(start_bot())

