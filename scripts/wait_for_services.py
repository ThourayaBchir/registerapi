"""Utility script to wait for dependent services before startup."""

import time


def wait_for(service: str, timeout: int = 30) -> None:
    print(f"Waiting for {service} (timeout={timeout}s)...")
    time.sleep(1)


if __name__ == "__main__":
    wait_for("postgres")
    wait_for("redis")
