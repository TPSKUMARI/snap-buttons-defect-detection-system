# start.py → Your new "double-click to run" file
import subprocess
import sys
import os

def run_wifi_connect():
    wifi_script = os.path.join(os.path.dirname(__file__), "wifi_connect.py")
    print("Running WiFi Auto-Connect first...")
    result = subprocess.call([sys.executable, wifi_script])
    
    if result == 0:
        print("WiFi setup completed successfully!\n")
    else:
        print("WiFi script ended (maybe failed or user closed).")
        input("Press Enter to continue launching the app anyway...")

def run_main_app():
    main_script = os.path.join(os.path.dirname(__file__), "main.py")
    print("Starting Button Detection System...")
    # This replaces the current process with main.py → clean & professional
    os.execvp(sys.executable, [sys.executable, main_script])

if __name__ == "__main__":
    run_wifi_connect()
    run_main_app()   # ← Only runs AFTER WiFi script is 100% done!

    #  C:\Users\idea8\Desktop\jjm\start.py