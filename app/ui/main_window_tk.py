"""
Tkinter-версия главного окна приложения.
"""
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.controllers.connection_controller import ConnectionController
from app.controllers.gcode_controller import GCodeController
from app.controllers.run_controller import RunController
from app.models.app_state import AppState, RunStatus
from app.utils.logger import get_logger

logger = get_logger()


class _GCodeViewAdapter:
    """Адаптер для совместимости с RunController.start_from_editor()."""

    def __init__(self, text_widget: tk.Text):
        self._text_widget = text_widget

    def get_lines(self):
        raw = self._text_widget.get("1.0", tk.END)
        return raw.splitlines()


class MainWindowTk:
    """Главное окно на tkinter с сохранением существующей логики контроллеров."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Delta Robot - G-code Sender v0.1 (tkinter)")
        self.root.geometry("1200x800")

        self.app_state = AppState()
        self.connection_controller = ConnectionController(self.app_state)
        self.gcode_controller = GCodeController(self.app_state)
        self.run_controller = RunController(self.app_state, self.connection_controller.get_manager())

        self._event_queue: queue.Queue = queue.Queue()
        self._ports: list[str] = []

        self._build_ui()
        self._connect_signals()
        self._refresh_ports()
        self._poll_events()

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        top = ttk.Frame(self.root, padding=8)
        top.grid(row=0, column=0, sticky="ew")
        for i in range(11):
            top.columnconfigure(i, weight=0)
        top.columnconfigure(10, weight=1)

        ttk.Label(top, text="COM-порт:").grid(row=0, column=0, padx=(0, 6))
        self.port_combo = ttk.Combobox(top, state="readonly", width=24)
        self.port_combo.grid(row=0, column=1, padx=(0, 6))

        self.refresh_btn = ttk.Button(top, text="Обновить", command=self._refresh_ports)
        self.refresh_btn.grid(row=0, column=2, padx=(0, 6))
        self.connect_btn = ttk.Button(top, text="Подключить", command=self._on_connect)
        self.connect_btn.grid(row=0, column=3, padx=(0, 6))
        self.disconnect_btn = ttk.Button(top, text="Отключить", command=self._on_disconnect)
        self.disconnect_btn.grid(row=0, column=4, padx=(0, 12))
        self.disconnect_btn.state(["disabled"])

        self.open_btn = ttk.Button(top, text="Открыть G-code", command=self._on_open_file)
        self.open_btn.grid(row=0, column=5, padx=(0, 6))
        self.start_btn = ttk.Button(top, text="Старт", command=self._on_start)
        self.start_btn.grid(row=0, column=6, padx=(0, 6))
        self.pause_btn = ttk.Button(top, text="Пауза", command=self._on_pause)
        self.pause_btn.grid(row=0, column=7, padx=(0, 6))
        self.stop_btn = ttk.Button(top, text="Стоп", command=self._on_stop)
        self.stop_btn.grid(row=0, column=8, padx=(0, 6))
        self.send_btn = ttk.Button(top, text="Отправить (построчно)", command=self._on_send_line_by_line)
        self.send_btn.grid(row=0, column=9, padx=(0, 6))

        self.start_btn.state(["disabled"])
        self.pause_btn.state(["disabled"])
        self.stop_btn.state(["disabled"])
        self.send_btn.state(["disabled"])

        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, sticky="nsew")

        left = ttk.Frame(body, padding=8)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text="G-code").grid(row=0, column=0, sticky="w")
        self.gcode_text = tk.Text(left, wrap=tk.NONE)
        self.gcode_text.grid(row=1, column=0, sticky="nsew")
        body.add(left, weight=3)

        right = ttk.Frame(body, padding=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(4, weight=0)
        ttk.Label(right, text="Консоль").grid(row=0, column=0, sticky="w")
        self.console_text = tk.Text(right, wrap=tk.WORD, state=tk.DISABLED, height=18)
        self.console_text.grid(row=1, column=0, sticky="nsew")

        cmd_frame = ttk.Frame(right)
        cmd_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        cmd_frame.columnconfigure(0, weight=1)
        self.cmd_entry = ttk.Entry(cmd_frame)
        self.cmd_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(cmd_frame, text="Отправить команду", command=self._on_send_console).grid(row=0, column=1)

        jog_frame = ttk.Frame(right)
        jog_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        jog_frame.columnconfigure(0, weight=1)
        self.jog_entry = ttk.Entry(jog_frame)
        self.jog_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(jog_frame, text="Jog", command=self._on_jog).grid(row=0, column=1)

        body.add(right, weight=2)

        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w").grid(
            row=2, column=0, sticky="ew"
        )

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _connect_signals(self):
        self.connection_controller.ports_changed.connect(
            lambda ports: self._event_queue.put(("ports_changed", ports))
        )
        self.connection_controller.connected.connect(
            lambda port: self._event_queue.put(("connected", port))
        )
        self.connection_controller.disconnected.connect(
            lambda: self._event_queue.put(("disconnected", None))
        )
        self.connection_controller.error_occurred.connect(
            lambda err: self._event_queue.put(("connection_error", err))
        )

        self.gcode_controller.gcode_loaded.connect(
            lambda lines: self._event_queue.put(("gcode_loaded", lines))
        )
        self.gcode_controller.trajectory_updated.connect(
            lambda points: self._event_queue.put(("trajectory_updated", points))
        )

        self.run_controller.started.connect(lambda: self._event_queue.put(("run_started", None)))
        self.run_controller.paused.connect(lambda: self._event_queue.put(("run_paused", None)))
        self.run_controller.resumed.connect(lambda: self._event_queue.put(("run_resumed", None)))
        self.run_controller.stopped.connect(lambda: self._event_queue.put(("run_stopped", None)))
        self.run_controller.completed.connect(lambda: self._event_queue.put(("run_completed", None)))
        self.run_controller.progress.connect(
            lambda current, total: self._event_queue.put(("run_progress", (current, total)))
        )

        manager = self.connection_controller.get_manager()
        manager.line_sent.connect(lambda line: self._event_queue.put(("line_sent", line)))
        manager.line_received.connect(lambda line: self._event_queue.put(("line_received", line)))
        manager.error.connect(lambda err: self._event_queue.put(("serial_error", err)))

    def _poll_events(self):
        try:
            while True:
                kind, payload = self._event_queue.get_nowait()
                self._handle_event(kind, payload)
        except queue.Empty:
            pass
        self.root.after(50, self._poll_events)

    def _handle_event(self, kind: str, payload):
        if kind == "ports_changed":
            ports = payload or []
            self._ports = [str(p) for p in ports]
            self.port_combo["values"] = self._ports
            if self._ports:
                self.port_combo.current(0)
            self._log_info(f"Найдено портов: {len(self._ports)}")
        elif kind == "connected":
            self.connect_btn.state(["disabled"])
            self.disconnect_btn.state(["!disabled"])
            self.status_var.set(f"Подключено: {payload}")
            self._log_info(f"Подключено к {payload}")
        elif kind == "disconnected":
            self.connect_btn.state(["!disabled"])
            self.disconnect_btn.state(["disabled"])
            self.status_var.set("Отключено")
            self._log_info("Отключено")
        elif kind == "connection_error":
            self._log_error(str(payload))
            messagebox.showwarning("Ошибка подключения", str(payload))
        elif kind == "gcode_loaded":
            self.gcode_text.delete("1.0", tk.END)
            self.gcode_text.insert("1.0", "\n".join(payload))
            self.start_btn.state(["!disabled"])
            self.send_btn.state(["!disabled"])
            self._log_info(f"G-code загружен: {len(payload)} строк")
        elif kind == "trajectory_updated":
            points_count = len(payload or [])
            self._log_info(f"Траектория построена: {points_count} точек")
        elif kind == "run_started":
            self.start_btn.state(["disabled"])
            self.pause_btn.state(["!disabled"])
            self.stop_btn.state(["!disabled"])
            self.send_btn.state(["disabled"])
            self.status_var.set("Выполнение...")
        elif kind == "run_paused":
            self.status_var.set("Пауза")
        elif kind == "run_resumed":
            self.status_var.set("Выполнение...")
        elif kind == "run_stopped":
            self._set_idle_controls()
            self.status_var.set("Остановлено")
        elif kind == "run_completed":
            self._set_idle_controls()
            self.status_var.set("Завершено")
            self._log_info("G-code выполнен полностью")
            messagebox.showinfo("Готово", "Выполнение G-code завершено")
        elif kind == "run_progress":
            current, total = payload
            percent = (current / total * 100.0) if total else 0.0
            self.status_var.set(f"Выполнение: {current}/{total} ({percent:.1f}%)")
        elif kind == "line_sent":
            self._log_info(f"→ {payload}")
        elif kind == "line_received":
            self._log_info(f"← {payload}")
        elif kind == "serial_error":
            self._log_error(str(payload))

    def _set_idle_controls(self):
        self.start_btn.state(["!disabled"])
        self.pause_btn.state(["disabled"])
        self.stop_btn.state(["disabled"])
        self.send_btn.state(["!disabled"])

    def _selected_port_device(self):
        selected = self.port_combo.get().strip()
        if not selected:
            return None
        return selected.split(" - ", 1)[0].strip()

    def _refresh_ports(self):
        self._log_info("Обновление списка портов...")
        self.connection_controller.refresh_ports()

    def _on_connect(self):
        port = self._selected_port_device()
        if not port:
            messagebox.showwarning("Внимание", "Выберите COM-порт")
            return
        self.app_state.set_active_port(port)
        self.connection_controller.get_manager().set_selected_port(port)
        self.connection_controller.connect_to_port(port)

    def _on_disconnect(self):
        self.connection_controller.disconnect_from_port()

    def _on_open_file(self):
        filepath = filedialog.askopenfilename(
            title="Открыть G-code файл",
            filetypes=[("G-code files", "*.gcode *.nc"), ("All files", "*.*")],
        )
        if not filepath:
            return
        self._log_info(f"Загрузка файла: {filepath}")
        if self.gcode_controller.load_gcode_from_file(filepath):
            self.app_state.set_gcode_file_path(filepath)
        else:
            messagebox.showerror("Ошибка", "Не удалось загрузить G-code файл")

    def _on_start(self):
        if not self.app_state.active_port:
            messagebox.showwarning("Внимание", "Сначала подключитесь к COM-порту")
            return
        self._log_info("Начато выполнение G-code")
        self.run_controller.start()

    def _on_pause(self):
        if self.app_state.run_status == RunStatus.RUNNING:
            self.run_controller.pause()
            self._log_info("Пауза")
        elif self.app_state.run_status == RunStatus.PAUSED:
            self.run_controller.resume()
            self._log_info("Продолжить")

    def _on_stop(self):
        self.run_controller.stop()
        self._log_info("Остановлено выполнение")

    def _on_send_line_by_line(self):
        if not self.app_state.active_port:
            messagebox.showwarning("Внимание", "Сначала подключитесь к COM-порту")
            return
        if not self.gcode_text.get("1.0", tk.END).strip():
            messagebox.showwarning("Внимание", "G-code редактор пуст")
            return
        adapter = _GCodeViewAdapter(self.gcode_text)
        self._log_info("Начало построчной отправки G-code из редактора")
        self.run_controller.start_from_editor(adapter)

    def _on_send_console(self):
        command = self.cmd_entry.get().strip()
        if not command:
            return
        if not self.app_state.active_port:
            self._log_error("Выберите COM-порт для отправки команд")
            return
        self.run_controller.send_immediate(command, wait_ok=True)
        self.cmd_entry.delete(0, tk.END)

    def _on_jog(self):
        command = self.jog_entry.get().strip()
        if not command:
            return
        if not self.app_state.active_port:
            self._log_error("Выберите COM-порт для jog команды")
            return
        self.run_controller.send_immediate(command, wait_ok=True)
        self.jog_entry.delete(0, tk.END)

    def _log_info(self, text: str):
        self._append_console(f"[INFO] {text}")

    def _log_error(self, text: str):
        self._append_console(f"[ERROR] {text}")

    def _append_console(self, text: str):
        self.console_text.configure(state=tk.NORMAL)
        self.console_text.insert(tk.END, text + "\n")
        self.console_text.see(tk.END)
        self.console_text.configure(state=tk.DISABLED)

    def _on_close(self):
        try:
            self.run_controller.stop()
        except Exception:
            pass
        try:
            self.connection_controller.get_manager().cleanup()
        except Exception:
            pass
        self.root.destroy()
