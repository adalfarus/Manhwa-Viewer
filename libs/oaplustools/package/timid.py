from time import time, perf_counter_ns, monotonic_ns
from datetime import timedelta, datetime
from typing import Optional, Type, Union
from timeit import default_timer


class TimidTimer:
    """Uses the timeit.default_timer function to calculate passed time."""
    def __init__(self, start_seconds: Optional[int] = 0,
                 start_now: Optional[bool] = True):
        self.starter = start_seconds
        self.ender = None
        self.timedelta = None

        if start_now:
            self.start()

    def start(self) -> float:
        self.starter = default_timer() + self.starter
        return self.starter

    def end(self, return_end_time: Optional[bool] = False) -> Union[timedelta, float]:
        self.ender = default_timer()
        self.timedelta = timedelta(seconds=self.ender - self.starter)

        if not return_end_time:
            return self.timedelta
        else:
            return self.ender

    def tick(self, return_time: Optional[bool] = False) -> Union[timedelta, float]:
        """Return how much time has passed till the start."""
        if not return_time:
            return timedelta(seconds=default_timer() - self.starter)
        else:
            return default_timer()

    def tock(self, return_time: Optional[bool] = False) -> Union[timedelta, float]:
        """Returns how much time has passed till the last tock."""
        last_time = self.ender or self.starter
        self.ender = default_timer()

        if not return_time:
            return timedelta(seconds=self.ender - last_time)
        else:
            return last_time

    @staticmethod
    def test_delay() -> timedelta:
        return TimidTimer().end()

    @staticmethod
    def test_tock_delay() -> timedelta:
        timer = TimidTimer()
        timer.tock()
        return timer.end()

    @staticmethod
    def time() -> float:
        return default_timer()


class TimidTimer2:
    """Uses the time.perf_counter_ns function to calculate passed time."""
    def __init__(self, start_seconds: Optional[int] = 0,
                 start_now: Optional[bool] = True):
        self.starter = start_seconds
        self.ender = None
        self.timedelta = None

        if start_now:
            self.start()

    def start(self) -> int:
        self.starter = perf_counter_ns() + int(self.starter * 1e+9)
        return self.starter

    def end(self, return_end_time: Optional[bool] = False) -> Union[timedelta, int]:
        self.ender = perf_counter_ns()
        self.timedelta = timedelta(microseconds=(self.ender - self.starter) / 1000)

        if not return_end_time:
            return self.timedelta
        else:
            return self.ender

    def tick(self, return_time: Optional[bool] = False) -> Union[timedelta, int]:
        """Return how much time has passed till the start."""
        if not return_time:
            return timedelta(microseconds=(perf_counter_ns() - self.starter) / 1000)
        else:
            return perf_counter_ns()

    def tock(self, return_time: Optional[bool] = False) -> Union[timedelta, int]:
        """Returns how much time has passed till the last tock."""
        last_time = self.ender or self.starter
        self.ender = perf_counter_ns()

        if not return_time:
            return timedelta(microseconds=(self.ender - last_time) / 1000)
        else:
            return last_time

    @staticmethod
    def test_delay() -> timedelta:
        return TimidTimer2().end()

    @staticmethod
    def test_tock_delay() -> timedelta:
        timer = TimidTimer2()
        timer.tock()
        return timer.end()

    @staticmethod
    def time() -> float:
        return perf_counter_ns() / 1e+9


class NormalTimer:
    """Uses the time.time function to calculate passed time."""
    def __init__(self, start_seconds: Optional[int] = 0,
                 start_now: Optional[bool] = True):
        self.starter = start_seconds
        self.stopper = None
        self.timedelta = None

        if start_now:
            self.start()

    def start(self) -> float:
        self.starter = time() + self.starter
        return self.starter

    def round(self) -> timedelta:
        last_time = self.starter or time()
        self.starter = self.stopper
        self.stopper = time()

        return timedelta(seconds=self.stopper - last_time)

    def stop(self) -> timedelta:
        self.stopper = time()
        return timedelta(seconds=self.stopper - self.starter)

    @staticmethod
    def time() -> datetime:
        return datetime.today()


class LazyTimer:
    """Uses the time.monotonic_ns function to calculate passed time."""
    def __init__(self, start_seconds: Optional[int] = 0,
                 start_now: Optional[bool] = True):
        self.starter = start_seconds
        self.stopper = None
        self.timedelta = None

        if start_now:
            self.start()

    def start(self) -> int:
        self.starter = monotonic_ns() + int(self.starter * 1e+9)
        return self.starter

    def round(self) -> timedelta:
        last_time = self.starter or monotonic_ns()
        self.starter = self.stopper
        self.stopper = monotonic_ns()

        return timedelta(seconds=(self.stopper - last_time) / 1e+9)

    def stop(self) -> timedelta:
        self.stopper = monotonic_ns()
        return timedelta(seconds=(self.stopper - self.starter) / 1e+9)

    @staticmethod
    def time() -> int:
        return int(monotonic_ns() / 1e+9)


# Timer

class TimerOut:
    WEEKS = 0
    DAYS = 1
    HOURS = 2
    MINUTES = 3
    SECONDS = 4
    MILISEC = 5
    MICROSEC = 6


class TimeDisplay:
    def __init__(self, td: timedelta, out: TimerOut):
        raise NotImplementedError("This class isn't implemented yet, please visit back in version 1.5 or later.")
        self.microsec = td.microseconds
        self.seconds = td.seconds
        self.days = td.days

        self.repr = ""

    def __repr__(self):
        return "TimerDisplay(\
                \
                )"


class Timer:
    def __init__(self, output_target: Optional[TimerOut] = TimerOut.SECONDS,
                 start_now: Optional[bool] = True):
        raise NotImplementedError("This class isn't implemented yet, please visit back in version 1.5 or later.")
        self.output_target = output_target

        self.start_t = None
        self.stop_t = None
        self.t_d = None

        if start_now:
            self.start()

    @staticmethod
    def test_delay() -> timedelta:
        return TimidTimer().end()

    def start(self) -> float:
        return
        self.start_t = timer()
        return self.start_t

    @staticmethod
    def time() -> float:
        return
        return timer()

    def tick(self, return_time: Optional[bool] = False) -> Union[timedelta, float]:
        return
        """Return how much time has passed till the start."""
        if not return_time:
            return timedelta(seconds=timer() - self.start_t)
        else:
            return timer()

    def tock(self, return_time: Optional[bool] = False) -> Union[timedelta, float]:
        return
        """Returns how much time has passed till the last tock."""
        time = self.stop_t or self.start_t
        self.stop_t = time()

        if not return_time:
            return timedelta(seconds=time - self.stop_t)
        else:
            return time

    def end(self, return_end_time: Optional[bool] = False) -> Union[timedelta, float]:
        return
        self.stop_t = timer()
        self.t_d = timedelta(seconds=self.stop_t-self.start_t)

        if not return_end_time:
            return self.t_d
        else:
            return self.stop_t


def local_test():
    try:
        def test_delay(cls: Type[Union[NormalTimer, LazyTimer]]):
            timer = TimidTimer2()
            cls().stop()
            return timer.end() - timedelta(microseconds=1)

        print("TimidTimerDelay", TimidTimer.test_delay())
        print("TimidTimer2Delay", TimidTimer2.test_delay())
        print("All other timers are too inaccurate as to measure them with themselves, \
so we measure them with TimidTimer2 and subtract the average delay.")
        print("NormalTimerDelay", test_delay(NormalTimer))
        print("LazyTimerDelay", test_delay(LazyTimer))

        print("\nTimer Test, using 1 million passes.")
        t_timer = TimidTimer()
        t_timer2 = TimidTimer2()
        n_timer = NormalTimer()
        l_timer = LazyTimer()
        for _ in range(1000000):
            pass
        print("TimidTimer", t_timer.end())
        print("TimidTimer2", t_timer2.end())
        print("NormalTimer", n_timer.stop())
        print("LazyTimer", l_timer.stop())

        print("\nTimer Test, using 1 second sleep.")
        import time as t
        t_timer = TimidTimer()
        t_timer2 = TimidTimer2()
        n_timer = NormalTimer()
        l_timer = LazyTimer()
        t.sleep(1)
        print("TimidTimer", t_timer.end())
        print("TimidTimer2", t_timer2.end())
        print("NormalTimer", n_timer.stop())
        print("LazyTimer", l_timer.stop())

        print("\nTimidTimer delay test 2")
        timid_t = TimidTimer()
        for i in range(10):
            print(timid_t.tock())

        print("\nTimidTimer2 delay test 2")
        timid_t2 = TimidTimer2()
        for i in range(10):
            print(timid_t2.tock())

        print("\nNormalTimer delay test 2")
        normal_t = NormalTimer()
        for i in range(10):
            print(normal_t.round())

        print("\nLazyTimer delay test 2")
        lazy_t = LazyTimer()
        for i in range(10):
            print(lazy_t.round())
    except Exception as e:
        print(f"Exception occurred {e}.")
        return False
    print("Test completed successfully.")
    return True


if __name__ == "__main__":
    local_test()
