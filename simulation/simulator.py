import multiprocessing.dummy as mp
import time
import numpy as np
import pandas as pd
from datetime import datetime, date
import sys
import json
import copy
import ast
import os
from simulation.client import send_transaction, replica_ack_primary, recv_inform
from simulation.replica import send_view_change, send_new_view, recv_new_view, recv_preprepare, send_prepare, recv_prepare, send_commit, recv_commit, send_inform 
from simulation.primary import send_preprepare
from simulation.message_generator import generate_new_view_msg
from simulation.utils import verify_signature, verify_mac
from nacl.signing import SigningKey, VerifyKey

# Possible Byzantine behavior to support
# - insert forged client transactions into the system
# - prevent replication of client transactions from some or all clients
# - send invalid results to client
# - interfere with correct working of distributed system e.g. convince replicas other good replicas are malicious
# - disrupting consensus protocol

# Currently supported
# - Byzantine replica(s) that do not respond to other replicas / client

np.random.seed(0)

class JSONEncoderWithDictProxy(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, mp.managers.DictProxy):
            return dict(o)
        return json.JSONEncoder.default(self, o)

def clear(q):
    try:
        while True:
            q.get_nowait()
    except:
        pass

def clear_all_queues(q_list):
    for q in q_list:
        for a in q:
            clear(a)

## TRANSACTION EXECUTION (TEMPORARY)
def execute_transaction(curr_transaction, r_name, replica_bank_copies, db_state):
    sender, receiver, amt = curr_transaction #ast.literal_eval(curr_transaction.message.decode("utf-8"))
    
    # does sender have at least amt to transfer?
    replica_bank = replica_bank_copies[r_name]
    if replica_bank[sender]["Balance"] >= amt:
        replica_bank[sender]["Balance"], replica_bank[receiver]["Balance"] = replica_bank[sender]["Balance"] - amt, replica_bank[receiver]["Balance"] + amt 
    
    replica_bank_copy = dict(copy.deepcopy(replica_bank))
    for key in replica_bank_copy.keys():
        replica_bank_copy[key] = dict(replica_bank[key])
    print("appending", replica_bank_copy)
    db_state.append(replica_bank_copy)
    return { sender: replica_bank[sender]["Balance"], receiver: replica_bank[receiver]["Balance"] }

## MULTIPROCESSING
def client_proc(client_name, client_signing_key, verify_keys, transactions, queues, t_queue, m_queue, visible_log, frontend_log, num_replicas, f, g, client_session_keys, replica_names):
    to_client = queues[client_name]

    status = True
    last_view = -1
    while status:
        # get p_index from t_queue
        p_index, primary_name, curr_transaction, curr_view, p = t_queue.get()
        if curr_view <= last_view:
            last_view = curr_view
            continue
        last_view = curr_view
        print("Main sending transaction", curr_transaction)

        curr_transaction_status = True
        while curr_transaction_status:
            # client sends transaction to the primary of the current view
            print("Client sending transaction", curr_transaction, primary_name)
            send_transaction(queues, client_name, primary_name, curr_transaction, curr_view, p, client_session_keys, replica_names)

            # wait for all replicas to acknowledge that primary has been informed
            replica_ack_primary(to_client, num_replicas, m_queue)

            # client receives f + 1 identical inform messages
            failure_status = recv_inform(to_client, f, visible_log, client_session_keys)
            print("failure status", failure_status)
            if failure_status == None:
                curr_view += 1
                p_index += 1
                p_index = p_index % num_replicas
                primary_name = "Replica_{}".format(p_index)
                print("Client", failure_status)
                m_queue.put(None)
                continue
            curr_transaction_status = False
        
        print("client moving to next transaction")
        m_queue.put("move to the next transaction")
        print("put into mqueue")

def replica_proc(r_name, r_idx, r_signing_key, verify_keys, client_name, queues, byz_status, t_queue, m_queue, visible_log, frontend_log, replica_logs, replica_bank_copies, f, g, good_replicas, db_state, replica_session_keys, replica_names):
    to_client = queues[client_name]["to_machine"]
    to_curr_replica = queues[r_name]
    transaction_communication_auth = None
    transaction_communication_msg = None
    
    status = True
    curr_view = 0
    while status:
        primary_status = False

        received = False
        while not received:
            queue_elem = to_curr_replica["to_machine"].get()

            if len(queue_elem) > 1:
                if queue_elem[0] == None:
                    transaction_msg = None
                    break 

                # verify that the signature is from client / that the msg hasn't been tampered with
                transaction_msg = queue_elem[0]
                transaction_communication = transaction_msg["Communication"]
                encoded_transaction_communication_msg = transaction_communication["Message"]
                transaction_communication_msg = json.loads(encoded_transaction_communication_msg)
                transaction_communication_auth = transaction_communication["Authenticator"]

                if not verify_mac(encoded_transaction_communication_msg, replica_session_keys[client_name], transaction_communication_auth[r_idx]):
                    continue

                # probable_transaction = transaction_msg["Transaction"]
                # if not verify_signature(probable_transaction, verify_keys[client_name]):
                #     continue

                if transaction_msg == None or transaction_msg["Type"] == "Transaction":
                    received = True 

        transaction, m_auth, primary_name  = transaction_msg, transaction_communication_auth, queue_elem[1]
        print(transaction, primary_name)

        visible_log.append("{} {}".format(transaction, primary_name))
        if transaction:
            primary_status = True
            # print("THIS IS IT", transaction_communication_msg["Operation"])
            curr_transaction, curr_view, p = transaction_communication, transaction["View"], transaction["Num_transaction"]
        else:
            # must be a regular replica
            primary_status = False
        
        visible_log.append("primary status {} {}".format(mp.current_process().name, primary_status))

        # send signal to client that primary has been informed
        to_client.put([primary_status])
        print("before primary informed")
        primary_informed = to_curr_replica["from_main"].get()
        visible_log.append(primary_informed)

        if primary_status:
            # primary broadcasts pre-prepare message to all other replicas
            m = send_preprepare(to_curr_replica, queues, client_name, r_name, m_queue, curr_transaction, curr_view, p, byz_status, visible_log, frontend_log, primary_name, replica_session_keys, m_auth, replica_names)
        else:
            # replicas receive pre-prepare message
            m = recv_preprepare(to_curr_replica, client_name, queues, r_name, m_queue, g, visible_log, frontend_log, good_replicas, verify_keys, byz_status, primary_name, replica_session_keys, r_idx, r_signing_key, curr_view)
            if m == None:
                print("{} exit prematurely, restart the transaction".format(r_name))
                continue
            curr_transaction, p = m["Transaction"], m["Num_transaction"]

        # prepare phase
        curr_view = m["View"]
        send_prepare(queues, client_name, r_name, byz_status, m, visible_log, frontend_log, primary_name, r_idx, replica_names, replica_session_keys, curr_view)

        m = recv_prepare(to_curr_replica, r_name, m_queue, byz_status, g, visible_log, replica_session_keys, r_idx)
        if m == None:
            print("{} exit prematurely, restart the transaction".format(r_name))
            # induce client to resend transaction
            new_view_msg = generate_new_view_msg(r_name, client_name, curr_view + 1, primary_name, r_signing_key, r_idx)
            to_client.put([new_view_msg])
            continue

        # commit phase
        send_commit(queues, client_name, r_name, m_queue, byz_status, m, visible_log, frontend_log, primary_name, r_idx, replica_names, replica_session_keys, curr_view)

        recv_commit(to_curr_replica, r_name, m_queue, byz_status, m, g, visible_log, frontend_log, replica_session_keys, r_idx)

        # append transaction to replica log
        replica_logs[r_name].append(curr_transaction)

        # execute transaction, generate optional result
        if r_name == primary_name:
            curr_transaction = json.loads(curr_transaction["Message"])["Operation"]
        print("Executing transaction {} {}".format(curr_transaction, r_name))
        result = execute_transaction(curr_transaction, r_name, replica_bank_copies, db_state)

        print(r_name, "sending inform", curr_transaction)
        send_inform(to_client, client_name, r_name, byz_status, curr_transaction, p, result, visible_log, frontend_log, primary_name, r_idx, curr_view, replica_session_keys[client_name]) # all replicas send an inform message to the client  

def run_simulation(num_replicas, num_byzantine, num_transactions, byz_behave, frontend_log, db_states, byz_replica_names_lst):
    manager = mp.Manager()
    visible_log = manager.list()

    # initialize mock db
    bank = {
        "Ana": { "Balance": 500 },
        "Bo": { "Balance": 200 },
        "Elisa": { "Balance": 100 }
    }

    f = (num_replicas - 1) // 3
    g = num_replicas - f - 1 # for primary

    print("good", g, "faulty", f)

    possible_transactions = [
        ["Ana", "Elisa", 400],
        ["Bo", "Elisa", 100],
        ["Elisa", "Ana", 20],
        ["Bo", "Ana", 2],
        ["Ana", "Bo", 100],
        ["Elisa", "Ana", 1],
        ["Elisa", "Ana", 1],
        ["Elisa", "Bo", 100],
        ["Bo", "Ana", 20],
        ["Ana", "Elisa", 30]
    ]
    transactions = possible_transactions[:num_transactions]

    # select the byzantine replicas
    all_byz = [
        [[], [1], [0, 1]], # 2
        [[], [1], [0, 1], [0, 1, 2]], # 3
        [[], [2], [0, 2], [0, 2, 3], [0, 1, 2, 3]], # 4
        [[], [3], [0, 2], [0, 2, 3], [0, 2, 3, 4], [0, 1, 2, 3, 4]], # 5
        [[], [4], [0, 3], [1, 3, 5], [1, 2, 3, 5], [0, 1, 3, 5], [0, 1, 2, 3, 4, 5]], # 6
        [[], [6], [2, 4], [1, 3, 5], [1, 2, 3, 5], [0, 1, 3, 5], [0, 1, 2, 3, 4, 5], [0, 1, 2, 3, 4, 5, 6]], # 7
        [[], [5], [1, 3], [0, 2, 3], [0, 2, 3, 4], [0, 1, 2, 3, 4], [0, 1, 2, 4, 5, 6], [0, 1, 2, 3, 4, 5, 6], [0, 1, 2, 3, 4, 5, 6, 7]], # 8
        # [[], [4], [2, 6], [0, 2, 3], [0, 2, 3, 4], [0, 1, 2, 3, 4], [0, 1, 2, 4, 5, 6], [0, 1, 2, 3, 4, 5, 6], [0, 1, 2, 3, 4, 5, 6, 7], [0, 1, 2, 3, 4, 5, 6, 7, 8]], # 9
        # [[], [7], [7, 9], [1, 7, 9], [0, 2, 3, 4], [0, 1, 2, 3, 4], [0, 1, 2, 4, 5, 6], [0, 1, 2, 3, 4, 5, 6], [0, 1, 2, 3, 4, 5, 6, 7], [0, 1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]], # 10
    ]
    byz_idxes = all_byz[num_replicas - 2][num_byzantine]

    # calculations based on inputs
    num_transactions = len(transactions)

    client_name = "Client"
    replica_names = ["Replica_{}".format(r) for r in range(num_replicas)]
    byz_replica_names = ["Replica_{}".format(r) for r in byz_idxes]
    good_replicas = ["Replica_{}".format(r) for r in list(set(range(num_replicas)) - set(byz_idxes))]

    for b in byz_replica_names:
        byz_replica_names_lst.append(b)

    local_db_states = manager.dict()
    for r_name in replica_names:
        local_db_states[r_name] = manager.list()
        local_db_states[r_name].append(bank)

    for r_name in replica_names:
        db_states[r_name] = list(local_db_states[r_name])

    replica_logs = {}
    replica_bank_copies = {}
    for r in replica_names:
        replica_logs[r] = manager.list()
        replica_bank_copies[r] = manager.dict()
        for user, data in bank.items():
            replica_bank_copies[r][user] = manager.dict()
            for k, v in data.items():
                replica_bank_copies[r][user][k] = v

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

    # generate a signing key for the client
    signing_keys = {}
    verify_keys = {}
    
    client_signing_key = SigningKey.generate()
    signing_keys[client_name] = client_signing_key
    verify_keys[client_name] = client_signing_key.verify_key

    # generate signing keys for each replica
    for r_name in replica_names:
        replica_signing_key = SigningKey.generate()
        signing_keys[r_name] = replica_signing_key
        verify_keys[r_name] = replica_signing_key.verify_key

    # generate a secret set of session keys between each pair of nodes
    session_keys = {}
    for idx1 in range(len(all_machine_names)):
        machine1 = all_machine_names[idx1]
        for idx2 in range(idx1 + 1, len(all_machine_names)):
            machine2 = all_machine_names[idx2]
            curr_session_key = os.urandom(16)
            if machine1 in session_keys:
                session_keys[machine1][machine2] = curr_session_key
            else:
                session_keys[machine1] = { machine2: curr_session_key }

            if machine2 in session_keys:
                session_keys[machine2][machine1] = curr_session_key
            else:
                session_keys[machine2] = { machine1: curr_session_key }

    print(session_keys)

    # spawn client and replica processes
    t_queue = mp.Queue()
    m_queue = mp.Queue()
    client = mp.Process(name = client_name, target = client_proc, args = (client_name, client_signing_key, verify_keys, transactions, machine_queues, t_queue, m_queue, visible_log, frontend_log, num_replicas, f, g, session_keys[client_name], replica_names ))
    replicas = []
    for r_idx in range(len(replica_names)):
        r_name = replica_names[r_idx]
        curr_replica = mp.Process(name = r_name, target = replica_proc, args = (r_name, r_idx, signing_keys[r_name], verify_keys, client_name, machine_queues, byz_behave if r_name in byz_replica_names else None, t_queue, m_queue, visible_log, frontend_log, replica_logs, replica_bank_copies, f, g, good_replicas, local_db_states[r_name], session_keys[r_name], replica_names ))
        replicas.append(curr_replica)

    client.start()
    for r in replicas:
        r.start()

    # iteratively execute all transactions
    curr_view = 0
    p = 0
    for t in range(len(transactions)):
        transaction_status = True
        print(t, transactions[t], "main value")
        while transaction_status:
            visible_log.append("Transaction {} {}".format(t, transactions[t]))

            # visible_log.append("PRIMARY ELECTION")
            print("PRIMARY ELECTION")
                
            # elect primary
            p_index = curr_view % num_replicas
            primary_name = replica_names[p_index]
            # visible_log.append("Primary selected {}".format(p_index))
            print("Primary selected {}".format(p_index))

            # send primary index, name, current view, and transaction to client
            print("sending", (p_index, primary_name, transactions[t], curr_view, p))
            t_queue.put((p_index, primary_name, transactions[t], curr_view, p))

            # replica inform done
            visible_log.append(m_queue.get())

            clear_all_queues(machine_queues.values())
            clear(m_queue)

            visible_log.append("PRE-PREPARE PHASE")
            
            for q_name, q in machine_queues.items():
                q["from_main"].put("start pre-prepare phase")

            # pre-prepare phase done
            print("before client response")
            client_response = m_queue.get()
            print("Client response", client_response)
            if client_response == None:
                continue
            for i in range(num_replicas):
                visible_log.append("Main {}".format(m_queue.get()))

            clear_all_queues(machine_queues.values())
            clear(m_queue)

            visible_log.append("PREPARE PHASE")
            
            for q_name, q in machine_queues.items():
                if q_name != client_name:
                    q["from_main"].put("start prepare phase")

            # prepare phase done
            for i in range(num_replicas):
                visible_log.append("Main {}".format(m_queue.get()))

            clear_all_queues(machine_queues.values())
            clear(m_queue)

            visible_log.append("COMMIT PHASE")
            print("COMMIT PHASE")
            
            for q_name, q in machine_queues.items():
                if q_name != client_name:
                    q["from_main"].put("start commit phase")

            # commit phase done
            for i in range(num_replicas):
                visible_log.append("Main {}".format(m_queue.get()))

            print("COMMIT PHASE DONE")

            clear_all_queues(machine_queues.values())
            clear(m_queue)

            visible_log.append("INFORM CLIENT")
            print("INFORM CLIENT")
            
            for q_name, q in machine_queues.items():
                if q_name != client_name:
                    print(q_name, "send inform message")
                    q["from_main"].put("send inform messages")

            # inform client done: client sends a message to move to the next transaction
            print("before getting from mqueue")
            inform_client_status = m_queue.get()
            print("inform client done", inform_client_status)
            visible_log.append("Main {}".format(inform_client_status))

            clear_all_queues(machine_queues.values())
            clear(m_queue)
            clear(t_queue)

            print("cleared queues")

            p += 1
            curr_view += 1
            transaction_status = False

            print("Move to next transaction in loop")

    # states of replica banks
    for r_name, bank_copy in replica_bank_copies.items():
        print(r_name, json.dumps(bank_copy, cls=JSONEncoderWithDictProxy))

    for r_name in replica_names:
        db_states[r_name] = list(local_db_states[r_name])

    # terminate all subprocesses
    client.join(timeout = 120)
    for r in replicas:
        r.join(timeout = 120)
