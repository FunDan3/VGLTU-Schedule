#! /usr/bin/python3
from telebot.async_telebot import AsyncTeleBot as telebot
import telebot as telegramlib
from vgltu_api import get_schedule, get_groups
import os, asyncio, json, datetime
import secrets

bot = telebot(secrets.telegram_token)
lock = False

async def waitlock():
	while lock:
		await time.sleep(1)

async def send_schedule(chat_id, value, json_data, schedule_cache):
	print(f"Sending to {chat_id}")
	group, day_sent, errored_out = value
	if group not in schedule_cache:
		print(f"Fetching {group}")
		schedule_cache[group] = get_schedule(group) #time, lesson, tutor, location
	schedule = schedule_cache[group]
	t = datetime.datetime.now()
	message = "\n\n".join([f"{t.day}.{t.month}.{t.year}"]+[f"""{lesson['time']}
{lesson['lesson']}
{lesson['tutor']}
{lesson['location']}""" for lesson in schedule])
	await bot.send_message(chat_id, message)
	print(f"Sent to {chat_id}")

async def timer():
	global lock
	schedule_cache = {}
	pday = datetime.datetime.now().day
	while True:
		if pday!=datetime.datetime.now().day:
			schedule_cache = {}
			pday = datetime.datetime.now().day
		await waitlock(); lock=True
		if os.path.exists("subscribers.json"):
			with open("subscribers.json", "r") as f:
				json_data = json.load(f)
		else:
			json_data = {}

		changed_json = False
		to_remove = []
		for chat_id, value in json_data.items():
			if value[1]!=datetime.datetime.now().day:
				try:
					await send_schedule(chat_id, value, json_data, schedule_cache)
					json_data[chat_id][1] = datetime.datetime.now().day
					json_data[chat_id][2] = False #Errored out
					changed_json = True
					await asyncio.sleep(1)
				except Exception as e:
					print(f"{e}: {chat_id}: {value}")
					if not json_data[chat_id][2]:
						json_data[chat_id][2] = True #Errored out
						changed_json = True
						try:
							await bot.send_message(chat_id, "Произошла ошибка. Если вы имеете доступ к вебсайту университета напишите @fundan3\n"+str(e))
						except telegramlib.asyncio_helper.ApiTelegramException as e:
							if "403" in str(e):
								to_remove.append(chat_id)
							else:
								raise e
		for chat_id in to_remove:
			del json_data[chat_id]
		if changed_json:
			with open("subscribers.json", "w") as f:
				f.write(json.dumps(json_data))
		lock = False
		await asyncio.sleep(60*1)
	return

@bot.message_handler(commands = ["start", "unsubscribe", "subscribe", "stats"])
async def command_handler(message):
	command = message.text.split(" ")[0].replace("/", "", 1)
	command = globals()[command] #Dont hack me please!
	await command(message)

async def stats(message):
	if os.path.exists("subscribers.json"):
		with open("subscribers.json", "r") as f:
			json_data = json.load(f)
	else:
		json_data = {}
	await bot.reply_to(message, f"Bot has {len(json_data.keys())} subscribers")

async def unsubscribe(message):
	global lock
	await waitlock(); lock = True
	with open("subscribers.json", "r") as f:
		json_data = json.load(f)
	if str(message.chat.id) not in json_data:
		await bot.reply_to(message, "Дак ты не подписан, гений...")
		lock = False
		return
	del json_data[str(message.chat.id)]
	with open("subscribers.json", "w") as f:
		json.dump(json_data, f)
	lock = False
	await bot.reply_to(message, "Ну и иди нафиг! 🖕")


async def subscribe(message):
	global lock
	group = message.text.replace("/subscribe ", "", 1)
	all_groups = get_groups()
	if group not in all_groups:
		await bot.reply_to(message, "Нет такой группы. Пишите как на сайте, включая заглавные буквы.")
		return
	await waitlock(); lock = True
	if os.path.exists("subscribers.json"):
		with open("subscribers.json", "r") as f:
			json_data = json.loads(f.read())
	else:
		json_data = {}
	if str(message.chat.id) in json_data:
		await bot.reply_to(message, "Так ты уже на чёт подписан. Отпишись сначала /unsubscribe")
		lock = False
		return
	json_data[str(message.chat.id)] = (group, -1, False)
	with open("subscribers.json", "w") as f:
		f.write(json.dumps(json_data))
	await bot.reply_to(message, "Спасибо что использовал меня, отправлю расписание в течении 5 минут. Когда тебя отчислят напиши /unsubscribe, окей?")
	lock = False

async def start(message):
	await bot.reply_to(message, """VGLTU-Schedule - это телеграм бот, который собирает расписание из сайта и отсылает примерно вам в час ночи.
Для того, чтобы начать получать расписание напишите /subscribe <ВАША ГРУППА>. Пишите как на сайте, включая заглавные буквы.

VGLTU-Schedule  Copyright (C) 2024  Fun_Dan3
Эта программа не предоставляет АБСОЛЮТНО НИКАКИХ ГАРАНТИЙ.
Лицензия: https://raw.githubusercontent.com/FunDan3/VGLTU-Schedule/refs/heads/main/LICENSE.

Если есть проблемы или предложения пишите @fun_dan3.
Это бета версия бота, не надейтесь на многое
""")

async def start_bot():
	try:
		await asyncio.gather(bot.infinity_polling(), timer())
	except Exception:
		await bot.close()
asyncio.run(start_bot())

