import tkinter as tk
from tkinter import simpledialog

def show_float_input_dialog(title="Введите значение", prompt="Введите число:", finish: bool = False):
    result = {"value": None, "button": None}

    def on_button(button_name):
        result["button"] = button_name
        if button_name == "ok":
            try:
                value = float(entry.get())
                result["value"] = value
            except ValueError:
                entry.delete(0, tk.END)
                entry.insert(0, "Ошибка!")
                return
        dialog.destroy()

    dialog = tk.Toplevel()
    dialog.title(title)
    dialog.geometry("300x150")
    dialog.grab_set()  # Блокирует остальные окна до закрытия

    tk.Label(dialog, text=prompt).pack(pady=5)

    entry = tk.Entry(dialog)
    entry.pack(pady=5)
    entry.focus()

    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=10)

    tk.Button(button_frame, text="OK", width=10, command=lambda: on_button("ok")).pack(side="left", padx=5)
    if finish:
        tk.Button(button_frame, text="Конец", width=10, command=lambda: on_button("default")).pack(side="left", padx=5)
    tk.Button(button_frame, text="Отменить", width=10, command=lambda: on_button("cancel")).pack(side="left", padx=5)

    dialog.wait_window()  # Ждет закрытия окна

    return result

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Скрываем основное окно

    result = show_float_input_dialog(title="Настройка", prompt="Введите тягу:")
    print(result)

    root.destroy()
