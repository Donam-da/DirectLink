import time
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By

def get_current_wifi_profile():
    """Tự động lấy tên Profile Wi-Fi đang kết nối hiện tại"""
    try:
        # Không dùng shell=True, dùng list để an toàn với mọi kí tự
        result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        lines = result.stdout.splitlines()
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith("Profile") or line_strip.startswith("Hồ sơ"):
                return line.split(":", 1)[1].strip()
        # Dự phòng trường hợp Windows không hiển thị dòng Profile, tìm qua dòng SSID
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith("SSID") and not line_strip.startswith("BSSID"):
                return line.split(":", 1)[1].strip()
    except Exception as e:
        print(f"[!] Lỗi khi lấy tên Wi-Fi: {e}")
    return None

def reconnect_wifi_windows(ssid):
    print("Đang ngắt kết nối Wi-Fi...")
    subprocess.run(['netsh', 'wlan', 'disconnect'], capture_output=True)
    time.sleep(3) # Đợi 3 giây để ngắt kết nối hoàn toàn
    
    print(f"Đang kết nối lại với mạng: '{ssid}'...")
    # Truyền lệnh dạng List thay vì String để tránh mọi lỗi liên quan đến khoảng trắng hay kí tự đặc biệt trong tên Wifi
    result = subprocess.run(['netsh', 'wlan', 'connect', f'name={ssid}'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    output = result.stdout.strip()
    error = result.stderr.strip() if result.stderr else ""
    
    # Nếu Windows báo thành công (tiếng Anh hoặc tiếng Việt) hoặc mã trả về = 0
    if result.returncode == 0 and ("successfully" in output.lower() or "thành công" in output.lower() or "hoàn tất" in output.lower()):
        print("  -> Đã gửi lệnh kết nối tới hệ thống thành công!")
    else:
        print(f"  -> [Cảnh báo] Phản hồi từ CMD: {output}")
        if error:
            print(f"  -> [Lỗi CMD]: {error}")
        print("  -> Đang thử gửi lệnh dự phòng...")
        # Lệnh dự phòng: Đôi khi Windows cần xác định rõ cả SSID và Name
        subprocess.run(['netsh', 'wlan', 'connect', f'ssid={ssid}', f'name={ssid}'], capture_output=True)
        
    time.sleep(5) # Đợi 5 giây để card mạng bắt được IP và có Internet trở lại

def main():
    # Tự động ghi nhớ tên Wi-Fi đang kết nối trước khi bắt đầu
    current_wifi = get_current_wifi_profile()
    if current_wifi:
        print(f"[*] Đã nhận diện tự động mạng Wi-Fi đang kết nối: '{current_wifi}'")
    else:
        current_wifi = input("[!] Không tự động tìm thấy Wi-Fi. Nhập tên mạng Wi-Fi thủ công: ")

    target_url = input("Nhập URL bạn muốn mở: ")
    
    # Khởi tạo trình duyệt Chrome một lần duy nhất ở ngoài vòng lặp
    options = webdriver.ChromeOptions()
    options.add_argument("--incognito") # Chế độ ẩn danh
    driver = webdriver.Chrome(options=options)
    
    try:
        while True:
            print(f"\n--- Bắt đầu mở URL: {target_url} ---")
            
            # Xóa toàn bộ cookie để trình duyệt "sạch" cho mỗi lần lặp
            driver.delete_all_cookies()
            
            # Thử tải trang, nếu chưa có mạng do chưa kết nối lại xong thì tự động thử lại
            while True:
                try:
                    driver.get(target_url)
                    break
                except Exception:
                    print("Internet chưa kết nối lại hoàn toàn, đang đợi thêm...")
                    time.sleep(2)
            
            # Chờ và liên tục kiểm tra xem URL trình duyệt có chứa 'google.com' không
            timeout = 30 # Thời gian chờ tối đa 30 giây
            start_time = time.time()
            is_redirected = False
            
            while time.time() - start_time < timeout:
                try:
                    current_url = driver.current_url
                    if "google.com" in current_url:
                        is_redirected = True
                        break
                except Exception:
                    pass

                # --- Tự động tìm và nhấn ô xác minh (Cloudflare/Captcha/Verify) ---
                try:
                    # 1. Quét các iframe (Thường checkbox xác thực nằm trong iframe do bên thứ 3 cung cấp)
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes:
                        src = iframe.get_attribute("src") or ""
                        title = iframe.get_attribute("title") or ""
                        # Nhận diện iFrame của Cloudflare hoặc Captcha
                        if "turnstile" in src or "challenge" in src or "cloudflare" in title.lower():
                            driver.switch_to.frame(iframe)
                            try:
                                # Tìm ô checkbox bên trong iframe
                                checkboxes = driver.find_elements(By.XPATH, "//*[@type='checkbox' or contains(@class, 'checkbox') or contains(@class, 'mark') or contains(@id, 'checkbox')]")
                                for cb in checkboxes:
                                    if cb.is_displayed():
                                        # Sử dụng Javascript click để vượt qua các overlay quảng cáo ẩn nếu có
                                        driver.execute_script("arguments[0].click();", cb)
                                        print("  -> Đã tick tự động vào ô xác thực Captcha/Cloudflare!")
                                        time.sleep(2) # Chờ 2 giây để trang xử lý sau khi ấn
                                        break
                            except Exception:
                                pass
                            finally:
                                driver.switch_to.default_content() # Trả luồng điều khiển về trang chính

                    # 2. Tìm nút bấm xác nhận trên trang chính (Dành cho các trang verify thông thường)
                    keywords = ['verify', 'human', 'xác minh', 'xác thực', 'continue', 'tiếp tục']
                    buttons = driver.find_elements(By.XPATH, "//button | //a | //div[contains(@class, 'btn')]")
                    for btn in buttons:
                        if btn.is_displayed() and any(kw in btn.text.lower() for kw in keywords):
                            driver.execute_script("arguments[0].click();", btn)
                            print(f"  -> Đã tự động nhấn nút: {btn.text.strip()}")
                            time.sleep(2)
                            break
                except Exception:
                    pass
                # -------------------------------------------------------------------

                time.sleep(1) # Kiểm tra mỗi giây 1 lần
            
            if is_redirected:
                print("Đã phát hiện chuyển hướng sang Google! Thực hiện reset Wi-Fi...")
                reconnect_wifi_windows(current_wifi)
            else:
                print("Hết thời gian chờ nhưng không thấy chuyển sang Google. Đang thử lại...")
                    
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình an toàn.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()