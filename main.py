import customtkinter as ctk
from gui.main_window import MainWindow

def main():
    ctk.set_appearance_mode("dark")  # hoặc "light"
    ctk.set_default_color_theme("green")
    
    root = ctk.CTk()
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()