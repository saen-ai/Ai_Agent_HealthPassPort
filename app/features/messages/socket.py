# Messages Feature - Socket.IO Server

import socketio
from typing import Optional, Dict, Any
from app.core.security import decode_token
from app.core.logging import logger
from app.features.auth.models import User
from app.features.patients.models import Patient
from bson import ObjectId


# Create Socket.IO server with ASGI support
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",  # In production, restrict this
    logger=False,
    engineio_logger=False,
)

# Store connected users: {sid: {user_type, user_id, clinic_id, name}}
connected_users: Dict[str, Dict[str, Any]] = {}

# Store which conversations each socket is in: {sid: set of conversation_ids}
socket_conversations: Dict[str, set] = {}


async def authenticate_socket(auth_data: Optional[Dict]) -> Optional[Dict]:
    """
    Authenticate a socket connection using JWT token.
    
    Args:
        auth_data: Authentication data containing token
        
    Returns:
        User info dict or None if authentication fails
    """
    if not auth_data or "token" not in auth_data:
        logger.warning("Socket connection attempted without token")
        return None
    
    token = auth_data["token"]
    payload = decode_token(token)
    
    if not payload:
        logger.warning("Socket connection with invalid token - decode failed")
        return None
    
    # Check if it's a patient or doctor token
    user_type = payload.get("type", "user")
    logger.info(f"Socket auth - user_type: {user_type}, payload keys: {payload.keys()}")
    
    if user_type == "patient":
        # Patient token
        patient_id = payload.get("patient_id")
        if not patient_id:
            logger.warning("Socket auth - patient token missing patient_id")
            return None
        
        patient = await Patient.find_one(Patient.patient_id == patient_id)
        if not patient:
            logger.warning(f"Socket auth - patient not found: {patient_id}")
            return None
        
        if not patient.is_active:
            logger.warning(f"Socket auth - patient inactive: {patient_id}")
            return None
        
        return {
            "user_type": "patient",
            "user_id": patient.patient_id,
            "clinic_id": patient.clinic_id,
            "name": patient.name,
        }
    else:
        # Doctor token
        user_id = payload.get("user_id")
        if not user_id:
            logger.warning("Socket auth - doctor token missing user_id")
            return None
        
        try:
            user = await User.get(ObjectId(user_id))
        except Exception as e:
            logger.warning(f"Socket auth - error getting user: {e}")
            return None
        
        if not user:
            logger.warning(f"Socket auth - user not found: {user_id}")
            return None
        
        return {
            "user_type": "doctor",
            "user_id": str(user.id),
            "clinic_id": user.clinic_id,
            "name": user.name,
        }


@sio.event
async def connect(sid, environ, auth):
    """Handle client connection."""
    logger.info(f"Socket connection attempt: {sid}, auth data: {auth}")
    
    # Authenticate
    try:
        user_info = await authenticate_socket(auth)
    except Exception as e:
        logger.error(f"Socket authentication error: {e}")
        return False
    
    if not user_info:
        logger.warning(f"Socket authentication failed: {sid}")
        return False  # Reject connection
    
    # Store user info
    connected_users[sid] = user_info
    socket_conversations[sid] = set()
    
    logger.info(f"Socket connected: {sid} ({user_info['user_type']}: {user_info['name']})")
    
    # Send connection confirmation
    await sio.emit("connected", {
        "message": "Connected successfully",
        "user_type": user_info["user_type"],
        "user_id": user_info["user_id"],
    }, room=sid)
    
    return True


@sio.event
async def disconnect(sid):
    """Handle client disconnection."""
    user_info = connected_users.pop(sid, None)
    conversations = socket_conversations.pop(sid, set())
    
    if user_info:
        # Leave all conversation rooms
        for conv_id in conversations:
            await sio.leave_room(sid, f"conversation_{conv_id}")
        
        logger.info(f"Socket disconnected: {sid} ({user_info['user_type']}: {user_info['name']})")
    else:
        logger.info(f"Socket disconnected: {sid}")


@sio.event
async def join_conversation(sid, data):
    """
    Join a conversation room.
    
    Args:
        data: {"conversation_id": "..."}
    """
    user_info = connected_users.get(sid)
    if not user_info:
        await sio.emit("error", {"message": "Not authenticated"}, room=sid)
        return
    
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        await sio.emit("error", {"message": "conversation_id required"}, room=sid)
        return
    
    # Join the room
    room = f"conversation_{conversation_id}"
    await sio.enter_room(sid, room)
    socket_conversations[sid].add(conversation_id)
    
    logger.info(f"User {user_info['name']} joined conversation {conversation_id}")
    
    # Notify others in the room
    await sio.emit("user_joined", {
        "user_type": user_info["user_type"],
        "user_name": user_info["name"],
        "conversation_id": conversation_id,
    }, room=room, skip_sid=sid)
    
    await sio.emit("joined", {
        "conversation_id": conversation_id,
        "message": "Joined conversation"
    }, room=sid)


@sio.event
async def leave_conversation(sid, data):
    """
    Leave a conversation room.
    
    Args:
        data: {"conversation_id": "..."}
    """
    user_info = connected_users.get(sid)
    if not user_info:
        return
    
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return
    
    room = f"conversation_{conversation_id}"
    await sio.leave_room(sid, room)
    socket_conversations[sid].discard(conversation_id)
    
    logger.info(f"User {user_info['name']} left conversation {conversation_id}")
    
    # Notify others
    await sio.emit("user_left", {
        "user_type": user_info["user_type"],
        "user_name": user_info["name"],
        "conversation_id": conversation_id,
    }, room=room)


@sio.event
async def typing(sid, data):
    """
    Handle typing indicator.
    
    Args:
        data: {"conversation_id": "...", "is_typing": true/false}
    """
    user_info = connected_users.get(sid)
    if not user_info:
        return
    
    conversation_id = data.get("conversation_id")
    is_typing = data.get("is_typing", True)
    
    if not conversation_id:
        return
    
    room = f"conversation_{conversation_id}"
    
    await sio.emit("user_typing", {
        "conversation_id": conversation_id,
        "user_type": user_info["user_type"],
        "user_name": user_info["name"],
        "is_typing": is_typing,
    }, room=room, skip_sid=sid)


@sio.event
async def mark_read(sid, data):
    """
    Handle marking messages as read.
    
    Args:
        data: {"conversation_id": "..."}
    """
    user_info = connected_users.get(sid)
    if not user_info:
        return
    
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return
    
    room = f"conversation_{conversation_id}"
    
    # Notify others that messages were read
    await sio.emit("messages_read", {
        "conversation_id": conversation_id,
        "read_by": user_info["user_type"],
        "reader_name": user_info["name"],
    }, room=room, skip_sid=sid)


# Helper function to get online status
async def get_conversation_online_users(conversation_id: str) -> Dict[str, bool]:
    """Get which users are online in a conversation."""
    room = f"conversation_{conversation_id}"
    members = sio.manager.get_participants("/", room) if hasattr(sio.manager, 'get_participants') else []
    
    online = {"doctor": False, "patient": False}
    
    for sid in members:
        user_info = connected_users.get(sid)
        if user_info:
            online[user_info["user_type"]] = True
    
    return online


# Create ASGI app for Socket.IO
socket_app = socketio.ASGIApp(sio)

