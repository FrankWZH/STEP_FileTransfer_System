
<div align="center">

# 📁 STEP FileTransfer System

### A Reliable File Transfer & Processing Pipeline

Built with **Python**, **Socket Programming**, and **Multithreading**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/Socket-Programming-4A90E2?style=for-the-badge&logo=socket.io&logoColor=white">
  <img src="https://img.shields.io/badge/Multithreading-Concurrent-32CD32?style=for-the-badge">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge">
</p>

<p align="center">
  <b>Client-Server • Concurrent Transfers • Error Handling • Data Integrity</b>
</p>

</div>

---

# 📖 Overview

STEP FileTransfer System is a **client-server file transfer application** built with Python's socket programming and multithreading. It enables reliable file transmission between multiple clients and a central server, with support for concurrent connections and basic error recovery.

This project demonstrates core networking concepts including TCP/IP communication, thread management, and file I/O operations in a practical file-sharing context.

---

# ✨ Features

## Core Capabilities

- **Client-Server Architecture** – Centralized file transfer management
- **Concurrent Connections** – Handle multiple clients simultaneously using multithreading
- **Reliable Transfer** – TCP-based transmission with checksum verification
- **File Integrity** – Basic validation to ensure complete file delivery
- **Progress Tracking** – Real-time transfer status (implementation dependent)

---

# 🛠 Tech Stack

| Category | Technologies |
|----------|--------------|
| Language | Python 3.x |
| Networking | Socket Programming (TCP/IP) |
| Concurrency | threading, queue |
| File Handling | os, hashlib (for integrity) |
| Development | PyCharm, venv |

---

# 📂 Project Structure

```text
STEP_FileTransfer_System/
├── CW1/                      # Coursework 1 deliverables
├── venv/                     # Python virtual environment
├── .idea/                    # IDE configuration
├── main.py                   # Main entry point (client/server launcher)
├── Practice_scientific1.py   # Utility/helper functions
├── requirements.txt          # Python dependencies
└── .DS_Store                 # System file (ignored)
````

> **Note:** The actual client and server implementation details are contained within `CW1/` and `main.py`. The structure may expand as the project evolves.

---

# ⚙️ Installation

## 1️⃣ Clone the Repository

```bash
git clone https://github.com/FrankWZH/STEP_FileTransfer_System.git
cd STEP_FileTransfer_System
```

## 2️⃣ Set Up Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
```

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

## 4️⃣ Run the Application

Start the server:

```bash
python main.py --mode server
```

Start a client (in a new terminal):

```bash
python main.py --mode client --server localhost --port 8080
```

---

# 🚀 Usage Example

## Basic File Transfer Flow

1. Launch Server – Server starts listening on specified port
2. Connect Client – Client establishes TCP connection
3. Request Transfer – Client sends filename and metadata
4. File Transmission – Server streams file in chunks
5. Verification – Client checks file integrity
6. Completion – Both sides close connection cleanly

## Typical Commands

```bash
GET file_list
DOWNLOAD filename.txt
UPLOAD localfile.txt
QUIT
```

---

# 📈 Performance Considerations

| Aspect         | Approach                                |
| -------------- | --------------------------------------- |
| Concurrency    | Thread-per-client model                 |
| Buffer Size    | Chunk-based transfer (e.g., 8192 bytes) |
| Error Handling | Timeout + exception handling            |
| Scalability    | Suitable for small–medium scale systems |

---

# 🔧 Future Improvements

* [ ] Resume capability for interrupted transfers
* [ ] TLS/SSL encryption
* [ ] GUI interface (desktop/web)
* [ ] Parallel chunk transfer
* [ ] Authentication system
* [ ] Logging and monitoring

---

# 🙏 Acknowledgements

This project was developed for learning purposes, focusing on:

* Python socket programming fundamentals
* Multithreading and concurrency
* Reliable file transfer design

---

# 👥 Author

| Name      | GitHub    | Role           |
| --------- | --------- | -------------- |
| Zihang Wu | [@FrankWZH](https://github.com/FrankWZH) | Sole Developer |


---

# ⚠️ Disclaimer

This project is for **educational purposes only** and is not intended for production use in secure or high-availability environments.

---

# 📜 License

MIT License (to be added)

```
```
