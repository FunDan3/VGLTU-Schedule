#! /usr/bin/python3
import json, requests, datetime
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
import datetime
ua = UserAgent()
cDay = lambda: datetime.datetime.now().day

groups_cache = {"day": cDay(), "cache": {}}
teachers_cache = {"day": cDay(), "cache": {}}

def _request_get(url):
	response = requests.get(url, timeout = 15, headers = {"User-Agent": ua.random})
	return response.content

def get_teachers():
	global teachers_cache
	data = _request_get("https://vgltu.ru/sveden/employees/")
	soup = bs(data, 'html.parser')
	if teachers_cache["day"]!=cDay():
		teachers_cache["cache"] = []
	if not teachers_cache["cache"]:
		teachers_cache["cache"] = [[[td.get_text(strip=True) for td in tr.find_all('td')] for tr in table.find_all('tr')] for table in soup.find_all('table')][0] #stolen from stack overflow. Should have used that for get_schedule but it works rn so I wouldn't dare to touch it
	return teachers_cache["cache"]

def get_groups():
	global groups_cache
	if groups_cache["day"]!=cDay():
		groups_cache["cache"] = {}
	if not groups_cache["cache"]:
		groups_cache["cache"] = json.loads(_request_get("https://api.vgltu.ru/s/param_list?param=group_name")) #not quite safe but worst case scenario is my server overloading
	return groups_cache["cache"]

def get_schedule(group): #THIS function SUCKS!!!!!!!!!!!!!!
	def is_vgltu_lesson_time(time):
		if len(time.split("-"))!=2 or len(time.split("-")[0].split(":"))!=2 or len(time.split("-")[1].split(":"))!=2: #checking if value is *:*-*:*
			return False
		assumed_ints = time.split("-")[0].split(":") + time.split("-")[1].split(":")
		for assumed_int in assumed_ints: #checking if all values are ints
			try:
				int(assumed_int)
			except ValueError:
				return False
		return True
	def extract_full_teacher(teacher):
		teacher = teacher.replace(".", " ")
		teacher = teacher[:len(teacher)-1]
		teacher_sirname, teacher_name1, teacher_name2 = teacher.split(" ")
		for probable_teacher in get_teachers():
			if not probable_teacher or len(probable_teacher[0].split(" "))!=3:
				continue
			probable_teacher_sirname, probable_teacher_name1, probable_teacher_name2 = probable_teacher[0].split(" ")
			if teacher_sirname == probable_teacher_sirname and probable_teacher_name1.startswith(teacher_name1) and probable_teacher_name2.startswith(teacher_name2):
				return probable_teacher[0]
		return teacher
	start_date = datetime.datetime.now()
	end_date = start_date + datetime.timedelta(days = 1)
	s = start_date; e = end_date
	data = _request_get(f"https://api.vgltu.ru/s/schedule?date_start={s.year}-{s.month}-{s.day}&date_end={e.year}-{e.month}-{e.day}&group_name={group}") #their website is broken and cant show just 1 day LOL

	#Parsing goes afterwards. I suck at that

	schedules = []

	soup = bs(data, "html.parser")
	for table in soup.find_all("table"):
		schedule = []
		lines = table.text.split("\n")
		for line_data in enumerate(lines):
			index, line = line_data
			if not line:
				continue
			while line[0] in [" ", "\t"]:
				line = line[1:]
				if not line:
					break
			lines[index]=line

		lesson_str = "\n".join(lines).replace("\n\n", "")
		lesson_data = lesson_str.split("\n")
		while "" in lesson_data:
			lesson_data.remove("")
		lesson_data.pop(0)
		lesson_splits = []
		for lesson_obj in lesson_data:
			if is_vgltu_lesson_time(lesson_obj):
				lesson_splits.append([lesson_obj, []])
			else:
				lesson_splits[-1][1].append(lesson_obj)
		for time, values in lesson_splits:
			if len(values) == 4:
				schedule.append({"time": time, "lesson": values[0], "teacher": extract_full_teacher(values[2]), "location": values[3]})
			elif len(values) == 8:
				schedule.append({"time": time, "lesson": values[0], "teacher": extract_full_teacher(values[2]), "location": values[3]})
				schedule.append({"time": time, "lesson": values[4], "teacher": extract_full_teacher(values[6]), "location": values[7]})
			else:
				raise ValueError("Unexpected amount of lesson values")
		schedules.append(schedule)
	return schedules

print(get_schedule("ИС2-242-ОБ"))
