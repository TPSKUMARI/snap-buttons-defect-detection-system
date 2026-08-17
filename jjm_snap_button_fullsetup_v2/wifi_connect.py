import serial
import json
import time
import subprocess
import os
import sys
import ctypes

# ===========================
# SERIAL PORT CONFIGURATION
# ===========================
SERIAL_PORT = "COM3"     # <-- Change to your ESP32 port
BAUD_RATE = 115200
CREDENTIALS_FILE = "wifi_credentials.json"
CONNECTION_TIMEOUT = 10  # seconds to wait for WiFi connection

# ===================================
# WINDOWS WIFI CONNECT FUNCTIONS
# ===================================

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_wifi_interface():
    output = subprocess.check_output("netsh wlan show interfaces", shell=True, encoding="utf-8")
    for line in output.splitlines():
        if "Name" in line:
            return line.split(":", 1)[1].strip()
    return "Wi-Fi"

def profile_exists(ssid):
    profiles = subprocess.check_output("netsh wlan show profiles", shell=True, encoding="utf-8")
    return ssid in profiles

def is_connected():
    """Check if currently connected to WiFi"""
    try:
        output = subprocess.check_output("netsh wlan show interfaces", shell=True, encoding="utf-8")
        return "State" in output and "connected" in output.lower()
    except:
        return False

def get_available_networks():
    """Get list of available WiFi networks"""
    try:
        output = subprocess.check_output("netsh wlan show networks", shell=True, encoding="utf-8")
        networks = []
        for line in output.splitlines():
            if "SSID" in line and "BSSID" not in line:
                ssid = line.split(":", 1)[1].strip()
                if ssid:
                    networks.append(ssid)
        return networks
    except:
        return []

def create_profile(ssid, password, interface):
    profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""

    with open("wifi_profile.xml", "w") as f:
        f.write(profile_xml)

    os.system(f'netsh wlan add profile filename="wifi_profile.xml" interface="{interface}"')

def connect(ssid, interface):
    os.system(f'netsh wlan connect name="{ssid}" interface="{interface}"')

def wait_for_connection(timeout=10):
    """Wait for WiFi connection with timeout"""
    print(f"Waiting up to {timeout} seconds for connection...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if is_connected():
            print("✔ Successfully connected to WiFi!")
            return True
        time.sleep(1)
        print(".", end="", flush=True)
    
    print("\n✖ Connection timeout - could not connect")
    return False

def load_saved_credentials():
    """Load previously saved WiFi credentials"""
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def try_auto_connect():
    """Try to connect to previously saved WiFi"""
    credentials = load_saved_credentials()
    
    if not credentials:
        print("No saved credentials found. Waiting for mobile provisioning...\n")
        return False
    
    ssid = credentials.get("ssid")
    password = credentials.get("password")
    
    if not ssid or not password:
        print("Invalid saved credentials. Waiting for mobile provisioning...\n")
        return False
    
    print(f"Found saved WiFi: {ssid}")
    
    # Check if the network is available
    available = get_available_networks()
    if ssid not in available:
        print(f"Network '{ssid}' not in range. Waiting for mobile provisioning...\n")
        return False
    
    print(f"Network '{ssid}' detected! Attempting to connect...")
    
    interface = get_wifi_interface()
    
    # If profile exists, just connect
    if profile_exists(ssid):
        connect(ssid, interface)  # FIXED: was connect_to_wifi()
        if wait_for_connection(CONNECTION_TIMEOUT):
            return True
        else:
            print("Failed to connect to saved network.\n")
            return False
    
    # Profile doesn't exist - need to create it
    if not is_admin():
        print("Need admin privileges to create profile. Please run as administrator.")
        return False
    
    print("Creating WiFi profile...")
    create_profile(ssid, password, interface)
    connect(ssid, interface)  # FIXED: was connect_to_wifi()
    
    if wait_for_connection(CONNECTION_TIMEOUT):
        return True
    else:
        print("Failed to connect to saved network.\n")
        return False

# ===================================
# MAIN PROGRAM
# ===================================

print("=" * 50)
print("WiFi Auto-Connect Manager")
print("=" * 50)

# First, try to auto-connect to saved WiFi
if try_auto_connect():
    print("\n✔ Auto-connected to saved WiFi successfully!")
    print("Exiting...")
    sys.exit(0)

# Auto-connect failed, listen for new credentials via mobile provisioning
print("=" * 50)
print("Waiting for WiFi credentials from ESP32 (mobile provisioning)...")
print("=" * 50)

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Give ESP32 time to reset
except Exception as e:
    print(f"Error opening serial port: {e}")
    print("Please check the COM port and try again.")
    sys.exit(1)

while True:
    try:
        line = ser.readline().decode().strip()

        if not line:
            continue
        
        print("Received:", line)

        try:
            data = json.loads(line)
            ssid = data.get("ssid")
            password = data.get("password")

            if ssid and password:
                print("\n✔ New WiFi credentials received!")
                print(f"SSID: {ssid}")

                # Save credentials locally
                with open(CREDENTIALS_FILE, "w") as f:
                    json.dump(data, f, indent=4)
                print(f"✔ Saved to {CREDENTIALS_FILE}")

                # Connect to the new WiFi
                interface = get_wifi_interface()

                if profile_exists(ssid):
                    print("Profile exists. Connecting...")
                    connect(ssid, interface)  # FIXED: was connect_to_wifi()
                    if wait_for_connection(CONNECTION_TIMEOUT):
                        print("\n✔ Successfully connected!")
                    break

                # Profile does not exist → need admin
                if not is_admin():
                    print("Admin privileges required. Relaunching...")
                    ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", sys.executable, f'"{__file__}"', None, 1
                    )
                    sys.exit()

                # Running with admin
                print("Running with admin privileges...")
                create_profile(ssid, password, interface)
                connect(ssid, interface)  # FIXED: was connect_to_wifi()
                
                if wait_for_connection(CONNECTION_TIMEOUT):
                    print("\n✔ Successfully connected!")
                else:
                    print("\n✖ Failed to connect. Please check credentials.")
                break

        except json.JSONDecodeError:
            print("Not valid JSON, ignoring...")

    except KeyboardInterrupt:
        print("\nStopped by user.")
        break
    except Exception as e:
        print(f"Error: {e}")
        break

ser.close()
print("\nProgram ended.")