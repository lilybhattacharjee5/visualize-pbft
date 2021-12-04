from nacl.signing import SigningKey, VerifyKey
import hashlib

def verify_signature(signed_msg, verify_key):
    try:
        verify_key.verify(signed_msg)
        return True
    except:
        return False

def verify_mac(msg, shared_key, provided_digest):
    print("mac inputs", msg, shared_key, provided_digest)
    return True
    # print("INSIDE VERIFY MAC")
    # digest_input = msg + shared_key 
    # input_encoding = hashlib.md5(digest_input)
    # digest = input_encoding.digest()[:-10]
    # print("CHECKING", provided_digest, digest)

    # if digest == provided_digest:
    #     return True
    # return False
