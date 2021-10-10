import multiprocessing as mp

# simulator inputs
num_replicas = 5
num_byzantine = 1
transactions = []

# calculations based on inputs
num_transactions = len(transactions)

def client_proc(transactions):
    print("inside client")
    pass 

def replica_proc():
    print("inside replica")
    pass

# spawn client and replica processes
client = mp.Process(target = client_proc, args = (transactions, ))
replicas = [mp.Process(target = replica_proc, args = ()) for r in range(num_replicas)]

client.start()

# iteratively execute all transactions
for t in range(len(transactions)):
    curr_transaction = transactions[t]
