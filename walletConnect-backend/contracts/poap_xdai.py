from web3 import Web3
import web3
import requests
import json
import time
import shutil
import glob
# --- local
import utils

CONTRACT = '0x22C1f6050E56d2876009903609a2cC3fEf83B415'
HTTPProvider = "https://dai.poa.network"
LABEL = 'POAP'

class Poap_xDai(object):
	def __init__(self):
		with open('contracts/contract_abi.json', 'r') as contract_abi:
			abi = json.load(contract_abi)
			w3 = Web3(Web3.HTTPProvider(HTTPProvider))
			# print(w3.isConnected())
			self.contract = w3.eth.contract(address=CONTRACT, abi=abi)

	def getBalance(self, acc):
		balance = self.contract.functions.balanceOf(acc).call()
		return balance

	def checkOwner(self, token):
		ori_owner = utils.col_user_collects_poap_xdai.find({'_id': token}).distinct('owner')[0]
		print('[Poap_xDai][checkOwner] check owner: ', token)
		new_owner = self.contract.functions.ownerOf(token).call()
		if ori_owner != new_owner:
			ori_path = utils.DB_PATH + 'POAP/' + ori_owner + '/'
			new_path = utils.DB_PATH + 'POAP/' + new_owner + '/'
			utils.mkdir('POAP', utils.DB_PATH)
			utils.mkdir(new_owner, utils.DB_PATH + 'POAP/')
			files = glob.glob(ori_path + '{}-*'.format(token))
			for file in files:
				shutil.move(file, new_path)
				print('[Poap_xDai][checkOwner] Poap token-{} file moved to new owner.'.format(token))
			utils.col_user_collects_poap_xdai.update_one({'_id': token}, {"$set": {'owner': new_owner}})

	def getCollections(self, acc):
		acc = utils.checkSumAddress(acc)
		# --- get db现有的token
		db_token = utils.col_user_collects_poap_xdai.find({'owner': acc}).distinct('_id')
		# ---
		balance = self.getBalance(acc)
		print('[Poap_xDai][getCollections] {} found {} assets'.format(acc, balance))
		for i in range(balance):
			start_time = time.time()
			token = self.contract.functions.tokenOfOwnerByIndex(acc, i).call()
			if token not in db_token:
				self.retrieveDataByToken(token, [], db_token)
				print('[Poap_xDai][getCollections] retrieve token {} used {:.2f}s'.format(token, time.time() - start_time))
			else:
				# --- update owner ---
				self.checkOwner(token)
				# ----
				print('[Poap_xDai][getCollections] Token {} finish checkOwner and already retrieved.'.format(token))
			if token in db_token:
				# print('-------------')
				# print(db_token)
				db_token.remove(token)
				# print(db_token)
				# print('-------------')
		# --- remove checked item
		# --- check owner for existing item but not belong for this address anymore
		for i in db_token:
			self.checkOwner(i)
		print('[Poap_xDai][getCollections] {} Has Done getCollections.'.format(acc))

	def retrieveDataByToken(self, token, owned_token=[], db_token=[]):
		def write_db():
			utils.col_user_collects_poap_xdai.update_one({'_id': data_token},
			                                   {'$set': {'owner': owner,
			                                             'type': 'single',
			                                             'name': name,
			                                             'description': description,
			                                             'create_time': create_time,
			                                             'creator': creator,
			                                             'hash': [''],
			                                             'canvas_token_id': data_token,
			                                             'state': 0,
			                                             'motype': motype,
			                                             'label': LABEL,
			                                             'image_url': image_url,
			                                             'home_url': home_url,
			                                             'attributes': attributes
			                                             },
			                                    '$push': {'file_main': file,
			                                              'file_preview': ['']}}, upsert=True)

		if not db_token:
			db_token = utils.col_user_collects_poap_xdai.find().distinct('_id')
		print('[Poap_xDai][retrieveDataByToken] now start downloading ', token)
		# --- get metadata url
		try:
			url = self.contract.functions.tokenURI(token).call()
		except web3.exceptions.ContractLogicError as e:
			raise web3.exceptions.ContractLogicError(e)
		# --- get metadata json ---
		try:
			response = requests.get(url, timeout=10, verify=False)
		except requests.exceptions.ReadTimeout as e:
			print(e)
			return False
		if response.status_code == 200:
			data = response.json()
			print(data)
			# ----
			data_token = int(token)
			name = data['name']
			description = data['description']
			year = data['year']
			image_url = data['image_url']
			home_url = data['home_url']
			attributes = data['attributes']
			# ----
			creator = 'POAP'
			owner = self.contract.functions.ownerOf(token).call()
			# canvas_token_id = data_token
			create_time = year
			motype = 'textrue'
			# label = LABEL
			# type = 'single'
			# state = 0
			file = str(image_url).split('/')[-1]
			# hash = ['']

			# --- get image png/apng ---
			response = requests.get(image_url, verify=False, timeout=20)
			if glob.glob(utils.DB_PATH + 'POAP/{}'.format(file)):
				print('[Poap_xDai][retrieveDataByToken] file already exists! so wont download again!')
			else:
				if response.status_code == 200:
					file = str(image_url).split('/')[-1]
					utils.mkdir('POAP', utils.DB_PATH)
					with open('{}POAP/{}'.format(utils.DB_PATH, file), 'wb') as f:
						for chunk in response.iter_content(chunk_size=1024):
							if chunk:
								f.write(chunk)
			write_db()
			print('[Poap_xDai][retrieveDataByToken] Finished download ', token)
			return True
		else:
			print('[Poap_xDai][retrieveDataByToken] data node connection error state {}!'.format(response))
			return False


