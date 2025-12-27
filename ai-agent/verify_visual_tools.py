import requests
import json

BASE_URL = "http://localhost:8000/api/chat"

def send_message(msg):
    print(f"\n[USER]: {msg}")
    full_resp = ""
    with requests.post(BASE_URL, json={"message": msg}, stream=True) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    data_str = decoded[6:]
                    if data_str == '[DONE]': break
                    try:
                        data = json.loads(data_str)
                        if 'content' in data:
                            content = data['content']
                            # Check for tool signatures
                            if "[RISK:" in content:
                                print(f"\n[SUCCESS] Risk Tool Triggered! Payload: {content[:100]}...")
                            if "[TIMELINE:" in content:
                                print(f"\n[SUCCESS] Timeline Tool Triggered! Payload: {content[:100]}...")
                            full_resp += content
                    except: pass
    print()
    return full_resp

def test_visual_tools():
    print("--- 1. TESTING RISK GAUGE ---")
    # Should trigger generate_risk_gauge
    send_message("Show me the risk gauge for Zomato.")
    
    print("\n--- 2. TESTING FUTURE TIMELINE ---")
    # Should trigger generate_future_timeline
    send_message("What is the future outlook timeline for Reliance?")

if __name__ == "__main__":
    test_visual_tools()
