import time
import subprocess
from selenium import webdriver

def get_current_wifi_profile():
    """Tự động lấy tên Profile Wi-Fi đang kết nối hiện tại"""
    try:
        result = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        for line in result.stdout.splitlines():
            # Lấy dòng chứa Profile (hoặc 'Hồ sơ' nếu Windows dùng Tiếng Việt)
            if "Profile" in line or "Hồ sơ" in line:
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None

def reconnect_wifi_windows(ssid):
    print("Đang ngắt kết nối Wi-Fi...")
    subprocess.run(["netsh", "wlan", "disconnect"], capture_output=True)
    time.sleep(3) # Đợi 3 giây để ngắt kết nối hoàn toàn
    
    print(f"Đang kết nối lại với mạng: {ssid}...")
    subprocess.run(["netsh", "wlan", "connect", f"name={ssid}"], capture_output=True)
    time.sleep(5) # Đợi 5 giây để card mạng bắt được IP và có Internet trở lại

def main():
    # Tự động ghi nhớ tên Wi-Fi đang kết nối trước khi bắt đầu
    current_wifi = get_current_wifi_profile()
    if current_wifi:
        print(f"[*] Đã nhận diện tự động mạng Wi-Fi đang kết nối: {current_wifi}")
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
                current_url = driver.current_url
                if "google.com" in current_url:
                    is_redirected = True
                    break
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