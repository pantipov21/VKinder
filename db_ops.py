import sys
sys.path.append("/usr/lib/python3/dist-packages")
import psycopg2
import sqlalchemy

LINK_PART = 'https://vk.com/id'

#
#
# База данных для обеспечения рабоаы бота из задания.
#
# методы: 
#
#	add - добавить запись в базу
#
#	remove - удалить запись
#
#	clear - удалить все записи из всех таблиц
#
#	is_exists - проверка наличия записи в базе
#
#	data_to_files -  поиск записи и экспорт записи в файл с мнемоническим названием
#
#	getdata - возвращает одну запись
#
#	get_all_data - возвращает все записи
#
#

class vkinderDB:
	def __init__(self,user_name, user_password):		
		db ='postgresql://'+user_name+':'+user_password+'@localhost:5432/vkinder'
		try:
			engine = sqlalchemy.create_engine(db)
			self.connection = engine.connect()
		except Exception as e:
			print("Database connection error. Check server operational, role and password")
			exit(0)
			
		req = '''
			CREATE TABLE IF NOT EXISTS search_results (
				id serial PRIMARY KEY,
				link_name TEXT NOT NULL,
				link_string TEXT NOT NULL,
				vk_id int
			);'''
		self.connection.execute(req)
		
		req = '''
			CREATE TABLE IF NOT EXISTS photos (
				id serial PRIMARY KEY,
				sr integer REFERENCES search_results (id),
				photo1 bytea,
				photo2 bytea,
				photo3 bytea 
			);'''
		self.connection.execute(req)

		
	
	def remove(self,data):
		if isinstance(data,str)==False:
			return -2
			
		req = "SELECT id FROM search_results WHERE vk_id=%s OR link_name=%s';"
		values = (data,data)
		res = self.connection.execute(req,values).fetchone()
		
		try:
			req = "DELETE FROM photos WHERE sr="+str(res[0])+";"
		except Exception as e:
			return -1
			
		res = self.connection.execute(req)

		req = "DELETE FROM search_results WHERE vk_id=%s OR link_name=%s';"
		res = self.connection.execute(req, values)
		return 0
		
		
	def clear(self):
		req = "DELETE FROM photos;"
		res = self.connection.execute(req)
		req = "DELETE FROM search_results;"
		res = self.connection.execute(req)
		return 0
		

	def add(self, name, link, vkid, pic1=None, pic2=None, pic3=None):
		req = 'INSERT INTO search_results(link_name,link_string, vk_id) VALUES(%s,%s,%s);'
		values = (name,link,vkid)
		self.connection.execute(req, values)
		req = "SELECT id FROM search_results ORDER BY id DESC LIMIT 1;"
		res = self.connection.execute(req).fetchone()
		req='INSERT INTO photos(sr,photo1,photo2,photo3) VALUES('+f'{res[0]}'+','+'%s,%s,%s);'
		data = (psycopg2.Binary(pic1), psycopg2.Binary(pic2), psycopg2.Binary(pic3))
		res = self.connection.execute(req, data)
		return 0
			

	def is_exists(self, vkid):
		req = "SELECT id FROM search_results WHERE vk_id=%s;"
		values = (vkid,)
		res = self.connection.execute(req,values).fetchone()
		try:
			if isinstance(res[0],int)==True:
				return True
			else:
				return False
		except Exception as e:
			return False
	

	def get_picture_format(self,buffer): 
		if (buffer[1]==b'P' and buffer[2]==b'N' and buffer[3]==b'G') :
			return 0,'.png'
			
		if (buffer[6]==b'J' and buffer[7]==b'F' and buffer[8]==b'I') \
			or (buffer[6]==b'J' and buffer[7]==b'P' and buffer[8]==b'E'):
			return 0, '.jpg'
			
		if buffer[0]==255 and buffer[1]==216:
			return 0, '.jpg'
			
		return -1, 'Other format'
		

	def data_to_files(self, data, dest_folder="./"):
		if self.is_exists(data):
			req = '''SELECT link_name, vk_id, photo1, photo2, photo3 FROM 
			search_results JOIN photos ON photos.sr = search_results.id 
			WHERE link_name=%s OR vk_id=%s;
			'''
			
			values = (data, data)
			res = tuple(self.connection.execute(req, values))			
			fn = dict()
			
			for i in range(1,4):
				
				if res[0][i+1]!=None:
					status, frmt = self.get_picture_format(res[0][i+1])
					if status == 0:
						filename = dest_folder+res[0][0]+'_'+str(i)+frmt
						f = open(filename,'wb')
						f.write(res[0][i+1])
						f.close()
					
			return 0, res[0][0], res[0][1]
		else:
			return -1, -1, -1


	def getdata(self,data):
		if self.is_exists(data):
			req = '''SELECT link_name, link_string, vk_id, photo1, photo2, photo3 FROM 
			search_results JOIN photos ON photos.sr = search_results.id 
			WHERE link_name=%s OR vk_id=%s;
			'''
			
			values = (data, data)
			res = tuple(self.connection.execute(req, values))
			return 0, res
		else:
			return -1, 0
			
			
	def	getalldata(self):
		req = '''SELECT link_name, link_string, vk_id, photo1, photo2, photo3 FROM 
		search_results JOIN photos ON photos.sr = search_results.id ;
		'''
		res = tuple(self.connection.execute(req))
		return res
				


def read_file(filename):
	f = open(filename,'rb')
	d = f.read()
	f.close()
	return d


def test_for_developers():
	vDB = vkinderDB('py48','123456')
#	vDB.clear()
	#print(isinstance((1,), tuple))
	print(vDB.is_exists("12345"))
	#print(vDB.getalldata())
	#f1 = read_file('_test.jpg');
	#vDB.add("Лена","https://lena", f1)
	
#	vDB.data_to_files("Маруся")
	exit(0)

	f1 = read_file('1.png');
	f2 = read_file('2.png');
	f3 = read_file('3.png');
	vDB.add("Петя",LINK_PART, 123456, f1, f2, f3)


	f1 = read_file('4.png');
	f2 = read_file('5.png');
	f3 = read_file('_1.png');
	vDB.add("Вася",LINK_PART, 234567, f1, f2, f3)


	f1 = read_file('_2.png');
	f2 = read_file('_3.png');
	vDB.add("Маруся",LINK_PART, 345678, f1, f2)


#test_for_developers()
