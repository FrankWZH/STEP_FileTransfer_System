from socket import *
import argparse
import json
import struct
import hashlib
import time
from os.path import getsize

# Const Value
# 给这些变量赋上字符串值
OP_SAVE, OP_DELETE, OP_GET, OP_UPLOAD, OP_DOWNLOAD, OP_BYE, OP_LOGIN, OP_ERROR = 'SAVE', 'DELETE', 'GET', 'UPLOAD', 'DOWNLOAD', 'BYE', 'LOGIN', "ERROR"
TYPE_FILE, TYPE_DATA, TYPE_AUTH, DIR_EARTH = 'FILE', 'DATA', 'AUTH', 'EARTH'
FIELD_OPERATION, FIELD_DIRECTION, FIELD_TYPE, FIELD_USERNAME, FIELD_PASSWORD, FIELD_TOKEN = 'operation', 'direction', 'type', 'username', 'password', 'token'
FIELD_KEY, FIELD_SIZE, FIELD_TOTAL_BLOCK, FIELD_MD5, FIELD_BLOCK_SIZE = 'key', 'size', 'total_block', 'md5', 'block_size'
FIELD_STATUS, FIELD_STATUS_MSG, FIELD_BLOCK_INDEX = 'status', 'status_msg', 'block_index'
DIR_REQUEST, DIR_RESPONSE = 'REQUEST', 'RESPONSE'



# 终端配置
def _argparse():
    parse = argparse.ArgumentParser()
    parse.add_argument("--ip", default='', action='store', required=False, dest="ip",
                       help="The IP address bind to the server. Default bind all IP.")
    parse.add_argument("--port", default='1379', action='store', required=False, dest="port",
                       help="The port that server listen on. Default is 1379.")
    parse.add_argument("--file", required=True, help="The file used for uploading.")
    return parse.parse_args()

# 将文件转换为md5格式的方法
def getfile_md5(filename):
    """
    Get MD5 value for big file
    :param filename:
    :return:
    """

    # 用hashlib模块创建md5哈希对象，可以将任意长度的数据转换成固定长度的哈希值
    m = hashlib.md5()
    with open(filename, 'rb') as fid:
        # while true: 无限循环，直到读取的d为空的时候停止，否则一直读文件
        while True:
            d = fid.read(2048)
            if not d:
                break
            # 用m来更新哈希值
            m.update(d)
    # 返回文件哈希值的16进制形式
    return m.hexdigest()


# 将信息转换为需求格式的数据包
def make_packet(json_data, bin_data=None):
    """
    Make a packet following the STEP protocol.
    Any information or data for TCP transmission has to use this function to get the packet.
    :param json_data:
    :param bin_data:
    :return:
        The complete binary packet
    """
    # 将json_data先转换为字典格式再转换为json格式，如果要反过来就用json.loads()
    j = json.dumps(dict(json_data), ensure_ascii=False)
    j_len = len(j)
    # struct.pack() 是 Python 中的一个函数，用于将 Python 值按照给定的格式字符串打包成字节序列
    if bin_data is None:
        return struct.pack('!II', j_len, 0) + j.encode()
    else:
        return struct.pack('!II', j_len, len(bin_data)) + j.encode() + bin_data

# 用于将tcp流中的数据格式转换为json_data和bin_data的形式
def get_tcp_packet(conn):
    # conn是那个连接的时候accept收到的那个server用于与对应client通信的connection
    """
    Receive a complete TCP "packet" from a TCP stream and get the json data and binary data.
    :param conn: the TCP connection
    :return:
        json_data
        bin_data
    """
    # 创建一个空的字节串
    bin_data = b''

    # 其实就是1.如果说接收到的数据为空返回None，2.如果不为空并且前面八个都是满的的化，就是八个，直接跳出循环
    # 3.如果前面八个不是满的的化，就可以进行第二次循环
    while len(bin_data) < 8:
        # 接收长度为8
        data_rec = conn.recv(8)
        # 如果收到的数据为空 睡眠0.01s
        if data_rec == b'':
            time.sleep(0.01)
        if data_rec == b'':
            return None, None
        bin_data += data_rec

    # data是前面八位
    # bin_data是第八位之后的,所以应该是上面的情况3才会有bin_data
    data = bin_data[:8]
    bin_data = bin_data[8:]
    # 变回字符串形式，j_len是json文件长度，b_len是bin_data的长度
    j_len, b_len = struct.unpack('!II', data)

    # 如果发现bin_data长度比j_len小，就用data_rec收取j_len长度的数据，然后把bin_data加长之后再截取前面j_len个数据，这样保证j_bin的长度至少是j_len
    while len(bin_data) < j_len:
        data_rec = conn.recv(j_len)
        if data_rec == b'':
            time.sleep(0.01)
        if data_rec == b'':
            return None, None
        bin_data += data_rec
    j_bin = bin_data[:j_len]

    # 变回python文件形式
    try:
        json_data = json.loads(j_bin.decode())
    except Exception as ex:
        return None, None

    # 保证bin_data的长度至少为b_len
    bin_data = bin_data[j_len:]
    while len(bin_data) < b_len:
        data_rec = conn.recv(b_len)
        if data_rec == b'':
            time.sleep(0.01)
        if data_rec == b'':
            return None, None
        bin_data += data_rec
    return json_data, bin_data

# 主函数
def main():
    parser = _argparse()
    server_hostname = parser.ip
    server_port = int(parser.port)
    print('IP:', server_hostname)
    print('Port:', server_port)
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((server_hostname, server_port))


    username = input("Please enter your username")
    # 从username得到password
    password = hashlib.md5(username.encode()).hexdigest()

    # 提供需求信息并打包
    json_data = {FIELD_OPERATION:OP_LOGIN, FIELD_DIRECTION:DIR_REQUEST, FIELD_TYPE:TYPE_AUTH, FIELD_USERNAME:username, FIELD_PASSWORD:password}
    message = make_packet(json_data)
    client_socket.send(message)

    # 收取来自Server的信息
    message0, message1 = get_tcp_packet(client_socket)
    print(message0)
    print(type(message0))
    TOKEN = message0[FIELD_TOKEN]
    print('TOKEN:', TOKEN)

    # 得到文件路径 /Users/wuzihang/Desktop/test.txt
    file_path = parser.file
    print(file_path)
    file_size = getsize(file_path)
    print(file_size)
    print(type(file_size))

    # 得到文件名
    file_name = (file_path.split('/'))[-1]
    print(file_name)

    # 发送针对于file的save操作，并接受来自于server的upload plan
    json_data2 = {FIELD_OPERATION:OP_SAVE, FIELD_DIRECTION:DIR_REQUEST, FIELD_TYPE:TYPE_FILE, FIELD_SIZE: file_size, FIELD_TOKEN:TOKEN}
    message_send = make_packet(json_data2)
    client_socket.send(message_send)
    message_recv0, message_recv1 = get_tcp_packet(client_socket)
    print(message_recv0)

# 从upload plan中获得对应的block大小以及block的总个数
    block_size = message_recv0[FIELD_BLOCK_SIZE]
    total_block = message_recv0[FIELD_TOTAL_BLOCK]
    key = message_recv0[FIELD_KEY]
    print(block_size)
    print(total_block)

# 将文件以block为单位进行读取并上传
    try:
        with open(file_path, 'rb') as source:
            for i in range(int(total_block)):
                block = source.read(int(block_size))
                if not block:
                    break

                # binary_content = ' '.join(format(byte, '08b') for byte in block)

                # 对应的json_data部分
                json_data3 = {FIELD_KEY:key, FIELD_OPERATION:OP_UPLOAD, FIELD_DIRECTION:DIR_REQUEST, FIELD_TYPE:TYPE_FILE, FIELD_TOKEN:TOKEN, FIELD_BLOCK_INDEX:i}

                message_send2 = make_packet(json_data3, bin_data=block)
                client_socket.send(message_send2)
                message_recv2, message_recv3 = get_tcp_packet(client_socket)
                print(message_recv2)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")



    # 提取server返回的md5值用于验证
    md5_recv = message_recv2[FIELD_MD5]
    # 将原文件直接转换为md5格式用于验证
    md5_testify = getfile_md5(file_path)
    # 验证成功，表明文件上传完整
    if md5_recv==md5_testify:
        print("md5 test success")



    client_socket.close()




if __name__ == '__main__':
    main()



