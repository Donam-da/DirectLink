import time
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By

def get_current_wifi_profile():
    """Tự động lấy tên Profile Wi-Fi đang kết nối hiện tại"""
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        lines = result.stdout.splitlines()
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith("Profile") or line_strip.startswith("Hồ sơ"):
                return line.split(":", 1)[1].strip()
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith("SSID") and not line_strip.startswith("BSSID"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""

class DirectLinkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DirectLink Auto Bot")
        self.root.geometry("650x550")
        
        self.is_running = False
        self.driver = None
        self.thread = None

        # --- UI Setup ---
        pad_x = 10
        pad_y = 5

        # Wi-Fi Profile
        tk.Label(root, text="Tên Wi-Fi (SSID):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=pad_x, pady=pad_y)
        self.wifi_entry = tk.Entry(root, width=50, font=("Arial", 10))
        self.wifi_entry.grid(row=0, column=1, padx=pad_x, pady=pad_y)
        current_wifi = get_current_wifi_profile()
        if current_wifi:
            self.wifi_entry.insert(0, current_wifi)

        # Target URL
        tk.Label(root, text="Target URL:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=pad_x, pady=pad_y)
        self.url_entry = tk.Entry(root, width=50, font=("Arial", 10))
        self.url_entry.grid(row=1, column=1, padx=pad_x, pady=pad_y)

        # Options
        self.headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(root, text="Chạy ngầm (Tiết kiệm RAM/CPU tối đa)", variable=self.headless_var, font=("Arial", 10)).grid(row=2, column=1, sticky="w", padx=pad_x)

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        self.start_btn = tk.Button(btn_frame, text="▶ Bắt đầu", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=15, command=self.start_bot)
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹ Dừng lại", bg="#F44336", fg="white", font=("Arial", 10, "bold"), width=15, state="disabled", command=self.stop_bot)
        self.stop_btn.pack(side="left", padx=10)

        # Log Text
        tk.Label(root, text="Nhật ký hoạt động:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", padx=pad_x)
        self.log_area = scrolledtext.ScrolledText(root, width=75, height=18, font=("Consolas", 9), state="disabled")
        self.log_area.grid(row=5, column=0, columnspan=2, padx=pad_x, pady=pad_y)

        self.log("Phần mềm sẵn sàng. Tự động tìm Wi-Fi: " + (current_wifi if current_wifi else "Không tìm thấy"))

    def log(self, message):
        """In log ra màn hình giao diện an toàn từ thread ẩn"""
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")

    def reconnect_wifi_windows(self, ssid):
        self.log(f"Đang khởi động lại Wi-Fi: '{ssid}'...")
        subprocess.run(['netsh', 'wlan', 'disconnect'], capture_output=True)
        time.sleep(1)
        
        result = subprocess.run(['netsh', 'wlan', 'connect', f'name={ssid}'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        output = result.stdout.strip()
        
        if result.returncode == 0 and ("successfully" in output.lower() or "thành công" in output.lower() or "hoàn tất" in output.lower()):
            pass # Thành công, không cần log dồn dập
        else:
            self.log("Gửi lệnh dự phòng (Kèm SSID)...")
            subprocess.run(['netsh', 'wlan', 'connect', f'ssid={ssid}', f'name={ssid}'], capture_output=True)
            
        time.sleep(3)

    def start_bot(self):
        wifi = self.wifi_entry.get().strip()
        url = self.url_entry.get().strip()
        
        if not wifi or not url:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đủ Tên Wi-Fi và URL!")
            return

        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.log("=== BẮT ĐẦU CHẠY TỰ ĐỘNG ===")

        # Khởi chạy trong Thread riêng để không block giao diện
        self.thread = threading.Thread(target=self.bot_task, args=(wifi, url, self.headless_var.get()), daemon=True)
        self.thread.start()

    def stop_bot(self):
        self.is_running = False
        self.log("=== ĐANG DỪNG... (Sẽ thoát an toàn ở chu kỳ tiếp theo) ===")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def bot_task(self, wifi, url, is_headless):
        options = webdriver.ChromeOptions()
        options.add_argument("--incognito")
        options.page_load_strategy = 'eager'
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        
        if is_headless:
            options.add_argument("--headless=new") # Chạy ngầm tiết kiệm RAM

        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            self.log("Đang khởi động Chrome...")
            self.driver = webdriver.Chrome(options=options)
            
            while self.is_running:
                # Dọn dẹp RAM: Đóng các tab quảng cáo thừa
                if len(self.driver.window_handles) > 1:
                    main_window = self.driver.window_handles[0]
                    for handle in self.driver.window_handles[1:]:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                    self.driver.switch_to.window(main_window)

                self.log(f"Đang mở URL...")
                self.driver.delete_all_cookies()
                
                while self.is_running:
                    try:
                        self.driver.get(url)
                        break
                    except Exception:
                        time.sleep(2)
                
                timeout = 30
                start_time = time.time()
                is_redirected = False
                omg_clicked = False
                
                while self.is_running and (time.time() - start_time < timeout):
                    try:
                        # Bọc try-except toàn bộ để không bị crash bởi lỗi vặt
                        current_url = self.driver.current_url
                        if "google.com" in current_url:
                            is_redirected = True
                            break
                            
                        if "omg10.com/afu.php" in current_url and not omg_clicked:
                            self.log("Nhận diện trang omg10.com, tự động click...")
                            body = self.driver.find_element(By.TAG_NAME, "body")
                            self.driver.execute_script("arguments[0].click();", body)
                            omg_clicked = True
                            time.sleep(1)
                            continue
                            
                        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                        for iframe in iframes:
                            src = iframe.get_attribute("src") or ""
                            title = iframe.get_attribute("title") or ""
                            if "turnstile" in src or "challenge" in src or "cloudflare" in title.lower():
                                try:
                                    self.driver.switch_to.frame(iframe)
                                    checkboxes = self.driver.find_elements(By.XPATH, "//*[@type='checkbox' or contains(@class, 'checkbox') or contains(@class, 'mark') or contains(@id, 'checkbox')]")
                                    for cb in checkboxes:
                                        if cb.is_displayed():
                                            self.driver.execute_script("arguments[0].click();", cb)
                                            self.log("Đã tick vào ô Cloudflare/Captcha!")
                                            time.sleep(1)
                                            break
                                except Exception:
                                    pass
                                finally:
                                    self.driver.switch_to.default_content()

                        keywords = ['verify', 'human', 'xác minh', 'xác thực', 'continue', 'tiếp tục']
                        buttons = self.driver.find_elements(By.XPATH, "//button | //a | //div[contains(@class, 'btn')]")
                        for btn in buttons:
                            if btn.is_displayed() and any(kw in btn.text.lower() for kw in keywords):
                                self.driver.execute_script("arguments[0].click();", btn)
                                self.log(f"Đã click nút xác minh.")
                                time.sleep(1)
                                break
                    except Exception:
                        pass
                    
                    time.sleep(1) # Nghỉ 1s tránh chạy 100% CPU
                
                if not self.is_running:
                    break

                if is_redirected:
                    self.log("-> Đã tới Google! Chuẩn bị Reset Wi-Fi...")
                    self.reconnect_wifi_windows(wifi)
                else:
                    self.log("-> Hết thời gian chờ nhưng chưa tới Google. Thử lại...")
                    
        except Exception as e:
            self.log(f"Lỗi hệ thống Chrome: {e}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
            self.is_running = False
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.log("=== ĐÃ DỪNG HOÀN TOÀN ===")

if __name__ == "__main__":
    root = tk.Tk()
    app = DirectLinkApp(root)
    root.mainloop()