import requests
import shutil
import re
import time
import pymongo
# -------
import utils
# -------
import warnings
warnings.filterwarnings('ignore')

# --- database ---
client = pymongo.MongoClient('127.0.0.1', 27017)
ting_db = client.meseum
col_user_collects_openseadata = ting_db.user_collects_openseadata
LABEL = 'opensea'
ACCOUNT = '0xb3866e0292D10eE4bf69534479b5113697D1c681'  # test new address


class OpenSea(object):
    def __init__(self, ):
        self.opensea_url = 'https://api.opensea.io/api/v1/assets'
        self.header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.97'}

    def downloadAssets(self, acc):
        def writedb():
            col_user_collects_openseadata.update_one({'_id': opensea_id},
                                                     {'$set': {'owner': ACCOUNT,
                                                               'name': name_asset,
                                                               'description': desc,
                                                               'create_time': create_time,
                                                               'creator': creator,
                                                               'opensea_link': opensea_link,
                                                               'url_img': url_img,
                                                               'url_ori_img': url_ori_img,
                                                               'url_animation': url_animation,
                                                               'url_ori_animation': url_ori_animation,
                                                               'img_type': type_img,
                                                               'animation_type': type_animation,
                                                               'type': asset_type,
                                                               'label': LABEL
                                                               }}, upsert=True)
        offset = 0
        limit = 50
        while True:
            print('[OpenSea] offset: ', offset)
            querystring = {"owner": acc, "order_direction": "desc", "offset": str(offset), "limit": str(limit)}
            response = requests.request("GET", self.opensea_url, headers=self.header, params=querystring)
            assets = response.json()['assets']
            print('[OpenSea] {} found {} assets'.format(acc, len(assets)))
            if len(assets) == 0:
                break
            for asset in assets:
                # name, creator, desc, dim, size, type)
                name_asset = asset['name']
                opensea_id = asset['id']
                desc = asset['description'] if asset['description'] else ''
                create_time = asset['asset_contract']['created_date'] if 'created_date' in asset['asset_contract'] else ''
                creator = asset['creator']['address'] if asset['creator'] else ''
                opensea_link = asset['permalink'] if asset['permalink'] else ''
                url_ori_img = asset['image_original_url'] if asset['image_original_url'] else asset['image_url']
                url_ori_img = url_ori_img if url_ori_img else ''
                url_ori_animation = asset['animation_original_url'] if asset['animation_original_url'] else asset['animation_url']
                url_ori_animation = url_ori_animation if url_ori_animation else ''
                url_img = asset['image_url'] if asset['image_url'] else ''
                url_animation = asset['animation_url'] if asset['animation_url'] else ''
                # ---------------------------------------------------------------------------
                if url_img and not url_animation:
                    while True:
                        try:
                            print('[INFO] starting parsing image OpenSea {}.'.format(opensea_id))
                            r = requests.get(url_img, stream=True, verify=False)
                            type_img = utils.parseType(url_img, r)
                            type_animation = ''
                            if r.status_code == 200:
                                asset_type = 'img'
                                writedb()   # write to db
                                print('[INFO] OpenSea {} wrote into db.'.format(opensea_id))
                                break
                            else:
                                print('[N-ERROR] {} status code error. {}'.format(opensea_id, img_url))
                            break
                        except requests.exceptions.SSLError as e:
                            print(e)
                            print('[ERROR] IMAGE Trying to download again....')
                        except requests.exceptions.ProxyError as e:
                            time.sleep(5)
                            print('[ERROR] ' + str(e))
                            print('[ERROR] Image trying to download again after 5s....')

                if url_animation:
                    while True:
                        try:
                            print('[INFO] starting download animation OpenSea {}.'.format(opensea_id))
                            r_animation =requests.get(animation_url, stream=True, verify=False)
                            r_img = requests.get(img_url, stream=True, verify=False)
                            animation_type = utils.parseType(animation_url, r_animation)
                            img_type = utils.parseType(animation_url, r_img)

                            if r_animation.status_code == 200 and r_img.status_code == 200:
                                asset_type = 'animation'
                                writedb() # write to db
                                print('[INFO] OpenSea animation {} wrote into db.'.format(opensea_id))
                                break
                            else:
                                print('[N-ERROR] {} status code error. {} {}'.format(opensea_id, animation_url, img_url))
                        except requests.exceptions.SSLError as e:
                            print(e)
                            print('[ERROR] MP4 Trying to download again....')
                        except requests.exceptions.ProxyError as e:
                            time.sleep(5)
                            print('[ERROR] ' + str(e))
                            print('[ERROR] MP4 trying to download again after 5s....')
                print(' -----------------------------------------------------------------------  \n')
            offset = offset + limit



op = OpenSea()
op.downloadAssets('0x9428e55418755b2f902d3b1f898a871ab5634182')