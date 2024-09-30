#! /usr/bin/python3
from telebot.async_telebot import AsyncTeleBot as telebot
import telebot as telegramlib
from vgltu_api import get_schedule, get_groups
import os, asyncio, json, datetime
import secrets

bot = telebot(secrets.telegram_token)
lock = False

async def waitlock():
	iter = 0
	while lock:
		iter +=1
		await asyncio.sleep(1)
		if iter >= 15:
			print("Lock took too long to open, forcing it open")
			break
async def send_schedule(chat_id, value, json_data, schedule_cache):
	print(f"Sending to {chat_id}")
	group, day_sent, errored_out, subgroup = value
	if group not in schedule_cache:
		print(f"Fetching {group}")
		schedule_cache[group] = get_schedule(group) #time, lesson, tutor, location
	schedules = schedule_cache[group]
	today = datetime.datetime.now()
	tomorrow = datetime.datetime.now() + datetime.timedelta(days = 1)

	if subgroup: #nesting ew
		for schedule in schedules:
			to_remove = []
			for lesson in schedule:
				if lesson['lesson'].endswith(" пг. ") and not lesson['lesson'].endswith(f"{subgroup} пг. "):
					to_remove.append(lesson)
			for removed_element in to_remove:
				schedule.remove(removed_element)

	tomorrow_message = "\n\n".join([f"Расписание на завтра ({tomorrow.day}.{tomorrow.month}.{tomorrow.year}):"]+[f"""{lesson['time']}
{lesson['lesson']}
{lesson['tutor']}
{lesson['location']}""" for lesson in schedules[1]])
	today_message = "\n\n".join([f"Расписание на сегодня ({today.day}.{today.month}.{today.year}):"]+[f"""{lesson['time']}
{lesson['lesson']}
{lesson['tutor']}
{lesson['location']}""" for lesson in schedules[0]])
	await bot.send_message(chat_id, tomorrow_message)
	await bot.send_message(chat_id, today_message)
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
		await asyncio.sleep(60*5) #TODO CHANGE BACK
	return

@bot.message_handler(commands = ["start", "unsubscribe", "subscribe", "stats", "setsubgroup"])
async def command_handler(message):
	command = message.text.split(" ")[0].replace("/", "", 1)
	command = globals()[command] #Dont hack me please!
	await command(message)

async def setsubgroup(message):
	global lock
	await waitlock(); lock = True
	if os.path.exists("subscribers.json"):
		with open("subscribers.json", "r") as f:
			json_data = json.load(f)
	else:
		json_data = {}
	if message.chat.id not in json_data:
		await bot.reply_to(message, "Подпишись сначала на рассылку чтоль...")
		lock = False
		return
	if message.text not in ["/setsubgroup 1", "/setsubgroup 2"]:
		await bot.reply_to(message, "Может быть только две подгруппы.")
		lock = False
		return
	json_data[str(message.chat.id)][3] = 1 if message.text.endswith("1") else 2
	with open("subscribers.json", "w") as f:
		json.dump(json_data, f)
	lock = False
	await bot.reply_to(message, f"Теперь ты в {1 if message.text.endswith('1') else 2} подгруппе")

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
	json_data[str(message.chat.id)] = (group, -1, False, False)
	with open("subscribers.json", "w") as f:
		f.write(json.dumps(json_data))
	await bot.reply_to(message, "Спасибо что использовал меня, отправлю расписание в течении 5 минут.\nТы можешь указать подгруппу введя команду /setsubgroup (тут 1 или 2).\nКогда тебя отчислят напиши /unsubscribe, окей?")
	lock = False

async def start(message):
	await bot.reply_to(message, """VGLTU-Schedule - это телеграм бот, который собирает расписание из сайта и отсылает примерно вам в час ночи.
Для того, чтобы начать получать расписание напишите /subscribe ВАША_ГРУППА. Пишите как на сайте, включая заглавные буквы.

VGLTU-Schedule  Copyright (C) 2024  Fun_Dan3
Эта программа не предоставляет АБСОЛЮТНО НИКАКИХ ГАРАНТИЙ.
Лицензия: https://raw.githubusercontent.com/FunDan3/VGLTU-Schedule/refs/heads/main/LICENSE.

Если есть проблемы или предложения пишите @fun_dan3.
Это бета версия бота, не надейтесь на многое
""")

async def start_bot():
	try:
		await asyncio.gather(bot.infinity_polling(), timer())
	except Exception as e:
		print(f"Closing due to {e}")
		await bot.close()
asyncio.run(start_bot())

