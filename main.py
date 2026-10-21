import flet as ft
import traceback
import json


STORAGE_KEY = "quick_note_data"


def make_default_data():
    return {
        "theme": "dark",
        "pages": [
            {
                "title": "Trang 1",
                "rows": [
                    {"label": f"Note {i + 1}", "content": f"Nội dung {i + 1}"}
                    for i in range(10)
                ],
            }
        ],
    }

async def main(page: ft.Page):
    try:
        page.title = "Quick Copy & Note App"
        # Chỉ tăng khoảng trống phía trên; giữ nguyên giao diện gốc, không thêm logo/tiêu đề mới.
        page.padding = ft.Padding.only(left=10, top=40, right=10, bottom=10)

        # Flet 1.x sử dụng service bất đồng bộ thay cho page.client_storage
        prefs = ft.SharedPreferences()
        clipboard = ft.Clipboard()

        stored_value = await prefs.get(STORAGE_KEY)
        try:
            if isinstance(stored_value, str):
                app_data = json.loads(stored_value) if stored_value else None
            elif isinstance(stored_value, dict):
                # Tương thích nếu dữ liệu cũ đã được lưu ở dạng dict.
                app_data = stored_value
            else:
                app_data = None
        except (TypeError, json.JSONDecodeError):
            app_data = None

        if (
            not isinstance(app_data, dict)
            or not isinstance(app_data.get("pages"), list)
            or len(app_data.get("pages", [])) == 0
        ):
            app_data = make_default_data()

        async def save_data():
            # SharedPreferences hỗ trợ string/list/number/bool, vì vậy lưu dict thành JSON.
            await prefs.set(
                STORAGE_KEY,
                json.dumps(app_data, ensure_ascii=False),
            )

        page.theme_mode = (
            ft.ThemeMode.DARK
            if app_data.get("theme", "dark") == "dark"
            else ft.ThemeMode.LIGHT
        )
        is_delete_mode = False
        page_to_delete_idx = -1

        # ==========================================
        # 1. CẤU TRÚC TABS MỚI CỦA FLET 1.x
        # ==========================================
        page_columns = []
        tab_bar = ft.TabBar(tabs=[ft.Tab(label="Trang 1")], scrollable=True)
        tab_bar_view = ft.TabBarView(
            controls=[ft.Container(content=ft.Column())], expand=True
        )
        tabs = ft.Tabs(
            length=1,
            selected_index=0,
            animation_duration=300,
            expand=True,
            content=ft.Column(
                controls=[tab_bar, tab_bar_view],
                expand=True,
                spacing=0,
            ),
        )

        # Thanh công cụ và các callback được tạo trước khi render trang.
        search_bar = ft.TextField(
            hint_text="Tìm nhanh...",
            prefix_icon=ft.Icons.SEARCH,
            height=35,
            text_size=13,
            expand=True,
            border=ft.OutlineInputBorder(border_radius=20),
            on_change=lambda e: render_rows(),
        )

        def open_delete_page_dialog(idx):
            nonlocal page_to_delete_idx
            page_to_delete_idx = idx
            page.show_dialog(delete_page_dialog)

        def cancel_delete_page(e):
            page.pop_dialog()

        async def confirm_delete_page(e):
            if 0 <= page_to_delete_idx < len(app_data["pages"]):
                deleted_index = page_to_delete_idx
                app_data["pages"].pop(deleted_index)

                # Luôn giữ ít nhất một trang để Tabs không ở trạng thái rỗng.
                if not app_data["pages"]:
                    app_data["pages"].append({"title": "Trang 1", "rows": []})

                for i, page_data in enumerate(app_data["pages"]):
                    page_data["title"] = f"Trang {i + 1}"

                await save_data()
                page.pop_dialog()
                new_selected_index = min(deleted_index, len(app_data["pages"]) - 1)
                render_all_pages(selected_index=new_selected_index)
            else:
                page.pop_dialog()

        delete_page_dialog = ft.AlertDialog(
            title=ft.Text("Xóa Trang", color=ft.Colors.RED_400),
            content=ft.Text("Xóa TOÀN BỘ trang này cùng các ghi chú bên trong?"),
            actions=[
                ft.TextButton("Hủy", on_click=cancel_delete_page),
                ft.TextButton(
                    "Xóa",
                    on_click=confirm_delete_page,
                    style=ft.ButtonStyle(color=ft.Colors.RED),
                ),
            ],
        )

        def cancel_delete_row(e):
            page.pop_dialog()

        async def confirm_delete_row(e):
            nonlocal is_delete_mode
            p_idx = tabs.selected_index
            if not (0 <= p_idx < len(page_columns)):
                page.pop_dialog()
                return

            lv = page_columns[p_idx]
            to_delete = []
            for row_control in lv.controls:
                if row_control.controls and isinstance(row_control.controls[0], ft.Checkbox):
                    checkbox = row_control.controls[0]
                    if checkbox.value:
                        to_delete.append(checkbox.data)

            for row_idx in sorted(to_delete, reverse=True):
                if 0 <= row_idx < len(app_data["pages"][p_idx]["rows"]):
                    app_data["pages"][p_idx]["rows"].pop(row_idx)

            page.pop_dialog()
            is_delete_mode = False
            delete_btn.icon = ft.Icons.DELETE
            delete_btn.icon_color = None
            await save_data()
            render_rows()

        confirm_row_dialog = ft.AlertDialog(
            title=ft.Text("Xóa Ghi Chú"),
            content=ft.Text("Bạn có chắc chắn muốn xóa các dòng đã chọn?"),
            actions=[
                ft.TextButton("Hủy", on_click=cancel_delete_row),
                ft.TextButton(
                    "Xóa",
                    on_click=confirm_delete_row,
                    style=ft.ButtonStyle(color=ft.Colors.RED),
                ),
            ],
        )

        # ==========================================
        # 2. RENDER GIAO DIỆN TỪ DATA
        # ==========================================
        def render_all_pages(selected_index=None):
            current_index = (
                tabs.selected_index if selected_index is None else selected_index
            )

            page_columns.clear()
            tab_bar.tabs.clear()
            tab_bar_view.controls.clear()

            if not app_data["pages"]:
                app_data["pages"].append({"title": "Trang 1", "rows": []})

            for p_idx, page_data in enumerate(app_data["pages"]):
                lv = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
                page_columns.append(lv)

                tab_header = ft.Container(
                    content=ft.Text(page_data.get("title", f"Trang {p_idx + 1}")),
                    on_long_press=lambda e, idx=p_idx: open_delete_page_dialog(idx),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                    tooltip="Nhấn giữ để xóa trang",
                )
                tab_bar.tabs.append(ft.Tab(label=tab_header))
                tab_bar_view.controls.append(
                    ft.Container(
                        content=lv,
                        padding=ft.Padding.only(top=15),
                    )
                )

            # Flet 1.x yêu cầu length bằng số tab và số view.
            tabs.length = len(tab_bar.tabs)
            tabs.selected_index = max(0, min(current_index, tabs.length - 1))
            render_rows()

        def render_rows():
            query = (search_bar.value or "").lower()
            for p_idx, page_data in enumerate(app_data["pages"]):
                if p_idx >= len(page_columns):
                    break
                lv = page_columns[p_idx]
                lv.controls.clear()

                for row_idx, row_data in enumerate(page_data["rows"]):
                    label = str(row_data.get("label", ""))
                    content = str(row_data.get("content", ""))
                    if query and query not in label.lower() and query not in content.lower():
                        continue
                    lv.controls.append(create_row_ui(p_idx, row_idx, row_data))

        def create_row_ui(p_idx, row_idx, row_data):
            checkbox = ft.Checkbox(visible=is_delete_mode, value=False, data=row_idx)

            async def update_label(e, p=p_idx, r=row_idx):
                app_data["pages"][p]["rows"][r]["label"] = e.control.value
                await save_data()

            async def update_content(e, p=p_idx, r=row_idx):
                app_data["pages"][p]["rows"][r]["content"] = e.control.value
                await save_data()

            label_field = ft.TextField(
                value=row_data.get("label", ""),
                text_size=12,
                width=80,
                border=ft.OutlineInputBorder(border_radius=8),
                on_change=update_label,
            )
            content_field = ft.TextField(
                value=row_data.get("content", ""),
                text_size=13,
                expand=True,
                read_only=True,
                border=ft.OutlineInputBorder(border_radius=8),
                on_change=update_content,
            )

            async def copy_content(e):
                current_text = content_field.value or ""
                if content_field.read_only and current_text:
                    await clipboard.set(str(current_text))
                    page.show_dialog(
                        ft.SnackBar(content=ft.Text(f"Đã copy: {current_text}"))
                    )

            content_field.on_focus = copy_content

            async def toggle_edit(e):
                btn = e.control
                if content_field.read_only:
                    content_field.read_only = False
                    content_field.border = ft.OutlineInputBorder(
                        border_radius=8,
                        side=ft.BorderSide(color=ft.Colors.GREEN),
                    )
                    btn.icon = ft.Icons.CHECK
                    btn.tooltip = "Lưu"
                    page.update()
                    await content_field.focus()
                else:
                    app_data["pages"][p_idx]["rows"][row_idx]["content"] = (
                        content_field.value or ""
                    )
                    await save_data()
                    content_field.read_only = True
                    content_field.border = ft.OutlineInputBorder(border_radius=8)
                    btn.icon = ft.Icons.EDIT
                    btn.tooltip = "Sửa"
                    page.update()

            edit_btn = ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_size=16,
                tooltip="Sửa",
                on_click=toggle_edit,
            )

            return ft.Row(
                controls=[checkbox, label_field, content_field, edit_btn],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            )

        # ==========================================
        # 3. THANH CÔNG CỤ
        # ==========================================
        async def toggle_theme(e):
            if page.theme_mode == ft.ThemeMode.DARK:
                page.theme_mode = ft.ThemeMode.LIGHT
                theme_btn.icon = ft.Icons.DARK_MODE
                app_data["theme"] = "light"
            else:
                page.theme_mode = ft.ThemeMode.DARK
                theme_btn.icon = ft.Icons.LIGHT_MODE
                app_data["theme"] = "dark"
            await save_data()
            page.update()

        theme_btn = ft.IconButton(
            icon=(
                ft.Icons.LIGHT_MODE
                if page.theme_mode == ft.ThemeMode.DARK
                else ft.Icons.DARK_MODE
            ),
            on_click=toggle_theme,
            tooltip="Đổi Sáng/Tối",
        )

        async def add_new_page(e):
            new_idx = len(app_data["pages"]) + 1
            app_data["pages"].append(
                {
                    "title": f"Trang {new_idx}",
                    "rows": [
                        {"label": f"Note {i + 1}", "content": f"Nội dung {i + 1}"}
                        for i in range(5)
                    ],
                }
            )
            await save_data()
            render_all_pages(selected_index=len(app_data["pages"]) - 1)

        async def add_row_to_current_page(e):
            p_idx = tabs.selected_index
            if 0 <= p_idx < len(app_data["pages"]):
                new_row_idx = len(app_data["pages"][p_idx]["rows"]) + 1
                app_data["pages"][p_idx]["rows"].append(
                    {"label": f"Note {new_row_idx}", "content": "Nội dung mới"}
                )
                await save_data()
                render_rows()

        def toggle_delete_mode(e):
            nonlocal is_delete_mode
            if not is_delete_mode:
                is_delete_mode = True
                delete_btn.icon = ft.Icons.CHECK_BOX
                delete_btn.icon_color = ft.Colors.RED_400
                render_rows()
            else:
                p_idx = tabs.selected_index
                if not (0 <= p_idx < len(page_columns)):
                    return
                lv = page_columns[p_idx]
                checked = any(
                    row_control.controls
                    and isinstance(row_control.controls[0], ft.Checkbox)
                    and row_control.controls[0].value
                    for row_control in lv.controls
                )
                if checked:
                    page.show_dialog(confirm_row_dialog)
                else:
                    is_delete_mode = False
                    delete_btn.icon = ft.Icons.DELETE
                    delete_btn.icon_color = None
                    render_rows()

        add_page_btn = ft.IconButton(
            icon=ft.Icons.LIBRARY_ADD,
            icon_color=ft.Colors.GREEN_400,
            on_click=add_new_page,
            tooltip="Thêm Trang",
        )
        add_row_btn = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE,
            icon_color=ft.Colors.BLUE_400,
            on_click=add_row_to_current_page,
            tooltip="Thêm Dòng",
        )
        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE,
            on_click=toggle_delete_mode,
            tooltip="Xóa Dòng",
        )

        def handle_tab_change(e):
            nonlocal is_delete_mode
            delete_btn.icon = ft.Icons.DELETE
            delete_btn.icon_color = None
            is_delete_mode = False
            render_rows()

        tabs.on_change = handle_tab_change

        header_row = ft.Row(
            controls=[
                search_bar,
                ft.Row(
                    controls=[add_page_btn, add_row_btn, delete_btn, theme_btn],
                    spacing=0,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        # ==========================================
        # 4. HIỂN THỊ LÊN MÀN HÌNH
        # ==========================================
        render_all_pages()
        page.add(
            header_row,
            ft.Divider(height=1, color=ft.Colors.WHITE_24),
            tabs,
        )

    except Exception:
        page.scroll = ft.ScrollMode.AUTO
        page.add(
            ft.Text(
                "⚠️ CÓ LỖI XẢY RA, HÃY CHỤP MÀN HÌNH NÀY:",
                color="red",
                weight="bold",
            ),
            ft.Text(traceback.format_exc(), selectable=True, size=12),
        )
        page.update()


if __name__ == "__main__":
    # Flet 1.x: ft.app() đã được thay bằng ft.run().
    ft.run(main)
