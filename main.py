from vk_ops import *


if __name__=='__main__':
		
	with open('vkinder.cfg', 'r') as f:
		params = json.load(f)
		
	vkinder=vkinderVK(params.get('group_token'), params.get('user_token'), params.get('db_name'), params.get('db_password'))
	vkinder.run()
	