import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import time
import random  # Pro Grid třídu
import sqlite3
import os
from datetime import datetime

# Třída Grid - řeší logiku hlavolamu:

class Grid:
    def __init__(self, size):
        self.size = size
        self.number_of_turns = 0
        self.matrix = []
        self.empty_space = "-"
        self.init_database()
        self._shuffle_matrix()

    def init_database(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(folder, 'halloffame.db')

        conn = sqlite3.connect(full_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS halloffame (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time INTEGER NOT NULL,
            turns INTEGER NOT NULL,
            grid_size INTEGER NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    def _shuffle_matrix(self):
        # příprava všech čísel dlaždic, včetně mezery
        matrix_one_dimension = []
        for number in range(self.size * self.size):
            matrix_one_dimension.append(number + 1)
        matrix_one_dimension[-1] = self.empty_space

        # uložení do matrixu jako vyřešeno
        self.matrix = []
        for r in range(self.size):
            row = matrix_one_dimension[r * self.size:(r + 1) * self.size]
            self.matrix.append(row)

        # Zamíchání pomocí platných tahů (garantuje řešitelnost)
        for _ in range(self.size * self.size * 100):  # Počet tahů na pořádné zamíchání
            re, ce = self.find_empty()
            possible_moves = []

            # hledání možných tahů
            if re > 0:  # Lze pohybovat dolů
                possible_moves.append((re - 1, ce, "down"))
            if re < self.size - 1:  # Lze pohybovat nahoru
                possible_moves.append((re + 1, ce, "up"))
            if ce > 0:  # Lze pohybovat doprava
                possible_moves.append((re, ce - 1, "right"))
            if ce < self.size - 1:  # Lze pohybovat doleva
                possible_moves.append((re, ce + 1, "left"))

            if possible_moves:
                rm, cm, direction = random.choice(possible_moves) # vybereme náhodný posun a nastavíme parametry jako při hře
                block_size = self.block_size(rm, cm, direction)
                self.move_in_matrix(rm, cm, block_size, direction)

    def find_empty(self):
        for r in range(len(self.matrix)):
            for c in range(len(self.matrix[r])):
                if self.matrix[r][c] == self.empty_space:
                    return r, c

    def can_move(self, rm, cm, direction):
        re, ce = self.find_empty()
        if re == rm and ce == cm:
            return False

        if direction == "left":
            return rm == re and cm > ce
        if direction == "right":
            return rm == re and cm < ce
        if direction == "up":
            return cm == ce and rm > re
        if direction == "down":
            return cm == ce and rm < re

    def block_size(self, rm, cm, direction):
        re, ce = self.find_empty()
        if direction in ("left", "right"):
            return abs(ce - cm)
        if direction in ("up", "down"):
            return abs(re - rm)

    def move_in_matrix(self, rm, cm, block_size, direction):
        re, ce = self.find_empty()
        if direction == "left":
            for i in range(block_size):
                self.matrix[rm][ce + i] = self.matrix[rm][ce + i + 1]
            self.matrix[rm][ce + block_size] = self.empty_space
        if direction == "right":
            for i in range(block_size):
                self.matrix[rm][ce - i] = self.matrix[rm][ce - i - 1]
            self.matrix[rm][ce - block_size] = self.empty_space
        if direction == "up":
            for i in range(block_size):
                self.matrix[re + i][cm] = self.matrix[re + i + 1][cm]
            self.matrix[re + block_size][cm] = self.empty_space
        if direction == "down":
            for i in range(block_size):
                self.matrix[re - i][cm] = self.matrix[re - i - 1][cm]
            self.matrix[re - block_size][cm] = self.empty_space

    def is_solved(self):
        previous_value = 0
        for row in self.matrix:
            for current_value in row:
                if current_value == self.empty_space:
                    continue
                if current_value != previous_value + 1:
                    return False
                previous_value = current_value
        return True

# GUI část
class PuzzleApp:
    def __init__(self):
        self.size = 4
        self.tile_size = 80
        self.start_time = 0
        self.elapsed_time = 0
        self.timer_running = False
        self.image_path = "Pictures"
        self.images = {}
        self.canvas_items = [[None] * self.size for _ in range(self.size)]
        self.g = None
        self.animating = False
        self.root = tk.Tk()
        self.root.title("Hlavolam")
        self.time_label = tk.Label(self.root, text="Čas: 00:00\t Počet tahů: 000", font=("Arial", 14))
        self.time_label.pack(pady=5, padx=5)
        self.canvas_size = self.size * self.tile_size

        self.canvas = tk.Canvas(self.root, width=self.canvas_size, height=self.canvas_size, bg="#8F7570")
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.pack(padx=5, pady=5)
        self.set_new_game()

    def canvas_items_init(self):
        # Inicializace canvas_items – NEVYTVOŘ pro prázdné ("-")
        for r in range(self.size):
            for c in range(self.size):
                value = self.g.matrix[r][c]
                if value != "-":
                    x = c * self.tile_size
                    y = r * self.tile_size
                    item_id = self.canvas.create_image(x, y, image=self.images[value], anchor="nw")
                    self.canvas_items[r][c] = item_id
                else:
                    self.canvas_items[r][c] = None  # Prázdné je díra (background)

    def load_images(self):
        # Zobrazí hlavolam a spustí čas
        for i in range(1, self.size * self.size):
            img = Image.open(f"{self.image_path}/tile_{i}.png")
            self.images[i] = ImageTk.PhotoImage(img)

    def on_click(self, event):
        if self.animating:
            return
        cm = event.x // self.tile_size
        rm = event.y // self.tile_size

        direction = self.get_direction(rm, cm)

        if direction is None:
            return

        if not self.g.can_move(rm, cm, direction):
            return

        self.animating = True
        size = self.g.block_size(rm, cm, direction)

        if direction == "left":
            re, ce = self.g.find_empty()
            self.animate_left(rm, cm, re, ce, size)

        if direction == "right":
            re, ce = self.g.find_empty()
            self.animate_right(rm, cm, re, ce, size)

        if direction == "up":
            re, ce = self.g.find_empty()
            self.animate_up(rm, cm, re, ce, size)

        if direction == "down":
            re, ce = self.g.find_empty()
            self.animate_down(rm, cm, re, ce, size)

    def get_direction(self, rm, cm):
        re, ce = self.g.find_empty()
        if rm == re:
            if cm > ce:
                return "left"
            if cm < ce:
                return "right"
        if cm == ce:
            if rm > re:
                return "up"
            if rm < re:
                return "down"
        return None

    def animate_left(self, rm, cm, re, ce, block_size, step=0):
        if step == self.tile_size:
            # Posun reference v canvas_items doleva
            for i in range(block_size):
                self.canvas_items[rm][ce + i] = self.canvas_items[rm][ce + i + 1]
            self.canvas_items[rm][ce + block_size] = None  # Nové prázdné je None (díra)

            # Posun v matici (používáme Grid metodu)
            self.g.move_in_matrix(rm, cm, block_size, "left")
            self.g.number_of_turns += 1
            self.animating = False
            # Kontrola, jestli je vyřešeno
            if self.g.is_solved():
                self.congratulations()
            return

        # Animace po 1 pixelu – posunují se jen existující itemy (dlaždice)
        for offset in range(block_size):
            item = self.canvas_items[rm][ce + 1 + offset]
            if item is not None:  # Bezpečnost, ale měly by být
                self.canvas.move(item, -1, 0)

        self.canvas.after(1, self.animate_left, rm, cm, re, ce, block_size, step + 1)

    def animate_right(self, rm, cm, re, ce, block_size, step=0):
        if step == self.tile_size:
            # Posun reference v canvas_items doprava
            for i in range(block_size):
                self.canvas_items[rm][ce - i] = self.canvas_items[rm][ce - i - 1]
            self.canvas_items[rm][ce - block_size] = None  # Nové prázdné je None (díra)

            # Posun v matici (používáme Grid metodu)
            self.g.move_in_matrix(rm, cm, block_size, "right")
            self.g.number_of_turns += 1
            self.animating = False
            # Kontrola, jestli je vyřešeno
            if self.g.is_solved():
                self.congratulations()
            return

        # Animace po 1 pixelu – posunují se jen existující itemy (dlaždice)
        for offset in range(block_size):
            item = self.canvas_items[rm][ce - 1 - offset]
            if item is not None:  # Bezpečnost, ale měly by být
                self.canvas.move(item, 1, 0)

        self.canvas.after(1, self.animate_right, rm, cm, re, ce, block_size, step + 1)

    def animate_up(self, rm, cm, re, ce, block_size, step=0):
        if step == self.tile_size:
            # Posun reference v canvas_items nahoru
            for i in range(block_size):
                self.canvas_items[re + i][cm] = self.canvas_items[re + i + 1][cm]
            self.canvas_items[re + block_size][cm] = None  # Nové prázdné je None (díra)

            # Posun v matici (používáme Grid metodu)
            self.g.move_in_matrix(rm, cm, block_size, "up")
            self.g.number_of_turns += 1
            self.animating = False
            # Kontrola, jestli je vyřešeno
            if self.g.is_solved():
                self.congratulations()
            return

        # Animace po 1 pixelu – posunují se jen existující itemy (dlaždice)
        for offset in range(block_size):
            item = self.canvas_items[re + 1 + offset][cm]
            if item is not None:  # Bezpečnost, ale měly by být
                self.canvas.move(item, 0, -1)

        self.canvas.after(1, self.animate_up, rm, cm, re, ce, block_size, step + 1)

    def animate_down(self, rm, cm, re, ce, block_size, step=0):
        if step == self.tile_size:
            # Posun reference v canvas_items dolů
            for i in range(block_size):
                self.canvas_items[re - i][cm] = self.canvas_items[re - i - 1][cm]
            self.canvas_items[re - block_size][cm] = None  # Nové prázdné je None (díra)

            # Posun v matici (používáme Grid metodu)
            self.g.move_in_matrix(rm, cm, block_size, "down")
            self.g.number_of_turns += 1
            self.animating = False
            # Kontrola, jestli je vyřešeno
            if self.g.is_solved():
                self.congratulations()
            return

        # Animace po 1 pixelu – posunují se jen existující itemy (dlaždice)
        for offset in range(block_size):
            item = self.canvas_items[re - 1 - offset][cm]
            if item is not None:  # Bezpečnost, ale měly by být
                self.canvas.move(item, 0, 1)

        self.canvas.after(1, self.animate_down, rm, cm, re, ce, block_size, step + 1)

    # def congratulations(self):
    #     self.stop_timer()
    #     again = tk.messagebox.askyesno("Vyřešeno !",
    #                            f"Gratuluji !\nVyřešeno za {self.format_time(self.elapsed_time)}\nPočet tahů: {self.g.number_of_turns}\nChceš začít novou hru?")
    #     if again:
    #         self.set_new_game()
    #     else:
    #         self.root.destroy()

    def congratulations(self):
        self.stop_timer()
        folder = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(folder, 'halloffame.db')

        datum = datetime.now().strftime('%d.%m.%Y')

        conn = sqlite3.connect(full_path)
        cursor = conn.cursor()

        #   zápis výsledku do databáze
        query = '''INSERT INTO halloffame(date, time, turns, grid_size) VALUES (?, ?, ?, ?)'''
        cursor.execute(query, (datum, int(self.elapsed_time), self.g.number_of_turns, self.size))

        conn.commit()

        my_id = cursor.lastrowid # ukazuje na id právě přidaného řádku výsledku

        # Zjištění pořadí času
        query = '''
                SELECT COUNT(*) FROM halloffame
                WHERE time < ? AND grid_size = ? AND id <> ?
                '''
        cursor.execute(query, (self.elapsed_time, self.size, my_id))
        poradi_casu = cursor.fetchone()[0] + 1

        # Pořadí tahů
        query = '''
                SELECT COUNT(*) FROM halloffame
                WHERE turns < ? AND grid_size = ? AND id <> ?
                '''
        cursor.execute(query, (self.g.number_of_turns, self.size, my_id))
        poradi_tahu = cursor.fetchone()[0] + 1

        # Celkový počet úspěšných řešení
        query = '''
                SELECT COUNT(*) FROM halloffame
                WHERE grid_size = ?
                '''
        cursor.execute(query, (self.size,))
        celkem = cursor.fetchone()[0]

        # TOP 10
        query = '''
                SELECT date, time, turns FROM halloffame
                WHERE grid_size = ?
                ORDER BY turns ASC, time ASC
                LIMIT 10
            '''
        cursor.execute(query, (self.size,))
        top_10 = cursor.fetchall()

        conn.close()

        # Výpisy

        text = (f"\n📊 Tvůj výsledek v porovnání se všemi:\n  ⏱  Čas:  {self.format_time(self.elapsed_time)} - {poradi_casu}. nejlepší z {celkem} hráčů\n"
                f"  🎯 Tahy: {self.g.number_of_turns} - {poradi_tahu}. nejlepší z {celkem} hráčů"
                f"\n\nVelikost hry: {self.size} x {self.size}\n"
                f"\n🏆 HALL OF FAME 🏆\n\n"
                f"{'   #':<6} {'Datum':<16} {'Čas':<8} {'Tahy'}\n") + "-" * 42

        for i, (datum, cas, tahy) in enumerate(top_10, start=1):
            text += f"\n{i:02}  {datum:<12} {self.format_time(cas):<8} {tahy}"

        self.root.withdraw()  # schová hlavní okno (nezničí ho)

        if celkem >= 10:
            koeficient = 10
        else: koeficient = celkem % 10
        font_size = 14

        congratulations_window = tk.Toplevel(self.root)
        congratulations_window.title("Gratuluji, vyřešil jste to !")
        y=str(450 + font_size * koeficient)
        congratulations_window.geometry(f"380x{y}")
        congratulations_window.protocol("WM_DELETE_WINDOW", self.root.destroy)

        # Výsledková listina
        label = tk.Label(congratulations_window, text=text, font=("Arial", font_size))
        label.grid(row=0, column=0, padx=10)

        # Tlačítka
        new_game_button = tk.Button(congratulations_window, text='Nová hra', font=("Arial", 12), command=lambda: [congratulations_window.destroy(), self.root.deiconify(), self.set_new_game()])
        new_game_button.grid(row=1, column=0, pady=(10, 10), ipadx=30, ipady=10)

        quit_game_button = tk.Button(congratulations_window, text='Konec hry', font=("Arial", 12), command=self.root.destroy)
        quit_game_button.grid(row=2, column=0, pady=(10, 10), ipadx=30, ipady=10)

    # Měření času

    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02}:{secs:02}"  # čas ve formátu mm:ss

    def start_timer(self):
        self.start_time = time.time()
        self.timer_running = True
        self.update_timer()

    def stop_timer(self):
        self.timer_running = False

    def update_timer(self):
        if self.timer_running:
            self.elapsed_time = time.time() - self.start_time
            self.time_label.config(text=f"Čas: {self.format_time(self.elapsed_time)}\tPočet tahů: {self.g.number_of_turns}")
            self.root.after(1000, self.update_timer)

    def choose_grid_size_window(self):
        self.root.update_idletasks()
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        dw = int(rw * 1.05)
        dh = int(rh * 1.05)
        x = rx + (rw - dw) // 2
        y = ry + (rh - dh) // 2
        dialog = tk.Toplevel(self.root)
        dialog.title("Výběr velikosti hracího pole")
        dialog.geometry(f"{dw}x{dh}+{x}+{y}")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Zakážeme zavření křížkem (nebo aspoň varování)
        dialog.protocol("WM_DELETE_WINDOW", lambda: messagebox.showwarning("Pozor", "Prosím použijte tlačítko 'Nová hra'"))

        choice = tk.StringVar(value="4")  # ← defaultně "4" (4x4)

        frame = tk.Frame(dialog, pady=20)
        frame.pack()

        tk.Label(frame, text="Zvolte velikost hlavolamu:", font=("Trebuchet", 14)).pack(pady=(0, 15))

        result = ["4"]

        options = [
            ("3 x 3", "3"),
            ("4 x 4", "4"),
            ("5 x 5", "5"),
        ]

        for text, option in options:
            tk.Radiobutton(
                frame,
                text=text,
                font=("Trebuchet", 12),
                variable=choice,
                value=option
            ).pack(pady=6)

        def new_game_button_click():
            result[0] = choice.get()
            dialog.destroy()

        tk.Button(frame, text="Zahájit hru", font=("Segoe UI", 12), command=new_game_button_click).pack(pady=30)

        dialog.wait_window()
        return int(result[0])

    def set_new_game(self):
        self.canvas.delete("all")
        self.size = self.choose_grid_size_window()
        self.load_images()
        self.canvas_size = self.size * self.tile_size
        self.canvas.config(width=self.canvas_size, height=self.canvas_size)
        self.g = Grid(self.size)
        self.canvas_items = [[None] * self.size for _ in range(self.size)]
        self.canvas_items_init()
        self.animating = False
        self.timer_running = False
        self.start_time = 0
        self.elapsed_time = 0
        self.start_timer()

if __name__ == "__main__":
    app = PuzzleApp()
    app.root.mainloop()