from message_generator import generate_prepare_msg, generate_commit_msg, generate_inform_msg, generate_view_change_msg, generate_new_view_msg

## REPLICA FUNCTIONS
def send_view_change(queues, r_name, client_name, frontend_log):
    # stop the byzantine commit algorithm for view v 
    # broadcast viewchange(E, v) to all replicas [E = set of all requests m prepared by R]
    for q_name, q in queues.items():
        if q_name != client_name:
            view_change_msg = generate_view_change_msg(r_name, q_name)
            q["to_machine"].put([view_change_msg])
            frontend_log.append(view_change_msg)

# def recv_view_change(r_name, to_curr_replica):
#     ## CHANGE THIS -- should be integrated into all while loops i.e. replicas should always be searching for view change messages
#     # receive at least f + 1 viewchange(e_i, v_i) messages
#     # detects failure in current view v
#     sender_count = 0
#     senders = {}
#     while sender_count < f + 1:
#         received = False 
#         while not received:
#             queue_elem = to_curr_replica["to_machine"].get()
#             if len(queue_elem) == 1 and queue_elem[0]["Type"] == "View change":
#                 received = True 
#                 curr_sender = queue_elem[0]["Sender"]
#                 if curr_sender not in senders:
#                     sender_count += 1
#                     senders[curr_sender] = True
#     print("{} received f + 1 view change".format(r_name))

def send_new_view(queues, r_name, client_name, to_curr_replica, curr_view, g, frontend_log):
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
        if q_name != client_name:
            new_view_msg = generate_new_view_msg(r_name, q_name, curr_view + 1)
            q["to_machine"].put([new_view_msg])
            frontend_log.append(new_view_msg)

def recv_new_view(r_name, to_curr_replica):
    received = False
    while not received:
        queue_elem = to_curr_replica["to_machine"].get()
        if len(queue_elem) == 1 and queue_elem[0]["Type"] == "New view":
            received = True
            print("{} received new view".format(r_name))

def recv_preprepare(to_curr_replica, client_name, queues, r_name, m_queue, g, visible_log, frontend_log):
    received = False
    counter = 0
    detected_failure = False
    while not received:
        try:
            queue_elem = to_curr_replica["to_machine"].get(timeout = 1)
            if len(queue_elem) == 1 and queue_elem[0]["Type"] == "Pre-prepare":
                received = True 
                visible_log.append("{} {}".format(r_name, queue_elem))
                visible_log.append("{} {}".format(r_name, "pre-prepare message received!"))
            else:
                print("other message", queue_elem)
                counter += 1
        except:
            counter += 1
            if counter > 10:
                print("{} has detected primary failure".format(r_name))
                send_view_change(queues, r_name, client_name, frontend_log)
                detected_failure = True
                break

    if detected_failure:
        if r_name == "Replica_1":
            # send new view message
            send_new_view(queues, r_name, client_name, to_curr_replica, 0, g, frontend_log)
        else:
            # receive new view message
            recv_new_view(r_name, to_curr_replica)
        return None

    m_queue.put(r_name + " pre-prepare phase done")
    visible_log.append(to_curr_replica["from_main"].get())

    preprepare_received = queue_elem[0]
    m = {
        "Transaction": preprepare_received["Transaction"],
        "View": preprepare_received["View"],
        "Num_transaction": preprepare_received["Num_transaction"],
    }
    return m

def send_prepare(queues, client_name, r_name, byz_status, m, visible_log, frontend_log):
    # all replicas broadcast prepare message to all other replicas
    if not byz_status:
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                prep_msg = generate_prepare_msg(r_name, q_name, m)
                q["to_machine"].put([prep_msg])
                frontend_log.append(prep_msg)
        visible_log.append("{} has sent prepare messages".format(r_name)) 

def recv_prepare(to_curr_replica, r_name, m_queue, byz_status, g, visible_log):
    # wait to receive prepare messages from at least g other distinct replicas
    sender_count = 0
    senders = {}
    while sender_count < g:
        received = False
        while not received:
            queue_elem = to_curr_replica["to_machine"].get()
            if len(queue_elem) == 1 and queue_elem[0]["Type"] == "Prepare":
                received = True 
            elif len(queue_elem) == 1 and queue_elem[0]["Type"] == "New view":
                return None

            curr_sender = queue_elem[0]["Sender"]
            if curr_sender not in senders:
                sender_count += 1
                senders[curr_sender] = True

        visible_log.append("{} {}".format(r_name, queue_elem))

    if not byz_status:
        visible_log.append("{} {}".format(r_name, "prepare messages received!"))

    m_queue.put(r_name + " prepare phase done")
    visible_log.append(to_curr_replica["from_main"].get())
    return True

def send_commit(queues, client_name, r_name, m_queue, byz_status, m, visible_log, frontend_log):
    # all replicas broadcast commit message to all other replicas
    if not byz_status:
        for q_name, q in queues.items():
            if q_name != client_name and q_name != r_name:
                commit_msg = generate_commit_msg(r_name, q_name, m)
                q["to_machine"].put([commit_msg])
                frontend_log.append(commit_msg)
        visible_log.append("{} has sent commit messages".format(r_name)) 

def recv_commit(to_curr_replica, r_name, m_queue, byz_status, m, g, visible_log, frontend_log):
    # wait to receive commit messages from at least g other distinct replicas
    sender_count = 0
    senders = {}
    while sender_count < g:
        received = False
        while not received:
            queue_elem = to_curr_replica["to_machine"].get()
            if len(queue_elem) == 1 and queue_elem[0]["Type"] == "Commit":
                received = True 

            curr_sender = queue_elem[0]["Sender"]
            if curr_sender not in senders:
                sender_count += 1
                senders[curr_sender] = True 

        visible_log.append("{} {}".format(r_name, queue_elem))

    if not byz_status:
        visible_log.append("{} {}".format(r_name, "commit messages received!"))

    m_queue.put(r_name + " commit phase done")
    visible_log.append(to_curr_replica["from_main"].get())

def send_inform(to_client, client_name, r_name, byz_status, curr_transaction, p, r, visible_log, frontend_log):
    if not byz_status:
        inform_msg = generate_inform_msg(r_name, client_name, curr_transaction, p, r)
        to_client.put([inform_msg])
        frontend_log.append(inform_msg)
        visible_log.append("{} has sent inform message to client".format(r_name))
