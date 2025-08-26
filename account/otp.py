import pyotp


def generateKey():
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret, digits=4, interval=9999)
    OTP = totp.now()
    return {"totp": secret, "OTP": OTP}


def verify_otp(activation_key, otp):
    totp = pyotp.TOTP(activation_key, digits=4, interval=9999)
    verify = totp.verify(otp)
    return verify