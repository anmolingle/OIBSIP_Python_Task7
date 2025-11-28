## 🛡️ SecureChat v2 (Python/Flask-SocketIO)

This project is a simple, real-time chat application built using **Python** (Flask and Flask-SocketIO) and a minimalist **Tailwind CSS/JavaScript** frontend. It simulates an "End-to-End Encrypted" chat experience using a basic XOR cipher combined with Base64 encoding.

### ✨ Features

  * **Real-Time Messaging:** Uses **Flask-SocketIO** for bi-directional, low-latency communication.
  * **Multiple Rooms:** Supports three persistent chat rooms: `general`, `tech`, and `random`.
  * **Simulated E2EE:** Messages can be sent in an "Encrypted" mode using a simple client-side XOR + Base64 pseudo-cipher.
  * **Message History:** Stores the last 50 messages per room in an in-memory dictionary.
  * **Modern UI:** A clean, single-page application (SPA) style interface built with **Tailwind CSS**.

### ⚙️ Prerequisites

  * Python 3.x
  * `pip` (Python package installer)

### 🚀 Getting Started

Follow these steps to set up and run the application locally.

#### 1\. Setup Environment

First, create a virtual environment and activate it:

```bash
# Create a virtual environment
python -m venv venv

# Activate the environment (Linux/macOS)
source venv/bin/activate

# Activate the environment (Windows)
.\venv\Scripts\activate
```

#### 2\. Install Dependencies

Install the required Python packages:

```bash
pip install Flask Flask-SocketIO
```

#### 3\. Run the Application

The application is entirely contained within the `Chat_Application.py` file. Run it directly:

```bash
python Chat_Application.py
```

#### 4\. Access the Chat

Open your web browser and navigate to the printed URL:

```
Starting Python SecureChat on http://127.0.0.1:5000
```

-----

### 🔑 Security & Architecture Notes

#### End-to-End Encryption (E2EE) Simulation

The application implements the pseudo-encryption logic entirely on the **client-side (JavaScript)** using the `pseudoEncrypt` and `pseudoDecrypt` functions.

  * **Client-Side Cipher:** A simple XOR operation with a fixed key (`123`) is applied to the message bytes, which are then Base64 encoded for transmission.
  * **Server Role:** The Python server simply receives the payload (encrypted or plain), adds a server timestamp, stores it, and **broadcasts the exact payload** to other clients in the room. The server **never decrypts** the message.
  * **Key Management:** For this simulation, the key (`123`) is hardcoded in the client-side JavaScript. In a real application, a robust key exchange mechanism (like Diffie-Hellman) would be required.

#### Data Storage

The application uses a simple Python dictionary, `DATA_STORE`, to hold chat messages in memory:

```python
DATA_STORE = {
    'general': [],
    'tech': [],
    'random': []
}
```

**⚠️ Important:** This in-memory storage means **all chat history will be lost** when the server is stopped. For a production-ready application, replace this with a persistent database (e.g., PostgreSQL, SQLite, or a NoSQL database like MongoDB).

### 🛠️ Key Files

| File Name | Description |
| :--- | :--- |
| `Chat_Application.py` | Contains the entire Flask-SocketIO backend logic, the in-memory data store, and the full HTML/JS frontend template. |
