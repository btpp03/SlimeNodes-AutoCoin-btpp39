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
            print(f"[INFO] Current URL: {current_url[:120]}")
            
            # We should be on Discord login or authorize page
            if "discord.com" in current_url:
                print("[INFO] On Discord OAuth page")
                
                # Check if we need to login to Discord first
                if "/login" in current_url or "authorize" not in current_url:
                    print("[INFO] Logging into Discord...")
                    
                    # Discord login page uses React - wait longer for JS to render
                    time.sleep(5)
                    
                    # Try multiple selectors for email input
                    email_selectors = [
                        'input[name="email"]',
                        'input[type="email"]',
                        'input[autocomplete="username"]',
                        '#uid_5',  # Discord sometimes uses generated IDs
                        'div[class*="inputWrapper"] input',
                    ]
                    
                    email_found = False
                    for sel in email_selectors:
                        try:
                            sb.wait_for_element(sel, timeout=10)
                            print(f"[INFO] Found email input with selector: {sel}")
                            email_found = True
                            break
                        except:
                            continue
                    
                    if not email_found:
                        # Try with JavaScript to find any visible text input
                        print("[INFO] Trying JS to find input elements...")
                        inputs = sb.find_elements("input")
                        print(f"[INFO] Found {len(inputs)} input elements on page")
                        for i, inp in enumerate(inputs):
                            attrs = sb.get_attribute(f"input:nth-of-type({i+1})", "outerHTML") if i < 5 else None
                            print(f"[INFO] Input {i}: {attrs}")
                        
                        # Last resort: try to find by visibility
                        try:
                            sb.wait_for_element_visible('input', timeout=10)
                            email_found = True
                            print("[INFO] Found generic input element")
                        except:
                            pass
                    
                    if email_found:
                        # Type email
                        for sel in email_selectors:
                            try:
                                sb.type(sel, DISCORD_EMAIL, timeout=5)
                                break
                            except:
                                continue
                        
                        time.sleep(1)
                        
                        # Type password
                        pw_selectors = [
                            'input[name="password"]',
                            'input[type="password"]',
                            'input[autocomplete="current-password"]',
                        ]
                        for sel in pw_selectors:
                            try:
                                sb.type(sel, DISCORD_PASS, timeout=5)
                                break
                            except:
                                continue
                        
                        time.sleep(1)
                        
                        # Click login button - try multiple selectors
                        login_selectors = [
                            'button[type="submit"]',
                            'div[class*="button"] button',
                            'button[class*="submit"]',
                        ]
                        for sel in login_selectors:
                            try:
                                sb.click(sel, timeout=5)
                                print(f"[INFO] Clicked login button with selector: {sel}")
                                break
                            except:
                                continue
                    else:
                        print("[ERROR] Could not find email input on Discord login page")
                        try:
                            page_source = sb.get_page_source()
                            print(f"[INFO] Page source (first 2000 chars): {page_source[:2000]}")
                        except:
                            pass
                    
                    time.sleep(8)
                    
                    # Handle potential captcha/verification
                    current_url = sb.get_current_url()
                    print(f"[INFO] After login attempt: {current_url[:120]}")
                    
                    if "verify" in current_url or "captcha" in current_url.lower() or "hcaptcha" in current_url.lower():
                        print("[WARN] Discord captcha/verify detected - trying UC click...")
                        try:
                            sb.uc_gui_click_captcha()
                            time.sleep(5)
                        except Exception as e:
                            print(f"[WARN] UC captcha click failed: {e}")
                            # Try to reconnect
                            sb.uc_open_with_reconnect(current_url, 8)
                            time.sleep(5)
                    
                    current_url = sb.get_current_url()
                    print(f"[INFO] After verify: {current_url[:120]}")
                
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
                    print(f"[INFO] After authorize: {current_url[:120]}")
            
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
