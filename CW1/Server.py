from socket import *
import struct #struct
import json
import os
from os.path import join, getsize
import hashlib
import argparse
from threading import Thread
import time
import logging
from logging.handlers import TimedRotatingFileHandler
import base64
import uuid
import math
import shutil

MAX_PACKET_SIZE = 20480

# Const Value
# 给这些变量赋上字符串值
OP_SAVE, OP_DELETE, OP_GET, OP_UPLOAD, OP_DOWNLOAD, OP_BYE, OP_LOGIN, OP_ERROR = 'SAVE', 'DELETE', 'GET', 'UPLOAD', 'DOWNLOAD', 'BYE', 'LOGIN', "ERROR"
TYPE_FILE, TYPE_DATA, TYPE_AUTH, DIR_EARTH = 'FILE', 'DATA', 'AUTH', 'EARTH'
FIELD_OPERATION, FIELD_DIRECTION, FIELD_TYPE, FIELD_USERNAME, FIELD_PASSWORD, FIELD_TOKEN = 'operation', 'direction', 'type', 'username', 'password', 'token'
FIELD_KEY, FIELD_SIZE, FIELD_TOTAL_BLOCK, FIELD_MD5, FIELD_BLOCK_SIZE = 'key', 'size', 'total_block', 'md5', 'block_size'
FIELD_STATUS, FIELD_STATUS_MSG, FIELD_BLOCK_INDEX = 'status', 'status_msg', 'block_index'
DIR_REQUEST, DIR_RESPONSE = 'REQUEST', 'RESPONSE'

# 创建一个用来记录日志信息的对象，记录程序的各种信息
logger = logging.getLogger('')


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

# ext是文件本来的名字吗？
def get_time_based_filename(ext, prefix='', t=None):
    """
    Get a filename based on time
    :param ext: ext name of the filename
    :param prefix: prefix of the filename
    :param t: the specified time if necessary, the default is the current time. Unix timestamp
    :return:
    """
    ext = ext.replace('.', '')
    if t is None:
        # 是一个时间戳
        t = time.time()
    if t > 4102464500:
        t = t / 1000
    # 将时间戳转换为local时间之后，转换为前面的特定格式
    # 返回的文件名就是该文件格式+ext（本来名字）
    return time.strftime(f"{prefix}%Y%m%d%H%M%S." + ext, time.localtime(t))

'''
配置日志记录器，要先建立日志记录器，配置文件处理器，配置控制台处理器，然后将文件处理器和控制台处理器添加到日志记录器中
其中首先要建立一个formatter，文件处理器和控制台处理器都需要配置formatter和对应的Level
'''


def set_logger(logger_name):
    """
    Create a logger
    :param logger_name: 日志名称
    :return: logger
    """
    # 建立一个日志记录器
    logger_ = logging.getLogger(logger_name)  # 不加名称设置root logger
    # 日志的级别设置为INFO，只记录INFO级别及以上的信息
    logger_.setLevel(logging.INFO)
# 日志格式化器，用于定义日志消息的格式
    formatter = logging.Formatter(
        '\033[0;34m%s\033[0m' % '%(asctime)s-%(name)s[%(levelname)s] %(message)s @ %(filename)s[%(lineno)d]',
        datefmt='%Y-%m-%d %H:%M:%S')

    # --> LOG FILE
    logger_file_name = get_time_based_filename('log')
    # 创建目录
    os.makedirs(f'log/{logger_name}', exist_ok=True)
    # 将日志写入文件，按天进行轮换，轮换间隔为1天，备份文件为1，在上面建立的目录之下，名字为log
    fh = TimedRotatingFileHandler(filename=f'log/{logger_name}/log', when='D', interval=1, backupCount=1)
    # 为文件处理器设置日志格式化器
    fh.setFormatter(formatter)
    # 设置文件处理器级别为INFO
    fh.setLevel(logging.INFO)

    # --> SCREEN DISPLAY
    # 控制台处理器
    # 将日志输出到控制台
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    # 以防止日志消息被传递到父记录器，避免重复日志。
    logger_.propagate = False

    # 所以说一个完整的日志记录器需要配置添加文件处理器以及控制台处理器
    logger_.addHandler(ch)
    logger_.addHandler(fh)
    return logger_

# 终端配置
def _argparse():
    parse = argparse.ArgumentParser()
    parse.add_argument("--ip", default='', action='store', required=False, dest="ip",
                       help="The IP address bind to the server. Default bind all IP.")
    parse.add_argument("--port", default='1379', action='store', required=False, dest="port",
                       help="The port that server listen on. Default is 1379.")
    return parse.parse_args()


# bin_data 是一个可能存在的2进制数据
# 函数输出的是2进制的字节包
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

# 这个json_data是python数据
def make_response_packet(operation, status_code, data_type, status_msg, json_data, bin_data=None):
    """
    Make a packet for response
    :param operation: [SAVE, DELETE, GET, UPLOAD, DOWNLOAD, BYE, LOGIN]
    :param status_code: 200 or 400+
    :param data_type: [FILE, DATA, AUTH]
    :param status_msg: A human-readable status massage
    :param json_data
    :param bin_data
    :return:
    """
    json_data[FIELD_OPERATION] = operation
    json_data[FIELD_DIRECTION] = DIR_RESPONSE
    json_data[FIELD_STATUS] = status_code
    json_data[FIELD_STATUS_MSG] = status_msg
    json_data[FIELD_TYPE] = data_type
    return make_packet(json_data, bin_data)


# 这个函数的return是收到的信息，分为两个部分json_data和bin_data
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


def data_process(username, request_operation, json_data, connection_socket):
    """
    Data Process
    :param username:
    :param request_operation:
    :param json_data: 是json格式
    :param connection_socket:
    :return: None
    """
    global logger


# 针对于request_operation是get的操作，最终成功的结果是针对实际情况发送一条信息，里面包含了所需求的文件
    if request_operation == OP_GET:
        # 情况一：当缺少key时，发送空字典并且提示错误原因
        if FIELD_KEY not in json_data.keys():
            logger.info(f'<-- Get data without key.')
            logger.error(f'<-- Field "key" is missing for DATA GET.')
            connection_socket.send(make_response_packet(OP_GET, 410, TYPE_DATA, f'Field "key" is missing for DATA GET.', {}))
            return
        logger.info(f'--> Get data {json_data[FIELD_KEY]}')

        # 检查这个文件是否存在，如果说不存在，则发送空字典并且提示错误原因
        # join是将多个路径部分连接成一个完整的路径 这个Field_KEY应该是一个唯一对应着我们想要存取的文件的文件名的键
        if os.path.exists(join('data', username, json_data[FIELD_KEY])) is False:
            logger.error(f'<-- The key {json_data[FIELD_KEY]} is not existing.')
            connection_socket.send(
                make_response_packet(OP_GET, 404, TYPE_DATA, f'The key {json_data[FIELD_KEY]} is not existing.', {}))
            return

        # 前面两个是出现错误的情况，发送的消息都是4开头，下面是正确的情况，发送搜寻到的文件
        try:
            # json_data是来自client信息（json）格式，里边包含的key里包含着所需要get的文件的文件名
            # 所以说with open的时候可以用FIELD_KEY找到路径之后打开文件
            with open(join('data', username, json_data[FIELD_KEY]), 'r') as fid:
                # 如果是这样的化，那么这个所搜寻到的文件是.json格式文件，将里面的数据反序列化，变为python数据
                data_from_file = json.load(fid)
                logger.info(f'<-- Find the data and return to client.')
                connection_socket.send(
                    make_response_packet(OP_GET, 200, TYPE_DATA, f'OK', data_from_file))
        except Exception as ex:
            logger.error(f'{str(ex)}@{ex.__traceback__.tb_lineno}')


# 针对请求任务是SAVE保存任务的,成功的结果是在server中以key为文件名，储存了对应文件，并发送一条信息
    if request_operation == OP_SAVE:
        # 生成一个全局唯一标识符并转换为字符串形式，可以避免主键冲突，文件名冲突
        # 其中uuid4是基于随机数生成，唯一性相当高
        key = str(uuid.uuid4())
        # 如果json_data中有对应的文件名，就用这个文件名，没有的化，文件名就用uuid4生成的唯一表示符
        if FIELD_KEY in json_data.keys():
            key = json_data[FIELD_KEY]
        logger.info(f'--> Save data with key "{key}"')

        # 情况一，当key已经存在的时候，
        if os.path.exists(join('data', username, key)) is True:
            logger.error(f'<-- This key "{key}" is existing.')
            connection_socket.send(make_response_packet(OP_SAVE, 402, TYPE_DATA, f'This key "{key}" is existing.', {}))
            return

        # 情况2，直接打开新文件并将json_data中的内容转换为json格式之后写入文件
        try:
            with open(join('data', username, key), 'w') as fid:
                json.dump(json_data, fid)
                logger.error(f'<-- Data is saved with key "{key}"')
                # FILELD_KEY 始终与文件名组成键值对
                connection_socket.send(
                    make_response_packet(OP_SAVE, 200, TYPE_DATA, f'Data is saved with key "{key}"', {FIELD_KEY: key}))
        except Exception as ex:
            logger.error(f'{str(ex)}@{ex.__traceback__.tb_lineno}')


# 当请求操作是DELETE删除的时候
    if request_operation == OP_DELETE:
        # 情况一：发送的信息中没有对应的key
        if FIELD_KEY not in json_data.keys():
            logger.info(f'--> Delete data without any key.')
            logger.error(f'<-- Field "key" is missing for DATA delete.')
            connection_socket.send(
                make_response_packet(OP_DELETE, 410, TYPE_DATA, f'Field "key" is missing for DATA delete.', {}))
            return
        # 情况二：发送的信息中有对应的key，但是在server的系统中不存在对应的文件名
        if os.path.exists(join('data', username, json_data[FIELD_KEY])) is False:
            logger.error(f'<-- The "key" {json_data[FIELD_KEY]} is not existing.')
            connection_socket.send(
                make_response_packet(OP_DELETE, 404, TYPE_DATA, f'The "key" {json_data[FIELD_KEY]} is not existing.',
                                     {}))
            return

        # 情况3：删除成功
        try:
            os.remove(join('data', username, json_data[FIELD_KEY]))
            logger.error(f'<-- The "key" {json_data[FIELD_KEY]} is deleted.')
            connection_socket.send(
                make_response_packet(OP_DELETE, 200, TYPE_DATA, f'The "key" {json_data[FIELD_KEY]} is deleted.',
                                     {FIELD_KEY: json_data[FIELD_KEY]}))
        except Exception as ex:
            logger.error(f'{str(ex)}@{ex.__traceback__.tb_lineno}')


def file_process(username, request_operation, json_data, bin_data, connection_socket):
    """
    File Process
    :param username:
    :param request_operation:
    :param json_data:
    :param bin_data:
    :param connection_socket:
    :return:
    """
    global logger


# 情况1：这个是负责将对应文件的下载的计划给制作出来，主要用于确定要下载的对应的目标文件名是否在tmp和file文件中都存在，然后返回一个下载计划，之后还有一个DOWNLOAD的操作请求
# 也就是说get是指get下载计划而不是文件本身
    if request_operation == OP_GET:

        # 情况1：发送信息中没有key
        if FIELD_KEY not in json_data.keys():
            logger.info(f'--> Plan to download file {json_data[FIELD_KEY]}')

            connection_socket.send(
                make_response_packet(OP_GET, 410, TYPE_FILE, f'Field "key" is missing for DATA GET.', {}))
            return

        # 情况2：key在两个文件夹中都不存在
        logger.info(f'--> Plan to download file with "key" {json_data[FIELD_KEY]}')
        if os.path.exists(join('file', username, json_data[FIELD_KEY])) is False and os.path.exists(
                join('tmp', username, json_data[FIELD_KEY])) is False:
            logger.error(f'<-- The key {json_data[FIELD_KEY]} is not existing.')
            connection_socket.send(
                make_response_packet(OP_GET, 404, TYPE_FILE, f'The key {json_data[FIELD_KEY]} is not existing.', {}))
            return

        # 情况3：key在file中没有，tmp中存在，部分uploaded
        if os.path.exists(join('file', username, json_data[FIELD_KEY])) is False and os.path.exists(
                join('tmp', username, json_data[FIELD_KEY])) is True:
            logger.error(f'<-- The key {json_data[FIELD_KEY]} is not completely uploaded.')
            connection_socket.send(
                make_response_packet(OP_GET, 404, TYPE_FILE,
                                     f'The key {json_data[FIELD_KEY]} is not completely uploaded.', {}))
            return

        file_path = join('file', username, json_data[FIELD_KEY])
        file_size = getsize(file_path)
        block_size = MAX_PACKET_SIZE
        total_block = math.ceil(file_size / block_size)
        md5 = getfile_md5(file_path)
        # Download Plan
        rval = {
            FIELD_KEY: json_data[FIELD_KEY],
            FIELD_SIZE: file_size,
            FIELD_TOTAL_BLOCK: total_block,
            FIELD_BLOCK_SIZE: block_size,
            FIELD_MD5: md5
        }
        logger.info(f'<-- Plan: file size {file_size}, total block number {FIELD_TOTAL_BLOCK}.')
        connection_socket.send(
            make_response_packet(OP_GET, 200, TYPE_FILE, f'OK. This is the download plan.', rval))
        return

# 如果操作是save
    if request_operation == OP_SAVE:
        key = str(uuid.uuid4())
        if FIELD_KEY in json_data.keys():
            key = json_data[FIELD_KEY]
        logger.info(f'--> Plan to save/upload a file with key "{key}"')

        # 情况1：对应的文件名已经存在
        if os.path.exists(join('file', username, key)) is True:
            logger.error(f'<-- This key "{key}" is existing.')
            connection_socket.send(make_response_packet(OP_SAVE, 402, TYPE_FILE, f'This "key" {key} is existing.', {}))
            return
        # 情况2：对应发送的请求中没有能包含size的信息
        if FIELD_SIZE not in json_data.keys():
            logger.error(f'<-- This file "size" has to be included.')
            connection_socket.send(
                make_response_packet(OP_SAVE, 402, TYPE_FILE, f'This file "size" has to be included', {}))
            return

        file_size = json_data[FIELD_SIZE]
        block_size = MAX_PACKET_SIZE
        total_block = math.ceil(file_size / block_size)

        # 情况3：成功，返回上传计划，并且写一个tmp文件
        try:
            rval = {
                FIELD_KEY: key,
                FIELD_SIZE: file_size,
                FIELD_TOTAL_BLOCK: total_block,
                FIELD_BLOCK_SIZE: block_size,
            }
            # Write a tmp file
            with open(join('tmp', username, key), 'wb+') as fid:
                fid.seek(file_size - 1)
                fid.write(b'\0')

            fid = open(join('tmp', username, key + '.log'), 'w')
            fid.close()

            logger.error(f'<-- Upload plan: key {key}, total block number {total_block}, block size {block_size}.')
            connection_socket.send(
                make_response_packet(OP_SAVE, 200, TYPE_FILE, f'This is the upload plan.', rval))
        except Exception as ex:
            logger.error(f'{str(ex)}@{ex.__traceback__.tb_lineno}')

# 当请求是DELETE的时候
    if request_operation == OP_DELETE:

        # 情况1：当发送的信息中缺少了key的时候
        if FIELD_KEY not in json_data.keys():
            logger.info(f'--> Delete file without any key.')
            logger.error(f'<-- Field "key" is missing for FILE delete.')
            connection_socket.send(
                make_response_packet(OP_GET, 410, TYPE_FILE, f'Field "key" is missing for FILE delete.', {}))
            return
#
        if os.path.exists(join('file', username, json_data[FIELD_KEY])) is False:

            # 情况2.1当系统中file文件夹内不存在对应的文件名，但是tmp中存在对应文件名时候，删除tmp文件中的两个对应文件（有一个带有.log）
            if os.path.exists(join('tmp', username, json_data[FIELD_KEY])) is True:
                try:
                    os.remove(join('tmp', username, json_data[FIELD_KEY]))
                    os.remove(join('tmp', username, json_data[FIELD_KEY]) + '.log')
                except Exception as ex:
                    logger.error(f'{str(ex)}@{ex.__traceback__.tb_lineno}')
                logger.error(
                    f'<-- The "key" {json_data[FIELD_KEY]} is not completely uploaded. The tmp files are deleted.')
                connection_socket.send(
                    make_response_packet(OP_GET, 404, TYPE_FILE,
                                         f'The "key" {json_data[FIELD_KEY]} is not completely uploaded. '
                                         f'The tmp files are deleted.',
                                         {}))
                return

            # 情况2.2当tmp和file文件夹内都不存在对应的信息的时候，直接返回不存在
            logger.error(f'<-- The "key" {json_data[FIELD_KEY]} is not existing.')
            connection_socket.send(
                make_response_packet(OP_GET, 404, TYPE_FILE, f'The "key" {json_data[FIELD_KEY]} is not existing.', {}))
            return

        # 情况3：
        try:
            os.remove(join('file', username, json_data[FIELD_KEY]))
            logger.error(f'<-- The "key" {json_data[FIELD_KEY]} is deleted.')
            connection_socket.send(
                make_response_packet(OP_GET, 200, TYPE_FILE, f'The "key" {json_data[FIELD_KEY]} is deleted.',
                                     {FIELD_KEY: json_data[FIELD_KEY]}))
        except Exception as ex:
            logger.error(f'{str(ex)}@{ex.__traceback__.tb_lineno}')

# 情况4：如果操作请求是UPLOAD，这应该是对应着save里边的操作，save只是创建了文件，现在要上传
    if request_operation == OP_UPLOAD:
        # 情况1：当上传的目标文件名不存在的时候：返回错误信息
        if FIELD_KEY not in json_data.keys():
            logger.info(f'--> Upload file/block without any key.')
            logger.error(f'<-- Field "key" is missing for FILE block uploading.')
            connection_socket.send(
                make_response_packet(OP_UPLOAD, 410, TYPE_FILE, f'Field "key" is missing for FILE uploading.', {}))
            return

        # 情况2：当上传的目标文件名在file中已经存在的时候，也就是已经完全上传
        logger.info(f'--> Upload file/block of "key" {json_data[FIELD_KEY]}.')
        if os.path.exists(join('file', username, json_data[FIELD_KEY])) is True:
            logger.error(f'<-- The "key" {json_data[FIELD_KEY]} is completely uploaded.')
            connection_socket.send(
                make_response_packet(OP_UPLOAD, 408, TYPE_FILE, f'The "key" {json_data[FIELD_KEY]} is completely uploaded.', {}))
            return
        # 情况3：当文件名在tmp中不存在的时候，不接受上传（所以说必须先出现在tmp中再出现在file中，换句话说，必须先save，再upload
        if os.path.exists(join('tmp', username, json_data[FIELD_KEY])) is False:
            logger.error(
                f'<-- The "key" {json_data[FIELD_KEY]} is not accepted for uploading.')
            connection_socket.send(
                make_response_packet(OP_UPLOAD, 408, TYPE_FILE,
                                     f'The "key" {json_data[FIELD_KEY]} is not accepted for uploading.',
                                     {}))
            return

        # 情况4：在前面的要求都满足的情况下，没有写block_index
        if FIELD_BLOCK_INDEX not in json_data.keys():
            logger.error(f'<-- The "block_index" is compulsory.')
            connection_socket.send(
                make_response_packet(OP_UPLOAD, 410, TYPE_FILE, f'The "block_index" is compulsory.', {}))
            return

        # 从tmp文件中获取文件的相关信息
        file_path = join('tmp', username, json_data[FIELD_KEY])
        file_size = getsize(file_path)
        block_size = MAX_PACKET_SIZE
        total_block = math.ceil(file_size / block_size)
        block_index = json_data[FIELD_BLOCK_INDEX]

        # 情况5：block_index超过了对应的block_size
        if block_index >= total_block:
            logger.error(f'<-- The "block_index" exceed the max index.')
            connection_socket.send(
                make_response_packet(OP_UPLOAD, 405, TYPE_FILE, f'The "block_index" exceed the max index.', {}))
            return
        # 情况6： block_index
        if block_index < 0:
            logger.error(f'<-- The "block_index" should >= 0.')
            connection_socket.send(
                make_response_packet(OP_UPLOAD, 410, TYPE_FILE, f'The "block_index" should >= 0.', {}))
            return
        # 情况7：block_size发生错误
        if block_index == total_block - 1 and len(bin_data) != file_size - block_size * block_index:
            logger.error(f'<-- The "block_size" is wrong.')
            connection_socket.send(
                make_response_packet(OP_UPLOAD, 406, TYPE_FILE, f'The "block_size" is wrong1.', {}))
            return
        # 情况8：block_size的另一种错误
        if block_index != total_block - 1 and len(bin_data) != block_size:
            logger.error(f'<-- The "block_size" is wrong.')
            connection_socket.send(
                make_response_packet(OP_UPLOAD, 406, TYPE_FILE, f'The "block_size" is wrong2.', {}))
            return

        # 情况9：正常的操作
        # 读写模式打开文件
        with open(file_path, 'rb+') as fid:
            fid.seek(block_size * block_index)
            fid.write(bin_data)
        # 以追加模式打开log文件，每一行一个对应的block_index,如果不存在对应文件的话会创建一个对应的文件
        with open(file_path + '.log', 'a') as fid:
            fid.write(f'{block_index}\n')
        fid = open(file_path + '.log', 'r')
        lines = fid.readlines()
        fid.close()
        rval = {
            FIELD_KEY: json_data[FIELD_KEY],
            FIELD_BLOCK_INDEX: block_index
        }
        # 检查是否所有块都上传完毕（每一次上传都会有一个index，这样当所有的块都上传之后，行数就会等于total_block）
        # ⚠️：这样设置tmp的目的就是可以先有一层检查，观察数据是否完整，以及相关的一些数据是否正确，然后再转移到file文件中
        if len(set(lines)) == total_block:
            md5 = getfile_md5(file_path)
            # 将tmp中的文件内容转换为md5的形式，体现在rval字典中
            rval[FIELD_MD5] = md5
            # 在确认了tmp的完整之后，就可以删除file_path.log这个文件了，然后将tmp文件中的内容转移到file文件中
            os.remove(file_path + '.log')
            shutil.move(file_path, join('file', username, json_data[FIELD_KEY]))
        connection_socket.send(
            make_response_packet(OP_UPLOAD, 200, TYPE_FILE, f'The block {block_index} is uploaded.', rval))
        return

# 如果说操作请求是DOWNLOAD
    if request_operation == OP_DOWNLOAD:
        # 情况1：发送信息中没有key
        if FIELD_KEY not in json_data.keys():
            logger.info(f'--> Download file/block without any key.')
            logger.error(f'<-- Field "key" is missing for FILE block downloading.')
            connection_socket.send(
                make_response_packet(OP_GET, 410, TYPE_FILE, f'Field "key" is missing for FILE downloading.', {}))
            return

        logger.info(f'--> Download file/block of "key" {json_data[FIELD_KEY]}.')
        if os.path.exists(join('file', username, json_data[FIELD_KEY])) is False:
            # 情况2：file中没有，tmp中有，没有上传完全
            if os.path.exists(join('tmp', username, json_data[FIELD_KEY])) is True:
                logger.error(
                    f'<-- The "key" {json_data[FIELD_KEY]} is not completely uploaded. Please upload it first.')
                connection_socket.send(
                    make_response_packet(OP_GET, 404, TYPE_FILE,
                                         f'The "key" {json_data[FIELD_KEY]} is not completely uploaded. '
                                         f'Please upload it first',
                                         {}))
                return
            # 情况3：file和tmp中都没有，那就是直接不存在了
            logger.error(f'<-- The "key" {json_data[FIELD_KEY]} is not existing.')
            connection_socket.send(
                make_response_packet(OP_GET, 404, TYPE_FILE, f'The "key" {json_data[FIELD_KEY]} is not existing.', {}))
            return

        # 情况4：没有index
        if FIELD_BLOCK_INDEX not in json_data.keys():
            logger.error(f'<-- The "block_index" is compulsory.')
            connection_socket.send(
                make_response_packet(OP_GET, 410, TYPE_FILE, f'The "block_index" is compulsory.', {}))
            return
        file_path = join('file', username, json_data[FIELD_KEY])
        file_size = getsize(file_path)
        block_size = MAX_PACKET_SIZE
        total_block = math.ceil(file_size / block_size)
        block_index = json_data[FIELD_BLOCK_INDEX]

        # 情况5：index超过
        if block_index >= total_block:
            logger.error(f'<-- The "block_index" exceed the max index.')
            connection_socket.send(
                make_response_packet(OP_GET, 410, TYPE_FILE, f'The "block_index" exceed the max index.', {}))
            return
        # 情况6：index<0
        if block_index < 0:
            logger.error(f'<-- The "block_index" should >= 0.')
            connection_socket.send(
                make_response_packet(OP_GET, 410, TYPE_FILE, f'The "block_index" should >= 0.', {}))
            return
        # 情况7：正确情况：下载对应block内的数据
        with open(file_path, 'rb') as fid:
            fid.seek(block_size * block_index)
            if block_size * (block_index + 1) < file_size:
                bin_data = fid.read(block_size)
            else:
                bin_data = fid.read(file_size - block_size * block_index)

            rval = {
                FIELD_BLOCK_INDEX: block_index,
                FIELD_KEY: json_data[FIELD_KEY],
                FIELD_SIZE: len(bin_data)
            }
            logger.info(f'<-- Return block {block_index}({len(bin_data)}bytes) of "key" {json_data[FIELD_KEY]} >= 0.')

            connection_socket.send(make_response_packet(OP_DOWNLOAD, 200, TYPE_FILE,
                                                        'An available block.', rval, bin_data))


def STEP_service(connection_socket, addr):
    """
    STEP Protocol service
    :param connection_socket:
    :param addr:
    :return: None
    """
    global logger
    while True:
        # 调用get_tcp_packet函数，将数据转换为json_data,bin_data格式
        json_data, bin_data = get_tcp_packet(connection_socket)
        # 如果json_data是空的，则跳出循环
        json_data: dict
        if json_data is None:
            logger.warning('Connection is closed by client.')
            break

        # ACK for "Three Body". If you never read the book "Three Body",
        # just understand the following part as an Echo function. This part is out of the protocol.
        # This is an Easter egg. Aha, this is a very good book.
        if FIELD_DIRECTION in json_data:
            if json_data[FIELD_DIRECTION] == DIR_EARTH:
                connection_socket.send(
                    make_response_packet('3BODY', 333, 'DANGEROUS', f'DO NOT ANSWER! DO NOT ANSWER! DO NOT ANSWER!', {}))
                continue

        # Check the compulsory fields
        compulsory_fields = [FIELD_OPERATION, FIELD_DIRECTION, FIELD_TYPE]

        check_ok = True
        for _compulsory_fields in compulsory_fields:
            if _compulsory_fields not in list(json_data.keys()):
                connection_socket.send(
                    make_response_packet(OP_ERROR, 400, 'ERROR', f'Compulsory field {_compulsory_fields} is missing.',
                                         {}))
                check_ok = False
                break
        # 如果说是False直接结束这整个while True循环，等待下一次接收信息
        if check_ok is False:
            continue

        request_type = json_data[FIELD_TYPE]
        request_operation = json_data[FIELD_OPERATION]
        request_direction = json_data[FIELD_DIRECTION]

        # 检查操作的方向
        if request_direction != DIR_REQUEST:
            connection_socket.send(
                make_response_packet(OP_ERROR, 407, 'ERROR', f'Wrong direction. Should be "REQUEST"', {}))
            continue

        # 检查操作在范围内
        if request_operation not in [OP_SAVE, OP_DELETE, OP_GET, OP_UPLOAD, OP_DOWNLOAD, OP_BYE, OP_LOGIN]:
            connection_socket.send(
                make_response_packet(OP_ERROR, 408, 'ERROR', f'Operation {request_operation} is not allowed', {}))
            continue

        # 检查请求的类型是三者之一
        if request_type not in [TYPE_FILE, TYPE_DATA, TYPE_AUTH]:
            connection_socket.send(
                make_response_packet(OP_ERROR, 409, 'ERROR', f'Type {request_type} is not allowed', {}))
            continue

        # 如果请求是LOGIN，则检查是否为AUTH类型
        if request_operation == OP_LOGIN:
            if request_type != TYPE_AUTH:
                connection_socket.send(
                    make_response_packet(OP_LOGIN, 409, TYPE_AUTH, f'Type of LOGIN has to be AUTH.', {}))
                continue

            else:
                # 检查FIELD_USERNAME是否为一个关键字
                if FIELD_USERNAME not in json_data.keys():
                    connection_socket.send(
                        make_response_packet(OP_LOGIN, 410, TYPE_AUTH, f'"username" has to be a field for LOGIN', {}))
                    continue

                # 检查是否有密码关键字
                if FIELD_PASSWORD not in json_data.keys():
                    connection_socket.send(
                        make_response_packet(OP_LOGIN, 410, TYPE_AUTH, f'"password" has to be a field for LOGIN', {}))
                    continue

                # Check the username and password
                # json_data中的USER_NAME变换为16进制md5格式之后，应该和password内储存的值相同
                if hashlib.md5(json_data[FIELD_USERNAME].encode()).hexdigest().lower() != json_data['password'].lower():
                    connection_socket.send(
                        make_response_packet(OP_LOGIN, 401, TYPE_AUTH, f'"Password error for login.', {}))
                    continue
                else:
                    # Login successful
                    # 得到一个以login加上current time命名的文件名
                    user_str = f'{json_data[FIELD_USERNAME].replace(".", "_")}.' \
                               f'{get_time_based_filename("login")}'
                    md5_auth_str = hashlib.md5(f'{user_str}kjh20)*(1'.encode()).hexdigest()
                    # 这个发送的token在该账号之后的其他操作里是需要包含的
                    connection_socket.send(
                        make_response_packet(OP_LOGIN, 200, TYPE_AUTH, f'Login successfully', {
                            FIELD_TOKEN: base64.b64encode(f'{user_str}.{md5_auth_str}'.encode()).decode()
                        }))
                    continue

        # If the operation is not LOGIN, check token
        if FIELD_TOKEN not in json_data.keys():
            connection_socket.send(
                make_response_packet(request_operation, 403, TYPE_AUTH, f'No token.', {}))
            continue

        token = json_data[FIELD_TOKEN]
        token = base64.b64decode(token).decode()
        token: str

        # 检查token格式，因为有3个'.'所以应该要被其分割为四个部分
        if len(token.split('.')) != 4:
            connection_socket.send(
                make_response_packet(request_operation, 403, TYPE_AUTH, f'Token format is wrong.', {}))
            continue

        user_str = ".".join(token.split('.')[:3])
        md5_auth_str = token.split('.')[3]

        # 检查前后的变换是否正确
        if hashlib.md5(f'{user_str}kjh20)*(1'.encode()).hexdigest().lower() != md5_auth_str.lower():
            connection_socket.send(
                make_response_packet(request_operation, 403, TYPE_AUTH, f'Token is wrong.', {}))
            continue

        username = token.split('.')[0]

        # 创建三个库：data file 和tmp，以及对应的二级分类都是username
        os.makedirs(join('data', username), exist_ok=True)
        os.makedirs(join('file', username), exist_ok=True)
        os.makedirs(join('tmp', username), exist_ok=True)

        if request_type == TYPE_DATA:
            data_process(username, request_operation, json_data, connection_socket)
            continue

        if request_type == TYPE_FILE:
            file_process(username, request_operation, json_data, bin_data, connection_socket)
            continue

    connection_socket.close()
    logger.info(f'Connection close. {addr}')


def Tcp_Listener(server_port, server_ip):
    """
    TCP listener: liston to a port and assign TCP sub connections using new threads
    :param server_ip
    :param server_port
    :return: None
    """
    global logger
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind((server_ip, int(server_port)))
    server_socket.listen(5)  # Start listening for incoming connections
    logger.info('Server is ready!')
    logger.info(
        f'Start the TCP service, listing {server_port} on IP {"All available" if server_ip == "" else server_ip}')
    while True:
        try:
            # Accept a new connection and get the connection socket and address
            connection_socket, addr = server_socket.accept()
            logger.info(f'--> New connection from {addr[0]} on {addr[1]}')
            th = Thread(target=STEP_service, args=(connection_socket, addr))
            th.daemon = True
            th.start()
        except Exception as ex:
            logger.error(f'{str(ex)}@{ex.__traceback__.tb_lineno}')


# 主函数
def main():
    global logger
    logger = set_logger('STEP')
    parser = _argparse()
    server_ip = parser.ip
    server_port = parser.port

    os.makedirs('data', exist_ok=True)
    os.makedirs('file', exist_ok=True)

    Tcp_Listener(server_port, server_ip)


    """
    tcp_listener(server_ip, server_port)
    """


if __name__ == '__main__':
    main()
