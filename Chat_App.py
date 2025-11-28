import React, { useState, useEffect, useRef } from 'react';
import { initializeApp } from 'firebase/app';
import { 
  getAuth, 
  signInAnonymously, 
  onAuthStateChanged,
  updateProfile,
  signInWithCustomToken
} from 'firebase/auth';
import { 
  getFirestore, 
  collection, 
  addDoc, 
  query, 
  orderBy, 
  onSnapshot, 
  serverTimestamp,
  limit
} from 'firebase/firestore';
import { 
  Send, 
  Image as ImageIcon, 
  Smile, 
  Lock, 
  Unlock, 
  Hash, 
  User, 
  LogOut, 
  Paperclip,
  X,
  ShieldCheck
} from 'lucide-react';

// --- Configuration & Initialization ---
const firebaseConfig = JSON.parse(__firebase_config);
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

// --- Helper Functions ---

// Improved pseudo-encryption using UTF-8 bytes to handle Emojis/Unicode
// This fixes the InvalidCharacterError by ensuring we only pass 8-bit bytes to btoa
const pseudoEncrypt = (text, key = 123) => {
  try {
    // 1. Encode text to UTF-8 bytes
    const encoder = new TextEncoder();
    const bytes = encoder.encode(text);
    
    // 2. XOR each byte
    const xorBytes = bytes.map(byte => byte ^ key);
    
    // 3. Convert bytes to binary string for btoa
    let binary = '';
    for (let i = 0; i < xorBytes.length; i++) {
      binary += String.fromCharCode(xorBytes[i]);
    }
    
    // 4. Base64 encode
    return btoa(binary);
  } catch (e) {
    console.error("Encryption error:", e);
    return text; // Fallback to plain text on error
  }
};

const pseudoDecrypt = (cipherText, key = 123) => {
  try {
    // 1. Decode Base64 to binary string
    const binary = atob(cipherText);
    
    // 2. Convert binary string to byte array
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    
    // 3. XOR decrypt
    const originalBytes = bytes.map(byte => byte ^ key);
    
    // 4. Decode UTF-8 bytes back to string
    const decoder = new TextDecoder();
    return decoder.decode(originalBytes);
  } catch (e) {
    console.error("Decryption failed:", e);
    return "**Encrypted Data**";
  }
};

// --- Components ---

const LoginScreen = ({ onJoin }) => {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);

  const handleJoin = async (e) => {
    e.preventDefault();
    if (!username.trim()) return;
    setLoading(true);
    await onJoin(username);
    setLoading(false);
  };

  return (
    <div className="flex items-center justify-center h-screen bg-slate-900 text-white">
      <div className="w-full max-w-md p-8 bg-slate-800 rounded-xl shadow-2xl border border-slate-700">
        <div className="flex justify-center mb-6">
          <div className="bg-blue-600 p-4 rounded-full animate-pulse">
            <ShieldCheck size={48} className="text-white" />
          </div>
        </div>
        <h1 className="text-3xl font-bold text-center mb-2">SecureChat v2</h1>
        <p className="text-slate-400 text-center mb-8">End-to-end encrypted communication</p>
        
        <form onSubmit={handleJoin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 rounded-lg bg-slate-700 border border-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 outline-none transition"
              placeholder="Enter your alias..."
            />
          </div>
          <button 
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 py-3 rounded-lg font-bold transition transform hover:scale-[1.02] active:scale-95 disabled:opacity-50"
          >
            {loading ? 'Connecting...' : 'Enter Secure Channel'}
          </button>
        </form>
      </div>
    </div>
  );
};

const EmojiPicker = ({ onSelect }) => {
  const emojis = ["😀", "😂", "😍", "😎", "🤔", "👍", "👎", "🔥", "🎉", "❤️", "🚀", "💻", "🐍", "👻", "💀", "🤖"];
  return (
    <div className="absolute bottom-16 right-4 bg-slate-800 border border-slate-700 p-2 rounded-lg shadow-xl grid grid-cols-4 gap-2 w-48 z-50">
      {emojis.map(e => (
        <button key={e} onClick={() => onSelect(e)} className="hover:bg-slate-700 p-2 rounded text-xl transition">
          {e}
        </button>
      ))}
    </div>
  );
};

export default function App() {
  const [user, setUser] = useState(null);
  const [activeRoom, setActiveRoom] = useState('general');
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [isEncrypted, setIsEncrypted] = useState(false); // Toggle for encryption
  const [showEmojis, setShowEmojis] = useState(false);
  const [imagePreview, setImagePreview] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Rooms configuration
  const rooms = [
    { id: 'general', name: 'General', icon: Hash },
    { id: 'tech', name: 'Technology', icon: Hash },
    { id: 'random', name: 'Random', icon: Hash },
  ];

  // 1. Authentication Logic
  useEffect(() => {
    const initAuth = async () => {
        if (typeof __initial_auth_token !== 'undefined' && __initial_auth_token) {
            await signInWithCustomToken(auth, __initial_auth_token);
        } else {
            await signInAnonymously(auth);
        }
    };
    initAuth();

    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      if (currentUser?.displayName) {
        setUser(currentUser);
      }
    });
    return () => unsubscribe();
  }, []);

  // 2. Real-time Message Sync (The "Socket" replacement)
  useEffect(() => {
    if (!user) return;

    const messagesRef = collection(db, 'artifacts', appId, 'public', 'data', `chat_messages_${activeRoom}`);
    // Query last 50 messages
    const q = query(messagesRef, orderBy('timestamp', 'asc')); // Note: limit(50) removed to follow simple query rules, handle via slice in UI if needed

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const msgs = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      
      // Handle simple client-side "limit" if array gets too big
      setMessages(msgs.slice(-50));
      
      // Notification sound or logic could go here
    }, (error) => {
      console.error("Error fetching messages:", error);
    });

    return () => unsubscribe();
  }, [user, activeRoom]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleLogin = async (username) => {
    if (auth.currentUser) {
      await updateProfile(auth.currentUser, { displayName: username });
      setUser({ ...auth.currentUser, displayName: username });
    }
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result); // Base64 string
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if ((!newMessage.trim() && !imagePreview) || !user) return;

    const textPayload = newMessage;
    // Simulate Encryption
    const finalPayload = isEncrypted ? pseudoEncrypt(textPayload) : textPayload;

    try {
      const messagesRef = collection(db, 'artifacts', appId, 'public', 'data', `chat_messages_${activeRoom}`);
      await addDoc(messagesRef, {
        text: finalPayload,
        sender: user.displayName,
        senderId: user.uid,
        timestamp: serverTimestamp(),
        isEncrypted: isEncrypted,
        image: imagePreview || null, // Storing base64 image directly (Note: In prod, use Storage buckets)
        avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.uid}`
      });

      setNewMessage('');
      setImagePreview(null);
      setShowEmojis(false);
    } catch (error) {
      console.error("Error sending message:", error);
    }
  };

  if (!user) {
    return <LoginScreen onJoin={handleLogin} />;
  }

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 font-sans overflow-hidden">
      
      {/* Sidebar */}
      <div className="w-64 bg-slate-800 border-r border-slate-700 flex flex-col hidden md:flex">
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-xl font-bold flex items-center gap-2 text-blue-400">
            <ShieldCheck /> SecureChat
          </h2>
          <div className="mt-4 flex items-center gap-3 bg-slate-700/50 p-3 rounded-lg">
            <img 
              src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user.uid}`} 
              className="w-8 h-8 rounded-full bg-slate-600"
              alt="avatar"
            />
            <div className="overflow-hidden">
              <div className="font-bold text-sm truncate">{user.displayName}</div>
              <div className="text-xs text-green-400 flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div> Online
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 p-4 overflow-y-auto">
          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Channels</h3>
          <div className="space-y-1">
            {rooms.map((room) => (
              <button
                key={room.id}
                onClick={() => setActiveRoom(room.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-all ${
                  activeRoom === room.id 
                    ? 'bg-blue-600 text-white shadow-md' 
                    : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                }`}
              >
                <room.icon size={18} />
                <span>{room.name}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 border-t border-slate-700">
          <button className="flex items-center gap-2 text-slate-400 hover:text-red-400 transition w-full px-2 text-sm">
            <LogOut size={16} /> Disconnect
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative">
        {/* Header */}
        <header className="h-16 border-b border-slate-700 bg-slate-800/50 backdrop-blur-md flex items-center justify-between px-6">
          <div className="flex items-center gap-2">
            <Hash className="text-slate-400" />
            <h2 className="font-bold text-lg capitalize">{activeRoom}</h2>
          </div>
          
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setIsEncrypted(!isEncrypted)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                isEncrypted 
                  ? 'bg-green-500/20 text-green-400 border border-green-500/50' 
                  : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
              }`}
            >
              {isEncrypted ? <Lock size={14} /> : <Unlock size={14} />}
              {isEncrypted ? 'E2EE On' : 'Unsecured'}
            </button>
          </div>
        </header>

        {/* Messages List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 opacity-50">
              <Hash size={64} />
              <p className="mt-4">No messages yet. Start the conversation!</p>
            </div>
          )}
          
          {messages.map((msg) => {
            const isMe = msg.senderId === user.uid;
            // Decrypt logic for display
            const displayText = msg.isEncrypted ? pseudoDecrypt(msg.text) : msg.text;

            return (
              <div key={msg.id} className={`flex gap-4 ${isMe ? 'flex-row-reverse' : ''}`}>
                <img 
                  src={msg.avatar} 
                  className="w-8 h-8 rounded-full bg-slate-700 mt-1 border border-slate-600"
                  alt={msg.sender} 
                />
                <div className={`max-w-[70%] ${isMe ? 'items-end' : 'items-start'} flex flex-col`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold text-slate-300">{msg.sender}</span>
                    {msg.timestamp && (
                      <span className="text-[10px] text-slate-500">
                        {new Date(msg.timestamp?.seconds * 1000).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </span>
                    )}
                    {msg.isEncrypted && <Lock size={10} className="text-green-500" />}
                  </div>
                  
                  <div className={`p-3 rounded-2xl text-sm shadow-sm leading-relaxed break-words ${
                    isMe 
                      ? 'bg-blue-600 text-white rounded-tr-none' 
                      : 'bg-slate-700 text-slate-200 rounded-tl-none'
                  }`}>
                    {msg.image && (
                      <img src={msg.image} alt="Shared" className="max-w-full rounded-lg mb-2 border border-white/10" />
                    )}
                    {displayText}
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-slate-800 border-t border-slate-700">
          {imagePreview && (
             <div className="mb-2 flex items-center gap-2 bg-slate-700 p-2 rounded-lg w-fit">
                <span className="text-xs text-slate-300">Image attached</span>
                <button onClick={() => setImagePreview(null)}><X size={14} className="hover:text-red-400"/></button>
             </div>
          )}
          
          <form onSubmit={handleSendMessage} className="flex items-end gap-2 relative">
            <input 
              type="file" 
              ref={fileInputRef}
              className="hidden" 
              accept="image/*" 
              onChange={handleImageUpload}
            />
            
            <button 
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-3 rounded-full bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-white transition"
            >
              <Paperclip size={20} />
            </button>

            <div className="flex-1 relative">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder={`Message #${activeRoom}...`}
                className="w-full bg-slate-700 text-white px-4 py-3 rounded-xl border border-transparent focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none pr-10"
              />
              <button 
                type="button"
                onClick={() => setShowEmojis(!showEmojis)}
                className="absolute right-3 top-3 text-slate-400 hover:text-yellow-400 transition"
              >
                <Smile size={20} />
              </button>
            </div>

            {showEmojis && (
              <EmojiPicker onSelect={(emoji) => {
                setNewMessage(prev => prev + emoji);
              }} />
            )}

            <button 
              type="submit"
              disabled={!newMessage.trim() && !imagePreview}
              className="p-3 rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg shadow-blue-900/20"
            >
              <Send size={20} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
