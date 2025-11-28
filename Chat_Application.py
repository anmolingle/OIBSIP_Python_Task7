import base64
from datetime import datetime
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, join_room, leave_room, emit

# --- Configuration ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- In-Memory Database (Replaces Firestore) ---
# In a real app, you would use SQLite or PostgreSQL
DATA_STORE = {
    'general': [],
    'tech': [],
    'random': []
}

# --- Helper Functions (Python Version of the Encryption) ---
# Note: In this architecture, we perform encryption on the CLIENT (JS)
# to maintain "End-to-End" security simulation. However, here is 
# how you would do the same logic in Python if you wanted server-side processing.
def python_pseudo_encrypt(text, key=123):
    try:
        # 1. Encode to UTF-8 bytes
        text_bytes = text.encode('utf-8')
        # 2. XOR each byte
        xor_bytes = bytearray(b ^ key for b in text_bytes)
        # 3. Base64 Encode
        return base64.b64encode(xor_bytes).decode('ascii')
    except Exception as e:
        print(f"Encryption error: {e}")
        return text

# --- Routes ---
@app.route('/')
def index():
    # We render the single-page UI defined at the bottom of this file
    return render_template_string(HTML_TEMPLATE)

# --- Socket Events (Real-time Logic) ---

@socketio.on('join')
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    
    # Send existing messages for this room to the user who just joined
    emit('load_history', DATA_STORE[room], to=request.sid)
    
    # Notify others
    emit('status', {'msg': f'{username} has entered the room.'}, room=room)

@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    emit('status', {'msg': f'{username} has left the room.'}, room=room)

@socketio.on('send_message')
def handle_message(data):
    """
    Receives message from client. 
    Data includes: {text, sender, room, isEncrypted, timestamp}
    """
    room = data['room']
    
    # Add server-side timestamp
    data['timestamp'] = datetime.now().strftime('%I:%M %p')
    
    # Store in memory
    DATA_STORE[room].append(data)
    
    # Keep only last 50 messages (Cleanup)
    if len(DATA_STORE[room]) > 50:
        DATA_STORE[room].pop(0)

    # Broadcast to everyone in the room
    emit('receive_message', data, room=room)

# --- The Frontend Template (Replicates the React UI) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SecureChat v2 (Python)</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        /* Custom scrollbar to match the React app */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #1e293b; }
        ::-webkit-scrollbar-thumb { background: #475569; border-radius: 4px; }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 font-sans h-screen flex overflow-hidden">

    <div id="login-screen" class="fixed inset-0 z-50 bg-slate-900 flex items-center justify-center">
        <div class="w-full max-w-md p-8 bg-slate-800 rounded-xl shadow-2xl border border-slate-700">
            <div class="flex justify-center mb-6">
                <div class="bg-blue-600 p-4 rounded-full animate-pulse">
                    <i data-lucide="shield-check" class="text-white w-12 h-12"></i>
                </div>
            </div>
            <h1 class="text-3xl font-bold text-center mb-2">SecureChat (Python)</h1>
            <p class="text-slate-400 text-center mb-8">End-to-end encrypted communication</p>
            <form id="login-form" class="space-y-4">
                <input type="text" id="username-input" placeholder="Enter your alias..." 
                    class="w-full px-4 py-3 rounded-lg bg-slate-700 border border-slate-600 focus:border-blue-500 outline-none transition" required>
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-lg font-bold transition transform hover:scale-[1.02]">
                    Enter Secure Channel
                </button>
            </form>
        </div>
    </div>

    <div id="app-container" class="flex w-full hidden">
        
        <div class="w-64 bg-slate-800 border-r border-slate-700 flex flex-col hidden md:flex">
            <div class="p-6 border-b border-slate-700">
                <h2 class="text-xl font-bold flex items-center gap-2 text-blue-400">
                    <i data-lucide="shield-check"></i> SecureChat
                </h2>
                <div class="mt-4 flex items-center gap-3 bg-slate-700/50 p-3 rounded-lg">
                    <img id="user-avatar" src="" class="w-8 h-8 rounded-full bg-slate-600">
                    <div>
                        <div id="display-username" class="font-bold text-sm truncate">User</div>
                        <div class="text-xs text-green-400 flex items-center gap-1">● Online</div>
                    </div>
                </div>
            </div>
            <div class="flex-1 p-4">
                <h3 class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Channels</h3>
                <div class="space-y-1" id="room-list">
                    </div>
            </div>
        </div>

        <div class="flex-1 flex flex-col relative">
            <header class="h-16 border-b border-slate-700 bg-slate-800/50 backdrop-blur-md flex items-center justify-between px-6">
                <div class="flex items-center gap-2">
                    <i data-lucide="hash" class="text-slate-400"></i>
                    <h2 id="current-room-name" class="font-bold text-lg capitalize">general</h2>
                </div>
                <button id="encryption-toggle" class="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all bg-slate-700 text-slate-400">
                    <i data-lucide="unlock" id="lock-icon" class="w-4 h-4"></i>
                    <span id="lock-text">Unsecured</span>
                </button>
            </header>

            <div id="messages-container" class="flex-1 overflow-y-auto p-6 space-y-6">
                </div>

            <div class="p-4 bg-slate-800 border-t border-slate-700">
                <form id="message-form" class="flex items-center gap-2">
                    <input type="text" id="message-input" placeholder="Message #general..." 
                        class="flex-1 bg-slate-700 text-white px-4 py-3 rounded-xl border border-transparent focus:border-blue-500 outline-none">
                    <button type="submit" class="p-3 rounded-xl bg-blue-600 text-white hover:bg-blue-700 transition shadow-lg">
                        <i data-lucide="send" class="w-5 h-5"></i>
                    </button>
                </form>
            </div>
        </div>
    </div>

    <script>
        // --- CLIENT SIDE LOGIC ---
        const socket = io();
        let currentUser = null;
        let activeRoom = 'general';
        let isEncrypted = false;
        const rooms = ['general', 'tech', 'random'];

        // --- Crypto Helper Functions (Matching the React Logic) ---
        const pseudoEncrypt = (text, key = 123) => {
            try {
                const encoder = new TextEncoder();
                const bytes = encoder.encode(text);
                const xorBytes = bytes.map(byte => byte ^ key);
                let binary = '';
                for (let i = 0; i < xorBytes.length; i++) binary += String.fromCharCode(xorBytes[i]);
                return btoa(binary);
            } catch (e) { return text; }
        };

        const pseudoDecrypt = (cipherText, key = 123) => {
            try {
                const binary = atob(cipherText);
                const bytes = new Uint8Array(binary.length);
                for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
                const originalBytes = bytes.map(byte => byte ^ key);
                const decoder = new TextDecoder();
                return decoder.decode(originalBytes);
            } catch (e) { return "**Encrypted Data**"; }
        };

        // --- UI Logic ---
        lucide.createIcons();

        // Login
        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const username = document.getElementById('username-input').value.trim();
            if(!username) return;

            currentUser = username;
            document.getElementById('login-screen').classList.add('hidden');
            document.getElementById('app-container').classList.remove('hidden');
            document.getElementById('app-container').classList.add('flex'); // Enable flex layout
            
            // Setup User UI
            document.getElementById('display-username').textContent = currentUser;
            document.getElementById('user-avatar').src = `https://api.dicebear.com/7.x/avataaars/svg?seed=${currentUser}`;
            
            joinRoom('general');
            renderRooms();
        });

        // Room Switching
        function renderRooms() {
            const container = document.getElementById('room-list');
            container.innerHTML = rooms.map(room => `
                <button onclick="joinRoom('${room}')" class="w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all ${activeRoom === room ? 'bg-blue-600 text-white shadow-md' : 'text-slate-400 hover:bg-slate-700'}">
                    <i data-lucide="hash" class="w-4 h-4"></i> ${room.charAt(0).toUpperCase() + room.slice(1)}
                </button>
            `).join('');
            lucide.createIcons();
        }

        function joinRoom(room) {
            if (currentUser) {
                socket.emit('leave', { username: currentUser, room: activeRoom });
                document.getElementById('messages-container').innerHTML = ''; // Clear chat
            }
            activeRoom = room;
            document.getElementById('current-room-name').textContent = room;
            document.getElementById('message-input').placeholder = `Message #${room}...`;
            socket.emit('join', { username: currentUser, room: activeRoom });
            renderRooms();
        }

        // Encryption Toggle
        document.getElementById('encryption-toggle').addEventListener('click', () => {
            isEncrypted = !isEncrypted;
            const btn = document.getElementById('encryption-toggle');
            const icon = document.getElementById('lock-icon');
            const text = document.getElementById('lock-text');

            if(isEncrypted) {
                btn.className = "flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all bg-green-500/20 text-green-400 border border-green-500/50";
                icon.setAttribute('data-lucide', 'lock');
                text.textContent = "E2EE On";
            } else {
                btn.className = "flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all bg-slate-700 text-slate-400 hover:bg-slate-600";
                icon.setAttribute('data-lucide', 'unlock');
                text.textContent = "Unsecured";
            }
            lucide.createIcons();
        });

        // Sending Messages
        document.getElementById('message-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const input = document.getElementById('message-input');
            const text = input.value.trim();
            if(!text) return;

            const finalPayload = isEncrypted ? pseudoEncrypt(text) : text;
            
            socket.emit('send_message', {
                text: finalPayload,
                sender: currentUser,
                room: activeRoom,
                isEncrypted: isEncrypted,
                avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${currentUser}`
            });
            input.value = '';
        });

        // Receiving Messages
        function appendMessage(msg) {
            const container = document.getElementById('messages-container');
            const isMe = msg.sender === currentUser;
            const displayText = msg.isEncrypted ? pseudoDecrypt(msg.text) : msg.text;

            const html = `
                <div class="flex gap-4 ${isMe ? 'flex-row-reverse' : ''}">
                    <img src="${msg.avatar}" class="w-8 h-8 rounded-full bg-slate-700 mt-1 border border-slate-600">
                    <div class="max-w-[70%] flex flex-col ${isMe ? 'items-end' : 'items-start'}">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-xs font-bold text-slate-300">${msg.sender}</span>
                            <span class="text-[10px] text-slate-500">${msg.timestamp || ''}</span>
                            ${msg.isEncrypted ? '<i data-lucide="lock" class="w-3 h-3 text-green-500"></i>' : ''}
                        </div>
                        <div class="p-3 rounded-2xl text-sm shadow-sm leading-relaxed break-words ${isMe ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-slate-700 text-slate-200 rounded-tl-none'}">
                            ${displayText}
                        </div>
                    </div>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', html);
            container.scrollTop = container.scrollHeight;
            lucide.createIcons();
        }

        // Socket Listeners
        socket.on('load_history', (msgs) => {
            msgs.forEach(appendMessage);
        });

        socket.on('receive_message', (msg) => {
            appendMessage(msg);
        });

        socket.on('status', (data) => {
            // Optional: Render system messages like "User joined"
            console.log(data.msg);
        });

    </script>
</body>
</html>
"""

if __name__ == '__main__':
    print("Starting Python SecureChat on http://127.0.0.1:5000")
    socketio.run(app, debug=True)
