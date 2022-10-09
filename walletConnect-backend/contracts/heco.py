# -*- coding: utf-8 -*-
import threading

import cv2
import web3
from web3 import Web3
import json
import requests
import ast
import base64
import shutil
import glob
import time
import os
# ----
import utils


LABEL = 'HECO'
LABEL_API = 'http://223.94.61.114:55001/api/v0/cat'
IPFS_API = 'https://ipfs.io/ipfs/'
# ADDRESS = '0x20daF99a080A2A4590A815465c499f123fD5c551'
ADDRESS = '0xC40cbF7b00Fb2fFaf4e25D12764eb043e494B7B9' # AWS
# ADDRESS = '0x791af8Ab218F1566aB68893EC8814059EddF49b8' # test new address
PINATA_API = 'https://icarusart.mypinata.cloud/ipfs/'


class hecoContract(object):
    def __init__(self):
        with open('contracts/contract_abi.json', 'r') as contract_abi:
            abi = json.load(contract_abi)
        # --- heco address ---
        w3 = Web3(Web3.HTTPProvider("https://http-mainnet-node.huobichain.com"))
        self.contract = w3.eth.contract(address=ADDRESS, abi=abi)
        self.in_progress = []
        print('[HECO][Info] HECO initialized.')

    def getBalance(self, acc):
        balance = self.contract.functions.balanceOf(acc).call()
        return balance

    def isInProgress(self, acc):
        if utils.checkSumAddress(acc) in self.in_progress:
            return True
        else:
            return False

    def checkOwner(self, token):
        ori_owner = utils.col_user_collects.find({'_id': token}).distinct('owner')[0]
        print('check owner: ', token)
        new_owner = self.contract.functions.ownerOf(token).call()
        if ori_owner != new_owner:
            ori_path = utils.DB_PATH + 'HECO/' + ori_owner + '/'
            new_path = utils.DB_PATH + 'HECO/' + new_owner + '/'
            utils.mkdir('HECO', utils.  DB_PATH)
            utils.mkdir(new_owner, utils.DB_PATH+'HECO/')
            files = glob.glob(ori_path + '{}-*'.format(token))
            for file in files:
                shutil.move(file, new_path)
                print('[Heco][INFO] Heco token-{} file moved to new owner.'.format(token))
            utils.col_user_collects.update_one({'_id': token},
                                               {"$set": {'owner': new_owner}})

    def checkState(self, token):
        try:
            state = self.contract.functions.getControlToken(token).call()[-1]
            utils.col_user_collects.update_one({'_id': token},{'$set': {'state': state}})
        except web3.exceptions.ContractLogicError:
            print('[Heco][ERROR] no state for token {}'.format(token))

    def getAllCollections(self):
        all_retrieved = False
        while all_retrieved == False:
            db_token = utils.col_user_collects.find().distinct('_id')
            all_retrieved = True
            with open('contracts/contract_abi.json', 'r') as contract_abi:
                abi = json.load(contract_abi)
                # --- heco address ---
            w3 = Web3(Web3.HTTPProvider("https://http-mainnet-node.huobichain.com"))
            contract = w3.eth.contract(address=ADDRESS, abi=abi)
            total = contract.functions.expectedTokenSupply().call()
            print('[HECO][Info] HECO total supply: ', total)
            for i in range(0, total+1):
                try:
                    if i in db_token:
                        self.checkOwner(i)
                        print('[HECO][Info] token {} already existed'.format(i))
                        # --- remove checked item
                    else:
                        print('[HECO][Info] starting to retrieve: ', i)
                        stt = self.retrieveDataByToken(int(i))
                        if stt == False:
                            all_retrieved = False
                        else:
                            all_retrieved = all_retrieved
                except web3.exceptions.ContractLogicError as e:
                    print('[Heco][ERROR] token {} - {}.'.format(i, e))
                print('---------------------------------------------')
        print('[HECO][Info] All heco assets retrieved.')

    def getCollections(self, acc):
        acc = utils.checkSumAddress(acc)
        # --- get db现有的token
        db_token = utils.col_user_collects.find({'owner': acc}).distinct('_id')
        # ---
        balance = self.getBalance(acc)
        print('[Heco][USER] {} found {} assets'.format(acc, balance))
        owned_token = []
        self.in_progress.append(acc)
        for i in range(balance):
            start_time = time.time()
            token = self.contract.functions.tokenOfOwnerByIndex(acc, i).call()
            if token not in owned_token and token not in db_token:
                owned_token.append(token)
                tokens_done = self.retrieveDataByToken(token, owned_token, db_token)
                owned_token = owned_token + tokens_done if tokens_done else owned_token
                print('[Heco][INFO] retrieve token {} used {:.2f}s'.format(token, time.time()-start_time))
            else:
                # --- update owner ---
                self.checkOwner(token)
                # ----
                print('[Heco][INFO] Token {} already retrieved.'.format(token))
            if i in db_token:
                db_token.remove(i)
            # --- remove checked item
        # --- check owner for existing item but not belong for this address anymore
        for i in db_token:
            self.checkOwner(i)
        print('[Heco][INFO] {} retrieved collections.'.format(acc))
        self.in_progress.remove(acc)

    def retrieveDataByToken(self, token, owned_token=[], db_token=[]):
        def write_db():
            utils.col_user_collects.update_one({'_id': data_token},
                                               {'$set': {'owner': owner,
                                                         'type': data_type,
                                                         'name': name,
                                                         'description': description,
                                                         'create_time': create_time,
                                                         'creator': creator,
                                                         'hash': data_hash,
                                                         'canvas_token_id': canvas_token_id,
                                                         'state': state,
                                                         'motype': motype,
                                                         'label': LABEL
                                                         },
                                                '$push': {'file_main': file,
                                                          'file_preview': preview_file}}, upsert=True)
        if not db_token:
            db_token = utils.col_user_collects.find().distinct('_id')
        tokens_done = []
        print('[Heco][retrieveDataByToken] ', token)
        try:
            url = self.contract.functions.tokenURI(token).call()
        except web3.exceptions.ContractLogicError as e:
            raise web3.exceptions.ContractLogicError(e)
        # --- NB label API  ----
        # response = requests.post(LABEL_API, params={'arg': url})
        # --- mypinta API ---
        try:
            if 'mypinata.cloud' in url:
                response = requests.get(url, timeout=7, verify=False)
            else:
                response = requests.get(PINATA_API + url, timeout=7, verify=False)
        except requests.exceptions.ReadTimeout as e:
            print(e)
            return False
        if response.status_code == 200:
            data = response.json()
            print(data)
            # ----
            data_token = data['token_id']
            data_hash = data['hash']
            data_type = data['type']
            name = data['name']
            creator = data['creator']
            description = data['introduce'] if 'introduce' in data else data['description']
            canvas_token_id = data['canvas_token_id']
            create_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(str(data['create_time'])[:10])))
            owner = self.contract.functions.ownerOf(token).call()
            state = self.contract.functions.getControlToken(token).call()[-1] if data_type == 'layer' else 0
            if data_type == 'canvas':
                for token in data_hash:
                    if token not in owned_token and token not in db_token:
                        print('[Heco][Additional] retrieving, ', token)
                        self.retrieveDataByToken(token)
                        tokens_done.append(token)
                file = ''
                preview_file = ''
                motype = 'textrue'
                write_db()
            else:
                for single_hash in data_hash:
                    try:
                        response = requests.get(PINATA_API + single_hash, stream=True, verify=False, timeout=20)
                        r_type = response.headers['content-type'].split('/')[1].split(';')[0]
                        r_type = 'mp4' if response.headers['content-type'].split('/')[0] == 'video' else r_type
                        # r_type = 'mov' if response.headers['content-type'].split('/')[1] == 'quicktime' else r_type
                        if response.status_code == 200:
                            temp = single_hash + '.' + r_type
                            file = str(token) + '-' + single_hash + '.' + r_type
                            utils.mkdir('HECO', utils.DB_PATH)
                            utils.mkdir(owner, utils.DB_PATH + 'HECO/')
                            start = time.time()
                            with open('{}HECO/{}/{}'.format(utils.DB_PATH, owner, temp), 'wb') as f:
                                for chunk in response.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)
                            # ----- resize ---
                            old_path = '{}HECO/{}/{}'.format(utils.DB_PATH, owner, temp)
                            new_path = '{}HECO/{}/{}'.format(utils.DB_PATH, owner, file)
                            utils.resize(old_path=old_path, new_path=new_path, asset_type=r_type)
                            os.remove(old_path)
                            # ----------------
                            if r_type in ['mp4', 'mov', 'm4v']:
                                preview_file = str(token) + '-' + single_hash + '.' + 'jpg'
                            else:
                                preview_file = ''

                            print('[Heco][Write Chunk] {}s'.format(time.time() - start))
                            print('[Heco][FILE] {} saved'.format(file))
                            if r_type.lower() == 'html':
                                motype = 'html'
                            elif r_type.lower() == 'svg':
                                motype = 'svg'
                            else:
                                motype = 'video' if response.headers['content-type'].split('/')[0] == 'video' else 'textrue'
                            write_db()
                    except requests.exceptions.ReadTimeout:
                        print('[Heco][Connection error] Pinata manual read time out!')
            return tokens_done
        else:
            print('[Heco][ERROR] data node connection error state {}!'.format(response))
            return False



