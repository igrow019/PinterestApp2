import flet as ft
import requests
from datetime import datetime
import json
import os

# --- CONFIGURATION ---
FIREBASE_URL = "https://pinterestmanager-e8dee-default-rtdb.firebaseio.com"
LOCAL_FILE_NAME = "pinterest_data.json"

def main(page: ft.Page):
    page.title = "Pinterest Monitor"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#1e1e1e"
    page.scroll = "adaptive"
    page.padding = 10

    accounts_column = ft.Column(spacing=15)
    status_indicator = ft.Text("Initializing...", size=12, color="grey")

    # --- FILE STORAGE FUNCTIONS (Replaces Memory) ---
    def save_data_to_file(data):
        """Saves data to a real file on the phone's disk"""
        try:
            with open(LOCAL_FILE_NAME, "w") as f:
                json.dump(data, f)
            print("Data saved to file successfully.")
        except Exception as e:
            print(f"Failed to save file: {e}")

    def load_data_from_file():
        """Reads data from the real file on the phone's disk"""
        if os.path.exists(LOCAL_FILE_NAME):
            try:
                with open(LOCAL_FILE_NAME, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to read file: {e}")
                return None
        return None

    # --- LOGIC ---
    def parse_time(date_str):
        if not date_str: return None
        try:
            if "." in date_str: date_str = date_str.split(".")[0]
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except: return None

    def get_status_color(hours_left):
        if hours_left < 0: return "#ff4444"      
        if hours_left < 24: return "#ff4444"     
        if hours_left < 48: return "#ff9800"     
        return "#4caf50"                         

    def build_ui(data, source="Cloud"):
        accounts_column.controls.clear()
        
        if not data:
            accounts_column.controls.append(ft.Text("No accounts found.", color="grey"))
            page.update()
            return

        for name, info in data.items():
            batches = info.get('batches', {})
            current_batch_name = "All Batches Done"
            time_msg = "No Content"
            color = "#555"
            b_end = None
            
            if batches:
                sorted_batches = []
                for k, v in batches.items():
                    end_dt = parse_time(v.get('end'))
                    display_name = v.get('original_name', k)
                    if end_dt:
                        sorted_batches.append((display_name, end_dt))
                
                sorted_batches.sort(key=lambda x: x[1])
                now = datetime.now()
                target_batch = None
                
                for b_name, b_end_val in sorted_batches:
                    if b_end_val > now:
                        target_batch = (b_name, b_end_val)
                        break
                
                if not target_batch and sorted_batches:
                    target_batch = sorted_batches[-1]

                if target_batch:
                    b_name, b_end = target_batch
                    diff = b_end - now
                    hours = diff.total_seconds() / 3600
                    current_batch_name = b_name
                    
                    if hours < 0:
                        time_msg = f"EXPIRED {abs(int(hours))}h ago"
                        color = "#ff4444"
                    else:
                        days = int(hours // 24)
                        h_left = int(hours % 24)
                        if days > 0:
                            time_msg = f"{days}d {h_left}h Left"
                        else:
                            time_msg = f"{h_left}h Left (Hurry!)"
                        color = get_status_color(hours)

            # --- UI CARD ---
            card = ft.Container(
                bgcolor="#2b2d30",
                border_radius=12,
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.icons.PUSH_PIN, color="red"),
                        ft.Text(name, size=18, weight="bold", color="white")
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Divider(color="#444"),
                    ft.Text("CURRENT BATCH:", color="grey", size=10, weight="bold"),
                    ft.Text(current_batch_name, size=16, weight="bold", color="white"),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(time_msg, color="white", weight="bold", size=18),
                            ft.Text(f"Ends: {str(b_end)[:16] if b_end else '-'}", size=10, color="white70")
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor=color,
                        padding=15,
                        border_radius=8,
                        alignment=ft.alignment.center,
                    )
                ])
            )
            accounts_column.controls.append(card)
        
        status_indicator.value = f"Data Source: {source}"
        status_indicator.color = "green" if source == "Cloud" else "orange"
        page.update()

    def refresh_data(e=None):
        status_indicator.value = "Syncing..."
        page.update()
        try:
            # 1. ATTEMPT CLOUD DOWNLOAD
            response = requests.get(f"{FIREBASE_URL}/accounts.json", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    # SUCCESS: Show Data AND Save to File (No Timeout Limit)
                    build_ui(data, source="Cloud")
                    save_data_to_file(data) 
                else:
                    load_offline()
            else:
                load_offline()
        except Exception as ex:
            print(f"Sync failed: {ex}")
            load_offline()

    def load_offline():
        """Loads from the physical file if internet fails"""
        cached_data = load_data_from_file()
        if cached_data:
            build_ui(cached_data, source="Offline File")
        else:
            accounts_column.controls.clear()
            accounts_column.controls.append(ft.Text("No internet & No saved file.", color="red"))
            status_indicator.value = "Connection Failed"
            status_indicator.color = "red"
            page.update()

    fab = ft.FloatingActionButton(
        icon=ft.icons.REFRESH, 
        bgcolor="#007acc", 
        on_click=refresh_data
    )
    
    page.add(
        ft.Container(
            content=ft.Column([
                ft.Text("Pinterest Monitor", size=26, weight="bold", color="white"),
                status_indicator
            ]),
            padding=ft.padding.only(bottom=10, top=10)
        ),
        accounts_column
    )
    page.floating_action_button = fab
    
    # Try to load offline data first (instant start), then sync
    load_offline()
    refresh_data()

ft.app(target=main)