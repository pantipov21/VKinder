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
	
		
	def write_msg(self, user_id, message): 
		self.vk.method('messages.send', {'user_id': user_id, 'message': message,  'random_id': randrange(10 ** 7),})
		return 0


	def write_photo(self, user_id, owner_id, media_id): 
		attach_str =f'photo{owner_id}_{media_id}'
		self.vk.method('messages.send', {'user_id': user_id, 'attachment':attach_str, 'random_id': randrange(10 ** 7),})


	def get_user_name(self, user_id):
		user = self.vk.method("users.get", {"user_ids": user_id}) 
		return user[0]['first_name'] +  ' ' + user[0]['last_name']

		
	def get_city_id(self, city):
		resp = self.user_vk.method("database.getCities", {'q':city, "country_id": 1} ) 
		if resp.get('count') == 0:
			return -1
		return resp.get('items')[0].get('id')


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

	
#download_images_and_record_to_DB(uid,selected_photos, self.get_user_name(uid), self.get_user_link(uid))
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
		
		#add(self, name, link, vkid, pic1=None, pic2=None, pic3=None):
		while len(byte_array)<3:
			byte_array.append(None)
			
		self.DB.add(name, link, owner_id, byte_array[0], byte_array[1], byte_array[2])
			
			

	def run(self):
		is_chat = False
		vk_offset = 0
		for event in self.longpoll.listen():
			if event.type == VkEventType.MESSAGE_NEW:
				if event.to_me:
					request = event.text.lower()
					if request == "стоп" or request == "stop":
						self.write_msg(event.user_id, 'Бот остановлен.')
						exit(0)
						
						
					if is_chat == False:
						
						if request == "привет":
							self.write_msg(event.user_id, f"Привет, {self.get_user_name(event.user_id)}")
							
						elif request == "ищу пару":
							self.write_msg(event.user_id, "Введите возраст, пол, населенный пункт проживания и семейное положение искомого человека")
							self.write_msg(event.user_id, "Например, вот такой запрос: 30, Ж, Москва, С")
							self.write_msg(event.user_id, "будет искать замужнюю женщину 30 лет в Москве. С - замужем, О - одинокая")
							is_chat = True
							
						elif request == "пока" or request == "до свидания" or request == "всего хорошего" or request == "всего доброго":
							is_chat = False
							vk_offset= 0
							self.write_msg(event.user_id, request)
						else:
							self.write_msg(event.user_id, 'Не понял, уточните.\nПонимаю: привет, ищу пару, пока')
							
					else:
						#разбираем request
						params = request.split(',')
						lp = len(params)
						if lp<=1 or lp>4:
							self.write_msg(event.user_id, 'Запрос не верен. Попробуйте еще раз')
							continue
							
						#проверка города
						city_id = self.get_city_id(params[2])
						if city_id==-1:
							self.write_msg(event.user_id, f'Населенный пункт {params[2]} не найден. Попробуйте еще раз')
							continue
						
						#проверка пола
						sex_id = params[1]
						if sex_id == 'f' or sex_id == 'ж':
							sex_id = 1
						elif sex_id == 'm' or sex_id == 'м':
							sex_id = 2
						else:
							self.write_msg(event.user_id, f'Пол указан неверно')
							continue
							
										
						#проверка семейного положения
						status_id = params[3]
						if status_id =='c' or status_id == 'с':
							status_id = 4
						elif status_id =='o' or status_id == 'о':
							status_id = 1
						else:
							self.write_msg(event.user_id, f'Семейное положение неясно. Уточните запрос')
							continue
						
						try:
							age_id = int(params[0])
						except Exception as e:
							self.write_msg(event.user_id, f'Возраст указан странно. Уточните запрос')
							continue
							
						#выполнение поиска
						self.write_msg(event.user_id, 'Выполняю поиск...')      
						result = self.user_vk.method("users.search", {'q':'',  'count':SEARCH_COUNT, 'offset':vk_offset,'has_photo':True,  'city':city_id, 'sex':sex_id, 'status':status_id,'age_from':age_id, 'age_to':age_id})
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
							selected_photos=set()
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
								
								print(len(selected_photos))
								
							print(selected_photos)
							for sp in selected_photos:
								self.write_photo(event.user_id, uid, sp)
																
							self.write_msg(event.user_id, f'Страничка здесь: {self.get_user_link(uid)}')
							self.write_msg(event.user_id, f'Имя: {self.get_user_name(uid)}')
							
							# и записать в базу данных бота
							self.download_images_and_record_to_DB(uid,selected_photos, self.get_user_name(uid), self.get_user_link(uid))
							
							print(self.get_user_link(uid))
							
							
						self.write_msg(event.user_id, 'Выполнено.')
						is_chat = False
						print('AFTER')
	
