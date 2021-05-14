
"""

Created on Mon May 10 13:41:43 2021
FatCatCoin
@author: vjmar
"""

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# imports
import datetime # for dates blocks are created
import hashlib # to hash the blocks
import json # to encode the blocks before hashing
from flask import Flask, jsonify, request # to create an object of Flask class and jsonify to return requests
import requests
from uuid import uuid4
from urllib.parse import urlparse
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Crytocurrency

receiver_name = "Tiger"

class Blockchain:
    
    # Constructor
    def __init__(self):
        self.chain = [] # list of blocks - no blocks in it atm 
        self.transactions = []            # must be put here! << all transactions before they are added to the block
        self.create_block(proof = 1, previous_hash = '0') # create the genesis block
        self.nodes = set() # not list as nodes have no orders
    
    def create_block(self, proof, previous_hash):
        block = {'index': len(self.chain) + 1,
                 'timestamp': str(datetime.datetime.now()),
                 'proof':proof,
                 'previous_hash': previous_hash,
                 'transactions': self.transactions}
        
        self.transactions = [] # making the list empty after adding transactions to the transactions section of the block
        self.chain.append(block) # attach block to the chain
        return block

    def get_previous_block(self): # self as we need to grab the chain
        return self.chain[-1]

    # method to get proof of work - miners will need to solve this problem
    def proof_of_work(self, previous_proof):
        new_proof = 1
        check_proof = False # Sets to true when you find the solution
        
        while check_proof is False:
            hash_operation = hashlib.sha256(str(new_proof**2 - previous_proof**2).encode()).hexdigest()
            if hash_operation[:4] == '0000':
                check_proof = True
            else:
                new_proof += 1
        return new_proof
            
    def hash(self, block): # returns the cryptographic has of a block
        encoded_block = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
        
    def is_chain_valid(self, chain):
        previous_block = chain[0] # get first block
        block_index = 1
        
        while block_index < len(chain): # go through the whole chain
            block = chain[block_index] # current block
            
            if block['previous_hash'] != self.hash(previous_block): # means previous hash doesnt match hash of previous block -  block is invalid!
                return False 
           
            previous_proof = previous_block['proof']
            proof = block['proof']
            hash_operation = hashlib.sha256(str(proof**2 - previous_proof**2).encode()).hexdigest()
            
            if hash_operation[:4] != '0000': # means first 4 chars of the hash isnt 0000
                return False
            
            previous_block = block
            block_index += 1
            
        return True # if no problems the chain is valid
            
    def add_transaction(self, sender, receiver, amount): # adds transactions to a block
        self.transactions.append({'sender': sender,
                                  'receiver': receiver,
                                  'amount': amount})
        previous_block = self.get_previous_block()
        return previous_block['index'] + 1
    
    def add_node(self, node_address):
        parsed_url = urlparse(node_address)
        self.nodes.add(parsed_url.netloc) # because parsed_url = ParseResult(scheme='http', netloc='127.0.0.1:5000', path='/', params='', query='', fragment='')
        
    def replace_chain(self):
        network = self.nodes
        longest_chain = None
        max_length = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['chain_length']
                chain = response.json()['chain']
                if length > max_length and self.is_chain_valid(chain):
                    max_length = length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False
            
        
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Create the web app - Flask
app = Flask(__name__)

# Create an address for the node on Port (5000 for now)
node_address = str(uuid4()).replace('-', '') # creates a node address on port 5000

    
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Create a blockchain - create instance of it
blockchain = Blockchain()

@app.route('/set_name', methods=['POST'])
def set_name():
    json = request.get_json()
    global receiver_name
    receiver_name = json['name']
    
    response = {'message': f'Name successfully set to {receiver_name}'}
    return jsonify(response), 200

# Mining a new block
@app.route('/mine_block', methods=['GET']) # full URL = "http://127.0.0.1:5000/" according to flask documents - check on postman
# method for this part of the app
def mine_block():
    prev_block = blockchain.get_previous_block() #get prev block
    prev_proof = prev_block['proof'] # get prev proof of work
    proof = blockchain.proof_of_work(prev_proof) # current proof 
    prev_hash = blockchain.hash(prev_block)
    blockchain.add_transaction(sender = node_address, receiver = receiver_name, amount = 1)
    current_block = blockchain.create_block(proof, prev_hash) # block is appended and returned
    
    # create the response to return
    response = {'message': "Block added to the chain! Nya~",
                'index': current_block['index'],
                'timestamp': current_block['timestamp'],
                'proof': current_block['proof'],
                'prev_hash': current_block['previous_hash'],
                'transacions': current_block['transactions']
                }
    
    return jsonify(response), 200
    
# get the blockchain
@app.route('/get_chain', methods=['GET'])
def get_full_blockchain():
    response = {'chain': blockchain.chain,
                'chain_length': len(blockchain.chain)}
    
    return jsonify(response), 200

@app.route('/is_valid', methods=['GET'])
def is_blockchain_valid():
    is_valid = blockchain.is_chain_valid(blockchain.chain)
    response = {'is_valid': is_valid}
    return jsonify(response), 200

# add transaction to blockchain
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    #get JSON file to post
    json = request.get_json()
    # make sure we have these keys!
    transaction_keys = ['sender', 'receiver', 'amount']
    if not all(key in json for key in transaction_keys):
        return 'Not all elements necessary for the transation are present!', 400
    # get index of the block with these transactions
    index = blockchain.add_transaction(json['sender'], json['receiver'], json['amount'])
    response = {'message': f'Transaction to be added to index {index}'}
    return jsonify(response), 201

# >>>>>>>>>>>>>> Decentralise blockchain

    # connecting new nodes
@app.route('/connect_node', methods=['POST'])
def connect_node():
    json = request.get_json()
    nodes = json.get('nodes') # grabs the json file with the list of nodes
    if nodes is None:
        return "No node", 400
    for node in nodes:
        blockchain.add_node(node)
    response = {'message': 'All the nodes are now connected.',
                'total_nodes': list(blockchain.nodes)}
    return jsonify(response), 201
    
    # replace the chain with the longest chain if current chain is shorter!
@app.route('/replace_chain', methods=['GET'])
def replace_chain():
    is_chain_replaced = blockchain.replace_chain()
    if is_chain_replaced:
        response = {'message': 'Current chain was replaced with a larger chain.',
                    'new_chain': blockchain.chain}
    else:
        response = {'message': 'No change required',
                    'actual_chain': blockchain.chain}
    return jsonify(response), 200
    

# Run the app - just copy-past from documentation for now - figure out something else later
app.run(host = '0.0.0.0', port = 5003)


# some notes:
# Get request - to get something
# Post - need to create something then send (post) it to the API





