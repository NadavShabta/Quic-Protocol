import logging
import random
import socket
import sys
from _csv import writer
from argparse import ArgumentParser
from hashlib import md5
from logging import FileHandler
from pathlib import Path
from queue import Queue
from threading import Thread, Event
from time import sleep
from timeit import default_timer

from tqdm import trange
from tqdm.contrib.logging import logging_redirect_tqdm

from quic.frames.stream import StreamFrame
from quic.packets.initial import QuicInitialPacket
from unreliable_client import UnreliableClient
from unreliable_server import UnreliableServer

# Configure console handler for INFO and higher level messages
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Configure file handler for DEBUG and higher level messages
file_handler = FileHandler("test_reliability.log", "w")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Create and configure root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Set root logger level to DEBUG
logger.addHandler(console_handler)  # Add console handler


def log_exception(exc_type, exc_value, exc_traceback):
    """
    Exception handler to log unhandled exceptions.
    """
    logging.exception("Unhandled exception occurred", exc_info=(exc_type, exc_value, exc_traceback))


def run_server(
        server_host,
        server_port,
        fail_chance,
        ack_threshold,
        expected_size: int,
        start_event: Event,
        stop_event: Event,
        result_queue: Queue,
        seed=random.randrange(sys.maxsize),
):
    chunks = {}

    with UnreliableServer(server_host, server_port, fail_chance, ack_threshold, seed=seed) as server:
        logging.info(f"Server started {server_host}:{server_port}")
        start_event.set()

        while not stop_event.is_set():
            try:
                packet, _ = server.receive_packet()
                if hasattr(packet, "frames") and len(packet.frames) > 0:
                    frame: StreamFrame = packet.frames[0]
                    chunks[frame.offset] = frame.data
            except socket.timeout:
                pass
                # logging.warning("Server reached timeout")

        logging.info("Server stopping")

    for offset in range(0, expected_size, 1000):
        if offset not in chunks:
            logging.debug(f"Missing offset {offset}")

    sorted_keys = sorted(chunks.keys())
    server_md5 = md5()
    for key in sorted_keys:
        server_md5.update(chunks[key])

    result_queue.put(server_md5.hexdigest())
    result_queue.put(server.packet_count)


def run_test(
        path: Path,
        start_event: Event,
        stop_event: Event,
        fail_chance: float,
        ack_threshold: int,
        server_host="127.0.0.1",
        server_port=5555,
        ack_detect=True,
        time_detect=True,
        client_seed=random.randrange(sys.maxsize),
        server_seed=random.randrange(sys.maxsize),
):
    start_event.clear()
    stop_event.clear()

    file_size = path.stat().st_size

    result_queue = Queue()

    server_thread = Thread(
        name="Server Thread",
        target=run_server,
        args=(
            server_host,
            server_port,
            fail_chance,
            ack_threshold,
            file_size,
            start_event,
            stop_event,
            result_queue,
            server_seed
        )
    )
    server_thread.start()

    logging.info("Waiting for server")
    start_event.wait()

    start = default_timer()

    with UnreliableClient(
            server_host,
            server_port,
            fail_chance,
            seed=client_seed,
            package_reordering_threshold=ack_threshold,
    ) as client:

        client.ack_detect = ack_detect
        client.time_detect = time_detect

        for frame in client.chunkify_file(path):
            packet = QuicInitialPacket(
                packet_number=client.get_packet_number(),
                version=1,
                dst_conn_id=1,
                src_conn_id=0,
                frames=[frame],
            )

            logging.debug(f"Packet #{packet.packet_number} contains offset {frame.offset}")
            client.send_packet(packet)

            # logging.debug("Number of unACKed packets: %d", len(client.unacked_packets))

            while True:
                try:
                    client.receive_packet()
                except socket.timeout:
                    break

        rtt = client.smoothed_rtt
        logging.info(f"{rtt=}")
        logging.info("Sending lost tail packets")

        while any(filter(lambda packet: len(packet.frames) > 0, client.unacked_packets.values())):
            if client.ack_detect:
                for i in range(client.package_reordering_threshold):
                    probe_packet = QuicInitialPacket(
                        packet_number=client.get_packet_number(),
                        version=1,
                        dst_conn_id=1,
                        src_conn_id=0,
                    )

                    # logging.info("Sending probe packet")
                    client.send_packet(probe_packet)

            if client.time_detect:
                sleep((rtt / 1000000) * client.waiting_time_threshold)
                probe_packet = QuicInitialPacket(
                    packet_number=client.get_packet_number(),
                    version=1,
                    dst_conn_id=1,
                    src_conn_id=0,
                )

                # logging.info("Sending probe packet")
                client.send_packet(probe_packet)
                client.resend_lost_packets()

            while True:
                try:
                    client.receive_packet()
                except socket.timeout:
                    # logging.warning("Reached timeout")
                    break

        end = default_timer()

        logging.info("Finished sending")
        stop_event.set()

    client_hash = md5(path.read_bytes()).hexdigest()
    logging.info("Client hash: %s", client_hash)

    server_hash = result_queue.get()
    logging.info("Server hash: %s", server_hash)

    success = client_hash == server_hash
    if not success:
        logging.error("Hash mismatch!")

    server_packet_count = result_queue.get()

    return end - start, success, client.packet_count, server_packet_count


def main(
        payload_path: Path,
        output_dir: Path,
        stop_event: Event,
        ack_threshold=5,
        client_seed=random.randrange(sys.maxsize),
        server_seed=random.randrange(sys.maxsize),
        show_graph=False,
):
    if client_seed is None:
        client_seed = random.randrange(sys.maxsize)

    if server_seed is None:
        server_seed = random.randrange(sys.maxsize)

    start_event = Event()

    matrix = [
        {
            "ack_detect": True,
            "time_detect": True,
        },
        {
            "ack_detect": False,
            "time_detect": True,
        },
        {
            "ack_detect": True,
            "time_detect": False,
        },
    ]

    results = {
        "ack_time": [],
        "ack_time_success": [],
        "ack_time_client_packets": [],
        "ack_time_server_packets": [],
        "ack_time_total_packets": [],
        "ack": [],
        "ack_success": [],
        "ack_client_packets": [],
        "ack_server_packets": [],
        "ack_total_packets": [],
        "time": [],
        "time_success": [],
        "time_client_packets": [],
        "time_server_packets": [],
        "time_total_packets": [],
    }

    logging.info(f"{client_seed=}")
    logging.info(f"{server_seed=}")
    for fail_chance in (i / 100 for i in range(0, 11)):
        # for fail_chance in (i / 100 for i in range(1, 2)):
        # if fail_chance != 0:
        #     continue

        for kwargs in matrix:
            # if kwargs["time_detect"]:
            #     continue

            test_name = ("ack" if kwargs["ack_detect"] else "") + \
                        ("_" if kwargs["ack_detect"] and kwargs["time_detect"] else "") + \
                        ("time" if kwargs["time_detect"] else "")
            logging.info(f"{fail_chance} {test_name}")

            test_time, success, client_packets, server_packets = run_test(
                payload_path,
                start_event,
                stop_event,
                fail_chance,
                ack_threshold,
                client_seed=client_seed,
                server_seed=server_seed,
                **kwargs,
            )

            results[test_name].append(test_time)
            results[f"{test_name}_success"].append(success)
            results[f"{test_name}_client_packets"].append(client_packets)
            results[f"{test_name}_server_packets"].append(server_packets)
            results[f"{test_name}_total_packets"].append(client_packets + server_packets)

    filename = output_dir / f"{client_seed}_{server_seed}.csv"
    with filename.open("w", newline="") as f:
        csvwriter = writer(f)

        csvwriter.writerow(["Test Name"] + [i / 100 for i in range(0, 11)])

        for test_name, times in results.items():
            csvwriter.writerow([test_name] + times)

    logging.info(filename)
    logging.info(results)

    # if show_graph:
    #     plot_data.main([filename.open()], filename.with_suffix(".png"))


if __name__ == "__main__":
    parser = ArgumentParser(description="Script to test the reliability mechanisms of our QUIC implementation")
    parser.add_argument("payload_path", type=Path, help="Path to payload for test")
    parser.add_argument("output_dir", type=Path, help="Path to directory for result data")
    parser.add_argument("--iterations", type=int, default=(d := 1), help=f"Number of test iterations to run (Default: {d})")
    parser.add_argument("--ack-threshold", type=int, default=(d := 3), help=f"ACK threshold to use (Default: {d})")
    parser.add_argument("--client-seed", type=int, help="Seed for client. Leave unspecified for random seed")
    parser.add_argument("--server-seed", type=int, help="Seed for server. Leave unspecified for random seed")
    parser.add_argument("--file-logging", action="store_true", default=False, help="Enable logging to file (test_reliability.log)")
    parser.add_argument("--show", action="store_true", default=False, help="Show graph after execution (not implemented)")

    args = parser.parse_args()

    if args.file_logging:
        logger.addHandler(file_handler)

    sys.excepthook = log_exception
    stop_event = Event()
    try:
        with logging_redirect_tqdm():
            for i in trange(args.iterations):
                main(
                    args.payload_path,
                    args.output_dir,
                    stop_event,
                    args.ack_threshold,
                    client_seed=args.client_seed,
                    server_seed=args.server_seed,
                    show_graph=args.show,
                )
    except KeyboardInterrupt:
        stop_event.set()
