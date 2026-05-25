from multiprocessing import Process
import time


def one_process(name):
    for i in range(10):
        print(name, i)
        time.sleep(0.5)
if __name__ == '__main__':
    p = Process(target=one_process, args=('In sub process',))
    p.start()
    time.sleep(0.2)

    for i in range(5):
        print('In main process', i)
        time.sleep(1)

# 等待p程序做完才能继续做，否则主程序和子程序将同时进行
    p.join()
