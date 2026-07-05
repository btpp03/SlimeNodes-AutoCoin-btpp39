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
        headless=False,         # NOT headless - use xvfb instead
        xvfb=True,              # Use Xvfb virtual display
        proxy=proxy_arg if proxy_arg else None,
    ) as sb:
        try:
            # Step 1: Go to SlimeNodes login (redirects to Discord OAuth)
            print("[INFO] Navigating to SlimeNodes login...")
            sb.uc_open_with_reconnect("https://dash.slimenodes.com/login", 4)
            time.sleep(3)
            
            current_url = sb.get_current_url()
            print(f"[INFO] Current URL: {current_url[:150]}")
            
            if "discord.com" in current_url:
                print("[INFO] On Discord page")
                
                if "/login" in current_url:
                    print("[INFO] Logging into Discord...")
                    time.sleep(5)
                    
                    # Type email
                    try:
                        sb.wait_for_element('input[name="email"]', timeout=15)
                        sb.type('input[name="email"]', DISCORD_EMAIL)
                        print("[INFO] Email entered")
                    except Exception as e:
                        print(f"[ERROR] Could not find email input: {e}")
                        sys.exit(1)
                    
                    time.sleep(1)
                    
                    # Type password
                    try:
                        sb.type('input[name="password"]', DISCORD_PASS)
                        print("[INFO] Password entered")
                    except:
                        try:
                            sb.type('input[type="password"]', DISCORD_PASS)
                            print("[INFO] Password entered (type=password)")
                        except Exception as e:
                            print(f"[ERROR] Could not find password input: {e}")
                            sys.exit(1)
                    
                    time.sleep(1)
                    
                    # Click login button
                    try:
                        sb.click('button[type="submit"]')
                        print("[INFO] Login button clicked")
                    except:
                        try:
                            sb.click('button')
                            print("[INFO] Generic button clicked")
                        except Exception as e:
                            print(f"[ERROR] Could not click login: {e}")
                            sys.exit(1)
                    
                    # Wait for either redirect or captcha
                    time.sleep(8)
                    
                    current_url = sb.get_current_url()
                    print(f"[INFO] After login: {current_url[:150]}")
                    
                    # Check for hCaptcha
                    captcha_iframes = sb.find_elements('iframe[src*="hcaptcha"]')
                    if captcha_iframes:
                        print(f"[INFO] Found {len(captcha_iframes)} hCaptcha iframes")
                    
                    # If still on /login, try uc_gui_click_captcha (needs non-headless)
                    if "/login" in current_url:
                        print("[WARN] Still on login page - attempting UC captcha handling...")
                        try:
                            sb.uc_gui_click_captcha()
                            print("[INFO] UC captcha click done")
                            time.sleep(10)
                        except Exception as e:
                            print(f"[WARN] UC captcha click failed: {e}")
                        
                        current_url = sb.get_current_url()
                        print(f"[INFO] After captcha handling: {current_url[:150]}")
                    
                    # If STILL on login, try clicking captcha again with longer wait
                    if "/login" in current_url:
                        print("[WARN] Still on login - second captcha attempt...")
                        try:
                            sb.uc_gui_click_captcha()
                            time.sleep(15)
                        except Exception as e:
                            print(f"[WARN] Second captcha attempt failed: {e}")
                        
                        current_url = sb.get_current_url()
                        print(f"[INFO] After 2nd captcha: {current_url[:150]}")
                    
                    if "/login" in current_url:
                        print("[WARN] Captcha could not be solved - login failed")
                        # Check for error messages
                        try:
                            errors = sb.find_elements('[class*="error"]')
                            for el in errors[:3]:
                                try:
                                    text = sb.get_text(el)
                                    if text:
                                        print(f"[INFO] Error: {text}")
                                except:
                                    pass
                        except:
                            pass
                        try:
                            sb.save_screenshot("/tmp/discord_login_fail.png")
                        except:
                            pass
                    
                    if "verify" in current_url or "mfa" in current_url:
                        print("[WARN] 2FA/MFA required")
                        sys.exit(1)
                
                # Check if on authorize page (not /login)
                if "oauth2/authorize" in current_url and "/login" not in current_url:
                    print("[INFO] On authorize page, clicking authorize...")
                    time.sleep(2)
                    try:
                        sb.wait_for_element('button[data-theme]', timeout=10)
                        sb.uc_click('button[data-theme]')
                        print("[INFO] Authorize clicked")
                    except:
                        try:
                            sb.click('div[role="button"] button')
                        except:
                            sb.click('button')
                    time.sleep(5)
                    current_url = sb.get_current_url()
                    print(f"[INFO] After authorize: {current_url[:150]}")
            
            # Check if back on SlimeNodes
            if "slimenodes.com" in sb.get_current_url():
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
                    print("[ERROR] No connect.sid in cookies")
                    print(f"[INFO] Cookies: {[c.get('name') for c in sb.get_cookies()]}")
            
            # Final attempt
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
            print(f"[INFO] Cookies: {[c.get('name') for c in sb.get_cookies()]}")
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
