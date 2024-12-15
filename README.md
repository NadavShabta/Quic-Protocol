# QUIC Protocol Implementation

## Overview
This project is a custom implementation of the QUIC protocol, designed to ensure reliable communication over unreliable networks. It incorporates advanced features such as packet retransmission, RTT estimation, and congestion control. The project was thoroughly tested and analyzed under varying conditions to evaluate performance and reliability.

## Features
- **Packet Retransmission**: Ensures reliable delivery of packets even in the presence of network failures.
- **Round-Trip Time (RTT) Estimation**: Dynamically calculates RTT to optimize retransmission timeout (RTO).
- **Congestion Control**: Implements mechanisms to manage traffic and avoid network congestion.
- **Performance Analysis**: Includes scripts for visualizing and analyzing performance under different thresholds (1, 3, and 5).
- **Network Simulation**: Simulates unreliable network conditions using dedicated client and server implementations.
- **Custom QUIC Protocol Logic**: Includes the handling of QUIC-specific frames and packet management.

## Reliability Testing
To evaluate and enhance the reliability of the protocol, the following mechanisms were implemented:

- **Single Flow Handling**: All communication occurs over a single flow, simplifying the detection and recovery of lost packets.

- **Packet Loss Detection**:
  - Implemented a mechanism to handle packet loss as described in chapter 5.3 of the QUIC protocol article.
  - Two methods were used to identify packet loss:
    1. **Packet Number Based Method**: Identifies missing packets by analyzing gaps in the sequence of packet numbers.
    2. **Time Based Method**: Detects packet loss when acknowledgments are not received within a calculated timeout period (based on RTT).

- **Failure Recovery**: Installed the failure recovery mechanism described in chapter 5.3, enabling efficient retransmissions.

- **Experimentation**:
  - Conducted three series of experiments to assess the reliability under different conditions. Each series varied the packet and ACK interception probability (`P`):
    - `P = 0.00, 0.01, ..., 0.10`
  - Experiment series:
    1. Using only the **Packet Number Based Method**.
    2. Using only the **Time Based Method**.
    3. Combining both methods.
  - Preliminary experiments were performed to determine relevant parameter values for the mechanisms.

### Results of Reliability Testing
The results of the experiments were as follows:

1. **Packet Number Based Method**:
   - Performed well in networks with low to moderate packet interception probabilities (`P < 0.05`).
   - Struggled to maintain reliability at higher probabilities due to lack of temporal awareness.

2. **Time Based Method**:
   - More resilient at higher interception probabilities (`P > 0.05`), leveraging RTT estimation to detect losses more effectively.
   - However, exhibited higher retransmission rates in low-probability scenarios, leading to increased overhead.

3. **Combined Method**:
   - Achieved the best overall performance across all probability ranges.
   - Minimized both retransmission overhead and packet loss rates by combining the strengths of the two individual methods.
   - Demonstrated consistent reliability even at `P = 0.10`.

## Project Structure
- **src/**: Contains the main source code files.
  - `client.py`, `server.py`, `unreliable_client.py`, `unreliable_server.py`: Core client and server implementations.
  - `plot_data.py`, `summary.py`, `test_reliability.py`: Scripts for analysis and reliability testing.
  - `var_int.py`: Handles variable-length integer encoding for QUIC.
  - **frames/**: Logic for handling QUIC frames.
    - `__init__.py`: Frame initialization logic.
    - `ack.py`: Handles acknowledgment frame operations.
    - `stream.py`: Manages QUIC stream frames.
  - **packets/**: (Optional) Directory for packet utilities if applicable.

- **tests/**: Includes test cases and logs.
  - `tests/`: Directory containing unit and integration tests.
  - `test_reliability.log`: Logs generated during reliability tests.
  - `test_reliability.py`: Reliability testing script.

- **data/**: Experimental results and datasets.
  - `threshold 1 filesize 2`
  - `threshold 3 filesize 2`
  - `threshold 5 filesize 2`

- **docs/**: Documentation and reports.
  - `README.txt`: Original project documentation.
  - `רשתות תקשורת - עבודת גמר.pdf`: Final project report.

- **captures/**: Packet capture files for analyzing network behavior.
  - `test_capture.pcapng`

## Usage
### Prerequisites
- **Python 3.7+**
- **Pipenv** for dependency management

### Setup
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd <repository_name>
   ```

2. Install dependencies:
   ```bash
   pipenv install
   pipenv shell
   ```

### Running the Project
1. Start the unreliable server:
   ```bash
   python src/unreliable_server.py
   ```

2. Start the unreliable client:
   ```bash
   python src/unreliable_client.py
   ```

3. Analyze results using:
   ```bash
   python src/plot_data.py
   ```

### Testing
Run the test suite:
```bash
python -m unittest discover tests
```

## Results
Performance was analyzed for three different thresholds (1, 3, and 5). Results demonstrate that:
- Threshold 1 offers the most stable performance under low-latency conditions.
- Threshold 3 balances reliability and responsiveness, making it ideal for varied network conditions.
- Threshold 5 is less stable but may be suitable for high-latency environments.

## Contributions
- **Protocol Implementation**: Designed and implemented custom QUIC protocol logic.
- **Network Simulation**: Developed tools to simulate and analyze unreliable network environments.
- **Performance Analysis**: Visualized and analyzed data to draw insights on optimal configurations.


## Acknowledgments
- Inspired by RFC 9000 (QUIC: A UDP-Based Multiplexed and Secure Transport) and RFC 9002 (QUIC Loss Detection and Congestion Control).


