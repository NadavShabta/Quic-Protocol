import csv
from argparse import ArgumentParser, FileType
from pathlib import Path

import matplotlib.pyplot as plt


def load_data(file):
    data = {}
    reader = csv.DictReader(file)

    row: dict[str, str]
    for row in reader:
        test_name = row.pop("Test Name")
        if not test_name.endswith("_success"):
            data[test_name] = {float(k): float(v) for k, v in row.items()}
        else:
            data[test_name] = {float(k): True if v == "True" else False for k, v in row.items()}
    return data


def plot_data(data, file_name, payload_size, ack_threshold, show=False):
    plt.figure(figsize=(10, 6))
    for test_name, test_data in data.items():
        if not test_name.endswith("_success") and not test_name.endswith("_packets"):
            fail_chances = list(test_data.keys())
            times = list(test_data.values())
            plt.plot(fail_chances, times, label=test_name)
        else:
            for fail_chance, success in test_data.items():
                if not success:
                    plt.plot(
                        fail_chance,
                        data[test_name.removesuffix("_success")][fail_chance],
                        marker="x",
                        linestyle="-"
                    )

    plt.xlabel("Fail Chance")
    plt.ylabel("Time")
    plt.title("Test Times at Different Fail Chances\n"
              f'({payload_size} Payload, Ack Threshold: {ack_threshold})')
    plt.legend()
    # Set x-axis ticks at intervals of 0.01
    plt.xticks([i / 100 for i in range(0, 11)])
    plt.grid(True)

    if file_name:
        plt.savefig(file_name)

    if show:
        plt.show()


def plot_packets(data, file_name, payload_size, ack_threshold, show=False):
    plt.figure(figsize=(10, 6))
    for test_name, test_data in data.items():
        if not test_name.endswith("total_packets"):
            continue

        fail_chances = list(test_data.keys())
        packets = list(test_data.values())
        plt.plot(fail_chances, packets, label=test_name)

    plt.xlabel("Fail Chance")
    plt.ylabel("Packets")
    plt.title("Packet Count at Different Fail Chances\n"
              f'({payload_size} Payload, Ack Threshold: {ack_threshold})')
    plt.legend()
    plt.xticks([i / 100 for i in range(0, 11)])
    plt.grid(True)

    if file_name:
        plt.savefig(str(file_name))

    if show:
        plt.show()


def main(csv_files, output_graph, payload_size, ack_threshold, show=False):
    all_data = {}
    for csv_file in csv_files:
        file_name = Path(csv_file.name).with_suffix("").name
        data = load_data(csv_file)
        for test_name, test_data in data.items():
            key = f"{file_name}.{test_name}"
            all_data[key] = test_data

    plot_data(all_data, output_graph, payload_size, ack_threshold, show=show)

    output_path = Path(output_graph)
    plot_packets(all_data, output_path.with_name(f"{output_path.stem}_packets"), payload_size, ack_threshold, show=show)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("csv", nargs="+", type=FileType())
    parser.add_argument("payload_size")
    parser.add_argument("ack_threshold", type=int)
    parser.add_argument("--output-image", help="With .png suffix")

    args = parser.parse_args()

    main(args.csv, args.output_image, args.payload_size, args.ack_threshold)
