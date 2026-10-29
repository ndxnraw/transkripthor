"""A crashed/terminated worker must never strand the parent stop signal."""
import multiprocessing
import os
import threading
import time
import unittest
from ndtranskripthor.application.asr_process import StopSignal


def abrupt_reader(signal, sender):
    for _ in range(1000):
        signal.is_set()
    signal.set()
    sender.send(True)
    os._exit(19)


def waiting_reader(signal, sender):
    sender.send(True)
    while True:
        signal.wait(.01)


class StopSignalTest(unittest.TestCase):
    def test_wait_timeout_and_thread_notification(self):
        signal = StopSignal(multiprocessing.get_context('spawn'))
        self.assertFalse(signal.wait(0))
        self.assertFalse(signal.wait(.02))
        timer = threading.Timer(.03, signal.set)
        timer.start()
        try:
            self.assertTrue(signal.wait(1))
            self.assertTrue(signal.wait(0))
            signal.set()
            self.assertTrue(signal.is_set())
        finally:
            timer.join()

    def test_real_spawn_crash_and_termination_keep_signal_nonblocking(self):
        ctx = multiprocessing.get_context('spawn')
        for target in (abrupt_reader, waiting_reader):
            signal = StopSignal(ctx)
            receiver, sender = ctx.Pipe(False)
            process = ctx.Process(target=target, args=(signal, sender))
            try:
                process.start(); sender.close()
                self.assertTrue(receiver.poll(10))
                self.assertTrue(receiver.recv())
                if target is waiting_reader:
                    process.terminate()
                process.join(5)
                self.assertFalse(process.is_alive())
                if target is abrupt_reader:
                    self.assertEqual(process.exitcode, 19)
                    self.assertTrue(signal.is_set())
                start = time.monotonic()
                signal.set()
                self.assertTrue(signal.wait(.1))
                self.assertLess(time.monotonic()-start, 1)
            finally:
                if process.is_alive():
                    process.terminate(); process.join(2)
                receiver.close(); sender.close()
