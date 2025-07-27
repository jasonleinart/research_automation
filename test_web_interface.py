#!/usr/bin/env python3
"""
Test the web interface endpoints to ensure they work correctly.
"""

import asyncio
import json
from fastapi.testclient import TestClient
from src.web.main import app

def test_web_interface():
    """Test the web interface endpoints."""
    client = TestClient(app)
    
    print("🧪 Testing Web Interface Endpoints")
    print("=" * 50)
    
    # Test 1: Chat page loads
    print("\n1️⃣ Testing chat page...")
    response = client.get("/chat")
    if response.status_code == 200:
        print("✅ Chat page loads successfully")
    else:
        print(f"❌ Chat page failed: {response.status_code}")
    
    # Test 2: Get papers API
    print("\n2️⃣ Testing papers API...")
    response = client.get("/api/chat/papers")
    if response.status_code == 200:
        papers = response.json()
        print(f"✅ Papers API works: {len(papers)} papers")
    else:
        print(f"❌ Papers API failed: {response.status_code}")
        return
    
    # Test 3: Get sessions API
    print("\n3️⃣ Testing sessions API...")
    response = client.get("/api/chat/sessions")
    if response.status_code == 200:
        sessions = response.json()
        print(f"✅ Sessions API works: {len(sessions)} sessions")
        
        # Test session history for existing sessions
        if sessions:
            session_id = sessions[0]['session_id']
            print(f"\n4️⃣ Testing session history for {session_id}...")
            response = client.get(f"/api/chat/sessions/{session_id}/history")
            if response.status_code == 200:
                history = response.json()
                print(f"✅ Session history works: {len(history)} messages")
            else:
                print(f"❌ Session history failed: {response.status_code}")
                print(f"   Response: {response.text}")
    else:
        print(f"❌ Sessions API failed: {response.status_code}")
    
    # Test 4: Send message API
    print("\n5️⃣ Testing send message API...")
    if papers:
        test_message = {
            "paper_id": papers[0]['id'],
            "message": "What is this paper about?"
        }
        
        response = client.post("/api/chat/message", json=test_message)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Send message works")
            print(f"   Response: {result['response'][:100]}...")
            print(f"   Confidence: {result['confidence']}")
            print(f"   Session ID: {result['session_id']}")
        else:
            print(f"❌ Send message failed: {response.status_code}")
            print(f"   Response: {response.text}")
    
    print("\n🎯 Web Interface Testing Complete!")

if __name__ == "__main__":
    test_web_interface()