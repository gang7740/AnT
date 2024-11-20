import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Text, Button
from PIL import Image, ImageTk, ImageDraw
import json
import os
import uuid
import random
import string


# Define a custom multi-line text input dialog
class MultiLineInputDialog:
    def __init__(self, parent, title="Input", initial_text=""):
        self.dialog = Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Create a larger Text widget for multi-line input
        self.text = Text(self.dialog, width=40, height=10, wrap="word")
        self.text.insert("1.0", initial_text)  # insert initial text if any
        self.text.pack(padx=10, pady=10)
        self.text.focus_set()  # Focus on input when dialog opens

        # Button to confirm input
        self.confirm_button = Button(self.dialog, text="OK", command=self.confirm)
        self.confirm_button.pack(pady=5)

        # Binding Shift+Return for new line without other actions
        self.text.bind("<Shift-Return>", self.insert_newline)

        # Binding Return to confirm() for submitting and closing the dialog
        self.text.bind("<Return>", self.on_return)

        self.result = None

    def insert_newline(self, event):
        # Insert a single newline and prevent other actions
        self.text.insert("insert", "\n")
        return "break"

    def on_return(self, event):
        # Confirm input and close dialog
        self.confirm()
        return "break"

    def confirm(self):
        # Get text input, remove trailing newline, and close the dialog
        self.result = self.text.get("1.0", "end-1c")
        self.dialog.destroy()

    def show(self):
        self.dialog.wait_window()
        return self.result
    


class ImageEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Drawing with Nodes")

        # 레이아웃 설정
        self.top_frame = tk.Frame(root)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        self.left_frame = tk.Frame(root)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right_frame = tk.Frame(root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # 투명도 슬라이더 설정
        self.opacity_slider = tk.Scale(self.top_frame, from_=0, to=255, orient=tk.HORIZONTAL, label="Transparency")
        self.opacity_slider.set(128)  # 기본 값 128
        self.opacity_slider.pack(fill=tk.X)
        self.opacity_slider.bind("<Motion>", self.adjust_opacity)

        # 비율 유지 체크박스 설정
        self.keep_aspect_ratio = tk.BooleanVar(value=True)
        self.aspect_ratio_checkbox = tk.Checkbutton(self.top_frame, text="Keep Aspect Ratio", variable=self.keep_aspect_ratio)
        self.aspect_ratio_checkbox.pack()

        # 캔버스 설정
        self.canvas = tk.Canvas(self.left_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self.on_resize)

        self.resizing = False  # Flag to check if resizing is active


        # 메뉴 바 설정
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        file_menu = tk.Menu(menubar)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Image", command=self.load_image)
        file_menu.add_command(label="Save Image", command=self.save_image)
        file_menu.add_command(label="Save Nodes and Connections as JSON", command=self.save_nodes_as_json)
        file_menu.add_command(label="Load JSON", command=self.load_json)  # New menu option
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)


        # 모드 선택 버튼
        self.mode_frame = tk.Frame(self.right_frame)
        self.mode_frame.pack(padx=10, pady=5)
        self.mode_var = tk.StringVar(value="draw")
        self.draw_mode_btn = tk.Radiobutton(self.mode_frame, text="Draw Node", variable=self.mode_var, value="draw")
        self.connect_mode_btn = tk.Radiobutton(self.mode_frame, text="Connect Nodes", variable=self.mode_var, value="connect")
        self.draw_mode_btn.pack(side=tk.LEFT, padx=5)
        self.connect_mode_btn.pack(side=tk.LEFT, padx=5)

        # 노드 목록 박스 및 버튼 설정
        self.label_listbox = tk.Listbox(self.right_frame, width=40, height=20)
        self.label_listbox.pack(padx=10, pady=10)
        self.label_listbox.bind('<<ListboxSelect>>', self.on_list_select)
        
        self.delete_button = tk.Button(self.right_frame, text="Delete Selected", command=self.delete_selected)
        self.delete_button.pack(padx=10, pady=5)
        
        self.edit_button = tk.Button(self.right_frame, text="Edit Selected", command=self.edit_selected)
        self.edit_button.pack(padx=10, pady=5)
        
        # Toggle Direction 버튼 추가
        self.toggle_direction_button = tk.Button(self.right_frame, text="Toggle Direction", command=self.toggle_direction)
        self.toggle_direction_button.pack(padx=10, pady=5)

        # 이미지 및 도형 관련 변수 초기화
        self.image = None
        self.original_image = None
        self.tk_image = None
        self.draw = None
        self.nodes = []
        self.connections = []
        self.start_x = None
        self.start_y = None
        self.selected_node = None
        self.selected_nodes = []
        self.dragging = False
        self.scale_x = 1
        self.scale_y = 1
        self.img_x = 0
        self.img_y = 0
        self.drag_data = {"x": 0, "y": 0}

        # 이벤트 바인딩
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<B3-Motion>", self.on_node_drag)
        self.canvas.bind("<ButtonRelease-3>", self.end_node_drag)

        # 키보드 화살표로 이미지 이동 설정
        move_step = 20
        self.root.bind("<Up>", lambda event: self.move_image(0, -move_step))
        self.root.bind("<Down>", lambda event: self.move_image(0, move_step))
        self.root.bind("<Left>", lambda event: self.move_image(-move_step, 0))
        self.root.bind("<Right>", lambda event: self.move_image(move_step, 0))

        # 확대/축소 관련 변수 및 이벤트 바인딩
        self.scale_factor = 1.0
        self.zoom_step = 0.1
        self.canvas.bind("<Control-MouseWheel>", self.zoom)
        self.canvas.bind("<Motion>", self.on_motion)

        # 단축키 바인딩: Ctrl+S로 JSON 파일 저장
        self.root.bind('<Control-s>', self.save_nodes_as_json)
        self.root.bind('<Control-S>', self.save_nodes_as_json)


        # Define available colors and current selected color
        self.colors = {
            "Black": "#000000",
            "Red": "#FF0000",
            "Green": "#00FF00",
            "Blue": "#0000FF",
            "Yellow": "#FFFF00",
            "Purple": "#800080",
            "Cyan": "#00FFFF",
            "Orange": "#FFA500"
        }
        self.selected_color = tk.StringVar(value="Black")  # Default color

        # Color selection menu
        self.color_label = tk.Label(self.right_frame, text="Select Connection Color:")
        self.color_label.pack(pady=5)
        self.color_menu = tk.OptionMenu(self.right_frame, self.selected_color, *self.colors.keys(), command=self.change_connection_color)
        self.color_menu.pack()

       
        # 기타 초기화
        self.image_path = None
        
        # 선택된 항목의 인덱스를 분리하여 초기화
        self.selected_node_index = None
        self.selected_connection_index = None
        self.selected_item_index = None  # 초기화 추가

        # type_selector 초기화
        self.setup_type_selector()
    def assign_parent_child_relationship(self):
        """노드 간 부모-자식 관계를 설정"""
        for child in self.nodes:
            child['parent_id'] = None  # 초기화

            for parent in self.nodes:
                if child['id'] == parent['id']:
                    continue

                # 부모 노드의 영역 계산
                px1, py1, px2, py2 = parent['coords']
                cx1, cy1, cx2, cy2 = child['coords']

                # 자식 노드가 부모 노드 안에 완전히 포함되는지 확인
                if px1 <= cx1 <= px2 and px1 <= cx2 <= px2 and py1 <= cy1 <= py2 and py1 <= cy2 <= py2:
                    child['parent_id'] = parent['id']
                    break  # 첫 번째 부모를 찾으면 종료


    def update_label_listbox(self):
        """Listbox 업데이트 메서드, 노드와 연결을 각각 추가."""
        self.label_listbox.delete(0, tk.END)

        # 노드를 리스트 박스에 추가
        for node in self.nodes:
            self.label_listbox.insert(tk.END, f"Node({node['id']}): {node['text']}")

        # 연결을 리스트 박스에 추가
        for connection in self.connections:
            from_id = connection['from']
            to_id = connection['to']
            direction_icon = "→" if connection['direction'] else "-"
            text = connection['text'] or ""
            connection_type = connection['type']
            display_text = f"Connection({connection['id']}): {from_id} {direction_icon} {to_id} ({text}) [Type: {connection_type}]"
            self.label_listbox.insert(tk.END, display_text)

    def on_list_select(self, event):
        selection = self.label_listbox.curselection()

        if selection:
            selected_index = selection[0]

            # `selected_item_index`로 통합 관리
            self.selected_item_index = selected_index

            # 노드와 연결 구분
            if selected_index < len(self.nodes):
                self.selected_node_index = selected_index
                self.selected_connection_index = None
            else:
                self.selected_node_index = None
                self.selected_connection_index = selected_index - len(self.nodes)
        else:
            self.selected_node_index = None
            self.selected_connection_index = None
            self.selected_item_index = None

        self.update_canvas()


    def change_connection_color(self, _=None):
        selected_index = self.label_listbox.curselection()
        if not selected_index:
            return  # 색상을 변경할 항목이 선택되지 않은 경우

        selected_index = selected_index[0]

        # 선택된 항목이 연결인지 확인
        if selected_index >= len(self.nodes):  # Nodes count as entries before connections in Listbox
            connection_index = selected_index - len(self.nodes)
            
            # 현재 선택된 색상 가져오기
            color_name = self.selected_color.get()
            new_color = self.colors[color_name]
            
            # 연결의 색상 속성 업데이트
            self.connections[connection_index]['color'] = new_color
            
            # Listbox에서 텍스트 업데이트
            connection = self.connections[connection_index]
            from_id = connection['from']
            to_id = connection['to']
            direction_icon = "→" if connection['direction'] else "-"
            text = connection['text'] or ""
            connection_type = connection['type']
            display_text = f"Connection({connection['id']}): {from_id} {direction_icon} {to_id} ({text}) [Type: {connection_type}] [Color: {color_name}]"
            
            # Listbox 갱신
            self.label_listbox.delete(selected_index)
            self.label_listbox.insert(selected_index, display_text)
            
            # 변경 사항을 반영하기 위해 캔버스를 다시 그립니다.
            self.update_canvas()



    def load_json(self):
        json_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if not json_path:
            return  # 파일 선택 취소 시 종료
        try:
            # JSON 파일에서 데이터 로드
            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)

            # 기존 데이터 초기화
            self.nodes.clear()
            self.connections.clear()
            self.label_listbox.delete(0, tk.END)
            self.selected_item_index = None  # 선택 항목 초기화

            # 좌표 겹침 방지를 위한 함수들 정의
            def is_overlapping(new_coords, existing_coords):
                """Check if new_coords overlap with any in existing_coords list."""
                x1, y1, x2, y2 = new_coords
                for ex_x1, ex_y1, ex_x2, ex_y2 in existing_coords:
                    if not (x2 < ex_x1 or x1 > ex_x2 or y2 < ex_y1 or y1 > ex_y2):
                        return True
                return False

            def assign_non_overlapping_coords(existing_coords):
                """Assign coordinates that do not overlap with existing_coords."""
                x, y, width, height = 50, 50, 100, 50
                while is_overlapping((x, y, x + width, y + height), existing_coords):
                    x += 120
                    if x + width > self.canvas.winfo_width():
                        x = 50
                        y += 70
                return (x, y, x + width, y + height)

            existing_coords = []  # Track existing node coordinates for overlap checking

            # 노드 불러오기 및 리스트 초기화
            def parse_nodes(node_list, parent_id=None):
                for node in node_list:
                    if "coords" not in node or not node["coords"]:
                        node["coords"] = assign_non_overlapping_coords(existing_coords)
                    existing_coords.append(node["coords"])

                    node_data = {
                        "id": node["id"],
                        "coords": node["coords"],
                        "text": node["text"],
                        "parent_id": parent_id
                    }
                    self.nodes.append(node_data)

                    # Listbox에 노드 추가
                    self.label_listbox.insert(tk.END, f"Node({node['id']}): {node['text']}")
                    parse_nodes(node["node"], node["id"])

            # 최상위 "components" 키의 데이터를 재귀적으로 파싱
            parse_nodes(data.get("components", []))  # "components"로 변경

            # connections를 불러와 Listbox에 추가
            def generate_unique_id(existing_ids):
                """Generate a unique 3-character ID."""
                while True:
                    new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
                    if new_id not in existing_ids:
                        return new_id

            existing_ids = {conn.get('id') for conn in data.get("connections", []) if 'id' in conn}
            self.connections = data.get("connections", [])
            for connection in self.connections:
                if 'id' not in connection or not connection['id']:
                    connection['id'] = generate_unique_id(existing_ids)
                    existing_ids.add(connection['id'])
                from_id = connection['from']
                to_id = connection['to']
                direction_icon = "→" if connection['direction'] else "-"
                text = connection['text'] or ""
                connection_type = connection['type']
                color = connection.get('color', "#000000")  # Default to black if color is missing
                connection['color'] = color  # 기본값 적용
                display_text = f"Connection({connection['id']}): {from_id} {direction_icon} {to_id} ({text}) [Type: {connection_type}]"
                self.label_listbox.insert(tk.END, display_text)

            # 이미지 파일을 찾아 로드
            base_name = os.path.splitext(os.path.basename(json_path))[0]
            directory = os.path.dirname(json_path)
            possible_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif"]
            image_path = None

            for ext in possible_extensions:
                image_path = os.path.join(directory, f"{base_name}{ext}")
                if os.path.exists(image_path):
                    break
            else:
                image_path = None

            if image_path:
                self.image_path = image_path
                self.original_image = Image.open(self.image_path)
                self.update_image()  # Canvas 크기와 이미지를 동기화
            else:
                messagebox.showwarning("Image Missing", "The corresponding image file could not be found with common extensions (.png, .jpg, .jpeg, .bmp, .gif).")

            # Listbox와 Canvas 업데이트
            self.update_label_listbox()
            self.assign_parent_child_relationship()  # JSON 로드 후 관계 설정
            self.update_canvas()

            messagebox.showinfo("Load Complete", "JSON file loaded successfully and is ready for editing.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load JSON file: {e}")




    def prompt_multiline_text(self, title="Input", initial_text=""):
            dialog = MultiLineInputDialog(self.root, title, initial_text)
            return dialog.show()

    def toggle_direction(self):
        selected_index = self.label_listbox.curselection()
        if not selected_index:
            messagebox.showinfo("Info", "방향을 변경할 연결을 선택하세요.")
            return

        selected_index = selected_index[0]
        if selected_index >= len(self.nodes):  # 연결만 선택되었는지 확인
            connection_index = selected_index - len(self.nodes)
            
            # `direction` 필드를 토글
            if 0 <= connection_index < len(self.connections):
                self.connections[connection_index]['direction'] = not self.connections[connection_index]['direction']
                
                # 리스트박스 업데이트
                from_id = self.connections[connection_index]['from']
                to_id = self.connections[connection_index]['to']
                text = self.connections[connection_index]['text'] or ""
                connection_type = self.connections[connection_index]['type'] or ""
                direction_icon = "→" if self.connections[connection_index]['direction'] else "-"
                display_text = f"Connection: {from_id} {direction_icon} {to_id} ({text}) [Type: {connection_type}]"
                self.label_listbox.delete(selected_index)
                self.label_listbox.insert(selected_index, display_text)
             
            
            self.update_canvas()



    def zoom(self, event):
        # 확대/축소 비율 계산
        if event.delta > 0:  # 마우스 휠 업 -> 확대
            self.scale_factor += self.zoom_step
        elif event.delta < 0:  # 마우스 휠 다운 -> 축소
            self.scale_factor = max(0.1, self.scale_factor - self.zoom_step)  # 축소 한계 설정
        
        self.update_canvas()

    def move_image(self, dx, dy):
    # """Move the image by (dx, dy) without affecting other items on the canvas."""
        self.img_x += dx
        self.img_y += dy
        self.update_canvas()

    # 창을 닫을 때 동작
    def on_closing(self):
        if messagebox.askokcancel("Quit", "정말 종료하시겠습니까?"):
            self.root.destroy()

    # 투명도 조절 메소드
    def adjust_opacity(self, event=None):
        if self.original_image:
            alpha = self.opacity_slider.get()
            self.image = self.original_image.copy().convert("RGBA")
            alpha_image = Image.new("L", self.image.size, alpha)
            self.image.putalpha(alpha_image)
            self.tk_image = ImageTk.PhotoImage(self.image)
            self.update_canvas()

    # 오른쪽 클릭으로 노드 이동 시작
    def on_right_click(self, event):
        clicked_node = self.get_node_at(event.x, event.y)
        if clicked_node is not None:
            self.selected_item_index = clicked_node
            self.update_canvas()
            self.dragging = True
            self.drag_data = {"x": event.x, "y": event.y}

    # 오른쪽 클릭 드래그로 노드 이동
    def on_node_drag(self, event):
        if self.dragging and self.selected_item_index is not None:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            node = self.nodes[self.selected_item_index]
            x1, y1, x2, y2 = node['coords']
            new_coords = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
            node['coords'] = new_coords
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            self.update_canvas()

    # 드래그 종료
    def end_node_drag(self, event):
        self.dragging = False
        self.assign_parent_child_relationship()  # 관계 재설정 호출
        self.update_canvas()

    def load_image(self):
        self.image_path = filedialog.askopenfilename()
        if self.image_path:
            # 새로운 이미지를 불러오면 기존 데이터 초기화
            self.nodes.clear()
            self.connections.clear()
            self.label_listbox.delete(0, tk.END)
            self.selected_item_index = None

            # 이미지 불러오기
            self.original_image = Image.open(self.image_path)

            # PNG의 알파 채널을 올바르게 처리하기 위한 설정
            if self.original_image.mode == "RGBA":
                # 투명한 부분을 흰색 배경으로 변경하여 알파 채널 문제 해결
                background = Image.new("RGB", self.original_image.size, (255, 255, 255))
                background.paste(self.original_image, mask=self.original_image.split()[3])  # 알파 채널 마스크
                self.original_image = background  # 알파 채널이 제거된 이미지로 설정
            else:
                self.original_image = self.original_image.convert("RGB")

            self.update_image()


    def update_image(self):
        if self.original_image:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if self.keep_aspect_ratio.get():
                # 이미지 비율을 유지하면서 캔버스 크기에 맞게 리사이징
                img_width, img_height = self.original_image.size
                scale = min(canvas_width / img_width, canvas_height / img_height)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
            else:
                # 이미지 비율을 무시하고 창 크기에 맞춤
                new_width, new_height = canvas_width, canvas_height

            # 이미지를 새 크기로 리사이즈
            resized_image = self.original_image.resize((new_width, new_height), Image.LANCZOS)

            self.image = resized_image
            self.tk_image = ImageTk.PhotoImage(self.image)

            self.canvas.delete("all")
            self.update_canvas()

            self.draw = ImageDraw.Draw(self.image)
            self.adjust_opacity()

    def on_resize(self, event):
        if self.original_image:
            # 캔버스의 크기를 새로 가져옴
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
    
            # 이미지 및 도형의 스케일링 비율 계산
            self.scale_x = canvas_width / self.canvas_width if self.canvas_width != 0 else 1
            self.scale_y = canvas_height / self.canvas_height if self.canvas_height != 0 else 1
    
            # 이미지 업데이트 (리사이즈)
            self.update_image()
    
            # 현재 캔버스 크기 저장
            self.canvas_width = canvas_width
            self.canvas_height = canvas_height

    def update_label_listbox(self):
        self.label_listbox.delete(0, tk.END)

        # 노드를 리스트 박스에 추가
        for node in self.nodes:
            self.label_listbox.insert(tk.END, f"Node({node['id']}): {node['text']}")

        # 연결을 리스트 박스에 추가
        for connection in self.connections:
            from_id = connection['from']
            to_id = connection['to']
            direction_icon = "→" if connection['direction'] else "-"
            text = connection['text'] or ""
            connection_type = connection['type']
            display_text = f"Connection({connection['id']}): {from_id} {direction_icon} {to_id} ({text}) [Type: {connection_type}]"
            self.label_listbox.insert(tk.END, display_text)


    def update_canvas(self):
        """캔버스에 이미지, 노드, 연결을 갱신하여 표시."""
        self.assign_parent_child_relationship()  # 관계 재설정 호출
        self.canvas.delete("all")
        if self.tk_image:
            img_width, img_height = int(self.image.width * self.scale_factor), int(self.image.height * self.scale_factor)
            resized_image = self.image.resize((img_width, img_height), Image.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(resized_image)
            self.canvas.create_image(self.img_x, self.img_y, anchor=tk.NW, image=self.tk_image)

        # 노드 그리기
        for i, node_info in enumerate(self.nodes):
            x1, y1, x2, y2 = node_info['coords']
            scaled_coords = (
                self.img_x + x1 * self.scale_factor,
                self.img_y + y1 * self.scale_factor,
                self.img_x + x2 * self.scale_factor,
                self.img_y + y2 * self.scale_factor
            )
            outline_color = "yellow" if i == self.selected_node_index else "red"
            width = 4 if i == self.selected_node_index else 3
            self.canvas.create_rectangle(scaled_coords, outline=outline_color, width=width)
            self.canvas.create_text(
                (scaled_coords[0] + scaled_coords[2]) / 2,
                (scaled_coords[1] + scaled_coords[3]) / 2,
                text=node_info["text"],
                font=("Arial", 12)
            )

        # 연결 그리기
        for i, connection in enumerate(self.connections):
            from_node = next((node for node in self.nodes if node['id'] == connection['from']), None)
            to_node = next((node for node in self.nodes if node['id'] == connection['to']), None)
            if not from_node or not to_node:
                continue

            from_center = self.get_center(from_node['coords'])
            to_center = self.get_center(to_node['coords'])
            scaled_from_center = (
                self.img_x + from_center[0] * self.scale_factor,
                self.img_y + from_center[1] * self.scale_factor
            )
            scaled_to_center = (
                self.img_x + to_center[0] * self.scale_factor,
                self.img_y + to_center[1] * self.scale_factor
            )

            line_dash = (6, 2) if connection['type'] == "dashed" else (2, 1) if connection['type'] == "dotted" else ()
            is_selected = i == self.selected_connection_index
            line_color = connection['color']
            width = 4 if is_selected else 2
            line_color = "yellow" if is_selected else line_color

             # 화살표 여부 결정
            arrow_option = tk.LAST if connection.get('direction', True) else None

            # Draw connections with the selected color
            self.canvas.create_line(
                scaled_from_center,
                scaled_to_center,
                arrow=arrow_option,
                fill=line_color,
                width=width,
                dash=line_dash if line_dash else None
            )

            if connection['text']:
                mid_x = (scaled_from_center[0] + scaled_to_center[0]) / 2
                mid_y = (scaled_from_center[1] + scaled_to_center[1]) / 2
                self.canvas.create_text(mid_x, mid_y, text=connection['text'], fill="blue", font=("Arial", 12))


    def get_center(self, coords):
        x1, y1, x2, y2 = coords
        return (x1 + x2) // 2, (y1 + y2) // 2

    def save_image(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".png")
        if save_path and self.image:
            self.image.save(save_path)

    
    def save_nodes_as_json(self, event=None):
        if self.image_path:
            # 이미지 파일명에서 확장자를 제거한 기본 이름 가져오기
            base_name = os.path.splitext(os.path.basename(self.image_path))[0]
            json_path = os.path.join(os.path.dirname(self.image_path), f"{base_name}.json")

            # 중첩된 노드 구조 생성
            def build_hierarchy(nodes):
                node_dict = {node['id']: node for node in nodes}
                for node in nodes:
                    node["node"] = []
                for node in nodes:
                    if node["parent_id"]:
                        parent_node = node_dict.get(node["parent_id"])
                        if parent_node:
                            parent_node["node"].append(node)
                return [node for node in nodes if node["parent_id"] is None]

            nested_nodes = build_hierarchy(self.nodes)

            # JSON 데이터 생성
            data = {
                "file_name": os.path.basename(self.image_path),  # 현재 이미지 파일명
                "node_count": len(self.nodes),                  # node 개수
                "connection_count": len(self.connections),      # connection 개수
                "components": nested_nodes,
                "connections": self.connections                 # color is automatically included in connections
            }

            # JSON 데이터 저장
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            messagebox.showinfo("Save JSON", f"JSON 파일이 다음 경로에 저장되었습니다: {json_path}")
        else:
            messagebox.showwarning("Save Error", "먼저 이미지를 불러오세요.")




    def delete_selected(self):
        selected_index = self.label_listbox.curselection()
        if not selected_index:
            messagebox.showinfo("Info", "삭제할 항목을 선택하세요.")
            return

        selected_index = selected_index[0]
        item_text = self.label_listbox.get(selected_index)

        # 선택한 항목이 노드인지 연결인지 확인
        if item_text.startswith("Node("):
            # 노드를 삭제
            node_index = selected_index
            if node_index < len(self.nodes):  # 인덱스가 범위 내에 있는지 확인
                node_id = self.nodes[node_index]["id"]
                
                # 관련된 모든 연결 삭제
                self.connections = [conn for conn in self.connections if conn['from'] != node_id and conn['to'] != node_id]
                self.nodes.pop(node_index)
                self.label_listbox.delete(0, tk.END)
                self.update_label_listbox()
            else:
                messagebox.showerror("Error", "선택한 노드를 삭제할 수 없습니다.")
        elif item_text.startswith("Connection("):
            # 연결을 삭제
            connection_index = selected_index - len(self.nodes)
            if 0 <= connection_index < len(self.connections):  # 인덱스가 범위 내에 있는지 확인
                self.connections.pop(connection_index)
                self.label_listbox.delete(0, tk.END)
                self.update_label_listbox()
            else:
                messagebox.showerror("Error", "선택한 연결을 삭제할 수 없습니다.")

        self.update_canvas()



    def edit_selected(self):
        selected_index = self.label_listbox.curselection()
        if not selected_index:
            messagebox.showinfo("Info", "수정할 항목을 선택하세요.")
            return

        selected_index = selected_index[0]
        item_text = self.label_listbox.get(selected_index)

        if item_text.startswith("Node("):
            # 노드 텍스트 수정
            node_index = selected_index
            new_text = self.prompt_multiline_text("Edit Node Text", initial_text=self.nodes[node_index]['text'])
            if new_text:
                self.nodes[node_index]['text'] = new_text
                self.label_listbox.delete(selected_index)
                self.label_listbox.insert(selected_index, f"Node({self.nodes[node_index]['id']}): {new_text}")

        elif item_text.startswith("Connection("):
            # 연결 텍스트 수정
            connection_index = selected_index - len(self.nodes)
            current_text = self.connections[connection_index]['text'] or ""
            new_text = self.prompt_multiline_text("Edit Connection Text", initial_text=current_text)
            if new_text:
                self.connections[connection_index]['text'] = new_text
                from_id = self.connections[connection_index]['from']
                to_id = self.connections[connection_index]['to']
                direction_icon = "→" if self.connections[connection_index]['direction'] else "-"
                connection_type = self.connections[connection_index]['type']
                display_text = f"Connection({self.connections[connection_index]['id']}): {from_id} {direction_icon} {to_id} ({new_text}) [Type: {connection_type}]"
                self.label_listbox.delete(selected_index)
                self.label_listbox.insert(selected_index, display_text)

        self.update_canvas()



    def get_node_at(self, x, y):
        # 실제 클릭 좌표를 원본 이미지 좌표계로 변환
        original_x = (x - self.img_x) / self.scale_factor
        original_y = (y - self.img_y) / self.scale_factor
        
        for i, node_info in enumerate(self.nodes):
            x1, y1, x2, y2 = node_info['coords']
            # 원본 좌표계에서 클릭한 위치가 노드 안에 있는지 확인
            if x1 <= original_x <= x2 and y1 <= original_y <= y2:
                return i
        return None


    def highlight_node(self, node_index):
        node_info = self.nodes[node_index]
        x1, y1, x2, y2 = node_info['coords']
        
        # 확대/축소 및 이미지 위치를 반영한 좌표로 변환
        scaled_coords = (
            self.img_x + x1 * self.scale_factor,
            self.img_y + y1 * self.scale_factor,
            self.img_x + x2 * self.scale_factor,
            self.img_y + y2 * self.scale_factor
        )
        
        # 변환된 좌표로 사각형 하이라이트 생성
        self.canvas.create_rectangle(
            scaled_coords,
            outline="blue",
            width=3,
            tags="highlight"
        )


    def setup_type_selector(self):
        # 관계 타입 선택 메뉴
        self.type_label = tk.Label(self.right_frame, text="Change Connection Type:")
        self.type_label.pack(pady=(20, 5))
        self.type_options = ["line", "dashed", "dotted", "unknown"]
        self.selected_type = tk.StringVar(value="line")  # 기본값 설정
        self.type_menu = tk.OptionMenu(self.right_frame, self.selected_type, *self.type_options, command=self.update_type)
        self.type_menu.pack()

    def update_type(self, _=None):  # 선택한 옵션을 반영하도록 기본값 매개변수 사용
        selected_index = self.label_listbox.curselection()
        if selected_index:
            selected_index = selected_index[0] - len(self.nodes)  # 관계 인덱스 조정
            if 0 <= selected_index < len(self.connections):
                # 선택된 옵션 메뉴에서 현재 타입을 가져옴
                selected_type = self.selected_type.get()
                
                # 연결의 type을 업데이트
                self.connections[selected_index]["type"] = selected_type
                
                # 리스트박스 업데이트
                self.label_listbox.delete(selected_index + len(self.nodes))
                from_id = self.connections[selected_index]['from']
                to_id = self.connections[selected_index]['to']
                text = self.connections[selected_index]['text'] or ""
                self.label_listbox.insert(selected_index + len(self.nodes), f"Connection: {from_id} → {to_id} ({text}) [Type: {selected_type}]")
                
                # 업데이트 후 화면 다시 그리기
                self.update_canvas()


    # prompt_multiline_text 메서드에서 MultiLineInputDialog를 호출
    def prompt_multiline_text(self, title="Input", initial_text=""):
        dialog = MultiLineInputDialog(self.root, title, initial_text)
        return dialog.show()


    def create_connection(self):
        if self.selected_nodes[0] != self.selected_nodes[1]:
            # MultiLineInputDialog를 사용하여 연결 텍스트 입력
            connection_text = self.prompt_multiline_text("Enter text for this connection (optional):")
            
            # 텍스트가 없을 경우 None으로 설정하고, 그렇지 않으면 JSON-friendly 형식으로 변환
            connection_text_json = connection_text.replace("\n", "\\n") if connection_text else None
            connection_text_display = connection_text if connection_text else ""

            # from_node와 to_node의 id를 가져와서 저장
            from_node_id = self.nodes[self.selected_nodes[0]]['id']
            to_node_id = self.nodes[self.selected_nodes[1]]['id']

            # Set color based on user selection
            color_name = self.selected_color.get()
            connection_color = self.colors[color_name]

            # 관계 정보 저장 (기본 type은 'line')
            connection_type = self.selected_type.get()  # 현재 선택된 타입
            connection_id = str(uuid.uuid4())[:3]  # 고유 id 추가
            self.connections.append({
                'id': connection_id,
                'from': from_node_id,
                'to': to_node_id,
                'text': connection_text_json,  # JSON 저장 시 줄바꿈을 '\n'으로 처리된 텍스트 사용
                'type': connection_type,  # 선택된 type 설정
                'direction': True,  # 기본 값 True로 설정
                'color': connection_color  # Add color attribute
            })

            # 리스트박스에 표시할 텍스트 설정 (화면에는 줄바꿈 그대로 표시)
            display_text = f"Connection({connection_id}): {from_node_id} → {to_node_id} ({connection_text_display}) [Type: {connection_type}] [Color: {color_name}]"
            self.label_listbox.insert(tk.END, display_text)

        # 선택 해제 및 업데이트
        self.selected_nodes = []
        self.canvas.delete("highlight")
        self.update_canvas()




    def on_click(self, event):
        self.start_x = event.x
        self.start_y = event.y
        current_mode = self.mode_var.get()
        
        if current_mode == "connect":
            clicked_node = self.get_node_at(event.x, event.y)
            if clicked_node is not None:
                if len(self.selected_nodes) < 2:
                    self.selected_nodes.append(clicked_node)
                    if len(self.selected_nodes) == 1:
                        self.highlight_node(clicked_node)
                if len(self.selected_nodes) == 2:
                    self.create_connection()
        elif current_mode == "draw":
            clicked_node = self.get_node_at(event.x, event.y)
            
            # 기존 노드 위에서 클릭한 경우 - 노드 크기 조절
            if clicked_node is not None:
                node = self.nodes[clicked_node]
                x1, y1, x2, y2 = node['coords']
                if abs(event.x - x2 * self.scale_factor - self.img_x) < 10 and abs(event.y - y2 * self.scale_factor - self.img_y) < 10:
                    self.resizing = True
                    self.selected_item_index = clicked_node
                else:
                    self.dragging = True  # 드래그 상태 활성화
            
            # 새로운 위치에서 클릭한 경우 - 새 노드 그리기
            else:
                self.dragging = True  # 새 노드 그리기 모드 활성화


    def on_drag(self, event):
        if self.resizing and self.selected_item_index is not None:
            # 노드 크기 조절
            node = self.nodes[self.selected_item_index]
            x1, y1, _, _ = node['coords']
            node['coords'] = (x1, y1, (event.x - self.img_x) / self.scale_factor, (event.y - self.img_y) / self.scale_factor)
            
            self.update_canvas()
        elif self.mode_var.get() == "draw" and self.dragging:
            # 임시 사각형으로 노드 그리기 미리보기
            self.canvas.delete("temp_shape")
            self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline="red", tags="temp_shape"
            )
            


    def on_motion(self, event):
        original_x = event.x
        original_y = event.y

        # 변환된 좌표를 사용하여 마우스 위치에 있는 노드 찾기
        hovered_node_index = self.get_node_at(original_x, original_y)

        # 현재 하이라이트된 노드와 다르면 업데이트
        if self.selected_item_index is None or hovered_node_index != self.selected_item_index:
            self.selected_item_index = hovered_node_index
            self.update_canvas()  # 하이라이트 업데이트를 위해 캔버스 다시 그림


     # Update where text input is required
    def on_release(self, event):
        if self.resizing:
            self.resizing = False
        elif self.mode_var.get() == "draw" and self.dragging:
            if abs(event.x - self.start_x) > 5 and abs(event.y - self.start_y) > 5:
                self.canvas.delete("temp_shape")

                # 새로운 노드 좌표 계산
                original_x1 = (self.start_x - self.img_x) / self.scale_factor
                original_y1 = (self.start_y - self.img_y) / self.scale_factor
                original_x2 = (event.x - self.img_x) / self.scale_factor
                original_y2 = (event.y - self.img_y) / self.scale_factor

                # 텍스트 입력 대화상자 열기
                text = self.prompt_multiline_text("Enter Text for Node")
                if text:
                    node_id = str(uuid.uuid4())[:3]
                    node_info = {
                        "id": node_id,
                        "coords": (original_x1, original_y1, original_x2, original_y2),
                        "text": text,
                        "parent_id": None
                    }
                    self.nodes.append(node_info)
                    self.label_listbox.insert(tk.END, f"Node({node_id}): {text}")

                    # Listbox와 노드 상태 일관성 유지
                    self.label_listbox.selection_clear(0, tk.END)
                    self.label_listbox.selection_set(tk.END)
                    self.selected_item_index = len(self.nodes) - 1

                    self.update_canvas()

        self.dragging = False
        self.start_x = None
        self.start_y = None



    # get_enclosed_nodes 메서드
    def get_enclosed_nodes(self, x1, y1, x2, y2):
        """지정된 좌표 범위 내에 있는 노드들을 찾습니다."""
        enclosed_nodes = []
        for node in self.nodes:
            nx1, ny1, nx2, ny2 = node["coords"]
            if x1 <= nx1 <= x2 and y1 <= ny1 <= y2 and x1 <= nx2 <= x2 and y1 <= ny2 <= y2:
                enclosed_nodes.append(node)
        return enclosed_nodes



if __name__ == "__main__":
    root = tk.Tk()
    # 전체화면 모드 설정
    root.attributes("-fullscreen", True)

    app = ImageEditor(root)
    root.mainloop()