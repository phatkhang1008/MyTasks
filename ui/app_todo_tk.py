import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox
import tkinter as tk

from services.task_service import load_tasks, save_tasks, sort_tasks, fmt_row, parse_dt
from models.task_model import Task

DATE_FMT = "%d-%m-%Y %H:%M"


class TodoApp:

    def __init__(self, root):

        self.root = root
        self.root.title("MyTasks")
        # Bắt event chuột nhấn/nhả để biết người dùng đang thao tác tay
        self.mouse_down = False
        self.root.bind_all(
            "<ButtonPress-1>", lambda e: setattr(self, "mouse_down", True)
        )
        self.root.bind_all(
            "<ButtonRelease-1>", lambda e: setattr(self, "mouse_down", False)
        )
        style = ttk.Style()
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TEntry", font=("Segoe UI", 10))

        self.updating = False
        self.editing_priority = False

        self.tasks = load_tasks()
        sort_tasks(self.tasks)

        # ===== Form =====
        frm = ttk.Frame(root, padding=10)
        frm.pack(fill="x")

        ttk.Label(frm, text="Tiêu đề:").grid(row=0, column=0, sticky="w")
        self.ent_title = ttk.Entry(frm, width=48)
        self.ent_title.grid(row=0, column=1, columnspan=3, sticky="we", padx=6, pady=2)

        ttk.Label(frm, text="Deadline (DD-MM-YYYY HH:MM):").grid(
            row=1, column=0, sticky="w"
        )
        self.ent_deadline = ttk.Entry(frm, width=22)
        self.ent_deadline.grid(row=1, column=1, sticky="w", padx=6, pady=2)

        ttk.Label(frm, text="Ưu tiên:").grid(row=1, column=2, sticky="e")
        self.cmb_priority = ttk.Combobox(
            frm, values=["Cao", "Trung bình", "Thấp"], width=12, state="readonly"
        )
        self.cmb_priority.set("Trung bình")
        self.cmb_priority.grid(row=1, column=3, sticky="w", padx=6, pady=2)

        def on_priority_change(_):
            self.editing_priority = True
            self.root.after(
                300, lambda: setattr(self, "editing_priority", False)
            )  # reset sau 0.3s
            self.cmb_priority.focus_set()

        self.cmb_priority.bind("<<ComboboxSelected>>", on_priority_change)

        ttk.Label(frm, text="Chi tiết/Yêu cầu:").grid(row=2, column=0, sticky="nw")
        self.txt_detail = tk.Text(frm, height=4, width=48)
        self.txt_detail.grid(row=2, column=1, columnspan=3, sticky="we", padx=6, pady=2)

        # ===== Buttons =====

        btns = ttk.Frame(root, padding=(10, 0))
        btns.pack(fill="x")
        ttk.Button(btns, text="Thêm", command=self.add_task, bootstyle="success").pack(
            side="left", padx=4, pady=6
        )
        ttk.Button(
            btns, text="Cập nhật", command=self.update_task, bootstyle="info"
        ).pack(side="left", padx=4)
        ttk.Button(
            btns,
            text="Đánh dấu hoàn thành",
            command=self.mark_done,
            bootstyle="secondary",
        ).pack(side="left", padx=4)
        ttk.Button(btns, text="Xóa", command=self.delete_task, bootstyle="danger").pack(
            side="left", padx=4
        )
        ttk.Button(
            btns, text="Làm mới", command=self.refresh, bootstyle="warning"
        ).pack(side="left", padx=4)

        # ===== Danh sách =====
        listfrm = ttk.Frame(root, padding=(10, 0))
        listfrm.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(listfrm, height=10, activestyle="dotbox")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind_class("Listbox", "<<ListboxSelect>>", self.on_select, add="+")

        sb = ttk.Scrollbar(listfrm, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=sb.set)

        info = ttk.Labelframe(root, text=" Chi tiết", padding=10, bootstyle="info")
        info.pack(fill="x", padx=10, pady=(6, 10))
        self.lbl_info = ttk.Label(
            info, text="Chọn 1 công việc để xem chi tiết…", justify="left"
        )
        self.lbl_info.pack(fill="x")

        self.refresh()

    # ===== CRUD =====
    def add_task(self):
        title = self.ent_title.get().strip()
        deadline = self.ent_deadline.get().strip()
        priority = self.cmb_priority.get().strip()
        detail = self.txt_detail.get("1.0", "end").strip()

        if not title:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập Tiêu đề.")
            return
        if deadline:
            try:
                _ = parse_dt(deadline)
            except Exception:
                messagebox.showwarning(
                    "Sai định dạng thời gian",
                    f"Deadline phải theo định dạng {DATE_FMT}",
                )
                return

        task = Task(title, detail, deadline, priority)
        self.tasks.append(task)
        sort_tasks(self.tasks)
        save_tasks(self.tasks)
        self.clear_form()
        self.refresh()
        messagebox.showinfo("Đã thêm", "Thêm công việc thành công.")
        self.ent_title.focus_set()

    def update_task(self):
        if self.updating:
            return

        idx = self.current_index()
        if idx is None or idx >= len(self.tasks):
            messagebox.showwarning("Lỗi", "Không tìm thấy công việc để cập nhật.")
            return

        self.updating = True  # khóa sự kiện select trong lúc cập nhật

        title = self.ent_title.get().strip()
        deadline = self.ent_deadline.get().strip()
        priority = self.cmb_priority.get().strip()
        detail = self.txt_detail.get("1.0", "end").strip()

        if not title:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập Tiêu đề.")
            self.updating = False
            return
        if deadline:
            try:
                _ = parse_dt(deadline)
            except Exception:
                messagebox.showwarning(
                    "Sai định dạng thời gian",
                    f"Deadline phải theo định dạng {DATE_FMT}",
                )
                self.updating = False
                return

        t = self.tasks[idx]
        t.title = title
        t.detail = detail
        t.deadline = deadline
        t.priority = priority
        sort_tasks(self.tasks)
        save_tasks(self.tasks)

        focused_widget = self.root.focus_get()

        self.refresh()

        if idx < self.listbox.size():
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            self.listbox.activate(idx)
            self.listbox.see(idx)

        if focused_widget:
            focused_widget.focus_set()

        messagebox.showinfo("Đã cập nhật", "Cập nhật công việc thành công.")
        self.ent_title.focus_set()
        self.updating = False  # mở lại sau khi xong

    def delete_task(self):
        idx = self.current_index()
        if idx is None or idx >= len(self.tasks):
            messagebox.showwarning("Lỗi", "Không tìm thấy công việc để xóa.")
            return

        if messagebox.askyesno("Xóa", "Xóa công việc đã chọn?"):
            self.tasks.pop(idx)
            save_tasks(self.tasks)
            self.clear_form()
            self.refresh()

    def mark_done(self):
        idx = self.current_index()
        if idx is None or idx >= len(self.tasks):
            messagebox.showwarning("Lỗi", "Không tìm thấy công việc.")
            return

        self.tasks[idx].done = True
        sort_tasks(self.tasks)
        save_tasks(self.tasks)
        self.refresh()

    # ===== UI helpers =====
    def current_index(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showinfo(
                "Chọn mục", "Vui lòng chọn 1 công việc trong danh sách."
            )
            return None
        return sel[0]

    def clear_form(self):
        self.ent_title.delete(0, tk.END)
        self.ent_deadline.delete(0, tk.END)
        self.cmb_priority.set("Trung bình")
        self.txt_detail.delete("1.0", "end")

    def refresh(self):
        self.listbox.delete(0, tk.END)
        sort_tasks(self.tasks)
        for t in self.tasks:
            display = fmt_row(t)
            if t.done:
                display = "✅ " + display
            self.listbox.insert(tk.END, display)

        self.lbl_info.config(
            text=f"Tổng: {len(self.tasks)}  •  Hoàn thành: "
            f"{sum(1 for t in self.tasks if t.done)}"
        )

    def on_select(self, _evt):
        # Bỏ qua nếu đang nhấn chuột, đang nhập hoặc đổi ưu tiên
        try:
            widget = self.root.focus_get()
            widget_name = widget.winfo_class() if widget else ""
        except (tk.TclError, KeyError):
            return

        if self.mouse_down or widget_name in (
            "TEntry",
            "Entry",
            "Text",
            "TCombobox",
            "Combobox",
        ):
            return
        if getattr(self, "editing_priority", False):
            return

        sel = self.listbox.curselection()
        if not sel:
            return

        idx = sel[0]
        if idx < 0 or idx >= len(self.tasks):
            return

        t = self.tasks[idx]
        self.ent_title.delete(0, tk.END)
        self.ent_title.insert(0, t.title)
        self.ent_deadline.delete(0, tk.END)
        self.ent_deadline.insert(0, t.deadline)
        self.cmb_priority.set(t.priority)
        self.txt_detail.delete("1.0", "end")
        self.txt_detail.insert("1.0", t.detail)

        info = (
            f"Tiêu đề: {t.title}\n"
            f"Chi tiết: {t.detail}\n"
            f"Ưu tiên: {t.priority}\n"
            f"Deadline: {t.deadline or '(chưa đặt)'}\n"
            f"Tạo lúc: {t.created_at}\n"
            f"Trạng thái: {'Hoàn thành' if t.done else 'Chưa xong'}"
        )
        self.lbl_info.config(text=info)


def run_app():
    root = ttk.Window(
        themename="flatly"
    )  # hoặc "minty" "yeti" "superhero", "darkly", "cosmo","flatly" ...
    root.iconbitmap("logo.ico")
    app = TodoApp(root)

    root.update_idletasks()
    w = 650
    h = 550
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    # ===== Hàm delay nhỏ =====
    def delay(ms):
        root.after(ms, lambda: None)

    # ===== Hiệu ứng fade-in =====
    root.attributes("-alpha", 0.0)
    for i in range(0, 11):
        root.attributes("-alpha", i / 10)
        root.update()
        delay(20)
    root.mainloop()
