import kthread, time

@kthread.timeout(1)
def test():
    time.sleep(2)
    print "success"


if __name__ == '__main__':
    test()