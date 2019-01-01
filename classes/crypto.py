# coding: utf8
import sys
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
from classes import config

class prpcrypt():
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    # 加密函数，如果text不是16的倍数【加密文本text必须为16的倍数！】，那就补足为16的倍数
    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        # 这里密钥key 长度必须为16（AES-128）、24（AES-192）、或32（AES-256）Bytes 长度.目前AES-128足够用
        length = 16
        count = len(text)
        add = length - (count % length)
        text = text + ('\0' * add)
        self.ciphertext = cryptor.encrypt(text)
        # 因为AES加密时候得到的字符串不一定是ascii字符集的，输出到终端或者保存时候可能存在问题
        # 所以这里统一把加密后的字符串转化为16进制字符串
        return b2a_hex(self.ciphertext)

    # 解密后，去掉补足的空格用strip() 去掉
    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, self.key)
        plain_text = cryptor.decrypt(a2b_hex(text))
        return plain_text.rstrip('\0')



def passwd_aes(db_passwd):
    '''
    AES加密密码
    :return:
    '''
    _config = config.config("../conf/crypto.ini")
    crypto_str = _config.getOption(section="crypto", option="key_str")
    pc = prpcrypt(crypto_str)  # 初始化密钥
    e = pc.encrypt(db_passwd)
    return e

def passwd_deaes(db_passwd_aes):
    _config = config.config("../conf/crypto.ini")
    print
    crypto_str = _config.getOption(section="crypto", option="key_str")
    pc = prpcrypt(crypto_str)  # 初始化密钥
    d = pc.decrypt(db_passwd_aes)
    return d

