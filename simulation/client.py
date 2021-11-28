from simulation.message_generator import generate_transaction_msg

## CLIENT FUNCTIONS
def send_transaction(queues, client_name, primary_name, curr_transaction, curr_view, p):
    for q_name, q in queues.items():
        if q_name != client_name:
            if q_name == primary_name:
                print("Client sending transaction to primary", primary_name)
                q["to_machine"].put((generate_transaction_msg(client_name, primary_name, curr_transaction, curr_view, p), primary_name))
            else:
                print("Client sending transaction to replica", q_name)
                q["to_machine"].put((None, primary_name))

def replica_ack_primary(to_client, num_replicas, m_queue):
    for i in range(num_replicas):
        to_client["to_machine"].get()
    m_queue.put("replica inform done")
    to_client["from_main"].get()

def recv_inform(to_client, f, visible_log):
    # gather inform messages from f + 1 distinct senders
    sender_count = 0
    senders = {}
    while sender_count < f + 1:
        received = False
        while not received:
            queue_elem = to_client["to_machine"].get()
            if len(queue_elem) == 1 and type(queue_elem[0]) == dict and queue_elem[0]["Type"] == "Inform":
                received = True 
                curr_sender = queue_elem[0]["Sender"]
                if curr_sender not in senders:
                    sender_count += 1
                    senders[curr_sender] = True
            # detected failure in pre-prepare stage -- resend transaction
            elif len(queue_elem) == 1 and type(queue_elem[0]) == dict and queue_elem[0]["Type"] == "New view":
                print("detected failure received by client")
                return None
        visible_log.append("client received {}".format(queue_elem))
    visible_log.append("client has received inform messages!")
    return True
