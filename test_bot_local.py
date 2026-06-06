import sys, traceback

print("1. Starting...", flush=True)

try:
    from daily import Daily, EventHandler, CallClient
    print("2. Imports OK", flush=True)
    
    Daily.init()
    print("3. Daily.init OK", flush=True)
    
    from conversation_bot import AnalysisBot
    print("4. Bot class imported", flush=True)
    
    bot = AnalysisBot("test123")
    print("5. Bot created", flush=True)
    
    bot.call_client = CallClient(event_handler=bot)
    print("6. CallClient created", flush=True)
    
    # Test joining a fake URL to see the error
    print("7. Attempting join (will fail - that's OK)...", flush=True)
    bot.call_client.join("https://tavus.daily.co/fake-room-test")
    
    import time
    time.sleep(3)
    print("8. Waited 3 seconds", flush=True)
    print(f"9. bot.running = {bot.running}", flush=True)
    
except Exception as e:
    print(f"ERROR at some step:", flush=True)
    traceback.print_exc()
    
print("10. Done", flush=True)
