import requests
import os
import glob
import time
import shutil
import pymongo
import cv2
import mimetypes
# -------
import utils
# -------
import warnings
warnings.filterwarnings('ignore')

mimetypes.init()
# --- database ---
client = pymongo.MongoClient('127.0.0.1', 27017)
ting_db = client.meseum
col_user_collects_opensea = ting_db.user_collects_opensea
LABEL = 'opensea'
ACCOUNT = '0xb3866e0292D10eE4bf69534479b5113697D1c681'  # test new address


class OpenSea(object):
    def __init__(self, ):
        self.opensea_url = 'https://api.opensea.io/api/v1/assets'
        # self.opensea_url = 'https://opensea-data-query.p.rapidapi.com/api/v1/assets'
        self.header = {
            "Accept": "application/json",
            "X-API-KEY": "***"}
        self.inprogress = []
        print('[OpenSea][Info] OpenSea initialized.')

    def isInProgress(self, acc):
        if utils.checkSumAddress(acc) in self.inprogress:
            return True
        else:
            return False

    def downloadByAsset(self, asset, acc):
        def writedb():
            col_user_collects_opensea.update_one({'_id': opensea_id},
                                                 {'$set': {'owner': utils.checkSumAddress(acc),
                                                           'name': name_asset,
                                                           'description': desc,
                                                           'create_time': create_time,
                                                           'creator': utils.checkSumAddress(creator) if creator else '',
                                                           'opensea_link': opensea_link,
                                                           'contract_name': contract_name,
                                                           'contract_address': contract_address,
                                                           'contract_type': contract_type,
                                                           'contract_token': contract_token,
                                                           'contract_external_link': contract_external_link,
                                                           'url_img': url_img,
                                                           'url_ori_img': url_ori_img,
                                                           'url_animation': url_animation,
                                                           'url_ori_animation': url_ori_animation,
                                                           'type_img': type_img,
                                                           'type_animation': type_animation,
                                                           'type': asset_type,
                                                           'motype': motype,  # 3Dstatus
                                                           'label': LABEL
                                                           }}, upsert=True)

        # name, creator, desc, dim, size, type)
        opensea_id = asset['id']
        name_asset = asset['name']
        desc = asset['description'] if asset['description'] else ''
        create_time = asset['asset_contract']['created_date'] if 'created_date' in asset['asset_contract'] else ''
        creator = asset['creator']['address'] if asset['creator'] else ''
        opensea_link = asset['permalink'] if asset['permalink'] else ''
        contract_name = asset['asset_contract']['name'] if 'name' in asset['asset_contract'] else ''
        contract_address = asset['asset_contract']['address'] if 'address' in asset['asset_contract'] else ''
        contract_type = asset['asset_contract']['schema_name'] if 'schema_name' in asset['asset_contract'] else ''
        contract_token = asset['token_id']
        contract_external_link = asset['external_link'] if asset['external_link'] else ''
        url_ori_img = asset['image_original_url'] if asset['image_original_url'] else asset['image_url']
        url_ori_img = url_ori_img if url_ori_img else ''
        url_ori_animation = asset['animation_original_url'] if asset['animation_original_url'] else asset['animation_url']
        url_ori_animation = url_ori_animation if url_ori_animation else ''
        url_img = asset['image_url'] if asset['image_url'] else ''
        url_animation = asset['animation_url'] if asset['animation_url'] else ''
        # ---------------------------------------------------------------------------
        utils.mkdir('opensea', utils.DB_PATH)
        opensea_path = utils.DB_PATH + LABEL + '/'
        utils.mkdir(acc, opensea_path)
        if url_img and not url_animation:
            while True:
                try:
                    print('[OpenSea][INFO] starting download image {}-{}-{}.'.format(opensea_id, contract_name, contract_token))
                    start_time = time.time()
                    r_img =requests.get(url_img, stream=True, verify=False)
                    re_get_time = time.time()
                    type_img = utils.parseType(url_img, r_img)
                    type_animation = ''
                    file_img = str(opensea_id) + '.' + type_img

                    if r_img.status_code == 200:
                        r_img.raw.decode_content = True
                        with open('{}/{}/{}'.format(opensea_path, acc, file_img), 'wb') as f:
                            for chunk in r_img.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)
                        print('[OpenSea][FILE] {} saved'.format(file_img))
                        if 'video' in mimetypes.guess_type(file_img)[0]:
                            type_animation = type_img
                            type_img = 'jpg'
                            file_animation = file_img
                            vid = cv2.VideoCapture('{}/{}/{}'.format(opensea_path, acc, file_animation))
                            total_frame = vid.get(cv2.CAP_PROP_FRAME_COUNT)
                            vid.set(1, total_frame//2)
                            flag, frame = vid.read()
                            file_img = str(opensea_id) + '.' + type_img
                            cv2.imwrite('{}/{}/{}'.format(opensea_path, acc, file_img), frame)
                            asset_type = 'animation'
                            motype = 'video'
                        else:
                            asset_type = 'img'
                            if type_img.lower() == 'html':
                                motype = 'html'
                            elif type_img.lower() == 'svg':
                                motype = 'svg'
                            else:
                                motype = 'textrue'
                        writedb()   # write to db
                        print('[OpenSea][INFO] Requests.get used {:.2f}s. Handling data used {:.2f}s.'.format(re_get_time-start_time, time.time()-re_get_time))
                        break   # leave loot successfully.
                    else:
                        print('[OpenSea][N-ERROR] {} status code error. {}'.format(opensea_id, url_img))
                except requests.exceptions.SSLError as e:
                    print(e)
                    print('[OpenSea][ERROR] IMAGE Trying to download again....')
                except requests.exceptions.ProxyError as e:
                    time.sleep(5)
                    print('[OpenSea][ERROR] ' + str(e))
                    print('[OpenSea][ERROR] Image trying to download again after 5s....')

        if url_animation:
            while True:
                try:
                    print('[OpenSea][INFO] starting download video {}-{}-{}.'.format(opensea_id, contract_name, contract_token))
                    start_time = time.time()
                    print(url_animation)
                    print(url_img)
                    r_animation = requests.get(url_animation, stream=True, verify=False)
                    r_img = requests.get(url_img, stream=True, verify=False)
                    re_get_time = time.time()
                    type_img = utils.parseType(url_img, r_img)
                    type_animation = utils.parseType(url_animation, r_animation)
                    file_animation = str(opensea_id) + '.' + type_animation
                    file_img = str(opensea_id) + '.' + type_img
                    if r_animation.status_code == 200 and r_img.status_code == 200:
                        r_animation.raw.decode_content = True
                        with open('{}/{}/{}'.format(opensea_path, acc, file_animation), 'wb') as f:
                            for chunk in r_animation.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)
                        with open('{}/{}/{}'.format(opensea_path, acc, file_img), 'wb') as f:
                            for chunk in r_img.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)
                        print('[OpenSea][FILE] {} saved'.format(file_animation))
                        print('[OpenSea][FILE] {} saved'.format(file_img))
                        asset_type = 'animation'
                        if type_animation.lower() == 'html':
                            motype = 'html'
                        elif type_animation.lower() == 'svg':
                            motype = 'svg'
                        else:
                            motype = 'video'
                        writedb() # write to db
                        print('[OpenSea][INFO] Requests.get used {:.2f}s. Handling data used {:.2f}s.'.format(re_get_time-start_time, time.time()-re_get_time))
                        break
                    else:
                        print('[OpenSea][N-ERROR] {} status code error. {} {}'.format(opensea_id, url_animation, url_img))
                except requests.exceptions.SSLError as e:
                    print(e)
                    print('[OpenSea][ERROR] MP4 Trying to download again....')
                except requests.exceptions.ProxyError as e:
                    time.sleep(5)
                    print('[OpenSea][ERROR] ' + str(e))
                    print('[OpenSea][ERROR] MP4 trying to download again after 5s....')
                except requests.exceptions.MissingSchema as e:
                    print('[OpenSea][FATAL_ERROR] {}'.format(e))
                    break
        print('[OpenSea] -----------------------------------------------------------------------  \n')

    def downloadAssets(self, acc):
        acc = utils.checkSumAddress(acc)
        self.inprogress.append(acc)
        offset = 0
        limit = 50
        db_owned = col_user_collects_opensea.find({'owner': acc}).distinct('_id')
        while True:
            print('[OpenSea] offset: ', offset)
            querystring = {"owner": acc, "order_direction": "desc", "offset": str(offset), "limit": str(limit)}
            response = requests.request("GET", self.opensea_url, headers=self.header, params=querystring)
            # print(response)
            # print(response.json())
            assets = response.json()['assets']
            print('[OpenSea] found {} assets'.format(len(assets)))
            if len(assets) == 0:
                break
            for asset in assets:
                opensea_id = asset['id']
                cursor = col_user_collects_opensea.find({'_id': opensea_id})
                if opensea_id in db_owned:
                    db_owned.remove(opensea_id)
                if cursor.count() == 0:
                    self.downloadByAsset(asset=asset, acc=acc)
                else:
                    pre_owner = cursor[0]['owner']
                    if pre_owner != acc:
                        utils.mkdir(acc, utils.DB_PATH + LABEL + '/')  # new folder: very important
                        pre_path = utils.DB_PATH + LABEL + '/' + pre_owner + '/'
                        new_path = utils.DB_PATH + LABEL + '/' + acc + '/'
                        files = glob.glob(pre_path + str(opensea_id) + '*')
                        for file in files:
                            try:
                                shutil.move(file, new_path)
                            except shutil.Error:
                                os.remove(file)
                            col_user_collects_opensea.update_one({'_id': opensea_id},
                                                                 {'$set': {'owner': acc}})
                            print('[OpenSea][INFO] OpenSea {} file moved to new owner.'.format(opensea_id))
                    print('[OpenSea][INFO] {} existed.'.format(opensea_id))
                    print('[OpenSea] ----------------------------------------------------------------------- ')
            offset = offset + limit
        for _id in db_owned:
            for single_path in glob.glob(utils.DB_PATH + LABEL + '/' + acc + '/' + str(_id) + '*'):
                os.remove(single_path)
                col_user_collects_opensea.delete_one({'_id': _id})
                print('[OpenSea][INFO] {} deleted {}.'.format(acc, single_path))
        self.inprogress.remove(acc)
