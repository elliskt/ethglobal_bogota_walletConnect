from web3 import Web3
import json
# --- local
import utils


# CONTRACT = '0x88B48F654c30e99bc2e4A1559b4Dcf1aD93FA656'  # rinkeby
CONTRACT = '0x495f947276749Ce646f68AC8c248420045cb7b5e'  # opensea
# HTTPProvie = 'https://rinkeby.infura.io/v3/e119901a0b704e9ba54bcc89e3448cdd' # rinkeby 100k requests access limit /
HTTPProvie = 'https://mainnet.infura.io/v3/***' # mainnet 100k requests access limit
TOKEN = dict()
TOKEN['EH001'] = [94111535282872533185076367983495775478047768850277227574032472505830374113780]
# TOKEN['EH002'] = [94111535282872533185076367983495775478047768850277227574032472504730862485992]
TOKEN['EH002'] = [94111535282872533185076367983495775478047768850277227574032472506929885741544]
# TOKEN['EH003'] = [94111535282872533185076367983495775478047768850277227574032472503631350857756]
TOKEN['EH003'] = [94111535282872533185076367983495775478047768850277227574032472508029397368860]
# --- this is for opensea collection contract ---
class OpenSea_Collection(object):
    def __init__(self):
        with open('contracts/erc1155.json', 'r') as contract_abi:
            abi = json.load(contract_abi)
        self.w3 = Web3(Web3.HTTPProvider(HTTPProvie))
        self.contract = self.w3.eth.contract(address=CONTRACT, abi=abi)
        print('[OpenSea][Info] tm opensea skin tracker contract initialized.')

    def checkBalance(self, acc, ehtype=str):
        SPECIAL_ACC = utils.col_code_redemption.find().distinct('redeemed_by')
        sum = 0
        for token in TOKEN[ehtype]:
            sum += self.contract.functions.balanceOf(acc, token).call()
        # --- open access once for EH001
        # if ehtype == 'EH001':
        #     sum += 1
        # --- open access once for special acc
        print(acc)
        print(SPECIAL_ACC)
        if acc in SPECIAL_ACC:
            sum += 1
        if acc in utils.ACCESS_AUTHORITY_TESTUSE:
            sum += 1
        if acc in utils.UPLOAD_AUTHORITY and ehtype == 'EH003':
            sum += 1
        return sum

    def checkAllBalance(self, acc):
        balance = []
        for ehtype in TOKEN:
            sum = 0
            for token in TOKEN[ehtype]:     # for each token id
                sum += self.contract.functions.balanceOf(utils.checkSumAddress(acc), token).call()
            balance.append(sum)
        return balance

