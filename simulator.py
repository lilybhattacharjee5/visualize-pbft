import multiprocessing as mp
import time
import numpy as np

np.random.seed(0)

def clear(q):
    print('Clearing')
    try:
        while True:
            print('Removing', q.get_nowait())
    except:
        pass

def clear_all_queues(q_list):
    for q in q_list:
        for a in q:
            clear(a)

# initialize mock db
bank = {
    "Ana": { "Balance": 500 },
    "Bo": { "Balance": 200 },
    "Elisa": { "Balance": 100 }
}

# simulator inputs
num_replicas = 5
num_byzantine = 1

f = (num_replicas - 1) // 3
g = num_replicas - f

transactions = [
    ["Ana", "Elisa", 400],
    ["Bo", "Elisa", 100],
    ["Elisa", "Ana", 20],
    # ["Bo", "Ana", 2],
    # ["Ana", "Bo", 100],
    # ["Elisa", "Ana", 1]
]
# transactions = [["Ana", "Elisa", 400] for i in range(1000)]

# select the random byzantine replicas
byz_idxes = np.random.choice(np.arange(0, num_replicas), num_byzantine, replace = False)
print("Byzantine replicas", byz_idxes)

# calculations based on inputs
num_transactions = len(transactions)

client_name = "Client"
replica_names = ["Replica_{}".format(r) for r in range(num_replicas)]
byz_replica_names = ["Replica_{}".format(r) for r in byz_idxes]

def generate_transaction_msg():
    pass

def generate_preprepare_msg():
    pass

def generate_prepare_msg():
    pass 

def generate_inform_msg():
    pass 

## CLIENT FUNCTIONS
def send_transaction(queues, primary_name, curr_transaction):
    for q_name, q in queues.items():
        if q_name != client_name:
            if q_name == primary_name:
                q["to_machine"].put((curr_transaction, primary_name))
            else:
                q["to_machine"].put((None, primary_name))

def replica_ack_primary(to_client):
    for i in range(num_replicas):
        to_client["to_machine"].get()
    m_queue.put("replica inform done")
    to_client["from_main"].get()

def recv_inform(to_client):
    for i in range(num_replicas):
        print("client received", to_client["to_machine"].get())
    print("client has received inform message!")

## PRIMARY FUNCTIONS
def send_preprepare(to_curr_replica, queues, client_name, r_name, m_queue):
    for q_name, q in queues.items():
        if q_name != client_name and q_name != r_name:
            q["to_machine"].put("pre-prepare message")
    print("primary has sent the pre-prepare messages")
    m_queue.put(r_name + " pre-prepare phase done")
    print(to_curr_replica["from_main"].get())

## REPLICA FUNCTIONS
def recv_preprepare(to_curr_replica, r_name, m_queue):
    print(r_name, to_curr_replica["to_machine"].get())
    print(r_name, "pre-prepare message received!")
    m_queue.put(r_name + " pre-prepare phase done")
    print(to_curr_replica["from_main"].get())

def prepare(to_curr_replica, queues, client_name, r_name, m_queue, byz_status):
    # all replicas broadcast prepare message to all other replicas
    # if not byz_status:
    for q_name, q in queues.items():
        if q_name != client_name and q_name != r_name:
            q["to_machine"].put("prepare message")
    print("{} has sent prepare messages".format(r_name))

    # wait to receive prepare messages from at least g other replicas
    for i in range(num_replicas - 1):
        print(r_name, to_curr_replica["to_machine"].get())
    print(r_name, "prepare messages received!")

    m_queue.put(r_name + " prepare phase done")
    print(to_curr_replica["from_main"].get())

def commit(to_curr_replica, queues, client_name, r_name, m_queue, byz_status):
    # all replicas broadcast commit message to all other replicas
    # if not byz_status:
    for q_name, q in queues.items():
        if q_name != client_name and q_name != r_name:
            q["to_machine"].put("commit message")
    print("{} has sent commit messages".format(r_name))

    # wait to receive commit messages from at least g other replicas
    for i in range(num_replicas - 1):
        to_curr_replica["to_machine"].get()
    print(r_name, "commit messages received!")

    m_queue.put(r_name + " commit phase done")
    print(to_curr_replica["from_main"].get())

def send_inform(to_client, r_name, byz_status):
    # if not byz_status:
    to_client.put("inform message")
    print("{} has sent inform message to client".format(r_name))

## MULTIPROCESSING
def client_proc(transactions, queues, t_queue):
    to_client = queues[client_name]

    status = True
    while status:
        # get p_index from t_queue
        p_index, primary_name, curr_transaction = t_queue.get()

        # client sends transaction to the primary of the current view
        send_transaction(queues, primary_name, curr_transaction)

        # wait for all primaries to acknowledge that primary has been informed
        replica_ack_primary(to_client)

        # client receives f + 1 identical inform messages
        recv_inform(to_client)
        
        m_queue.put("move to the next transaction")

def replica_proc(r_name, queues, byz_status):
    to_client = queues[client_name]["to_machine"]
    to_curr_replica = queues[r_name]
    
    status = True
    while status:
        primary_status = False
        transaction, primary_name  = to_curr_replica["to_machine"].get()
        print(transaction, primary_name)
        if transaction:
            primary_status = True   
        else:
            # must be a regular replica
            primary_status = False
        
        print("primary status", mp.current_process().name, primary_status)

        # send signal to client that primary has been informed
        to_client.put(primary_status)
        print(to_curr_replica["from_main"].get())

        if primary_status:
            # primary broadcasts pre-prepare message to all other replicas
            send_preprepare(to_curr_replica, queues, client_name, r_name, m_queue)
        else:
            # replicas receive pre-prepare message
            recv_preprepare(to_curr_replica, r_name, m_queue)

        prepare(to_curr_replica, queues, client_name, r_name, m_queue, byz_status) # prepare phase

        commit(to_curr_replica, queues, client_name, r_name, m_queue, byz_status) # commit phase

        send_inform(to_client, r_name, byz_status) # all replicas send an inform message to the client  

all_machine_names = [client_name] + replica_names
machine_queues = {}
for a in range(len(all_machine_names)):
    a_machine_name = all_machine_names[a]
    curr_queue_to_a = mp.Queue()
    curr_queue_to_a_from_main = mp.Queue()
    machine_queues[a_machine_name] = {
        "to_machine": curr_queue_to_a,
        "from_main": curr_queue_to_a_from_main
    }

# spawn client and replica processes
t_queue = mp.Queue()
m_queue = mp.Queue()
client = mp.Process(name = client_name, target = client_proc, args = (transactions, machine_queues, t_queue, ))
replicas = [mp.Process(name = r_name, target = replica_proc, args = (r_name, machine_queues, r_name in byz_replica_names, )) for r_name in replica_names]

client.start()
for r in replicas:
    r.start()

# iteratively execute all transactions
curr_view = 0
for t in range(len(transactions)):
    curr_transaction = transactions[t]

    print("Transaction {}".format(t), transactions[t])

    print("PRIMARY ELECTION")
        
    # elect primary
    p_index = curr_view % num_replicas
    primary_name = replica_names[p_index]
    print("Primary selected", p_index)

    # send p_index to client
    t_queue.put((p_index, primary_name, curr_transaction))

    # replica inform done
    print(m_queue.get())

    clear_all_queues(machine_queues.values())
    clear(m_queue)

    print()

    print("PRE-PREPARE PHASE")
    
    for q_name, q in machine_queues.items():
        q["from_main"].put("start pre-prepare phase")

    # pre-prepare phase done
    for i in range(num_replicas):
        print('Main', m_queue.get())

    clear_all_queues(machine_queues.values())
    clear(m_queue)

    print()

    print("PREPARE PHASE")
    
    for q_name, q in machine_queues.items():
        if q_name != client_name:
            q["from_main"].put("start prepare phase")

    # prepare phase done
    for i in range(num_replicas):
        print('Main', m_queue.get())

    clear_all_queues(machine_queues.values())
    clear(m_queue)

    print()

    print("COMMIT PHASE")
    
    for q_name, q in machine_queues.items():
        if q_name != client_name:
            q["from_main"].put("start commit phase")

    # commit phase done
    for i in range(num_replicas):
        print('Main', m_queue.get())

    clear_all_queues(machine_queues.values())
    clear(m_queue)

    print()

    print("INFORM CLIENT")
    
    for q_name, q in machine_queues.items():
        if q_name != client_name:
            q["from_main"].put("send inform messages")

    # inform client done: client sends a message to move to the next transaction
    print('Main', m_queue.get())

    clear_all_queues(machine_queues.values())
    clear(m_queue)
    clear(t_queue)

    curr_view += 1
    print("\n\n")
    
    # time.sleep(5) # artificial latency to view text output between transactions

# terminate all subprocesses
client.terminate()
for r in replicas:
    r.terminate()
