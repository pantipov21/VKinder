#import datetime
from random import randrange
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from db_ops import *
import json
import time
import sys
sys.path.append('/usr/lib/python3/dist-packages')
import requests

SEARCH_COUNT = 10


class vkinderVK():
	def __init__(self, g_token, u_token, db_name, db_password):
		self.user_vk = vk_api.VkApi(token = u_token)
		self.vk = vk_api.VkApi(token=g_token)
		self.longpoll = VkLongPoll(self.vk)
		self.DB = vkinderDB(db_name,db_password)
		self.country = 'Россия'
		self.country_list = self.user_vk.method("database.getCountries", {"need_all": True, 'count':234} ) .get('items')

		
	def write_msg(self, user_id, message): 
		self.vk.method('messages.send', {'user_id': user_id, 'message': message,  'random_id': randrange(10 ** 7),})
		return 0


	def write_photo(self, user_id, owner_id, media_id): 
		attach_str =f'photo{owner_id}_{media_id}'
		self.vk.method('messages.send', {'user_id': user_id, 'attachment':attach_str, 'random_id': randrange(10 ** 7),})


	def get_user_name(self, user_id):
		user = self.vk.method("users.get", {"user_ids": user_id}) 
		return user[0]['first_name'] +  ' ' + user[0]['last_name']


	def ask_for_users_byear(self, user_id): # всё равно сделал, до того, как Вам ответ написал. Убирать код не стал - практика всё же))
		self.write_msg(user_id, 'Уточните, пожалуйста, год Вашего рождения')
		for event in self.longpoll.listen():
			if event.type == VkEventType.MESSAGE_NEW:
				if event.to_me:
					
					try:	
						r = int(event.text)
						if r>1900 and r <2022:#в высшей степени условность, прекрасно это вижу
							self.write_msg(user_id, 'Спасибо')
							return r
						else:
							self.write_msg(user_id, 'Попробуйте еще раз')
							
					except ValueError as e:
						self.write_msg(user_id, 'Попробуйте еще раз')


	def check_ages(self,s):
		if s.isdigit()==True:
			return 0, s, s
		else:
			if s.count('-')==1:
				ages = s.split('-')
				if ages[0].isdigit() == True and ages[1].isdigit() == True:
					afrom = ages[0]
					ato = ages[1]
					if ato<afrom:
						t = afrom
						afrom = ato
						ato = t
					return 1, str(afrom), str(ato)
			return -1, None, None
			


	def ask_for_age(self, user_id):
		self.write_msg(user_id, 'Какой возраст кандидатов ?\nПримеры:\n 25\n25-30')
		for event in self.longpoll.listen():
			if event.type == VkEventType.MESSAGE_NEW:
				if event.to_me:
					r = self.remove_spaces(event.text)
					res, afrom, ato = self.check_ages(r)
					if res == 0:
						return afrom
					elif res == 1:
						return afrom+'-'+ ato
					else:
						self.write_msg(user_id, 'Попробуйте еще раз')
						continue


	def remove_spaces(self,s):
		tmp_ = ''
		for i in range(0,len(s)):
			if s[i]!=' ':
				tmp_=tmp_+s[i]
		return tmp_


	def get_user_params(self, uid):
		user = self.vk.method('users.get', {'user_ids': uid, 'fields':'city,country,sex'})#,bdate'}) 
		print(user[0])
#		now = datetime.datetime.now()
		
#		try:
#			year = user[0].get('bdate')
#			r = year.split('.')
#			res = str(now.year - int(r[2]))
#		except AttributeError as e:
#			#res = str(now.year-self.ask_for_users_byear(uid))
#			res='25'
		
		res = self.ask_for_age(uid)	
			
		gender = user[0].get('sex')
		if gender == 1:
			gender = 'М'
		elif gender == 2:
			gender = 'Ж'
		else:
			gender = 'Ж'
		res = res+', '+gender+', О'
		
		try:
			city = user[0].get('city').get('title')
		except AttributeError as e:
			city='Москва'
		res = res+', '+city	
			
		try:
			self.country = user[0].get('country').get('title')
		except AttributeError as e:
			self.country = 'Россия'
			
		res = res+', '+self.country
		return res

		
	def get_city_id(self, city,country_id):
		resp = self.user_vk.method("database.getCities", {'q':city, "country_id": country_id} ) 
		if resp.get('count') == 0:
			return -1
		return resp.get('items')[0].get('id')


	def get_country_id(self, country):
		country = country.lower()
		for item in self.country_list:
			if country == item.get('title').lower():
				return item.get('id')
		return 1


	def get_user_link(self, id):
		return 'https://vk.com/id'+str(id)


	def get_photos_quantity(self, id):
		resp = self.user_vk.method("photos.get", {'owner_id':id, "album_id": 'profile', 'count':1 } )
		q = resp.get('count')
		if q <3:
			return False, 0
		else:
			return True, q
		

	def get_photos(self, uid, item):
		res = False
		quantity = 0
		try:
			res, quantity = self.get_photos_quantity(uid)
			if res == False:#отбрасываем профиль без фотографий
				return -1,None
				
		except vk_api.exceptions.ApiError as e:
			return -1,None # отбрасываем приватный профиль
			
		#отбрасываем закрытый профиль	
		if item.get('is_closed') == True:
			return -1,None
		
		#отбрасываем уже существующие в БД
		if self.DB.is_exists(uid) == True:
			return -1,None
		
		resp = self.user_vk.method("photos.get", {'owner_id':uid, "album_id": 'profile', 'count':quantity, 'extended':True } )
		return 0, resp.get('items')

	
	def download_images_and_record_to_DB(self, owner_id,sel_photos, name, link):
		count = 0
		
		byte_array = list()
		
		for sp in sel_photos:
			ph_str = f'{owner_id}_{sp}'
			res = self.user_vk.method("photos.getById", {"photos": ph_str} ) 
			print('getById')
			print(res)
			ph_url = res[0].get('sizes')[0].get('url')
			ufr = requests.get(ph_url)
			if ufr.status_code == 200:
				byte_array.append(ufr.content);
			count = count + 1
		
		while len(byte_array)<3:
			byte_array.append(None)
			
		self.DB.add(name, link, owner_id, byte_array[0], byte_array[1], byte_array[2])
			

	def run(self):
		selected_photos=set()
		request_sample=''
		is_chat = False
		vk_offset = 0
		for event in self.longpoll.listen():
			if event.type == VkEventType.MESSAGE_NEW:
				if event.to_me:
					request = event.text.lower()
					if request == "стоп" or request == "stop":
						self.write_msg(event.user_id, 'Бот остановлен.')
						exit(0)
						
					elif request == "пока" or request == "до свидания" or request == "всего хорошего" or request == "всего доброго":
						is_chat = False
						vk_offset= 0
						self.write_msg(event.user_id, request)
						continue
						
					if is_chat == False:
						
						if request == "привет":
							self.write_msg(event.user_id, f"Привет, {self.get_user_name(event.user_id)}")
							self.write_msg(event.user_id, f"Понимаю команды:\nпривет\nищу пару\nпока")
							
						elif request == "ищу пару":
							request_sample = self.get_user_params(event.user_id)
							
							self.write_msg(event.user_id, "Вам предлагается такой поисковый запрос:")
							self.write_msg(event.user_id, request_sample)
							self.write_msg(event.user_id, "Если согласны с этим запросом, то наберите ДА\n"+
							"или введите свой поисковый запрос.")
							self.write_msg(event.user_id,
							"Например, вот такой запрос: \n30, Ж, С, Москва, Россия"+
							"\nбудет искать замужнюю женщину 30 лет в Москве."+
							"\nС - замужем, О - одинокая")
							is_chat = True
							
						else:
							self.write_msg(event.user_id, 'Не понял, уточните.\nПонимаю команды:\nпривет\nищу пару\nпока')
							
					else:
						if request == 'да':
							request = request_sample
							
						#удаляем пробелы	
						request = self.remove_spaces(request)
						
						#разбираем request
						params = request.split(',')
						lp = len(params)
						if lp!=5:
							self.write_msg(event.user_id, 'Запрос не верен. Попробуйте еще раз')
							continue
							
						#проверка возраста
						res, afrom, ato = self.check_ages(params[0])
						if res ==-1:
							self.write_msg(event.user_id, f'Возраст указан неправильно.')
							continue
							
						#проверка города
						city_id = self.get_city_id(params[3], self.get_country_id(params[4]))
						if city_id==-1:
							self.write_msg(event.user_id, f'Населенный пункт {params[3]} не найден. Попробуйте еще раз')
							continue
						
						#проверка пола
						sex_id = params[1].lower()
						if sex_id == 'f' or sex_id == 'ж':
							sex_id = 1
						elif sex_id == 'm' or sex_id == 'м':
							sex_id = 2
						else:
							self.write_msg(event.user_id, f'Пол указан неверно')
							continue
							
										
						#проверка семейного положения
						status_id = params[2].lower()
						if status_id =='c' or status_id == 'с':
							status_id = 4
						elif status_id =='o' or status_id == 'о':
							status_id = 1
						else:
							self.write_msg(event.user_id, f'Семейное положение неясно. Уточните запрос')
							continue
												
						#выполнение поиска
						self.write_msg(event.user_id, 'Выполняю поиск...')      
						result = self.user_vk.method("users.search", {'q':'',  'count':SEARCH_COUNT, 'country':self.get_country_id(params[4]), 'offset':vk_offset,'has_photo':True,  'city':city_id, 'sex':sex_id, 'status':status_id,'age_from':afrom, 'age_to':ato})
						vk_offset = vk_offset + SEARCH_COUNT
						
						print(result)
						
						if result.get('count')==0:
							self.write_msg(event.user_id, f'Никого по заданным критериям не найдено.')
							vk_offset = 0;
							continue
							
						
						user_list = result.get('items')
						for item in user_list:
							time.sleep(0.2)
							uid = item.get('id')
							res, photos_list = self.get_photos(uid, item)
							if res == -1:
								print('Profile is not valid: '+self.get_user_link(uid));
								continue
							
							#print(photos_list) #список фотографий конкретного пользователя
							
							
							#
							# 1 получить id фотографии
							# 2 получить количество лайков
							# 3 получить количество комментариев
							# 4 найти id трех самых популярных фотографий
							# 5 получить url для каждой фотографии 
							# 6 отправить их в чат
							# 7 отправить в чат ссылку на собственника этих фотографий
							#
						###################################
							selected_photos.clear()
							#1. получаем id фотографии
							max_id=1
							while max_id!=0 and len(selected_photos) < 3:
								
								time.sleep(0.2)
								max_likes = 0
								max_id = 0
								
								for ph in photos_list:
									cur_like = ph.get('likes').get('count')
									if cur_like > max_likes and ph.get('id') not in selected_photos:
										max_likes = cur_like
										max_id = ph.get('id')
										
								if max_id!=0 :
									selected_photos.add(max_id)
								
								if max_id == 0:
									max_id = 1
									while max_id != 0 and len(selected_photos)<3:
										time.sleep(0.2)
										max_id = 0
										max_comments = 0
										for ph1 in photos_list:
											cur_comment = ph1.get('comments').get('count')
											if cur_comment > max_comments and ph1.get('id') not in selected_photos:
												max_comments = cur_comment
												max_id = ph1.get('id')
												
										if max_id !=0:
											selected_photos.add(max_id)
											
							#отправить очередную запись в чат
							#
							#сначала фотографии 
							for sp in selected_photos:
								self.write_photo(event.user_id, uid, sp)
							#потом информацию									
							self.write_msg(event.user_id, f'Страничка здесь: {self.get_user_link(uid)}')
							self.write_msg(event.user_id, f'Имя: {self.get_user_name(uid)}')
							
							# и записать в базу данных бота
							self.download_images_and_record_to_DB(uid,selected_photos, self.get_user_name(uid), self.get_user_link(uid))
													
							self.write_msg(event.user_id, 'Показывать дальше? (ДА или НЕТ)')
							stop_flag=False
							for event_ in self.longpoll.listen():
								if event_.type == VkEventType.MESSAGE_NEW:
									if event_.to_me:
										request = event_.text.lower()
										if request=='да':
											break
										else:
											stop_flag=True
											break
							if stop_flag==True:
								self.write_msg(event.user_id, 'Прервано пользователем')
								break
								

							print(self.get_user_link(uid))
							
							
						self.write_msg(event.user_id, 'Выполнено.')
						is_chat = False
						print('AFTER')
	
