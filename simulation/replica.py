from simulation.message_generator import generate_prepare_msg, generate_commit_msg, generate_inform_msg, generate_view_change_msg, generate_new_view_msg
from simulation.utils import verify_signature, verify_mac
import ast
import copy
import hashlib
import json

def byz_replica_send_prepare(byz_status):
    if byz_status == "no_response":
        return 
    else:
        return # none of the other byzantine behaviors are related to the replica's prepare phase

def byz_replica_send_commit(byz_status):
    if byz_status == "no_response":
        return 
    else:
        return # none of the other byzantine behaviors are related to the replica's commit phase

def byz_replica_send_inform(to_client, client_name, r_name, byz_status, curr_transaction, p, r, visible_log, frontend_log, primary_name):
    if byz_status == "no_response":
        return 
    elif byz_status == "bad_transaction_results":
        bad_result = {
            "Ana": 14,
            "Bob": 20
        }
        inform_msg = generate_inform_msg(r_name, client_name, curr_transaction, p, bad_result, primary_name)
        to_client.put([inform_msg])
        clean_inform_msg = copy.deepcopy(inform_msg)
        # clean_inform_msg["Transaction"] = str(clean_inform_msg["Transaction"].message.decode("utf-8"))
        frontend_log.append(clean_inform_msg)
        visible_log.append("{} has sent inform message to client".format(r_name))
    else:
        return # none of the other byzantine behaviors are related to the replica's inform phase

def byz_replica_recv_prepare(byz_status):
    return

def byz_replica_recv_commit(byz_status):
    return

## REPLICA FUNCTIONS
def send_view_change(queues, r_name, client_name, frontend_log, primary_name):
    # stop the byzantine commit algorithm for view v 
    # broadcast viewchange(E, v) to all replicas [E = set of all requests m prepared by R]
    for q_name, q in queues.items():
        if q_name != client_name and q_name != r_name:
            view_change_msg = generate_view_change_msg(r_name, q_name, primary_name)
            q["to_machine"].put([view_change_msg])
            frontend_log.append(view_change_msg)

def send_new_view(queues, r_name, client_name, to_curr_replica, curr_view, g, frontend_log, primary_name):
    # used by replica p' = (v + 1) mod n to become the new primary
    # p' receives at least g viewchange(E_i, v_i) messages
    sender_count = 0
    senders = {}
    while sender_count < g:
        received = False 
        while not received:
            queue_elem = to_curr_replica["to_machine"].get()
            if len(queue_elem) == 1 and queue_elem[0]["Type"] == "View change":
                received = True 
                curr_sender = queue_elem[0]["Sender"]
                if curr_sender not in senders:
                    sender_count += 1
                    senders[curr_sender] = True
                print("{} received {} view change request".format(r_name, curr_sender))

    # broadcast newview(v + 1, V, N) to all replicas
    for q_name, q in queues.items():
        if q_name != client_name and q_name != r_name:
            new_view_msg = generate_new_view_msg(r_name, q_name, curr_view + 1, primary_name)
            q["to_machine"].put([new_view_msg])
            frontend_log.append(new_view_msg)

def recv_new_view(r_name, to_curr_replica):
    received = False
    while not received:
        queue_elem = to_curr_replica["to_machine"].get()
        print("inside recv new view", r_name, "receiving", queue_elem)
        if len(queue_elem) == 1 and queue_elem[0]["Type"] == "New view":
            received = True
            print("{} received new view".format(r_name))

def recv_preprepare(to_curr_replica, client_name, queues, r_name, m_queue, g, visible_log, frontend_log, good_replicas, verify_keys, byz_status, primary_name, replica_session_keys, r_idx):
    received = False
    counter = 0
    detected_failure = False
    while not received:
        try:
            queue_elem = to_curr_replica["to_machine"].get(timeout = 1)
            if len(queue_elem) == 1 and queue_elem[0]["Type"] == "Pre-prepare":
                # if replica is byzantine, keep spamming view change requests (even if primary is good)
                if byz_status == "bad_view_change_requests":
                    print("spammed request: {} has detected primary failure".format(r_name))
                    send_view_change(queues, r_name, client_name, frontend_log, primary_name)
                    break
                
                # verify that transaction message is signed by client
                preprepare_msg = queue_elem[0]
                preprepare_communication = preprepare_msg["Communication"]
                transaction_communication = preprepare_communication["Message"]
                transaction_msg = transaction_communication["Message"]
                transaction_digest = transaction_communication["Authenticator"][r_idx]
                shared_key = replica_session_keys[client_name]

                if not verify_mac(transaction_msg, shared_key, transaction_digest):
                    print("signature issue: {} has detected primary failure".format(r_name))
                    send_view_change(queues, r_name, client_name, frontend_log, primary_name)
                    detected_failure = True
                    break

                # verify that primary message is signed by primary
                primary_communication = preprepare_communication["Primary_message"]
                primary_digest = preprepare_communication["Authenticator"][r_idx]
                shared_key = replica_session_keys[primary_name]
                if not verify_mac(primary_communication, shared_key, primary_digest):
                    print("signature issue: {} has detected primary failure".format(r_name))
                    send_view_change(queues, r_name, client_name, frontend_log, primary_name)
                    detected_failure = True
                    break

                # probable_transaction = queue_elem[0]["Transaction"]
                # if not verify_signature(probable_transaction, verify_keys[client_name]):
                #     print("signature issue: {} has detected primary failure".format(r_name))
                #     send_view_change(queues, r_name, client_name, frontend_log, primary_name)
                #     detected_failure = True
                #     break

                received = True 
                visible_log.append("{} {}".format(r_name, queue_elem))
                visible_log.append("{} {}".format(r_name, "pre-prepare message received!"))
            else:
                counter += 1
        except:
            counter += 1
            if counter > 5:
                print("{} has detected primary failure".format(r_name))
                send_view_change(queues, r_name, client_name, frontend_log, primary_name)
                detected_failure = True
                break

    if detected_failure:
        print(good_replicas)
        if r_name == good_replicas[0]: # this needs to be changed! "Replica_1"
            # send new view message
            print("sending new view", r_name)
            send_new_view(queues, r_name, client_name, to_curr_replica, 0, g, frontend_log, primary_name)
        else:
            # receive new view message
            recv_new_view(r_name, to_curr_replica)
        return None

    m_queue.put(r_name + " pre-prepare phase done")
    print(r_name + " pre-prepare phase done")
    visible_log.append(to_curr_replica["from_main"].get())

    preprepare_comm_received = queue_elem[0]
    transaction_received = json.loads(preprepare_comm_received["Communication"]["Message"]["Message"])["Operation"]
    view_received = preprepare_comm_received["View"]
    num_transaction_received = preprepare_comm_received["Num_transaction"]
    m = {
        "Transaction": transaction_received,
        "View": view_received,
        "Num_transaction": num_transaction_received,
    }
    return m

def send_prepare(queues, client_name, r_name, byz_status, m, visible_log, frontend_log, primary_name, r_idx, replica_names, replica_session_keys, curr_view):
    # all replicas broadcast prepare message to all other replicas
    if byz_status:
        byz_replica_send_prepare(byz_status)
    else:
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                prep_msg = generate_prepare_msg(r_name, q_name, m, primary_name, r_idx, replica_names, replica_session_keys, curr_view)
                q["to_machine"].put([prep_msg])
                clean_prep_msg = copy.deepcopy(prep_msg)
                # clean_prep_msg["Message"]["Transaction"] = str(clean_prep_msg["Message"]["Transaction"].message.decode("utf-8"))
                frontend_log.append(clean_prep_msg)
        visible_log.append("{} has sent prepare messages".format(r_name)) 

def recv_prepare(to_curr_replica, r_name, m_queue, byz_status, g, visible_log, replica_session_keys, r_idx):
    # wait to receive prepare messages from at least g other distinct replicas
    sender_count = 0
    senders = {}
    while sender_count < g:
        received = False
        while not received:
            queue_elem = to_curr_replica["to_machine"].get()
            if len(queue_elem) == 1 and queue_elem[0]["Type"] == "Prepare":
                received = True 

                # verify that the prepare message is signed by the sender
                curr_sender = queue_elem[0]["Sender"]
                curr_prepare_communication = queue_elem[0]["Communication"]
                curr_msg = curr_prepare_communication["Message"]
                shared_key = replica_session_keys[curr_sender]
                provided_digest = curr_prepare_communication["Authenticator"][r_idx]
                if not verify_mac(curr_msg, shared_key, provided_digest):
                    continue

            elif len(queue_elem) == 1 and queue_elem[0]["Type"] == "New view":
                return None

            curr_sender = queue_elem[0]["Sender"]
            if curr_sender not in senders:
                sender_count += 1
                senders[curr_sender] = True

        visible_log.append("{} {}".format(r_name, queue_elem))

    if byz_status:
        byz_replica_recv_prepare(byz_status)
    else:
        visible_log.append("{} {}".format(r_name, "prepare messages received!"))

    m_queue.put(r_name + " prepare phase done")
    visible_log.append(to_curr_replica["from_main"].get())
    return True

def send_commit(queues, client_name, r_name, m_queue, byz_status, m, visible_log, frontend_log, primary_name, r_idx, replica_names, replica_session_keys, curr_view):
    # all replicas broadcast commit message to all other replicas
    if byz_status:
        byz_replica_send_commit(byz_status)
    else:
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                commit_msg = generate_commit_msg(r_name, q_name, m, primary_name, r_idx, replica_names, replica_session_keys, curr_view)
                q["to_machine"].put([commit_msg])
                frontend_log.append(commit_msg)
        visible_log.append("{} has sent commit messages".format(r_name)) 

def recv_commit(to_curr_replica, r_name, m_queue, byz_status, m, g, visible_log, frontend_log, replica_session_keys, r_idx):
    # wait to receive commit messages from at least g other distinct replicas
    sender_count = 0
    senders = {}
    while sender_count < g:
        received = False
        while not received:
            queue_elem = to_curr_replica["to_machine"].get()
            if len(queue_elem) == 1 and queue_elem[0]["Type"] == "Commit":
                received = True 

                # verify that the prepare message is signed by the sender
                curr_sender = queue_elem[0]["Sender"]
                curr_prepare_communication = queue_elem[0]["Communication"]
                curr_msg = curr_prepare_communication["Message"]
                shared_key = replica_session_keys[curr_sender]
                provided_digest = curr_prepare_communication["Authenticator"][r_idx]
                if not verify_mac(curr_msg, shared_key, provided_digest):
                    continue

            curr_sender = queue_elem[0]["Sender"]
            if curr_sender not in senders:
                sender_count += 1
                senders[curr_sender] = True 

        visible_log.append("{} {}".format(r_name, queue_elem))

    if byz_status:
        byz_replica_recv_commit(byz_status)
    else:
        visible_log.append("{} {}".format(r_name, "commit messages received!"))

    m_queue.put(r_name + " commit phase done")
    visible_log.append(to_curr_replica["from_main"].get())

def send_inform(to_client, client_name, r_name, byz_status, curr_transaction, p, r, visible_log, frontend_log, primary_name, r_idx, curr_view, replica_client_key):
    if byz_status:
        byz_replica_send_inform(to_client, client_name, r_name, byz_status, curr_transaction, p, r, visible_log, frontend_log, primary_name)
    else:
        inform_msg = generate_inform_msg(r_name, client_name, curr_transaction, p, r, primary_name, replica_client_key, r_idx, curr_view)
        to_client.put([inform_msg])
        clean_inform_msg = copy.deepcopy(inform_msg)
        # clean_inform_msg["Transaction"] = str(clean_inform_msg["Transaction"].message.decode("utf-8"))
        frontend_log.append(clean_inform_msg)
        visible_log.append("{} has sent inform message to client".format(r_name))
