import csv
import glob
from argparse import ArgumentParser
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def read_csv_files(files):
    test_data = {}
    for file in files:
        with open(file, mode='r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                test_name = row['Test Name']
                if test_name.endswith("_success"):
                    continue
                if test_name not in test_data:
                    test_data[test_name] = []
                test_data[test_name].append({k: float(v) for k, v in row.items() if k != 'Test Name'})
    return test_data


def remove_outliers(data, threshold=3):
    filtered_data = {}
    for fc, values in data.items():
        mean = np.mean(values)
        std_dev = np.std(values)
        z_scores = [(value - mean) / std_dev for value in values]
        filtered_values = [v for v, z in zip(values, z_scores) if abs(z) < threshold]
        filtered_data[fc] = filtered_values
    return filtered_data


def analyze_data(test_data):
    analysis = {}
    for test_name, runs in test_data.items():
        all_fail_chances = runs[0].keys()
        cleaned_runs = {fc: [run[fc] for run in runs] for fc in all_fail_chances}
        cleaned_runs = remove_outliers(cleaned_runs)
        averages = {fc: np.mean(cleaned_runs[fc]) for fc in all_fail_chances}
        std_devs = {fc: np.std(cleaned_runs[fc]) for fc in all_fail_chances}
        analysis[test_name] = {'averages': averages, 'std_devs': std_devs}
    return analysis


def plot_analysis(analysis, ack_threshold, payload_size, file_name, tests):
    for test_name, stats in analysis.items():
        if test_name.endswith("_packets"):
            continue

        fail_chances = list(stats['averages'].keys())
        avg_times = list(stats['averages'].values())
        std_devs = list(stats['std_devs'].values())

        plt.errorbar(fail_chances, avg_times, yerr=std_devs, label=f'{test_name} (avg ± std dev)', fmt='-o', capsize=5)

    plt.xlabel('Fail Chance')
    plt.ylabel('Run Time (s)')
    plt.title(f'Average Run Time and Standard Deviation by Fail Chance\n'
              f'({payload_size} Payload, {tests} Tests, Ack Threshold: {ack_threshold})')
    plt.legend()
    plt.grid(True)

    plt.savefig(file_name)

    plt.show()


def plot_packets(analysis, ack_threshold, payload_size, file_name, tests):
    for test_name, stats in analysis.items():
        if not test_name.endswith("total_packets"):
            continue

        fail_chances = list(stats['averages'].keys())
        avg_packets = list(stats['averages'].values())
        std_devs = list(stats['std_devs'].values())

        test_name = test_name.removesuffix("_total_packets")
        plt.errorbar(fail_chances, avg_packets, yerr=std_devs, label=f'{test_name} (avg ± std dev)', fmt='-o', capsize=5)

    plt.xlabel('Fail Chance')
    plt.ylabel('Packets')
    plt.title(f'Average Packet Count and Standard Deviation by Fail Chance\n'
              f'({payload_size} Payload, {tests} Tests, Ack Threshold: {ack_threshold})')
    plt.legend()
    plt.grid(True)

    plt.savefig(file_name)

    plt.show()


def main(path, ack_threshold, payload_size, output_graph: Path):
    files = glob.glob(str(path / '*.csv'))

    test_data = read_csv_files(files)
    analysis = analyze_data(test_data)

    if not output_graph:
        output_graph = path / f"summary_threshold_{ack_threshold}.png"

    output_graph_packets = output_graph.with_name(f"{output_graph.stem}_packets").with_suffix(".png")

    plot_analysis(analysis, ack_threshold, payload_size, output_graph, len(files))
    plot_packets(analysis, ack_threshold, payload_size, output_graph_packets, len(files))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("ack_threshold")
    parser.add_argument("payload_size")
    parser.add_argument("--output-image", help="With .png suffix")

    args = parser.parse_args()

    main(args.path, args.ack_threshold, args.payload_size, args.output_image)
