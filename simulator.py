import multiprocessing as mp
import time

# initialize mock db
bank = {
    "Ana": { "Balance": 500 },
    "Bo": { "Balance": 200 },
    "Elisa": { "Balance": 100 }
}

# simulator inputs
num_replicas = 5
num_byzantine = 1
transactions = [
    ["Ana", "Elisa", 400],
    ["Bo", "Elisa", 100],
    ["Elisa", "Ana", 20],
    ["Bo", "Ana", 2],
    ["Ana", "Bo", 100],
    ["Elisa", "Ana", 1]
]

# calculations based on inputs
num_transactions = len(transactions)

client_name = "Client"
replica_names = ["Replica_{}".format(r) for r in range(num_replicas)]

def client_proc(transactions, queues):
    # print(mp.current_process().name, queues)
    # while status:
    #     pass
    pass

def replica_proc(queues):
    # print(mp.current_process().name, queues)
    client_queue = queues[client_name]
    status = True
    while status:
        primary_status = False
        transaction = client_queue.get()
        if transaction:
            primary_status = True   
        else:
            # must be a regular replica
            primary_status = False
        
        print('primary status', mp.current_process().name, primary_status)

        # send signal to client that primary has been informed
        client_queue.put(primary_status)
        time.sleep(10)

all_machine_names = [client_name] + replica_names
comm_queues = {}
machine_queues = {}
for a1 in range(len(all_machine_names)):
    for a2 in range(a1 + 1, len(all_machine_names)):
        a1_machine_name = all_machine_names[a1]
        a2_machine_name = all_machine_names[a2]
        curr_queue_name = a1_machine_name + "_" + a2_machine_name
        curr_queue = mp.Queue()
        comm_queues[curr_queue_name] = curr_queue 
        if a1_machine_name in machine_queues:
            machine_queues[a1_machine_name][a2_machine_name] = curr_queue 
        else:
            machine_queues[a1_machine_name] = {a2_machine_name: curr_queue}

        if a2_machine_name in machine_queues:
            machine_queues[a2_machine_name][a1_machine_name] = curr_queue 
        else:
            machine_queues[a2_machine_name] = {a1_machine_name: curr_queue}

# spawn client and replica processes
client = mp.Process(name = client_name, target = client_proc, args = (transactions, machine_queues[client_name], ))
replicas = [mp.Process(name = r_name, target = replica_proc, args = (machine_queues[r_name], )) for r_name in replica_names]

client.start()
for r in replicas:
    r.start()

# iteratively execute all transactions
all_client_queues = machine_queues[client_name]
curr_view = 0
for t in range(len(transactions)):
    curr_transaction = transactions[t]

    print("Transaction {}".format(t), transactions[t])
    
    # exec = True
    # while exec:
        
    # elect primary
    p_index = curr_view % num_replicas
    primary = replicas[p_index]
    print('Primary selected', p_index)

    # client sends transaction to the primary of the current view
    client_primary_comm_name = "Replica_{}".format(p_index)
    for q_name, q in all_client_queues.items():
        if q_name == client_primary_comm_name:
            q.put(curr_transaction)
        else:
            q.put([])

    time.sleep(10)

    # wait for all client_replica queues to send back a message
    for q_name, q in all_client_queues.items():
        primary_status = q.get()
        print('received status', q_name, primary_status)

    curr_view += 1
    print()

# terminate all subprocesses
client.terminate()
for r in replicas:
    r.terminate()
