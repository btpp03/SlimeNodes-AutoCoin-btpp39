#!/usr/bin/env python3
"""SlimeNodes Auto Login - Refresh connect.sid via Discord OAuth using SeleniumBase UC mode."""
import os, sys, re, time, json, subprocess

def install_seleniumbase():
    subprocess.run([sys.executable, "-m", "pip", "install", "seleniumbase", "--quiet"], check=True)

def main():
    install_seleniumbase()
    
    from seleniumbase import SB
    
    DISCORD_EMAIL = os.environ.get("DISCORD_EMAIL", "")
    DISCORD_PASS = os.environ.get("DISCORD_PASS", "")
    PROXY = os.environ.get("SOCKS_PROXY", "")
    TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
    TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
    
    if not DISCORD_EMAIL or not DISCORD_PASS:
        print("[ERROR] DISCORD_EMAIL or DISCORD_PASS not set!")
        sys.exit(1)
    
    print(f"[INFO] Starting auto-login for {DISCORD_EMAIL}...")
    
    proxy_arg = None
    if PROXY:
        proxy_arg = PROXY.replace("socks5h://", "socks5://")
    
    with SB(
        uc=True,
        headless=True,
        proxy=proxy_arg if proxy_arg else None,
    ) as sb:
        try:
            # Step 1: Go to SlimeNodes login (redirects to Discord OAuth)
            print("[INFO] Navigating to SlimeNodes login...")
            sb.uc_open_with_reconnect("https://dash.slimenodes.com/login", 4)
            time.sleep(3)
            
            current_url = sb.get_current_url()
            print(f"[INFO] Current URL: {current_url[:100]}")
            
            # We should be on Discord login or authorize page
            if "discord.com" in current_url:
                print("[INFO] On Discord OAuth page")
                
                # Check if we need to login to Discord first
                if "/login" in current_url or "authorize" not in current_url:
                    print("[INFO] Logging into Discord...")
                    
                    # Wait for login form
                    sb.wait_for_element('input[type="email"]', timeout=15)
                    sb.type('input[type="email"]', DISCORD_EMAIL)
                    sb.type('input[type="password"]', DISCORD_PASS)
                    
                    # Click login button
                    sb.click('button[type="submit"]')
                    time.sleep(5)
                    
                    # Handle potential captcha/verification
                    current_url = sb.get_current_url()
                    if "verify" in current_url or "captcha" in current_url.lower():
                        print("[WARN] Discord captcha/verify - using UC click to handle...")
                        try:
                            sb.uc_gui_click_captcha()
                            time.sleep(5)
                        except Exception as e:
                            print(f"[WARN] UC captcha click failed: {e}")
                            time.sleep(10)
                    
                    current_url = sb.get_current_url()
                    print(f"[INFO] After login: {current_url[:100]}")
                
                # Check if we are on the authorize page
                if "authorize" in current_url:
                    print("[INFO] On authorize page, clicking authorize...")
                    time.sleep(2)
                    try:
                        sb.wait_for_element('button[data-theme]', timeout=10)
                        sb.uc_click('button[data-theme]')
                    except:
                        try:
                            sb.click('div[role="button"] button')
                        except:
                            sb.click('button')
                    time.sleep(5)
                    current_url = sb.get_current_url()
                    print(f"[INFO] After authorize: {current_url[:100]}")
            
            # Step 2: Check if we got redirected back to SlimeNodes
            if "slimenodes.com" in current_url:
                print("[OK] Back on SlimeNodes!")
                cookies = sb.get_cookies()
                sid = None
                for cookie in cookies:
                    if cookie.get("name") == "connect.sid":
                        sid = cookie.get("value")
                        break
                
                if sid:
                    print(f"[OK] Got connect.sid: {sid[:30]}...")
                    with open("/tmp/slime_session.txt", "w") as f:
                        f.write(sid)
                    
                    if TG_BOT_TOKEN and TG_CHAT_ID:
                        msg = f"SlimeNodes Auto-Login\n[OK] Session refreshed\nSID: {sid[:20]}..."
                        subprocess.run([
                            "curl", "-s", "-X", "POST",
                            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                            "-H", "Content-Type: application/json",
                            "-d", json.dumps({"chat_id": TG_CHAT_ID, "text": msg})
                        ], capture_output=True, timeout=10)
                    return
                else:
                    print("[ERROR] No connect.sid found in cookies")
                    print(f"[INFO] Cookies: {[c.get('name') for c in cookies]}")
            
            # Try direct navigation
            print("[INFO] Trying dashboard directly...")
            sb.uc_open_with_reconnect("https://dash.slimenodes.com/dashboard", 4)
            time.sleep(3)
            
            cookies = sb.get_cookies()
            for cookie in cookies:
                if cookie.get("name") == "connect.sid":
                    sid = cookie.get("value")
                    with open("/tmp/slime_session.txt", "w") as f:
                        f.write(sid)
                    print(f"[OK] Got connect.sid: {sid[:30]}...")
                    return
            
            print("[ERROR] Failed to get connect.sid")
            print(f"[INFO] Final URL: {sb.get_current_url()}")
            print(f"[INFO] All cookies: {[c.get('name') for c in sb.get_cookies()]}")
            try:
                sb.save_screenshot("/tmp/login_debug.png")
                print("[INFO] Screenshot saved")
            except:
                pass
            sys.exit(1)
            
        except Exception as e:
            print(f"[ERROR] {e}")
            try:
                sb.save_screenshot("/tmp/login_error.png")
            except:
                pass
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()
