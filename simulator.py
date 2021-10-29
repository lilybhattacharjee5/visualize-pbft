import multiprocessing as mp
import time

def clear(q):
    try:
        while True:
            q.get_nowait()
    except:
        pass

def clear_all_queues(q_list):
    for q in q_list:
        clear(q)

# initialize mock db
bank = {
    "Ana": { "Balance": 500 },
    "Bo": { "Balance": 200 },
    "Elisa": { "Balance": 100 }
}

# simulator inputs
num_replicas = 5
num_byzantine = 1
# transactions = [
#     ["Ana", "Elisa", 400],
#     ["Bo", "Elisa", 100],
#     ["Elisa", "Ana", 20],
#     ["Bo", "Ana", 2],
#     ["Ana", "Bo", 100],
#     ["Elisa", "Ana", 1]
# ]
transactions = [["Ana", "Elisa", 400] for i in range(1000)]

# calculations based on inputs
num_transactions = len(transactions)

client_name = "Client"
replica_names = ["Replica_{}".format(r) for r in range(num_replicas)]

def generate_transaction_msg():
    pass

def generate_preprepare_msg():
    pass

def generate_prepare_msg():
    pass 

def generate_inform_msg():
    pass 

def client_proc(transactions, queues, t_queue):
    to_client = queues[client_name]

    status = True
    while status:
        # get p_index from t_queue
        p_index, primary_name, curr_transaction = t_queue.get()

        # client sends transaction to the primary of the current view
        for q_name, q in queues.items():
            if q_name == primary_name:
                q.put((curr_transaction, primary_name))
            else:
                q.put((None, primary_name))

        # wait for all replicas to acknowledge that primary has been informed
        for i in range(num_replicas):
            to_client.get()
        m_queue.put("replica inform done")
        to_client.get()

        # client receives all inform messages
        for i in range(num_replicas):
            to_client.get()

        print("client has received inform message!")
        
        m_queue.put("move to the next transaction")

def replica_proc(r_name, queues):
    to_client = queues[client_name]
    to_curr_replica = queues[r_name]
    
    status = True
    while status:
        primary_status = False
        transaction, primary_name = to_curr_replica.get()
        if transaction:
            primary_status = True   
        else:
            # must be a regular replica
            primary_status = False
        
        print("primary status", mp.current_process().name, primary_status)

        # send signal to client that primary has been informed
        to_client.put(primary_status)
        print(to_curr_replica.get())

        if primary_status:
            # primary broadcasts pre-prepare message to all other replicas
            for q_name, q in queues.items():
                if q_name != client_name and q_name != r_name:
                    q.put("pre-prepare message")
            print("primary has sent the pre-prepare messages")
        else:
            # replicas receive pre-prepare message
            print(r_name, to_curr_replica.get())
            print(r_name, "pre-prepare message received!")

        m_queue.put(r_name + " pre-prepare phase done")
        print(to_curr_replica.get())

        # all replicas broadcast prepare message to all other replicas
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                q.put("prepare message")
        print("{} has sent prepare messages".format(r_name))

        # wait to receive prepare messages from all other replicas
        for i in range(num_replicas - 1):
            print(r_name, to_curr_replica.get())
        print(r_name, "prepare messages received!")

        m_queue.put(r_name + " prepare phase done")
        print(to_curr_replica.get())

        # all replicas broadcast commit message to all other replicas
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                q.put("commit message")
        print("{} has sent commit messages".format(r_name))

        # wait to receive commit messages from all other replicas
        for i in range(num_replicas - 1):
            to_curr_replica.get()
        print(r_name, "commit messages received!")

        m_queue.put(r_name + " commit phase done")
        print(to_curr_replica.get())

        # all replicas send an inform message to the client
        to_client.put("inform message")
        print("{} has sent inform message to client".format(r_name))

all_machine_names = [client_name] + replica_names
machine_queues = {}
for a in range(len(all_machine_names)):
    a_machine_name = all_machine_names[a]
    curr_queue_to_a = mp.Queue()
    machine_queues[a_machine_name] = curr_queue_to_a

# spawn client and replica processes
t_queue = mp.Queue()
m_queue = mp.Queue()
client = mp.Process(name = client_name, target = client_proc, args = (transactions, machine_queues, t_queue, ))
replicas = [mp.Process(name = r_name, target = replica_proc, args = (r_name, machine_queues, )) for r_name in replica_names]

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

    # replica inform done
    print(m_queue.get())

    clear_all_queues(machine_queues.values())
    
    for q_name, q in machine_queues.items():
        q.put("start pre-prepare phase")

    # pre-prepare phase done
    for i in range(num_replicas):
        print(m_queue.get())

    clear_all_queues(machine_queues.values())
    
    for q_name, q in machine_queues.items():
        if q_name != client_name:
            q.put("start prepare phase")

    # prepare phase done
    for i in range(num_replicas):
        print(m_queue.get())

    clear_all_queues(machine_queues.values())
    
    for q_name, q in machine_queues.items():
        if q_name != client_name:
            q.put("start commit phase")

    # commit phase done
    for i in range(num_replicas):
        print(m_queue.get())

    clear_all_queues(machine_queues.values())
    
    for q_name, q in machine_queues.items():
        if q_name != client_name:
            q.put("send inform messages")

    # inform client done: client sends a message to move to the next transaction
    print(m_queue.get())

    clear_all_queues(machine_queues.values())
    clear(m_queue)
    clear(t_queue)

    curr_view += 1
    print()
    
    # time.sleep(5) # artificial latency to view text output between transactions

# terminate all subprocesses
client.terminate()
for r in replicas:
    r.terminate()
