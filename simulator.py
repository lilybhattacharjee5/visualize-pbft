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

def generate_preprepare_msg():
    pass

def client_proc(transactions, queues, t_queue):
    all_client_queues = queues[client_name]
    all_replica_queues = [(q_name, q_dict[client_name]) for q_name, q_dict in list(queues.items()) if q_name != client_name]

    status = True
    while status:
        # get p_index from t_queue
        p_index, primary_name, curr_transaction = t_queue.get()

        # client sends transaction to the primary of the current view
        client_primary_comm_name = "Replica_{}".format(p_index)
        for q_name, q in all_client_queues.items():
            if q_name == client_primary_comm_name:
                q.put((curr_transaction, primary_name))
            else:
                q.put(([], primary_name))

        # wait for all client_replica queues to send back a message
        for q_name, q in all_replica_queues:
            primary_status = q.get()
            print("received status", q_name, primary_status)

        # client receives all inform messages
        for q_name, q in all_replica_queues:
            if q_name != client_name:
                q.get()

        print("client has received inform message!")
        
        m_queue.put("move to the next transaction")

def replica_proc(r_name, queues, from_client):
    r_queues = queues[r_name]
    to_client = r_queues[client_name]
    
    status = True
    while status:
        primary_status = False
        transaction, primary_name = from_client.get()
        if transaction:
            primary_status = True   
        else:
            # must be a regular replica
            primary_status = False
        
        print("primary status", mp.current_process().name, primary_status)

        # send signal to client that primary has been informed
        to_client.put(primary_status)

        if primary_status:
            # primary broadcasts pre-prepare message to all other replicas
            for q_name, q in r_queues.items():
                if q_name != client_name:
                    q.put("pre-prepare message")
            print("primary has sent the pre-prepare messages")
        else:
            # replicas receive pre-prepare message
            from_primary = queues[primary_name][r_name]
            from_primary.get()
            print(r_name, "pre-prepare message received!")

        # all replicas broadcast prepare message to all other replicas
        for q_name, q in r_queues.items():
            if q_name != client_name:
                q.put("prepare message")
        print("{} has sent prepare messages".format(r_name))

        # wait to receive prepare messages from all other replicas
        for q_name, q_dict in queues.items():
            if q_name != r_name and q_name != client_name:
                q_dict[r_name].get()
        print(r_name, "prepare messages received!")

        # all replicas broadcast commit message to all other replicas
        for q_name, q in r_queues.items():
            if q_name != client_name:
                q.put("commit message")
        print("{} has sent commit messages".format(r_name))

        # wait to receive commit messages from all other replicas
        for q_name, q_dict in queues.items():
            if q_name != r_name and q_name != client_name:
                q_dict[r_name].get()
        print(r_name, "commit messages received!")

        # all replicas send an inform message to the client
        to_client.put("inform message")
        print("{} has sent inform message to client".format(r_name))

all_machine_names = [client_name] + replica_names
machine_queues = {}
for a1 in range(len(all_machine_names)):
    for a2 in range(a1 + 1, len(all_machine_names)):
        a1_machine_name = all_machine_names[a1]
        a2_machine_name = all_machine_names[a2]
        curr_queue_a1_a2 = mp.Queue()
        curr_queue_a2_a1 = mp.Queue()
        
        if a1_machine_name in machine_queues:
            machine_queues[a1_machine_name][a2_machine_name] = curr_queue_a1_a2
        else:
            machine_queues[a1_machine_name] = {a2_machine_name: curr_queue_a1_a2}

        if a2_machine_name in machine_queues:
            machine_queues[a2_machine_name][a1_machine_name] = curr_queue_a2_a1
        else:
            machine_queues[a2_machine_name] = {a1_machine_name: curr_queue_a2_a1}

# spawn client and replica processes
t_queue = mp.Queue()
m_queue = mp.Queue()
client = mp.Process(name = client_name, target = client_proc, args = (transactions, machine_queues, t_queue, ))
replicas = [mp.Process(name = r_name, target = replica_proc, args = (r_name, machine_queues, machine_queues[client_name][r_name] )) for r_name in replica_names]

client.start()
for r in replicas:
    r.start()

# iteratively execute all transactions
curr_view = 0
for t in range(len(transactions)):
    curr_transaction = transactions[t]

    print("Transaction {}".format(t), transactions[t])
        
    # elect primary
    p_index = curr_view % num_replicas
    primary_name = replica_names[p_index]
    print("Primary selected", p_index)

    # send p_index to client
    t_queue.put((p_index, primary_name, curr_transaction))

    # client sends a message (to itself) to move to the next transaction
    m_queue.get()
    curr_view += 1
    print()
    
    time.sleep(5) # artificial latency to view text output between transactions

# terminate all subprocesses
client.terminate()
for r in replicas:
    r.terminate()
