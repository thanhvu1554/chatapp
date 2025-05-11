import kivy
kivy.require('2.0.0') # Yêu cầu phiên bản Kivy

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.network.urlrequest import UrlRequest # QUAN TRỌNG: Để gọi API bất đồng bộ
from kivy.utils import get_color_from_hex, platform
from kivy.clock import Clock
from functools import partial
import json
import os
import base64
from datetime import datetime # Di chuyển lên đầu file
from urllib.parse import urlencode

# --- Theme màu sắc và Font ---
BACKGROUND_COLOR = get_color_from_hex('#F0F2F5') # Màu nền xám nhạt (FB style)
PRIMARY_COLOR = get_color_from_hex('#1877F2')    # Màu xanh dương chính (FB style)
TEXT_COLOR = get_color_from_hex('#050505')       # Màu chữ đen
SECONDARY_TEXT_COLOR = get_color_from_hex('#606770') # Màu chữ xám phụ
INPUT_BACKGROUND_COLOR = get_color_from_hex('#FFFFFF')
BUTTON_TEXT_COLOR = get_color_from_hex('#FFFFFF')
FONT_NAME = 'Roboto' # Hoặc một font nào đó bạn có và phù hợp với mobile
# Kivy sẽ dùng font hệ thống nếu Roboto không có, bạn cần đảm bảo font được đóng gói khi build

# --- API URL và file session ---
API_URL = 'http://51.81.228.215:5000'
SESSION_FILE = 'session_kivy.json'

# --- Helper functions for session ---
def save_session_kivy(username, password):
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump({'username': username, 'password': password}, f)
    except IOError:
        pass

def load_session_kivy():
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
    except (IOError, json.JSONDecodeError):
        pass
    return None

def clear_session_kivy():
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except IOError:
        pass

# --- Custom Widgets với Style mới ---
class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = FONT_NAME
        self.background_color = PRIMARY_COLOR
        self.color = BUTTON_TEXT_COLOR
        self.background_normal = '' # Để background_color có tác dụng

class StyledLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = FONT_NAME
        self.color = TEXT_COLOR

class StyledTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_name = FONT_NAME
        self.background_color = INPUT_BACKGROUND_COLOR
        self.foreground_color = TEXT_COLOR
        self.padding = [10, 10, 10, 10] # Thêm padding cho dễ nhìn

# --- Các màn hình của ứng dụng ---
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.name = 'login' # Đặt tên cho màn hình
        layout = BoxLayout(orientation='vertical', padding=40, spacing=15, size_hint=(None,None), size=(400,500), pos_hint={'center_x':0.5, 'center_y':0.5})
        layout.canvas.before.add(kivy.graphics.Color(rgba=BACKGROUND_COLOR))
        layout.canvas.before.add(kivy.graphics.Rectangle(size=layout.size, pos=layout.pos))
        # Rebind canvas on size/pos change
        layout.bind(size=lambda instance, value: setattr(layout.canvas.before.children[-1], 'size', value),
                    pos=lambda instance, value: setattr(layout.canvas.before.children[-1], 'pos', value))

        layout.add_widget(StyledLabel(text='Đăng nhập ChatApp', font_size='28sp', size_hint_y=None, height=60, color=PRIMARY_COLOR, bold=True))
        
        self.username_input = StyledTextInput(hint_text='Tên đăng nhập', multiline=False, size_hint_y=None, height=50, font_size='16sp')
        layout.add_widget(self.username_input)

        self.password_input = StyledTextInput(hint_text='Mật khẩu', password=True, multiline=False, size_hint_y=None, height=50, font_size='16sp')
        layout.add_widget(self.password_input)

        login_button = StyledButton(text='Đăng nhập', size_hint_y=None, height=55, font_size='18sp')
        login_button.bind(on_press=self.login_user)
        layout.add_widget(login_button)

        register_button = Button(text='Tạo tài khoản mới', size_hint_y=None, height=55, font_size='16sp',
                                background_color=(0,0,0,0), color=PRIMARY_COLOR) # Nút trong suốt, chữ màu xanh
        register_button.bind(on_press=self.go_to_register)
        layout.add_widget(register_button)
        
        self.status_label = StyledLabel(text='', size_hint_y=None, height=40, color=SECONDARY_TEXT_COLOR)
        layout.add_widget(self.status_label)

        layout.add_widget(BoxLayout()) # Spacer
        self.add_widget(layout)

    def login_user(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        if not username or not password:
            self.status_label.text = "Vui lòng nhập đủ thông tin."
            return

        self.status_label.text = "Đang đăng nhập..."
        payload = json.dumps({'username': username, 'password': password})
        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        UrlRequest(
            f'{API_URL}/login',
            req_body=payload,
            req_headers=headers,
            on_success=self.login_success,
            on_failure=self.login_failure,
            on_error=self.login_error,
            timeout=10
        )

    def login_success(self, request, result):
        if result.get('success'):
            save_session_kivy(self.username_input.text.strip(), self.password_input.text.strip())
            self.manager.current = 'chat'
            self.manager.get_screen('chat').set_user(result['user'])
            self.status_label.text = "" # Xóa thông báo
            self.username_input.text = "" # Xóa input
            self.password_input.text = ""
        else:
            self.status_label.text = result.get('message', 'Đăng nhập thất bại.')

    def login_failure(self, request, result):
        self.status_label.text = "Lỗi kết nối máy chủ (failure)."
        print("Login Failure:", result)

    def login_error(self, request, error):
        self.status_label.text = "Lỗi mạng hoặc máy chủ không phản hồi (error)."
        print("Login Error:", error)

    def go_to_register(self, instance):
        self.manager.current = 'register'
        self.status_label.text = "" # Xóa thông báo khi chuyển màn hình
        self.manager.get_screen('register').clear_fields()

class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super(RegisterScreen, self).__init__(**kwargs)
        self.name = 'register' # Đặt tên cho màn hình
        layout = BoxLayout(orientation='vertical', padding=40, spacing=15, size_hint=(None,None), size=(400,500), pos_hint={'center_x':0.5, 'center_y':0.5})
        layout.canvas.before.add(kivy.graphics.Color(rgba=BACKGROUND_COLOR))
        layout.canvas.before.add(kivy.graphics.Rectangle(size=layout.size, pos=layout.pos))
        layout.bind(size=lambda instance, value: setattr(layout.canvas.before.children[-1], 'size', value),
            pos=lambda instance, value: setattr(layout.canvas.before.children[-1], 'pos', value))

        layout.add_widget(StyledLabel(text='Tạo tài khoản ChatApp', font_size='26sp', size_hint_y=None, height=60, color=PRIMARY_COLOR, bold=True))
        
        self.username_input = StyledTextInput(hint_text='Tên đăng nhập mới', multiline=False, size_hint_y=None, height=50, font_size='16sp')
        layout.add_widget(self.username_input)

        self.password_input = StyledTextInput(hint_text='Mật khẩu mới', password=True, multiline=False, size_hint_y=None, height=50, font_size='16sp')
        layout.add_widget(self.password_input)

        register_button = StyledButton(text='Đăng ký', size_hint_y=None, height=55, font_size='18sp')
        register_button.bind(on_press=self.register_user)
        layout.add_widget(register_button)

        back_button = Button(text='Quay lại Đăng nhập', size_hint_y=None, height=55, font_size='16sp',
                             background_color=(0,0,0,0), color=PRIMARY_COLOR)
        back_button.bind(on_press=self.go_to_login)
        layout.add_widget(back_button)
        
        self.status_label = StyledLabel(text='', size_hint_y=None, height=40, color=SECONDARY_TEXT_COLOR)
        layout.add_widget(self.status_label)
        
        layout.add_widget(BoxLayout()) # Spacer
        self.add_widget(layout)
        
    def clear_fields(self):
        self.username_input.text = ""
        self.password_input.text = ""
        self.status_label.text = ""

    def register_user(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        if not username or not password:
            self.status_label.text = "Vui lòng nhập đủ thông tin."
            return

        self.status_label.text = "Đang đăng ký..."
        try:
            # Không tạo key nữa, chỉ gửi username và password
            payload_dict = {'username': username, 'password': password}
            payload = json.dumps(payload_dict)
            headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

            UrlRequest(
                f'{API_URL}/register',
                req_body=payload,
                req_headers=headers,
                on_success=self.register_success,
                on_failure=self.register_failure,
                on_error=self.register_error,
                timeout=10
            )
        except Exception as e:
            self.status_label.text = f"Lỗi đăng ký: {e}"

    def register_success(self, request, result):
        if result.get('success'):
            self.status_label.text = "Đăng ký thành công! Quay lại đăng nhập."
            self.username_input.text = ""
            self.password_input.text = ""
        else:
            self.status_label.text = result.get('message', 'Đăng ký thất bại.')

    def register_failure(self, request, result):
        self.status_label.text = "Lỗi kết nối máy chủ (failure)."
        print("Register Failure:", result)

    def register_error(self, request, error):
        self.status_label.text = "Lỗi mạng hoặc máy chủ không phản hồi (error)."
        print("Register Error:", error)

    def go_to_login(self, instance):
        self.manager.current = 'login'
        self.status_label.text = "" # Xóa thông báo khi chuyển màn hình
        self.manager.get_screen('login').status_label.text = "" # Xóa cả ở màn hình login

class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        self.name = 'chat'
        self.user = None
        self.popup = None # Để hiển thị dialog
        self.new_friend_requests_indicator = False # Chỉ báo yêu cầu mới
        self.friend_requests_check_event = None

        main_layout = BoxLayout(orientation='vertical', spacing=5, padding=10)
        main_layout.canvas.before.add(kivy.graphics.Color(rgba=BACKGROUND_COLOR))
        main_layout.canvas.before.add(kivy.graphics.Rectangle(size=main_layout.size, pos=main_layout.pos))
        main_layout.bind(size=lambda instance, value: setattr(main_layout.canvas.before.children[-1], 'size', value),
                         pos=lambda instance, value: setattr(main_layout.canvas.before.children[-1], 'pos', value))
        
        header_layout = BoxLayout(size_hint_y=None, height=60, padding=5)
        self.username_label = StyledLabel(text='Chưa đăng nhập', font_size='20sp', bold=True, halign='left', valign='middle')
        self.username_label.bind(size=self.username_label.setter('text_size')) # Cho text wrap
        
        logout_button = StyledButton(text='Đăng xuất', size_hint_x=None, width=130, height=45)
        logout_button.bind(on_press=self.logout)
        
        header_layout.add_widget(self.username_label)
        header_layout.add_widget(BoxLayout(size_hint_x=0.1)) # Spacer nhỏ
        header_layout.add_widget(logout_button)
        main_layout.add_widget(header_layout)

        # Nút Refresh bạn bè
        refresh_friends_button = StyledButton(text='Làm mới DS Bạn', size_hint_y=None, height=45, font_size='15sp')
        refresh_friends_button.bind(on_press=lambda x: self.load_friends_list(show_loading=True))
        main_layout.add_widget(refresh_friends_button)

        friends_actions_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        add_friend_button = StyledButton(text='Thêm bạn', font_size='15sp')
        add_friend_button.bind(on_press=self.show_add_friend_popup)
        self.requests_button = StyledButton(text='Yêu cầu kết bạn', font_size='15sp')
        self.requests_button.bind(on_press=self.show_friend_requests_popup)
        friends_actions_layout.add_widget(add_friend_button)
        friends_actions_layout.add_widget(self.requests_button)
        main_layout.add_widget(friends_actions_layout)

        main_layout.add_widget(StyledLabel(text='Bạn bè:', size_hint_y=None, height=35, font_size='18sp', bold=True))
        self.friends_layout = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=[0, 5, 0, 5])
        self.friends_layout.bind(minimum_height=self.friends_layout.setter('height'))
        friends_scrollview = ScrollView(size_hint=(1, 1))
        friends_scrollview.add_widget(self.friends_layout)
        main_layout.add_widget(friends_scrollview)
        
        self.add_widget(main_layout)

    def on_enter(self, *args): # Được gọi khi màn hình này được hiển thị
        if self.user: # Chỉ load nếu đã có user
            self.load_friends_list()
            self.check_friend_requests_periodically() # Bắt đầu kiểm tra định kỳ
        print(f"ChatScreen entered for user: {self.user['username'] if self.user else 'None'}")

    def on_leave(self, *args): # Được gọi khi rời màn hình này
        if self.friend_requests_check_event:
            self.friend_requests_check_event.cancel() # Hủy kiểm tra định kỳ
            self.friend_requests_check_event = None
        print("ChatScreen left")

    def check_friend_requests_periodically(self):
        if self.friend_requests_check_event: # Hủy event cũ nếu có
            self.friend_requests_check_event.cancel()
        self.fetch_friend_requests_status() # Lên lịch kiểm tra ngay và sau đó mỗi 30 giây
        self.friend_requests_check_event = Clock.schedule_interval(lambda dt: self.fetch_friend_requests_status(), 30)

    def fetch_friend_requests_status(self, *args):
        if not self.user: return
        # Chỉ lấy trạng thái (có yêu cầu mới hay không) để không làm mới toàn bộ popup nếu không cần
        # Server cần hỗ trợ API này, ví dụ /has_new_friend_requests/<username>
        # Hoặc đơn giản là lấy toàn bộ /friend_requests và kiểm tra
        UrlRequest(
            f'{API_URL}/friend_requests/{self.user["username"]}',
            on_success=self.parse_friend_requests_status,
            on_failure=lambda req, res: print("Failed to check friend requests status"),
            on_error=lambda req, err: print("Error checking friend requests status"),
            timeout=5
        )

    def parse_friend_requests_status(self, request, result):
        if result.get('success') and result.get('friend_requests'):
            if not self.new_friend_requests_indicator: # Chỉ cập nhật text nếu trạng thái thay đổi
                self.requests_button.text = 'Yêu cầu kết bạn (Mới!)'
                self.requests_button.background_color = get_color_from_hex('#FFD700') # Màu vàng
                self.new_friend_requests_indicator = True
        else: # Không có yêu cầu hoặc lỗi
            if self.new_friend_requests_indicator: # Chỉ cập nhật text nếu trạng thái thay đổi
                self.requests_button.text = 'Yêu cầu kết bạn'
                self.requests_button.background_color = PRIMARY_COLOR # Trở lại màu mặc định
                self.new_friend_requests_indicator = False
    
    def set_user(self, user_data):
        self.user = user_data
        self.username_label.text = f"Xin chào, {self.user['username']}"
        if self.manager.current == self.name: # Nếu màn hình chat đang active thì load luôn
            self.load_friends_list()
            self.check_friend_requests_periodically()

    def load_friends_list(self, show_loading=False):
        if not self.user: return
        if show_loading:
            self.friends_layout.clear_widgets()
            self.friends_layout.add_widget(StyledLabel(text='Đang tải danh sách bạn bè...', size_hint_y=None, height=40))

        UrlRequest(
            f'{API_URL}/friends/{self.user["username"]}',
            on_success=self.populate_friends_list,
            on_failure=self.load_friends_failure,
            on_error=self.load_friends_error,
            timeout=7
        )

    def populate_friends_list(self, request, result):
        self.friends_layout.clear_widgets()
        if result.get('success') and result['friends']:
            for friend_username in result['friends']:
                friend_button = Button(text=friend_username, size_hint_y=None, height=50, font_name=FONT_NAME, font_size='16sp',
                                       background_color=get_color_from_hex('#E4E6EB'), color=TEXT_COLOR, background_normal='')
                friend_button.bind(on_press=partial(self.open_conversation, friend_username))
                self.friends_layout.add_widget(friend_button)
        else:
            self.friends_layout.add_widget(StyledLabel(text='(Chưa có bạn bè)', size_hint_y=None, height=40, color=SECONDARY_TEXT_COLOR))

    def load_friends_failure(self, request, result):
        self.friends_layout.clear_widgets()
        self.friends_layout.add_widget(StyledLabel(text='(Lỗi tải danh sách bạn (server error))', size_hint_y=None, height=40, color=SECONDARY_TEXT_COLOR))

    def load_friends_error(self, request, error):
        self.friends_layout.clear_widgets()
        self.friends_layout.add_widget(StyledLabel(text='(Lỗi tải danh sách bạn (network error))', size_hint_y=None, height=40, color=SECONDARY_TEXT_COLOR))

    def open_conversation(self, friend_username, instance):
        self.manager.current = 'conversation'
        conversation_screen = self.manager.get_screen('conversation')
        conversation_screen.set_chat_participants(self.user, friend_username)

    def show_add_friend_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=20)
        content.add_widget(StyledLabel(text='Nhập tên người dùng:', font_size='16sp'))
        self.add_friend_input = StyledTextInput(hint_text='Tên bạn bè', multiline=False, size_hint_y=None, height=45)
        content.add_widget(self.add_friend_input)
        
        self.add_friend_status_label = StyledLabel(text='', size_hint_y=None, height=30) # Status trong popup
        content.add_widget(self.add_friend_status_label)

        buttons_layout = BoxLayout(size_hint_y=None, height=45, spacing=10)
        add_btn = StyledButton(text='Gửi yêu cầu')
        add_btn.bind(on_press=self.send_friend_request_action)
        buttons_layout.add_widget(add_btn)
        cancel_btn = Button(text='Hủy', background_color=(0,0,0,0), color=SECONDARY_TEXT_COLOR, font_name=FONT_NAME)
        cancel_btn.bind(on_press=lambda x: self.popup.dismiss())
        buttons_layout.add_widget(cancel_btn)
        content.add_widget(buttons_layout)

        self.popup = Popup(title='Thêm bạn mới', content=content, size_hint=(0.9, None), height=280,
                           title_font=FONT_NAME, title_size='18sp',
                           separator_color=PRIMARY_COLOR,
                           background_color=BACKGROUND_COLOR, background='') # Custom background
        self.popup.open()

    def send_friend_request_action(self, instance):
        friend_username_to_add = self.add_friend_input.text.strip()
        if not friend_username_to_add or not self.user:
            self.add_friend_status_label.text = "Tên không hợp lệ."
            return
        if friend_username_to_add == self.user['username']:
            self.add_friend_status_label.text = "Không thể tự kết bạn."
            return
        
        self.add_friend_status_label.text = "Đang gửi..."
        payload = json.dumps({'user1': self.user['username'], 'user2': friend_username_to_add})
        headers = {'Content-type': 'application/json'}
        UrlRequest(f'{API_URL}/add_friend', req_body=payload, req_headers=headers,
                   on_success=self.add_friend_success,
                   on_failure=partial(self.add_friend_failure_error, "Lỗi server khi thêm bạn."),
                   on_error=partial(self.add_friend_failure_error, "Lỗi mạng khi thêm bạn."),
                   timeout=7)

    def add_friend_success(self, request, result):
        self.add_friend_status_label.text = result.get('message', 'Yêu cầu đã xử lý.')
        if result.get('success'):
            Clock.schedule_once(lambda dt: self.popup.dismiss(), 2) # Tự đóng popup sau 2 giây nếu thành công
        else:
            pass 
            
    def add_friend_failure_error(self, error_message_prefix, request, result_or_error):
        self.add_friend_status_label.text = f"{error_message_prefix}"
        print(f"Add Friend Error/Failure: {result_or_error}")

    def show_friend_requests_popup(self, instance):
        if not self.user: return
        
        # Reset chỉ báo nút yêu cầu
        self.requests_button.text = 'Yêu cầu kết bạn'
        self.requests_button.background_color = PRIMARY_COLOR
        self.new_friend_requests_indicator = False

        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        title_label = StyledLabel(text='Yêu cầu kết bạn đang chờ:', size_hint_y=None, height=35, font_size='18sp', bold=True)
        content.add_widget(title_label)
        
        self.requests_layout_popup = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.requests_layout_popup.bind(minimum_height=self.requests_layout_popup.setter('height'))
        requests_scroll = ScrollView(size_hint=(1,1))
        requests_scroll.add_widget(self.requests_layout_popup)
        content.add_widget(requests_scroll)

        # Status label for this popup
        self.friend_req_popup_status = StyledLabel(text='Đang tải...', size_hint_y=None, height=30)
        content.add_widget(self.friend_req_popup_status)

        close_button = StyledButton(text='Đóng', size_hint_y=None, height=45)
        close_button.bind(on_press=lambda x: self.popup.dismiss())
        content.add_widget(close_button)
        
        self.popup = Popup(title='Quản lý yêu cầu', content=content, size_hint=(0.9, 0.8),
                           title_font=FONT_NAME, title_size='18sp', 
                           separator_color=PRIMARY_COLOR,
                           background_color=BACKGROUND_COLOR, background='')
        self.popup.open()
        self.load_requests_for_popup() # Tải dữ liệu cho popup

    def load_requests_for_popup(self):
        self.friend_req_popup_status.text = 'Đang tải yêu cầu...'
        UrlRequest(
            f'{API_URL}/friend_requests/{self.user["username"]}',
            on_success=self.populate_requests_popup,
            on_failure=partial(self.requests_popup_failure_error, "Lỗi server khi tải yêu cầu."),
            on_error=partial(self.requests_popup_failure_error, "Lỗi mạng khi tải yêu cầu."),
            timeout=5
        )
    
    def populate_requests_popup(self, request, result):
        self.requests_layout_popup.clear_widgets()
        if result.get('success') and result['friend_requests']:
            self.friend_req_popup_status.text = '' # Xóa status
            for req_user in result['friend_requests']:
                req_box = BoxLayout(size_hint_y=None, height=50, spacing=5)
                req_label = StyledLabel(text=req_user, font_size='16sp')
                
                accept_btn = Button(text='Chấp nhận', size_hint_x=None, width=120, font_name=FONT_NAME,
                                    background_color=get_color_from_hex('#42b72a'), color=BUTTON_TEXT_COLOR, background_normal='') # Green
                accept_btn.bind(on_press=partial(self.accept_request_action, req_user))
                
                reject_btn = Button(text='Từ chối', size_hint_x=None, width=100, font_name=FONT_NAME,
                                    background_color=get_color_from_hex('#E4E6EB'), color=TEXT_COLOR, background_normal='') # Light Gray
                reject_btn.bind(on_press=partial(self.reject_request_action, req_user))
                
                req_box.add_widget(req_label)
                req_box.add_widget(accept_btn)
                req_box.add_widget(reject_btn)
                self.requests_layout_popup.add_widget(req_box)
        else:
            self.friend_req_popup_status.text = '(Không có yêu cầu mới)' if result.get('success') else result.get('message', 'Lỗi tải.')

    def requests_popup_failure_error(self, error_message_prefix, request, result_or_error):
        self.requests_layout_popup.clear_widgets()
        self.friend_req_popup_status.text = error_message_prefix
        print(f"Requests Popup Error/Failure: {result_or_error}")

    def accept_request_action(self, friend_to_accept, instance):
        self.friend_req_popup_status.text = f"Đang chấp nhận {friend_to_accept}..."
        payload = json.dumps({'user': self.user['username'], 'friend': friend_to_accept})
        UrlRequest(f'{API_URL}/accept_friend', req_body=payload, req_headers={'Content-type': 'application/json'},
                   on_success=partial(self.handle_request_action_success, f"Đã chấp nhận {friend_to_accept}."),
                   on_failure=partial(self.handle_request_action_failure_error, "Lỗi server khi chấp nhận."),
                   on_error=partial(self.handle_request_action_failure_error, "Lỗi mạng khi chấp nhận."),
                   timeout=7)

    def reject_request_action(self, friend_to_reject, instance):
        self.friend_req_popup_status.text = f"Đang từ chối {friend_to_reject}..."
        payload = json.dumps({'user': self.user['username'], 'friend': friend_to_reject})
        UrlRequest(f'{API_URL}/reject_friend', req_body=payload, req_headers={'Content-type': 'application/json'},
                   on_success=partial(self.handle_request_action_success, f"Đã từ chối {friend_to_reject}."),
                   on_failure=partial(self.handle_request_action_failure_error, "Lỗi server khi từ chối."),
                   on_error=partial(self.handle_request_action_failure_error, "Lỗi mạng khi từ chối."),
                   timeout=7)
                   
    def handle_request_action_success(self, success_message_prefix, request, result):
        self.friend_req_popup_status.text = f"{success_message_prefix}: {result.get('message')}"
        self.load_requests_for_popup() # Tải lại danh sách yêu cầu trong popup
        self.load_friends_list() # Quan trọng: Làm mới danh sách bạn bè ở màn hình chính

    def handle_request_action_failure_error(self, error_message_prefix, request, result_or_error):
        self.friend_req_popup_status.text = error_message_prefix
        self.load_requests_for_popup() # Vẫn tải lại để user thấy trạng thái mới nhất dù có lỗi
        print(f"Handle Request Action Error/Failure: {result_or_error}")

    def logout(self, instance):
        clear_session_kivy()
        if self.friend_requests_check_event: # Hủy event khi logout
            self.friend_requests_check_event.cancel()
            self.friend_requests_check_event = None
        self.manager.current = 'login'
        self.user = None
        self.username_label.text = 'Chưa đăng nhập'
        self.friends_layout.clear_widgets()
        self.requests_button.text = 'Yêu cầu kết bạn' # Reset nút
        self.requests_button.background_color = PRIMARY_COLOR
        self.new_friend_requests_indicator = False

class ConversationScreen(Screen):
    def __init__(self, **kwargs):
        super(ConversationScreen, self).__init__(**kwargs)
        self.name = 'conversation'
        self.current_user_data = None
        self.friend_username = None
        self.private_key_obj = None
        self.message_load_event = None

        main_layout = BoxLayout(orientation='vertical', spacing=5, padding=5)
        main_layout.canvas.before.add(kivy.graphics.Color(rgba=BACKGROUND_COLOR))
        main_layout.canvas.before.add(kivy.graphics.Rectangle(size=main_layout.size, pos=main_layout.pos))
        main_layout.bind(size=lambda instance, value: setattr(main_layout.canvas.before.children[-1], 'size', value),
                         pos=lambda instance, value: setattr(main_layout.canvas.before.children[-1], 'pos', value))

        header = BoxLayout(size_hint_y=None, height=60, padding=5)
        self.friend_label = StyledLabel(text='Chat với...', font_size='20sp', bold=True)
        back_button = StyledButton(text='< Bạn bè', size_hint_x=None, width=130, height=45)
        back_button.bind(on_press=self.go_back_to_chat_screen)
        header.add_widget(back_button)
        header.add_widget(self.friend_label)
        header.add_widget(BoxLayout(size_hint_x=0.1)) # Spacer nhỏ
        main_layout.add_widget(header)

        self.messages_display_layout = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=[5,10,5,10])
        self.messages_display_layout.bind(minimum_height=self.messages_display_layout.setter('height'))
        
        self.messages_scrollview = ScrollView(size_hint=(1, 1)) # Lưu trữ ScrollView để cuộn
        self.messages_scrollview.add_widget(self.messages_display_layout)
        main_layout.add_widget(self.messages_scrollview)

        input_area = BoxLayout(size_hint_y=None, height=60, padding=5, spacing=5)
        self.message_input = StyledTextInput(hint_text='Nhập tin nhắn...', multiline=False, size_hint_y=None, height=50, font_size='16sp')
        send_button = StyledButton(text='Gửi', size_hint_x=None, width=90, height=50, font_size='16sp')
        send_button.bind(on_press=self.send_chat_message)
        input_area.add_widget(self.message_input)
        input_area.add_widget(send_button)
        main_layout.add_widget(input_area)

        self.add_widget(main_layout)
        
    def on_enter(self, *args):
        self.load_chat_history() # Tải lần đầu
        if self.message_load_event: self.message_load_event.cancel() # Hủy event cũ
        self.message_load_event = Clock.schedule_interval(lambda dt: self.load_chat_history(is_periodic_refresh=True), 15) # Làm mới tin nhắn mỗi 15s
        print(f"ConversationScreen entered with {self.friend_username}")

    def on_leave(self, *args):
        if self.message_load_event:
            self.message_load_event.cancel()
            self.message_load_event = None
        print("ConversationScreen left")

    def set_chat_participants(self, user_data, friend_username):
        self.current_user_data = user_data
        self.friend_username = friend_username
        self.friend_label.text = f"Chat với {self.friend_username}"
        self.message_input.text = "" 
        self.messages_display_layout.clear_widgets()
        
        if not self.current_user_data or not isinstance(self.current_user_data, dict):
            print("[DEBUG] set_chat_participants: current_user_data is invalid.")
            Clock.schedule_once(lambda dt: self.add_message_to_display_widget("[LỖI] Dữ liệu người dùng không hợp lệ.", is_system=True))
            return 

    def load_chat_history(self, is_periodic_refresh=False):
        if not self.current_user_data or not self.friend_username: return
        if not is_periodic_refresh: 
            self.messages_display_layout.clear_widgets()
            self.add_message_to_display_widget("Đang tải tin nhắn...", is_system=True)

        from urllib.parse import urlencode
        history_params = {'sender': self.current_user_data['username'], 'recipient': self.friend_username}
        url = f"{API_URL}/message_history?{urlencode(history_params)}"
        UrlRequest(
            url,
            on_success=partial(self.populate_chat_history, is_periodic_refresh),
            on_failure=partial(self.load_chat_history_fallback, is_periodic_refresh), 
            on_error=partial(self.load_chat_history_fallback, is_periodic_refresh),   
            timeout=7
        )

    def populate_chat_history(self, is_periodic_refresh, request, result):
        current_message_widgets = {child.text for child in self.messages_display_layout.children if hasattr(child, 'text')} # Lưu text của widget hiện tại (đơn giản hóa)
        new_messages_data = []
        has_new_content = False

        if result.get('success') and result.get('history'):
            new_messages_data = result['history']
            if not is_periodic_refresh: # Lần tải đầu tiên, luôn vẽ lại
                has_new_content = True
            else: # Kiểm tra nếu có tin nhắn mới thực sự
                if len(new_messages_data) != len(current_message_widgets):
                    has_new_content = True
                else:
                    # So sánh nội dung (đơn giản, có thể cần ID tin nhắn để chính xác hơn)
                    temp_new_texts = {msg['original_content'] for msg in new_messages_data}
                    if temp_new_texts != current_message_widgets:
                        has_new_content = True
        
        if has_new_content:
            self.messages_display_layout.clear_widgets() 
            if not new_messages_data and not is_periodic_refresh : self.add_message_to_display_widget("(Chưa có tin nhắn)", is_system=True)
            for msg_data in new_messages_data:
                is_my_message = (msg_data['sender'] == self.current_user_data['username'])
                self.add_message_to_display_widget(msg_data['original_content'], is_my_message)
            if new_messages_data: # Chỉ cuộn nếu có tin nhắn mới được thêm
                Clock.schedule_once(self.scroll_to_bottom, 0.1) 
        elif not new_messages_data and not is_periodic_refresh:
            self.messages_display_layout.clear_widgets()
            self.add_message_to_display_widget("(Lỗi tải lịch sử hoặc không có tin nhắn)", is_system=True)

    def load_chat_history_fallback(self, is_periodic_refresh, request, result_or_error):
        if not self.private_key_obj:
            if not is_periodic_refresh: self.add_message_to_display_widget("[LỖI] Không thể giải mã (no key).", is_system=True)
            return
        if not is_periodic_refresh:
            self.messages_display_layout.clear_widgets()
            self.add_message_to_display_widget("Đang tải tin nhắn (fallback)...", is_system=True)
        
        from urllib.parse import urlencode
        params = {'user1': self.current_user_data['username'], 'user2': self.friend_username}
        url = f"{API_URL}/messages?{urlencode(params)}"
        UrlRequest(
            url,
            on_success=partial(self.populate_chat_history_fallback, is_periodic_refresh),
            on_failure=lambda req,res: self.add_message_to_display_widget("Lỗi fallback API /messages.", is_system=True) if not is_periodic_refresh else None,
            on_error=lambda req,err: self.add_message_to_display_widget("Lỗi mạng fallback API /messages.", is_system=True) if not is_periodic_refresh else None,
            timeout=7
        )

    def populate_chat_history_fallback(self, is_periodic_refresh, request, result):
        current_message_widgets_texts = {child.text for child in self.messages_display_layout.children if hasattr(child, 'text')}
        processed_messages_texts = []
        messages_to_render = []
        has_new_content_fallback = False

        if result.get('success') and result.get('messages'):
            for msg_data in result['messages']:
                is_my_message = (msg_data['from'] == self.current_user_data['username'])
                message_content = msg_data['message']  # Không cần giải mã
                
                display_text = message_content
                processed_messages_texts.append(display_text)
                messages_to_render.append({'text': display_text, 'is_mine': is_my_message})

            if not is_periodic_refresh or set(processed_messages_texts) != current_message_widgets_texts:
                has_new_content_fallback = True
        
        if has_new_content_fallback:
            self.messages_display_layout.clear_widgets()
            if not messages_to_render and not is_periodic_refresh : self.add_message_to_display_widget("(Chưa có tin nhắn - fallback)", is_system=True)
            for msg in messages_to_render:
                self.add_message_to_display_widget(msg['text'], msg['is_mine'])
            if messages_to_render:
                 Clock.schedule_once(self.scroll_to_bottom, 0.1)
        elif not messages_to_render and not is_periodic_refresh:
            self.messages_display_layout.clear_widgets()
            self.add_message_to_display_widget("(Lỗi tải hoặc không có tin nhắn - fallback)", is_system=True)

    def add_message_to_display_widget(self, text, is_my_message=False, is_system=False):
        if is_system:
            msg_label = StyledLabel(text=text, size_hint_y=None, height=35, color=SECONDARY_TEXT_COLOR, font_size='13sp')
            msg_label.halign = 'center'
            self.messages_display_layout.add_widget(msg_label) # Thêm trực tiếp label hệ thống
        else:
            bubble_layout = BoxLayout(orientation='horizontal', size_hint_y=None, padding=[5,3,5,3])
            # Không bind minimum_height ở đây, để tự tính toán từ Label bên trong

            msg_label = Label(
                text=text, font_name=FONT_NAME, font_size='15sp',
                text_size=(self.messages_display_layout.width * 0.65 if self.messages_display_layout.width > 0 else Window.width * 0.65, None), 
                size_hint_x=None, 
                valign='top', halign='left', 
                padding=[10,8], 
                markup=True 
            )
            msg_label.bind(texture_size=msg_label.setter('size')) 
            msg_label.width = self.messages_display_layout.width * 0.7 if self.messages_display_layout.width > 0 else Window.width * 0.7

            with msg_label.canvas.before:
                kivy.graphics.Color(rgba=PRIMARY_COLOR if is_my_message else get_color_from_hex('#E4E6EB'))
                # Lưu trữ RoundedRectangle để cập nhật vị trí/kích thước
                # Quan trọng: Khởi tạo với kích thước ban đầu, sẽ được cập nhật bởi binding
                bubble_rect = kivy.graphics.RoundedRectangle(radius=[(15,15),(15,15),(15,15) if is_my_message else (3,3) ,(3,3) if is_my_message else (15,15)],
                                               pos=msg_label.pos, size=msg_label.texture_size) # Sử dụng texture_size ban đầu nếu có
            
            def update_bubble_graphics(instance, _):
                bubble_rect.pos = instance.pos
                bubble_rect.size = instance.size
            msg_label.bind(pos=update_bubble_graphics, size=update_bubble_graphics)

            if is_my_message:
                msg_label.color = BUTTON_TEXT_COLOR 
                bubble_layout.add_widget(BoxLayout(size_hint_x=None, width=self.messages_display_layout.width * 0.25 if self.messages_display_layout.width > 0 else Window.width *0.25)) # Spacer
                bubble_layout.add_widget(msg_label)
            else:
                msg_label.color = TEXT_COLOR 
                bubble_layout.add_widget(msg_label)
                bubble_layout.add_widget(BoxLayout(size_hint_x=None, width=self.messages_display_layout.width * 0.25 if self.messages_display_layout.width > 0 else Window.width * 0.25)) # Spacer
            
            self.messages_display_layout.add_widget(bubble_layout)
            # Thiết lập chiều cao của bubble_layout sau khi msg_label có kích thước
            Clock.schedule_once(lambda dt, lbl=msg_label, bl=bubble_layout: setattr(bl, 'height', lbl.texture_size[1] + 20 if lbl.texture_size else 40), 0.01)

    def scroll_to_bottom(self, dt):
        if self.messages_scrollview:
            self.messages_scrollview.scroll_y = 0 

    def send_chat_message(self, instance):
        original_message = self.message_input.text.strip()
        if not original_message or not self.current_user_data or not self.friend_username:
            return
        
        self.message_input.disabled = True
        
        # Gửi tin nhắn không mã hóa
        timestamp = datetime.now().isoformat()
        payload_send = {
            'from': self.current_user_data['username'], 
            'to': self.friend_username, 
            'message': original_message, 
            'timestamp': timestamp
        }
        
        UrlRequest(
            f'{API_URL}/send_message', 
            req_body=json.dumps(payload_send), 
            req_headers={'Content-type': 'application/json'}, 
            on_success=partial(self._on_send_message_success, original_message, timestamp), 
            on_failure=self._on_send_message_failure, 
            on_error=self._on_send_message_failure, 
            timeout=7
        )

    def _on_send_message_success(self, orig_msg, ts, request, result_send):
        if result_send.get('success'):
            # Không cần lưu lịch sử riêng nữa, tin nhắn đã được lưu khi gửi
            self.add_message_to_display_widget(orig_msg, is_my_message=True)
            self.message_input.text = ""
            Clock.schedule_once(self.scroll_to_bottom, 0.1)
        else:
            Clock.schedule_once(lambda dt: self.add_message_to_display_widget("[LỖI GỬI] Server báo lỗi.", is_system=True))
        self.message_input.disabled = False

    def _on_send_message_failure(self, request, result_or_error):
        Clock.schedule_once(lambda dt: self.add_message_to_display_widget("[LỖI GỬI] Không thể gửi tin nhắn.", is_system=True))
        self.message_input.disabled = False

    def go_back_to_chat_screen(self, instance):
        self.manager.transition = NoTransition() 
        self.manager.current = 'chat'

class ChatAppKivy(App):
    def build(self):
        sm = ScreenManager(transition=NoTransition()) 
        sm.add_widget(LoginScreen(name='login')) 
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(ChatScreen(name='chat'))
        sm.add_widget(ConversationScreen(name='conversation'))

        Clock.schedule_once(self.check_auto_login, 0.1) 
        return sm

    def check_auto_login(self, dt):
        session = load_session_kivy()
        sm = self.root 
        if session and 'username' in session and 'password' in session:
            def auto_login_success(request, result):
                if result.get('success'):
                    user_data = result['user']
                    sm.current = 'chat'
                    chat_screen = sm.get_screen('chat')
                    chat_screen.set_user(user_data)
                else:
                    clear_session_kivy()
                    sm.current = 'login' 
            
            def auto_login_fail_err(request, result_or_error):
                clear_session_kivy()
                sm.current = 'login'

            payload = json.dumps({'username': session['username'], 'password': session['password']})
            headers = {'Content-type': 'application/json'}
            UrlRequest(f'{API_URL}/login', req_body=payload, req_headers=headers, 
                       on_success=auto_login_success, 
                       on_failure=auto_login_fail_err, 
                       on_error=auto_login_fail_err, timeout=5)
        else: 
             if sm.current != 'login' and sm.current != 'register':
                sm.current = 'login'

if __name__ == '__main__':
    from kivy.core.window import Window 
    ChatAppKivy().run() 
