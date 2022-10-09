# -*- coding: utf-8 -*-
# author: Ellis Lam
import mimetypes
import os

import flask
from flask import request
from flask_cors import *
import json
import pymongo
import copy
from datetime import datetime
import threading
from bson.objectid import ObjectId
import time
import glob
import ast
import argparse
from itertools import chain
import random
# --- local
import utils
from contracts import opensea
from contracts import heco
from contracts import opensea_tm
from contracts import poap_xdai
import database
# --- warning
import warnings
warnings.filterwarnings('ignore')
# --- setting argparser ---
parser = argparse.ArgumentParser(prog='Flask API for Ting Museum',
                                 usage='[optionals] Example: python3 main.py')
parser.add_argument('--host', metavar='', type=str, default='localhost', help='Input localhost or host X.X.X.X')
args, unknown = parser.parse_known_args()
# --- connect to db ---
client = pymongo.MongoClient('127.0.0.1', 27017)
ting_db = client.meseum
col_user_page = ting_db.user_page       # user_page collection in db
col_follow_state = ting_db.follow_state
col_user_collects = ting_db.user_collects
col_user_exhibition = ting_db.user_exhibition
col_collects_state = ting_db.collects_state
col_collects_state_opensea = ting_db.collects_state_opensea
col_user_collects_opensea = ting_db.user_collects_opensea
col_user_collects_notmint = ting_db.user_collects_notmint
HOST = '0.0.0.0' if args.host == 'localhost' else args.host.lower()
# --- flask server ----
server = flask.Flask(__name__, static_folder=utils.DB_PATH)
CORS(server, supports_credetials=True)
# --- HECO & Opensea agent ---
heco_agent = heco.hecoContract()
open_agent = opensea.OpenSea()
tm_agent = opensea_tm.OpenSea_Collection()
poap_agent = poap_xdai.Poap_xDai()

# --- USER STATE --------------
@server.route("/retrieve_personal_collections", methods=['POST'])
def retrieve_personal_collections():
    data = request.get_json()
    user_address = data['user_address']
    user_address = utils.checkSumAddress(user_address)
    if heco_agent.isInProgress(user_address):
        print('[USER] {} has been retrieving collections.'.format(user_address))
    else:
        # --- retrieve account user_address collections
        threading.Thread(target=heco_agent.getCollections, args=(user_address, )).start()
    if open_agent.isInProgress(user_address):
        print('[USER] {} has been retrieving collections.'.format(user_address))
    else:
        # --- retrieve account user_address collections
        threading.Thread(target=open_agent.downloadAssets, args=(user_address, )).start()
    # --- retrieve poap collections
    threading.Thread(target=poap_agent.getCollections, args=(user_address, )).start()
    threading.Thread(target=poap_agent.getCollections, args=(user_address,)).start()
    return flask.Response(response='{} in process.'.format(user_address))


@server.route("/save_sincetime_info", methods=['POST'])
def save_sincetime_info():
    data = request.get_json()
    user_address = data['user_address']
    user_address = utils.checkSumAddress(user_address)
    # ----
    new_data = copy.copy(utils.user_dict)
    # new_data['username'] = user_address
    new_data['image_avatar'] = 'ting_museum_database/avatar/default.jpeg'
    new_data['since_time'] = datetime.now().__str__()
    print(new_data['since_time'])
    query = {'_id': user_address,
             'since_time': {'$exists': True}}               # mongodb query
    exist_ct = col_user_page.count_documents(query)
    if exist_ct == 0:
        print('[USER] {} user default info inserted.'.format(user_address))
        col_user_page.update_one({'_id': user_address}, {'$set': new_data}, upsert=True)
        return flask.Response(response='[INFO] user first time info inserted.', status=200)
    else:
        print('[USER] {} first time existed.'.format(user_address))
        return flask.Response(response='[INFO] user existed.', status=200)


@server.route("/save_personal_info", methods=['POST'])
def save_personal_info():
    database.save_personal_info(form=request.form, avatar=request.files['image_avatar'] if 'image_avatar' in request.files else None)
    return flask.Response(response='[INFO] personal info saved.', status=200)


@server.route("/save_coverpage_info", methods=['POST'])
def save_coverpage_info():
    if 'image_coverpage' in request.files:
        user_address = request.form['user_address']
        cover_page = request.files['image_coverpage']
        # ---
        file_path = database.save_cover_page(acc=user_address, cover_page=cover_page)
        # ---
        print('[USER] {} cover page saved'.format(user_address))
        return flask.Response(response=file_path, status=200)
    else:
        return flask.Response(response='Unsuccessful.', status=201)


@server.route("/get_personal_avatars", methods=['POST'])
def get_personal_avatars():
    user_address = request.form['user_address']     # a list of user_addresses
    if user_address:
        user_address = [user_address] if type(user_address) == str else user_address
        acc_avatars = database.get_avatars(user_address)
        return json.dumps(acc_avatars)
    else:
        return flask.Response(status=501)


@server.route("/get_user_info", methods=['GET'])
def get_user_info():
    user_address = request.args.get("user_address")
    user_address = utils.checkSumAddress(user_address)
    cursor = col_user_page.find({'_id': user_address})
    for data in cursor:
        # --- plus one visited
        col_user_page.update_one({'_id': data['_id']}, {'$inc': {'visited': 1}})
        # ---
        user_dict = {'_id': data['_id'],
                     'username': data['username'],
                     'description': data['description'],
                     'personal_url': data['personal_url'],
                     'image_avatar': data['image_avatar'],
                     'facebook_url': data['facebook_url'],
                     'twitter_url': data['twitter_url'],
                     'instagram_url': data['instagram_url'],
                     'pinter_url': data['pinter_url'],
                     'image_coverpage': data['image_coverpage'],
                     'since_time': str(data['since_time'])}
        print('[USER] user info retrieved: ', user_address)
        return json.dumps(user_dict)
    return flask.Response(status=500)


# --- get all user page
@server.route("/get_all_user", methods=['POST'])
def get_all_user():
    cursor = col_user_page.find()
    ids = []
    ava = []
    name = []
    for i in cursor:
        ids.append(i['_id'])
        ava.append(i['image_avatar'])
        name.append(i['username'] if 'username' in i else '')
    # return dict(zip(ids, ava))
    return json.dumps(dict(zip(ids, zip(ava, name))))

@server.route("/get_all_user_test", methods=['POST'])
def get_all_user_test():
    cursor = utils.col_user_page.find()
    res = dict()
    for data in cursor:
        res[data['_id']] = {'username': data['username'],
                            'image_avatar': data['image_avatar'],
                            'image_coverpage': data['image_coverpage'],
                            'description': data['description'],
                            'count_museum': utils.col_user_exhibition.find({'user_address': data['_id']}).count(),
                            'count_nft': utils.col_user_collects.find({'owner': data['_id']}).count() + utils.col_user_collects_opensea.find({'owner': data['_id']}).count(),
                            'count_poap': utils.col_user_collects_poap_xdai.find({'owner': data['_id']}).count()
                            }
    return json.dumps(res)


@server.route("/get_skins_all_exhibition/<filter>", methods=['POST'])
def get_skins_all_exhibition(filter):
    limit = 6
    page = request.form['page'] if 'page' in request.form else 1
    if filter:
        cursor = col_user_exhibition.find({'museum_type': filter}).sort('visited', pymongo.DESCENDING)
    else:
        cursor = col_user_exhibition.find()
    cursor_tmp = cursor.__copy__()
    total_page = cursor.count() // limit + (0 if cursor.count() % limit == 0 else 1)
    tmp = []
    for cur in cursor_tmp:
        tmp.append(cur)
    # --- set page and index for retrieve data in mongodb
    page = int(page) if page else 1
    id_range = [i for i in range((page-1) * limit, min(cursor.count(), limit * page))]
    collects_dict = dict(count=cursor.count(), total_page=total_page, page=0, data=[])

    cursor_return = col_user_exhibition.find({'museum_type': filter}).sort('visited', pymongo.DESCENDING)[(page-1) * limit: min(cursor.count(), limit * page)]
    for i in id_range:
        museum_dict = copy.copy(utils.museum_dict)
        data = tmp[i]
        # data = tmp[i]
        # print(data['name'])
        # print(data['visited'])
        museum_dict['museum_id'] = data['_id'].__str__()
        museum_dict['name'] = data['name']
        museum_dict['creator_username'] = col_user_page.find({'_id': data['user_address']}).distinct('username')
        museum_dict['creator_username'] = museum_dict['creator_username'] if museum_dict['creator_username'] else ''
        museum_dict['participant'] = data['participant']
        # museum_dict['participant_avatar'] = col_user_page.find({'_id': {'$in': data['participant']}}).distinct('image_avatar')
        museum_dict['participant_avatar'] = []
        for address in museum_dict['participant']:
            tmp_avatar = col_user_page.find({'_id': address}).distinct('image_avatar')
            if tmp_avatar:
                museum_dict['participant_avatar'].append(tmp_avatar)
            else:
                museum_dict['participant_avatar'].append(utils.UNKNOWN_AVATAR)
        museum_dict['image_banner'] = data['image_banner']
        museum_dict['description'] = data['description']
        museum_dict['museum_type'] = data['museum_type']
        collects_dict['data'].append(museum_dict)
    print('--------------------------------------')
    collects_dict['page'] = page
    return json.dumps(collects_dict)


@server.route("/get_all_exhibition", methods=['POST'])
def get_all_exhibition():
    limit = 16
    page = request.form['page'] if 'page' in request.form else 1
    cursor = col_user_exhibition.find()
    total_page = cursor.count() // limit + (0 if cursor.count() % limit == 0 else 1)
    # --- set page and index for retrieve data in mongodb
    page = int(page) if page else 1
    id_range = [i for i in range((page-1) * limit, min(cursor.count(), limit * page))]
    collects_dict = dict(count=cursor.count(), total_page=total_page, page=0, data=[])
    for i in id_range:
        museum_dict = copy.copy(utils.museum_dict)
        data = cursor[i]
        museum_dict['museum_id'] = data['_id'].__str__()
        museum_dict['name'] = data['name']
        museum_dict['participant'] = data['participant']
        # museum_dict['participant_avatar'] = col_user_page.find({'_id': {'$in': data['participant']}}).distinct('image_avatar')
        museum_dict['participant_avatar'] = []
        for address in museum_dict['participant']:
            tmp_avatar = col_user_page.find({'_id': address}).distinct('image_avatar')
            if tmp_avatar:
                museum_dict['participant_avatar'].append(tmp_avatar)
            else:
                museum_dict['participant_avatar'].append(utils.UNKNOWN_AVATAR)
        museum_dict['image_banner'] = data['image_banner']
        museum_dict['description'] = data['description']
        museum_dict['museum_type'] = data['museum_type']
        collects_dict['data'].append(museum_dict)
    collects_dict['page'] = page
    return json.dumps(collects_dict)


# --- follow state ---
@server.route('/get_follow', methods=['GET'])
def get_follow():
    user_address = request.args.get("user_address")
    current_address = request.args.get("current_address")
    user_address = utils.checkSumAddress(user_address)
    current_address = utils.checkSumAddress(current_address)
    follow_dict = {'count_follower': 0,
                   'count_following': 0,
                   'follower': [],
                   'following': [],
                   'isFollowing': False}
    try:
        follow_stat = col_follow_state.find({'_id': current_address})[0]
        count_follower = len(follow_stat['follower']) if 'follower' in follow_stat else 0
        count_following = len(follow_stat['following']) if 'following' in follow_stat else 0
        follow_dict['count_follower'] = count_follower
        follow_dict['count_following'] = count_following
        follow_dict['follower'] = follow_stat['follower'] if 'follower' in follow_stat else []
        follow_dict['following'] = follow_stat['following'] if 'following' in follow_stat else []
        follow_dict['following_avatars'] = database.get_avatars(follow_stat['following']) if 'following' in follow_stat else []
        follow_dict['follower_avatars'] = database.get_avatars(follow_stat['follower']) if 'follower' in follow_stat else []
        if user_address in follow_dict['follower']:
            follow_dict['isFollowing'] = True
        return json.dumps(follow_dict)
    except IndexError:
        return json.dumps(follow_dict), 200


@server.route('/follow_current', methods=['POST'])
def user_follow():
    data = request.get_json()
    user_address = data['user_address']
    if user_address:
        current_address = data['current_address']
        user_address = utils.checkSumAddress(user_address)
        current_address = utils.checkSumAddress(current_address)
        # --- push following and follower
        if user_address == current_address:
            return flask.Response(status=400)
        if col_follow_state.count_documents({'_id': user_address, 'following': current_address}) == 0:
            col_follow_state.update_one({"_id": user_address}, {'$push': {'following': current_address}}, upsert=True)
            col_follow_state.update_one({"_id": current_address}, {'$push': {'follower': user_address}}, upsert=True)
        return flask.Response(status=200)
    else:
        return flask.Response(status=500)


@server.route('/unfollow_current', methods = ['POST'])
def user_unfollow():
    data = request.get_json()
    user_address = data['user_address']
    current_address = data['current_address']
    user_address = utils.checkSumAddress(user_address)
    current_address = utils.checkSumAddress(current_address)
    # --- pull following and follower
    col_follow_state.update_one({"_id": user_address}, {'$pull': {'following': current_address}}, upsert=True)
    col_follow_state.update_one({"_id": current_address}, {'$pull': {'follower': user_address}}, upsert=True)
    return flask.Response(status=200)


@server.route('/get_collects/<filters>', methods=['GET'])
def get_collects(filters):
    limit = 8
    user_address = request.args.get("user_address")
    user_address = utils.checkSumAddress(user_address)
    current_address = request.args.get("current_address")
    current_address = utils.checkSumAddress(current_address)
    if request.args.get('limit'):
        limit = int(request.args.get('limit'))
    # current_address = '0xD0113dc737FACDdc6996679eeAF87e7fc1C86278'          # !!! immutable condition
    # current_address = '0xB5a3B5D99880c4903c035F7afccF2BC074fC1d32'        # icarus IcarusArt
    page = request.args.get('page')
    if filters == 'owned':  # this is heco!!!
        if current_address in utils.ACCESS_AUTHORITY:
            cursor = col_user_collects.find().sort('name')
            cursor_notmint = col_user_collects_notmint.find()
        elif current_address in utils.UPLOAD_AUTHORITY:
            cursor = col_user_collects_notmint.find()
        else:
            cursor = col_user_collects.find({'owner': current_address}).sort('name')
    elif filters == 'opensea':
        if current_address in utils.ACCESS_AUTHORITY:
            cursor = col_user_collects_opensea.find().sort('name')
        else:
            cursor = col_user_collects_opensea.find({'owner': current_address})
    elif filters == 'liked':
        ids_heco = col_collects_state.find({'liked_by': current_address}).distinct('_id')
        cursor_heco = col_user_collects.find({'_id': {'$in': ids_heco}})
        ids_opensea = col_collects_state_opensea.find({'liked_by': current_address}).distinct('_id')
        cursor_opensea = col_user_collects_opensea.find({'_id': {'$in': ids_opensea}})
    elif filters == 'poap':
        if current_address:
            addr = current_address
        elif user_address:
            addr = user_address
        # if addr in utils.ACCESS_AUTHORITY:
        #     cursor = utils.col_user_collects_poap_xdai.find()
        # else:
        cursor = utils.col_user_collects_poap_xdai.find({'owner': addr})
    elif filters == 'music':
        if current_address:
            addr = current_address
        elif user_address:
            addr = user_address
        cursor = utils.col_user_collects_music.find({'owner': addr})

    count_all_cursor = cursor_heco.count() + cursor_opensea.count() if filters == 'liked' else cursor.count()
    count_all_cursor = count_all_cursor + cursor_notmint.count() if filters == 'owned' and current_address in utils.ACCESS_AUTHORITY else count_all_cursor
    total_page = count_all_cursor // limit + (0 if count_all_cursor % limit == 0 else 1)
    # --- set page and index for retrieve data in mongodb
    page = int(page) if page else 1
    # --- check page is overloaded ---
    if (page-1) * limit > min(count_all_cursor, limit * page):
        return flask.Response(response='No more page!', status=401)
    id_range = [i for i in range((page-1) * limit, min(count_all_cursor, limit * page))]
    collects_dict = dict(count=0, total_page=0, page=1, data=[])

    print('[COLLECTIONS] user {} retrieved {} collections in database.'.format(current_address, count_all_cursor))
    if count_all_cursor == 0:
        return json.dumps(collects_dict)
    elif filters == 'owned':
        if current_address in utils.ACCESS_AUTHORITY:
            chain_cursor = [x for x in chain(cursor, cursor_notmint)]
        else:
            chain_cursor = cursor
        for i in id_range:
            collect_dict = database.get_collects_heco(user_address, chain_cursor[i])
            # --- to the global json
            collects_dict['data'].append(collect_dict)
    elif filters == 'opensea':
        for i in id_range:
            collect_dict = database.get_collects_opensea(user_address, cursor[i])
            # --- to the global json
            collects_dict['data'].append(collect_dict)
    elif filters == 'poap':
        for i in id_range:
            collect_dict = database.get_collects_poap(None, cursor[i])
            collects_dict['data'].append(collect_dict)
    collects_dict['count'] = count_all_cursor
    collects_dict['total_page'] = total_page
    collects_dict['page'] = page

    if filters == 'liked':
        cursor_merge = [x for x in chain(cursor_heco, cursor_opensea)]
        for i in id_range:
            if cursor_merge[i]['label'].lower() == 'heco' or 'notmint':
                collect_dict = database.get_collects_heco(user_address, cursor_merge[i])
            if cursor_merge[i]['label'].lower() == 'opensea':
                collect_dict = database.get_collects_opensea(user_address, cursor_merge[i])
            collects_dict['data'].append(collect_dict)
    return json.dumps(collects_dict)


@server.route('/get_collects_single', methods=['POST'])
def get_collects_single():
    token_id = request.form['token_id']
    label = request.form['label']
    user_address = utils.checkSumAddress(request.form['user_address']) if 'user_address' in request.form else None
    # print('wtf is calling')
    print('[INFO][get_collects_single] {} {} {}'.format(label, token_id, user_address))
    print(label, token_id)
    if label.lower() == 'heco' and token_id:
        cursor = col_user_collects.find({'_id': int(token_id)})[0]
        print('[INFO] retrieve {} single {}'.format(label, token_id))
        collect_dict = database.get_collects_heco(user_address=user_address, cursor=cursor)
        # print(collect_dict)
        return json.dumps(collect_dict)
    elif label.lower() == 'notmint' and token_id:
        cursor = col_user_collects_notmint.find({'_id': int(token_id)})[0]
        print('[INFO] notmint retrieve {} single {}'.format(label, token_id))
        collect_dict = database.get_collects_heco(user_address=user_address, cursor=cursor)
        # print(collect_dict)
        return json.dumps(collect_dict)
    elif label.lower() == 'opensea' and token_id:
        cursor = col_user_collects_opensea.find({'_id': int(token_id)})[0]
        collect_dict = database.get_collects_opensea(user_address=user_address, cursor=cursor)
        return json.dumps(collect_dict)
    else:
        return 401


@server.route('/get_collects_skin_balance', methods=['POST'])
def get_collects_skin_balance():
    current_address = request.form['current_address']
    current_address = utils.checkSumAddress(current_address)
    total_balance = dict()
    for ehtype in opensea_tm.TOKEN:
        used = col_user_exhibition.find({'user_address': current_address, 'museum_type': ehtype}).count()

        balance = tm_agent.checkBalance(acc=current_address, ehtype=ehtype)
        total_balance[ehtype] = [used, balance]
    return json.dumps(total_balance)


@server.route('/get_collects_by_artists_address', methods=['POST'])
def get_collects_by_address():
    artist_address = request.form['artist_address']
    artist_address = utils.checkSumAddress(artist_address)
    collects = dict()
    collects['data'] = []
    asset_heco = col_user_collects.find({'creator': artist_address}).sort('name')
    asset_opensea = col_user_collects_opensea.find({'creator': artist_address}).sort('name')
    for cursor in asset_heco:
        collect_dict = database.get_collects_heco(user_address=None, cursor=cursor)
        collects['data'].append(collect_dict)
    for cursor in asset_opensea:
        collect_dict = database.get_collects_opensea(user_address=None, cursor=cursor)
        collects['data'].append(collect_dict)
    return json.dumps(collects)


# --- exhibition ---
@server.route('/add_exhibition', methods=['POST'])
def add_exhibition():
    # ---
    museum_id = database.add_exhibition(form=request.form, banner=request.files['image_banner'] if 'image_banner' in request.files else None)
    # ---321
    if museum_id == False:
        return flask.Response(response='Museum type quantity exceeded limit', status=401)
    print('new museum id built: ', museum_id)
    return json.dumps({'museum_id': museum_id})


@server.route('/edit_exhibition', methods=['POST'])
def edit_exhibition():
    # ---
    database.edit_exhibition(form=request.form, banner=request.files['image_banner'] if 'image_banner' in request.files else None)
    # ---
    return flask.Response(status=200)


@server.route('/delete_exhibition', methods=['POST'])
def delete_exhibition():
    # ---
    database.delete_exhibition(form=request.form)
    # ---
    return flask.Response(status=200)


@server.route('/add_participant/<options>', methods=['POST'])
def add_participant(options):
    # ---
    museum_id = request.form['museum_id']
    target_address = request.form['target_address']
    print('Add participant , ', target_address)
    target_address = utils.checkSumAddress(target_address)
    print('Add participant , ', target_address)
    # ---
    # return 409 == conflict
    if options == 'add':
        if col_user_exhibition.count_documents({'_id': ObjectId(museum_id), 'participant': target_address}):
            return flask.Response(response='Address already in participant.', status=409)
        else:
            col_user_exhibition.update({'_id': ObjectId(museum_id)}, {'$push': {'participant': target_address}}, upsert=True)
            participant = col_user_exhibition.find({'_id': ObjectId(museum_id)}).distinct('participant')
            avatars = database.get_avatars(participant)
            return json.dumps(avatars)
    elif options == 'delete':
        c = col_user_exhibition.find({'_id': ObjectId(museum_id)})[0]
        if target_address == c['user_address']:
            return flask.Response(response='Cannot remove yourself!', status=409)
        elif target_address not in c['participant']:
            return flask.Response(response='Address not in participant!', status=409)
        else:
            col_user_exhibition.update_one({'_id': ObjectId(museum_id)}, {'$pull': {'participant': target_address}})


# --- personal page show personal exhibiton ---
@server.route('/show_exhibition', methods=['GET'])
def show_exhibition():
    limit = 8
    current_address = request.args.get('current_address')
    if not current_address:
        return flask.Response(status=401)
    else:
        current_address = utils.checkSumAddress(current_address)
        page = request.args.get('page')
        cursor = col_user_exhibition.find({'$or': [{'user_address': current_address}, {'participant': {'$in': [current_address]}}]})
        total_page = cursor.count() // limit + (0 if cursor.count() % limit == 0 else 1)
        # --- set page and index for retrieve data in mongodb
        page = int(page) if page else 1
        id_range = [i for i in range((page-1) * limit, min(cursor.count(), limit * page))]
        collects_dict = dict(count=cursor.count(), total_page=total_page, page=0, data=[])
        for i in id_range:
            museum_dict = copy.copy(utils.museum_dict)
            data = cursor[i]
            museum_dict['museum_id'] = data['_id'].__str__()
            museum_dict['name'] = data['name']
            museum_dict['participant'] = data['participant']
            # museum_dict['participant_avatar'] = col_user_page.find({'_id': {'$in': data['participant']}}).distinct('image_avatar')
            museum_dict['participant_avatar'] = []
            for address in museum_dict['participant']:
                tmp_avatar = col_user_page.find({'_id': address}).distinct('image_avatar')
                if tmp_avatar:
                    museum_dict['participant_avatar'].append(tmp_avatar)
                else:
                    museum_dict['participant_avatar'].append(utils.UNKNOWN_AVATAR)
            museum_dict['image_banner'] = data['image_banner']
            museum_dict['description'] = data['description']
            museum_dict['museum_type'] = data['museum_type']
            museum_dict['windymuse_visited'] = utils.col_musicfi_firsttime.count_documents({'museum_id': data['_id'].__str__()})
            collects_dict['data'].append(museum_dict)
        collects_dict['page'] = page
        return json.dumps(collects_dict)


@server.route('/save_exhibition', methods=['POST'])
def save_exhibition():
    museum_id = request.form['museum_id']
    prod = request.form['prod']
    prod = ast.literal_eval(prod) if type(prod) == str else prod
    print(museum_id)
    print(prod)
    print(type(prod))
    for i in list(prod):
        if len(prod[i]) == 0:
            del prod[i]
    for i in prod:
        prod[i]['url'] = prod[i]['url'][prod[i]['url'].find('ting_museum_database'):]
        print('save_exhibition only left ', i, prod[i])
    # ---
    col_user_exhibition.update({'_id':  ObjectId(museum_id)}, {'$set': prod})
    return flask.Response(response='museum saved', status=200)


@server.route('/enter_museum', methods=['POST'])
def enter_museum():
    museum_id = str(request.form['museum_id'])
    # user_address = request.form['user_address']
    if col_user_exhibition.find({'_id':  ObjectId(museum_id)}).count() > 0:
        col_user_exhibition.update_one({'_id':  ObjectId(museum_id)}, {'$inc': {'visited': 1}}, upsert=True)
    print('[INFO] enter museum...', museum_id)
    if col_user_exhibition.count_documents({'_id': ObjectId(museum_id)}):
        cursor = col_user_exhibition.find({'_id': ObjectId(museum_id)})
        data = cursor[0]
        data['_id'] = data['_id'].__str__()
        # print(data)
        for i in range(1, 25):
            if (data['Product_{}'.format(i)]['token_id']) and (data['Product_{}'.format(i)]['label'].lower() == 'heco' or data['Product_{}'.format(i)]['label'].lower() == 'notmint'):
                print('heco/notmint', data['Product_{}'.format(i)]['token_id'])
                if data['Product_{}'.format(i)]['label'].lower() == 'heco':
                    cursor_token = col_user_collects.find({'_id': int(data['Product_{}'.format(i)]['token_id'])})
                elif data['Product_{}'.format(i)]['label'].lower() == 'notmint':
                    cursor_token = col_user_collects_notmint.find({'_id': int(data['Product_{}'.format(i)]['token_id'])})
                print(data['Product_{}'.format(i)]['label'].lower())
                c = database.get_collects_heco(None, cursor_token[0])
                data['Product_{}'.format(i)]['url'] = c['data'][0]
                data['Product_{}'.format(i)]['preview'] = c['preview'][0]
                data['Product_{}'.format(i)]['name'] = c['name']
                data['Product_{}'.format(i)]['creator'] = c['creator']
                data['Product_{}'.format(i)]['creator_username'] = c['creator_username']
                data['Product_{}'.format(i)]['description'] = c['description']
                data['Product_{}'.format(i)]['firststate'] = 0
            elif data['Product_{}'.format(i)]['token_id'] and data['Product_{}'.format(i)]['label'].lower() == 'opensea':
                print('opensea', data['Product_{}'.format(i)]['token_id'])
                cursor_token = col_user_collects_opensea.find({'_id': int(data['Product_{}'.format(i)]['token_id'])})
                c = database.get_collects_opensea(None, cursor_token[0])
                data['Product_{}'.format(i)]['preview'] = c['data_img'][0]
                data['Product_{}'.format(i)]['url'] = c['data_animation'][0] if 'data_animation' in c else c['data_img'][0]
                data['Product_{}'.format(i)]['name'] = c['name']
                data['Product_{}'.format(i)]['creator'] = c['creator']
                data['Product_{}'.format(i)]['creator_username'] = c['creator_username']
                data['Product_{}'.format(i)]['description'] = c['description']
                data['Product_{}'.format(i)]['firststate'] = 0
        return json.dumps(data)
    else:
        return flask.Response(response='museum does not exist', status=400)


# --- collections state ---
@server.route('/collections_state/<platform>/<operation>', methods=['POST'])
def collections_state(platform, operation):
    if operation.lower() == 'like':
        status = database.like_collection(platform, form=request.form)
    elif operation.lower() == 'unlike':
        status = database.unlike_collection(platform, form=request.form)
    elif operation.lower() == 'favor':
        status = database.favor_collection(platform, form=request.form)
    elif operation.lower() == 'unfavor':
        status = database.unfavor_collection(platform, form=request.form)
    return flask.Response(status=200) if status == 200 else flask.Response(status=409)



# --- upload not mint ---
@server.route('/upload_notmint', methods=['POST'])
def upload_notmint():
    user_address = request.form['user_address']
    user_address = utils.checkSumAddress(user_address)
    if user_address in utils.ACCESS_AUTHORITY or user_address in utils.UPLOAD_AUTHORITY:
        img = request.files['image']
        # owner = request.form['owner']
        owner = 'IcarusArt.AI'
        # --- random hash ---
        random_hash = random.getrandbits(128)
        # --- check id num iteration ---
        cursor = col_user_collects_notmint.find().sort('_id', pymongo.DESCENDING).limit(1)
        if cursor.count() == 0:
            sequence_id = 1
        else:
            sequence_id = cursor[0]['_id'] + 1
        # --------------------------------
        utils.mkdir(owner, utils.DB_PATH+'HECO/')
        if 'video' in mimetypes.guess_type(img.filename)[0]:
            file_path = utils.DB_PATH +'HECO/' + owner + '/' + ''.join(img.filename.split('.')[:-1]) + '.mp4'
            new_path = '{}{}/{}/{}-{}.{}'.format(utils.DB_PATH, "HECO", owner, sequence_id, random_hash, 'mp4')
        else:
            file_path = utils.DB_PATH + 'HECO/' + owner + '/' + img.filename
            new_path = '{}{}/{}/{}-{}.{}'.format(utils.DB_PATH, "HECO", owner, sequence_id, random_hash, img.filename.split('.')[-1])
        img.save(file_path)
        print(file_path, 'saved success')

        utils.resize(old_path=file_path, new_path=new_path, asset_type=img.filename.split('.')[-1])
        os.remove(file_path)
        d = {'_id': sequence_id,
             'canvas_token_id': sequence_id,
             'creator': request.form['creator'],
             'create_time': '',
             'description': request.form['description'],
             'name': request.form['name'],
             'owner': owner,
             'motype': 'video' if img.filename.split('.')[-1].lower() in ['mp4', 'mov', 'm4v'] else 'textrue',
             'label': 'notmint',
             'state': 0,
             'type': 'single',
             "file_main": [new_path.split('/')[-1]],
             "file_preview": ['{}-{}.{}'.format(sequence_id, random_hash, 'jpg')] if img.filename.split('.')[-1].lower() in ['mp4', 'mov', 'm4v'] else [''],
             "hash": [""],
             }
        col_user_collects_notmint.insert_one(d)
        return flask.Response(response=json.dumps({'status': 1}), status=200)
    else:
        return flask.Response(response=json.dumps({'status': 0}), status=200)


# --- GameFi ---
@server.route('/musicfi_save_singleround', methods=['POST'])
def musicfi_save_singleround():
    data = request.get_json()
    user_address = data['user_address']
    # user_address = '0x123'
    status = database.musicfi_save_singleround(user_address=user_address, data=data)
    return flask.Response(response=json.dumps({'status': status}),
                          status=200)


@server.route('/musicfi_get_specificranking', methods=['POST'])
def musicfi_get_specificranking():
    data = request.get_json()
    res = database.musicfi_get_specificranking(data['music_name'], data['music_difficulty'])
    return json.dumps(res)


@server.route('/musicfi_get_user_specificranking', methods=['POST'])
def musicfi_get_user_specificranking():
    data = request.get_json()
    res = database.musicfi_get_user_specificranking(data['user_address'], data['music_name'], data['music_difficulty'])
    return json.dumps(res)

@server.route('/musicfi_save_firsttime', methods=['POST'])
def musicfi_save_firsttime():
    data = request.get_json()
    status = database.musicfi_save_firsttime(data['user_address'], data['museum_id'])
    return flask.Response(response=json.dumps({'status': status}), status=200)

# --- special event ---
@server.route('/redeem_status', methods=['POST'])
def redeem_status():
    user_address = request.form['user_address']
    user_address = utils.checkSumAddress(user_address)
    redeemed = utils.col_code_redemption.find({'redeemed_by': user_address})
    res = dict()
    if redeemed.count() > 0:
        res[redeemed[0]['_id']] = []
        nodes = utils.col_code_redemption.find({'root_user': user_address})
        for i in nodes:
            res[redeemed[0]['_id']].append(i)
    return json.dumps(res)

@server.route('/redeem_code', methods=['POST'])
def redeem_code():
    user_address = request.form['user_address']
    user_address = utils.checkSumAddress(user_address)
    code = request.form['code']
    status = database.red_code(user_address=user_address, code=code)
    if status:
        return flask.Response('Redeem succeeded.', status=200)
    else:
        return flask.Response('Redeem failed.', status=400)



@server.route('/event_christmaseve', methods=['POST'])
def event_christmaseve():
    user_address = request.form['user_address']
    discord_id = request.form['discord_id']
    date_limit = datetime(2021, 12, 31, 4, 0)
    if datetime.now() > date_limit:
        return flask.Response('[Christmas event] Sorry, the event was closed. (ಥ﹏ಥ)', status=400)
    else:
        # build database
        col_event_christmaseve = utils.ting_db.event_christmaseve
        user_address = utils.checkSumAddress(user_address)
        try:
            col_event_christmaseve.insert_one({'_id': user_address, 'discord_id': discord_id})
            return flask.Response('[Christmas event] Register succeed!', status=200)
        except pymongo.errors.DuplicateKeyError:
            col_event_christmaseve.update_one({'_id': user_address}, {'$set': {'discord_id': discord_id}})
            return flask.Response('[Christmas event] You have registered already!', status=400)

# --------- NLP & GPT3 --------
@server.route('/gpt3_api', methods=['POST'])
def gpt3_api():
    content = request.form['prompt']
    text = database.gpt3_api(content)
    return flask.Response(response=json.dumps({'text': text, 'status': 1}),
                          status=200)

@server.route('/gpt3_romance_api', methods=['POST'])
def gpt3_romance_api():
    content = request.form['prompt']
    text = database.gpt3_romance_api(content)
    return flask.Response(response=json.dumps({'text': text, 'status': 1}),
                          status=200)

# --------- Eth Moon ----------
@server.route('/eth_blocks', methods=['POST'])
def eth_blocks():
    nums = database.get_ethblocks()
    return flask.Response(response=json.dumps({'blocks': nums, 'status': 1}),
                          status=200)


@server.route("/")
def hello():
    return "<h1 style='color:blue'>Hello There!</h1>"


if __name__ == '__main__':
    server.run(host=HOST, port=8800, debug=True, threaded=True)