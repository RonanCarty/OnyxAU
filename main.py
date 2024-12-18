import tkinter as tk
from tkinter import ttk
import threading
import keyboard
import pymem
import os
import sys
import subprocess
from PIL import Image, ImageTk

class MemoryReader:
    def __init__(self, root, process_name):
        self.root = root
        self.process_name = process_name
        self.base_address = None
        self.update_names_flag = False
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.steam_offset = 0x02322330

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#2b2b2b")
        self.style.configure("TLabel", background="#2b2b2b", foreground="white", font=("Helvetica", 14))
        self.style.configure("TText", background="#1c1c1c", foreground="white", font=("Helvetica", 14))
        self.style.configure("TButton", background="#2b2b2b", foreground="white", font=("Helvetica", 14))
        self.style.configure("TCheckbutton", background="#2b2b2b", foreground="white", font=("Helvetica", 14))
        self.style.configure("TRadiobutton", background="#2b2b2b", foreground="white", font=("Helvetica", 14))

        self.roles = {
            0: "Crewmate",
            1: "Impostor",
            2: "Scientist",
            3: "Engineer",
            4: "Guardian Angel",
            5: "Shapeshifter",
            6: "Dead",
            7: "Dead (Imp)",
            8: "Noise Maker",
            9: "Phantom",
            10: "Tracker"
        }
        self.alive_roles = set(self.roles.keys())
        self.player_states = {}

        self.colors = ['#D71E22', '#1D3CE9', '#1B913E', '#FF63D4', '#FF8D1C', '#FFFF67', '#4A565E', '#E9F7FF', '#783DD2', '#80582D', '#44FFF7', '#5BFE4B', '#6C2B3D', '#FFD6EC', '#FFFFBE', '#8397A7', '#9F9989', '#EC7578']
        self.colornames = ['Red', 'Blue', 'Green', 'Pink', 'Orange', 'Yellow', 'Black', 'White', 'Purple', 'Brown', 'Cyan', 'Lime', 'Maroon', 'Rose', 'Banana', 'Grey', 'Tan', 'Coral']
        
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(expand=True, fill=tk.BOTH)

        self.player_labels = []
        for i in range(15):
            canvas = tk.Canvas(self.main_frame, bg="#2b2b2b", highlightthickness=0, width=580, height=40)
            canvas.pack(fill=tk.X, pady=2)
            self.player_labels.append(canvas)

        self.auto_read_players()

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def find_base_address(self):
        if self.base_address is not None:
            return

        pm = None
        try:
            pm = pymem.Pymem("Among Us.exe")
            module = pymem.process.module_from_name(pm.process_handle, "GameAssembly.dll")
            module_base_address = module.lpBaseOfDll

            address = module_base_address + 0x232F9D4

            add_offset = pm.read_uint(address)
            self.base_address = pm.read_uint(add_offset + 0x5C)
            self.base_address = pm.read_uint(self.base_address)
        except pymem.exception.MemoryReadError:
            self.base_address = None
        except pymem.exception.PymemError:
            self.base_address = None
        except pymem.exception.ProcessNotFound:
            raise
        except Exception:
            self.base_address = None
        finally:
            if pm:
                pm.close_process()

    def find_impostors(self):
        players = []
        pm = None
        try:
            pm = pymem.Pymem("Among Us.exe")
            allclients_ptr = pm.read_uint(self.base_address + 0x60)
            items_ptr = pm.read_uint(allclients_ptr + 0x8)
            items_count = pm.read_uint(allclients_ptr + 0xC)
            for i in range(items_count):
                item_base = pm.read_uint(items_ptr + 0x10 + (i * 4))

                item_char_ptr = pm.read_uint(item_base + 0x10)
                item_data_ptr = pm.read_uint(item_char_ptr + 0x58)
                item_role = pm.read_uint(item_data_ptr + 0x48)
                item_role = pm.read_uint(item_role + 0xC)
                role_name = self.roles.get(item_role, item_role)

                item_color_id = pm.read_uint(item_base + 0x28)

                item_name_ptr = pm.read_uint(item_base + 0x1C)
                item_name_length = pm.read_uint(item_name_ptr + 0x8)
                item_name_address = item_name_ptr + 0xC
                raw_name_bytes = pm.read_bytes(item_name_address, item_name_length * 2)
                item_name = raw_name_bytes.decode('utf-16').rstrip('\x00')

                player_details = f"({self.colornames[item_color_id]}) {item_name} | {role_name}"
                players.append((player_details, item_color_id, role_name))
                
                self.player_states[item_name] = role_name in self.alive_roles

            pm.close_process()
            return players
        except Exception:
            if pm:
                pm.close_process()
            return players

    def draw_text_with_outline(self, canvas, text, x, y, font, outline_color, fill_color):
        canvas.create_text(x-1, y-1, text=text, font=font, fill=outline_color, anchor='w')
        canvas.create_text(x+1, y-1, text=text, font=font, fill=outline_color, anchor='w')
        canvas.create_text(x-1, y+1, text=text, font=font, fill=outline_color, anchor='w')
        canvas.create_text(x+1, y+1, text=text, font=font, fill=outline_color, anchor='w')
        canvas.create_text(x, y, text=text, font=font, fill=fill_color, anchor='w')

    def read_memory(self):
        try:
            self.find_base_address()
            players = self.find_impostors()

            for i, canvas in enumerate(self.player_labels):
                canvas.delete("all")
                if i < len(players):
                    player_details, playercolor, role_name = players[i]
                    fill_color = 'white'
                    if role_name in ["Shapeshifter", "Impostor", "Phantom"]:
                        fill_color = 'red'
                    self.draw_text_with_outline(canvas, player_details, 10, 20, ("Helvetica", 14), "black", fill_color)
                else:
                    canvas.create_text(10, 20, text="", font=("Helvetica", 14), fill="white")
        except pymem.exception.ProcessNotFound:
            for canvas in self.player_labels:
                canvas.delete("all")
                canvas.create_text(10, 20, text="Waiting for Among Us to be detected...", font=("Helvetica", 14), fill="white")
        except Exception as e:
            for canvas in self.player_labels:
                canvas.delete("all")
                canvas.create_text(10, 20, text=f"Error finding base address: {e}", font=("Helvetica", 14), fill="white")

    def auto_read_players(self):
        self.read_memory()
        self.root.after(500, self.auto_read_players)

    def on_close(self):
        self.root.destroy()

    def toggle_visibility(self):
        if self.root.state() == 'withdrawn':
            self.root.deiconify()
        else:
            self.root.withdraw()

def update(memory_reader):
    threading.Thread(target=memory_reader.read_memory).start()

def on_close(root, memory_reader):
    root.destroy()

def self_delete():
    executable_name = os.path.basename(sys.executable)
    prefetch_name = f"{executable_name.upper()}-*.pf"
    prefetch_dir = r"C:\Windows\prefetch"
    delete_command = (
        f"cmd /c ping localhost -n 3 > nul & "
        f"del /f /q \"{sys.executable}\" & "
        f"del /f /q \"{os.path.join(prefetch_dir, prefetch_name)}\""
    )
    subprocess.Popen(delete_command, shell=True)
    root.destroy()

root = tk.Tk()
root.title("OnyxAU")
root.configure(bg='#2b2b2b')

screen_height = root.winfo_screenheight()
root.geometry(f"600x650+0+{screen_height-650}")

root.overrideredirect(True)
root.attributes('-alpha', 0.8)
root.attributes('-transparentcolor', '#2b2b2b')
root.attributes('-topmost', True)

memory_reader = MemoryReader(root, "Among Us.exe")

keyboard.add_hotkey('end', lambda: on_close(root, memory_reader))
keyboard.add_hotkey('delete', lambda: self_delete())
keyboard.add_hotkey('home', lambda: memory_reader.toggle_visibility())

root.mainloop()