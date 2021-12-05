from datetime import datetime
import hashlib
import json

def generate_transaction_msg(sender, recipient, curr_transaction, curr_view, p, client_session_keys, replica_names):
    communication = {
        "Operation": curr_transaction,
        "Timestamp": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        "Client_name": sender,
    }

    communication_bytes = json.dumps(communication).encode("utf-8")
    digests = []
    
    for r_name in replica_names:
        if r_name == sender:
            continue
        replica_session_key = client_session_keys[r_name]
        digest_input = communication_bytes + replica_session_key
        input_encoding = hashlib.md5(digest_input)
        curr_digest = input_encoding.digest()[:-10]
        digests.append(curr_digest)

    sent_message = {
        "Message": communication_bytes,
        "Authenticator": digests
    }

    signed_msg = {
        "Type": "Transaction",
        "Sender": sender,
        "Recipient": recipient,
        "Communication": sent_message, # <o, t, c>_client signature
        "View": curr_view,
        "Num_transaction": p,
    }
    return signed_msg

def generate_preprepare_msg(sender, recipient, curr_transaction, m_auth, curr_view, p, primary, primary_session_keys, replica_names):
    communication = {
        "View": curr_view,
    }
    communication_bytes = json.dumps(communication).encode("utf-8")
    digests = []
    
    for r_name in replica_names:
        if r_name == sender:
            digests.append(None)
            continue
        replica_session_key = primary_session_keys[r_name]
        digest_input = communication_bytes + replica_session_key
        input_encoding = hashlib.md5(digest_input)
        curr_digest = input_encoding.digest()[:-10]
        digests.append(curr_digest)

    sent_message = {
        "Message": curr_transaction, # already signed by client
        "Primary_message": communication_bytes,
        "Authenticator": digests
    }

    msg = {
        "Type": "Pre-prepare",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "Communication": sent_message, # <v, n, d>_primary signature, m
        "View": curr_view,
        "Num_transaction": p,
    }
    return msg

def generate_prepare_msg(sender, recipient, m, primary, r_idx, replica_names, replica_session_keys, curr_view, p):
    communication = {
        "View": curr_view,
        "Replica": r_idx
    }
    communication_bytes = json.dumps(communication).encode("utf-8")
    digests = []
    
    for r_name in replica_names:
        if r_name == sender:
            digests.append(None)
            continue
        replica_session_key = replica_session_keys[r_name]
        digest_input = communication_bytes + replica_session_key
        input_encoding = hashlib.md5(digest_input)
        curr_digest = input_encoding.digest()[:-10]
        digests.append(curr_digest)

    sent_message = {
        "Message": communication_bytes, # signed by current replica
        "Authenticator": digests
    }

    return {
        "Type": "Prepare",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "Communication": sent_message,
        "Num_transaction": p,
    }

def generate_commit_msg(sender, recipient, m, primary, r_idx, replica_names, replica_session_keys, curr_view, p):
    communication = {
        "View": curr_view,
        "Replica": r_idx
    }
    communication_bytes = json.dumps(communication).encode("utf-8")
    digests = []
    
    for r_name in replica_names:
        if r_name == sender:
            digests.append(None)
            continue
        replica_session_key = replica_session_keys[r_name]
        digest_input = communication_bytes + replica_session_key
        input_encoding = hashlib.md5(digest_input)
        curr_digest = input_encoding.digest()[:-10]
        digests.append(curr_digest)
    
    sent_message = {
        "Message": communication_bytes, # signed by current replica
        "Authenticator": digests
    }

    return {
        "Type": "Commit",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "Communication": sent_message,
        "Num_transaction": p,
    }

def generate_inform_msg(sender, recipient, curr_transaction, p, r, primary, replica_client_key, r_idx, curr_view):
    communication = {
        "View": curr_view,
        "Replica": r_idx,
        "Timestamp": datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
        "Result": r
    }
    communication_bytes = json.dumps(communication).encode("utf-8")
    digest_input = communication_bytes + replica_client_key
    input_encoding = hashlib.md5(digest_input)
    digest = input_encoding.digest()[:-10]
    
    sent_message = {
        "Message": communication_bytes, # signed by current replica
        "Digest": digest
    }

    return {
        "Type": "Inform",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "Num_transaction": p,
        "Communication": sent_message,
    }

def generate_view_change_msg(sender, recipient, primary, replica_signing_key, r_idx, curr_view, p):
    communication = {
        "View": curr_view + 1,
        "Replica": r_idx,
    }
    communication_bytes = json.dumps(communication).encode("utf-8")
    signed_communication = replica_signing_key.sign(communication_bytes)

    return {
        "Type": "View change",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "Communication": signed_communication,
        "Num_transaction": p,
    }

def generate_new_view_msg(sender, recipient, new_view, primary, replica_signing_key, r_idx, p):
    communication = {
        "View": new_view,
        "Replica": r_idx
    }
    communication_bytes = json.dumps(communication).encode("utf-8")
    signed_communication = replica_signing_key.sign(communication_bytes)

    return {
        "Type": "New view",
        "Sender": sender,
        "Recipient": recipient,
        "Primary": primary,
        "View": new_view,
        "Communication": signed_communication,
        "Num_transaction": p,
    }
