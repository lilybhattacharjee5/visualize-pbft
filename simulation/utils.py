from nacl.signing import SigningKey, VerifyKey

def verify_signature(signed_msg, verify_key):
    try:
        verify_key.verify(signed_msg)
        return True
    except:
        return False
