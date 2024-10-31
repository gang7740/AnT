import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import json
import uuid

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
        self.opacity_slider.set(255)  # 기본 값 255 (완전히 불투명)
        self.opacity_slider.pack(fill=tk.X)

        # 비율 유지 체크박스 설정
        self.keep_aspect_ratio = tk.BooleanVar(value=True)  # 이미지 비율 유지 여부
        self.aspect_ratio_checkbox = tk.Checkbutton(
            self.top_frame, text="Keep Aspect Ratio", variable=self.keep_aspect_ratio
        )
        self.aspect_ratio_checkbox.pack()

        # 캔버스 설정
        self.canvas = tk.Canvas(self.left_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas_width = 0
        self.canvas_height = 0

        # type_selector 초기화
        self.setup_type_selector()

        # 창 크기 조정 시 이미지 리사이징
        self.canvas.bind("<Configure>", self.on_resize)

        # 메뉴 바 설정
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        file_menu = tk.Menu(menubar)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Image", command=self.load_image)
        file_menu.add_command(label="Save Image", command=self.save_image)
        file_menu.add_command(label="Save Nodes and Connections as JSON", command=self.save_nodes_as_json)

        # 창 닫기 메뉴 추가
        file_menu.add_separator()  # 구분선 추가
        file_menu.add_command(label="Exit", command=self.on_closing)  # 창 닫기 메뉴

        # 창 닫기 처리 (윈도우 기본 닫기 버튼)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 모드 선택 버튼
        self.mode_frame = tk.Frame(self.right_frame)
        self.mode_frame.pack(padx=10, pady=5)
        self.mode_var = tk.StringVar(value="draw")
        self.draw_mode_btn = tk.Radiobutton(self.mode_frame, text="Draw Node", variable=self.mode_var, value="draw")
        self.connect_mode_btn = tk.Radiobutton(self.mode_frame, text="Connect Nodes", variable=self.mode_var, value="connect")
        self.draw_mode_btn.pack(side=tk.LEFT, padx=5)
        self.connect_mode_btn.pack(side=tk.LEFT, padx=5)

        # 노드 목록 박스 설정
        self.label_listbox = tk.Listbox(self.right_frame, width=40, height=20)
        self.label_listbox.pack(padx=10, pady=10)

        # 삭제 버튼 설정
        self.delete_button = tk.Button(self.right_frame, text="Delete Selected", command=self.delete_selected)
        self.delete_button.pack(padx=10, pady=5)

        # 수정 버튼 설정
        self.edit_button = tk.Button(self.right_frame, text="Edit Selected", command=self.edit_selected)
        self.edit_button.pack(padx=10, pady=5)

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

        # 이미지 이동 관련 변수
        self.img_x = 0  # 이미지의 현재 X 위치
        self.img_y = 0  # 이미지의 현재 Y 위치
        self.drag_data = {"x": 0, "y": 0}

        # 이벤트 바인딩
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)  # 오른쪽 클릭으로 노드 이동 시작
        self.canvas.bind("<B3-Motion>", self.on_node_drag)  # 오른쪽 버튼 드래그
        self.canvas.bind("<ButtonRelease-3>", self.end_node_drag)  # 오른쪽 버튼 놓기

        self.opacity_slider.bind("<Motion>", self.adjust_opacity)

        # 기존 화살표 키 이벤트 바인딩을 통합된 함수로 수정
        self.root.bind("<Up>", lambda event: self.move_image(0, -5))
        self.root.bind("<Down>", lambda event: self.move_image(0, 5))
        self.root.bind("<Left>", lambda event: self.move_image(-5, 0))
        self.root.bind("<Right>", lambda event: self.move_image(5, 0))

        # 선택된 항목 하이라이트를 위한 변수 추가
        self.selected_item_index = None

        # 리스트박스에 선택 이벤트 바인딩 추가
        self.label_listbox.bind('<<ListboxSelect>>', self.on_list_select)


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

    def update_canvas(self):
        self.canvas.delete("all")
        self.canvas.create_image(self.img_x, self.img_y, anchor=tk.NW, image=self.tk_image)

        # 노드 그리기
        for i, node_info in enumerate(self.nodes):
            outline_color = "yellow" if i == self.selected_item_index else "red"
            width = 4 if i == self.selected_item_index else 3
            self.canvas.create_rectangle(
                node_info['coords'],
                outline=outline_color,
                width=width
            )

        # 관계 그리기
        for i, connection in enumerate(self.connections):
            from_node = self.nodes[connection['from']]
            to_node = self.nodes[connection['to']]
            self.canvas.create_line(
                self.get_center(from_node['coords']),
                self.get_center(to_node['coords']),
                arrow=tk.LAST,
                fill="black",
                width=1
            )

    def load_image(self):
        image_path = filedialog.askopenfilename()
        if image_path:
            self.original_image = Image.open(image_path).convert("RGBA")
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


    def update_canvas(self):
        self.canvas.delete("all")
        self.canvas.create_image(self.img_x, self.img_y, anchor=tk.NW, image=self.tk_image)

        # 노드 그리기
        for i, node_info in enumerate(self.nodes):
            outline_color = "yellow" if i == self.selected_item_index else "red"
            width = 4 if i == self.selected_item_index else 3
            self.canvas.create_rectangle(
                node_info['coords'],
                outline=outline_color,
                width=width
            )

        # 연결 그리기
        for i, connection in enumerate(self.connections):
            from_node = next((node for node in self.nodes if node['id'] == connection['from']), None)
            to_node = next((node for node in self.nodes if node['id'] == connection['to']), None)

            if from_node and to_node:
                # type에 따른 스타일 설정
                if connection['type'] == "dashed":
                    line_dash = (4, 2)  # 대시 형태로 표현 (길이 6, 간격 4)
                elif connection['type'] == "dotted":
                    line_dash = (2, 1)  # 도트 형태로 표현 (길이 1, 간격 4)
                else:
                    line_dash = ()  # 빈 튜플로 설정해 실선으로 표현

                # 선택된 경우 스타일 강조
                is_selected = (i + len(self.nodes)) == self.selected_item_index
                line_color = "green" if is_selected else "black"
                width = 4 if is_selected else 2

                # 화살표 그리기
                self.canvas.create_line(
                    self.get_center(from_node['coords']),
                    self.get_center(to_node['coords']),
                    arrow=tk.LAST,
                    fill=line_color,
                    width=width,
                    dash=line_dash if line_dash else None  # 스타일 설정 적용
                )

                # 관계 텍스트가 있는 경우 텍스트도 함께 그리기
                if connection['text']:
                    mid_x = (self.get_center(from_node['coords'])[0] + self.get_center(to_node['coords'])[0]) // 2
                    mid_y = (self.get_center(from_node['coords'])[1] + self.get_center(to_node['coords'])[1]) // 2
                    self.canvas.create_text(mid_x, mid_y, text=connection['text'], fill="blue")


            
    def on_list_select(self, event):
        selection = self.label_listbox.curselection()
        
        if selection:
            selected_index = selection[0]
            
            # 노드와 연결 구분을 위한 리스트 아이템 텍스트 확인
            item_text = self.label_listbox.get(selected_index)
            
            if item_text.startswith("Node:"):
                # 노드 인덱스를 설정
                self.selected_item_index = selected_index
            elif item_text.startswith("Relation:"):
                # 관계 인덱스 설정
                connection_index = selected_index - len(self.nodes)
                if 0 <= connection_index < len(self.connections):
                    self.selected_item_index = connection_index + len(self.nodes)  # 관계 인덱스 구분
                else:
                    self.selected_item_index = None
        else:
            self.selected_item_index = None  # 선택 해제

        self.update_canvas()  # 선택 상태 업데이트



    def get_center(self, coords):
        x1, y1, x2, y2 = coords
        return (x1 + x2) // 2, (y1 + y2) // 2

    def save_image(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".png")
        if save_path and self.image:
            self.image.save(save_path)

    def save_nodes_as_json(self):
        save_path = filedialog.asksaveasfilename(defaultextension=".json")
        if save_path:
            unique_nodes = {tuple(node['coords']): node for node in self.nodes}
            unique_connections = {tuple((rel['from'], rel['to'])): rel for rel in self.connections}
            data = {
                'node': list(unique_nodes.values()),
                'connections': list(unique_connections.values())
            }
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

    def delete_selected(self):
        selected_index = self.label_listbox.curselection()
        if not selected_index:
            messagebox.showinfo("Info", "삭제할 항목을 선택하세요.")
            return
    
        selected_index = selected_index[0]
        item_text = self.label_listbox.get(selected_index)
    
        # 선택된 항목이 노드인지 관계인지 확인
        if item_text.startswith("Node:"):
            # 노드의 인덱스를 구하고 nodes에서 삭제
            node_index = selected_index
            del self.nodes[node_index]
    
            # 노드와 관련된 관계들도 삭제
            self.connections = [
                rel for rel in self.connections if rel['from'] != node_index and rel['to'] != node_index
            ]
    
            # Listbox에서 해당 항목 삭제
            self.label_listbox.delete(selected_index)
    
            # 관계 인덱스 업데이트를 위해 남은 노드들에 대한 관계 업데이트
            for rel in self.connections:
                if rel['from'] > node_index:
                    rel['from'] -= 1
                if rel['to'] > node_index:
                    rel['to'] -= 1

        elif item_text.startswith("Relation:"):
            # 관계의 인덱스를 구하고 connections에서 삭제
            relation_index = selected_index - len(self.nodes)
            del self.connections[relation_index]
    
            # Listbox에서 해당 항목 삭제
            self.label_listbox.delete(selected_index)
    
        # 캔버스 업데이트
        self.update_canvas()


    def edit_selected(self):
        selected_index = self.label_listbox.curselection()
        if not selected_index:
            messagebox.showinfo("Info", "수정할 항목을 선택하세요.")
            return

        selected_index = selected_index[0]
        item_text = self.label_listbox.get(selected_index)

        if item_text.startswith("Node:"):
            new_text = simpledialog.askstring("Edit", "새 텍스트를 입력하세요:", initialvalue=item_text[5:])
            if new_text:
                self.nodes[selected_index]['text'] = new_text
                self.label_listbox.delete(selected_index)
                self.label_listbox.insert(selected_index, f"Node: {new_text}")
        elif item_text.startswith("Relation:"):
            messagebox.showinfo("Info", "관계 항목은 수정할 수 없습니다.")

        self.update_canvas()

    def get_node_at(self, x, y):
        for i, node_info in enumerate(self.nodes):
            x1, y1, x2, y2 = node_info['coords']
            if x1 <= x <= x2 and y1 <= y <= y2:
                return i
        return None

    def highlight_node(self, node_index):
        node_info = self.nodes[node_index]
        self.canvas.create_rectangle(
            node_info['coords'],
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
                self.label_listbox.insert(selected_index + len(self.nodes), f"Relation: {from_id} to {to_id} ({text}) [Type: {selected_type}]")
                
                # 업데이트 후 화면 다시 그리기
                self.update_canvas()



    def create_connection(self):
        if self.selected_nodes[0] != self.selected_nodes[1]:
            connection_text = simpledialog.askstring("Input", "Enter text for this connection (optional):")
            if not connection_text:
                connection_text = None  # 입력이 없으면 None으로 설정

            # from_node와 to_node의 id를 가져와서 저장
            from_node_id = self.nodes[self.selected_nodes[0]]['id']
            to_node_id = self.nodes[self.selected_nodes[1]]['id']

            # 관계 정보 저장 (기본 type은 'line')
            connection_type = self.selected_type.get()  # 현재 선택된 타입
            self.connections.append({
                'id': str(uuid.uuid4()),  # 고유 id 추가
                'from': from_node_id,
                'to': to_node_id,
                'text': connection_text,
                'type': connection_type  # 선택된 type 설정
            })

            # 리스트박스에 표시할 텍스트 설정
            display_text = f"Relation: {from_node_id} to {to_node_id} ({connection_text or ''}) [Type: {connection_type}]"
            self.label_listbox.insert(tk.END, display_text)

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
        else:
            self.dragging = True

    def on_drag(self, event):
        if self.mode_var.get() == "draw" and self.dragging:
            self.canvas.delete("temp_shape")
            self.canvas.create_rectangle(
                self.start_x, self.start_y,
                event.x, event.y,
                outline="red",
                tags="temp_shape"
            )

    def on_release(self, event):
        if self.mode_var.get() == "draw" and self.dragging:
            if abs(event.x - self.start_x) > 5 and abs(event.y - self.start_y) > 5:
                self.canvas.delete("temp_shape")
                text = simpledialog.askstring("Input", "텍스트를 입력하세요:")
                if text:
                    node_info = {
                        "id": str(uuid.uuid4()),  # 고유 id 추가
                        "coords": (self.start_x, self.start_y, event.x, event.y),
                        "text": text
                    }
                    self.nodes.append(node_info)
                    self.label_listbox.insert(tk.END, f"Node: {text}")
                    self.update_canvas()

        self.dragging = False
        self.start_x = None
        self.start_y = None
        self.update_canvas()


    def load_image(self):
        image_path = filedialog.askopenfilename()
        if image_path:
            self.original_image = Image.open(image_path).convert("RGBA")
    
            # 이미지 크기에 맞게 캔버스 크기를 조정
            img_width, img_height = self.original_image.size
            self.canvas.config(width=img_width, height=img_height)
    
            # 이미지를 캔버스에 그리기
            self.update_image()


if __name__ == "__main__":
    root = tk.Tk()
    
    # 전체화면 모드 설정
    root.attributes("-fullscreen", True)

    app = ImageEditor(root)
    root.mainloop()