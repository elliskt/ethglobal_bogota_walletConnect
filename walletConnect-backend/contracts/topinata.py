import requests
import os
import sys

headers = {
    'pinata_api_key': '***',
    'pinata_secret_api_key': '***',
}


def pin_file_to_ipfs(file_path):
    url = 'https://api.pinata.cloud/pinning/pinFileToIPFS'
    with open(file_path, 'rb') as f:
        requests.post(url, files=files, headers=headers)


for addr in os.listdir(sys.argv[1]):
    print(addr)
    for ass in os.listdir('{}/{}'.format(sys.argv[1], addr)):
        print(ass)
        pin_file_to_ipfs('{}/{}/{}'.format(sys.argv[1], addr, ass))
        print('---------------------')
