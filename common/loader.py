from threading import Thread, Event


class Loader(Thread):
    def __init__(self, name):
        Thread.__init__(self, name=name)

        self._name = name
        self._runevent = Event()
        self._stopevent = Event()

    def log(self, msg):
        print(f'{self._name.rjust(10)}: {msg}')

    def running(self):
        return self._runevent.is_set()

    def stopped(self):
        return self._stopevent.is_set()

    def run(self):
        raise NotImplementedError

    def stop(self, timeout=None):
        raise NotImplementedError
