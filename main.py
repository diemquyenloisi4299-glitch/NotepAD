import flet as ft
import traceback

def main(page: ft.Page):
    try:
        page.title = "Quick Copy & Note App"
        page.padding = 10
        
        # ==========================================
        # 1. TẢI VÀ QUẢN LÝ DỮ LIỆU BẰNG HỆ THỐNG NATIVE
        # ==========================================
        app_data = page.client_storage.get("quick_note_data")
        
        if not app_data:
            app_data = {
                "theme": "dark",
                "pages": [
                    {
                        "title": "Trang 1",
                        "rows": [{"label": f"Note {i+1}", "content": f"Nội dung {i+1}"} for i in range(10)]
                    }
                ]
            }

        def save_data():
            page.client_storage.set("quick_note_data", app_data)

        page.theme_mode = ft.ThemeMode.DARK if app_data.get("theme") == "dark" else ft.ThemeMode.LIGHT
        is_delete_mode = False

        # ==========================================
        # 2. CÁC HỘP THOẠI XÁC NHẬN
        # ==========================================
        page_to_delete_idx = -1
        def open_delete_page_dialog(idx):
            nonlocal page_to_delete_idx
            page_to_delete_idx = idx
            page.dialog = delete_page_dialog
            delete_page_dialog.open = True
            page.update()

        def confirm_delete_page(e):
            if 0 <= page_to_delete_idx < len(app_data["pages"]):
                app_data["pages"].pop(page_to_delete_idx)
                for i, p in enumerate(app_data["pages"]):
                    p["title"] = f"Trang {i+1}"
                save_data()
                render_all_pages()
                
                if tabs.selected_index >= len(app_data["pages"]):
                    tabs.selected_index = max(0, len(app_data["pages"]) - 1)
            delete_page_dialog.open = False
            page.update()

        delete_page_dialog = ft.AlertDialog(
            title=ft.Text("Xóa Trang", color=ft.Colors.RED_400),
            content=ft.Text("Xóa TOÀN BỘ trang này cùng các ghi chú bên trong?"),
            actions=[
                ft.TextButton("Hủy", on_click=lambda e: (setattr(delete_page_dialog, 'open', False), page.update())),
                ft.TextButton("Xóa", on_click=confirm_delete_page, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ]
        )

        def confirm_delete_row(e):
            nonlocal is_delete_mode
            p_idx = tabs.selected_index or 0
            lv = tabs.tabs[p_idx].content.content
            
            to_delete = []
            for ctrl in lv.controls:
                cb = ctrl.controls[0]
                if isinstance(cb, ft.Checkbox) and cb.value:
                    to_delete.append(cb.data)
            
            for r_idx in sorted(to_delete, reverse=True):
                app_data["pages"][p_idx]["rows"].pop(r_idx)
            
            confirm_row_dialog.open = False
            is_delete_mode = False
            delete_btn.icon = ft.Icons.DELETE
            delete_btn.icon_color = None
            save_data()
            render_rows()

        confirm_row_dialog = ft.AlertDialog(
            title=ft.Text("Xóa Ghi Chú"),
            content=ft.Text("Bạn có chắc chắn muốn xóa các dòng đã chọn?"),
            actions=[
                ft.TextButton("Hủy", on_click=lambda e: (setattr(confirm_row_dialog, 'open', False), page.update())),
                ft.TextButton("Xóa", on_click=confirm_delete_row, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ]
        )

        # ==========================================
        # 3. RENDER GIAO DIỆN (UI) TỪ DATA
        # ==========================================
        tabs = ft.Tabs(animation_duration=300, expand=True, scrollable=True)

        def render_all_pages():
            tabs.tabs.clear()
            for p_idx, p_data in enumerate(app_data["pages"]):
                lv = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
                tab_header = ft.Container(
                    content=ft.Text(p_data["title"]),
                    on_long_press=lambda e, idx=p_idx: open_delete_page_dialog(idx),
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    tooltip="Nhấn giữ để xóa trang"
                )
                new_tab = ft.Tab(tab_content=tab_header, content=ft.Container(content=lv, padding=ft.padding.only(top=15)))
                tabs.tabs.append(new_tab)
            render_rows()

        def render_rows():
            query = search_bar.value.lower() if search_bar.value else ""
            for p_idx, p_data in enumerate(app_data["pages"]):
                if p_idx >= len(tabs.tabs): break
                lv = tabs.tabs[p_idx].content.content
                lv.controls.clear()
                
                for r_idx, r_data in enumerate(p_data["rows"]):
                    if query and query not in r_data["label"].lower() and query not in r_data["content"].lower():
                        continue
                    lv.controls.append(create_row_ui(p_idx, r_idx, r_data))
            page.update()

        def create_row_ui(p_idx, r_idx, r_data):
            checkbox = ft.Checkbox(visible=is_delete_mode, value=False, data=r_idx)
            
            def update_label(e, p=p_idx, r=r_idx):
                app_data["pages"][p]["rows"][r]["label"] = e.control.value
                save_data()
                
            def update_content(e, p=p_idx, r=r_idx):
                app_data["pages"][p]["rows"][r]["content"] = e.control.value
                save_data()

            label_field = ft.TextField(
                value=r_data["label"], text_size=12, dense=True, width=80, border_radius=8,
                on_change=update_label
            )
            content_field = ft.TextField(
                value=r_data["content"], text_size=13, dense=True, expand=True, border_radius=8, read_only=True,
                on_change=update_content
            )

            def copy_content(e, text=r_data["content"]):
                if content_field.read_only and text:
                    page.set_clipboard(str(text))
                    page.snack_bar = ft.SnackBar(content=ft.Text(f"Đã copy: {text}"))
                    page.snack_bar.open = True
                    page.update()
            content_field.on_focus = copy_content

            def toggle_edit(e):
                btn = e.control
                if content_field.read_only:
                    content_field.read_only = False
                    content_field.border_color = ft.Colors.GREEN
                    btn.icon = ft.Icons.CHECK
                    btn.tooltip = "Lưu"
                    page.update()
                    content_field.focus()
                else:
                    content_field.read_only = True
                    content_field.border_color = None
                    btn.icon = ft.Icons.EDIT
                    btn.tooltip = "Sửa"
                    page.update()
                    
            edit_btn = ft.IconButton(icon=ft.Icons.EDIT, icon_size=16, tooltip="Sửa", on_click=toggle_edit)

            return ft.Row(
                controls=[checkbox, label_field, content_field, edit_btn],
                alignment=ft.MainAxisAlignment.CENTER, spacing=4
            )

        # ==========================================
        # 4. THANH CÔNG CỤ
        # ==========================================
        def toggle_theme(e):
            if page.theme_mode == ft.ThemeMode.DARK:
                page.theme_mode = ft.ThemeMode.LIGHT
                theme_btn.icon = ft.Icons.DARK_MODE
                app_data["theme"] = "light"
            else:
                page.theme_mode = ft.ThemeMode.DARK
                theme_btn.icon = ft.Icons.LIGHT_MODE
                app_data["theme"] = "dark"
            save_data()
            page.update()

        theme_btn = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.DARK_MODE, 
            on_click=toggle_theme, tooltip="Đổi Sáng/Tối"
        )

        search_bar = ft.TextField(
            hint_text="Tìm nhanh...", prefix_icon=ft.Icons.SEARCH, height=35, text_size=13, 
            expand=True, content_padding=ft.padding.only(left=10, right=10, top=5, bottom=5),
            border_radius=20, on_change=lambda e: render_rows()
        )

        def add_new_page(e):
            new_idx = len(app_data["pages"]) + 1
            app_data["pages"].append({
                "title": f"Trang {new_idx}",
                "rows": [{"label": f"Note {i+1}", "content": f"Nội dung {i+1}"} for i in range(5)]
            })
            save_data()
            render_all_pages()
            tabs.selected_index = len(app_data["pages"]) - 1
            page.update()

        def add_row_to_current_page(e):
            p_idx = tabs.selected_index or 0
            if p_idx < len(app_data["pages"]):
                new_row_idx = len(app_data["pages"][p_idx]["rows"]) + 1
                app_data["pages"][p_idx]["rows"].append({
                    "label": f"Note {new_row_idx}", "content": "Nội dung mới"
                })
                save_data()
                render_rows()

        def toggle_delete_mode(e):
            nonlocal is_delete_mode
            if not is_delete_mode:
                is_delete_mode = True
                delete_btn.icon = ft.Icons.CHECK_BOX
                delete_btn.icon_color = ft.Colors.RED_400
                render_rows()
            else:
                p_idx = tabs.selected_index or 0
                lv = tabs.tabs[p_idx].content.content
                checked = any(ctrl.controls[0].value for ctrl in lv.controls if isinstance(ctrl.controls[0], ft.Checkbox))
                if checked:
                    page.dialog = confirm_row_dialog
                    confirm_row_dialog.open = True
                    page.update()
                else:
                    is_delete_mode = False
                    delete_btn.icon = ft.Icons.DELETE
                    delete_btn.icon_color = None
                    render_rows()

        add_page_btn = ft.IconButton(icon=ft.Icons.LIBRARY_ADD, icon_color=ft.Colors.GREEN_400, on_click=add_new_page, tooltip="Thêm Trang")
        add_row_btn = ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.BLUE_400, on_click=add_row_to_current_page, tooltip="Thêm Dòng")
        delete_btn = ft.IconButton(icon=ft.Icons.DELETE, on_click=toggle_delete_mode, tooltip="Xóa Dòng")

        def handle_tab_change(e):
            nonlocal is_delete_mode
            delete_btn.icon = ft.Icons.DELETE
            delete_btn.icon_color = None
            is_delete_mode = False
            render_rows()

        tabs.on_change = handle_tab_change

        header_row = ft.Row([
            search_bar,
            ft.Row([add_page_btn, add_row_btn, delete_btn, theme_btn], spacing=0)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # ==========================================
        # 5. HIỂN THỊ LÊN MÀN HÌNH
        # ==========================================
        render_all_pages()
        
        page.add(
            header_row,
            ft.Divider(height=1, color=ft.Colors.WHITE24),
            tabs
        )

    # KHỐI BẮT LỖI TỰ ĐỘNG
    except Exception as e:
        page.scroll = ft.ScrollMode.AUTO
        page.add(
            ft.Text("⚠️ CÓ LỖI XẢY RA, HÃY CHỤP MÀN HÌNH NÀY:", color="red", weight="bold"),
            ft.Text(traceback.format_exc(), selectable=True, size=12)
        )
        page.update()

if __name__ == "__main__":
    ft.app(target=main)
