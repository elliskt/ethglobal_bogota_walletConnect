from web3 import Web3
import web3
import requests
import json
import time
import shutil
import glob
# --- local
import utils


CONTRACT = '0xCf22FF0B493B91BfFC9C14092Abb7C0CE08b5521'
HTTPProvider = 'https://ropsten.infura.io/v3/***'
ACCOUNT = '0x5C6EB9fdB3FF265D687636769C20aE9B804Eb339'

class Music_eth(object):
    def __init__(self):
        with open('contracts/erc1155.json', 'r') as contract_abi:
            abi = json.load(contract_abi)
            w3 = Web3(Web3.HTTPProvider(HTTPProvider))
            # print(w3.isConnected())
            self.contract = w3.eth.contract(address=CONTRACT, abi=abi)

    def getBalance(self, acc):
        balance = self.contract.functions.balanceOf(acc, 100000).call()
        # balance = self.contract.functions.balanceOfBatch([acc], [0]).call()
        return balance

a = Music_eth()
b = a.getBalance(ACCOUNT)
print()
print(b)
