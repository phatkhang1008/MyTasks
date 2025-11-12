import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import DateEntry
from datetime import datetime
from services.task_service import load_tasks, save_tasks, sort_tasks, fmt_row, parse_dt
from models.task_model import Task

DATE_FMT = "%d-%m-%Y %H:%M"


# ===== Time picker =====
class SimpleTimePicker(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.hour = tk.StringVar(value="00")
        self.minute = tk.StringVar(value="00")

        # Giảm width, canh giữa, thêm padding nhẹ cho đẹp
        spin_style = {"justify": "center", "width": 2, "wrap": True}

        ttk.Spinbox(self, from_=0, to=23, textvariable=self.hour, **spin_style).grid(
            row=0, column=0, padx=(0, 2)
        )

        ttk.Label(self, text=":", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=1, padx=(0, 2)
        )

        ttk.Spinbox(self, from_=0, to=59, textvariable=self.minute, **spin_style).grid(
            row=0, column=2
        )

    def get(self):
        return f"{self.hour.get().zfill(2)}:{self.minute.get().zfill(2)}"

    def set(self, time_str):
        try:
            h, m = time_str.split(":")
            self.hour.set(h)
            self.minute.set(m)
        except ValueError:
            self.hour.set("00")
            self.minute.set("00")


# ===== Main App =====
class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MyTasks - Quản lý công việc cá nhân")
        self.mouse_down = False
        self.updating = False
        self.editing_priority = False
        self.tasks = load_tasks()
        sort_tasks(self.tasks)

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

        header = ttk.Frame(root, padding=10)
        header.pack(fill="x")
        ttk.Label(
            header, text=" Quản lý công việc", font=("Segoe UI", 18, "bold")
        ).pack(side="left")
        ttk.Label(
            header, text="Theo dõi - Sắp xếp - Hoàn thành", bootstyle="secondary"
        ).pack(side="left", padx=10)

        # ===== Form =====
        frm = ttk.Labelframe(
            root, text=" Thông tin công việc ", padding=10, bootstyle="info"
        )
        frm.pack(fill="x", padx=12, pady=8)

        # Tiêu đề
        ttk.Label(frm, text="Tiêu đề:").grid(row=0, column=0, sticky="w", pady=4)
        self.ent_title = ttk.Entry(frm, width=48)
        self.ent_title.grid(row=0, column=1, columnspan=3, sticky="we", padx=6, pady=4)

        # Ngày hết hạn
        ttk.Label(frm, text="Ngày hết hạn:").grid(row=1, column=0, sticky="w", pady=4)
        self.date_deadline = DateEntry(frm, width=12, dateformat="%d-%m-%Y")
        self.date_deadline.grid(row=1, column=1, sticky="w", padx=6, pady=4)

        # Giờ
        ttk.Label(frm, text="Giờ:").grid(row=1, column=2, sticky="e", pady=4)
        self.time_deadline = SimpleTimePicker(frm)
        self.time_deadline.grid(row=1, column=3, sticky="w", pady=4)

        # Ưu tiên (custom popup)
        ttk.Label(frm, text="Ưu tiên:").grid(row=2, column=0, sticky="w", pady=4)
        self.priority_var = tk.StringVar(value="Trung bình")
        self.btn_priority = ttk.Button(
            frm,
            text="Trung bình ",
            bootstyle="warning",
            width=12,
            command=self.show_priority_popup,
        )
        self.btn_priority.grid(row=2, column=1, sticky="w", padx=6, pady=4)

        # Chi tiết
        ttk.Label(frm, text="Chi tiết:").grid(row=3, column=0, sticky="nw", pady=4)
        self.txt_detail = tk.Text(frm, height=8, width=48)
        self.txt_detail.grid(row=3, column=1, columnspan=3, sticky="we", padx=6, pady=4)

        # ===== Buttons =====
        btns = ttk.Frame(root, padding=(10, 0))
        btns.pack(fill="x", pady=(2, 8))
        ttk.Button(
            btns, text="➕ Thêm", command=self.add_task, bootstyle="success-outline"
        ).pack(side="left", padx=4)
        ttk.Button(
            btns, text="💾 Cập nhật", command=self.update_task, bootstyle="info-outline"
        ).pack(side="left", padx=4)
        ttk.Button(
            btns, text="✅ Hoàn thành", command=self.mark_done, bootstyle="success"
        ).pack(side="left", padx=4)
        ttk.Button(
            btns, text="🗑️ Xóa", command=self.delete_task, bootstyle="danger"
        ).pack(side="left", padx=4)
        ttk.Button(
            btns, text="🔄 Làm mới", command=self.refresh, bootstyle="warning-outline"
        ).pack(side="left", padx=4)

        # ===== Danh sách =====
        listfrm = ttk.Labelframe(root, text=" Danh sách công việc ", padding=8)
        listfrm.pack(fill="both", expand=True, padx=8, pady=4)
        self.listbox = tk.Listbox(
            listfrm, height=8, activestyle="dotbox", font=("Segoe UI", 10)
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        sb = ttk.Scrollbar(listfrm, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=sb.set)

        info = ttk.Labelframe(
            root,
            text=" Chi tiết ",
            padding=12,
            bootstyle="secondary",
        )
        info.pack(fill="x", padx=14, pady=(10, 14))
        self.lbl_info = ttk.Label(
            info,
            text="Chọn 1 công việc để xem chi tiết…",
            justify="left",
            anchor="w",
            wraplength=820,
        )
        self.lbl_info.pack(fill="x", padx=4, pady=4)
        self.refresh()

    # ===== CRUD =====
    def add_task(self):
        title = self.ent_title.get().strip()
        date_str = self.date_deadline.entry.get().strip()
        time_str = self.time_deadline.get()
        deadline = f"{date_str} {time_str}"
        priority = self.priority_var.get().strip()
        detail = self.txt_detail.get("1.0", "end").strip()

        if not title:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập tiêu đề.")
            return
        try:
            _ = parse_dt(deadline)
        except Exception:
            messagebox.showwarning(
                "Sai định dạng", f"Deadline phải theo định dạng {DATE_FMT}"
            )
            return

        task = Task(title, detail, deadline, priority)
        self.tasks.append(task)
        sort_tasks(self.tasks)
        save_tasks(self.tasks)
        self.clear_form()
        self.refresh()
        messagebox.showinfo("Thành công", "Đã thêm công việc mới.")
        self.ent_title.focus_set()

    def update_task(self):
        if self.updating:
            return
        idx = self.current_index()
        if idx is None or idx >= len(self.tasks):
            messagebox.showwarning("Lỗi", "Không tìm thấy công việc để cập nhật.")
            return
        self.updating = True

        title = self.ent_title.get().strip()
        date_str = self.date_deadline.entry.get().strip()
        time_str = self.time_deadline.get()
        deadline = f"{date_str} {time_str}"
        priority = self.priority_var.get().strip()
        detail = self.txt_detail.get("1.0", "end").strip()

        try:
            _ = parse_dt(deadline)
        except Exception:
            messagebox.showwarning(
                "Sai định dạng", f"Deadline phải theo định dạng {DATE_FMT}"
            )
            self.updating = False
            return

        t = self.tasks[idx]
        t.title, t.detail, t.deadline, t.priority = title, detail, deadline, priority
        sort_tasks(self.tasks)
        save_tasks(self.tasks)
        self.refresh()
        messagebox.showinfo("Đã cập nhật", "Cập nhật công việc thành công.")
        self.updating = False

    def delete_task(self):
        idx = self.current_index()
        if idx is None:
            return
        if messagebox.askyesno("Xóa", "Bạn có chắc muốn xóa công việc này?"):
            self.tasks.pop(idx)
            save_tasks(self.tasks)
            self.clear_form()
            self.refresh()

    def mark_done(self):
        idx = self.current_index()
        if idx is None:
            return
        self.tasks[idx].done = True
        sort_tasks(self.tasks)
        save_tasks(self.tasks)
        self.refresh()

    # ===== Popup chọn ưu tiên =====
    def show_priority_popup(self):
        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)
        popup.geometry(
            "+%d+%d"
            % (self.btn_priority.winfo_rootx(), self.btn_priority.winfo_rooty() + 30)
        )
        popup.config(bg="#f0f0f0", padx=4, pady=4)

        options = [
            ("Cao", "danger"),
            ("Trung bình", "warning"),
            ("Thấp", "success"),
        ]

        def select_priority(value, style):
            self.priority_var.set(value)  # Cập nhật biến ngay lập tức
            self.btn_priority.config(text=value, bootstyle=style)
            popup.destroy()

        for text, style in options:
            ttk.Button(
                popup,
                text=text,
                bootstyle=style,
                width=14,
                command=lambda t=text, s=style: select_priority(t, s),
            ).pack(fill="x", pady=2)
        try:
            popup.focus_set()
            popup.grab_set()  # giữ chuột và bàn phím trong cửa sổ này cho đến khi nó đóng
        except:
            pass
        popup.after(
            100, lambda: popup.wait_window()
        )  # Dừng ở đây tới khi popup bị destroy

    # ===== Helpers =====
    def current_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def clear_form(self):
        self.ent_title.delete(0, tk.END)
        self.txt_detail.delete("1.0", tk.END)

    def refresh(self):
        self.listbox.delete(0, tk.END)
        sort_tasks(self.tasks)
        for t in self.tasks:
            label = fmt_row(t)
            self.listbox.insert(tk.END, label)
            color = "#E9FBE9" if t.done else "#FFFBEA"
            self.listbox.itemconfig(tk.END, bg=color)
        done_count = sum(1 for t in self.tasks if t.done)
        self.lbl_info.config(text=f"Tổng: {len(self.tasks)} | Hoàn thành: {done_count}")

    def on_select(self, _evt):
        # 👉 lấy vị trí task đang chọn
        idx = self.current_index()
        if idx is None or idx >= len(self.tasks):
            return
        t = self.tasks[idx]
        self.ent_title.delete(0, tk.END)
        self.ent_title.insert(0, t.title)
        self.txt_detail.delete("1.0", tk.END)
        self.txt_detail.insert("1.0", t.detail)
        if t.deadline:
            try:
                dt = parse_dt(t.deadline)
                self.date_deadline.entry.delete(0, tk.END)
                self.date_deadline.entry.insert(0, dt.strftime("%d-%m-%Y"))
                self.time_deadline.set(dt.strftime("%H:%M"))
            except:
                pass
        # Cập nhật label chi tiết
        info = (
            f"📝 Tiêu đề: {t.title}\n"
            f"📄 Chi tiết: {t.detail}\n"
            f"🎯 Ưu tiên: {t.priority}\n"
            f"⏰ Deadline: {t.deadline or '(chưa đặt)'}\n"
            f"📅 Tạo lúc: {t.created_at}\n"
            f"📌 Trạng thái: {'Hoàn thành' if t.done else 'Chưa xong'}"
        )
        self.lbl_info.config(text=info)
        # Cập nhật nút ưu tiên cho đúng màu
        style_map = {
            "Cao": "danger",
            "Trung bình": "warning",
            "Thấp": "success",
        }
        style = style_map.get(t.priority, "secondary")
        self.priority_var.set(t.priority)
        self.btn_priority.config(text=f" {t.priority}", bootstyle=style)


def run_app():
    root = ttk.Window(themename="flatly")
    root.title("MyTasks - Đang khởi động...")

    # Splash screen
    splash = ttk.Frame(root, padding=60)
    ttk.Label(
        splash, text="Đang khởi động MyTasks...", font=("Segoe UI", 16, "bold")
    ).pack(pady=20)
    bar = ttk.Progressbar(splash, mode="indeterminate", bootstyle="info-striped")
    bar.pack(fill="x", padx=40, pady=10)
    bar.start(10)
    splash.pack(expand=True)

    root.update()
    root.after(2000)  # 👈 Giữ splash 2 giây
    root.update()  # ép vẽ lại (để thấy hiệu ứng)

    splash.destroy()  # Sau đó mới phá splash
    root.iconbitmap("logo.ico")

    # App chính
    app = TodoApp(root)
    w, h = 900, 800
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.attributes("-alpha", 0.0)

    for i in range(0, 11):
        root.attributes("-alpha", i / 10)
        root.update()
        root.after(80, lambda: None)  # hiệu ứng sáng dần rõ hơn

    root.mainloop()


if __name__ == "__main__":
    run_app()
