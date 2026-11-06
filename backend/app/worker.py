from signal import SIGINT, SIGTERM, signal
from threading import Event


def main() -> None:
    stop = Event()

    def shutdown(_signum: int, _frame: object) -> None:
        stop.set()

    signal(SIGINT, shutdown)
    signal(SIGTERM, shutdown)
    print("Worker ready, job processing coming soon with db queue.", flush=True)
    stop.wait()


if __name__ == "__main__":
    main()
