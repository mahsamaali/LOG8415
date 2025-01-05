# LOG8415

## MySQL Cluster Management and Proxy Implementation

This project demonstrates the implementation of a MySQL cluster with a proxy pattern for managing database routing and a gatekeeper-trusted host pattern for secure client communication. The setup automates AWS resource deployment, MySQL configuration, and benchmarking using Python and Docker.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [Security Measures](#security-measures)
- [Benchmarking](#benchmarking)
- [Cleanup](#cleanup)
- [License](#license)

## Overview
The project consists of:
1. A MySQL cluster with one manager and two worker nodes.
2. A proxy instance for database query routing and load balancing.
3. A trusted host to forward validated requests to the proxy.
4. A gatekeeper to validate client requests before forwarding them to the trusted host.

## Features
- **Automated Deployment**: Use `main.py` to automate AWS resource creation and configuration.
- **Proxy Pattern**: Routes database queries with direct, random, and customized strategies.
- **Gatekeeper-Trusted Host Pattern**: Adds an extra security layer for client-server communication.
- **Benchmarking**: Evaluates cluster performance with read and write operations.

## Prerequisites
- Python 3.8+
- AWS CLI configured with programmatic access.
- Required Python libraries: `boto3`, `flask`, `pymysql`.

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/mahsamaali/LOG8415
   cd LOG8415
2. **Install Required Libraries**:
  ```bash
pip install requirements.txt
 ```
3. **Run main.py**:
    ```bash
    python /code/main.py
    ```
   
