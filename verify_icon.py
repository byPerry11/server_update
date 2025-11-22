import flet as ft

try:
    i = ft.Icon(name="dns")
    print("Successfully created Icon with name='dns'")
except Exception as e:
    print(f"Error creating Icon: {e}")
