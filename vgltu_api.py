import json, requests, datetime
from bs4 import BeautifulSoup as bs

groups_cache = {}

def _request_get(url):
	response = requests.get(url, timeout = 15)
	return response.content

def get_groups():
	global groups_cache
	if not groups_cache:
		groups_cache = json.loads(_request_get("https://api.vgltu.ru/s/param_list?param=group_name")) #not quite safe but worst case scenario is my server overloading
	return groups_cache
def get_schedule(group): #THIS METHOD SUCKS!!!!!!!!!!!!!!

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
	start_date = datetime.datetime.now()
	end_date = start_date + datetime.timedelta(days = 1)
	s = start_date; e = end_date
	data = _request_get(f"https://api.vgltu.ru/s/schedule?date_start={s.year}-{s.month}-{s.day}&date_end={e.year}-{e.month}-{e.day}&group_name={group}") #their website is broken and cant show just 1 day LOL

	#Parsing goes afterwards. I suck at that

	schedule = []

	soup = bs(data, "html.parser")
	table = soup.find_all("table")[0]

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
			schedule.append({"time": time, "lesson": values[0], "tutor": values[2], "location": values[3]})
		elif len(values) == 8:
			schedule.append({"time": time, "lesson": values[0], "tutor": values[2], "location": values[3]})
			schedule.append({"time": time, "lesson": values[4], "tutor": values[6], "location": values[7]})
		else:
			raise ValueError("Unexpected amount of lesson values")
	return schedule
