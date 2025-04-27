import requests
from io import BytesIO
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import cv2
import base64
import os

import anthropic

# Anthropic client #
client = anthropic.Anthropic(api_key="")

# Chat memory (store last few exchanges) #
chat_memory = []

root = tk.Tk()
root.title("Magic Deck Builder")
root.geometry("1000x600")

root.grid_columnconfigure(0, weight=3)
root.grid_columnconfigure(1, weight=2)
root.grid_rowconfigure(0, weight=1)

# Left side: Card Area #
card_frame = ttk.Frame(root)
card_frame.grid(row=0, column=0, sticky="nsew")

search_bar_frame = ttk.Frame(card_frame)
search_bar_frame.pack(fill="x", padx=5, pady=5)

search_entry = ttk.Entry(search_bar_frame)
search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

canvas = tk.Canvas(card_frame)
scrollbar = ttk.Scrollbar(card_frame, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas)

scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

image_refs = []
card_widgets = []
pending_commands = []

tooltip = tk.Label(root, text="", bg="black", fg="white", font=("Arial", 10), relief="solid", bd=1)
tooltip.place_forget()

def show_tooltip(event, name):
    tooltip.config(text=name)
    tooltip.place(x=event.x_root + 10, y=event.y_root - 10)

def hide_tooltip(event=None):
    tooltip.place_forget()

def get_deck_list():
    return [
        {"name": name, "count": count_var.get()}
        for _, name, count_var, _ in card_widgets
    ]

def refresh_card_grid():
    for widget in scrollable_frame.winfo_children():
        widget.destroy()

    for idx, (img, name, count_var, card_id) in enumerate(card_widgets):
        container = tk.Frame(scrollable_frame, bd=2, relief="ridge", width=150, height=240)
        container.grid(row=idx // 3, column=idx % 3, padx=5, pady=5)
        container.grid_propagate(False)

        image_label = tk.Label(container, image=img)
        image_label.place(x=0, y=0)
        image_label.bind("<Enter>", lambda e, n=name: show_tooltip(e, n))
        image_label.bind("<Leave>", hide_tooltip)

        count_display = tk.Label(container, textvariable=count_var, bg="white", fg="black", font=("Arial", 10, "bold"))
        count_display.place(x=5, y=5)

        def update(delta, index=idx):
            new_count = card_widgets[index][2].get() + delta
            if new_count <= 0:
                card_widgets.pop(index)
            else:
                card_widgets[index][2].set(new_count)
            refresh_card_grid()

        btn_frame = tk.Frame(container)
        btn_frame.place(x=20, y=215)

        tk.Button(btn_frame, text="+", width=2, command=lambda i=idx: update(1, i)).pack(side="left")
        tk.Button(btn_frame, text="-", width=2, command=lambda i=idx: update(-1, i)).pack(side="left")

def add_card_by_name(card_name, count=1):
    r = requests.get(f"https://api.scryfall.com/cards/named?fuzzy={card_name}")
    if r.status_code == 200:
        data = r.json()
        image_url = data.get("image_uris", {}).get("normal")
        if image_url:
            img_data = requests.get(image_url).content
            img = Image.open(BytesIO(img_data)).resize((150, 210))
            tk_img = ImageTk.PhotoImage(img)
            var = tk.IntVar(value=count)
            card_widgets.append((tk_img, data["name"], var, data["id"]))
            image_refs.append(tk_img)
            refresh_card_grid()

def apply_command(command):
    name = command["card"]
    amount = command["amount"]
    action = command["action"]

    for idx, (_, card_name, count_var, _) in enumerate(card_widgets):
        if card_name.lower() == name.lower():
            if action == "add":
                count_var.set(count_var.get() + amount)
            elif action == "remove":
                count_var.set(max(0, count_var.get() - amount))
                if count_var.get() == 0:
                    card_widgets.pop(idx)
            refresh_card_grid()
            return

    if action == "add":
        add_card_by_name(name, count=amount)
        refresh_card_grid()

def search_and_add_card():
    query = search_entry.get().strip()
    if not query:
        return
    r = requests.get(f"https://api.scryfall.com/cards/named?fuzzy={query}")
    if r.status_code == 200:
        data = r.json()
        card_name = data["name"]
        card_id = data["id"]

        for idx, (_, name, count_var, cid) in enumerate(card_widgets):
            if cid == card_id:
                card_widgets[idx][2].set(count_var.get() + 1)
                refresh_card_grid()
                return

        image_url = data.get("image_uris", {}).get("normal")
        if image_url:
            img_data = requests.get(image_url).content
            img = Image.open(BytesIO(img_data)).resize((150, 210))
            tk_img = ImageTk.PhotoImage(img)
            count = tk.IntVar(value=1)
            card_widgets.append((tk_img, card_name, count, card_id))
            image_refs.append(tk_img)
            refresh_card_grid()

add_button = ttk.Button(search_bar_frame, text="Add Card", command=search_and_add_card)
add_button.pack(side="right", padx=(5, 0))

search_entry.bind("<Return>", lambda event: search_and_add_card())

# Export Deck #
def export_deck():
    if not card_widgets:
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
    if not file_path:
        return

    with open(file_path, "w") as f:
        f.write("// MTG Deck Export\n")
        for _, name, count_var, _ in card_widgets:
            f.write(f"{count_var.get()} {name}\n")

export_button = ttk.Button(card_frame, text="Export Deck", command=export_deck)
export_button.pack(padx=5, pady=5, anchor="w")

# Chat Side #
chat_frame = ttk.Frame(root, padding=10)
chat_frame.grid(row=0, column=1, sticky="nsew")

chat_log = tk.Text(chat_frame, height=30, width=40, state='disabled', wrap="word")
chat_log.pack(pady=(0, 10), fill="both", expand=True)

input_frame = ttk.Frame(chat_frame)
input_frame.pack(fill="x")

user_input = ttk.Entry(input_frame)
user_input.pack(side="left", fill="x", expand=True, padx=(0, 5))

def call_claude(prompt):
    deck = json.loads(json.dumps(get_deck_list()))
    
    history = chat_memory[-6:]  # Last 3 user/assistant pairs

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that manages a Magic: The Gathering deck. You can suggest cards, help build strategies, and modify decks based on user input. Always respond using the JSON format described."
        }
    ] + history + [
        {
            "role": "user",
            "content": f"""Current Deck:
{json.dumps(deck, indent=2)}

User said: "{prompt}"

Respond ONLY with:
{{
  "message": "Your message to user",
  "command": {{
    "action": "add" | "remove",
    "card": "Card name",
    "amount": integer
  }}
}}
If you are unsure, set "command" to null."""
        }
    ]

    try:
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=512,
            temperature=0.5,
            system="You manage a deck of Magic cards.",
            messages=messages
        )

        content = response.content[0].text.strip()
        return json.loads(content)

    except Exception as e:
        return {
            "message": f"Claude error: {str(e)}",
            "command": None
        }

def send_message():
    message = user_input.get().strip()
    if not message:
        return

    chat_log.config(state='normal')
    chat_log.insert("end", f"You: {message}\n")
    chat_log.config(state='disabled')
    chat_log.see("end")

    chat_memory.append({"role": "user", "content": message})

    response = call_claude(message)

    chat_log.config(state='normal')
    chat_log.insert("end", f"Claude: {response['message']}\n")
    chat_log.config(state='disabled')
    chat_log.see("end")
    user_input.delete(0, "end")

    chat_memory.append({"role": "assistant", "content": response['message']})

    if response["command"]:
        approve = messagebox.askyesno("Approve Command", f"Do you want to {response['command']['action']} {response['command']['amount']} {response['command']['card']}?")
        if approve:
            apply_command(response["command"])

send_button = ttk.Button(input_frame, text="Send", command=send_message)
send_button.pack(side="right")

# Camera Scan
def extract_card_info_from_image(image_bytes, mime_type="image/jpeg"):
    message = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("utf-8")
                        }
                    },
                    {
    "type": "text",
    "text": """You are given an image of a Magic: The Gathering card. Please try to extract its details.

If the card's text is readable and in English, extract the information as exactly shown.

If the text is unclear, missing, or in another language, identify the card based on its artwork instead.

Format the output strictly as:
Name: [Card Name]
Mana Cost: [Mana Cost]
Type: [Card Type]
Set: [Set Name]
Text: [Card Text]

Leave any unknown fields blank. Do NOT add commentary or guesses outside of this format."""
}

                ]
            }
        ]
    )
    return message.content[0].text

def scan_card_with_camera():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        messagebox.showerror("Camera Error", "Cannot open webcam.")
        return

    messagebox.showinfo("Camera", "Press SPACE to capture, ESC to cancel.")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imshow('Capture Card (Press SPACE)', frame)

        key = cv2.waitKey(1)
        if key % 256 == 27:  # ESC
            cap.release()
            cv2.destroyAllWindows()
            return
        elif key % 256 == 32:  # SPACE
            _, buffer = cv2.imencode('.jpg', frame)
            image_bytes = buffer.tobytes()
            cap.release()
            cv2.destroyAllWindows()

            try:
                text_info = extract_card_info_from_image(image_bytes)
                lines = text_info.splitlines()
                card_name = ""
                for line in lines:
                    if line.lower().startswith("name:"):
                        card_name = line.split(":", 1)[1].strip()
                        break

                if card_name:
                    confirm = messagebox.askyesno("Confirm Card", f"Found card: {card_name}\n\nAdd this card to your deck?")
                    if confirm:
                        add_card_by_name(card_name)
                        refresh_card_grid()
                        chat_log.config(state="normal")
                        chat_log.insert("end", f"📸 Scanned and added card: {card_name}\n")
                        chat_log.config(state="disabled")
                        chat_log.see("end")
                else:
                    messagebox.showerror("Scan Failed", "Could not find card name.")

            except Exception as e:
                messagebox.showerror("Scan Error", f"Error scanning image: {str(e)}")
            break

scan_button = ttk.Button(search_bar_frame, text="📸 Scan Card", command=scan_card_with_camera)
scan_button.pack(side="right", padx=(5, 0))

root.mainloop()
